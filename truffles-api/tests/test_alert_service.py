from unittest.mock import MagicMock, Mock, patch

from app.services.alert_service import (
    alert_critical,
    alert_error,
    alert_warning,
    send_alert,
)


class TestSendAlert:
    @patch("app.services.alert_service.ALERT_BOT_TOKEN", None)
    @patch("app.services.alert_service.ALERT_CHAT_ID", None)
    def test_returns_false_when_not_configured(self):
        result = send_alert("ERROR", "Test message")
        assert result is False

    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_sends_alert_to_telegram(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        result = send_alert("ERROR", "Test error message")

        assert result is True
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        assert "api.telegram.org" in call_args[0][0]
        json_data = call_args[1]["json"]
        assert "chat_id" in json_data
        assert "text" in json_data
        assert "ERROR" in json_data["text"]

    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_includes_context_in_message(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        context = {"client_id": "123", "error": "test error"}
        send_alert("ERROR", "Test message", context)

        call_args = mock_client.post.call_args
        json_data = call_args[1]["json"]
        assert "client_id" in json_data["text"]
        assert "123" in json_data["text"]

    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_returns_false_on_telegram_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 400
        mock_client.post.return_value = mock_response

        result = send_alert("ERROR", "Test message")

        assert result is False

    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_returns_false_on_exception(self, mock_client_class):
        mock_client_class.return_value.__enter__.side_effect = Exception("Network error")

        result = send_alert("ERROR", "Test message")

        assert result is False


class TestAlertShortcuts:
    @patch("app.services.alert_service.send_alert")
    def test_alert_error_calls_send_alert_with_error_level(self, mock_send):
        mock_send.return_value = True

        result = alert_error("Test error", {"key": "value"})

        mock_send.assert_called_once_with("ERROR", "Test error", {"key": "value"})
        assert result is True

    @patch("app.services.alert_service.send_alert")
    def test_alert_critical_calls_send_alert_with_critical_level(self, mock_send):
        mock_send.return_value = True

        result = alert_critical("Critical issue")

        mock_send.assert_called_once_with("CRITICAL", "Critical issue", None)
        assert result is True

    @patch("app.services.alert_service.send_alert")
    def test_alert_warning_calls_send_alert_with_warning_level(self, mock_send):
        mock_send.return_value = True

        result = alert_warning("Warning message")

        mock_send.assert_called_once_with("WARNING", "Warning message", None)
        assert result is True


class TestAlertEmojis:
    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_error_has_correct_emoji(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        send_alert("ERROR", "Test")

        json_data = mock_client.post.call_args[1]["json"]
        assert "❌" in json_data["text"]

    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_critical_has_correct_emoji(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        send_alert("CRITICAL", "Test")

        json_data = mock_client.post.call_args[1]["json"]
        assert "🔥" in json_data["text"]
