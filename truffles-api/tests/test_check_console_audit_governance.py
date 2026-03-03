from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_console_audit_governance.py"
SPEC = importlib.util.spec_from_file_location("check_console_audit_governance", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

build_governance_report = MODULE.build_governance_report


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_governance_report_passes_for_unique_ids_and_gap_tags(tmp_path: Path) -> None:
    canon = _write(
        tmp_path / "canon.md",
        "\n".join(
            [
                "## Sample",
                "- [partial] (gap:integrations_rbac_scope) Integrations access differs from canon. Canon: `SPECS/CONTROL_PLANE.md`.",
                "- [missing] (gap:team_invite_disable) Team invite/disable is not implemented. Canon: `SPECS/CONTROL_PLANE.md`.",
            ]
        ),
    )
    backlog = _write(
        tmp_path / "backlog.md",
        "\n".join(
            [
                "| ID | Priority | Area | Problem | Impact | Evidence | Status |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| UX-11 | P1 | API | Router too large | High blast radius | report | Open |",
                "| UX-12 | P1 | UI | Wizard too large | Slow iteration | report | Open |",
            ]
        ),
    )

    report = build_governance_report(canon_path=canon, backlog_path=backlog)

    assert report["valid"] is True
    assert report["violations"] == []
    assert report["canon"]["missing_gap_tag_total"] == 0
    assert report["backlog"]["tracked_items"] == 2


def test_governance_report_fails_on_duplicate_backlog_ids(tmp_path: Path) -> None:
    canon = _write(
        tmp_path / "canon.md",
        "- [partial] (gap:integrations_rbac_scope) Integrations access differs from canon. Canon: `SPECS/CONTROL_PLANE.md`.\n",
    )
    backlog = _write(
        tmp_path / "backlog.md",
        "\n".join(
            [
                "| ID | Priority | Area | Problem | Impact | Evidence | Status |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| UX-11 | P1 | API | Router too large | High blast radius | report | Open |",
                "| UX-11 | P1 | API | Router too large (duplicate) | High blast radius | report | Open |",
            ]
        ),
    )

    report = build_governance_report(canon_path=canon, backlog_path=backlog)

    assert report["valid"] is False
    violation_types = {item["type"] for item in report["violations"]}
    assert "backlog_duplicate_id" in violation_types


def test_governance_report_fails_on_missing_gap_tag(tmp_path: Path) -> None:
    canon = _write(
        tmp_path / "canon.md",
        "- [partial] Integrations access differs from canon. Canon: `SPECS/CONTROL_PLANE.md`.\n",
    )
    backlog = _write(
        tmp_path / "backlog.md",
        "\n".join(
            [
                "| ID | Priority | Area | Problem | Impact | Evidence | Status |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| UX-11 | P1 | API | Router too large | High blast radius | report | Open |",
            ]
        ),
    )

    report = build_governance_report(canon_path=canon, backlog_path=backlog)

    assert report["valid"] is False
    violation_types = {item["type"] for item in report["violations"]}
    assert "canon_missing_gap_tag" in violation_types


def test_governance_report_fails_on_duplicate_gap_ids(tmp_path: Path) -> None:
    canon = _write(
        tmp_path / "canon.md",
        "\n".join(
                [
                "- [partial] (gap:integrations_rbac_scope) First mention. Canon: `SPECS/CONTROL_PLANE.md`.",
                "- [partial] (gap:integrations_rbac_scope) Second mention. Canon: `SPECS/CONTROL_PLANE.md`.",
                ]
            ),
        )
    backlog = _write(
        tmp_path / "backlog.md",
        "\n".join(
            [
                "| ID | Priority | Area | Problem | Impact | Evidence | Status |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| UX-11 | P1 | API | Router too large | High blast radius | report | Open |",
            ]
        ),
    )

    report = build_governance_report(canon_path=canon, backlog_path=backlog)

    assert report["valid"] is False
    violation_types = {item["type"] for item in report["violations"]}
    assert "canon_duplicate_gap_id" in violation_types
