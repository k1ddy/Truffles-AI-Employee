import asyncio
import json
import os
import re
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.contracts.decision import (
    DecisionOutcome,
    DecisionSignals,
    ExpectedReplyState,
    IntentDecompositionState,
)
from app.database import get_db
from app.main import app
from app.models import Branch, Client, ClientSettings, Conversation, User
from app.routers import webhook as webhook_router
from app.routers.webhook import response as webhook_response
from app.routers.webhook.decision import (
    _classify_policy_core_degrade_reason,
    _policy_core_reason_supports_info_rescue,
    _policy_has_style_reference_hint,
    _validate_policy_check_confirm_contract,
)
from app.routers.webhook.session_memory import _is_session_reset_only_message
from app.schemas.consult import ConsultControllerOutput
from app.schemas.message import MessageRequest, MessageResponse
from app.schemas.webhook import (
    WebhookBody,
    WebhookMetadata,
    WebhookRequest,
    WebhookResponse,
    WebhookTenantContext,
)
from app.services import escalation_service
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    SemanticServiceMatch,
    get_demo_salon_decision,
    semantic_service_match,
)
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    is_opt_out_message,
    is_strong_out_of_domain,
)
from app.services.knowledge_snapshot_consumer import ConsultSnapshotShadowResult
from app.services.knowledge_validation import MinimumDataContractStatus
from app.services.message_service import select_handover_user_message
from app.services.result import Result
from app.services.state_machine import ConversationState
from app.services.tool_registry_service import validate_tool_args_contract

MINIMUM_DATA_READY = MinimumDataContractStatus(ready=True, missing_fields=[])


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fake_intent_decomp():
    def _extract_service_query(normalized: str) -> str:
        patterns = [
            r"(?:сколько стоит|сколько стоят|стоимость|цена|прайс|почем)\s+([^?!.;,]+)",
            r"(?:сколько длится|сколько по времени|по времени|длительность|сколько времени)\s+([^?!.;,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if not candidate:
                continue
            tokens = candidate.split()
            return " ".join(tokens[:6])
        return ""

    def _detect_stub(text: str, **_kwargs):
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
        service_query = _extract_service_query(normalized)
        return {
            "multi_intent": len(intents) > 1,
            "primary_intent": primary,
            "secondary_intents": secondary,
            "intents": intents,
            "service_query": service_query,
            "consult_intent": False,
            "consult_topic": "",
            "consult_question": "",
        }

    with patch("app.routers.webhook._legacy.detect_multi_intent", side_effect=_detect_stub):
        yield


@pytest.fixture(autouse=True)
def _disable_debounce_redis():
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None)
        )
        stack.enter_context(
            patch("app.routers.webhook.dedup._get_debounce_redis", return_value=None)
        )
        yield


@pytest.fixture(autouse=True)
def _disable_quiet_hours_notices():
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.webhook.decision.build_quiet_hours_notice", return_value=None)
        )
        stack.enter_context(
            patch("app.routers.webhook.decision.build_evening_greeting", return_value=None)
        )
        yield


@pytest.fixture(autouse=True)
def _disable_minimum_data_safe_mode():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.routers.webhook.decision._build_minimum_data_contract_status",
                return_value=SimpleNamespace(ready=True, missing_fields=[]),
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_signal_lexicons():
    from app.services import demo_salon_knowledge as knowledge

    original = knowledge.get_signal_lexicon_list

    def _stub(client_slug: str | None, key: str):
        if client_slug == "generic":
            return []
        return original(client_slug, key)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.demo_salon_knowledge.get_signal_lexicon_list",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook.info.get_signal_lexicon_list",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_policy_pack():
    from app.routers.webhook import policy as policy_router

    original = policy_router._load_policy_pack

    def _stub(*, policy_type: str | None, client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(policy_type=policy_type, client_slug=client_slug)

    with patch(
        "app.routers.webhook.policy._load_policy_pack",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_booking_request_lexicon():
    from app.routers.webhook import decision as decision_router

    original = decision_router._collect_booking_request_lexicon

    def _stub(client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(client_slug)

    with patch(
        "app.routers.webhook.decision._collect_booking_request_lexicon",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_service_hint():
    from app.routers.webhook import decision as decision_router

    original = decision_router._extract_service_hint

    def _stub(text: str | None, client_slug: str | None):
        if client_slug == "generic":
            return None
        return original(text, client_slug)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.routers.webhook.decision._extract_service_hint",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook._legacy._extract_service_hint",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_datetime_lexicon():
    from app.routers.webhook import booking as booking_router

    original = booking_router._load_datetime_lexicon

    def _stub(client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(client_slug)

    with patch(
        "app.routers.webhook.booking._load_datetime_lexicon",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_truth_pack():
    from app.services import demo_salon_knowledge as knowledge

    original = knowledge.load_yaml_truth
    generic_truth = {
        "domain_pack": {},
        "services_catalog": {"services": []},
        "client_pack": {"policy": {}},
        "salon": {"timezone": "UTC"},
    }

    def _stub(client_slug: str | None = None):
        if client_slug == "generic":
            return dict(generic_truth)
        return original(client_slug)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.demo_salon_knowledge.load_yaml_truth",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook.decision.load_yaml_truth",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _disable_consult_snapshot():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
                return_value="shadow",
            )
        )
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
                return_value=False,
            )
        )
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
                return_value=False,
            )
        )
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

    def test_message_routes_through_webhook_pipeline(self, client):
        conversation_id = uuid4()
        conversation = SimpleNamespace(id=conversation_id, state=ConversationState.BOT_ACTIVE.value)
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation

        db = Mock()
        db.query.return_value = conversation_query

        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with patch(
                "app.routers.message.get_client_slug", return_value="demo_salon"
            ), patch(
                "app.routers.message.reasoning_core.handle_webhook_payload",
                new_callable=AsyncMock,
            ) as mock_handle:
                mock_handle.return_value = WebhookResponse(
                    success=True,
                    message="ok",
                    conversation_id=conversation_id,
                    bot_response="reply",
                )

                response = client.post(
                    "/message",
                    json={
                        "client_id": str(uuid4()),
                        "remote_jid": "77759841926@s.whatsapp.net",
                        "content": "Привет!",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["bot_response"] == "reply"
                assert data["conversation_id"] == str(conversation_id)
                assert data["state"] == ConversationState.BOT_ACTIVE.value

                payload = mock_handle.call_args.args[0]
                assert payload.client_slug == "demo_salon"
                assert payload.body.message == "Привет!"
                assert payload.body.metadata.remoteJid == "77759841926@s.whatsapp.net"
                assert payload.body.metadata.messageId
                assert isinstance(payload.body.metadata.timestamp, int)
        finally:
            app.dependency_overrides.pop(get_db, None)


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


def test_policy_gate_escalates_without_llm():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="demo_salon", config={})
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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-18 10:00",
                "name": "Лена",
                "last_question": "name",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу оплатить картой",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-law-1",
                timestamp=1234567890,
            ),
        ),
    )

    import app.services.demo_salon_knowledge as demo_salon_knowledge

    truth = demo_salon_knowledge.load_yaml_truth("demo_salon")
    policy = truth.get("policy") or truth.get("client_pack", {}).get("policy") or {}
    expected_reply = policy.get("payment_info", {}).get("response") or "Передам администратору вопрос по оплате."

    decision = DemoSalonDecision(
        action="escalate",
        response=expected_reply,
        intent="payment",
        meta={"policy_gate": "payment_info"},
    )

    def _escalation_gate(_messages, *, client_slug=None):
        return decision

    def _policy_gate_stub(*, saved_message, **_kwargs):
        if saved_message is not None:
            saved_message.message_metadata.setdefault("decision_meta", {}).update(
                {
                    "source": "policy_pack",
                    "policy_gate": "payment_info",
                    "policy_section": "payment_info",
                    "intent": "payment",
                    "action": "escalate",
                }
            )
        return WebhookResponse(
            success=True,
            message="Policy escalation sent",
            conversation_id=conversation_id,
            bot_response=expected_reply,
        )

    policy_handler = {
        "policy_type": "demo_salon",
        "policy_pack": {},
        "escalation_gate": _escalation_gate,
    }

    with patch("app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate", side_effect=_policy_gate_stub
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover", return_value=(None, False, False)
    ), patch(
        "app.routers.webhook._legacy.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace()),
    ), patch(
        "app.routers.webhook._legacy.send_telegram_notification", return_value=True
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert response.bot_response == expected_reply
    mock_llm.assert_not_called()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("source") == "policy_pack"
    assert meta.get("policy_gate") == "payment_info"
    assert meta.get("policy_section") == "payment_info"
    assert meta.get("intent") == "payment"
    assert meta.get("action") == "escalate"


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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
    )
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
            with patch("app.routers.webhook.http.report_integration_incident") as incident_mock:
                response = client.post(
                    "/webhook",
                    json={"client_slug": "test", "body": {"message": "hi"}},
                    headers={"X-Webhook-Secret": "wrong"},
                )
            assert response.status_code == 401
            incident_mock.assert_called_once()
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

    @patch("app.routers.webhook.http.alert_warning")
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


def _build_query_side_effect(
    *,
    client_query=None,
    settings_query=None,
    conversation_query=None,
    user_query=None,
    branch_query=None,
    branch_phone_query=None,
):
    def _default_first(value):
        query = Mock()
        query.filter.return_value.first.return_value = value
        return query

    def _default_all(values):
        query = Mock()
        query.filter.return_value.all.return_value = values
        return query

    client_query = client_query or _default_first(None)
    settings_query = settings_query or _default_first(None)
    conversation_query = conversation_query or _default_first(None)
    user_query = user_query or _default_first(None)
    branch_query = branch_query or _default_first(None)
    branch_phone_query = branch_phone_query or _default_all([])

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    return _query


def _booking_signal_snapshot(messages: list[str], *, client_slug: str = "demo_salon") -> dict:
    message_text = messages[-1] if messages else None
    client_config = {"domain_router": DEMO_DOMAIN_ROUTER_CONFIG}
    booking_block_meta = webhook_router._preflight_booking_block(
        message_text=message_text,
        client_config=client_config,
        booking_active=False,
    )
    if booking_block_meta:
        booking_signal = False
    else:
        booking_signal, booking_block_meta = webhook_router._evaluate_booking_signal(
            messages,
            client_slug=client_slug,
            message_text=message_text,
        )
    booking_snapshot = webhook_router._compact_signal_snapshot(
        {
            "signal": booking_signal,
            "blocked": bool(booking_block_meta),
            "blocked_reason": (
                booking_block_meta.get("booking_blocked_reason")
                if isinstance(booking_block_meta, dict)
                else None
            ),
            "active": False,
            "wants_flow": False,
            "expected_reply_type": None,
            "expected_reply_reason": None,
            "expected_reply_shortcircuit": False,
        }
    )
    saved_message = Mock()
    saved_message.message_metadata = {}
    webhook_router._update_message_signal_snapshot(saved_message, {"booking": booking_snapshot})
    decision_meta = (
        saved_message.message_metadata.get("decision_meta")
        if isinstance(saved_message.message_metadata, dict)
        else None
    )
    signal_snapshot = decision_meta.get("signal_snapshot") if isinstance(decision_meta, dict) else None
    return signal_snapshot.get("booking") if isinstance(signal_snapshot, dict) else {}


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
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            assert snapshot.get("signal") is True

    def test_booking_signal_blocked_for_info_question(self):
        messages = ["Вы сегодня работаете? Сколько стоит педикюр?"]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint), patch(
            "app.routers.webhook._legacy.semantic_question_type",
            return_value=SimpleNamespace(kind="pricing", score=0.72, second_score=0.1),
        ):
            snapshot = _booking_signal_snapshot(messages)
            assert snapshot.get("signal") is False

    def test_booking_updates_across_messages(self):
        booking = {"active": True}
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            updated = webhook_router._update_booking_from_messages(
                booking,
                ["маникюр", "на завтра в 5"],
                client_slug="demo_salon",
            )
        assert updated.get("service") == "маникюр"
        assert updated.get("datetime") == "в 5"


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

    def test_booking_prompt_skips_name_when_refused(self):
        booking = {"service": "маникюр", "datetime": "завтра"}
        refusal_flags = {"name": {"value": True, "source": "explicit_refusal", "last_set_at": "2025-12-29T00:00:00Z"}}
        updated, prompt = webhook_router._next_booking_prompt(booking, refusal_flags=refusal_flags)
        assert isinstance(prompt, str)
        assert "точное время" in prompt.casefold()
        assert updated.get("last_question") == "datetime"

    def test_booking_prompt_accepts_weekday_daypart_as_grounded_datetime(self):
        booking = {"service": "маникюр", "datetime": "в субботу вечером"}
        updated, prompt = webhook_router._next_booking_prompt(booking, client_slug="demo_salon")
        assert updated.get("last_question") == "name"
        assert isinstance(prompt, str)
        assert webhook_router.MSG_BOOKING_ASK_NAME in prompt

    def test_booking_prompt_accepts_daypart_without_exact_clock(self):
        booking = {"service": "маникюр", "datetime": "после обеда"}
        updated, prompt = webhook_router._next_booking_prompt(booking, client_slug="demo_salon")
        assert updated.get("last_question") == "name"
        assert isinstance(prompt, str)
        assert webhook_router.MSG_BOOKING_ASK_NAME in prompt


class TestDatetimeExtraction:
    def test_extract_datetime_keeps_date_and_time(self):
        from app.routers.webhook import decision as decision_router

        value = decision_router._extract_datetime(
            "2026-02-13 11:00",
            client_slug="demo_salon",
            relative_base=datetime.now(timezone.utc),
        )

        assert isinstance(value, str)
        assert "2026-02-13" in value
        assert "11:00" in value

    def test_extract_datetime_rejects_invalid_clock_time(self):
        from app.routers.webhook import decision as decision_router

        value = decision_router._extract_datetime(
            "запишите в 45:38",
            client_slug="demo_salon",
            relative_base=datetime.now(timezone.utc),
        )

        assert value is None

    def test_validate_datetime_slot_parses_booking_hour_phrase(self):
        value = webhook_router._validate_datetime_slot(
            "Я хочу записаться на 3 часа.",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value == "03:00"

    def test_validate_datetime_slot_rejects_duration_question_without_booking_signal(self):
        value = webhook_router._validate_datetime_slot(
            "Сколько длится маникюр на 3 часа?",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value is None


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

    def test_extract_service_hint_returns_none_without_client_slug(self):
        with patch("app.routers.webhook.decision.semantic_service_match") as semantic_match, patch(
            "app.routers.webhook.decision.get_pack_service_hint"
        ) as pack_hint:
            hint = webhook_router._extract_service_hint("хочу маникюр", None)

        assert hint is None
        semantic_match.assert_not_called()
        pack_hint.assert_not_called()


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
        assert policy["allow_booking_flow"] is True
        assert policy["allow_handover_create"] is False
        assert policy["allow_truth_gate_reply"] is True
        assert policy["allow_bot_reply"] is True

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
        assert should_run is True

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

        with patch("app.routers.webhook._legacy.classify_intent", return_value=Intent.QUESTION) as mock_classify:
            signals = webhook_router._detect_intent_signals(message)
        assert signals.intent == Intent.QUESTION
        mock_classify.assert_called_once()

    def test_human_request_overrides_short_question_hint(self):
        signals = webhook_router._detect_intent_signals(
            "позовите менеджера",
            timing_context={"short_intent_hint": Intent.QUESTION.value},
        )

        assert signals.intent == Intent.HUMAN_REQUEST


def test_truth_gate_sets_decision_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
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
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("source") == "truth_gate"
    assert meta.get("fast_intent") is False
    assert meta.get("llm_primary_used") is False
    assert meta.get("llm_used") is False
    assert meta.get("llm_timeout") is False


def test_truth_gate_appends_booking_cta_for_info_reply():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    decision = DemoSalonDecision(action="reply", response="Работаем с 9:00 до 21:00.", intent="hours")

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return decision

    response = webhook_router._handle_truth_gate_fallback(
        db=Mock(),
        conversation=conversation,
        user=user,
        message_text="Когда вы работаете?",
        saved_message=saved_message,
        client_slug="demo_salon",
        routing={"allow_booking_flow": True, "allow_handover_create": False},
        booking_wants_flow=False,
        policy_handler={"policy_type": "demo_salon", "truth_gate": _truth_gate},
        policy_type="demo_salon",
        current_goal=None,
        intent_decomp_used=False,
        intent_decomp_intents=[],
        intent_decomp_payload=None,
        llm_primary_reason="low_confidence",
        message_count=1,
        now=datetime.now(timezone.utc),
        consult_return_pending=False,
        consult_return_prompt=None,
        consult_context=None,
        consult_return_reason=None,
        maybe_apply_fact_guard=lambda **_kwargs: None,
        send_and_save=lambda text: (text, True),
        log_timing=lambda *args, **_kwargs: None,
        record_escalation_metric=lambda *_args, **_kwargs: None,
    )

    assert response is not None
    assert decision.response in (response.bot_response or "")
    assert (response.bot_response or "").endswith(webhook_router.MSG_BOOKING_CTA)


def test_truth_gate_off_topic_handles_simplenamespace_message_metadata():
    saved_message = SimpleNamespace(
        message_metadata={"decision_meta": {"expected_reply_matched": False}}
    )
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE},
    )
    user = SimpleNamespace(id="user-123", context={})

    decision = DemoSalonDecision(
        action="reply",
        response="Извините, это не по теме.",
        intent="off_topic",
    )

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return decision

    response = webhook_router._handle_truth_gate_fallback(
        db=Mock(),
        conversation=conversation,
        user=user,
        message_text="ок",
        saved_message=saved_message,
        client_slug="demo_salon",
        routing={"allow_booking_flow": True, "allow_handover_create": False},
        booking_wants_flow=False,
        policy_handler={"policy_type": "demo_salon", "truth_gate": _truth_gate},
        policy_type="demo_salon",
        current_goal=None,
        intent_decomp_used=False,
        intent_decomp_intents=[],
        intent_decomp_payload=None,
        llm_primary_reason="low_confidence",
        message_count=1,
        now=datetime.now(timezone.utc),
        consult_return_pending=False,
        consult_return_prompt=None,
        consult_context=None,
        consult_return_reason=None,
        maybe_apply_fact_guard=lambda **_kwargs: None,
        send_and_save=lambda text: (text, True),
        log_timing=lambda *args, **_kwargs: None,
        record_escalation_metric=lambda *_args, **_kwargs: None,
    )

    assert response is not None
    assert webhook_router.MSG_EXPECTED_SERVICE_OFF_TOPIC in (response.bot_response or "")
    decision_meta = saved_message.message_metadata.get("decision_meta", {})
    assert decision_meta.get("expected_reply_guard") == "truth_gate_off_topic_override"


def test_strict_ood_sets_out_of_domain_without_in_signals():
    conversation = SimpleNamespace(
        id="conv-ood-1",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.UNKNOWN, 0.0, 0.0, {}),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="какая погода?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is True
    assert "out_of_domain" in (result.class_router_result.get("classes") or [])


def test_strict_ood_skips_out_of_domain_with_in_signals():
    conversation = SimpleNamespace(
        id="conv-ood-2",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.UNKNOWN, 0.0, 0.0, {}),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="когда работаете?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents={"hours"},
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is False


