import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.schemas.message import MessageRequest, MessageResponse


@pytest.fixture
def client():
    return TestClient(app)


class TestMessageEndpoint:
    def test_message_request_validation(self, client):
        # Missing required fields
        response = client.post("/message", json={
            "content": "Привет!"
        })
        assert response.status_code == 422

    def test_message_with_invalid_uuid(self, client):
        response = client.post("/message", json={
            "client_id": "not-a-uuid",
            "remote_jid": "77759841926@s.whatsapp.net",
            "content": "Привет!"
        })
        assert response.status_code == 422


class TestMessageSchemas:
    def test_message_request_valid(self):
        req = MessageRequest(
            client_id=uuid4(),
            remote_jid="77759841926@s.whatsapp.net",
            content="Test",
            channel="whatsapp"
        )
        assert req.content == "Test"
        assert req.channel == "whatsapp"
    
    def test_message_response_valid(self):
        resp = MessageResponse(
            success=True,
            conversation_id=uuid4(),
            state="bot_active",
            bot_response="Test response"
        )
        assert resp.success == True
        assert resp.state == "bot_active"
