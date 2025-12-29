import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routers import webhook as webhook_router
from app.schemas.message import MessageRequest, MessageResponse
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services import escalation_service
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    SemanticServiceMatch,
    get_demo_salon_decision,
    semantic_service_match,
)
from app.services.intent_service import (
    Intent,
    classify_domain_with_scores,
    is_opt_out_message,
    is_strong_out_of_domain,
)
from app.services.message_service import select_handover_user_message
from app.services.result import Result
from app.services.state_machine import ConversationState


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fake_intent_decomp():
    def _detect_stub(text: str):
        normalized = (text or "").casefold()
        intents: list[str] = []

        if re.search(r"\b(запис|запишите|запиши|записать|бронь|заброн)\b", normalized):
            intents.append("booking")
        if re.search(r"\b(сегодня|завтра|послезавтра)\b", normalized) and re.search(r"\b\d{1,2}\b", normalized):
            intents.append("booking")

        if any(keyword in normalized for keyword in ["цена", "стоим", "стоимость", "прайс", "сколько стоит", "почем"]):
            intents.append("pricing")
        if any(
            keyword in normalized
            for keyword in [
                "сколько длится",
                "длится",
                "длительность",
                "по времени",
                "сколько по времени",
                "сколько времени",
                "время процедуры",
            ]
        ):
            intents.append("duration")
        if any(keyword in normalized for keyword in ["работаете", "график", "режим работы", "часы", "во сколько"]):
            intents.append("hours")

        if not intents:
            intents = ["other"]

        primary = intents[0]
        secondary = [intent for intent in intents[1:] if intent != primary]
        return {
            "multi_intent": len(intents) > 1,
            "primary_intent": primary,
            "secondary_intents": secondary,
            "intents": intents,
            "service_query": "",
        }

    with patch("app.routers.webhook.detect_multi_intent", side_effect=_detect_stub):
        yield


@pytest.fixture(autouse=True)
def _disable_debounce_redis():
    with patch("app.routers.webhook._get_debounce_redis", return_value=None):
        yield


DEMO_DOMAIN_ROUTER_CONFIG = {
    "anchors_in": [
        "запись на услугу",
        "записаться на маникюр",
        "запис",
        "услуг",
        "адрес салона",
        "адрес",
        "как добраться",
        "часы работы",
        "часы",
        "график работы",
        "график",
        "режим работы",
        "во сколько",
        "цены на услуги",
        "прайс салона",
        "маникюр педикюр",
        "стрижка окрашивание",
        "брови ресницы",
        "уход за лицом",
        "депиляция шугаринг",
        "макияж укладка",
        "макияж",
        "кошачий глаз",
        "референс прически",
        "прическа как у",
    ],
    "anchors_in_strict": [
        "запис",
        "услуг",
        "адрес",
        "часы",
        "график",
        "режим",
    ],
    "anchors_out": [
        "погода сегодня",
        "прогноз погоды",
        "анекдот",
        "стихотворение",
        "политика новости",
        "выборы президент",
        "рецепт",
        "как приготовить",
        "программирование",
        "напиши код",
        "python",
        "личные советы",
        "совет по отношениям",
        "ветеринар",
        "животн",
        "питомец",
        "питомц",
        "собак",
        "собач",
        "пес",
        "пёс",
        "кот",
        "кошка",
        "кошк",
        "стрижка собаки",
        "стрижка кошки",
        "постричь козу",
        "спасти сестру",
        "слепая сестра",
        "слепой сестре",
    ],
    "in_threshold": 0.55,
    "out_threshold": 0.55,
    "margin": 0.03,
}


def _fake_service_hint(text: str, client_slug: str | None) -> str | None:
    normalized = (text or "").casefold()
    if "маник" in normalized:
        return "маникюр"
    if "педик" in normalized:
        return "педикюр"
    if "стриж" in normalized:
        return "стрижка"
    if "массаж" in normalized and "ног" in normalized:
        return "массаж ног"
    if "бров" in normalized:
        return "брови"
    if "ресниц" in normalized:
        return "ресницы"
    return None


class TestMessageEndpoint:
    def test_message_request_validation(self, client):
        # Missing required fields
        response = client.post("/message", json={"content": "Привет!"})
        assert response.status_code == 422

    def test_message_with_invalid_uuid(self, client):
        response = client.post(
            "/message",
            json={"client_id": "not-a-uuid", "remote_jid": "77759841926@s.whatsapp.net", "content": "Привет!"},
        )
        assert response.status_code == 422