def test_strict_ood_skips_out_of_domain_with_service_request_signal():
    conversation = SimpleNamespace(
        id="conv-ood-3",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(
            DomainIntent.OUT_OF_DOMAIN,
            0.0,
            0.9,
            {"out_hits": 1, "strict_in_hits": 0},
        ),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="Вырыть бассейн в холле",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is False
    assert "explicit_service" in (result.class_router_result.get("in_signals") or [])


def test_signal_snapshot_written_on_class_router():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id="conv-snapshot-1",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.QUESTION,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )
    domain_meta = {
        "in_threshold": 0.6,
        "out_threshold": 0.6,
        "margin": 0.1,
        "in_hits": 2,
        "out_hits": 0,
        "strict_in_hits": 1,
        "anchors_in": 12,
        "anchors_out": 6,
        "strict_in_anchors": 4,
    }
    class_router_result = {
        "out_of_domain_signal": False,
        "in_signals": ["explicit_service"],
        "out_signals": [],
        "classes": ["info_bundle"],
        "intents": ["location"],
        "carryover_intents": [],
        "carryover_class": None,
        "carryover_info_sections": None,
        "router_fallback_reason": None,
        "controller_fallback_reason": None,
        "router": {"eligible": True},
        "controller": {
            "used": True,
            "attempted": True,
            "fallback": False,
            "low_confidence": False,
            "confidence": 0.82,
            "goal": "info",
        },
    }

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.IN_DOMAIN, 0.77, 0.12, domain_meta),
    ), patch(
        "app.routers.webhook._legacy._resolve_class_router_result",
        return_value=class_router_result,
    ), patch(
        "app.routers.webhook.decision._has_explicit_service_signal", return_value=True
    ):
        webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Где вы находитесь?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    assert snapshot.get("domain_router", {}).get("intent") == "in_domain"
    assert snapshot.get("class_router", {}).get("out_of_domain_signal") is False
    assert snapshot.get("intent_signals", {}).get("intent") == "question"


def test_signal_snapshot_records_pack_index_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id="conv-snapshot-pack-index",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.QUESTION,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )
    domain_meta = {
        "in_threshold": 0.6,
        "out_threshold": 0.6,
        "margin": 0.1,
        "in_hits": 1,
        "out_hits": 0,
        "strict_in_hits": 0,
        "anchors_in": 4,
        "anchors_out": 2,
        "strict_in_anchors": 0,
    }
    class_router_result = {
        "out_of_domain_signal": False,
        "in_signals": ["explicit_service"],
        "out_signals": [],
        "classes": ["info_bundle"],
        "intents": ["location"],
        "carryover_intents": [],
        "carryover_class": None,
        "carryover_info_sections": None,
        "router_fallback_reason": None,
        "controller_fallback_reason": None,
        "router": {"eligible": True},
        "controller": {
            "used": True,
            "attempted": True,
            "fallback": False,
            "low_confidence": False,
            "confidence": 0.82,
            "goal": "info",
        },
    }
    client_config = {
        "pack_index": {
            "schema_version": "pack_index.v1",
            "hash": "hash-123",
            "version_id": "version-123",
            "compiled_at": "2026-01-31T00:00:00+00:00",
            "source": "knowledge_publish",
        }
    }

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.IN_DOMAIN, 0.77, 0.12, domain_meta),
    ), patch(
        "app.routers.webhook._legacy._resolve_class_router_result",
        return_value=class_router_result,
    ), patch(
        "app.routers.webhook.decision._has_explicit_service_signal", return_value=True
    ):
        webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Где вы находитесь?",
            client_slug="demo_salon",
            client_config=client_config,
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    pack_index = snapshot.get("pack_index", {})
    assert pack_index.get("hash") == "hash-123"
    assert pack_index.get("version_id") == "version-123"


def test_consult_pack_writes_decision_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    user = SimpleNamespace(id=uuid4(), user_metadata={})
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id=user.id,
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-18 10:00",
                "name": "Лена",
                "last_question": "name",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Посоветуйте уход после окрашивания",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-1",
                timestamp=1234567891,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "окрашивание",
        "consult_intent": True,
        "consult_topic": "hair_aftercolor",
        "consult_question": "уход после окрашивания",
    }
    service_decision = DemoSalonDecision(
        action="reply",
        response="SERVICE MATCH",
        intent="service_match",
        meta={"service_query": "окрашивание"},
    )
    service_matcher = Mock(return_value=service_decision)
    policy_handler = {"policy_type": "demo_salon", "service_matcher": service_matcher}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert response.bot_response is not None
    assert "SERVICE MATCH" in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response.bot_response
    service_matcher.assert_called_once()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_intent") is True
    assert meta.get("consult_topic") == "hair_aftercolor"
    assert meta.get("expected_reply_type") != webhook_router.EXPECTED_REPLY_SERVICE
    assert meta.get("branch_id") is None

    trace = conversation.context.get("decision_trace", [])
    if settings.branch_resolution_mode != "disabled":
        assert any(
            entry.get("stage") in {"branch_selection", "branch_routing"}
            for entry in trace
            if isinstance(entry, dict)
        )
    assert any(
        entry.get("stage") == "consult_flow"
        and entry.get("decision") == "consult_reply"
        and entry.get("reason") in {"service_availability", "consult_pack"}
        for entry in trace
        if isinstance(entry, dict)
    )
    mock_llm.assert_not_called()


def test_signal_snapshot_records_rag_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(id="conv-rag-1", context={})
    timing_context = {
        "rag_scores": {"vector_count": 1, "bm25_count": 0, "vector_score": 0.42},
        "rag_attempted": True,
        "rag_best_score": 0.42,
        "branch_id": "branch-1",
        "knowledge_tag": "tag-1",
    }

    webhook_response._record_rag_meta(
        conversation=conversation,
        saved_message=saved_message,
        timing_context=timing_context,
    )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    rag_snapshot = snapshot.get("rag", {})
    assert rag_snapshot.get("scores", {}).get("vector_count") == 1
    assert rag_snapshot.get("attempted") is True
    assert snapshot.get("knowledge", {}).get("knowledge_tag") == "tag-1"


def test_consult_precedence_over_booking_flow():
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
        context={"booking": {"active": True}},
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Что посоветуете?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-2",
                timestamp=1234567892,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "booking",
        "secondary_intents": ["pricing"],
        "intents": ["booking", "pricing"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "general",
        "consult_question": "что посоветуете",
    }

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.consult_pack_service.load_consult_playbook",
        return_value=(None, "missing"),
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert response.bot_response == (
        f"{webhook_router.MSG_EXPECTED_SERVICE_OFF_TOPIC}\n\n"
        f"{webhook_router.MSG_BOOKING_ASK_SERVICE}"
    )

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_intent") is True
    assert meta.get("expected_reply_type") is None
    mock_llm.assert_not_called()


def test_consult_pack_flow_records_trace_and_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="generic", config={})
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
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        tenant_context=WebhookTenantContext(client_id=client_id, client_slug="generic"),
        body=WebhookBody(
            message="Подскажите, что можно сделать для улучшения ухода?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-pack-1",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "что можно сделать для улучшения ухода",
    }
    topic_candidates = [
        {
            "topic_id": "general_guidance",
            "title": "General guidance",
            "summary": "Safe guidance",
            "score": 0.91,
        }
    ]
    controller_output = ConsultControllerOutput(
        intent="consult",
        topic_id="general_guidance",
        confidence=0.92,
        risk_class="low",
        actions=["answer"],
        slots={"goal": "care"},
        notes="",
    )
    controller_result = Result.success(controller_output)

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=topic_candidates,
    ), patch(
        "app.services.ai_service.generate_consult_controller_output",
        return_value=controller_result,
    ) as mock_controller, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert response.bot_response
    mock_controller.assert_called_once()
    mock_llm.assert_not_called()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_intent") is True
    assert meta.get("consult_topic_id") == "general_guidance"
    assert meta.get("consult_playbook_id") == "general_guidance"
    assert meta.get("consult_source") == "pack"
    assert meta.get("consult_selector") == "controller"
    assert meta.get("consult_confidence") == pytest.approx(0.92)
    assert meta.get("consult_risk_class") == "low"
    assert meta.get("consult_controller_used") is True
    assert meta.get("consult_controller_error") is None

    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "consult_topic_resolver"
        for entry in trace
        if isinstance(entry, dict)
    )
    assert any(
        entry.get("stage") == "consult_controller"
        and entry.get("decision") == "ok"
        and entry.get("topic_id") == "general_guidance"
        for entry in trace
        if isinstance(entry, dict)
    )
    assert any(
        entry.get("stage") == "consult_flow"
        and entry.get("decision") == "consult_reply"
        and entry.get("reason") == "consult_pack"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_consult_snapshot_shadow_disabled():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="generic", config={})
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
        branch_id=uuid4(),
        context={},
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        tenant_context=WebhookTenantContext(client_id=client_id, client_slug="generic"),
        body=WebhookBody(
            message="Подскажите, как ухаживать после процедуры?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-snapshot-disabled",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "как ухаживать после процедуры",
    }
    topic_candidates = [
        {
            "topic_id": "general_guidance",
            "title": "General guidance",
            "summary": "Safe guidance",
            "score": 0.91,
        }
    ]
    controller_output = ConsultControllerOutput(
        intent="consult",
        topic_id="general_guidance",
        confidence=0.92,
        risk_class="low",
        actions=["answer"],
        slots={"goal": "care"},
        notes="",
    )
    controller_result = Result.success(controller_output)

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=topic_candidates,
    ), patch(
        "app.services.ai_service.generate_consult_controller_output",
        return_value=controller_result,
    ) as mock_controller, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm, patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
    ), patch(
        "app.services.knowledge_snapshot_consumer.build_consult_snapshot_shadow"
    ) as mock_snapshot:
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
    mock_controller.assert_called_once()
    mock_llm.assert_not_called()
    mock_snapshot.assert_not_called()

    trace = conversation.context.get("decision_trace", [])
    assert not any(
        entry.get("stage") == "consult_snapshot"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_consult_snapshot_shadow_records_trace_and_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="generic", config={})
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
        branch_id=uuid4(),
        context={},
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        body=WebhookBody(
            message="Подскажите, как ухаживать после процедуры?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-snapshot-enabled",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "как ухаживать после процедуры",
    }
    topic_candidates = [
        {
            "topic_id": "general_guidance",
            "title": "General guidance",
            "summary": "Safe guidance",
            "score": 0.91,
        }
    ]
    controller_output = ConsultControllerOutput(
        intent="consult",
        topic_id="general_guidance",
        confidence=0.92,
        risk_class="low",
        actions=["answer"],
        slots={"goal": "care"},
        notes="",
    )
    controller_result = Result.success(controller_output)
    snapshot_result = ConsultSnapshotShadowResult(
        playbook=None,
        error=None,
        snapshot_id="snap-1",
        version_id="version-1",
        sha256="sha-256",
        playbook_error=None,
        playbook_present=True,
    )

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=topic_candidates,
    ), patch(
        "app.services.ai_service.generate_consult_controller_output",
        return_value=controller_result,
    ) as mock_controller, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm, patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=True,
    ), patch(
        "app.services.knowledge_snapshot_consumer.build_consult_snapshot_shadow",
        return_value=snapshot_result,
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
    mock_controller.assert_called_once()
    mock_llm.assert_not_called()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_snapshot_id") == "snap-1"
    assert meta.get("consult_snapshot_version_id") == "version-1"
    assert meta.get("consult_snapshot_playbook_present") is True

    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "consult_snapshot"
        and entry.get("decision") == "ok"
        and entry.get("version_id") == "version-1"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_consult_snapshot_shadow_records_error():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="generic", config={})
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
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        body=WebhookBody(
            message="Подскажите, как ухаживать после процедуры?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-snapshot-error",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "как ухаживать после процедуры",
    }
    topic_candidates = [
        {
            "topic_id": "general_guidance",
            "title": "General guidance",
            "summary": "Safe guidance",
            "score": 0.91,
        }
    ]
    controller_output = ConsultControllerOutput(
        intent="consult",
        topic_id="general_guidance",
        confidence=0.92,
        risk_class="low",
        actions=["answer"],
        slots={"goal": "care"},
        notes="",
    )
    controller_result = Result.success(controller_output)
    snapshot_result = ConsultSnapshotShadowResult(
        playbook=None,
        error="missing_branch_id",
        snapshot_id=None,
        version_id=None,
        sha256=None,
        playbook_error=None,
        playbook_present=False,
    )

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=topic_candidates,
    ), patch(
        "app.services.ai_service.generate_consult_controller_output",
        return_value=controller_result,
    ) as mock_controller, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm, patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=True,
    ), patch(
        "app.services.knowledge_snapshot_consumer.build_consult_snapshot_shadow",
        return_value=snapshot_result,
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
    mock_controller.assert_called_once()
    mock_llm.assert_not_called()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_snapshot_error") == "missing_branch_id"

    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "consult_snapshot"
        and entry.get("decision") == "error"
        and entry.get("error") == "missing_branch_id"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_consult_snapshot_cutover_fallback_uses_legacy_pack():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="generic", config={})
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
        branch_id=uuid4(),
        context={},
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        body=WebhookBody(
            message="Подскажите, как ухаживать после процедуры?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-snapshot-fallback",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "как ухаживать после процедуры",
    }
    topic_candidates = [
        {
            "topic_id": "general_guidance",
            "title": "General guidance",
            "summary": "Safe guidance",
            "score": 0.91,
        }
    ]
    controller_output = ConsultControllerOutput(
        intent="consult",
        topic_id="general_guidance",
        confidence=0.92,
        risk_class="low",
        actions=["answer"],
        slots={"goal": "care"},
        notes="",
    )
    controller_result = Result.success(controller_output)
    snapshot_result = ConsultSnapshotShadowResult(
        playbook=None,
        error=None,
        snapshot_id="snap-fallback",
        version_id="version-fallback",
        sha256="sha-256",
        playbook_error="consult_playbook_missing",
        playbook_present=False,
    )

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=topic_candidates,
    ), patch(
        "app.services.ai_service.generate_consult_controller_output",
        return_value=controller_result,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm, patch(
        "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
        return_value="fallback",
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
        return_value=True,
    ), patch(
        "app.services.knowledge_snapshot_consumer.build_consult_snapshot",
        return_value=snapshot_result,
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
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
    mock_llm.assert_not_called()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_snapshot_mode") == "fallback"
    assert meta.get("consult_snapshot_source") == "fallback"
    assert meta.get("consult_snapshot_playbook_present") is False
    assert meta.get("consult_source") == "pack"


def test_consult_snapshot_cutover_strict_clarifies():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="generic", config={})
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
        branch_id=uuid4(),
        context={},
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model is Branch:
            query.filter.return_value.first.return_value = None
            return query
        if model is Branch.phone:
            query.filter.return_value.all.return_value = []
            return query
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="generic",
        body=WebhookBody(
            message="Подскажите, как ухаживать после процедуры?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-consult-snapshot-strict",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": True,
        "consult_topic": "",
        "consult_question": "как ухаживать после процедуры",
    }
    snapshot_result = ConsultSnapshotShadowResult(
        playbook=None,
        error="version_not_found",
        snapshot_id=None,
        version_id=None,
        sha256=None,
        playbook_error=None,
        playbook_present=False,
    )

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.services.demo_salon_knowledge.build_consult_reply"
    ) as mock_consult_reply, patch(
        "app.services.ai_service.generate_consult_advice"
    ) as mock_consult_llm, patch(
        "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
        return_value="strict",
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
        return_value=True,
    ), patch(
        "app.services.knowledge_snapshot_consumer.build_consult_snapshot",
        return_value=snapshot_result,
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
    ), patch(
        "app.services.consult_pack_service.load_consult_playbook",
        return_value=(None, "consult_playbook_missing"),
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
    mock_consult_reply.assert_not_called()
    mock_consult_llm.assert_not_called()

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_snapshot_mode") == "strict"
    assert meta.get("consult_snapshot_source") == "missing"
    assert meta.get("clarify_reason") == "snapshot_missing"

    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "consult_snapshot"
        and entry.get("mode") == "strict"
        and entry.get("decision") == "error"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_session_reset_marker_is_stripped():
    text = "начнем сначала [LC:AUTO:CA05:RESET:20260126-123000]"
    assert _is_session_reset_only_message(text) is True


def test_booking_info_interrupt_appends_prompt():
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
        context={"booking": {"active": True, "service": "маникюр"}},
    )
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится по времени? Записаться можно?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-info-1",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "duration",
        "secondary_intents": ["booking"],
        "intents": ["duration", "booking"],
        "service_query": "маникюр",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return DemoSalonDecision(
            action="reply",
            response="Маникюр — 60 минут.",
            intent="service_duration",
            meta={
                "service_query": "маникюр",
                "service_query_source": "intent_decomp",
                "service_query_score": 1.0,
            },
        )

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert "60 минут" in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in response.bot_response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True
    assert "duration" in (meta.get("booking_info_intents") or [])
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "booking_interrupt" for entry in trace if isinstance(entry, dict))
    mock_llm.assert_not_called()


def test_booking_info_interrupt_with_expected_reply_type_keeps_info_reply():
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
        context={
            "booking": {"active": True, "service": "маникюр"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
    )
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Где находится ваш салон?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-info-expected",
                timestamp=1234567894,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "location",
        "secondary_intents": ["booking"],
        "intents": ["location", "booking"],
        "service_query": "маникюр",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return DemoSalonDecision(
            action="reply",
            response="Мы находимся в центре города.",
            intent="location",
            meta={"info_sections": ["address"]},
        )

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    with patch("app.routers.webhook.decision._current_openai_api_key", return_value="test-key"), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
    ) as route_controller_mock, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    response_text = response.bot_response.lower()
    assert any(token in response_text for token in ("находимся", "адрес", "алматы"))
    assert (
        webhook_router.MSG_BOOKING_ASK_DATETIME in response.bot_response
        or webhook_router.MSG_BOOKING_ASK_NAME in response.bot_response
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("action_source") in {"llm_policy_core", "policy_core", "truth_gate"}
    assert meta.get("tool_action") not in {"calendar.list_slots", "calendar.book_slot"}
    assert meta.get("expected_reply_blocked_by_info") is True
    assert meta.get("router_eligible") is True
    assert meta.get("controller_eligible") is True
    assert meta.get("router_skipped_reason") == "none"
    assert meta.get("controller_skipped_reason") == "none"
    assert meta.get("controller_attempted") is True
    trace = conversation.context.get("decision_trace", [])
    assert isinstance(trace, list)
    assert route_controller_mock.called is True
    mock_llm.assert_not_called()


def test_booking_time_service_question_keeps_time_contract():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    context_manager = {
        "clarify_attempts": {
            "booking": {"count": 1, "last_at": "2025-12-01T10:00:00+00:00"},
        },
    }
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
        context={
            "booking": {"active": True, "service": "педикюр"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "context_manager": context_manager,
        },
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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр делаете?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-time-service-1",
                timestamp=1234567894,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return DemoSalonDecision(
            action="reply",
            response="Да, делаем маникюр.",
            intent="service_match",
            meta={
                "service_query": "маникюр",
                "service_query_source": "semantic_match",
                "service_query_score": 0.9,
            },
        )

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert "делаем маникюр" in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    booking_state = conversation.context.get("booking", {})
    assert booking_state.get("service") == "маникюр"
    clarify_state = conversation.context.get("context_manager", {}).get("clarify_attempts", {})
    assert clarify_state.get("booking", {}).get("count") == 1
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "booking_interrupt" for entry in trace if isinstance(entry, dict))
    mock_llm.assert_not_called()


def test_booking_info_interrupt_without_policy_handler_uses_service_hint_for_pricing():
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
        context={
            "booking": {"active": True, "service": "Стрижка"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
    )
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А сколько это стоит?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-price-no-policy",
                timestamp=1234567895,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    response_text = (response.bot_response or "").casefold()
    assert "стриж" in response_text or "₸" in response_text
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in response.bot_response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True
    assert "pricing" in (meta.get("booking_info_intents") or [])
    assert "pricing" in (meta.get("info_sections") or [])
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "booking_interrupt" for entry in trace if isinstance(entry, dict))
    mock_llm.assert_not_called()


def test_booking_info_interrupt_without_policy_handler_falls_back_to_info_clarify():
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
        context={
            "booking": {"active": True, "service": "Маникюр"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
    )
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой у вас самый популярный стиль?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-style-no-policy",
                timestamp=1234567896,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm:
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
    assert webhook_router.MSG_FACT_GUARD_CLARIFY in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True
    assert meta.get("action") == "reply"
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "booking_interrupt" for entry in trace if isinstance(entry, dict))
    mock_llm.assert_not_called()


def test_service_carryover_applies_for_pricing():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    context_manager = {
        "message_count": 4,
        "service_carryover": {
            "service_query": "маникюр",
            "service_query_source": "semantic_match",
            "service_query_score": 0.7,
            "message_count": 4,
            "ttl": 4,
        },
    }
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
        context={"context_manager": context_manager},
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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-carryover-1",
                timestamp=1234567894,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "pricing",
        "secondary_intents": [],
        "intents": ["pricing"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_decision(question: str, *_args, **_kwargs):
        assert "маникюр" in question
        return DemoSalonDecision(
            action="reply",
            response="Маникюр — 3 000 ₸.",
            intent="price_query",
            meta={
                "service_query": "маникюр",
                "service_query_source": "context",
                "service_query_score": 0.7,
            },
        )

    policy_handler = {"policy_type": "demo_salon"}

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.services.demo_salon_knowledge.get_demo_salon_decision",
        side_effect=_truth_decision,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success(("OK", "high")),
    ) as mock_llm:
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("service_query_source") == "context"
    assert meta.get("service_query_ttl") == 4
    assert meta.get("service_query_ttl_remaining") == 4
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "service_carryover" and entry.get("decision") == "used"
        for entry in trace
        if isinstance(entry, dict)
    )


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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=semantic
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value="маникюр"
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
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
    assert response.bot_response == semantic.response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("source") == "service_semantic_matcher"
    assert meta.get("action") == "match"
    assert meta.get("service_semantic_score") == semantic.score


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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=semantic
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value="массаж ног"
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
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
    assert response.bot_response == semantic.response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("source") == "service_semantic_matcher"
    assert meta.get("action") == "suggest"
    assert meta.get("service_semantic_score") == semantic.score


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
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    def _query_side_effect(model, *args, **kwargs):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if getattr(model, "class_", None) is Branch and getattr(model, "key", None) == "phone":
            return branch_phone_query
        fallback = Mock()
        fallback.filter.return_value.first.return_value = None
        fallback.filter.return_value.all.return_value = []
        return fallback

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
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
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    def semantic_side_effect(text: str, client_slug: str):
        if text == "маникюр":
            return semantic
        return None

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.classify_intent", return_value=Intent.QUESTION
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=low_confidence
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", side_effect=semantic_side_effect
    ) as mock_semantic, patch(
        "app.routers.webhook._legacy.rewrite_for_service_match", return_value="маникюр"
    ) as mock_rewrite, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value="маникюр"
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
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
    assert response.bot_response == semantic.response
    assert mock_semantic.call_count == 2
    mock_rewrite.assert_called_once()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("service_semantic_rewrite_used") is True
    assert meta.get("service_semantic_rewrite_query") == "маникюр"


