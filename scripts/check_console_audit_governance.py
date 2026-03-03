#!/usr/bin/env python3
"""Fail-closed governance checks for console audit canonical docs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CANON_GAP_RE = re.compile(r"^- \[(?P<status>partial|missing)\]\s*(?:\(gap:(?P<gap_id>[a-z0-9][a-z0-9_-]*)\))?\s*(?P<body>.*)$")
BACKLOG_ID_RE = re.compile(r"^UX-\d+$")


def _is_table_separator_line(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    return all(part.strip(" -:") == "" for part in stripped.split("|"))


def _split_markdown_row(line: str) -> list[str]:
    raw = line.strip()
    if not (raw.startswith("|") and raw.endswith("|")):
        return []
    return [cell.strip() for cell in raw[1:-1].split("|")]


def _parse_canon(canon_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    partial_missing_entries: list[dict[str, Any]] = []
    missing_gap_tag_lines: list[int] = []

    for lineno, line in enumerate(canon_path.read_text(encoding="utf-8").splitlines(), start=1):
        match = CANON_GAP_RE.match(line)
        if not match:
            continue
        # Skip legend bullets; governance entries are canon-mapped statements.
        if "Canon:" not in line:
            continue
        gap_id = match.group("gap_id")
        body = (match.group("body") or "").strip()
        status = match.group("status")
        if not gap_id:
            missing_gap_tag_lines.append(lineno)
            continue
        partial_missing_entries.append(
            {
                "line": lineno,
                "status": status,
                "gap_id": gap_id,
                "body": body,
            }
        )

    violations: list[dict[str, Any]] = []
    if missing_gap_tag_lines:
        violations.append(
            {
                "type": "canon_missing_gap_tag",
                "lines": missing_gap_tag_lines,
            }
        )

    gap_counter = Counter(entry["gap_id"] for entry in partial_missing_entries)
    duplicate_gap_ids = sorted(gap_id for gap_id, count in gap_counter.items() if count > 1)
    if duplicate_gap_ids:
        details = {
            gap_id: [entry["line"] for entry in partial_missing_entries if entry["gap_id"] == gap_id]
            for gap_id in duplicate_gap_ids
        }
        violations.append(
            {
                "type": "canon_duplicate_gap_id",
                "gap_ids": duplicate_gap_ids,
                "details": details,
            }
        )

    summary = {
        "path": str(canon_path),
        "partial_missing_total": len(partial_missing_entries) + len(missing_gap_tag_lines),
        "tagged_total": len(partial_missing_entries),
        "missing_gap_tag_total": len(missing_gap_tag_lines),
        "unique_gap_ids": len(gap_counter),
    }
    return summary, violations


def _parse_backlog(backlog_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lines = backlog_path.read_text(encoding="utf-8").splitlines()
    in_table = False
    data_rows: list[dict[str, Any]] = []
    malformed_rows: list[int] = []

    for lineno, line in enumerate(lines, start=1):
        if not in_table:
            if line.strip().startswith("| ID |"):
                in_table = True
            continue

        if _is_table_separator_line(line):
            continue

        if not line.strip().startswith("|"):
            if data_rows:
                break
            continue

        row = _split_markdown_row(line)
        if len(row) < 7:
            malformed_rows.append(lineno)
            continue

        item_id = row[0]
        if not BACKLOG_ID_RE.match(item_id):
            continue

        data_rows.append(
            {
                "line": lineno,
                "id": item_id,
                "status": row[6],
                "area": row[2],
                "problem": row[3],
            }
        )

    violations: list[dict[str, Any]] = []
    if malformed_rows:
        violations.append(
            {
                "type": "backlog_malformed_rows",
                "lines": malformed_rows,
            }
        )

    id_counter = Counter(row["id"] for row in data_rows)
    duplicate_ids = sorted(item_id for item_id, count in id_counter.items() if count > 1)
    if duplicate_ids:
        details = {
            item_id: [row["line"] for row in data_rows if row["id"] == item_id]
            for item_id in duplicate_ids
        }
        violations.append(
            {
                "type": "backlog_duplicate_id",
                "ids": duplicate_ids,
                "details": details,
            }
        )

    open_ids = sorted(row["id"] for row in data_rows if "open" in row["status"].lower())
    summary = {
        "path": str(backlog_path),
        "tracked_items": len(data_rows),
        "unique_ids": len(id_counter),
        "open_total": len(open_ids),
        "open_ids": open_ids,
    }
    return summary, violations


def build_governance_report(canon_path: Path, backlog_path: Path) -> dict[str, Any]:
    canon_summary, canon_violations = _parse_canon(canon_path)
    backlog_summary, backlog_violations = _parse_backlog(backlog_path)

    violations = canon_violations + backlog_violations
    return {
        "valid": not violations,
        "canon": canon_summary,
        "backlog": backlog_summary,
        "violations": violations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check console audit governance consistency")
    parser.add_argument(
        "--canon",
        default="docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md",
        help="Path to canonical comparison markdown",
    )
    parser.add_argument(
        "--backlog",
        default="docs/CONSOLE_AUDIT/UX_BACKLOG.md",
        help="Path to UX backlog markdown",
    )
    parser.add_argument("--output", help="Optional JSON output file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canon_path = Path(args.canon)
    backlog_path = Path(args.backlog)

    report = build_governance_report(canon_path=canon_path, backlog_path=backlog_path)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))

    if report["valid"]:
        return 0

    print("Console audit governance check failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