class TestMessageSchemas:
    def test_message_request_valid(self):
        req = MessageRequest(
            client_id=uuid4(), remote_jid="77759841926@s.whatsapp.net", content="Test", channel="whatsapp"
        )
        assert req.content == "Test"
        assert req.channel == "whatsapp"

    def test_message_response_valid(self):
        resp = MessageResponse(success=True, conversation_id=uuid4(), state="bot_active", bot_response="Test response")
        assert resp.success == True
        assert resp.state == "bot_active"


def _build_db(client_slug: str, webhook_secret: str | None):
    client = Mock()
    client.id = "client-123"
    client.name = client_slug

    settings = Mock()
    settings.webhook_secret = webhook_secret

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client

    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings

    db = Mock()
    db.query.side_effect = [client_query, settings_query]
    return db


class TestWebhookAuth:
    def _client_with_db(self, db):
        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        return TestClient(app)

    def test_missing_secret_returns_401(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post("/webhook", json={"client_slug": "test", "body": {"message": "hi"}})
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_invalid_secret_returns_401(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi"}},
                headers={"X-Webhook-Secret": "wrong"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_valid_secret_returns_200(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi"}},
                headers={"X-Webhook-Secret": "secret"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.webhook.alert_warning")
    def test_missing_secret_allows_request_with_warning(self, mock_alert):
        db = _build_db("test", None)
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi"}},
            )
            assert response.status_code == 200
            mock_alert.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_query_secret_fallback_returns_200(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook?webhook_secret=secret",
                json={"client_slug": "test", "body": {"message": "hi"}},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_direct_webhook_missing_secret_returns_401(self):
        db = _build_db("direct", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post("/webhook/direct", json={"client_slug": "direct", "body": {"message": "hi"}})
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


def _mock_db_with_messages(messages):
    query = Mock()
    query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = messages

    db = Mock()
    db.query.return_value = query
    return db


class TestSelectHandoverUserMessage:
    def test_uses_previous_meaningful_message(self):
        messages = [
            Mock(content="позови менеджера"),
            Mock(content="а вы можете сделать прическу как майкла джордана?"),
        ]
        db = _mock_db_with_messages(messages)

        result = select_handover_user_message(db, uuid4(), "позови менеджера")

        assert result == "а вы можете сделать прическу как майкла джордана?"

    def test_falls_back_when_no_better_message(self):
        messages = [
            Mock(content="позови менеджера"),
            Mock(content="ок"),
            Mock(content="спасибо"),
        ]
        db = _mock_db_with_messages(messages)

        result = select_handover_user_message(db, uuid4(), "позови менеджера")

        assert result == "позови менеджера"


class TestBatchBookingSignals:
    def test_booking_signal_across_messages(self):
        messages = ["сколько стоит маникюр", "на завтра в 5"]
        with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
            assert (
                webhook_router._has_booking_signal(
                    messages,
                    client_slug="demo_salon",
                    message_text=messages[-1],
                )
                is True
            )

    def test_booking_signal_blocked_for_info_question(self):
        messages = ["Вы сегодня работаете? Сколько стоит педикюр?"]
        with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint), patch(
            "app.routers.webhook.semantic_question_type",
            return_value=SimpleNamespace(kind="pricing", score=0.72, second_score=0.1),
        ):
            assert (
                webhook_router._has_booking_signal(
                    messages,
                    client_slug="demo_salon",
                    message_text=messages[0],
                )
                is False
            )

    def test_booking_updates_across_messages(self):
        booking = {"active": True}
        with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
            updated = webhook_router._update_booking_from_messages(
                booking,
                ["маникюр", "на завтра в 5"],
                client_slug="demo_salon",
            )
        assert updated.get("service") == "маникюр"
        assert updated.get("datetime") == "завтра"


class TestBookingSlotGuards:
    def test_booking_name_skips_opt_out(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(
            booking,
            ["не пиши мне"],
            client_slug="demo_salon",
        )
        assert updated.get("name") is None

    def test_booking_name_skips_frustration(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(
            booking,
            ["иди нахуй"],
            client_slug="demo_salon",
        )
        assert updated.get("name") is None


class TestServiceHints:
    def test_service_hint_within_window(self):
        now = datetime.now(timezone.utc)
        context = webhook_router._set_service_hint({}, "маникюр", now)

        hint = webhook_router._get_recent_service_hint(context, now + timedelta(minutes=30))

        assert hint == "маникюр"

    def test_service_hint_expires(self):
        now = datetime.now(timezone.utc)
        context = webhook_router._set_service_hint({}, "маникюр", now)

        hint = webhook_router._get_recent_service_hint(
            context,
            now + timedelta(minutes=webhook_router.SERVICE_HINT_WINDOW_MINUTES + 1),
        )

        assert hint is None


class TestReengageConfirmation:
    def test_reengage_confirmation_active(self):
        now = datetime.now(timezone.utc)
        confirmation = {"asked_at": now.isoformat(), "booking_messages": ["запишите на завтра"]}

        assert webhook_router._is_reengage_confirmation_active(
            confirmation,
            now + timedelta(minutes=5),
        )

    def test_reengage_confirmation_expires(self):
        now = datetime.now(timezone.utc)
        confirmation = {"asked_at": now.isoformat(), "booking_messages": ["запишите на завтра"]}

        assert (
            webhook_router._is_reengage_confirmation_active(
                confirmation,
                now + timedelta(minutes=webhook_router.REENGAGE_CONFIRM_WINDOW_MINUTES + 1),
            )
            is False
        )


class TestRoutingPolicy:
    def test_routing_policy_bot_active(self):
        policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)
        assert policy["allow_booking_flow"] is True
        assert policy["allow_handover_create"] is True
        assert policy["allow_bot_reply"] is True

    def test_routing_policy_pending(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        assert policy["allow_booking_flow"] is False
        assert policy["allow_handover_create"] is False
        assert policy["allow_truth_gate_reply"] is False
        assert policy["allow_bot_reply"] is False

    def test_routing_policy_manager_active(self):
        policy = webhook_router._get_routing_policy(ConversationState.MANAGER_ACTIVE.value)
        assert policy["allow_bot_reply"] is False
        assert policy["allow_truth_gate_reply"] is False

    def test_booking_flow_runs_with_signal_in_pending(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        should_run = webhook_router._should_run_booking_flow(
            policy,
            booking_active=False,
            booking_signal=True,
        )
        assert should_run is False

    def test_demo_truth_gate_skips_when_booking(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        assert webhook_router._should_run_demo_truth_gate(policy, booking_wants_flow=True) is False

    def test_escalate_gate_respects_policy(self):
        pending_policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        active_policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)

        assert webhook_router._should_escalate_to_pending(pending_policy, Intent.HUMAN_REQUEST) is False
        assert webhook_router._should_escalate_to_pending(active_policy, Intent.HUMAN_REQUEST) is True


class TestFastIntent:
    @pytest.mark.parametrize(
        "message,expect_action,expect_intent",
        [
            ("Сәлем!", "smalltalk", "greeting"),
            ("спасибо", "smalltalk", "thanks"),
            ("ок", "smalltalk", "ack"),
        ],
    )
    def test_fast_intent_matches(self, message, expect_action, expect_intent):
        decision = webhook_router._detect_fast_intent(
            message,
            policy_type="demo_salon",
            booking_wants_flow=False,
            bypass_domain_flows=False,
        )

        assert decision is not None
        assert decision.action == expect_action
        assert decision.intent == expect_intent

    def test_fast_intent_fallback_to_llm(self):
        message = "Есть ли у вас абонементы?"
        decision = webhook_router._detect_fast_intent(
            message,
            policy_type="demo_salon",
            booking_wants_flow=False,
            bypass_domain_flows=False,
        )

        assert decision is None

        with patch("app.routers.webhook.classify_intent", return_value=Intent.QUESTION) as mock_classify:
            signals = webhook_router._detect_intent_signals(message)
        assert signals.intent == Intent.QUESTION
        mock_classify.assert_called_once()


def test_truth_gate_sets_decision_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие услуги у вас есть?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-123",
                timestamp=1234567890,
            ),
        ),
    )

    decision = DemoSalonDecision(action="reply", response="OK", intent="services_overview")

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return decision

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}
    low_confidence = SimpleNamespace(ok=True, value=(None, "low_confidence"))

    with patch("app.routers.webhook._get_policy_handler", return_value=policy_handler), patch(
        "app.routers.webhook.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert mock_update.call_count >= 1
    updates = [call.args[1] for call in mock_update.call_args_list]
    truth_updates = next(item for item in updates if item.get("source") == "truth_gate")
    assert truth_updates["fast_intent"] is False
    assert truth_updates["llm_primary_used"] is False
    assert truth_updates["llm_used"] is False
    assert truth_updates["llm_timeout"] is False


def test_semantic_service_matcher_handles_low_confidence_match():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="делаете манник?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-semantic-1",
                timestamp=1234567890,
            ),
        ),
    )

    low_confidence = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    semantic = SemanticServiceMatch(action="match", response="Маникюр — 2 500 ₸.", score=0.52)

    with patch("app.routers.webhook._get_policy_handler", return_value=None), patch(
        "app.routers.webhook.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook.semantic_service_match", return_value=semantic
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook._extract_service_hint", return_value=None
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == semantic.response
    updates = mock_update.call_args[0][1]
    assert updates["source"] == "service_semantic_matcher"
    assert updates["action"] == "match"
    assert updates["service_semantic_score"] == semantic.score


def test_semantic_service_matcher_handles_low_confidence_suggest():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="делаете массаж ног?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-semantic-2",
                timestamp=1234567890,
            ),
        ),
    )

    low_confidence = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    semantic = SemanticServiceMatch(
        action="suggest",
        response="В списке услуг нет такой позиции. Возможно, вы имели в виду: уход за лицом.",
        score=0.31,
        suggestions=["Уход за лицом"],
    )

    with patch("app.routers.webhook._get_policy_handler", return_value=None), patch(
        "app.routers.webhook.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook.semantic_service_match", return_value=semantic
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook._extract_service_hint", return_value=None
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == semantic.response
    updates = mock_update.call_args[0][1]
    assert updates["source"] == "service_semantic_matcher"
    assert updates["action"] == "suggest"
    assert updates["service_semantic_score"] == semantic.score


def test_semantic_service_matcher_uses_rewrite_on_low_confidence():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="манник",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-semantic-3",
                timestamp=1234567890,
            ),
        ),
    )

    low_confidence = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    semantic = SemanticServiceMatch(action="match", response="Маникюр — 2 500 ₸.", score=0.52)

    def semantic_side_effect(text: str, client_slug: str):
        if text == "маникюр":
            return semantic
        return None

    with patch("app.routers.webhook._get_policy_handler", return_value=None), patch(
        "app.routers.webhook.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook.semantic_service_match", side_effect=semantic_side_effect
    ) as mock_semantic, patch(
        "app.routers.webhook.rewrite_for_service_match", return_value="маникюр"
    ) as mock_rewrite, patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook._extract_service_hint", return_value=None
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == semantic.response
    assert mock_semantic.call_count == 2
    mock_rewrite.assert_called_once()
    updates = mock_update.call_args[0][1]
    assert updates["service_semantic_rewrite_used"] is True
    assert updates["service_semantic_rewrite_query"] == "маникюр"


