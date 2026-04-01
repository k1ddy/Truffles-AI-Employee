from types import SimpleNamespace
from uuid import uuid4

from app.services.audit_service import AuditEvent, list_audit_events, record_audit_event


def test_list_audit_events_filters_by_client_id():
    client_id = uuid4()
    db = SimpleNamespace()
    query = SimpleNamespace()

    captured = {}

    def _filter(expr):
        captured["expr"] = expr
        return query

    query.filter = _filter
    query.order_by = lambda *_args, **_kwargs: query
    query.offset = lambda *_args, **_kwargs: query
    query.limit = lambda *_args, **_kwargs: query
    query.all = lambda: []
    db.query = lambda model: query

    rows = list_audit_events(db, client_id=client_id, limit=25, offset=5)

    assert rows == []
    expr = captured["expr"]
    assert getattr(expr.left, "name", None) == "client_id"
    assert getattr(expr.right, "value", None) == client_id


def test_record_audit_event_resolves_actor_tenant_fields():
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    actor = SimpleNamespace(id=actor_id, name="Agent", client_id=client_id, branch_id=branch_id)

    captured = {}

    class _DB:
        def add(self, event):
            captured["event"] = event

    db = _DB()
    event = record_audit_event(db, actor=actor, event_type="test.event")

    assert event is captured["event"]
    assert isinstance(event, AuditEvent)
    assert event.client_id == client_id
    assert event.branch_id == branch_id
    assert event.actor_id == actor_id
