#!/usr/bin/env python3
"""Build a compact quality digest from llm-quality artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PRICE_RE = re.compile(r"(цена|стоим|скольк|прайс|почем|how much|price)", re.IGNORECASE)
PARKING_RE = re.compile(r"(парков|паркинг|стоян|тұрақ)", re.IGNORECASE)
HOURS_RE = re.compile(r"(час|график|режим|работ|откры|закры|schedule|hours)", re.IGNORECASE)
LOCATION_RE = re.compile(r"(адрес|где|наход|локац|район|location|address)", re.IGNORECASE)
PRICE_BOT_RE = re.compile(r"(₸|тенге|тг|цена|стоим|от\s+\d)", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _text_from_row(row: dict[str, Any]) -> str:
    for key in ("turn_text", "user_text", "text", "message"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _bot_text_from_row(row: dict[str, Any]) -> str:
    for key in ("outbox_text", "inline_response_text"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _decision_meta(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("decision_meta")
    return meta if isinstance(meta, dict) else {}


def _normalized_info_sections(meta: dict[str, Any]) -> set[str]:
    sections = meta.get("info_sections")
    if not isinstance(sections, list):
        return set()
    normalized: set[str] = set()
    for value in sections:
        if not isinstance(value, str):
            continue
        token = value.strip().casefold()
        if token:
            normalized.add(token)
    return normalized


def detect_logic_issues(row: dict[str, Any]) -> list[str]:
    text = _text_from_row(row)
    if not text:
        return []
    bot_text = _bot_text_from_row(row)
    meta = _decision_meta(row)
    action = str(meta.get("action") or "").strip().casefold()
    info_sections = _normalized_info_sections(meta)
    issues: list[str] = []

    price_question = bool(PRICE_RE.search(text))
    parking_question = bool(PARKING_RE.search(text))
    hours_question = bool(HOURS_RE.search(text))
    location_question = bool(LOCATION_RE.search(text))

    if price_question:
        has_price_section = bool({"pricing", "price", "payment_info"} & info_sections)
        has_price_reply = bool(PRICE_BOT_RE.search(bot_text))
        if not has_price_section and not has_price_reply:
            issues.append("price_unanswered")
    if parking_question and "parking" not in info_sections:
        issues.append("parking_unanswered")
    if hours_question and "hours" not in info_sections:
        issues.append("hours_unanswered")
    if location_question and not ({"location", "address"} & info_sections):
        issues.append("location_unanswered")
    if action == "booking_prompt" and (
        price_question or parking_question or hours_question or location_question
    ):
        issues.append("info_to_booking_prompt")
    return issues


def build_gap_scenarios(rows: list[dict[str, Any]], *, max_dialogs: int) -> dict[str, Any]:
    dialogs: list[dict[str, Any]] = []
    for row in rows:
        if len(dialogs) >= max_dialogs:
            break
        evaluation = row.get("evaluation") if isinstance(row.get("evaluation"), dict) else {}
        reasons = evaluation.get("reasons") if isinstance(evaluation.get("reasons"), list) else []
        logic_issues = detect_logic_issues(row)
        if not reasons and not logic_issues:
            continue
        text = _text_from_row(row)
        if not text:
            continue
        meta = _decision_meta(row)
        expected_reply_type = row.get("expected_reply_type")
        if not isinstance(expected_reply_type, str) or not expected_reply_type.strip():
            expected_reply_type = meta.get("expected_reply_type")
        expect: dict[str, Any] = {}
        state = row.get("conversation_state")
        if isinstance(state, str) and state.strip():
            expect["state"] = state.strip()
        if isinstance(expected_reply_type, str) and expected_reply_type.strip():
            expect["reply_type"] = expected_reply_type.strip()
        info_expect: list[str] = []
        if "price_unanswered" in logic_issues:
            info_expect.append("pricing")
        if "parking_unanswered" in logic_issues:
            info_expect.append("parking")
        if "hours_unanswered" in logic_issues:
            info_expect.append("hours")
        if "location_unanswered" in logic_issues:
            info_expect.append("location")
        if info_expect:
            expect["info_sections"] = sorted(set(info_expect))

        dialog_id = f"gap-{len(dialogs)+1:03d}"
        tags = ["gap"] + sorted(set(str(reason) for reason in reasons + logic_issues))
        dialogs.append(
            {
                "dialog_id": dialog_id,
                "goal": "regression-gap",
                "source_turn": {
                    "conversation_id": row.get("conversation_id"),
                    "turn_index": row.get("turn_index"),
                    "message_id": row.get("message_id"),
                },
                "turns": [
                    {
                        "kind": "text",
                        "text": text,
                        "tags": tags,
                        "expect": expect,
                    }
                ],
            }
        )
    return {"dialogs": dialogs}


def build_digest(summary: dict[str, Any], rows: list[dict[str, Any]], *, max_examples: int) -> dict[str, Any]:
    failure_counts: Counter[str] = Counter()
    logic_counts: Counter[str] = Counter()
    logic_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        evaluation = row.get("evaluation")
        reasons = []
        if isinstance(evaluation, dict):
            raw_reasons = evaluation.get("reasons")
            if isinstance(raw_reasons, list):
                reasons = [str(item) for item in raw_reasons if str(item).strip()]
        for reason in reasons:
            failure_counts[reason] += 1

        issues = detect_logic_issues(row)
        for issue in issues:
            logic_counts[issue] += 1
            bucket = logic_examples[issue]
            if len(bucket) >= max_examples:
                continue
            bucket.append(
                {
                    "conversation_id": row.get("conversation_id"),
                    "turn_index": row.get("turn_index"),
                    "message_id": row.get("message_id"),
                    "turn_text": _text_from_row(row),
                    "bot_text": _bot_text_from_row(row),
                    "action": _decision_meta(row).get("action"),
                    "intent": _decision_meta(row).get("intent"),
                    "info_sections": sorted(_normalized_info_sections(_decision_meta(row))),
                }
            )

    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    rates = metrics.get("rates") if isinstance(metrics.get("rates"), dict) else {}
    counts = metrics.get("counts") if isinstance(metrics.get("counts"), dict) else {}

    return {
        "run_id": summary.get("run_id"),
        "infra_valid": summary.get("infra_valid"),
        "semantic_valid": summary.get("semantic_valid"),
        "rates": rates,
        "counts": counts,
        "top_failures": failure_counts.most_common(10),
        "logic_findings": {
            "counts": dict(logic_counts),
            "examples": dict(logic_examples),
        },
    }


def render_markdown(digest: dict[str, Any]) -> str:
    lines = [
        "# LLM Quality Digest",
        "",
        f"- run_id: `{digest.get('run_id')}`",
        f"- infra_valid: `{digest.get('infra_valid')}`",
        f"- semantic_valid: `{digest.get('semantic_valid')}`",
    ]
    rates = digest.get("rates") if isinstance(digest.get("rates"), dict) else {}
    if rates:
        lines.extend(
            [
                f"- strict_pass_rate: `{rates.get('strict_pass_rate')}`",
                f"- pass_rate: `{rates.get('pass_rate')}`",
                f"- info_answer_rate: `{rates.get('info_answer_rate')}`",
                f"- degraded_fallback_rate: `{rates.get('degraded_fallback_rate')}`",
            ]
        )

    lines.append("")
    lines.append("## Top Failures")
    top_failures = digest.get("top_failures") or []
    if not top_failures:
        lines.append("- none")
    else:
        for reason, count in top_failures:
            lines.append(f"- `{reason}`: {count}")

    logic_findings = digest.get("logic_findings") if isinstance(digest.get("logic_findings"), dict) else {}
    logic_counts = logic_findings.get("counts") if isinstance(logic_findings.get("counts"), dict) else {}
    logic_examples = logic_findings.get("examples") if isinstance(logic_findings.get("examples"), dict) else {}

    lines.append("")
    lines.append("## Logic Findings")
    if not logic_counts:
        lines.append("- none")
    else:
        for issue, count in sorted(logic_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{issue}`: {count}")
            for example in logic_examples.get(issue, [])[:3]:
                lines.append(
                    f"  - conv={example.get('conversation_id')} turn={example.get('turn_index')} "
                    f"text={example.get('turn_text')!r}"
                )
                lines.append(
                    f"  - bot={example.get('bot_text')!r} action={example.get('action')} "
                    f"intent={example.get('intent')} info_sections={example.get('info_sections')}"
                )
    return "\n".join(lines).rstrip() + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build digest and gap scenarios from llm-quality run.")
    parser.add_argument("--run-dir", required=True, help="llm-quality output directory")
    parser.add_argument("--summary", default=None, help="summary.json path override")
    parser.add_argument("--responses", default=None, help="responses.jsonl path override")
    parser.add_argument("--output", default=None, help="Markdown output path")
    parser.add_argument("--json-output", default=None, help="JSON digest output path")
    parser.add_argument("--gaps-output", default=None, help="Generated gap scenarios file path")
    parser.add_argument("--max-examples", type=int, default=5)
    parser.add_argument("--max-gap-dialogs", type=int, default=25)
    return parser.parse_args()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(payload)


def main() -> int:
    args = _parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    summary_path = Path(args.summary).expanduser().resolve() if args.summary else run_dir / "summary.json"
    responses_path = Path(args.responses).expanduser().resolve() if args.responses else run_dir / "responses.jsonl"
    output_path = Path(args.output).expanduser().resolve() if args.output else run_dir / "digest.md"
    digest_json_path = (
        Path(args.json_output).expanduser().resolve() if args.json_output else run_dir / "digest.json"
    )
    gaps_path = (
        Path(args.gaps_output).expanduser().resolve()
        if args.gaps_output
        else run_dir / "gaps_scenarios.json"
    )

    if not responses_path.exists():
        raise SystemExit(f"responses.jsonl not found: {responses_path}")

    summary: dict[str, Any] = {}
    if summary_path.exists():
        summary = _load_json(summary_path)
    rows = _load_jsonl(responses_path)
    digest = build_digest(summary, rows, max_examples=max(1, args.max_examples))
    gaps = build_gap_scenarios(rows, max_dialogs=max(1, args.max_gap_dialogs))

    _write_json(digest_json_path, digest)
    _write_json(gaps_path, gaps)
    _write_text(output_path, render_markdown(digest))

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "digest_markdown": str(output_path),
                "digest_json": str(digest_json_path),
                "gaps_scenarios": str(gaps_path),
                "rows": len(rows),
                "logic_issues": sum((digest.get("logic_findings") or {}).get("counts", {}).values()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