def test_semantic_service_matcher_allows_short_query_without_keywords():
    results = [
        {
            "score": 0.5,
            "payload": {"canonical_name": "Маникюр"},
        }
    ]

    with patch(
        "app.services.demo_salon_knowledge._search_services_index", return_value=results
    ), patch(
        "app.services.demo_salon_knowledge._format_semantic_service_reply",
        return_value="Маникюр — 2 500 ₸.",
    ):
        result = semantic_service_match("манник?", "demo_salon")

    assert result is not None
    assert result.action == "match"
    assert result.response == "Маникюр — 2 500 ₸."


def test_semantic_question_type_routes_duration_and_price():
    import app.services.demo_salon_knowledge as demo_salon_knowledge

    def fake_embedding(text: str):
        normalized = text.casefold()
        if "дл" in normalized or "врем" in normalized:
            return [1.0, 0.0]
        if "стоит" in normalized or "цена" in normalized or "прайс" in normalized:
            return [0.0, 1.0]
        return [0.1, 0.1]

    with patch("app.services.demo_salon_knowledge.get_embedding", side_effect=fake_embedding):
        demo_salon_knowledge._question_type_examples.cache_clear()
        demo_salon_knowledge._question_type_embeddings.cache_clear()

        decision = get_demo_salon_decision("Сколько длится процедура?")
        assert decision is not None
        assert decision.intent == "service_duration"
        assert "по времени" in decision.response.casefold() or "какая именно" in decision.response.casefold()

        decision = get_demo_salon_decision("Сколько стоит процедура?")
        assert decision is not None
        assert decision.intent == "price_query"

        decision = get_demo_salon_decision("Сколько по времени маникюр?")
        assert decision is not None
        assert decision.intent == "service_duration"
        assert "маникюр" in decision.response.casefold()