def test_semantic_service_matcher_returns_not_found_on_empty_rag():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})
    timing_context = {
        "rag_attempted": True,
        "rag_scores": {"vector_count": 0, "bm25_count": 0},
        "llm_used": False,
        "llm_timeout": False,
        "llm_cache_hit": False,
    }
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    intent_decomp_payload = {
        "intents": ["other"],
        "service_query": "стрижка",
        "service_query_source": "intent_decomp",
    }

    with patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy.rewrite_for_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
    ), patch(
        "app.routers.webhook._legacy._record_knowledge_backlog"
    ):
        outcome = webhook_response._handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="делаете стрижку?",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-123",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=llm_primary_result,
            append_user_message=False,
            timing_context=timing_context,
            intent_decomp_payload=intent_decomp_payload,
            class_router_result={"in_signals": [], "anchors_in_hits": 0},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=False,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response is not None
    assert "В списке услуг нет такой позиции" in outcome.bot_response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent") == "service_not_found"
    assert meta.get("source") == "service_semantic_matcher"


def test_rag_rewrite_and_scores_logged():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})
    timing_context: dict = {}

    def fake_generate_bot_response(*args, **kwargs):
        timing_context = kwargs.get("timing_context")
        if isinstance(timing_context, dict):
            timing_context["rag_trace"] = [
                {
                    "stage": "rag_retrieve",
                    "phase": "generate",
                    "retry": False,
                    "query": "адрес салона",
                    "results": 1,
                    "rag_scores": {"vector_max": 0.6, "bm25_max": 1.2, "hybrid_max": 0.8},
                }
            ]
            timing_context["rag_scores"] = {"vector_max": 0.6, "bm25_max": 1.2, "hybrid_max": 0.8}
            timing_context["rag_best_score"] = 0.6
            timing_context["rag_attempted"] = True
        return Result.success(("Адрес: Абая 150", "high"))

    intent_decomp_payload = {
        "intents": ["other"],
        "service_query": "",
    }

    with patch(
        "app.services.ai_service.rewrite_query_for_retrieval",
        return_value={"rewrite_used": True, "rewrite_text": "адрес салона", "reason": "rewritten"},
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        side_effect=fake_generate_bot_response,
    ):
        outcome = webhook_response._handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="чо по адресу",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-123",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=None,
            append_user_message=False,
            timing_context=timing_context,
            intent_decomp_payload=intent_decomp_payload,
            class_router_result={"in_signals": [], "anchors_in_hits": 0},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=False,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text, **_kwargs: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response is not None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("rewrite_used") is True
    assert meta.get("rewrite_text") == "адрес салона"
    assert meta.get("rag_scores") == {"vector_max": 0.6, "bm25_max": 1.2, "hybrid_max": 0.8}
    assert meta.get("rag_confident") is True
    assert meta.get("rag_reason") is None
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "rewrite" for entry in trace if isinstance(entry, dict))
    assert any(entry.get("stage") == "rag_retrieve" for entry in trace if isinstance(entry, dict))


def test_record_rag_meta_sets_branch_id():
    conversation = SimpleNamespace(context={})
    saved_message = SimpleNamespace(message_metadata={})
    branch_id = "b7f75692-951e-421a-aae6-f5db97394799"
    timing_context = {
        "rag_scores": {"vector_max": 0.6, "bm25_max": 1.2, "hybrid_max": 0.8},
        "rag_best_score": 0.6,
        "rag_attempted": True,
        "branch_id": branch_id,
    }

    with patch("app.routers.webhook.response._record_llm_budget_trace"), patch(
        "app.routers.webhook.response._record_llm_degradation"
    ), patch("app.routers.webhook.response._record_decision_trace"):
        webhook_response._record_rag_meta(
            conversation=conversation,
            saved_message=saved_message,
            timing_context=timing_context,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("branch_id") == branch_id


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


def test_semantic_service_matcher_returns_suggestions_reply():
    results = [
        {"score": 0.35, "payload": {"canonical_name": "Маникюр"}},
        {"score": 0.32, "payload": {"canonical_name": "Педикюр"}},
    ]
    truth = {
        "services_catalog": {
            "not_found_reply": "В списке услуг нет такой позиции. Возможно, вы имели в виду: {suggestions}.",
        }
    }

    with patch(
        "app.services.demo_salon_knowledge._search_services_index", return_value=results
    ), patch(
        "app.services.demo_salon_knowledge.load_yaml_truth", return_value=truth
    ):
        result = semantic_service_match("маникюр?", "demo_salon")

    assert result is not None
    assert result.action == "suggest"
    assert "Маникюр" in result.response


def test_semantic_question_type_routes_duration_and_price():
    import app.services.demo_salon_knowledge as demo_salon_knowledge

    def fake_embedding(text: str):
        normalized = text.casefold()
        if "дл" in normalized or "врем" in normalized:
            return [1.0, 0.0]
        if "стоит" in normalized or "цена" in normalized or "прайс" in normalized:
            return [0.0, 1.0]
        return [0.1, 0.1]

    def fake_search(text: str, client_slug: str, limit: int):
        normalized = text.casefold()
        if "маник" in normalized:
            return [{"score": 0.9, "payload": {"canonical_name": "Маникюр"}}]
        return []

    with patch("app.services.demo_salon_knowledge.get_embedding", side_effect=fake_embedding), patch(
        "app.services.demo_salon_knowledge._search_services_index", side_effect=fake_search
    ):
        demo_salon_knowledge._question_type_examples.cache_clear()
        demo_salon_knowledge._question_type_embeddings.cache_clear()

        decision = get_demo_salon_decision("Сколько длится процедура?")
        assert decision is not None
        assert decision.intent == "service_duration"
        assert "по времени" in decision.response.casefold() or "какая именно" in decision.response.casefold()

        decision = get_demo_salon_decision("Сколько стоит процедура?")
        assert decision is not None
        assert decision.intent == "service_clarify"

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ) as mock_llm, patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
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


def test_price_clarify_asks_only_service_and_sets_reason():
    import app.services.demo_salon_knowledge as demo_salon_knowledge

    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000001@s.whatsapp.net",
                messageId="msg-price-clarify",
                timestamp=1234567894,
            ),
        ),
    )

    clarify_reply = demo_salon_knowledge.format_reply_from_truth("service_clarify")
    service_decision = DemoSalonDecision(
        action="reply",
        response=clarify_reply or "Уточните, пожалуйста, какая именно услуга интересует?",
        intent="service_clarify",
        meta={"service_query": None, "service_query_source": "none", "service_query_score": 0.0},
    )

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return service_decision

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success(("OK", "high")),
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook.branch_selection._get_active_branches", return_value=[]
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
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
    assert response.bot_response is not None
    response_text = response.bot_response.casefold()
    assert "дат" not in response_text
    assert "врем" not in response_text

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("clarify_reason") == "missing_service_query"


def test_context_manager_sets_refusal_flag_in_decision_meta():
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Не хочу говорить имя",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000002@s.whatsapp.net",
                messageId="msg-refusal",
                timestamp=1234567895,
            ),
        ),
    )

    llm_result = SimpleNamespace(ok=True, value=("Понял вас.", "high"))

    with patch("app.routers.webhook._legacy._get_policy_handler", return_value=None), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=llm_result
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    refusal_flags = meta.get("refusal_flags", {})
    assert refusal_flags.get("name", {}).get("value") is True


def test_clarify_limit_escalates_after_two_attempts():
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
    user = SimpleNamespace(id="user-123", context={})

    service_decision = DemoSalonDecision(
        action="reply",
        response="Уточните, пожалуйста, какая услуга интересует?",
        intent="service_clarify",
        meta={"service_query": None, "service_query_source": "none", "service_query_score": 0.0},
    )

    def _service_matcher(*_args, **_kwargs):
        return service_decision

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return service_decision

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    def _run(message_id: str, timestamp: int):
        saved_message = Mock()
        saved_message.message_metadata = {}

        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user

        db = Mock()
        db.query.side_effect = _build_query_side_effect(
            client_query=client_query,
            settings_query=settings_query,
            conversation_query=conversation_query,
            user_query=user_query,
        )
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()

        payload = WebhookRequest(
            client_slug="demo_salon",
            body=WebhookBody(
                message="Сколько стоит?",
                messageType="text",
                metadata=WebhookMetadata(
                    remoteJid="77000000003@s.whatsapp.net",
                    messageId=message_id,
                    timestamp=timestamp,
                ),
            ),
        )

        with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
            "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
        ), patch(
            "app.routers.webhook._legacy.generate_bot_response",
            return_value=Result.success(("OK", "high")),
        ), patch(
            "app.routers.webhook._legacy.send_bot_response", return_value=True
        ), patch(
            "app.routers.webhook._legacy._reuse_active_handover", return_value=(None, False, False)
        ), patch(
            "app.routers.webhook._legacy.escalate_to_pending", return_value=SimpleNamespace(ok=True, value=SimpleNamespace())
        ), patch(
            "app.routers.webhook._legacy.send_telegram_notification", return_value=True
        ), patch(
            "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
        ), patch(
            "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
        ), patch(
            "app.routers.webhook._legacy.should_process_debounced_message",
            AsyncMock(return_value=True),
        ), patch(
            "app.routers.webhook._legacy.route_dialogue_controller",
            return_value={"ok": False, "error": "skipped"},
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
        return response, saved_message

    _run("msg-clarify-1", 1234567896)
    _run("msg-clarify-2", 1234567897)
    context_manager = conversation.context.get("context_manager", {})
    context_manager = dict(context_manager) if isinstance(context_manager, dict) else {}
    last_attempt_at = datetime.now(timezone.utc).isoformat()
    context_manager["clarify_attempts"] = {
        "pricing": {"count": 2, "last_at": last_attempt_at},
        "info": {"count": 2, "last_at": last_attempt_at},
        "booking": {"count": 2, "last_at": last_attempt_at},
        "consult": {"count": 2, "last_at": last_attempt_at},
    }
    context_manager["current_goal"] = "info"
    conversation.context = {**conversation.context, "context_manager": context_manager}
    response, saved_message = _run("msg-clarify-3", 1234567898)

    assert response.success is True
    assert response.bot_response == webhook_router.MSG_ESCALATED
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("clarify_limit") is True
    attempt = meta.get("clarify_attempt", {})
    assert attempt.get("count") == 2


def test_llm_guard_blocks_payment_response():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(
        id="client-123",
        name="demo_salon",
        config={
            "policy_pack": {
                "guard_topics": {"payment": ["оплат", "карт"]},
            }
        },
    )
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
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

    with patch("app.routers.webhook._legacy._get_policy_handler", return_value=None), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=llm_result
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover", return_value=(None, False, False)
    ), patch(
        "app.routers.webhook._legacy.escalate_to_pending", return_value=SimpleNamespace(ok=True, value=handover)
    ), patch(
        "app.routers.webhook._legacy.send_telegram_notification", return_value=True
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=branch_id
    ), patch(
        "app.routers.webhook.decision._build_minimum_data_contract_status",
        return_value=MINIMUM_DATA_READY,
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
    assert response.bot_response == webhook_router.MSG_ESCALATED
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("source") == "llm_guard"
    assert meta.get("llm_primary_used") is False


def test_hard_law_gate_pre_llm_uses_policy_pack():
    saved_message = Mock()
    saved_message.message_metadata = {}

    policy_pack = {
        "hard_law": {"intents": ["refund"], "risk_level": "high"},
        "refund": {
            "keywords": ["верну", "возврат"],
            "response": "Передам администратору ваш запрос.",
            "risk_level": "high",
            "intent": "refund",
        },
    }
    client = SimpleNamespace(id="client-123", name="demo_salon", config={"policy_pack": policy_pack})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу вернуть деньги.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000001@s.whatsapp.net",
                messageId="msg-hard-law",
                timestamp=1234567891,
            ),
        ),
    )

    with patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        side_effect=AssertionError("detect_multi_intent called"),
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        return_value=(None, False, False),
    ), patch(
        "app.routers.webhook._legacy.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace()),
    ), patch(
        "app.routers.webhook._legacy.send_telegram_notification",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch",
        return_value=None,
    ), patch(
        "app.routers.webhook.branch_selection._get_active_branches",
        return_value=[],
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
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
    assert response.bot_response == policy_pack["refund"]["response"]
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("policy_gate") == "hard_law"
    assert meta.get("risk_level") == "high"
    assert meta.get("source") == "policy_pack"


@pytest.mark.parametrize(
    "message,policy_section,keywords",
    [
        ("похоже грибок на ногте, можно записаться?", "medical", ["грибок"]),
        ("пойду в суд, это незаконно, хочу записаться", "legal", ["суд", "незаконно"]),
    ],
)
def test_hard_law_blocks_booking_signal(message, policy_section, keywords):
    saved_message = Mock()
    saved_message.message_metadata = {}

    policy_pack = {
        "hard_law": {"sections": [policy_section]},
        policy_section: {
            "keywords": keywords,
            "response": "Передал менеджеру.",
            "risk_level": "high",
            "intent": policy_section,
        },
    }
    client = SimpleNamespace(id="client-123", name="demo_salon", config={"policy_pack": policy_pack})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="hybrid",
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
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=message,
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000002@s.whatsapp.net",
                messageId=f"msg-hard-law-{policy_section}",
                timestamp=1234567892,
            ),
        ),
    )

    with patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        side_effect=AssertionError("detect_multi_intent called"),
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        return_value=(None, False, False),
    ), patch(
        "app.routers.webhook._legacy.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace()),
    ), patch(
        "app.routers.webhook._legacy.send_telegram_notification",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch",
        return_value=None,
    ), patch(
        "app.routers.webhook.branch_selection._get_active_branches",
        return_value=[],
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("policy_gate") == "hard_law"
    assert meta.get("policy_section") == policy_section
    assert meta.get("action") == "escalate"
    assert meta.get("source") == "policy_pack"
    assert conversation.context.get("expected_reply_type") is None


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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
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
        "app.routers.webhook.decision._maybe_transcribe_voice",
        AsyncMock(return_value=(None, "empty_transcript", asr_meta)),
    ), patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook.decision._store_media_locally",
        return_value={"stored": False, "path": None, "error": None},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
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


def test_enqueue_only_media_sets_public_url():
    saved_message = Mock()
    saved_message.message_metadata = {"media": {"type": "photo"}}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    user = SimpleNamespace(id=uuid4(), user_metadata={})
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id=user.id,
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

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="image",
            message=None,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-image-123",
                timestamp=1234567890,
            ),
            mediaData={
                "type": "image",
                "mimetype": "image/jpeg",
                "url": "https://app.chatflow.kz/media.jpg",
                "fileName": "photo.jpg",
                "size": 120,
            },
        ),
    )

    storage_path = "/tmp/truffles-media/demo_salon/conv/photo.jpg"
    signed_payload = {
        "public_url": "https://example.com/media.jpg?expires=1700000000&sig=abc",
        "expires_at": "2026-01-01T00:00:00+00:00",
    }

    def _save_message(_db, _conversation_id, _client_id, **kwargs):
        saved_message.message_metadata = kwargs.get("message_metadata")
        saved_message.content = kwargs.get("content")
        saved_message.role = kwargs.get("role")
        return saved_message

    with patch(
        "app.routers.webhook.decision._handle_dedup_gate",
        AsyncMock(return_value=(None, "msg-image-123")),
    ), patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook.decision.get_or_create_user",
        return_value=user,
    ), patch(
        "app.routers.webhook.decision.find_active_conversation_by_channel_ref",
        return_value=conversation,
    ), patch(
        "app.routers.webhook.decision.get_or_create_conversation",
        return_value=conversation,
    ), patch(
        "app.routers.webhook.decision.save_message",
        side_effect=_save_message,
    ), patch(
        "app.routers.webhook.outbox._store_media_locally",
        AsyncMock(
            return_value={
                "stored": True,
                "path": storage_path,
                "size_bytes": 120,
                "sha256": "abc",
            }
        ),
    ), patch(
        "app.routers.webhook.media._build_signed_media_payload",
        return_value=signed_payload,
    ), patch(
        "app.routers.webhook.outbox.enqueue_outbox_message",
        return_value=True,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                enqueue_only=True,
                skip_persist=False,
                conversation_id=None,
            )
        )

    assert response.success is True
    media_meta = saved_message.message_metadata.get("media") or {}
    assert media_meta.get("storage_path") == storage_path
    assert media_meta.get("public_url") == signed_payload["public_url"]
    assert media_meta.get("expires_at") == signed_payload["expires_at"]


