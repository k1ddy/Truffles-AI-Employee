import pytest
from uuid import uuid4

from app.services.callback_service import (
    handle_take,
    handle_resolve,
    handle_skip,
    handle_return,
    CallbackError,
)
from app.services.state_machine import ConversationState
from app.schemas.callback import CallbackRequest, CallbackResponse


class MockConversation:
    def __init__(self, state="pending"):
        self.id = uuid4()
        self.state = state
        self.human_operator_id = None


class MockHandover:
    def __init__(self):
        self.status = "pending"
        self.assigned_to = None
        self.assigned_to_name = None
        self.first_response_at = None
        self.skipped_by = []


class MockDB:
    def __init__(self, handover=None):
        self._handover = handover
    
    def query(self, model):
        return self
    
    def filter(self, *args):
        return self
    
    def first(self):
        return self._handover


class TestHandleTake:
    def test_take_from_pending(self):
        conv = MockConversation(state="pending")
        db = MockDB(handover=MockHandover())
        
        old, new = handle_take(db, conv, "manager123", "John")
        
        assert old == "pending"
        assert new == "manager_active"
        assert conv.state == "manager_active"
        assert conv.human_operator_id == "manager123"
    
    def test_take_from_wrong_state_fails(self):
        conv = MockConversation(state="bot_active")
        db = MockDB()
        
        with pytest.raises(CallbackError) as exc:
            handle_take(db, conv, "manager123")
        assert "Expected 'pending'" in str(exc.value)


class TestHandleResolve:
    def test_resolve_from_manager_active(self):
        conv = MockConversation(state="manager_active")
        db = MockDB()
        
        old, new = handle_resolve(db, conv, "manager123")
        
        assert old == "manager_active"
        assert new == "bot_active"
        assert conv.state == "bot_active"
    
    def test_resolve_from_wrong_state_fails(self):
        conv = MockConversation(state="pending")
        db = MockDB()
        
        with pytest.raises(CallbackError) as exc:
            handle_resolve(db, conv, "manager123")
        assert "Expected 'manager_active'" in str(exc.value)


class TestHandleSkip:
    def test_skip_does_not_change_state(self):
        conv = MockConversation(state="pending")
        handover = MockHandover()
        db = MockDB(handover=handover)
        
        old, new = handle_skip(db, conv, "manager123")
        
        assert old == "pending"
        assert new == "pending"  # Unchanged
        assert "manager123" in handover.skipped_by


class TestHandleReturn:
    def test_return_from_manager_active(self):
        conv = MockConversation(state="manager_active")
        db = MockDB()
        
        old, new = handle_return(db, conv, "manager123")
        
        assert old == "manager_active"
        assert new == "bot_active"
    
    def test_return_from_wrong_state_fails(self):
        conv = MockConversation(state="pending")
        db = MockDB()
        
        with pytest.raises(CallbackError) as exc:
            handle_return(db, conv, "manager123")
        assert "Expected 'manager_active'" in str(exc.value)


class TestCallbackSchemas:
    def test_callback_request_valid(self):
        req = CallbackRequest(
            conversation_id=uuid4(),
            action="take",
            manager_id="mgr123",
            manager_name="John"
        )
        assert req.action == "take"
    
    def test_callback_request_invalid_action(self):
        with pytest.raises(ValueError):
            CallbackRequest(
                conversation_id=uuid4(),
                action="invalid_action",
                manager_id="mgr123"
            )
    
    def test_callback_response_valid(self):
        resp = CallbackResponse(
            success=True,
            conversation_id=uuid4(),
            action="take",
            old_state="pending",
            new_state="manager_active"
        )
        assert resp.success == True
