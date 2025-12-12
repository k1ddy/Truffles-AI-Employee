from unittest.mock import Mock, patch
from uuid import uuid4

from app.services.ai_service import (
    KNOWLEDGE_CONFIDENCE_THRESHOLD,
    generate_ai_response,
    get_conversation_history,
    get_system_prompt,
)
from app.services.result import Result


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

        assert result.ok is True
        assert result.value[0] == "AI generated response"
        assert result.value[1] == "high"
        mock_llm.return_value.generate.assert_called_once()

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_low_confidence_returns_escalation_flag(self, mock_prompt, mock_search):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = [{"score": 0.5, "text": "Some text"}]  # Below threshold

        result = generate_ai_response(
            db=mock_db,
            client_id=uuid4(),
            client_slug="test",
            conversation_id=uuid4(),
            user_message="Test question",
        )

        assert result.ok is True
        assert result.value[0] is None  # No response text
        assert result.value[1] == "low_confidence"

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_empty_knowledge_returns_escalation_flag(self, mock_prompt, mock_search):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = []  # Empty results

        result = generate_ai_response(
            db=mock_db,
            client_id=uuid4(),
            client_slug="test",
            conversation_id=uuid4(),
            user_message="Test question",
        )

        assert result.ok is True
        assert result.value[0] is None
        assert result.value[1] == "low_confidence"

    @patch("app.services.ai_service.alert_error")
    @patch("app.services.ai_service.get_llm_provider")
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_returns_failure_on_exception(self, mock_history, mock_prompt, mock_search, mock_llm, mock_alert):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
        mock_search.return_value = [{"score": 0.85, "text": "Relevant"}]  # High confidence
        mock_llm.return_value.generate.side_effect = Exception("LLM error")

        result = generate_ai_response(mock_db, uuid4(), "test-client", uuid4(), "What is X?")

        assert result.ok is False
        assert result.error_code == "ai_error"
        assert "LLM error" in result.error
        mock_alert.assert_called_once()


class TestLowConfidenceEscalation:
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_score_at_threshold_is_reliable(self, mock_prompt, mock_search):
        """Score exactly at threshold should be considered reliable."""
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = [{"score": KNOWLEDGE_CONFIDENCE_THRESHOLD, "text": "Info"}]

        with patch("app.services.ai_service.get_llm_provider") as mock_llm, \
             patch("app.services.ai_service.get_conversation_history") as mock_history:
            mock_history.return_value = []
            mock_response = Mock()
            mock_response.content = "Response"
            mock_llm.return_value.generate.return_value = mock_response

            result = generate_ai_response(mock_db, uuid4(), "test", uuid4(), "Q?")

            assert result.ok is True
            assert result.value[1] == "high"

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_score_below_threshold_triggers_escalation(self, mock_prompt, mock_search):
        """Score below threshold should trigger escalation."""
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = [{"score": KNOWLEDGE_CONFIDENCE_THRESHOLD - 0.01, "text": "Info"}]

        result = generate_ai_response(mock_db, uuid4(), "test", uuid4(), "Q?")

        assert result.ok is True
        assert result.value[1] == "low_confidence"
