import uuid
from unittest.mock import Mock, patch

import pytest

from app.services.learning_service import add_to_knowledge, get_client_slug, is_owner_response


class TestIsOwnerResponse:
    def test_returns_true_when_manager_is_owner_by_id(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = "123456789"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789)

        assert result is True

    def test_returns_true_when_manager_is_owner_by_username(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = "@owner_user"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789, manager_username="owner_user")

        assert result is True

    def test_returns_true_when_owner_list_matches_id(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = "123456789, @owner_user"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789, manager_username="someone")

        assert result is True

    def test_returns_true_when_owner_list_matches_username(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = "987654321 @owner_user"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 111111111, manager_username="OWNER_USER")

        assert result is True

    def test_returns_false_when_manager_is_not_owner(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = "987654321"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789)

        assert result is False

    def test_returns_false_when_no_settings(self):
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789)

        assert result is False

    def test_returns_false_when_no_owner_id(self):
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.owner_telegram_id = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        result = is_owner_response(mock_db, uuid.uuid4(), 123456789)

        assert result is False


class TestGetClientSlug:
    def test_returns_slug_when_found(self):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        result = get_client_slug(mock_db, uuid.uuid4())

        assert result == "test_client"

    def test_returns_none_when_not_found(self):
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_client_slug(mock_db, uuid.uuid4())

        assert result is None


class TestAddToKnowledge:
    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    def test_adds_to_qdrant_successfully(self, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.return_value = [0.1] * 1024

        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__enter__.return_value.put.return_value = mock_response

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "What is the price?"
        mock_handover.manager_response = "The price is 10000 tenge"
        mock_handover.assigned_to_name = "Owner"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is not None
        mock_httpx.return_value.__enter__.return_value.put.assert_called_once()

    def test_returns_none_when_missing_user_message(self):
        mock_db = Mock()
        mock_handover = Mock()
        mock_handover.user_message = None
        mock_handover.manager_response = "Some response"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None

    def test_returns_none_when_missing_manager_response(self):
        mock_db = Mock()
        mock_handover = Mock()
        mock_handover.user_message = "Some question"
        mock_handover.manager_response = None

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None

    @patch("app.services.learning_service.get_client_slug")
    def test_returns_none_when_no_client_slug(self, mock_get_slug):
        mock_db = Mock()
        mock_get_slug.return_value = None

        mock_handover = Mock()
        mock_handover.user_message = "Question"
        mock_handover.manager_response = "Answer"
        mock_handover.client_id = uuid.uuid4()

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None

    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    @patch("app.services.learning_service.alert_error")
    def test_returns_none_on_qdrant_error(self, mock_alert, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.return_value = [0.1] * 1024

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        mock_httpx.return_value.__enter__.return_value.put.return_value = mock_response

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "Question text"
        mock_handover.manager_response = "Answer text"
        mock_handover.assigned_to_name = "Test"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None
        mock_alert.assert_called_once()

    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    @patch("app.services.learning_service.alert_error")
    def test_returns_none_on_exception(self, mock_alert, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.side_effect = Exception("Embedding service error")

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "Question text"
        mock_handover.manager_response = "Answer text"
        mock_handover.assigned_to_name = "Test"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None
        mock_alert.assert_called_once()

    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    def test_accepts_status_201(self, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.return_value = [0.1] * 1024

        mock_response = Mock()
        mock_response.status_code = 201
        mock_httpx.return_value.__enter__.return_value.put.return_value = mock_response

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "Question"
        mock_handover.manager_response = "Answer"
        mock_handover.assigned_to_name = "Owner"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is not None

    def test_skips_too_short_texts(self):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "да"
        mock_handover.manager_response = "ок"
        mock_handover.assigned_to_name = "Owner"

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is None

    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    def test_uses_custom_source(self, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.return_value = [0.1] * 1024

        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__enter__.return_value.put.return_value = mock_response

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "Question"
        mock_handover.manager_response = "Answer"
        mock_handover.assigned_to_name = "Owner"

        result = add_to_knowledge(mock_db, mock_handover, source="owner")

        assert result is not None
        # Verify the call was made with correct source
        call_args = mock_httpx.return_value.__enter__.return_value.put.call_args
        assert call_args[1]["json"]["points"][0]["payload"]["metadata"]["source"] == "owner"

    @patch("app.services.learning_service.get_embedding")
    @patch("app.services.learning_service.httpx.Client")
    def test_uses_manager_as_default_learned_from(self, mock_httpx, mock_embedding):
        mock_db = Mock()
        mock_client = Mock()
        mock_client.name = "test_client"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client

        mock_embedding.return_value = [0.1] * 1024

        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__enter__.return_value.put.return_value = mock_response

        mock_handover = Mock()
        mock_handover.id = uuid.uuid4()
        mock_handover.client_id = uuid.uuid4()
        mock_handover.user_message = "Question"
        mock_handover.manager_response = "Answer"
        mock_handover.assigned_to_name = None

        result = add_to_knowledge(mock_db, mock_handover)

        assert result is not None
        call_args = mock_httpx.return_value.__enter__.return_value.put.call_args
        assert call_args[1]["json"]["points"][0]["payload"]["metadata"]["learned_from"] == "manager"
