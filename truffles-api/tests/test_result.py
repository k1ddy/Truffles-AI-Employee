from app.services.result import Result


class TestResultSuccess:
    def test_success_creates_ok_result(self):
        result = Result.success("test value")
        assert result.ok is True
        assert result.value == "test value"
        assert result.error is None

    def test_success_with_different_types(self):
        int_result = Result.success(42)
        assert int_result.value == 42

        dict_result = Result.success({"key": "value"})
        assert dict_result.value == {"key": "value"}


class TestResultFailure:
    def test_failure_creates_not_ok_result(self):
        result = Result.failure("Something went wrong", "test_error")
        assert result.ok is False
        assert result.error == "Something went wrong"
        assert result.error_code == "test_error"
        assert result.value is None

    def test_failure_default_code(self):
        result = Result.failure("Error message")
        assert result.error_code == "unknown"


class TestResultUnwrapOr:
    def test_unwrap_or_returns_value_on_success(self):
        result = Result.success("actual value")
        assert result.unwrap_or("default") == "actual value"

    def test_unwrap_or_returns_default_on_failure(self):
        result = Result.failure("Error", "code")
        assert result.unwrap_or("default") == "default"

    def test_unwrap_or_with_none_value(self):
        result = Result.success(None)
        assert result.unwrap_or("default") is None


class TestErrorCodes:
    def test_ai_error_code(self):
        result = Result.failure("LLM не ответил", "ai_error")
        assert result.error_code == "ai_error"

    def test_rag_error_code(self):
        result = Result.failure("Qdrant недоступен", "rag_error")
        assert result.error_code == "rag_error"

    def test_escalation_error_code(self):
        result = Result.failure("Не удалось эскалировать", "escalation_error")
        assert result.error_code == "escalation_error"

    def test_db_error_code(self):
        result = Result.failure("PostgreSQL недоступен", "db_error")
        assert result.error_code == "db_error"
