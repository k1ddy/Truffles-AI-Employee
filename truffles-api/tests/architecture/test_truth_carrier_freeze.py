from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def test_truth_carrier_freeze_inventory_materializes_guard_contract() -> None:
    truth = _load_yaml("docs/SOURCE_OF_TRUTH.yaml")
    inventory = _load_json(truth["compatibility_carrier_inventory"])
    legacy = _load_yaml(truth["legacy_sunset"])

    assert inventory["schema_version"] == "v3"
    assert inventory["status"] == "machine_readable_system_reproof_base"
    assert inventory["active_block"] == "Consultant Core Block H.1B — File Replay Scenario Contract Materialization"
    assert inventory["freeze_guard"]["allowed_new_writer_paths"] == [
        "truffles-api/app/core/dialog_state_service.py"
    ]
    assert set(inventory["freeze_guard"]["guarded_context_tokens"]) == set(
        legacy["continuity_guard"]["guarded_tokens"]
    )
    assert inventory["reader_precedence_law"]["default_order"]


def test_truth_carrier_freeze_inventory_covers_booking_resume_queue_and_aux_flags() -> None:
    truth = _load_yaml("docs/SOURCE_OF_TRUTH.yaml")
    inventory = _load_json(truth["compatibility_carrier_inventory"])
    carriers = {item["carrier_id"]: item for item in inventory["carriers"]}

    assert {
        "consultant_runtime.booking_payload",
        "context.booking",
        "pending_resume",
        "intent_queue_and_service_hints",
        "handover_confirmation",
        "reengage_confirmation",
        "asr_confirm_pending",
        "asr_inflight",
        "style_reference_pending",
        "memory_profile",
        "memory_pending",
    }.issubset(carriers)
    assert carriers["context.booking"]["guarded_context_tokens"] == ["booking"]
    assert set(carriers["intent_queue_and_service_hints"]["guarded_context_tokens"]) == {
        "intent_queue",
        "last_service_hint",
        "last_service_hint_at",
        "re_entry_required",
    }
    assert carriers["handover_confirmation"]["allowed_future_write_paths"] == [
        "truffles-api/app/core/dialog_state_service.py"
    ]
    assert carriers["style_reference_pending"]["confidence"] == "high"


def test_truth_carrier_freeze_entries_have_precedence_and_expiry() -> None:
    truth = _load_yaml("docs/SOURCE_OF_TRUTH.yaml")
    inventory = _load_json(truth["compatibility_carrier_inventory"])
    freeze_tokens = set(inventory["freeze_guard"]["guarded_context_tokens"])

    for entry in inventory["carriers"]:
        assert entry["writer_precedence"]
        assert entry["reader_precedence"]
        assert entry["allowed_future_write_paths"]
        assert entry["expiry_trigger"]
        assert set(entry["guarded_context_tokens"]).issubset(freeze_tokens)
        assert entry["confidence"] == "high"
