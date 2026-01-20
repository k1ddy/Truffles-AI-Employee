from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.models import Branch, Client, ClientSettings
from app.routers.webhook.branch_selection import _handle_branch_selection_gate
from app.routers.webhook.http import _run_preflight
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.chatflow_service import get_instance_id
from app.services.conversation_service import get_or_create_conversation
from app.services.state_machine import ConversationState


def test_instance_id_overrides_existing_branch():
    client_id = uuid4()
    branch_a_id = uuid4()
    branch_b_id = uuid4()

    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_a_id,
        context={},
        state=ConversationState.BOT_ACTIVE.value,
    )
    user = SimpleNamespace(user_metadata={})
    settings = SimpleNamespace(branch_resolution_mode="hybrid", remember_branch_preference=True)
    metadata = SimpleNamespace(instanceId="instance-b")
    branch_b = SimpleNamespace(
        id=branch_b_id,
        client_id=client_id,
        instance_id="instance-b",
        is_active=True,
        name="Branch B",
        slug="branch_b",
    )

    query = Mock()
    query.filter.return_value.first.return_value = branch_b
    db = Mock()
    db.query.return_value = query

    result = _handle_branch_selection_gate(
        db=db,
        client_id=client_id,
        settings=settings,
        conversation=conversation,
        user=user,
        metadata=metadata,
        message_text="hello",
        now=datetime.now(timezone.utc),
        send_and_save=Mock(return_value=("ok", True)),
    )

    assert result is None
    assert conversation.branch_id == branch_b_id
    assert user.user_metadata.get("branch_id") == str(branch_b_id)


def test_get_instance_id_prefers_branch_id():
    client_id = uuid4()
    branch_id = uuid4()

    branch = SimpleNamespace(id=branch_id, client_id=client_id, instance_id="inst-branch")
    client = SimpleNamespace(id=client_id, config={"instance_id": "inst-client"})

    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = branch
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client

    db = Mock()
    db.query.side_effect = [branch_query, client_query]

    instance_id = get_instance_id(db, client_id, branch_id=branch_id)

    assert instance_id == "inst-branch"


def test_preflight_rejects_missing_instance_id_by_instance():
    client = SimpleNamespace(id=uuid4(), name="demo_salon")
    settings = SimpleNamespace(branch_resolution_mode="by_instance", webhook_secret=None)

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    branch_query = Mock()
    branch_query.filter.return_value.all.return_value = []

    def _query_side_effect(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Branch or getattr(model, "key", None) == "phone":
            return branch_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query_side_effect
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(remoteJid="77000000000@s.whatsapp.net"),
        ),
    )

    response, preflight_payload = _run_preflight(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=None,
        resolve_trace_conversation=lambda **_: None,
        record_early_trace=lambda *args, **kwargs: False,
    )

    assert response is not None
    assert response.success is False
    assert response.message == "Missing instanceId"
    assert preflight_payload == {}


def test_preflight_rejects_unknown_instance_id_hybrid():
    client = SimpleNamespace(id=uuid4(), name="demo_salon")
    settings = SimpleNamespace(branch_resolution_mode="hybrid", webhook_secret=None)

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_query.filter.return_value.all.return_value = []

    def _query_side_effect(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Branch or getattr(model, "key", None) == "phone":
            return branch_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query_side_effect
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                instanceId="unknown",
            ),
        ),
    )

    response, preflight_payload = _run_preflight(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=None,
        resolve_trace_conversation=lambda **_: None,
        record_early_trace=lambda *args, **kwargs: False,
    )

    assert response is not None
    assert response.success is False
    assert response.message == "Unknown instanceId"
    assert preflight_payload == {}


def test_preflight_resolves_branch_instance_id():
    client = SimpleNamespace(id=uuid4(), name="demo_salon")
    settings = SimpleNamespace(branch_resolution_mode="by_instance", webhook_secret=None)
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        instance_id="inst-123",
        knowledge_tag="branch-tag",
        is_active=True,
    )

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = branch
    branch_query.filter.return_value.all.return_value = []

    def _query_side_effect(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Branch or getattr(model, "key", None) == "phone":
            return branch_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query_side_effect
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                instanceId="inst-123",
            ),
        ),
    )

    response, preflight_payload = _run_preflight(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=None,
        resolve_trace_conversation=lambda **_: None,
        record_early_trace=lambda *args, **kwargs: False,
    )

    assert response is None
    assert preflight_payload.get("resolved_branch_id") == branch.id
    assert preflight_payload.get("resolved_knowledge_tag") == "branch-tag"


def test_preflight_drops_branch_sender():
    client = SimpleNamespace(id=uuid4(), name="demo_salon")
    settings = SimpleNamespace(branch_resolution_mode="by_instance", webhook_secret=None)
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        instance_id="inst-123",
        knowledge_tag=None,
        is_active=True,
        phone="+77055740455",
    )

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    branch_query = Mock()
    branch_query.filter.return_value.all.return_value = [(branch.phone,)]

    def _query_side_effect(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Branch or getattr(model, "key", None) == "phone":
            return branch_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query_side_effect
    db.commit = Mock()

    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(remoteJid="77055740455@s.whatsapp.net"),
        ),
    )

    response, preflight_payload = _run_preflight(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=None,
        resolve_trace_conversation=lambda **_: None,
        record_early_trace=lambda *args, **kwargs: False,
    )

    assert response is not None
    assert response.success is True
    assert response.message == "Ignored branch sender"
    assert preflight_payload == {}


def test_get_or_create_conversation_sets_branch_id():
    client_id = uuid4()
    user_id = uuid4()
    branch_id = uuid4()

    query = Mock()
    query.filter.return_value.first.return_value = None
    db = Mock()
    db.query.return_value = query
    db.add = Mock()
    db.flush = Mock()

    conversation = get_or_create_conversation(
        db,
        client_id,
        user_id,
        "whatsapp",
        branch_id=branch_id,
    )

    assert conversation.branch_id == branch_id