def test_manager_active_media_sets_public_url():
    saved_message = Mock()
    saved_message.message_metadata = {"media": {"type": "photo"}}

    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    user = SimpleNamespace(id=uuid4(), user_metadata={})
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id=user.id,
        client_id=client.id,
        state=ConversationState.MANAGER_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            messageType="image",
            message=None,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-image-456",
                timestamp=1234567890,
            ),
            mediaData={
                "type": "image",
                "mimetype": "image/jpeg",
                "url": "https://app.chatflow.kz/media.jpg",
                "fileName": "photo.jpg",
                "size": 120,
            },
        ),
    )

    storage_path = "/tmp/truffles-media/demo_salon/conv/photo.jpg"
    signed_payload = {
        "public_url": "https://example.com/media.jpg?expires=1700000000&sig=abc",
        "expires_at": "2026-01-01T00:00:00+00:00",
    }

    def _save_message(_db, _conversation_id, _client_id, **kwargs):
        saved_message.message_metadata = kwargs.get("message_metadata")
        saved_message.content = kwargs.get("content")
        saved_message.role = kwargs.get("role")
        return saved_message

    with patch(
        "app.routers.webhook.decision._handle_dedup_gate",
        AsyncMock(return_value=(None, "msg-image-456")),
    ), patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook.decision.get_or_create_user",
        return_value=user,
    ), patch(
        "app.routers.webhook.decision.find_active_conversation_by_channel_ref",
        return_value=conversation,
    ), patch(
        "app.routers.webhook.decision.get_or_create_conversation",
        return_value=conversation,
    ), patch(
        "app.routers.webhook.decision.save_message",
        side_effect=_save_message,
    ), patch(
        "app.routers.webhook.decision._store_media_locally",
        AsyncMock(
            return_value={
                "stored": True,
                "path": storage_path,
                "size_bytes": 120,
                "sha256": "abc",
            }
        ),
    ), patch(
        "app.routers.webhook.media._build_signed_media_payload",
        return_value=signed_payload,
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                enqueue_only=False,
                skip_persist=False,
                conversation_id=None,
            )
        )

    assert response.success is True
    media_meta = saved_message.message_metadata.get("media") or {}
    assert media_meta.get("storage_path") == storage_path
    assert media_meta.get("public_url") == signed_payload["public_url"]
    assert media_meta.get("expires_at") == signed_payload["expires_at"]


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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
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
        "app.routers.webhook._legacy.detect_multi_intent",
        return_value=multi_payload,
    ), patch(
        "app.routers.webhook.decision.get_instance_id",
        return_value="instance-123",
    ), patch(
        "app.routers.webhook.decision.ChatFlowAdapter.send_text",
        return_value=SimpleNamespace(is_ok=lambda: True, error=None),
    ), patch(
        "app.routers.webhook.decision.enqueue_outbox_message",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
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
    assert isinstance(response.bot_response, str) and response.bot_response.strip()
    normalized_response = response.bot_response.casefold()
    assert "минут" in normalized_response
    assert (
        "точное время" in normalized_response
        or webhook_router.MSG_BOOKING_ASK_DATETIME.casefold() in normalized_response
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME


def test_intent_queue_sets_context_and_prompt():
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    db.refresh = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр, сколько длится и где вы находитесь?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-queue-1",
                timestamp=1234567893,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "pricing",
        "secondary_intents": ["duration", "location"],
        "intents": ["pricing", "duration", "location"],
        "service_query": "маникюр",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _service_matcher(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return DemoSalonDecision(
            action="reply",
            response="PRICE",
            intent="price_query",
            meta={"service_query": "маникюр"},
        )

    policy_handler = {"policy_type": "demo_salon", "service_matcher": _service_matcher}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert "Что разобрать дальше" in response.bot_response
    assert "по длительности" in response.bot_response
    assert "по адресу" in response.bot_response
    assert conversation.context.get("intent_queue") == ["duration", "location"]
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE


def test_intent_queue_info_limit_skips_booking():
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    db.refresh = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр, сколько длится, где вы и хочу записаться?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-queue-2",
                timestamp=1234567898,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": True,
        "primary_intent": "pricing",
        "secondary_intents": ["duration", "booking"],
        "intents": ["pricing", "duration", "booking"],
        "service_query": "маникюр",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return DemoSalonDecision(
            action="reply",
            response="LOCATION",
            intent="location",
        )

    def _info_decision(question: str, *_args, **_kwargs):
        if "длится" in question:
            return DemoSalonDecision(
                action="reply",
                response="DURATION",
                intent="duration_query",
                meta={"service_query": "маникюр"},
            )
        return DemoSalonDecision(
            action="reply",
            response="PRICE",
            intent="price_query",
            meta={"service_query": "маникюр"},
        )

    policy_handler = {"policy_type": "demo_salon", "truth_gate": _truth_gate}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=policy_handler
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy.get_demo_salon_decision", side_effect=_info_decision
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert "Что разобрать дальше" in response.bot_response
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response.bot_response
    assert conversation.context.get("intent_queue") == ["booking", "location"]
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent_queue") == ["booking", "location"]
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE
    assert meta.get("info_intents_answered") == ["pricing", "duration"]


def test_intent_queue_choice_pricing_replies_and_updates_queue():
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_INTENT_CHOICE,
            "intent_queue": ["pricing", "location"],
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="по цене",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-queue-choice-1",
                timestamp=1234567896,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "маникюр",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _price_decision(question: str, *_args, **_kwargs):
        assert "маникюр" in question
        return DemoSalonDecision(
            action="reply",
            response="PRICE",
            intent="price_query",
            meta={"service_query": "маникюр"},
        )

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy.get_demo_salon_decision", side_effect=_price_decision
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    response_text = response.bot_response.casefold()
    assert "маникюр" in response_text
    assert "Что разобрать дальше" in response.bot_response
    assert "по адресу" in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE
    assert conversation.context.get("intent_queue") == ["location"]
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_matched") is True
    assert meta.get("expected_reply_choice") == "pricing"
    assert meta.get("intent_queue_remaining") == ["location"]
    assert meta.get("expected_reply_next") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE


def test_intent_queue_choice_hours_matches_time_phrase():
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_INTENT_CHOICE,
            "intent_queue": ["hours", "pricing"],
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="по времени",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-queue-choice-hours",
                timestamp=1234567897,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    def _truth_reply(key: str):
        assert key == "hours"
        return "HOURS"

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy.format_reply_from_truth", side_effect=_truth_reply
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    response_text = response.bot_response.casefold()
    assert any(token in response_text for token in ("9:00", "21:00", "ежедневно"))
    assert "Что разобрать дальше" in response.bot_response
    assert "по цене" in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE
    assert conversation.context.get("intent_queue") == ["pricing"]
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_matched") is True
    assert meta.get("expected_reply_choice") == "hours"
    assert meta.get("intent_queue_remaining") == ["pricing"]
    assert meta.get("expected_reply_next") == webhook_router.EXPECTED_REPLY_INTENT_CHOICE


def test_intent_queue_choice_booking_starts_prompt_and_clears_queue(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_INTENT_CHOICE,
            "intent_queue": ["booking", "location"],
            "context_manager": {
                "message_count": 0,
                "service_carryover": {
                    "service_query": "маникюр",
                    "service_query_source": "semantic_match",
                    "service_query_score": 0.72,
                    "message_count": 0,
                    "ttl": 4,
                },
            },
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="по записи",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-queue-choice-booking",
                timestamp=1234567898,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_SERVICE
    assert conversation.context.get("intent_queue") is None
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "booking_prompt"
    assert meta.get("intent") == "booking"
    assert meta.get("expected_reply_matched") is True
    assert meta.get("expected_reply_choice") == "booking"
    assert meta.get("intent_queue_remaining") == []
    assert meta.get("expected_reply_next") == "booking"
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE


def test_expected_reply_type_clears_on_match():
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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-expected-1",
                timestamp=1234567894,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    llm_result = SimpleNamespace(ok=True, value=("OK", "high_confidence"))
    expected_reply_result = {
        "ok": True,
        "payload": {"slot": "service", "value": "маникюр", "confidence": 0.9, "reason": "match"},
        "error": None,
        "raw": None,
    }

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response", return_value=llm_result
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply", return_value=expected_reply_result
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value="маникюр"
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
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert meta.get("expected_reply_matched") is True


def test_expected_reply_type_off_topic_keeps_contract(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
            "intent_queue": ["duration"],
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="проституция",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-expected-ood-1",
                timestamp=1234567895,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    domain_result = (DomainIntent.OUT_OF_DOMAIN, 0.1, 0.9, {"out_hits": 1, "strict_in_hits": 0})
    expected_reply_result = {
        "ok": False,
        "payload": {"slot": "service", "value": "", "confidence": 0.0, "reason": "invalid_choice"},
        "error": "invalid_choice",
        "raw": None,
    }

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(False, None)
    ), patch(
        "app.routers.webhook._legacy._should_run_booking_flow", return_value=False
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply", return_value=expected_reply_result
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
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
    assert webhook_router.MSG_EXPECTED_SERVICE_OFF_TOPIC in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    assert conversation.context.get("intent_queue") == ["duration"]
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    assert meta.get("expected_reply_matched") is False
    assert meta.get("expected_reply_reason") == "off_topic"


def test_expected_reply_contract_bypasses_human_request():
    from app.routers.webhook import decision as decision_router

    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_TIME},
        state=ConversationState.BOT_ACTIVE.value,
    )

    with patch("app.routers.webhook._legacy.interpret_expected_reply") as interpret_expected_reply:
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="позовите менеджера",
            batch_messages=["позовите менеджера"],
            context=conversation.context,
            context_manager={},
            now=datetime.now(timezone.utc),
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    assert interpret_expected_reply.call_count == 0
    assert state.expected_reply_shortcircuit is False
    assert state.expected_reply_type is None
    assert conversation.context.get("expected_reply_type") is None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_bypassed") == "human_request"


def test_should_block_expected_reply_time_for_question_without_datetime():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Можно ли совместить чистку лица и пилинг в один день?",
        client_slug="demo_salon",
    )

    assert blocked is True


def test_should_not_block_expected_reply_time_for_grounded_datetime_reply():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Завтра в 18:00",
        client_slug="demo_salon",
    )

    assert blocked is False


def test_should_not_block_expected_reply_time_for_booking_question_with_datetime():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Можно сегодня записаться прямо сейчас?",
        client_slug="demo_salon",
    )

    assert blocked is False