def test_service_matcher_short_circuits_llm():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Делаете педикюр?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service",
                timestamp=1234567890,
            ),
        ),
    )

    policy_handler = {"policy_type": "demo_salon", "service_matcher": webhook_router.get_demo_salon_service_decision}

    with patch("app.routers.webhook._get_policy_handler", return_value=policy_handler), patch(
        "app.routers.webhook.generate_bot_response"
    ) as mock_llm, patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert "педикюр" in (response.bot_response or "").casefold()
    mock_llm.assert_not_called()
    updates = mock_update.call_args[0][1]
    assert updates["source"] == "service_matcher"
    assert updates["llm_primary_used"] is False


def test_llm_guard_blocks_payment_response():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=branch_id,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу узнать подробности.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-guard",
                timestamp=1234567890,
            ),
        ),
    )

    llm_result = SimpleNamespace(ok=True, value=("Оплата картой возможна.", "high"))
    handover = SimpleNamespace(id="handover-123")

    with patch("app.routers.webhook._get_policy_handler", return_value=None), patch(
        "app.routers.webhook.generate_bot_response", return_value=llm_result
    ), patch(
        "app.routers.webhook._reuse_active_handover", return_value=(None, False, False)
    ), patch(
        "app.routers.webhook.escalate_to_pending", return_value=SimpleNamespace(ok=True, value=handover)
    ), patch(
        "app.routers.webhook.send_telegram_notification", return_value=True
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook._update_message_decision_metadata"
    ) as mock_update:
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == webhook_router.MSG_ESCALATED
    updates = mock_update.call_args[0][1]
    assert updates["source"] == "llm_guard"
    assert updates["llm_primary_used"] is False


