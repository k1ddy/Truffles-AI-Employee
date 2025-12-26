from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routers import webhook as webhook_router
from app.schemas.message import MessageRequest, MessageResponse
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
