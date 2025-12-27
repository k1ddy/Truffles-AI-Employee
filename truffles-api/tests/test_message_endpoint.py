import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routers import webhook as webhook_router
from app.schemas.message import MessageRequest, MessageResponse
from app.services import escalation_service
from app.services.intent_service import Intent, is_opt_out_message
from app.services.message_service import select_handover_user_message
from app.services.state_machine import ConversationState


@pytest.fixture
def client():
    return TestClient(app)


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
        assert webhook_router._has_booking_signal(messages) is True

    def test_booking_updates_across_messages(self):
        booking = {"active": True}
        updated = webhook_router._update_booking_from_messages(booking, ["маникюр", "на завтра в 5"])
        assert updated.get("service")
        assert updated.get("datetime")


class TestBookingSlotGuards:
    def test_booking_name_skips_opt_out(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(booking, ["не пиши мне"])
        assert updated.get("name") is None

    def test_booking_name_skips_frustration(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(booking, ["иди нахуй"])
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
        assert policy["allow_booking_flow"] is True
        assert policy["allow_handover_create"] is False
        assert policy["allow_truth_gate_reply"] is True

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
            ("какие услуги вы оказываете?", "reply", "services_overview"),
            ("где вы находитесь?", "reply", "location"),
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
        message = "Как ухаживать за гель-лаком после процедуры?"
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


def _load_golden_cases() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "tests" / "test_cases.json"
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
        booking_signal = webhook_router._has_booking_signal(messages)
        opt_out = any(is_opt_out_message(msg) for msg in messages)

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if "expect_opt_out" in automation:
            assert opt_out == automation["expect_opt_out"]
        return

    if check == "booking_flow":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        booking_signal = webhook_router._has_booking_signal(messages)
        booking_state = webhook_router._update_booking_from_messages({}, messages)

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if automation.get("expect_service"):
            assert booking_state.get("service")
        if automation.get("expect_datetime"):
            assert booking_state.get("datetime")
        return

    pytest.fail(f"Unknown golden automation check: {check}")
