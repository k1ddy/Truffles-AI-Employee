from unittest.mock import Mock, patch
from uuid import uuid4

from app.services.ai_service import (
    KNOWLEDGE_CONFIDENCE_THRESHOLD,
    generate_ai_response,
    get_conversation_history,
    get_system_prompt,
)


class TestKnowledgeConfidenceThreshold:
    def test_threshold_is_reasonable(self):
        assert 0.5 <= KNOWLEDGE_CONFIDENCE_THRESHOLD <= 0.9

    def test_threshold_is_float(self):
        assert isinstance(KNOWLEDGE_CONFIDENCE_THRESHOLD, float)


class TestGetSystemPrompt:
    def test_returns_prompt_text_when_found(self):
        mock_db = Mock()
        mock_prompt = Mock()
        mock_prompt.text = "Test system prompt"
        mock_db.query().filter().first.return_value = mock_prompt

        result = get_system_prompt(mock_db, uuid4())

        assert result == "Test system prompt"

    def test_returns_none_when_not_found(self):
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        result = get_system_prompt(mock_db, uuid4())

        assert result is None


class TestGetConversationHistory:
    def test_returns_empty_list_for_no_messages(self):
        mock_db = Mock()
        mock_db.query().filter().order_by().limit().all.return_value = []

        result = get_conversation_history(mock_db, uuid4())

        assert result == []

    def test_converts_messages_to_history_format(self):
        mock_db = Mock()
        msg1 = Mock(role="user", content="Hello")
        msg2 = Mock(role="assistant", content="Hi there")
        mock_db.query().filter().order_by().limit().all.return_value = [msg2, msg1]

        result = get_conversation_history(mock_db, uuid4())

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_skips_system_messages(self):
        mock_db = Mock()
        msg1 = Mock(role="system", content="System instruction")
        msg2 = Mock(role="user", content="Hello")
        mock_db.query().filter().order_by().limit().all.return_value = [msg2, msg1]

        result = get_conversation_history(mock_db, uuid4())

        assert len(result) == 1
        assert result[0]["role"] == "user"


class TestGenerateAIResponse:
    @patch("app.services.ai_service.get_llm_provider")
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_generates_response_with_reliable_knowledge(self, mock_history, mock_prompt, mock_search, mock_llm):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
        mock_search.return_value = [{"score": 0.85, "text": "Relevant info"}]

        mock_response = Mock()
        mock_response.content = "AI generated response"
        mock_llm.return_value.generate.return_value = mock_response

        result = generate_ai_response(mock_db, uuid4(), "test-client", uuid4(), "What is X?")

        assert result == "AI generated response"
        mock_llm.return_value.generate.assert_called_once()

    @patch("app.services.ai_service.get_llm_provider")
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_instructs_escalation_when_low_confidence(self, mock_history, mock_prompt, mock_search, mock_llm):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
        mock_search.return_value = [{"score": 0.3, "text": "Low relevance"}]

        mock_response = Mock()
        mock_response.content = "Let me check with colleagues"
        mock_llm.return_value.generate.return_value = mock_response

        result = generate_ai_response(mock_db, uuid4(), "test-client", uuid4(), "What is X?")

        assert result == "Let me check with colleagues"

        call_args = mock_llm.return_value.generate.call_args
        messages = call_args[0][0]
        system_content = messages[0]["content"]
        assert "уточнишь у коллег" in system_content

    @patch("app.services.ai_service.alert_error")
    @patch("app.services.ai_service.get_llm_provider")
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_returns_error_message_on_exception(self, mock_prompt, mock_search, mock_llm, mock_alert):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = []
        mock_llm.return_value.generate.side_effect = Exception("LLM error")

        result = generate_ai_response(mock_db, uuid4(), "test-client", uuid4(), "What is X?")

        assert "ошибка" in result.lower()
        mock_alert.assert_called_once()