def test_audio_transcription_failure_returns_prompt():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="audio",
            message=None,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-voice-123",
                timestamp=1234567890,
            ),
            mediaData={"type": "audio", "mimetype": "audio/ogg", "ptt": True, "size": 100},
        ),
    )

    asr_meta = {
        "asr_used": True,
        "asr_provider": "openai_whisper",
        "asr_fallback_used": False,
        "asr_failed": True,
        "asr_text_len": 0,
    }

    with patch(
        "app.routers.webhook._maybe_transcribe_voice",
        AsyncMock(return_value=(None, "empty_transcript", asr_meta)),
    ), patch(
        "app.routers.webhook._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook._store_media_locally",
        return_value={"stored": False, "path": None, "error": None},
    ), patch(
        "app.routers.webhook.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == webhook_router.MSG_MEDIA_TRANSCRIPT_FAILED
    assert saved_message.message_metadata["asr"]["asr_failed"] is True


def test_multi_intent_long_message_prioritizes_booking():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    db.refresh = Mock()

    long_text = (
        "Можно записаться завтра и сколько длится маникюр? "
        + "Дополнительная информация. " * 20
    ).strip()
    assert len(long_text) >= webhook_router.MULTI_INTENT_MIN_CHARS

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="text",
            message=long_text,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-long-123",
                timestamp=1234567890,
            ),
        ),
    )

    multi_payload = {
        "multi_intent": True,
        "primary_intent": "booking",
        "secondary_intents": ["duration"],
    }

    with patch(
        "app.routers.webhook.detect_multi_intent",
        return_value=multi_payload,
    ), patch(
        "app.routers.webhook.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
                batch_messages=[long_text],
            )
        )

    assert response.success is True
    assert any(
        prompt in response.bot_response
        for prompt in (
            webhook_router.MSG_BOOKING_ASK_SERVICE,
            webhook_router.MSG_BOOKING_ASK_DATETIME,
            webhook_router.MSG_BOOKING_ASK_NAME,
        )
    )
    assert "длител" in response.bot_response.casefold()


