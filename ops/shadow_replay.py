#!/usr/bin/env python3
"""
Shadow replay report generator.

Inputs:
- A trace bundle JSON produced by `ops/diagnose.py trace-bundle`.
- Optionally a second bundle for comparison.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from typing import Any


def _load_json(path: str) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    return json.loads(raw)


def _bundle_key(bundle: dict[str, Any], index: int) -> str:
    message = bundle.get("message")
    if isinstance(message, dict):
        for key in ("message_uuid", "message_id", "conversation_id"):
            value = message.get(key)
            if value:
                return str(value)
    return f"bundle-{index}"


def _pack_meta(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    meta: dict[str, Any] = {}
    for key in ("schema_version", "hash", "version_id", "compiled_at", "source"):
        if value.get(key) is not None:
            meta[key] = value.get(key)
    return meta


def _compact_meta(meta: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in ("action", "intent", "reply_type", "routing_token", "policy", "expected_reply"):
        if meta.get(key) is not None:
            summary[key] = meta.get(key)
    snapshot = meta.get("signal_snapshot")
    if isinstance(snapshot, dict):
        summary["pack_index"] = _pack_meta(snapshot.get("pack_index"))
        summary["compiled_pack"] = _pack_meta(snapshot.get("compiled_pack"))
    return summary


def _trace_items(trace: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(trace, list):
        for entry in trace:
            if not isinstance(entry, dict):
                continue
            stage = entry.get("stage")
            decision = entry.get("decision")
            if decision is None:
                decision = entry.get("action") or entry.get("result")
            items.append({"stage": stage, "decision": decision})
    return items


def _trace_signature(items: list[dict[str, Any]]) -> list[str]:
    signature: list[str] = []
    for item in items:
        stage = item.get("stage")
        decision = item.get("decision")
        if isinstance(decision, (dict, list)):
            decision_repr = json.dumps(decision, sort_keys=True, ensure_ascii=False)
        elif decision is None:
            decision_repr = ""
        else:
            decision_repr = str(decision)
        if stage:
            signature.append(f"{stage}:{decision_repr}")
        else:
            signature.append(decision_repr or "<unknown>")
    return signature


def _hash_payload(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    meta = _compact_meta(bundle.get("decision_meta"))
    trace_signature = _trace_signature(_trace_items(bundle.get("decision_trace")))
    return {
        "meta": meta,
        "meta_hash": _hash_payload(meta),
        "trace": trace_signature,
        "trace_hash": _hash_payload(trace_signature),
    }


def _build_bundle_map(bundles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for idx, bundle in enumerate(bundles):
        key = _bundle_key(bundle, idx)
        if key in mapping:
            key = f"{key}#{idx}"
        mapping[key] = bundle
    return mapping


def _format_meta(meta: dict[str, Any]) -> str:
    if not meta:
        return "{}"
    return json.dumps(meta, ensure_ascii=False, sort_keys=True)


def _format_trace(trace: list[str]) -> str:
    if not trace:
        return "-"
    return " -> ".join(trace)


def _build_report(
    *,
    base_payload: dict[str, Any],
    shadow_payload: dict[str, Any] | None,
    input_path: str,
    shadow_path: str | None,
) -> str:
    base_bundles = base_payload.get("bundles") if isinstance(base_payload, dict) else None
    base_bundles = base_bundles if isinstance(base_bundles, list) else []
    shadow_map = None
    if shadow_payload:
        shadow_bundles = shadow_payload.get("bundles") if isinstance(shadow_payload, dict) else None
        shadow_bundles = shadow_bundles if isinstance(shadow_bundles, list) else []
        shadow_map = _build_bundle_map(shadow_bundles)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    lines = [
        "# Shadow Replay Report",
        "",
        f"- generated_at: {now}",
        f"- input: {input_path}",
        f"- shadow: {shadow_path or ''}",
        f"- bundles: {len(base_bundles)}",
    ]

    mismatches = 0
    matched = 0

    for idx, bundle in enumerate(base_bundles):
        key = _bundle_key(bundle, idx)
        summary = _summarize_bundle(bundle)
        shadow_summary = None
        if shadow_map:
            shadow_bundle = shadow_map.get(key)
            if shadow_bundle:
                shadow_summary = _summarize_bundle(shadow_bundle)
                matched += 1
                if (
                    summary["meta_hash"] != shadow_summary["meta_hash"]
                    or summary["trace_hash"] != shadow_summary["trace_hash"]
                ):
                    mismatches += 1

        message = bundle.get("message") if isinstance(bundle, dict) else None
        if not isinstance(message, dict):
            message = {}

        lines.extend(
            [
                "",
                f"## {key}",
                "",
                f"- message_id: {message.get('message_id') or ''}",
                f"- message_uuid: {message.get('message_uuid') or ''}",
                f"- conversation_id: {message.get('conversation_id') or ''}",
                f"- content: {str(message.get('content') or '')[:200]}",
                f"- baseline.meta_hash: {summary['meta_hash']}",
                f"- baseline.trace_hash: {summary['trace_hash']}",
                f"- baseline.meta: {_format_meta(summary['meta'])}",
                f"- baseline.trace: {_format_trace(summary['trace'])}",
            ]
        )

        if shadow_summary:
            lines.extend(
                [
                    f"- shadow.meta_hash: {shadow_summary['meta_hash']}",
                    f"- shadow.trace_hash: {shadow_summary['trace_hash']}",
                    f"- shadow.meta: {_format_meta(shadow_summary['meta'])}",
                    f"- shadow.trace: {_format_trace(shadow_summary['trace'])}",
                ]
            )
            if (
                summary["meta_hash"] != shadow_summary["meta_hash"]
                or summary["trace_hash"] != shadow_summary["trace_hash"]
            ):
                lines.append("- diff: mismatch")
            else:
                lines.append("- diff: ok")

    if shadow_map is not None:
        lines.insert(5, f"- matched: {matched}")
        lines.insert(6, f"- mismatches: {mismatches}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate shadow replay report.")
    parser.add_argument("--input", required=True, help="Input trace bundle JSON.")
    parser.add_argument("--output", required=True, help="Output markdown path (or '-' for stdout).")
    parser.add_argument(
        "--shadow",
        default=None,
        help="Optional shadow bundle JSON for comparison.",
    )
    args = parser.parse_args()

    base_payload = _load_json(args.input)
    shadow_payload = _load_json(args.shadow) if args.shadow else None

    report = _build_report(
        base_payload=base_payload,
        shadow_payload=shadow_payload,
        input_path=args.input,
        shadow_path=args.shadow,
    )

    if args.output == "-":
        sys.stdout.write(report)
        return 0

    output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else ""
    if output_dir:
        import os

        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
