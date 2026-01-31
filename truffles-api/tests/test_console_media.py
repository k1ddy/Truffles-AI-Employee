import io
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.routers import console as console_router
from app.services import manager_message_service
from app.services.console_errors import ConsoleAPIError


def test_console_media_type_resolution():
    assert console_router._resolve_console_media_type("photo.jpg", "image/jpeg") == "photo"
    assert console_router._resolve_console_media_type("audio.ogg", "audio/ogg") == "audio"
    assert console_router._resolve_console_media_type("doc.pdf", "application/pdf") == "document"


def test_console_media_type_rejects_video():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_console_media_type("clip.mp4", "video/mp4")
    assert getattr(exc_info.value, "code", None) == "MEDIA_TYPE_FORBIDDEN"


@pytest.mark.asyncio
async def test_console_media_upload_outbox_payload(monkeypatch, tmp_path):
    db = SimpleNamespace(commit=lambda: None)
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
    )
    handover = SimpleNamespace(channel_ref=None)
    agent = SimpleNamespace(id=uuid4(), name="Agent")
    upload = UploadFile(
        filename="photo.jpg",
        file=io.BytesIO(b"test"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    captured = {}

    def fake_enqueue_outbox(*_args, **kwargs):
        captured["payload"] = kwargs.get("payload_json")
        return True

    def fake_save_message(**_kwargs):
        return SimpleNamespace(
            id=uuid4(),
            role="manager",
            content="caption",
            created_at=datetime.now(timezone.utc),
            message_metadata={},
        )

    monkeypatch.setattr(manager_message_service, "MEDIA_STORAGE_BASE_DIR", tmp_path)
    monkeypatch.setattr(manager_message_service, "get_client_slug", lambda *_args, **_kwargs: "demo")
    monkeypatch.setattr(manager_message_service, "get_user_remote_jid", lambda *_args, **_kwargs: "777@s.whatsapp.net")
    monkeypatch.setattr(manager_message_service, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(manager_message_service, "_is_env_enabled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        manager_message_service,
        "build_signed_media_url",
        lambda *_args, **_kwargs: "https://example.com/media.jpg?expires=1700000000&sig=abc",
    )
    monkeypatch.setattr(manager_message_service, "enqueue_outbox_message", fake_enqueue_outbox)
    monkeypatch.setattr(manager_message_service, "save_message", fake_save_message)
    monkeypatch.setattr(manager_message_service, "record_audit_event", lambda *_args, **_kwargs: None)

    message, status, error = await manager_message_service.process_console_media_upload(
        db=db,
        conversation=conversation,
        handover=handover,
        agent=agent,
        upload=upload,
        media_type="photo",
        caption="caption",
        idempotency_key="idem-1",
    )

    assert message.role == "manager"
    assert status == "queued"
    assert error is None
    assert captured["payload"]["event_type"] == "whatsapp.send_media"
    assert captured["payload"]["payload"]["media_type"] == "photo"