def test_multi_truth_reply_handles_hours_and_service_without_booking():
    saved_message_first = Mock()
    saved_message_first.message_metadata = {}
    saved_message_second = Mock()
    saved_message_second.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user

        db = Mock()
        db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload_info = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Здравствуйте! Вы сегодня работаете? Вы маникюром занимаетесь?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-info-1",
                timestamp=1234567890,
            ),
        ),
    )
    payload_name = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="ислам",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-info-2",
                timestamp=1234567891,
            ),
        ),
    )

    def _fake_question_type(segment: str, *, include_kinds=None, return_multi: bool = False):
        normalized = (segment or "").casefold()
        if "работаете" in normalized:
            result = SimpleNamespace(kind="hours", score=0.81, second_score=0.1)
            return [result] if return_multi else result
        return [] if return_multi else None

    def _fake_search_services_index(text: str, client_slug: str, limit: int):
        normalized = (text or "").casefold()
        if "маник" in normalized:
            return [{"score": 0.9, "payload": {"canonical_name": "Маникюр"}}]
        if "ислам" in normalized:
            return [{"score": 0.5, "payload": {"canonical_name": "Маникюр"}}]
        return []

    with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint), patch(
        "app.routers.webhook.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge._search_services_index", side_effect=_fake_search_services_index
    ), patch(
        "app.routers.webhook.generate_bot_response",
        side_effect=[
            Result.success((None, "low_confidence")),
            Result.success(("ok", "high")),
        ],
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        side_effect=[saved_message_first, saved_message_second],
    ), patch(
        "app.routers.webhook.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook.escalate_to_pending"
    ) as mock_escalate:
        mock_reuse.return_value = (None, False, False)
        mock_escalate.return_value = SimpleNamespace(ok=False, error="test")
        response_info = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload_info,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )
        response_name = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload_name,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )
        islam_match = semantic_service_match("ислам", "demo_salon")

    assert response_info.success is True
    assert response_info.bot_response is not None
    response_text = response_info.bot_response.casefold()
    assert "маникюр" in response_text
    assert any(token in response_text for token in ("9:00", "21:00", "ежедневно", "без выходных"))
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response_info.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response_info.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response_info.bot_response

    assert response_name.success is True
    assert response_name.bot_response == "ok"
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response_name.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response_name.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response_name.bot_response
    assert islam_match is None
    mock_reuse.assert_not_called()
    mock_escalate.assert_not_called()


def test_multi_truth_reply_handles_hours_and_price_in_single_segment():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user

        db = Mock()
        db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="зд, вы сегодня работаете, сколько стоит педикюр?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-info-3",
                timestamp=1234567892,
            ),
        ),
    )

    def _fake_question_type(segment: str, *, include_kinds=None, return_multi: bool = False):
        normalized = (segment or "").casefold()
        if "работаете" in normalized and "стоит" in normalized:
            if return_multi:
                return [
                    SimpleNamespace(kind="hours", score=0.82, second_score=0.05),
                    SimpleNamespace(kind="pricing", score=0.79, second_score=0.05),
                ]
            return SimpleNamespace(kind="pricing", score=0.82, second_score=0.05)
        if "работаете" in normalized:
            result = SimpleNamespace(kind="hours", score=0.82, second_score=0.05)
            return [result] if return_multi else result
        if "стоит" in normalized:
            result = SimpleNamespace(kind="pricing", score=0.79, second_score=0.05)
            return [result] if return_multi else result
        return [] if return_multi else None

    semantic_match = SemanticServiceMatch(
        action="match",
        response="Педикюр — 5 000 ₸.",
        score=0.91,
        canonical_name="Педикюр",
        suggestions=["Педикюр"],
    )

    def _fake_semantic_match(text: str, client_slug: str):
        normalized = (text or "").casefold()
        if "педик" in normalized:
            return semantic_match
        return None

    with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint), patch(
        "app.routers.webhook.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.routers.webhook.generate_bot_response",
        return_value=Result.success((None, "low_confidence")),
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook.escalate_to_pending"
    ) as mock_escalate:
        mock_reuse.return_value = (None, False, False)
        mock_escalate.return_value = SimpleNamespace(ok=False, error="test")
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response is not None
    response_text = response.bot_response.casefold()
    assert "педикюр" in response_text
    assert "5 000" in response.bot_response
    assert any(token in response_text for token in ("9:00", "21:00", "ежедневно", "без выходных"))
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response.bot_response
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("intent") == "multi_truth" for entry in trace if isinstance(entry, dict)
    )
    mock_reuse.assert_not_called()
    mock_escalate.assert_not_called()


