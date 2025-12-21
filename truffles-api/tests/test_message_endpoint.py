from uuid import uuid4
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.schemas.message import MessageRequest, MessageResponse


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
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_invalid_secret_returns_401(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
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
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
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
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
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
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_path_secret_fallback_returns_200(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook/secret",
                json={"client_slug": "test", "body": {"message": "hi", "metadata": {"remoteJid": "1@wa"}}},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
