from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "observability_e2e_turn_truth.py"


def load_module():
    spec = importlib.util.spec_from_file_location("observability_e2e_turn_truth", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_snapshot() -> dict:
    return {
        "post": {"status_code": 200, "payload": {"success": True}},
        "runtime": {"version_valid": True},
        "metrics": {"valid": True},
        "console": {"valid": True},
        "logs": {"valid": True},
        "tempo": {"valid": True},
        "provider": {"valid_for_internal_turn": True},
        "correlation": {
            "trace_id": "abc123",
            "inbound_message_id": "msg-1",
            "outbox_id": "outbox-1",
        },
        "turn_state": {
            "outbox_found": True,
            "outbox": {
                "id": "outbox-1",
                "status": "SENT",
                "inbound_message_id": "msg-1",
                "meta": {
                    "timing": {"process_ms": 12.0},
                    "correlation": {"inbound_message_id": "msg-1", "trace_id": "abc123"},
                },
            },
            "messages": [
                {"role": "user", "decision_meta": {"outbox_enqueue": "enqueued"}},
                {
                    "role": "assistant",
                    "transport_status": "skipped",
                    "decision_meta": {
                        "source": "llm_policy_core",
                        "outcome": "FACT",
                        "action": "fact",
                    },
                    "decision_trace": {"trace_id": "abc123", "stage": "consultant_runtime"},
                    "runtime_trace_contract": {"trace_id": "abc123"},
                },
            ],
        },
    }


def test_evaluate_turn_snapshot_accepts_correlated_turn() -> None:
    module = load_module()

    verdict = module.evaluate_turn_snapshot(_valid_snapshot())

    assert verdict["valid"] is True
    assert verdict["checks"]["outbox_processed"] is True
    assert verdict["checks"]["semantic_owner_source"] == "llm_policy_core"


def test_evaluate_turn_snapshot_rejects_missing_trace_contract() -> None:
    module = load_module()
    snapshot = _valid_snapshot()
    snapshot["turn_state"]["messages"][-1]["runtime_trace_contract"] = {}

    verdict = module.evaluate_turn_snapshot(snapshot)

    assert verdict["valid"] is False
    assert any("runtime_trace_contract is missing" in item for item in verdict["errors"])


def test_extract_correlation_prefers_runtime_trace_and_checks_outbox_meta() -> None:
    module = load_module()
    snapshot = _valid_snapshot()

    correlation = module.extract_correlation(snapshot["turn_state"])

    assert correlation["trace_id"] == "abc123"
    assert correlation["outbox_meta_trace_id"] == "abc123"
    assert correlation["outbox_timing"]["process_ms"] == 12.0
