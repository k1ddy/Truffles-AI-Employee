from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "ops" / "platform_admin_remediation_assist.py"
SPEC = importlib.util.spec_from_file_location("platform_admin_remediation_assist", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - guard for broken runtime
    raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


build_remediation_plan = MODULE.build_remediation_plan
build_brief = MODULE.build_brief


def _snapshot(*, status: str, incident_class: str, reason: str = "provider unavailable") -> dict:
    return {
        "runtime": {
            "guards": {
                "outbox": {
                    "status": status,
                    "incident_class": incident_class,
                    "guidance": ["guidance-line"],
                    "reason_breakdown": {
                        "rows": [
                            {
                                "status": "FAILED",
                                "class": "unexpected_failure",
                                "reason": reason,
                                "count": 7,
                            }
                        ]
                    },
                }
            }
        }
    }


def test_runtime_critical_builds_blocked_plan_with_ops_jobs() -> None:
    snapshot = _snapshot(status="critical", incident_class="runtime_incident")

    plan = build_remediation_plan(snapshot, run_id="r1", source_snapshot="/tmp/kpi.json")

    assert plan["decision"]["rollout"] == "blocked"
    assert len(plan["ops_jobs"]) == 2
    assert plan["ops_jobs"][0]["payload"]["mode"] == "dry_run"
    assert plan["ops_jobs"][1]["payload"]["mode"] == "execute"
    assert any(action["id"] == "run_outbox_dry_run_first" for action in plan["actions"])


def test_external_block_keeps_runtime_execute_out_of_plan() -> None:
    snapshot = _snapshot(status="critical", incident_class="external_block_only", reason="billing blocked")

    plan = build_remediation_plan(snapshot, run_id="r2", source_snapshot="/tmp/kpi.json")

    assert plan["decision"]["rollout"] == "caution"
    assert plan["ops_jobs"] == []
    assert any(action["id"] == "escalate_billing_provider" for action in plan["actions"])


def test_ok_status_produces_observe_only_plan_and_brief() -> None:
    snapshot = _snapshot(status="ok", incident_class="none")

    plan = build_remediation_plan(snapshot, run_id="r3", source_snapshot="/tmp/kpi.json")
    brief = build_brief(plan)

    assert plan["decision"]["rollout"] == "proceed"
    assert plan["ops_jobs"] == []
    assert "Что делать сейчас" in brief
    assert "Проверить целостность среды" in brief
