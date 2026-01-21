import unittest
from unittest.mock import MagicMock, patch

from app.adapters.chatflow import ChatFlowAdapter
from app.contracts import ErrorCodes
from app.ports.messaging import MessageOptions


class TestChatFlowAdapter(unittest.TestCase):
    def test_instantiation(self):
        adapter = ChatFlowAdapter()
        self.assertIsNotNone(adapter)

    @patch("app.services.chatflow_service.send_message_safe")
    def test_send_text_success(self, mock_send):
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True

        class MockData:
            remote_jid = "123"
            instance_id = "inst_1"
            message_id = "id1"

        mock_result.unwrap.return_value = MockData()
        mock_send.return_value = mock_result

        adapter = ChatFlowAdapter()
        options = MessageOptions(instance_id="inst_1", idempotency_key="id1")
        result = adapter.send_text("123", "hello", options)

        self.assertTrue(result.is_ok())
        val = result.unwrap()
        self.assertEqual(val.remote_jid, "123")
        self.assertEqual(val.provider_response["instance_id"], "inst_1")
        self.assertEqual(val.message_id, "id1")

        mock_send.assert_called_once_with(
            instance_id="inst_1",
            remote_jid="123",
            message="hello",
            idempotency_key="id1",
        )

    @patch("app.services.chatflow_service.send_message_safe")
    def test_send_text_missing_instance_id(self, mock_send):
        adapter = ChatFlowAdapter()
        options = MessageOptions(instance_id=None)
        result = adapter.send_text("123", "hello", options)

        self.assertTrue(result.is_err())
        self.assertEqual(result.error.code, ErrorCodes.CONFIG_MISSING)
        mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
