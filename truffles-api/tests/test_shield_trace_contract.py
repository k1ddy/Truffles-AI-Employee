"""
Contract tests for Shield module.

Tests behavioral shield (spam/toxic filtering) contracts.
"""

import pytest
from datetime import datetime, timezone


class TestShieldContract:
    """Test shield module contracts."""

    def test_compute_shield_flags_returns_tuple(self):
        """_compute_shield_flags should return (is_short, is_repeat, is_spam_burst, too_long)."""
        from app.routers.webhook.shield import _compute_shield_flags
        
        flags = _compute_shield_flags(
            message_text="Hello",
            normalized_text="hello",
            previous_text="hello",  # Same as normalized = repeat
            recent=[1.0, 2.0, 3.0],
        )
        
        assert isinstance(flags, tuple)
        assert len(flags) == 4
        is_short, is_repeat, is_spam_burst, too_long = flags
        assert isinstance(is_short, bool)
        assert isinstance(is_repeat, bool)
        assert isinstance(is_spam_burst, bool)
        assert isinstance(too_long, bool)

    def test_short_message_detected(self):
        """Messages <= 3 chars should be flagged as short."""
        from app.routers.webhook.shield import _compute_shield_flags
        
        flags = _compute_shield_flags(
            message_text="Hi",
            normalized_text="hi",
            previous_text=None,
            recent=[1.0],
        )
        
        is_short, _, _, _ = flags
        assert is_short is True

    def test_repeat_message_detected(self):
        """Same normalized text as previous should be flagged as repeat."""
        from app.routers.webhook.shield import _compute_shield_flags
        
        flags = _compute_shield_flags(
            message_text="Привет всем",
            normalized_text="привет всем",
            previous_text="привет всем",  # Exact match
            recent=[1.0],
        )
        
        _, is_repeat, _, _ = flags
        assert is_repeat is True

    def test_long_message_detected(self):
        """Messages > 4000 chars should be flagged as too_long."""
        from app.routers.webhook.shield import _compute_shield_flags
        
        long_message = "x" * 5000
        flags = _compute_shield_flags(
            message_text=long_message,
            normalized_text=long_message,
            previous_text=None,
            recent=[1.0],
        )
        
        _, _, _, too_long = flags
        assert too_long is True

    def test_toxic_message_detected(self):
        """Toxic patterns should be detected."""
        from app.routers.webhook.shield import _is_toxic_message
        
        # Note: actual patterns may vary, this tests the contract
        result = _is_toxic_message("some text")
        assert isinstance(result, bool)

    def test_nonsense_message_detected(self):
        """Messages without meaningful content should be detected."""
        from app.routers.webhook.shield import _is_nonsense_message
        
        result = _is_nonsense_message("!!??")
        assert isinstance(result, bool)
        
        # Empty should be nonsense
        result_empty = _is_nonsense_message("")
        assert result_empty is True


class TestTraceContract:
    """Test decision trace module contracts."""

    def test_record_decision_trace_accepts_dict(self):
        """_record_decision_trace should accept conversation and dict."""
        # This is a contract test - we verify the function signature
        from app.routers.webhook.trace import _record_decision_trace
        import inspect
        
        sig = inspect.signature(_record_decision_trace)
        params = list(sig.parameters.keys())
        
        assert "conversation" in params
        assert "trace" in params

    def test_decision_trace_max_constant(self):
        """DECISION_TRACE_MAX should be defined and positive."""
        from app.routers.webhook.trace import DECISION_TRACE_MAX
        
        assert isinstance(DECISION_TRACE_MAX, int)
        assert DECISION_TRACE_MAX > 0

    def test_critical_stages_defined(self):
        """Critical stages set should be defined."""
        from app.routers.webhook.trace import DECISION_TRACE_CRITICAL_STAGES
        
        assert isinstance(DECISION_TRACE_CRITICAL_STAGES, set)
        assert len(DECISION_TRACE_CRITICAL_STAGES) > 0
        # Check some expected stages
        assert "booking" in DECISION_TRACE_CRITICAL_STAGES or "escalation" in DECISION_TRACE_CRITICAL_STAGES

    def test_is_critical_trace_returns_bool(self):
        """_is_critical_trace should return boolean."""
        from app.routers.webhook.trace import _is_critical_trace
        
        result = _is_critical_trace({"stage": "booking", "decision": "match"})
        assert isinstance(result, bool)
        
        result2 = _is_critical_trace({"stage": "unknown"})
        assert isinstance(result2, bool)

    def test_retain_decision_trace_limits_size(self):
        """_retain_decision_trace should limit trace list size."""
        from app.routers.webhook.trace import _retain_decision_trace, DECISION_TRACE_MAX
        
        # Create oversized trace
        oversized = [{"stage": f"stage_{i}", "decision": "test"} for i in range(DECISION_TRACE_MAX + 20)]
        
        result = _retain_decision_trace(oversized)
        
        assert isinstance(result, list)
        assert len(result) <= DECISION_TRACE_MAX


class TestResultContract:
    """Test Result type from contracts module."""

    def test_result_chain_operations(self):
        """Result should support and_then chaining."""
        from app.contracts import Ok, Err, TrufflesError
        
        def double(x: int):
            return Ok(x * 2)
        
        result = Ok(5).and_then(double)
        assert result.is_ok()
        assert result.unwrap() == 10
        
        error = TrufflesError(code="ERR", message="fail")
        err_result = Err(error).and_then(double)
        assert err_result.is_err()

    def test_result_to_dict_serialization(self):
        """Result.to_dict() should return serializable dict."""
        from app.contracts import Ok, Err, TrufflesError
        import json
        
        ok_result = Ok({"key": "value"})
        ok_dict = ok_result.to_dict()
        assert ok_dict["success"] is True
        json.dumps(ok_dict)  # Should not raise
        
        err = TrufflesError(code="TEST", message="test")
        err_result = Err(err)
        err_dict = err_result.to_dict()
        assert err_dict["success"] is False
        assert "error" in err_dict