def test_human_request_bypasses_active_booking_flow_and_escalates(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")

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
        context={
            "booking": {
                "active": True,
                "service": "Чистка лица",
                "datetime": "завтра вечером",
                "last_question": "datetime",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Если нет, передайте администратору, пожалуйста",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-human-request-booking-bypass-1",
                timestamp=1234567907,
            ),
        ),
    )

    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook._legacy._should_run_booking_flow", return_value=True
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover", return_value=(None, False, False)
    ), patch(
        "app.routers.webhook.decision.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace(id="handover-1")),
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification", return_value=True
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
    assert response.bot_response == webhook_router.MSG_ESCALATED
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_bypassed_reason") == "human_request"
    assert meta.get("action") == "escalate"


def test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue():
    from app.routers.webhook import decision as decision_router

    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "intent_queue": ["pricing"],
            "booking": {
                "active": True,
                "service": "Женская стрижка",
                "datetime": "среду",
                "last_question": "datetime",
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    expected_reply_result = {
        "ok": False,
        "payload": {"slot": "datetime", "value": "", "confidence": 0.0, "reason": "deterministic"},
        "error": "deterministic",
        "raw": None,
    }

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "19:00", []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=False,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=expected_reply_result,
    ):
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="19:00",
            batch_messages=["19:00"],
            context=conversation.context,
            context_manager={},
            now=datetime.now(timezone.utc),
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    booking_state = conversation.context.get("booking") or {}
    assert booking_state.get("datetime") == "среду 19:00"
    assert conversation.context.get("expected_reply_type") is None
    assert conversation.context.get("intent_queue") is None
    assert state.expected_reply_type is None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_matched") is True
    assert meta.get("intent_queue_cleared") == "booking_expected_reply"


def test_expected_reply_time_question_like_info_does_not_match_deterministic():
    from app.routers.webhook import decision as decision_router

    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {
                "active": True,
                "service": "чистка лица",
                "last_question": "datetime",
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "в один день", []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=False,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
    ) as interpret_expected_reply:
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Можно ли совместить чистку лица и пилинг в один день?",
            batch_messages=["Можно ли совместить чистку лица и пилинг в один день?"],
            context=conversation.context,
            context_manager={},
            now=datetime.now(timezone.utc),
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    assert interpret_expected_reply.call_count == 0
    assert state.expected_reply_matched is False
    assert state.expected_reply_type == webhook_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_blocked_by_info") is True
    assert meta.get("expected_reply_matched") is False


def test_expected_reply_type_invalid_choice_keeps_contract(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
            "intent_queue": ["location"],
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="проституция",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-expected-invalid-1",
                timestamp=1234567896,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    domain_result = (DomainIntent.UNKNOWN, 0.0, 0.0, {"out_hits": 0, "strict_in_hits": 0})
    expected_reply_result = {
        "ok": False,
        "payload": {"slot": "service", "value": "", "confidence": 0.0, "reason": "invalid_choice"},
        "error": "invalid_choice",
        "raw": None,
    }
    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=webhook_router.EXPECTED_REPLY_SERVICE,
        intent_queue=["location"],
        expected_reply_matched=False,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal=None,
    )
    booking_result = SimpleNamespace(response=None, booking_t0=None, booking_logged=True)

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(False, None)
    ), patch(
        "app.routers.webhook.decision._is_booking_slot_signal", return_value=False
    ), patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook._legacy._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._handle_booking_flow",
        return_value=booking_result,
    ), patch(
        "app.routers.webhook._legacy._handle_booking_flow",
        return_value=booking_result,
    ), patch(
        "app.routers.webhook._legacy._should_run_booking_flow", return_value=False
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply", return_value=expected_reply_result
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
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
    assert webhook_router.MSG_EXPECTED_SERVICE_OFF_TOPIC in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    assert conversation.context.get("intent_queue") == ["location"]
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    assert meta.get("expected_reply_matched") is False
    assert meta.get("expected_reply_reason") == "invalid_choice"


def test_expected_reply_type_invalid_choice_service_request_returns_not_found(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
            "intent_queue": ["location"],
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу вырыть у вас в холле бассейн с лавой.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-expected-invalid-service-request-1",
                timestamp=1234567897,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    domain_result = (DomainIntent.UNKNOWN, 0.0, 0.0, {"out_hits": 0, "strict_in_hits": 0})
    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=webhook_router.EXPECTED_REPLY_SERVICE,
        intent_queue=["location"],
        expected_reply_matched=False,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal=None,
    )
    booking_result = SimpleNamespace(response=None, booking_t0=None, booking_logged=True)

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(False, None)
    ), patch(
        "app.routers.webhook.decision._is_booking_slot_signal", return_value=False
    ), patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook._legacy._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._handle_booking_flow",
        return_value=booking_result,
    ), patch(
        "app.routers.webhook._legacy._handle_booking_flow",
        return_value=booking_result,
    ), patch(
        "app.routers.webhook._legacy._should_run_booking_flow", return_value=False
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
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
    lowered = (response.bot_response or "").lower()
    assert "нет такой позиции" in lowered or "нет такой услуги" in lowered
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    assert meta.get("expected_reply_matched") is False
    assert meta.get("expected_reply_reason") == "invalid_choice"
    assert meta.get("intent") == "service_not_found"


def test_llm_policy_core_collect_sets_expected_reply_type():
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-plan-collect-1",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "pricing",
        "action": "collect",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": ["pricing"],
        "language": "ru",
        "confidence": 0.9,
        "reason": "need_service",
        "goal": "info",
        "slots": {},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.5,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.format_reply_from_truth", return_value="Уточните услугу."
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert response.bot_response == "Уточните услугу."
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("payload", {}).get("tool_action") == "info"
    assert llm_policy_meta.get("payload", {}).get("next_question") == "service"
    assert llm_policy_meta.get("payload", {}).get("open_questions") == ["service"]


def test_llm_policy_core_receives_memory_hints_and_writes_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}

    summary_text = "Услуга: Стрижка; Время: завтра после 15:00; Язык: ru"
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
        context={
            "context_manager": {"compact_summary": {"text": summary_text}},
            "memory_profile": {
                "ttl_days": 30,
                "consent": {"status": "granted", "prompt_count": 1},
                "items": {
                    "preferred_master": {"value": "Алия", "expires_at": "2099-01-01T00:00:00+00:00"},
                    "parking_preference": {
                        "value": "рядом со входом",
                        "expires_at": "2099-01-01T00:00:00+00:00",
                    },
                },
            },
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу к мастеру Алия",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-plan-memory-1",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "pricing",
        "action": "collect",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": ["pricing"],
        "language": "ru",
        "confidence": 0.9,
        "reason": "need_service",
        "goal": "info",
        "slots": {},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.5,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_kwargs = {}

    def _route_policy_core(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return policy_result

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        side_effect=_route_policy_core,
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.format_reply_from_truth", return_value="Уточните услугу."
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert captured_kwargs.get("memory_summary") == summary_text
    assert captured_kwargs.get("memory_profile", {}).get("consent_status") == "granted"
    assert captured_kwargs.get("memory_profile", {}).get("stored_keys") == [
        "parking_preference",
        "preferred_master",
    ]
    assert captured_kwargs.get("memory_profile", {}).get("retrieved_items") == [
        {"key": "preferred_master", "value": "Алия"},
    ]
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("memory_summary_used") is True
    assert llm_policy_meta.get("memory_profile_used") is True
    assert llm_policy_meta.get("memory_profile_keys") == [
        "parking_preference",
        "preferred_master",
    ]
    assert llm_policy_meta.get("memory_profile_retrieved_keys") == ["preferred_master"]
    assert llm_policy_meta.get("memory_profile_retrieved_count") == 1


def test_llm_policy_core_normalizes_action_from_tool_action(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_TIME},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Можно на 17:45?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-normalize-action-1",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "calendar.list_slots",
        "tool_action": "calendar.list_slots",
        "tool_args": {"start_at": "2026-02-14T17:45:00+05:00"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "show_slots",
        "goal": "booking",
        "slots": {"service": "педикюр"},
        "next_question": "",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    tool_result = SimpleNamespace(
        handled=True,
        ok=True,
        response_text="Есть свободные окна: 17:45 и 18:00.",
        error_code=None,
        decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
        trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
    )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action", return_value=tool_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "17:45" in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("action_normalized") is True
    assert meta.get("intent") == "calendar.list_slots"
    assert meta.get("action") == "reply"
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_NAME
    booking_ctx = conversation.context.get("booking", {})
    assert booking_ctx.get("active") is True
    assert (booking_ctx.get("service") or "").casefold() == "педикюр"
    assert booking_ctx.get("datetime") == "2026-02-14T17:45:00+05:00"


def test_llm_policy_core_collect_list_slots_with_known_service_normalizes_to_fact(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу на стрижку завтра в 17:45",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-known-service",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "show_slots",
        "goal": None,
        "slots": {"service": "стрижка", "datetime": "2026-02-14T17:45:00+05:00"},
        "next_question": "",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть свободные окна: 17:45 и 18:15.",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "17:45" in (response.bot_response or "")
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    assert (captured_tool_call.get("tool_args", {}).get("service_query") or "").casefold() == "стрижка"
    start_at = captured_tool_call.get("tool_args", {}).get("start_at")
    assert isinstance(start_at, str) and "45" in start_at
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("tool_action") == "calendar.list_slots"
    assert meta.get("action") == "reply"


def test_llm_policy_core_collect_uses_expected_reply_slot_when_missing(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_TIME},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="да",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-collect-fallback-1",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "continue_booking",
        "goal": "booking",
        "slots": {},
        "next_question": "",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME


def test_llm_policy_core_collect_infers_missing_slot_from_plan_slots(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться на стрижку.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-collect-slot-infer",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "need_datetime",
        "goal": None,
        "slots": {"service": "стрижка"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME


def test_llm_policy_core_info_tool_uses_tool_args_info_refs(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Во сколько вы работаете?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-info-refs",
                timestamp=1234567899,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"info_refs": ["hours"]},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "hours_followup",
        "goal": "info",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook.decision._build_info_intent_reply",
        return_value=("Мы работаем с 09:00 до 21:00.", {"info_sections": ["hours"]}),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert ("9:00" in (response.bot_response or "")) or ("09:00" in (response.bot_response or ""))
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("policy_core_degrade_reason") is None


def test_llm_policy_core_info_style_reference_without_pack_refs_routes_to_portfolio(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_TIME},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я могу прислать фото своей прически?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-style-ref-no-pack-refs",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "style_reference",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "style_reference",
        "goal": "info",
        "slots": {"service": "Стрижка"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Портфолио доступно по ссылке.",
            error_code=None,
            decision_meta={"tool_action": "catalog.portfolio", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "catalog.portfolio"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert captured_tool_call.get("tool_action") == "catalog.portfolio"
    assert webhook_router.MSG_STYLE_REFERENCE_NEED_MEDIA in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("policy_core_degrade_reason") is None


def test_llm_policy_core_info_style_intent_without_pack_refs_routes_to_portfolio(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_TIME},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой у вас самый популярный стиль?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-style-intent-no-pack-refs",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "get_popular_style",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "popular_style_request",
        "goal": "info",
        "slots": {"service": "Маникюр"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Портфолио доступно по ссылке.",
            error_code=None,
            decision_meta={"tool_action": "catalog.portfolio", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "catalog.portfolio"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert captured_tool_call.get("tool_action") == "catalog.portfolio"
    assert webhook_router.MSG_STYLE_REFERENCE_NEED_MEDIA in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("policy_core_degrade_reason") is None


def test_llm_policy_core_info_name_slot_without_pack_refs_normalizes_to_collect(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12 13:00",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Меня зовут Айгуль.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-name-no-pack-refs",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "introduce",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "introduce_name",
        "goal": "booking",
        "slots": {"name": "Айгуль"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-1",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-1",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("policy_core_degrade_reason") is None


def test_llm_policy_core_info_single_info_ref_stays_info_in_booking_context(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Когда лучше всего приезжать?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-single-info-ref-booking-context",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"info_ref": "hours"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "booking_hours_question",
        "goal": "booking",
        "slots": {"service": "Маникюр"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.8, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Мы работаем с 09:00 до 21:00.",
            error_code=None,
            decision_meta={"tool_action": "info", "tool_decision": "ok", "info_sections": ["hours"]},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "info"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert ("9:00" in (response.bot_response or "")) or ("09:00" in (response.bot_response or ""))
    assert "Booking info interrupt" in (response.message or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy_meta = meta.get("llm_policy_core", {})
    assert llm_policy_meta.get("validated") is True
    assert llm_policy_meta.get("validation_error") is None
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("policy_core_degrade_reason") is None


def test_llm_policy_core_allows_plan_with_expected_reply(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-1",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "need_service",
        "goal": "booking",
        "slots": {},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.5,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ) as policy_mock, patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert webhook_router.MSG_BOOKING_ASK_SERVICE in response.bot_response
    assert policy_mock.called is True
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("llm_policy_core", {}).get("validated") is True


def test_llm_policy_core_collect_with_full_slots_normalizes_to_book_slot(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12 13:00",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Лена",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-normalize",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "slot_complete_but_collect",
        "goal": None,
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Лена",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-1",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-1",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == "Запись создана."
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    start_at = captured_tool_call.get("tool_args", {}).get("start_at")
    assert isinstance(start_at, str) and "13:00" in start_at
    assert captured_tool_call.get("tool_args", {}).get("customer_name") == "Лена"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.book_slot"
    assert meta.get("tool_decision") == "ok"
    assert meta.get("appointment_id") == "apt-1"
    assert meta.get("llm_policy_core", {}).get("validated") is True
    plan_audit = meta.get("llm_policy_plan_audit", {})
    assert plan_audit.get("plan_action") == "collect"
    assert plan_audit.get("plan_tool_action") == "collect"
    assert plan_audit.get("final_tool_action") == "calendar.book_slot"
    assert plan_audit.get("override_applied") is True
    assert "contract_validation_failure" in (plan_audit.get("override_reason_codes") or [])


def test_llm_policy_core_list_slots_name_stage_normalizes_to_book_slot(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12 13:00",
                "last_question": "name",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Меня зовут Лена.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-name-stage-normalize",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "name_stage_drift",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Лена",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-name-stage",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-name-stage",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": False,
            "ok": False,
            "specialist_name": None,
            "confidence": None,
            "language": None,
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == "Запись создана."
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    start_at = captured_tool_call.get("tool_args", {}).get("start_at")
    assert isinstance(start_at, str) and "13:00" in start_at
    assert captured_tool_call.get("tool_args", {}).get("customer_name") == "Лена"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "booking_transition_guard"
        and entry.get("decision") == "normalize_list_slots_to_book_slot"
        for entry in trace
        if isinstance(entry, dict)
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.book_slot"
    assert meta.get("tool_decision") == "ok"
    assert meta.get("appointment_id") == "apt-name-stage"
    assert meta.get("llm_policy_core", {}).get("validated") is True
    plan_audit = meta.get("llm_policy_plan_audit", {})
    assert plan_audit.get("plan_tool_action") == "calendar.list_slots"
    assert plan_audit.get("final_tool_action") == "calendar.book_slot"
    assert plan_audit.get("override_applied") is True
    assert "contract_validation_failure" in (plan_audit.get("override_reason_codes") or [])


def test_llm_policy_core_low_confidence_book_slot_with_complete_slots_is_allowed(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12 13:00",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Алия",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-low-confidence",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "start_at": "2026-02-12T13:00:00",
            "customer_name": "Алия",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.0,
        "reason": "low_confidence_complete_slots",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Алия",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-low-confidence",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-low-confidence",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == "Запись создана."
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    start_at = captured_tool_call.get("tool_args", {}).get("start_at")
    assert isinstance(start_at, str) and "13:00" in start_at
    assert captured_tool_call.get("tool_args", {}).get("customer_name") == "Алия"
    assert captured_tool_call.get("tool_args", {}).get("service_query") == "Маникюр"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.book_slot"
    assert meta.get("tool_decision") == "ok"
    assert meta.get("appointment_id") == "apt-low-confidence"
    assert meta.get("llm_policy_core", {}).get("validated") is True
    assert meta.get("llm_policy_core", {}).get("low_confidence_ok") is True


def test_llm_policy_core_book_slot_unknown_tool_arg_rejected(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу записаться на маникюр завтра.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-unknown-arg",
                timestamp=1234567899,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
            "start_at": "2026-02-12T13:00:00",
            "customer_name": "Алия",
            "mystery_field": "unexpected",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Алия",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_FACT_GUARD_CLARIFY
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.book_slot"
    assert meta.get("tool_decision") == "verifier_blocked"
    assert meta.get("tool_args_contract") == "invalid"
    assert meta.get("tool_args_error") == "tool_args_unknown_field"
    assert meta.get("tool_args_error_field") == "mystery_field"
    assert meta.get("tool_verifier") == "pre_execute"
    assert meta.get("router_eligible") is True
    assert meta.get("controller_eligible") is True
    assert meta.get("router_skipped_reason") == "policy_core_tool"
    assert meta.get("controller_skipped_reason") == "policy_core_tool"
    assert meta.get("controller_attempted") is not True


def test_llm_policy_core_book_slot_missing_start_at_blocked_by_policy_verifier(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запиши меня на маникюр, пожалуйста.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-missing-start-at",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
            "customer_name": "Алия",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "name": "Алия",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_DATETIME
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.book_slot"
    assert meta.get("tool_decision") == "verifier_blocked"
    assert meta.get("tool_args_error") == "tool_args_required_missing"
    assert meta.get("tool_args_error_field") == "start_at"
    assert meta.get("tool_verifier_slot") == "datetime"
    assert meta.get("router_eligible") is True
    assert meta.get("controller_eligible") is True
    assert meta.get("router_skipped_reason") == "policy_core_tool"
    assert meta.get("controller_skipped_reason") == "policy_core_tool"
    assert meta.get("controller_attempted") is not True


def test_llm_policy_core_book_slot_backfills_required_args_from_slots_and_specialist_hint(
    monkeypatch,
):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Маникюр"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запишите меня к Айгерим на маникюр 2026-02-18 12:00, имя Лена.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-backfill-specialist",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "booking",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-18 12:00",
            "name": "Лена",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-42",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-42",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "Запись создана" in (response.bot_response or "")
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    tool_args = captured_tool_call.get("tool_args", {})
    assert isinstance(tool_args.get("start_at"), str) and "12:00" in tool_args.get("start_at")
    assert tool_args.get("customer_name") == "Лена"
    assert tool_args.get("specialist_name") == "Айгерим"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_decision") == "ok"
    assert meta.get("appointment_id") == "apt-42"
    assert meta.get("tool_args_error") is None
    assert meta.get("specialist_hint_ok") is True
    assert meta.get("specialist_hint_confidence") == 0.92


def test_llm_policy_core_list_slots_backfills_specialist_from_message_hint(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие есть слоты к Айгерим завтра?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-specialist-hint",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "check_availability",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "list_slots",
        "goal": "booking",
        "slots": {"service": "Маникюр", "datetime": "завтра"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Свободные слоты: Айгерим 10:00.",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.9,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    assert captured_tool_call.get("tool_args", {}).get("specialist_name") == "Айгерим"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("specialist_hint_ok") is True


def test_llm_policy_core_list_slots_converts_non_uuid_specialist_id_to_name(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Есть ли слоты на маникюр у Айгерим завтра?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-specialist-id-as-name",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "check_availability",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {
            "service_query": "Маникюр",
            "specialist_id": "Айгерим",
            "start_at": "2026-02-18T00:00:00Z",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "list_slots",
        "goal": "booking",
        "slots": {"service": "Маникюр", "datetime": "2026-02-18", "name": "Айгерим"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Свободные слоты: Айгерим 10:00.",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={"attempted": False, "ok": False, "specialist_name": None, "confidence": 0.0, "error": None},
    ) as specialist_hint_mock, patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    tool_args = captured_tool_call.get("tool_args", {})
    assert tool_args.get("specialist_name") == "Айгерим"
    assert "specialist_id" not in tool_args
    assert specialist_hint_mock.call_count == 0


def test_llm_policy_core_list_slots_uses_turn_datetime_hint_when_slots_datetime_missing(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Покажи свободные слоты у Айгерим завтра",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-turn-datetime-hint",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "check_availability",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {
            "service_query": "Маникюр",
            "specialist_name": "Айгерим",
            "date": "2023-10-04",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "list_slots",
        "goal": "booking",
        "slots": {"service": "Маникюр", "datetime": "", "name": "Айгерим"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Свободные слоты: Айгерим 10:00.",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._extract_datetime",
        return_value="завтра в 10:00",
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    tool_args = captured_tool_call.get("tool_args", {})
    assert tool_args.get("start_at") == "завтра в 10:00"
    assert "date" not in tool_args


def test_llm_policy_core_book_slot_uses_service_query_hint_when_missing(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запиши меня завтра в 15:00 к Айгерим на маникюр",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-service-hint",
                timestamp=1234567906,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "booking",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "specialist_id": "Айгерим",
            "start_at": "2023-10-04T15:00:00",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.92,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {"service": "", "datetime": "завтра в 15:00", "name": "Айгерим"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-103",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-103",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": False,
            "ok": False,
            "specialist_name": None,
            "confidence": 0.0,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.routers.webhook.decision.extract_customer_name_hint_llm",
        return_value={
            "attempted": False,
            "ok": False,
            "customer_name": None,
            "confidence": 0.0,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.routers.webhook.decision.extract_service_query_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "service_query": "Маникюр",
            "confidence": 0.93,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    tool_args = captured_tool_call.get("tool_args", {})
    assert tool_args.get("service_query") == "Маникюр"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("service_query_hint_ok") is True
    assert meta.get("service_query_hint_confidence") == 0.93


def test_llm_policy_core_booking_skips_intent_decomp_when_budget_reserved(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Маникюр"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запишите меня к Айгерим на маникюр 2026-02-18 10:00, имя Лена.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-booking-budget-reserve",
                timestamp=1234567904,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "booking",
        "tool_action": "calendar.book_slot",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {"service": "Маникюр", "datetime": "2026-02-18 10:00", "name": "Айгерим"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-101",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-101",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_MS",
        20000.0,
    ), patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        side_effect=AssertionError("detect_multi_intent should be skipped on reserved booking budget"),
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.routers.webhook.decision.extract_customer_name_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "customer_name": "Лена",
            "confidence": 0.95,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent_decomp_skipped_reason") == "booking_critical_path_budget_reserved"
    assert meta.get("intent_decomp_budget_required_ms") == 20000.0


def test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist(
    monkeypatch,
):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Маникюр"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запишите меня к Айгерим на маникюр 2026-02-18 10:00, имя Лена.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-customer-name-hint",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "booking",
        "tool_action": "calendar.book_slot",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-18 10:00",
            "name": "Айгерим",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-99",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-99",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.9,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.routers.webhook.decision.extract_customer_name_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "customer_name": "Лена",
            "confidence": 0.95,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    tool_args = captured_tool_call.get("tool_args", {})
    assert isinstance(tool_args.get("start_at"), str) and "10:00" in tool_args.get("start_at")
    assert tool_args.get("specialist_name") == "Айгерим"
    assert tool_args.get("customer_name") == "Лена"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("customer_name_hint_ok") is True
    assert meta.get("customer_name_hint_confidence") == 0.95


def test_llm_policy_core_book_slot_rebases_stale_start_at_to_current_slot(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Маникюр"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запишите меня к Айгерим на маникюр в 12:00, имя Лена.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-rebase-start-at",
                timestamp=1234567905,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "booking",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
            "start_at": "2023-10-04T12:00:00",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "12:00",
            "name": "Айгерим",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 8.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-102",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-102",
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.9,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.routers.webhook.decision.extract_customer_name_hint_llm",
        return_value={
            "attempted": True,
            "ok": True,
            "customer_name": "Лена",
            "confidence": 0.95,
            "language": "ru",
            "error": None,
        },
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    tool_args = captured_tool_call.get("tool_args", {})
    assert tool_args.get("start_at") == "12:00"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_start_at_rebased") is True


def test_llm_policy_core_reschedule_missing_reference_prompts_booking_reference(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Маникюр"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Перенеси запись на завтра в 11:00.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-reschedule-missing-reference",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.reschedule",
        "tool_args": {
            "start_at": "2026-02-12T11:00:00",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "reschedule_time",
        "goal": "booking",
        "slots": {
            "datetime": "2026-02-12 11:00",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    execute_tool_action_mock = Mock()

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._handle_hard_law_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        execute_tool_action_mock,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_REFERENCE
    assert response.bot_response != webhook_router.MSG_FACT_GUARD_CLARIFY
    assert execute_tool_action_mock.called is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.reschedule"
    assert meta.get("tool_decision") == "verifier_blocked"
    assert meta.get("tool_args_error") == "tool_args_required_missing"
    assert meta.get("tool_args_error_field") == "appointment_id"
    assert meta.get("tool_verifier_slot") == "booking_reference"
    assert meta.get("action") == "check_booking_prompt"
    assert meta.get("intent") == "check_booking"


def test_llm_policy_core_get_booking_invalid_reference_maps_to_booking_reference_slot():
    verifier_error, verifier_error_field = webhook_router._verify_policy_tool_args_contract(
        tool_action="calendar.get_booking",
        tool_args={"appointment_id": "not-a-uuid"},
        validate_tool_args_contract=validate_tool_args_contract,
    )

    assert verifier_error == "appointment_id_invalid"
    assert verifier_error_field == "appointment_id"
    assert (
        webhook_router.TOOL_VERIFIER_SLOT_BY_FIELD.get(verifier_error_field) == "booking_reference"
    )


def test_llm_policy_core_reschedule_uses_booking_context_appointment_id(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    saved_message = Mock()
    saved_message.message_metadata = {}
    appointment_id = "3b9cce70-0ee4-4cd2-951b-a7ba6eb5a6e6"

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
        context={
            "booking": {
                "active": True,
                "appointment_id": appointment_id,
                "service": "Маникюр",
                "datetime": "2026-02-12 10:00",
            }
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Перенеси на завтра в 12:00.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-reschedule-reference-from-context",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.reschedule",
        "tool_args": {
            "start_at": "2026-02-13T12:00:00",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "reschedule_time",
        "goal": "booking",
        "slots": {"datetime": "2026-02-13 12:00"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Перенос оформлен. Менеджер подтвердит новое время.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.reschedule",
                "tool_decision": "ok",
                "appointment_id": appointment_id,
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.reschedule",
                "appointment_id": appointment_id,
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._handle_hard_law_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate", return_value=None
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == "Перенос оформлен. Менеджер подтвердит новое время."
    assert captured_tool_call.get("tool_action") == "calendar.reschedule"
    assert captured_tool_call.get("tool_args", {}).get("appointment_id") == appointment_id
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.reschedule"
    assert meta.get("tool_decision") == "ok"
    assert meta.get("appointment_id") == appointment_id
    booking_context = (conversation.context or {}).get("booking", {})
    assert booking_context.get("appointment_id") == appointment_id


def test_llm_policy_core_book_slot_contract_invalid_does_not_auto_escalate(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу записаться на маникюр завтра.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-book-slot-contract-invalid",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
            "start_at": "2026-02-12T13:00:00",
            "customer_name": "Алия",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Алия",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    handover = SimpleNamespace(id=uuid4(), status="pending")
    escalate_result = SimpleNamespace(ok=True, value=handover, error=None)

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending", return_value=escalate_result
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification", return_value=True
    ) as telegram_mock:
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
    assert "Не удалось подтвердить действие автоматически" in (response.bot_response or "")
    assert reuse_handover_mock.called is False
    assert escalate_mock.called is False
    assert telegram_mock.called is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_decision") == "contract_invalid"
    assert meta.get("tool_contract") == "post_condition"
    assert meta.get("tool_contract_error") == "appointment_id_missing"
    assert meta.get("tool_verifier_post") == "invalid"
    assert meta.get("tool_verifier_guard") == "post_condition"
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "calendar.book_slot"
    assert meta.get("source") == "tool_registry"


def test_llm_policy_core_tool_decision_mismatch_does_not_auto_escalate(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запиши меня на маникюр завтра.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-tool-decision-mismatch",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {
            "service_query": "Маникюр",
            "start_at": "2026-02-12T13:00:00",
            "customer_name": "Алия",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "book_slot",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-12 13:00",
            "name": "Алия",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    handover = SimpleNamespace(id=uuid4(), status="pending")
    escalate_result = SimpleNamespace(ok=True, value=handover, error=None)

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="Не удалось создать запись.",
            error_code="slot_unavailable",
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-123",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending", return_value=escalate_result
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification", return_value=True
    ) as telegram_mock:
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
    assert "Не удалось подтвердить действие автоматически" in (response.bot_response or "")
    assert reuse_handover_mock.called is False
    assert escalate_mock.called is False
    assert telegram_mock.called is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_decision") == "contract_invalid"
    assert meta.get("tool_contract") == "post_condition"
    assert meta.get("tool_contract_error") == "tool_decision_mismatch"
    assert meta.get("tool_verifier_post") == "invalid"
    assert meta.get("tool_verifier_guard") == "post_condition"
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "calendar.book_slot"
    assert meta.get("source") == "tool_registry"


def test_llm_policy_core_catalog_tool_decision_mismatch_escalates(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-catalog-tool-decision-mismatch",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "pricing",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {
            "service_query": "Маникюр",
        },
        "pack_refs": ["pricing"],
        "language": "ru",
        "confidence": 0.9,
        "reason": "service_query",
        "goal": "info",
        "slots": {
            "service": "Маникюр",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    handover = SimpleNamespace(id=uuid4(), status="pending")
    escalate_result = SimpleNamespace(ok=True, value=handover, error=None)

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="Уточните услугу.",
            error_code="service_not_found",
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "ok",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending", return_value=escalate_result
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification", return_value=True
    ) as telegram_mock:
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
    assert isinstance(response.bot_response, str)
    assert "Не удалось подтвердить действие автоматически" in response.bot_response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_decision") == "contract_invalid"
    assert meta.get("tool_contract") == "post_condition"
    assert meta.get("tool_contract_error") == "tool_decision_mismatch"
    assert meta.get("tool_verifier_post") == "invalid"
    assert meta.get("tool_verifier_guard") == "post_condition"
    assert meta.get("action") in {"reply", "escalate"}
    assert meta.get("source") == "tool_registry"


def test_llm_policy_core_low_confidence_handoff_is_allowed_for_human_request(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Вы можете передать меня менеджеру?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-handoff-low-confidence",
                timestamp=1234567899,
            ),
        ),
    )

    policy_payload = {
        "intent": "other",
        "action": "handoff",
        "tool_action": "handoff",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.0,
        "reason": "user_requested_manager",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": True,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, True, True),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_ESCALATED
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "escalate"
    assert meta.get("intent") == "llm_policy_core"
    assert meta.get("llm_policy_core", {}).get("validated") is True
    assert meta.get("llm_policy_core", {}).get("low_confidence_ok") is True


def test_llm_policy_core_tool_response_includes_style_reference_prompt(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Вот фото референса",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-style-reference-tool-response",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "booking_followup",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 14.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    def _fake_execute_tool_action(*_args, **_kwargs):
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="На какую дату и время вам удобно?",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "фото/референс" in (response.bot_response or "").lower()
    assert "дату и время" in (response.bot_response or "").lower()


def test_llm_policy_core_degraded_collect_keeps_style_reference_prompt(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
            "booking": {"active": True},
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я могу прислать фото своей прически?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-style-degraded-collect",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "other",
        "action": "handoff",
        "tool_action": "handoff",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.0,
        "reason": "style_reference_text",
        "goal": "other",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": True,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "фото/референс" in (response.bot_response or "").lower()
    assert "какую услугу хотите записаться" in (response.bot_response or "").lower()


def test_llm_policy_core_info_lateness_signal_uses_lateness_reply(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А если я опоздаю, вы меня примете?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-lateness-info",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": ["hours"],
        "language": "ru",
        "confidence": 0.9,
        "reason": "hours_info",
        "goal": "info",
        "slots": {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 13.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "опоздан" in (response.bot_response or "").lower()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent") == "lateness_ok"
    assert meta.get("booking_info_interrupt") is True


def test_llm_policy_core_list_slots_drops_hallucinated_date_without_datetime_signal(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-13 11:00",
                "last_question": "name",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подскажите, пожалуйста.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-date-guard",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"date": "2023-10-03"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "ask_name",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "2026-02-13 11:00",
            "name": "",
        },
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Как вас зовут?",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "ok",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.list_slots",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    tool_args = captured_tool_call.get("tool_args", {})
    assert "date" not in tool_args
    assert "start_at" not in tool_args
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("llm_policy_core", {}).get("validated") is True


def test_llm_policy_core_list_slots_keeps_context_datetime_when_expected_time(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "завтра",
                "last_question": "datetime",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Меня зовут Айгуль.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-keep-context-datetime",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"date": "2023-10-03"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "collect_time",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "завтра",
            "name": "",
        },
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Свободные слоты: Айгерим 10:00, 11:00",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "ok",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.list_slots",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "Свободные слоты" in (response.bot_response or "")
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    tool_args = captured_tool_call.get("tool_args", {})
    assert "date" not in tool_args
    assert tool_args.get("start_at") == "завтра"


def test_llm_policy_core_list_slots_keeps_context_datetime_when_expected_service_choice(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "service",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_INTENT_CHOICE,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А в какое время?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-list-slots-keep-context-datetime-service-choice",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"start_at": "2023-10-05T00:00:00Z"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "collect_time",
        "goal": "booking",
        "slots": {
            "service": "Маникюр",
            "datetime": "сегодня",
            "name": "",
        },
        "next_question": "name",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=False,
            response_text="На какую дату и время вам удобно?",
            error_code="missing_slot",
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "missing_slot",
                "missing_slot": "datetime",
            },
            trace={
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
                "missing_slot": "datetime",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    tool_args = captured_tool_call.get("tool_args", {})
    assert "date" not in tool_args
    assert tool_args.get("start_at") == "сегодня"


def test_llm_policy_core_catalog_service_reply_normalized_to_booking_prompt(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {"active": True},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-catalog-override",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "service_match",
        "goal": "booking",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр классический - 2 500 тг",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "service_not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "service_not_found",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_DATETIME
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "booking_prompt"
    assert meta.get("intent") == "booking"
    assert meta.get("tool_contract_error") != "tool_decision_mismatch"


def test_llm_policy_core_catalog_service_reply_normalized_to_booking_prompt_without_existing_booking_context(
    monkeypatch,
):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Мне нужно сделать маникюр.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-catalog-override-no-booking",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "service_match",
        "goal": "booking",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр классический - 2 500 тг",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "service_not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "service_not_found",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_DATETIME
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "booking_prompt"
    assert meta.get("intent") == "booking"


def test_llm_policy_core_catalog_service_reply_keeps_info_answer_for_info_query(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {"active": True},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-catalog-info-query",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "service_match",
        "goal": "booking",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр классический - 2 500 тг",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "truth_fallback",
                "info_sections": ["pricing"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "Маникюр классический - 2 500 тг" in (response.bot_response or "")
    assert (response.bot_response or "").startswith("Маникюр классический - 2 500 тг")
    assert response.bot_response != webhook_router.MSG_BOOKING_ASK_DATETIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "catalog.service_query"
    assert meta.get("tool_contract_error") != "tool_decision_mismatch"


def test_llm_policy_core_catalog_service_info_followup_uses_time_after_fact_answer(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {"active": True, "service": "Маникюр"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А сколько стоит укладка?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-catalog-info-followup-time",
                timestamp=1234567899,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {},
        "pack_refs": ["pricing"],
        "language": "ru",
        "confidence": 0.9,
        "reason": "pricing_query",
        "goal": "booking",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр классический - 2 500 тг",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "truth_fallback",
                "info_sections": ["pricing"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    bot_response = response.bot_response or ""
    assert bot_response.startswith("Маникюр классический - 2 500 тг")
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in bot_response
    if webhook_router.MSG_BOOKING_ASK_DATETIME in bot_response:
        assert bot_response.find("Маникюр классический - 2 500 тг") < bot_response.find(
            webhook_router.MSG_BOOKING_ASK_DATETIME
        )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "catalog.service_query"


def test_llm_policy_core_tool_branch_persists_booking_slots_before_expected_reply(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-tool-context-persist",
                timestamp=1234567897,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "collect_datetime",
        "goal": "booking",
        "slots": {"service": "Маникюр"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 15.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="На какую дату и время вам удобно?",
            error_code="missing_slot",
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "missing_slot",
                "missing_slot": "datetime",
            },
            trace={
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
                "missing_slot": "datetime",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response == "На какую дату и время вам удобно?"
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.list_slots"
    assert meta.get("tool_decision") == "missing_slot"


def test_llm_policy_core_provider_unavailable_escalates_after_clarify_limit(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {"active": True, "service": "Маникюр"},
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Тогда можно завтра в 13:00",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-provider-unavailable-clarify-limit",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.book_slot",
        "tool_args": {"service_query": "маникюр", "start_at": "2026-02-12T13:00:00"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "booking_confirm_attempt",
        "goal": "booking",
        "slots": {"service": "Маникюр", "datetime": "2026-02-12 13:00"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    escalated_response = WebhookResponse(
        success=True,
        message="clarify-limit-escalated",
        conversation_id=conversation_id,
        bot_response="Передаю менеджеру, чтобы подтвердить запись вручную.",
    )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="Сейчас календарь недоступен. Напишите удобное время, и мы уточним.",
            error_code="provider_unavailable",
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "provider_unavailable",
                "provider_reason": "credentials_missing",
            },
            trace={
                "stage": "tool_registry",
                "decision": "provider_unavailable",
                "tool_action": "calendar.book_slot",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._should_escalate_for_clarify", return_value=True
    ), patch(
        "app.routers.webhook.decision._get_clarify_attempt_state", return_value=(3, None)
    ), patch(
        "app.routers.webhook.decision._register_clarify_attempt"
    ) as register_attempt_mock, patch(
        "app.routers.webhook.decision._handle_clarify_limit_escalation",
        return_value=escalated_response,
    ) as escalate_mock:
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
    assert response.message == "clarify-limit-escalated"
    assert "менеджеру" in (response.bot_response or "").casefold()
    assert escalate_mock.called
    assert register_attempt_mock.called is False


def test_llm_policy_core_list_slots_provider_unavailable_keeps_booking_question(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Мне нужно сделать маникюр.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-provider-unavailable-followup",
                timestamp=1234567904,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "collect_datetime",
        "goal": "booking",
        "slots": {"service": "Маникюр"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 14.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision._evaluate_booking_signal", return_value=(True, None)
    ), patch(
        "app.routers.webhook.decision._preflight_booking_block", return_value=None
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="Сейчас календарь недоступен. Напишите удобное время, и мы уточним.",
            error_code="provider_unavailable",
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "provider_unavailable",
            },
            trace={
                "stage": "tool_registry",
                "decision": "provider_unavailable",
                "tool_action": "calendar.list_slots",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "На какую дату и время вам удобно?" in (response.bot_response or "")
    assert "Сейчас календарь недоступен" in (response.bot_response or "")
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.list_slots"
    assert meta.get("tool_decision") == "provider_unavailable"


def test_booking_verification_reuses_active_handover_before_truth_gate(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Все еще жду подтверждения, позовите менеджера.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-verification-reuse-handover",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "other",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": ""},
        "pack_refs": [],
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": "",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": "ru",
        "confidence": 0.0,
        "reason": "waiting_confirmation",
        "goal": "other",
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    active_handover = SimpleNamespace(id="handover-1", status="pending")

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision.get_active_handover", return_value=active_handover
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(active_handover, True, True),
    ) as reuse_handover_mock:
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
    assert reuse_handover_mock.called
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "escalate"
    assert meta.get("intent") == "check_booking"
    assert meta.get("source") == "booking_verification"


def test_booking_verification_creates_handover_when_none_active(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Все еще жду ответа, соедините с менеджером.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-verification-create-handover",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "other",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": ""},
        "pack_refs": [],
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": "",
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": "ru",
        "confidence": 0.0,
        "reason": "waiting_reply",
        "goal": "other",
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    handover = SimpleNamespace(id=uuid4(), status="pending")
    escalate_result = SimpleNamespace(ok=True, value=handover, error=None)

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending", return_value=escalate_result
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification", return_value=True
    ) as telegram_mock:
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
    assert reuse_handover_mock.called
    assert escalate_mock.called
    assert telegram_mock.called
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "escalate"
    assert meta.get("intent") == "check_booking"
    assert meta.get("source") == "booking_verification"


def test_booking_verification_request_does_not_escalate_active_booking_without_reference(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Стрижка",
                "datetime": "",
                "name": "",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хотел бы изменить свою запись.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-verification-no-reference",
                timestamp=1234567910,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service_query": "Стрижка"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "collect_datetime",
        "goal": "booking",
        "slots": {"service": "Стрижка"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="На какую дату и время вам удобно?",
            error_code="missing_date",
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "missing_slot",
                "missing_slot": "datetime",
            },
            trace={
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
                "missing_slot": "datetime",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision.get_active_handover", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending"
    ) as escalate_mock:
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
    assert response.bot_response != webhook_router.MSG_ESCALATED
    assert "На какую дату и время вам удобно?" in (response.bot_response or "")
    assert reuse_handover_mock.called is False
    assert escalate_mock.called is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.list_slots"
    assert meta.get("tool_decision") == "missing_slot"


def test_llm_policy_core_get_booking_ok_does_not_force_handoff(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-18 10:00",
                "name": "Лена",
                "appointment_id": "cb99d242-69ce-4154-b428-797f6e76c0cb",
            }
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подтвердите, пожалуйста, что запись успешна.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-get-booking-ok-no-handoff",
                timestamp=1234567912,
            ),
        ),
    )

    policy_payload = {
        "intent": "check_booking",
        "action": "fact",
        "tool_action": "calendar.get_booking",
        "tool_args": {"appointment_id": ""},
        "pack_refs": [],
        "slots": {"service": "Маникюр", "datetime": "2026-02-18", "name": "Лена"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "booking_check",
        "goal": "booking",
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Да, запись подтверждена: 18.02 в 10:00 у Айгерим.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "ok",
                "appointment_id": "cb99d242-69ce-4154-b428-797f6e76c0cb",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.get_booking",
                "appointment_id": "cb99d242-69ce-4154-b428-797f6e76c0cb",
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending"
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification"
    ) as telegram_mock:
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
    assert "запись подтверждена" in (response.bot_response or "").lower()
    assert reuse_handover_mock.call_count == 0
    assert escalate_mock.call_count == 0
    assert telegram_mock.call_count == 0
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_decision") == "ok"
    assert meta.get("action") != "escalate"


def test_booking_reschedule_missing_slot_does_not_escalate_without_manager_request(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "llm_policy_core_tool",
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Могу изменить время на утро?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-reschedule-missing-slot",
                timestamp=1234567911,
            ),
        ),
    )

    policy_payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.9,
        "reason": "reschedule_time",
        "goal": "booking",
        "slots": {"service": "Маникюр"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=False,
            response_text="На какую дату и время вам удобно?",
            error_code="missing_date",
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "missing_slot",
                "missing_slot": "datetime",
            },
            trace={
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
                "missing_slot": "datetime",
            },
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ) as reuse_handover_mock, patch(
        "app.routers.webhook.decision.escalate_to_pending"
    ) as escalate_mock, patch(
        "app.routers.webhook.decision.send_telegram_notification"
    ) as telegram_mock:
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
    assert response.bot_response != webhook_router.MSG_ESCALATED
    assert "На какую дату и время вам удобно?" in (response.bot_response or "")
    assert reuse_handover_mock.called is False
    assert escalate_mock.called is False
    assert telegram_mock.called is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "calendar.list_slots"
    assert meta.get("tool_decision") == "missing_slot"


def test_llm_policy_core_info_tool_restores_booking_followup_from_slots(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12T13:00:00",
            }
        },
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть парковка?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-info-tool-booking-followup",
                timestamp=1234567898,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": ["parking"],
        "language": "ru",
        "confidence": 0.8,
        "reason": "parking_question",
        "goal": "info",
        "slots": {"service": "Маникюр", "datetime": "2026-02-12T13:00:00"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        return_value=SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Да, есть парковка рядом с салоном.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "ok",
                "info_sections": ["parking"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "catalog.location",
                "info_sections": ["parking"],
            },
            expected_reply_type=None,
        ),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "парковка" in response.bot_response.casefold()
    assert webhook_router.MSG_BOOKING_ASK_NAME in response.bot_response
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_NAME
    booking_ctx = conversation.context.get("booking", {})
    assert booking_ctx.get("service") == "Маникюр"
    assert booking_ctx.get("datetime") == "2026-02-12T13:00:00"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("tool_action") == "catalog.location"
    assert "parking" in (meta.get("info_sections") or [])


def test_llm_policy_core_service_query_rewrites_to_location_with_reason_code(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Где вы находитесь и есть парковка?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-service-to-location",
                timestamp=1234567908,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": ["location", "parking"],
        "language": "ru",
        "confidence": 0.85,
        "reason": "explicit_location_question",
        "goal": "info",
        "slots": {},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured_tool_action = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_action["tool_action"] = kwargs.get("tool_action")
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Адрес: Алматы, ул. Абая 150. Парковка есть.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "ok",
                "info_sections": ["location", "parking"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "catalog.location",
                "info_sections": ["location", "parking"],
            },
            expected_reply_type=None,
        )

    def _fake_detect_info_class_intents(_message_text, *, intent_decomp_set, client_slug=None):
        _ = intent_decomp_set, client_slug
        return {"location", "parking"}, {
            "info_signals": {
                "location": True,
                "parking": True,
                "hours": False,
                "master": False,
            }
        }

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook.decision._detect_info_class_intents",
        side_effect=_fake_detect_info_class_intents,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured_tool_action.get("tool_action") == "catalog.location"
    meta = saved_message.message_metadata.get("decision_meta", {})
    plan_audit = meta.get("llm_policy_plan_audit", {})
    assert plan_audit.get("plan_tool_action") == "catalog.service_query"
    assert plan_audit.get("final_tool_action") == "catalog.location"
    assert plan_audit.get("override_applied") is True
    assert "contract_validation_failure" in (plan_audit.get("override_reason_codes") or [])
    assert meta.get("llm_policy_override_reason_code") == "contract_validation_failure"


def test_llm_policy_core_catalog_location_passes_parking_info_hint(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Стрижка"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Парковка есть?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-location-parking-hint",
                timestamp=1234567899,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.7,
        "reason": "parking_question",
        "goal": "info",
        "slots": {"service": "Стрижка"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured = {}

    def _fake_tool_action(*args, **kwargs):
        captured["message_text"] = kwargs.get("message_text")
        captured["info_sections_hint"] = kwargs.get("info_sections_hint")
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть парковка рядом с салоном.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "ok",
                "info_sections": ["parking"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "catalog.location",
                "info_sections": ["parking"],
            },
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert captured.get("message_text") == "Парковка есть?"
    assert "parking" in (captured.get("info_sections_hint") or [])


def test_llm_policy_core_catalog_location_uses_policy_reason_for_parking_hint(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Стрижка"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Где вы находитесь?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-location-parking-reason",
                timestamp=1234567900,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.7,
        "reason": "Запрос информации о наличии парковки.",
        "goal": "info",
        "slots": {"service": "Стрижка"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured = {}

    def _fake_tool_action(*args, **kwargs):
        captured["info_sections_hint"] = kwargs.get("info_sections_hint")
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть парковка рядом с салоном.",
            error_code=None,
            decision_meta={"tool_action": "catalog.location", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "catalog.location"},
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "parking" in (captured.get("info_sections_hint") or [])


def test_llm_policy_core_catalog_location_uses_parking_intent_hint(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
        context={"booking": {"active": True, "service": "Стрижка"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подскажите адрес",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-location-parking-intent",
                timestamp=1234567901,
            ),
        ),
    )

    policy_payload = {
        "intent": "parking_inquiry",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.7,
        "reason": "location_followup",
        "goal": "info",
        "slots": {"service": "Стрижка"},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})
    captured = {}

    def _fake_tool_action(*args, **kwargs):
        captured["info_sections_hint"] = kwargs.get("info_sections_hint")
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть парковка рядом с салоном.",
            error_code=None,
            decision_meta={"tool_action": "catalog.location", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "catalog.location"},
            expected_reply_type=None,
        )

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch("app.routers.webhook.decision._collect_plan_consult_refs", return_value=([], None)), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "parking" in (captured.get("info_sections_hint") or [])


def test_llm_policy_core_info_tool_master_reply_sent_without_clarify(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Кто будет делать процедуру?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-info-master",
                timestamp=1234567902,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": "master"},
        "pack_refs": ["master"],
        "language": "ru",
        "confidence": 0.8,
        "reason": "master_question",
        "goal": "info",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook.decision._build_info_intent_reply",
        return_value=("По мастерам: Айгерим — маникюр.", {"info_sections": ["master"]}),
    ), patch(
        "app.routers.webhook.decision._handle_info_flow",
        side_effect=AssertionError("info flow should not be called when policy-core info reply is sent"),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert "мастер" in (response.bot_response or "").casefold()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "master"


def test_llm_policy_core_catalog_service_reply_normalized_to_master_info_by_signal(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть мастер по маникюру?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-master-override",
                timestamp=1234567903,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "Маникюр"},
        "pack_refs": ["pricing"],
        "language": "ru",
        "confidence": 0.7,
        "reason": "service_query_fallback",
        "goal": "info",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    def _fake_tool_action(*_args, **_kwargs):
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр классический — 2 500 ₸.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "truth_fallback",
            },
            trace={
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        )

    def _fake_detect_info_class_intents(
        _message_text, *, intent_decomp_set, client_slug=None
    ):
        _ = client_slug
        if intent_decomp_set:
            return set(), {"info_signals": {"master": False}}
        return {"master"}, {"info_signals": {"master": True}}

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ), patch(
        "app.routers.webhook.decision._detect_info_class_intents",
        side_effect=_fake_detect_info_class_intents,
    ), patch(
        "app.routers.webhook.decision._build_info_intent_reply",
        return_value=("По мастерам: Айгерим — маникюр.", {"info_sections": ["master"]}),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert "мастер" in (response.bot_response or "").casefold()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "master"
    assert meta.get("expected_reply_type") == "service_choice"


def test_llm_policy_core_catalog_location_reply_normalized_to_master_info(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть мастера для длинной стрижки?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-master-location-override",
                timestamp=1234567904,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": ["hours"],
        "language": "ru",
        "confidence": 0.7,
        "reason": "location_fallback",
        "goal": "info",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 11.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    def _fake_tool_action(*_args, **_kwargs):
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Адрес: Алматы, ул. Абая 150.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "ok",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "catalog.location",
            },
            expected_reply_type=None,
        )

    def _fake_detect_info_class_intents(
        _message_text, *, intent_decomp_set, client_slug=None
    ):
        _ = client_slug
        if intent_decomp_set:
            return set(), {"info_signals": {"master": False}}
        return {"master"}, {"info_signals": {"master": True, "hours": False, "location": False}}

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ), patch(
        "app.routers.webhook.decision._detect_info_class_intents",
        side_effect=_fake_detect_info_class_intents,
    ), patch(
        "app.routers.webhook.decision._build_info_intent_reply",
        return_value=("По мастерам: Айгерим — длинные стрижки.", {"info_sections": ["master"]}),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert "мастер" in (response.bot_response or "").casefold()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "master"


def test_has_explicit_location_or_hours_request_strict_mode_ignores_derived_hours(monkeypatch):
    from app.routers.webhook import decision as decision_router

    def _fake_detect(*_args, **_kwargs):
        return {
            "master",
            "hours",
        }, {
            "info_signals": {
                "master": True,
                "hours": True,
                "location": False,
                "parking": False,
                "location_address_hint": False,
            },
            "anchor_intents": [],
        }

    monkeypatch.setattr(decision_router, "_detect_info_class_intents", _fake_detect)

    assert (
        decision_router._has_explicit_location_or_hours_request(
            "У вас есть мастера, которые работают с долгими стрижками?",
            client_slug="demo_salon",
            strict=True,
        )
        is False
    )


def test_has_explicit_location_or_hours_request_strict_mode_real_phrase_no_false_positive():
    from app.routers.webhook import decision as decision_router

    assert (
        decision_router._has_explicit_location_or_hours_request(
            "У вас есть мастера, которые работают с долгими стрижками?",
            client_slug="demo_salon",
            strict=True,
        )
        is False
    )


def test_derive_policy_info_refs_mixed_master_hours_prefers_master_without_explicit_markers():
    from app.routers.webhook import decision as decision_router

    refs = decision_router._derive_policy_info_refs(
        policy_intent=None,
        message_text="У вас есть мастера, которые работают с долгими стрижками?",
        client_slug="demo_salon",
    )

    assert refs
    assert "master" in refs
    assert refs[0] == "master"


def test_derive_policy_info_refs_mixed_master_hours_keeps_hours_priority_when_explicit():
    from app.routers.webhook import decision as decision_router

    refs = decision_router._derive_policy_info_refs(
        policy_intent=None,
        message_text="Какие мастера работают до скольки?",
        client_slug="demo_salon",
    )

    assert "master" in refs
    assert "hours" in refs
    assert refs.index("hours") < refs.index("master")


def test_llm_policy_core_semantic_arbitration_off_keeps_master_without_location_rewrite(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("LLM_POLICY_CORE_SEMANTIC_ARBITRATION", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть мастера, которые работают с долгими стрижками?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-semantic-arb-off",
                timestamp=1234567905,
            ),
        ),
    )

    policy_payload = {
        "intent": "info",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "долгие стрижки"},
        "pack_refs": ["hours"],
        "language": "ru",
        "confidence": 0.75,
        "reason": "mixed_master_hours",
        "goal": "info",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 10.0,
    }
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    def _fake_tool_action(*_args, **_kwargs):
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Долгие стрижки доступны по прайсу.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "truth_fallback",
            },
            trace={
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
            },
            expected_reply_type=None,
        )

    def _fake_detect_info_class_intents(_message_text, *, intent_decomp_set, client_slug=None):
        _ = client_slug
        if intent_decomp_set:
            return set(), {"info_signals": {"master": False}}
        return {"master", "hours"}, {
            "info_signals": {"master": True, "hours": True, "location": False, "parking": False},
            "anchor_intents": [],
        }

    with patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_tool_action,
    ) as execute_tool_action_mock, patch(
        "app.routers.webhook.decision._detect_info_class_intents",
        side_effect=_fake_detect_info_class_intents,
    ), patch(
        "app.routers.webhook.decision._build_info_intent_reply",
        return_value=("По мастерам: Айгерим и Дана работают с длинными стрижками.", {"info_sections": ["master"]}),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert "мастер" in (response.bot_response or "").casefold()
    assert execute_tool_action_mock.call_count == 1
    assert execute_tool_action_mock.call_args.kwargs.get("tool_action") == "catalog.service_query"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent") == "master"


def test_llm_policy_core_consult_tool_normalized_to_info_by_info_signals(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько это занимает по времени?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-consult-normalize-info",
                timestamp=1234567901,
            ),
        ),
    )

    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=None,
        intent_queue=None,
        expected_reply_matched=None,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal="consult",
    )
    intent_decomp_state = IntentDecompositionState(
        intent_decomp_payload={"intents": ["duration"], "consult_intent": False},
        intent_decomp_intents=["duration"],
        intent_decomp_primary="duration",
        intent_decomp_secondary=[],
        intent_decomp_service_query=None,
        intent_decomp_multi=False,
        intent_decomp_used=True,
        intent_decomp_set={"duration"},
        consult_intent=False,
        consult_topic=None,
        consult_question=None,
        intent_queue_choice=None,
        pending_intent_queue=None,
        pending_expected_reply_type=None,
        intent_queue_expected_next=None,
        intent_queue_event=None,
        info_class_intents={"duration"},
        info_class_meta={"info_signals": {"duration": True}},
        basic_info_message=False,
        allow_service_carryover=False,
        consult_return_pending=False,
        consult_return_reason=None,
        consult_return_prompt=None,
        booking_signal=False,
        booking_block_meta=None,
        booking_wants_flow=False,
        booking_blocked=False,
        booking_active=False,
        booking_context={},
        booking={},
        class_carryover=None,
        context=conversation.context,
        context_manager={},
        current_goal="consult",
    )
    policy_payload = {
        "intent": "consult",
        "action": "fact",
        "tool_action": "consult",
        "tool_args": {"consult_question": "Сколько это занимает по времени?"},
        "pack_refs": ["general_consult"],
        "language": "ru",
        "confidence": 0.0,
        "reason": "consult_duration_question",
        "goal": "consult",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    info_response = WebhookResponse(
        success=True,
        message="Info class reply sent",
        conversation_id=conversation_id,
        bot_response="Обычно это занимает 1-2 часа.",
    )

    with patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._run_intent_decomposition",
        return_value=intent_decomp_state,
    ), patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=(["general_consult"], None),
    ), patch(
        "app.routers.webhook.decision._handle_info_flow",
        return_value=SimpleNamespace(response=info_response, force_truth_gate=False),
    ) as info_flow_mock, patch(
        "app.routers.webhook.decision._handle_consult_flow",
        return_value=SimpleNamespace(
            consult_intent=False,
            consult_topic=None,
            consult_question=None,
            intent_decomp_payload=intent_decomp_state.intent_decomp_payload,
            response=None,
        ),
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "1-2" in response.bot_response
    assert info_flow_mock.called
    info_call_kwargs = info_flow_mock.call_args.kwargs
    assert info_call_kwargs.get("policy_handler") is not None
    assert info_call_kwargs.get("info_class_meta") == {"info_signals": {"duration": True}}
    meta = saved_message.message_metadata.get("decision_meta", {})
    llm_policy = meta.get("llm_policy_core", {})
    assert llm_policy.get("validated") is True
    assert llm_policy.get("consult_normalized_to_info") is True


def test_llm_policy_core_consult_ref_does_not_shadow_allowed_consult_refs(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Здравствуйте, мне нужна консультация по стрижкам.",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-consult-ref-only",
                timestamp=1234567911,
            ),
        ),
    )

    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=None,
        intent_queue=None,
        expected_reply_matched=None,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal="consult",
    )
    intent_decomp_state = IntentDecompositionState(
        intent_decomp_payload={"intents": ["duration"], "consult_intent": False},
        intent_decomp_intents=["duration"],
        intent_decomp_primary="duration",
        intent_decomp_secondary=[],
        intent_decomp_service_query=None,
        intent_decomp_multi=False,
        intent_decomp_used=True,
        intent_decomp_set={"duration"},
        consult_intent=False,
        consult_topic=None,
        consult_question=None,
        intent_queue_choice=None,
        pending_intent_queue=None,
        pending_expected_reply_type=None,
        intent_queue_expected_next=None,
        intent_queue_event=None,
        info_class_intents={"duration"},
        info_class_meta={"info_signals": {"duration": True}},
        basic_info_message=False,
        allow_service_carryover=False,
        consult_return_pending=False,
        consult_return_reason=None,
        consult_return_prompt=None,
        booking_signal=False,
        booking_block_meta=None,
        booking_wants_flow=False,
        booking_blocked=False,
        booking_active=False,
        booking_context={},
        booking={},
        class_carryover=None,
        context=conversation.context,
        context_manager={},
        current_goal="consult",
    )
    policy_payload = {
        "intent": "consult",
        "action": "fact",
        "tool_action": "consult",
        "tool_args": {
            "consult_ref": "general_consult",
            "consult_question": "Здравствуйте, мне нужна консультация по стрижкам.",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.7,
        "reason": "consult_ref_only",
        "goal": "consult",
        "slots": {"service": "", "datetime": "", "name": ""},
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    policy_result = {
        "ok": True,
        "payload": policy_payload,
        "error": None,
        "raw": json.dumps(policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 12.0,
    }
    info_response = WebhookResponse(
        success=True,
        message="Info class reply sent",
        conversation_id=conversation_id,
        bot_response="По стрижкам обычно это занимает около 1-2 часов.",
    )

    with patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._run_intent_decomposition",
        return_value=intent_decomp_state,
    ), patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=(["general_consult"], None),
    ), patch(
        "app.routers.webhook.decision._handle_info_flow",
        return_value=SimpleNamespace(response=info_response, force_truth_gate=False),
    ), patch(
        "app.routers.webhook.decision._handle_consult_flow",
        return_value=SimpleNamespace(
            consult_intent=False,
            consult_topic=None,
            consult_question=None,
            intent_decomp_payload=intent_decomp_state.intent_decomp_payload,
            response=None,
        ),
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler",
        return_value={"truth_gate": Mock(), "service_matcher": Mock()},
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match",
        return_value=None,
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
    assert "1-2" in (response.bot_response or "")
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action_source") == "llm_policy_core"
    assert meta.get("source") != "reasoning_core"
    assert meta.get("error_source") != "reasoning_core"
    llm_policy = meta.get("llm_policy_core", {})
    assert llm_policy.get("validated") is True
    assert llm_policy.get("consult_normalized_to_info") is True


def test_llm_policy_core_degraded_booking_guard_uses_safe_collect(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")

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
        context={"booking": {"active": True}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="хочу записаться",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-degraded-1",
                timestamp=1234567897,
            ),
        ),
    )

    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=None,
        intent_queue=None,
        expected_reply_matched=None,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal="booking",
    )
    intent_decomp_state = IntentDecompositionState(
        intent_decomp_payload={"intents": ["booking"]},
        intent_decomp_intents=["booking"],
        intent_decomp_primary="booking",
        intent_decomp_secondary=[],
        intent_decomp_service_query=None,
        intent_decomp_multi=False,
        intent_decomp_used=True,
        intent_decomp_set={"booking"},
        consult_intent=False,
        consult_topic=None,
        consult_question=None,
        intent_queue_choice=None,
        pending_intent_queue=None,
        pending_expected_reply_type=None,
        intent_queue_expected_next=None,
        intent_queue_event=None,
        info_class_intents=set(),
        info_class_meta={},
        basic_info_message=False,
        allow_service_carryover=False,
        consult_return_pending=False,
        consult_return_reason=None,
        consult_return_prompt=None,
        booking_signal=True,
        booking_block_meta=None,
        booking_wants_flow=True,
        booking_blocked=False,
        booking_active=True,
        booking_context={"active": True},
        booking={"active": True},
        class_carryover=None,
        context=conversation.context,
        context_manager={},
        current_goal="booking",
    )
    policy_result = {
        "ok": False,
        "payload": None,
        "error": "invalid_schema",
        "raw": "{\"action\":\"collect\"}",
        "attempted": True,
        "elapsed_ms": 12.0,
    }

    with patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._run_intent_decomposition",
        return_value=intent_decomp_state,
    ), patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        return_value=policy_result,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._resolve_action",
        side_effect=AssertionError("degraded guard should return before _resolve_action"),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
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
    assert response.bot_response == webhook_router.MSG_BOOKING_ASK_SERVICE
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("policy_core_mode") == "degraded_fallback"
    assert meta.get("policy_core_degrade_reason") == "policy_error:invalid_schema"
    failure = meta.get("policy_core_failure", {})
    assert failure.get("category") == "policy_error"
    assert failure.get("code") == "invalid_schema"
    assert failure.get("retryable") is False
    assert failure.get("info_rescue_eligible") is True
    assert meta.get("action") == "booking_prompt"


def test_llm_policy_core_degraded_booking_guard_retries_with_llm_rescue_then_uses_calendar_tool(
    monkeypatch,
):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "1")

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
        context={"booking": {"active": True, "service": "Стрижка"}},
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на завтра?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-llm-policy-core-degraded-slot-lookup",
                timestamp=1234567898,
            ),
        ),
    )

    expected_reply_state = ExpectedReplyState(
        context=conversation.context,
        context_manager={},
        expected_reply_type=None,
        intent_queue=None,
        expected_reply_matched=None,
        expected_reply_shortcircuit=False,
        expected_reply_blocked_by_info=False,
        memory_expected_reply_type=None,
        current_goal="booking",
    )
    intent_decomp_state = IntentDecompositionState(
        intent_decomp_payload={"intents": ["booking"]},
        intent_decomp_intents=["booking"],
        intent_decomp_primary="booking",
        intent_decomp_secondary=[],
        intent_decomp_service_query="Стрижка",
        intent_decomp_multi=False,
        intent_decomp_used=True,
        intent_decomp_set={"booking"},
        consult_intent=False,
        consult_topic=None,
        consult_question=None,
        intent_queue_choice=None,
        pending_intent_queue=None,
        pending_expected_reply_type=None,
        intent_queue_expected_next=None,
        intent_queue_event=None,
        info_class_intents=set(),
        info_class_meta={},
        basic_info_message=False,
        allow_service_carryover=False,
        consult_return_pending=False,
        consult_return_reason=None,
        consult_return_prompt=None,
        booking_signal=True,
        booking_block_meta=None,
        booking_wants_flow=True,
        booking_blocked=False,
        booking_active=True,
        booking_context={"active": True, "service": "Стрижка"},
        booking={"active": True, "service": "Стрижка"},
        class_carryover=None,
        context=conversation.context,
        context_manager={},
        current_goal="booking",
    )
    primary_policy_result = {
        "ok": False,
        "payload": None,
        "error": "invalid_schema",
        "raw": "{\"action\":\"collect\"}",
        "attempted": True,
        "elapsed_ms": 9.0,
    }
    rescue_policy_payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.list_slots",
        "tool_args": {
            "service_query": "Стрижка",
            "start_at": "2026-02-18T10:00:00",
        },
        "pack_refs": [],
        "language": "ru",
        "confidence": 0.95,
        "reason": "slots_lookup",
        "goal": "booking",
        "slots": {
            "service": "Стрижка",
            "datetime": "2026-02-18T10:00:00",
        },
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
    }
    rescue_policy_result = {
        "ok": True,
        "payload": rescue_policy_payload,
        "error": None,
        "raw": json.dumps(rescue_policy_payload, ensure_ascii=False),
        "attempted": True,
        "elapsed_ms": 13.0,
    }

    route_policy_calls = []

    def _route_policy_core(*_args, **kwargs):
        route_policy_calls.append(kwargs)
        if len(route_policy_calls) == 1:
            return primary_policy_result
        return rescue_policy_result

    captured_tool_call = {}

    def _fake_execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Свободные слоты: Айгерим 10:00, 11:00",
            error_code=None,
            decision_meta={"tool_action": "calendar.list_slots", "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": "calendar.list_slots"},
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        )

    with patch(
        "app.routers.webhook.decision._apply_expected_reply_contract",
        return_value=expected_reply_state,
    ), patch(
        "app.routers.webhook.decision._run_intent_decomposition",
        return_value=intent_decomp_state,
    ), patch(
        "app.routers.webhook.decision.route_llm_policy_core",
        side_effect=_route_policy_core,
    ), patch(
        "app.routers.webhook.decision._collect_plan_consult_refs",
        return_value=([], None),
    ), patch(
        "app.routers.webhook.decision._handle_policy_escalation_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_knowledge_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision._handle_minimum_data_safe_mode_gate",
        return_value=None,
    ), patch(
        "app.routers.webhook.decision.POLICY_CORE_RESCUE_TIMEOUT_SECONDS",
        1.5,
    ), patch(
        "app.services.tool_registry_service.execute_tool_action",
        side_effect=_fake_execute_tool_action,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert "Свободные слоты" in (response.bot_response or "")
    assert len(route_policy_calls) == 2
    rescue_timing_context = route_policy_calls[1].get("timing_context")
    assert isinstance(rescue_timing_context, dict)
    assert rescue_timing_context.get("pipeline_budget_ms") == 1500
    assert captured_tool_call.get("tool_action") == "calendar.list_slots"
    assert (captured_tool_call.get("tool_args", {}).get("service_query") or "").casefold() == "стрижка"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "reply"
    assert meta.get("intent") == "calendar.list_slots"
    assert meta.get("policy_core_mode") == "policy_core"
    assert meta.get("tool_action") == "calendar.list_slots"
    llm_policy = meta.get("llm_policy_core", {})
    assert llm_policy.get("rescue_attempted") is True
    assert llm_policy.get("rescue_applied") is True
    assert llm_policy.get("rescue_trigger_error") == "invalid_schema"


def test_policy_core_reason_supports_info_rescue_prefixes():
    assert _policy_core_reason_supports_info_rescue("policy_error:invalid_schema") is True
    assert _policy_core_reason_supports_info_rescue("policy_validation:low_confidence") is True
    assert _policy_core_reason_supports_info_rescue("llm_degraded:llm_timeout") is True
    assert _policy_core_reason_supports_info_rescue("guard_not_eligible") is False
    assert _policy_core_reason_supports_info_rescue(None) is False


def test_classify_policy_core_degrade_reason_taxonomy():
    retryable_error = _classify_policy_core_degrade_reason("policy_error:timeout")
    assert retryable_error["category"] == "policy_error"
    assert retryable_error["code"] == "timeout"
    assert retryable_error["retryable"] is True
    assert retryable_error["info_rescue_eligible"] is True
    assert retryable_error["severity"] == "medium"

    hard_validation = _classify_policy_core_degrade_reason("policy_validation:invalid_schema")
    assert hard_validation["category"] == "policy_validation"
    assert hard_validation["code"] == "invalid_schema"
    assert hard_validation["retryable"] is False
    assert hard_validation["severity"] == "high"

    guard = _classify_policy_core_degrade_reason("guard_not_eligible")
    assert guard["category"] == "guard"
    assert guard["code"] == "guard_not_eligible"
    assert guard["retryable"] is False
    assert guard["info_rescue_eligible"] is False
    assert guard["severity"] == "low"


def test_policy_has_style_reference_hint_from_intent_or_reason():
    assert _policy_has_style_reference_hint(policy_intent="send_photo", policy_reason=None) is True
    assert _policy_has_style_reference_hint(policy_intent="get_popular_style", policy_reason=None) is True
    assert (
        _policy_has_style_reference_hint(
            policy_intent="other",
            policy_reason="style_reference_text",
        )
        is True
    )
    assert _policy_has_style_reference_hint(policy_intent="booking", policy_reason="booking_flow") is False


def test_validate_policy_check_confirm_contract_allows_valid_paths():
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="check_booking",
            policy_action="fact",
            policy_tool_action="calendar.get_booking",
        )
        is None
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="confirm_booking",
            policy_action="collect",
            policy_tool_action="calendar.book_slot",
        )
        is None
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="verify_booking",
            policy_action="handoff",
            policy_tool_action="handoff",
        )
        is None
    )


def test_validate_policy_check_confirm_contract_rejects_mismatch():
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="check_booking",
            policy_action="fact",
            policy_tool_action="calendar.book_slot",
        )
        == "check_confirm_tool_mismatch"
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="confirm_booking",
            policy_action="handoff",
            policy_tool_action="calendar.book_slot",
        )
        == "check_confirm_action_mismatch"
    )


def test_unknown_state_fallback_sends_reply():
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
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
        conversation_query=conversation_query,
        user_query=user_query,
    )
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="тест",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-unknown-state-1",
                timestamp=1234567897,
            ),
        ),
    )

    domain_result = (DomainIntent.UNKNOWN, 0.0, 0.0, {"out_hits": 0, "strict_in_hits": 0})
    policy_result = {
        "ok": False,
        "payload": None,
        "error": "skip",
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
    }

    with patch("app.routers.webhook.decision._resolve_action", return_value=DecisionOutcome("unknown_state")), patch(
        "app.routers.webhook.decision.route_llm_policy_core", return_value=policy_result
    ), patch(
        "app.routers.webhook.decision._handle_llm_primary",
        return_value=SimpleNamespace(
            response=None,
            llm_primary_result=None,
            llm_primary_failed=False,
            llm_primary_reason=None,
        ),
    ), patch(
        "app.routers.webhook.decision._handle_booking_flow",
        return_value=SimpleNamespace(response=None, booking_t0=None, booking_logged=True),
    ), patch(
        "app.routers.webhook.decision._handle_booking_interrupt", return_value=None
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
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
    assert response.bot_response in {
        webhook_router.MSG_FACT_GUARD_CLARIFY,
        webhook_router.MSG_BOOKING_ASK_SERVICE,
    }
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("policy_core_mode") == "degraded_fallback"


def test_short_intent_hint_bypasses_early_ood():
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
    user = SimpleNamespace(id="user-123", context={})

    def _query(model):
        query = Mock()
        query.filter.return_value.first.return_value = None
        query.filter.return_value.all.return_value = []
        model_name = getattr(model, "__name__", None)
        if model_name == "Client":
            query.filter.return_value.first.return_value = client
        elif model_name == "ClientSettings":
            query.filter.return_value.first.return_value = settings
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        elif model_name == "User":
            query.filter.return_value.first.return_value = user
        return query

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="рахмет",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-short-intent-1",
                timestamp=1234567897,
            ),
        ),
    )

    intent_decomp = {
        "multi_intent": False,
        "primary_intent": "other",
        "secondary_intents": [],
        "intents": ["other"],
        "service_query": "",
        "consult_intent": False,
        "consult_topic": "",
        "consult_question": "",
    }

    domain_result = (DomainIntent.OUT_OF_DOMAIN, 0.1, 0.9, {"out_hits": 1, "strict_in_hits": 0})

    with patch("app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp), patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook.decision.classify_intent", return_value=Intent.THANKS
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch", return_value=None
    ), patch(
        "app.routers.webhook.branch_selection._get_active_branches", return_value=[]
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
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
    assert response.bot_response == webhook_router.THANKS_RESPONSE
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") != "out_of_domain"


def test_booking_confirm_requires_yes_for_llm_slot(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
    saved_message_1 = Mock()
    saved_message_1.message_metadata = {}
    saved_message_2 = Mock()
    saved_message_2.message_metadata = {}

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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {"active": True, "service": "маникюр", "last_question": "datetime"},
        },
    )
    user = SimpleNamespace(id="user-123", context={})

    def _make_db():
        client_query = Mock()
        client_query.filter.return_value.first.return_value = client
        settings_query = Mock()
        settings_query.filter.return_value.first.return_value = settings
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation
        user_query = Mock()
        user_query.filter.return_value.first.return_value = user
        branch_query = Mock()
        branch_query.filter.return_value.first.return_value = None
        branch_phone_query = Mock()
        branch_phone_query.filter.return_value.all.return_value = []

        def _query(model):
            if model is Client:
                return client_query
            if model is ClientSettings:
                return settings_query
            if model is Conversation:
                return conversation_query
            if model is User:
                return user_query
            if model is Branch:
                return branch_query
            if model is Branch.phone:
                return branch_phone_query
            return Mock()

        db = Mock()
        db.query.side_effect = _query
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        return db

    payload_confirm = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="на завтра в 15:00",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-confirm-1",
                timestamp=1234567899,
            ),
        ),
    )
    payload_yes = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="да",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-confirm-2",
                timestamp=1234567900,
            ),
        ),
    )

    llm_payload = {"ok": True, "payload": {"slot": "datetime", "value": "15:00", "confidence": 0.4}}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch.dict(
        os.environ,
        {
            "BOOKING_CONFIRM_ENABLED": "1",
            "BOOKING_CONFIRM_CONFIDENCE_THRESHOLD": "0.9",
            "TZ": "UTC",
        },
    ), patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "15:00", []),
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=llm_payload,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        side_effect=[saved_message_1, saved_message_2],
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
    ):
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload_confirm,
                _make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )
        assert response.success is True
        assert "15:00" in response.bot_response
        assert "верно" in response.bot_response.casefold()
        confirmation = conversation.context.get("booking", {}).get("confirmation")
        assert confirmation and confirmation.get("slot") == "datetime"
        meta = saved_message_1.message_metadata.get("decision_meta", {})
        assert meta.get("slot_confirmation_required") is True

        response_yes = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload_yes,
                _make_db(),
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )

    assert response_yes.success is True
    assert webhook_router.MSG_BOOKING_ASK_NAME in response_yes.bot_response
    booking_context = conversation.context.get("booking", {})
    assert booking_context.get("datetime") == "15:00"
    assert booking_context.get("confirmation") is None


def test_booking_time_date_only_prefers_deterministic_without_confirm(monkeypatch):
    monkeypatch.setenv("LLM_POLICY_CORE_ENABLED", "0")
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {"active": True, "service": "маникюр", "last_question": "datetime"},
        },
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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="на завтра",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-date-only",
                timestamp=1234567901,
            ),
        ),
    )

    llm_payload = {"ok": True, "payload": {"slot": "datetime", "value": "завтра", "confidence": 0.2}}

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch.dict(
        os.environ,
        {
            "BOOKING_CONFIRM_ENABLED": "1",
            "BOOKING_CONFIRM_CONFIDENCE_THRESHOLD": "0.9",
            "TZ": "UTC",
        },
    ), patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "завтра", []),
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=llm_payload,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
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
    assert "точное время" in response.bot_response.casefold()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "booking_prompt"
    assert meta.get("slot_confirmation_required") is False
    assert conversation.context.get("booking", {}).get("datetime") == "завтра"
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME


def test_booking_slot_lock_keeps_booking_active_on_ood():
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {"active": True, "service": "маникюр", "last_question": "datetime"},
        },
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
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="какая погода?",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-slot-lock-1",
                timestamp=1234567901,
            ),
        ),
    )

    domain_result = (DomainIntent.OUT_OF_DOMAIN, 0.1, 0.9, {"out_hits": 1, "strict_in_hits": 0})

    with patch(
        "app.routers.webhook.decision.classify_domain_with_scores", return_value=domain_result
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response"
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
    assert webhook_router.MSG_BOOKING_ASK_DATETIME in response.bot_response
    assert webhook_router.MSG_BOOKING_REENGAGE not in response.bot_response
    assert conversation.context.get("booking", {}).get("active") is True


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
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            query.order_by.return_value.limit.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
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

    def _fake_question_type(segment: str, *, include_kinds=None, return_multi: bool = False, **_kwargs):
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
    booking_result = SimpleNamespace(response=None, booking_t0=None, booking_logged=True)

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint
    ), patch(
        "app.routers.webhook._legacy.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge._search_services_index", side_effect=_fake_search_services_index
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        side_effect=[
            Result.success((None, "low_confidence")),
            Result.success(("Адрес: Абая, Алматы. Работаем 9:00-21:00 ежедневно.", "high")),
        ],
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        side_effect=[saved_message_first, saved_message_second],
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook.decision._handle_booking_flow",
        return_value=booking_result,
    ), patch(
        "app.routers.webhook._legacy._should_run_booking_flow",
        return_value=False,
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook._legacy.escalate_to_pending"
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
    assert any(
        token in response_text
        for token in ("адрес", "алматы", "маник", "работ", "9:00", "21:00", "ежедневно", "без выходных")
    )
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response_info.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response_info.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response_info.bot_response

    assert response_name.success is True
    response_name_text = response_name.bot_response.casefold()
    assert any(
        token in response_name_text
        for token in ("адрес", "алматы", "маник", "работ", "9:00", "21:00", "ежедневно", "без выходных")
    )
    assert webhook_router.MSG_BOOKING_ASK_SERVICE not in response_name.bot_response
    assert webhook_router.MSG_BOOKING_ASK_DATETIME not in response_name.bot_response
    assert webhook_router.MSG_BOOKING_ASK_NAME not in response_name.bot_response
    meta_first = saved_message_first.message_metadata.get("decision_meta", {})
    meta_second = saved_message_second.message_metadata.get("decision_meta", {})
    assert meta_first.get("tool_action") not in {"calendar.list_slots", "calendar.book_slot"}
    assert meta_second.get("tool_action") not in {"calendar.list_slots", "calendar.book_slot"}
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
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            query.order_by.return_value.limit.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
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

    def _fake_question_type(segment: str, *, include_kinds=None, return_multi: bool = False, **_kwargs):
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint
    ), patch(
        "app.routers.webhook._legacy.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_fake_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success((None, "low_confidence")),
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook._legacy.escalate_to_pending"
    ) as mock_escalate, patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
    ):
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
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-18 10:00",
                "name": "Лена",
                "last_question": "name",
            },
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            query.order_by.return_value.limit.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.detect_multi_intent", return_value=intent_decomp
    ), patch(
        "app.routers.webhook._legacy.semantic_question_type", side_effect=_empty_question_type
    ), patch(
        "app.services.demo_salon_knowledge.semantic_question_type", side_effect=_empty_question_type
    ), patch(
        "app.routers.webhook._legacy.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.services.demo_salon_knowledge.semantic_service_match", side_effect=_fake_semantic_match
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success(("llm", "high")),
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover"
    ) as mock_reuse, patch(
        "app.routers.webhook._legacy.escalate_to_pending"
    ) as mock_escalate:
        mock_reuse.return_value = (None, False, False)
        mock_escalate.return_value = SimpleNamespace(ok=False, error="test", error_code="test")
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
    assert meta.get("service_query_source") == "intent_decomp"
    assert meta.get("service_query_score") == 1.0
    assert meta.get("booking_blocked_reason") == "info_question"
    booking_ctx = (conversation.context or {}).get("booking", {})
    assert booking_ctx.get("service") == "Маникюр"
    assert booking_ctx.get("datetime") == "2026-02-18 10:00"
    assert booking_ctx.get("name") == "Лена"
    assert booking_ctx.get("active") is False

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
        db.query.side_effect = _build_query_side_effect(
            client_query=client_query,
            settings_query=settings_query,
            conversation_query=conversation_query,
            user_query=user_query,
        )
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook.decision._maybe_transcribe_voice",
        AsyncMock(return_value=("маникюр", "ok", asr_meta)),
    ), patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
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

    with patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success(("ok", "high")),
    ) as mock_generate, patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        return_value=saved_message,
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
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


