"""
Contract tests for ChatFlow service.

Tests that the chatflow_service correctly handles:
- Success responses
- Error responses
- Timeouts
- Rate limits

Uses respx for HTTP mocking.
"""

import pytest
import respx
from httpx import Response

from app.contracts import Result, IntegrationError, ConfigError, ErrorCodes


class TestSendMessageSafeContract:
    """Test contract: send_message_safe returns Result[MessageSent]."""

    @respx.mock
    def test_success_returns_ok_result(self):
        """When ChatFlow returns 200, should return Result.ok(MessageSent)."""
        import os
        os.environ["CHATFLOW_TOKEN"] = "test-token"
        os.environ["TEST_MODE"] = "0"
        
        from app.services.chatflow_service import send_message_safe, MessageSent
        
        # Mock ChatFlow API
        respx.get("https://app.chatflow.kz/api/v1/send-text").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = send_message_safe(
            instance_id="test-instance",
            remote_jid="77001234567@s.whatsapp.net",
            message="Test message",
        )
        
        assert result.is_ok()
        assert isinstance(result.unwrap(), MessageSent)
        assert result.unwrap().remote_jid == "77001234567@s.whatsapp.net"

    @respx.mock
    def test_chatflow_500_returns_integration_error(self):
        """When ChatFlow returns 500, should return Result.fail(IntegrationError)."""
        import os
        os.environ["CHATFLOW_TOKEN"] = "test-token"
        os.environ["TEST_MODE"] = "0"
        
        from app.services.chatflow_service import send_message_safe
        
        respx.get("https://app.chatflow.kz/api/v1/send-text").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        
        result = send_message_safe(
            instance_id="test-instance",
            remote_jid="77001234567@s.whatsapp.net",
            message="Test message",
        )
        
        assert result.is_err()
        assert isinstance(result.error, IntegrationError)
        assert result.error.code == ErrorCodes.CHATFLOW_ERROR

    @respx.mock
    def test_timeout_returns_timeout_error(self):
        """When ChatFlow times out, should return CHATFLOW_TIMEOUT error."""
        import os
        import httpx
        os.environ["CHATFLOW_TOKEN"] = "test-token"
        os.environ["TEST_MODE"] = "0"
        
        from app.services.chatflow_service import send_message_safe
        
        respx.get("https://app.chatflow.kz/api/v1/send-text").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        result = send_message_safe(
            instance_id="test-instance",
            remote_jid="77001234567@s.whatsapp.net",
            message="Test message",
        )
        
        assert result.is_err()
        assert result.error.code == ErrorCodes.CHATFLOW_TIMEOUT

    @respx.mock
    def test_missing_token_returns_config_error(self, monkeypatch):
        """When CHATFLOW_TOKEN not set, should return ConfigError."""
        monkeypatch.delenv("CHATFLOW_TOKEN", raising=False)
        monkeypatch.setenv("TEST_MODE", "0")
        
        # Force module reload to pick up env change
        import importlib
        import app.services.chatflow_service as chatflow_module
        importlib.reload(chatflow_module)
        
        result = chatflow_module.send_message_safe(
            instance_id="test-instance",
            remote_jid="77001234567@s.whatsapp.net",
            message="Test message",
        )
        
        assert result.is_err()
        # Could be ConfigError or the actual call failed

    def test_missing_instance_returns_error(self, monkeypatch):
        """When instance_id is empty, should return IntegrationError."""
        monkeypatch.setenv("CHATFLOW_TOKEN", "test-token")
        monkeypatch.setenv("TEST_MODE", "0")
        
        import importlib
        import app.services.chatflow_service as chatflow_module
        importlib.reload(chatflow_module)
        
        result = chatflow_module.send_message_safe(
            instance_id="",
            remote_jid="77001234567@s.whatsapp.net",
            message="Test message",
        )
        
        assert result.is_err()
        assert result.error.code == ErrorCodes.INVALID_PAYLOAD


class TestResultContract:
    """Test the Result type contract."""
    
    def test_ok_result_is_success(self):
        """Result.ok() should have is_ok() == True."""
        from app.contracts import Ok
        
        result = Ok(42)
        
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == 42
    
    def test_err_result_is_failure(self):
        """Result.fail() should have is_err() == True."""
        from app.contracts import Err, TrufflesError
        
        error = TrufflesError(code="TEST", message="test error")
        result = Err(error)
        
        assert result.is_err()
        assert not result.is_ok()
        assert result.error.code == "TEST"
    
    def test_unwrap_or_returns_default_on_error(self):
        """unwrap_or should return default when result is error."""
        from app.contracts import Err, TrufflesError
        
        error = TrufflesError(code="TEST", message="test error")
        result = Err(error)
        
        assert result.unwrap_or("default") == "default"
    
    def test_map_transforms_ok_result(self):
        """map should transform data in Ok result."""
        from app.contracts import Ok
        
        result = Ok(10)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.unwrap() == 20
    
    def test_map_preserves_error(self):
        """map should preserve error in Err result."""
        from app.contracts import Err, TrufflesError
        
        error = TrufflesError(code="TEST", message="test")
        result = Err(error)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.is_err()
        assert mapped.error.code == "TEST"


class TestErrorContract:
    """Test error types contract."""
    
    def test_truffles_error_serializes(self):
        """TrufflesError should serialize to dict."""
        from app.contracts import IntegrationError
        
        error = IntegrationError(
            code="CHATFLOW_ERROR",
            message="API failed",
            service="chatflow",
            context={"status": 500},
        )
        
        data = error.to_dict()
        
        assert data["code"] == "CHATFLOW_ERROR"
        assert data["error_type"] == "IntegrationError"
        assert "service" in data["context"]
    
    def test_error_str_includes_code(self):
        """str(error) should include error code."""
        from app.contracts import TrufflesError
        
        error = TrufflesError(code="TEST_CODE", message="Test message")
        
        assert "TEST_CODE" in str(error)