def test_intent_decomp_blocks_booking_and_drives_multi_truth():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user

        db = Mock()
        db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-info-4",
                timestamp=1234567893,
            ),
        ),
    )

    def _empty_question_type(*args, **kwargs):
        return [] if kwargs.get("return_multi") else None

    semantic_match = SemanticServiceMatch(
        action="match",
        response="Педикюр — 5 000 ₸.",
        score=0.91,
        canonical_name="Педикюр",
        suggestions=["Педикюр"],
    )

    def _fake_semantic_match(text: str, client_slug: str):
        normalized = (text or "").casefold()
        if "педик" in normalized:
            return semantic_match
        return None

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "hours",
        "secondary_intents": ["pricing"],
        "intents": ["hours", "pricing"],
        "service_query": "педикюр",
    }

    with patch("app.routers.webhook.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook.semantic_question_type", side_effect=_empty_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_empty_question_type
    ), patch(
        "app.routers.webhook.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.services.demo_salon_knowledge.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.routers.webhook.generate_bot_response",
        return_value=Result.success(("llm", "high")),
    ), patch(
        "app.routers.webhook.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook.escalate_to_pending"
    ) as mock_escalate:
        mock_reuse.return_value = (None, False, False)
        mock_escalate.return_value = SimpleNamespace(ok=False, error="test")
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response is not None
    response_text = response.bot_response.casefold()
    assert "педикюр" in response_text
    assert "5 000" in response.bot_response
    assert any(token in response_text for token in ("9:00", "21:00", "ежедневно", "без выходных"))
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response.bot_response

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent_decomp_used") is True
    assert "hours" in (meta.get("intents") or [])
    assert "pricing" in (meta.get("intents") or [])
    assert meta.get("service_query") == "педикюр"
    assert meta.get("booking_blocked_reason") == "info_question"

    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "intent_decomposition" for entry in trace if isinstance(entry, dict)
    )
    assert any(entry.get("stage") == "multi_truth" for entry in trace if isinstance(entry, dict))
    mock_reuse.assert_not_called()
    mock_escalate.assert_not_called()


