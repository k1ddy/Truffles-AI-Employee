from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas.consult import (
    ConsultControllerOutput,
    ConsultPlaybook,
    validate_consult_controller_output,
    validate_consult_playbook,
)


def _load_generic_pack() -> dict:
    base_dir = Path(__file__).resolve().parents[1]
    path = base_dir / "app" / "knowledge" / "generic" / "CONSULT_PLAYBOOK.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def test_consult_playbook_generic_valid() -> None:
    payload = _load_generic_pack()
    model, error = validate_consult_playbook(payload)
    assert error is None
    assert isinstance(model, ConsultPlaybook)
    assert model.version == "v1"
    assert model.topics


def test_consult_controller_output_valid() -> None:
    payload = {
        "intent": "consult",
        "topic_id": "general_guidance",
        "confidence": 0.84,
        "risk_class": "low",
        "actions": ["answer"],
        "slots": {"goal": "understand options"},
    }
    model, error = validate_consult_controller_output(payload)
    assert error is None
    assert isinstance(model, ConsultControllerOutput)
