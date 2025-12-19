from unittest.mock import Mock, patch
from uuid import uuid4

from app.services.ai_service import (
    KNOWLEDGE_CONFIDENCE_THRESHOLD,
    ACKNOWLEDGEMENT_RESPONSE,
    GREETING_RESPONSE,
    LOW_SIGNAL_RESPONSE,
    generate_ai_response,
    get_conversation_history,
    get_system_prompt,
    _sanitize_query_for_rag,
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


class TestSanitizeQueryForRag:
    def test_removes_profanity_and_keeps_meaningful_tokens(self):
        query = "вы работаете сегодня блять?"
        sanitized = _sanitize_query_for_rag(query)
        assert "блять" not in sanitized.lower()
        assert "работаете" in sanitized

    def test_returns_original_when_clean(self):
        query = "сколько стоит маникюр?"
        sanitized = _sanitize_query_for_rag(query)
        assert sanitized == query


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

    @patch("app.services.ai_service.get_llm_provider")
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_contextual_rag_retry_avoids_escalation(self, mock_history, mock_prompt, mock_search, mock_llm):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = [
            {"role": "user", "content": "педикюр интересует"},
            {"role": "assistant", "content": "Какой вид педикюра вас интересует?"},
            {"role": "user", "content": "сколько длится по времени"},
            {"role": "assistant", "content": "Уточните вид педикюра."},
        ]

        def search_side_effect(query: str, client_slug: str, limit: int = 3):
            if query == "классический интересует":
                return [{"score": 0.1, "text": "Weak match"}]
            return [{"score": 0.8, "text": "Relevant info"}]

        mock_search.side_effect = search_side_effect

        mock_response = Mock()
        mock_response.content = "AI generated response"
        mock_llm.return_value.generate.return_value = mock_response

        result = generate_ai_response(mock_db, uuid4(), "demo_salon", uuid4(), "классический интересует")

        assert result.ok is True
        assert result.value[0] == "AI generated response"
        assert result.value[1] in ["medium", "high"]
        mock_llm.return_value.generate.assert_called_once()

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_low_confidence_returns_escalation_flag(self, mock_history, mock_prompt, mock_search):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
        mock_search.return_value = [{"score": 0.49, "text": "Some text"}]  # Below threshold

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
    @patch("app.services.ai_service.get_conversation_history")
    def test_empty_knowledge_returns_escalation_flag(self, mock_history, mock_prompt, mock_search):
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
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

            result = generate_ai_response(mock_db, uuid4(), "test", uuid4(), "Test question?")

            assert result.ok is True
            assert result.value[1] == "medium"

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    def test_score_below_threshold_triggers_escalation(self, mock_prompt, mock_search):
        """Score below threshold should trigger escalation."""
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_search.return_value = [{"score": KNOWLEDGE_CONFIDENCE_THRESHOLD - 0.01, "text": "Info"}]

        result = generate_ai_response(mock_db, uuid4(), "test", uuid4(), "Test question?")

        assert result.ok is True
        assert result.value[1] == "low_confidence"

    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_system_prompt")
    @patch("app.services.ai_service.get_conversation_history")
    def test_whitelisted_message_avoids_escalation(self, mock_history, mock_prompt, mock_search):
        """Greeting/thanks should respond even when knowledge is low."""
        mock_db = Mock()
        mock_prompt.return_value = "You are a helpful assistant"
        mock_history.return_value = []
        mock_search.return_value = []  # No knowledge

        result = generate_ai_response(
            db=mock_db,
            client_id=uuid4(),
            client_slug="test",
            conversation_id=uuid4(),
            user_message="Привет",
        )

        assert result.ok is True
        assert result.value[1] == "medium"
        assert result.value[0] == GREETING_RESPONSE


class TestAckAndLowSignal:
    def test_acknowledgement_does_not_trigger_escalation(self):
        result = generate_ai_response(Mock(), uuid4(), "test", uuid4(), "ок?")

        assert result.ok is True
        assert result.value[1] == "medium"
        assert result.value[0] == ACKNOWLEDGEMENT_RESPONSE

    def test_low_signal_message_returns_clarifying_prompt(self):
        result = generate_ai_response(Mock(), uuid4(), "test", uuid4(), "???")

        assert result.ok is True
        assert result.value[1] == "medium"
        assert result.value[0] == LOW_SIGNAL_RESPONSE
