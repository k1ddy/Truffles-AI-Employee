from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.knowledge_service import (
    QDRANT_COLLECTION,
    format_knowledge_context,
    get_embedding,
    search_knowledge,
)


class TestQdrantCollection:
    def test_collection_name_is_set(self):
        assert QDRANT_COLLECTION == "truffles_knowledge"


class TestFormatKnowledgeContext:
    def test_returns_empty_string_for_empty_results(self):
        result = format_knowledge_context([])
        assert result == ""

    def test_formats_single_result(self):
        results = [{"text": "Some knowledge", "score": 0.9}]
        result = format_knowledge_context(results)

        assert "Релевантная информация" in result
        assert "1. Some knowledge" in result

    def test_formats_multiple_results(self):
        results = [
            {"text": "First info", "score": 0.9},
            {"text": "Second info", "score": 0.8},
        ]
        result = format_knowledge_context(results)

        assert "1. First info" in result
        assert "2. Second info" in result

    def test_skips_empty_text(self):
        results = [
            {"text": "Valid info", "score": 0.9},
            {"text": "", "score": 0.8},
            {"text": None, "score": 0.7},
        ]
        result = format_knowledge_context(results)

        assert "1. Valid info" in result
        assert "2." not in result


class TestGetEmbedding:
    @patch("app.services.knowledge_service.httpx.Client")
    def test_returns_embedding_from_response(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0.1, 0.2, 0.3]]
        mock_client.post.return_value = mock_response

        result = get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]

    @patch("app.services.knowledge_service.httpx.Client")
    def test_raises_on_error_status(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_client.post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            get_embedding("test text")

        assert "BGE-M3 error" in str(exc_info.value)


class TestSearchKnowledge:
    @patch("app.services.knowledge_service.alert_warning")
    @patch("app.services.knowledge_service.get_embedding")
    @patch("app.services.knowledge_service.httpx.Client")
    def test_returns_empty_list_on_qdrant_error(self, mock_client_class, mock_embedding, mock_alert):
        mock_embedding.return_value = [0.1, 0.2, 0.3]

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Qdrant error"
        mock_client.post.return_value = mock_response

        result = search_knowledge("test query", "test-client")

        assert result == []
        mock_alert.assert_called_once()

    @patch("app.services.knowledge_service.get_embedding")
    @patch("app.services.knowledge_service.httpx.Client")
    def test_returns_formatted_results(self, mock_client_class, mock_embedding):
        mock_embedding.return_value = [0.1, 0.2, 0.3]

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "score": 0.85,
                    "payload": {
                        "content": "Test content",
                        "metadata": {"doc_name": "test.md", "client_slug": "test"},
                    },
                }
            ]
        }
        mock_client.post.return_value = mock_response

        result = search_knowledge("test query", "test-client")

        assert len(result) == 1
        assert result[0]["score"] == 0.85
        assert result[0]["text"] == "Test content"
        assert result[0]["source"] == "test.md"