def test_asr_inflight_blocks_new_audio():
    saved_message = Mock()
    saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    now = datetime.now(timezone.utc)
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
        context={
            webhook_router.ASR_INFLIGHT_KEY: {
                "started_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=60)).isoformat(),
            }
        },
    )
    user = SimpleNamespace(id="user-123", user_metadata={})

    def make_db():
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
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
                messageId="msg-voice-inflight",
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

    with patch(
        "app.routers.webhook.decision._maybe_transcribe_voice",
        AsyncMock(return_value=("маникюр", "ok", {})),
    ) as mock_transcribe, patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
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
    assert response.bot_response == webhook_router.MSG_ASR_INFLIGHT_WAIT
    mock_transcribe.assert_not_called()


def test_style_reference_sets_pending():
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
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})

    def make_db():
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу как на фото",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-style-ref-1",
                timestamp=1234567899,
            ),
        ),
    )
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED",
        False,
    ), patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        return_value={"multi_intent": False, "intents": []},
    ), patch(
        "app.routers.webhook._legacy.classify_intent",
        return_value=Intent.QUESTION,
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
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
    assert response.bot_response == webhook_router.MSG_STYLE_REFERENCE_NEED_MEDIA
    pending = conversation.context.get(webhook_router.STYLE_REFERENCE_PENDING_KEY)
    assert isinstance(pending, dict)
    assert pending.get("reason") == "text_only"
    assert "asr_confirm_pending" not in conversation.context


def test_style_reference_detects_send_photo_phrases():
    assert webhook_router._is_style_reference_request(
        "Я могу прислать фото своей прически.",
        has_media=False,
    )
    assert webhook_router._is_style_reference_request(
        "У вас есть возможность отправить фото?",
        has_media=False,
    )


def test_booking_verification_handoff_intent_detection():
    assert webhook_router._is_booking_verification_handoff_intent(
        "check_booking",
        "calendar.get_booking",
    )
    assert webhook_router._is_booking_verification_handoff_intent(
        "confirm_booking",
        "calendar.book_slot",
    )
    assert not webhook_router._is_booking_verification_handoff_intent(
        "booking",
        "calendar.get_booking",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Я хочу проверить свою запись.",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Подтвердите, пожалуйста, запись.",
    )
    assert not webhook_router._looks_like_booking_verification_request(
        "Мне нужно изменить время записи.",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Подтвердите, пожалуйста, новую дату.",
    )


def test_is_booking_request_detects_need_plus_service_with_datetime_without_lexicon_phrase():
    assert webhook_router._is_booking_request(
        "Здравствуйте, мне нужна маникюр завтра.",
        client_slug="demo_salon",
    )


def test_is_booking_request_rejects_need_plus_service_without_datetime_or_booking_lexicon():
    assert not webhook_router._is_booking_request(
        "Здравствуйте, мне нужна маникюр.",
        client_slug="demo_salon",
    )


def test_style_reference_photo_escalates_during_booking_flow():
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
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
            "booking": {
                "active": True,
                "service": "Педикюр",
                "datetime": "2023-10-07T18:00:00",
                "last_question": "service",
            },
        },
    )
    user = SimpleNamespace(id="user-123", context={}, user_metadata={})
    handover = SimpleNamespace(id=uuid4(), status="pending")
    escalate_result = SimpleNamespace(ok=True, value=handover, error=None)

    def make_db():
        def _query(model):
            query = Mock()
            query.filter.return_value.first.return_value = None
            query.filter.return_value.all.return_value = []
            model_name = getattr(model, "__name__", None)
            if model_name == "Client":
                query.filter.return_value.first.return_value = client
            elif model_name == "ClientSettings":
                query.filter.return_value.first.return_value = settings
            elif model_name == "Conversation":
                query.filter.return_value.first.return_value = conversation
            elif model_name == "User":
                query.filter.return_value.first.return_value = user
            return query

        db = Mock()
        db.query.side_effect = _query
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Вот фото референса",
            messageType="image",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-style-ref-booking-photo-1",
                timestamp=1234567999,
            ),
            mediaData={
                "type": "image",
                "mimetype": "image/jpeg",
                "url": "/home/zhan/TrufflesLogoClear.png",
                "fileName": "TrufflesLogoClear.png",
                "caption": "Вот фото референса",
            },
        ),
    )
    domain_result = (DomainIntent.IN_DOMAIN, 0.7, 0.1, {"out_hits": 0, "strict_in_hits": 1})

    with patch(
        "app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED",
        False,
    ), patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        return_value={"multi_intent": False, "intents": []},
    ), patch(
        "app.routers.webhook._legacy.classify_intent",
        return_value=Intent.QUESTION,
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook.decision.classify_domain_with_scores",
        return_value=domain_result,
    ), patch(
        "app.routers.webhook.decision._evaluate_media_decision",
        AsyncMock(return_value=webhook_router.MediaDecision(allowed=True)),
    ), patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook.http._lookup_sender_branch",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
    ), patch(
        "app.routers.webhook.decision._reuse_active_handover",
        return_value=(None, False, False),
    ), patch(
        "app.routers.webhook.decision.escalate_to_pending",
        return_value=escalate_result,
    ), patch(
        "app.routers.webhook.decision.send_telegram_notification",
        return_value=True,
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
    assert response.bot_response == webhook_router.MSG_MEDIA_STYLE_REFERENCE
    assert conversation.state in {
        ConversationState.BOT_ACTIVE.value,
        ConversationState.PENDING.value,
    }
    assert conversation.context.get("expected_reply_type") in {
        webhook_router.EXPECTED_REPLY_SERVICE,
        None,
    }
    booking_ctx = conversation.context.get("booking", {})
    assert booking_ctx.get("active") is True
    assert (booking_ctx.get("service") or "").casefold() == "педикюр"
    assert conversation.context.get(webhook_router.STYLE_REFERENCE_PENDING_KEY) is None
    trace_entries = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "style_reference" and entry.get("decision") == "escalate"
        for entry in trace_entries
        if isinstance(entry, dict)
    )


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
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            booking_signal = snapshot.get("signal")
        opt_out = any(is_opt_out_message(msg) for msg in messages)

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if "expect_opt_out" in automation:
            assert opt_out == automation["expect_opt_out"]
        return

    if check == "booking_flow":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            booking_signal = snapshot.get("signal")
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
