from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas.consult import validate_consult_playbook
from app.services.consult_pack_service import build_consult_pack_reply, get_consult_topic
from app.services.knowledge_service import resolve_consult_topic_candidates


def _load_generic_playbook():
    base_dir = Path(__file__).resolve().parents[1]
    path = base_dir / "app" / "knowledge" / "generic" / "CONSULT_PLAYBOOK.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    model, error = validate_consult_playbook(payload if isinstance(payload, dict) else {})
    assert error is None
    return model


def test_build_consult_pack_reply_uses_allowed_advice() -> None:
    playbook = _load_generic_playbook()
    topic = get_consult_topic(playbook, "general_guidance")
    assert topic is not None
    decision = build_consult_pack_reply(
        playbook=playbook,
        topic_id=topic.id,
        conversation_id="conv-1",
        consult_question="need help",
    )
    assert decision is not None
    assert decision.response
    assert any(advice in decision.response for advice in topic.allowed_advice)
    meta = decision.meta or {}
    assert meta.get("consult_topic_id") == topic.id
    assert meta.get("consult_playbook_id") == topic.id


def test_resolve_consult_topic_candidates_stub_embedding() -> None:
    playbook = _load_generic_playbook()

    def _stub_embed(text: str):
        lower = text.lower()
        if "safety" in lower:
            return [1.0, 0.0]
        return [0.0, 1.0]

    candidates = resolve_consult_topic_candidates(
        "safety concern",
        playbook.topics,
        client_slug="generic",
        embedding_fn=_stub_embed,
        top_k=2,
    )
    assert candidates
    assert candidates[0]["topic_id"] == "safety_check"