def test_asr_low_confidence_requires_confirmation_then_accepts_yes():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user

        db = Mock()
        db.query.side_effect = [client_query, settings_query, conversation_query, user_query]
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="audio",
            message=None,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-voice-123",
                timestamp=1234567890,
            ),
            mediaData={
                "type": "audio",
                "mimetype": "audio/ogg",
                "ptt": True,
                "size": 100,
                "seconds": 7,
            },
        ),
    )

    asr_meta = {
        "asr_used": True,
        "asr_provider": "elevenlabs",
        "asr_fallback_used": False,
        "asr_failed": False,
        "asr_text_len": 7,
    }

    with patch(
        "app.routers.webhook._maybe_transcribe_voice",
        AsyncMock(return_value=("маникюр", "ok", asr_meta)),
    ), patch(
        "app.routers.webhook._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == webhook_router.MSG_ASR_CONFIRM.format(text="маникюр")
    pending = conversation.context.get("asr_confirm_pending")
    assert pending["transcript"] == "маникюр"
    assert pending["attempt"] == 1

    payload_yes = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="text",
            message="да",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-voice-124",
                timestamp=1234567891,
            ),
        ),
    )

    with patch(
        "app.routers.webhook.generate_bot_response",
        return_value=Result.success(("ok", "high")),
    ) as mock_generate, patch(
        "app.routers.webhook.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._find_message_by_message_id",
        return_value=saved_message,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload_yes,
                make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response.success is True
    assert response.bot_response == "ok"
    assert mock_generate.call_args[0][2] == "маникюр"
    assert "asr_confirm_pending" not in conversation.context


def _load_golden_cases() -> list[dict]:
    path = Path(__file__).resolve().parent / "test_cases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    manual = data.get("manual_tests", {})
    cases = manual.get("test_cases", []) if isinstance(manual, dict) else []
    return [case for case in cases if isinstance(case, dict) and case.get("automation")]


def test_escalation_reuses_active_handover():
    db = Mock()
    conversation = Mock()
    conversation.id = "conv-id"
    conversation.client_id = "client-id"
    conversation.state = ConversationState.BOT_ACTIVE.value
    conversation.escalated_at = None
    user = Mock()
    user.remote_jid = "77000000000@s.whatsapp.net"

    existing = Mock()
    existing.id = "handover-id"
    existing.status = "pending"

    with patch("app.services.escalation_service.get_active_handover", return_value=existing), patch(
        "app.services.escalation_service.create_handover"
    ) as mock_create, patch(
        "app.services.escalation_service.send_telegram_notification", return_value=True
    ) as mock_send:
        handover, sent = escalation_service.escalate_conversation(
            db=db,
            conversation=conversation,
            user=user,
            trigger_type="intent",
            trigger_value="payment",
            user_message="по оплате уточню",
        )

        assert handover == existing
        assert sent is True
        mock_create.assert_not_called()
        mock_send.assert_called_once_with(
            db=db,
            handover=existing,
            conversation=conversation,
            user=user,
            message="по оплате уточню",
        )
        assert conversation.state == ConversationState.PENDING.value


@pytest.mark.parametrize("case", _load_golden_cases())
def test_golden_cases(case):
    automation = case["automation"]
    check = automation.get("check")
    if check == "fast_intent":
        decision = webhook_router._detect_fast_intent(
            case.get("input", ""),
            policy_type=automation.get("policy_type", "demo_salon"),
            booking_wants_flow=automation.get("booking_wants_flow", False),
            bypass_domain_flows=automation.get("bypass_domain_flows", False),
        )
        if automation.get("expect_action") is not None:
            assert decision is not None
            assert decision.action == automation["expect_action"]
        if automation.get("expect_intent") is not None:
            assert decision is not None
            assert decision.intent == automation["expect_intent"]
        if automation.get("expect_match") is False:
            assert decision is None
        return
    if check == "domain_router":
        router_key = automation.get("domain_router")
        if router_key == "demo_salon":
            client_config = {"domain_router": DEMO_DOMAIN_ROUTER_CONFIG}
        else:
            client_config = automation.get("domain_router_config", {})
        domain_intent, in_score, out_score, _ = classify_domain_with_scores(
            case.get("input", ""),
            client_config,
        )
        strong_out, _ = is_strong_out_of_domain(
            case.get("input", ""),
            domain_intent,
            in_score,
            out_score,
            client_config,
        )
        if automation.get("expect_out_of_domain") is not None:
            assert strong_out is automation["expect_out_of_domain"]
        if automation.get("expect_domain_intent") is not None:
            assert domain_intent.value == automation["expect_domain_intent"]
        return
    if check == "decision":
        state = automation.get("state", ConversationState.BOT_ACTIVE.value)
        state_value = state.value if isinstance(state, ConversationState) else state
        policy = webhook_router._get_routing_policy(state_value)
        signals = webhook_router._detect_intent_signals(case.get("input", ""))
        outcome = webhook_router._resolve_action(
            routing=policy,
            state=state_value,
            signals=signals,
            is_pending_status_question=False,
            style_reference=False,
            out_of_domain_signal=False,
            rag_confident=False,
        )
        assert outcome.action == automation["expect_action"]
        return

    if check == "signals":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
            booking_signal = webhook_router._has_booking_signal(
                messages,
                client_slug="demo_salon",
                message_text=messages[-1] if messages else None,
            )
        opt_out = any(is_opt_out_message(msg) for msg in messages)

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if "expect_opt_out" in automation:
            assert opt_out == automation["expect_opt_out"]
        return

    if check == "booking_flow":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
            booking_signal = webhook_router._has_booking_signal(
                messages,
                client_slug="demo_salon",
                message_text=messages[-1] if messages else None,
            )
            booking_state = webhook_router._update_booking_from_messages(
                {},
                messages,
                client_slug="demo_salon",
            )

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if automation.get("expect_service"):
            assert booking_state.get("service")
        if automation.get("expect_datetime"):
            assert booking_state.get("datetime")
        return

    pytest.fail(f"Unknown golden automation check: {check}")
