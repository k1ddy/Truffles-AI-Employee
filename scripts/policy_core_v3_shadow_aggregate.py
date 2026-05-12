#!/usr/bin/env python3
"""Aggregate a ComparisonRecord JSONL into a divergence histogram report.

Usage:
    python3 scripts/policy_core_v3_shadow_aggregate.py \\
        --jsonl /tmp/shadow_run.jsonl \\
        [--out /tmp/shadow_report.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "truffles-api"))


from app.policy_core_v3_corpus import (  # noqa: E402
    aggregate_jsonl_file,
    format_report_text,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", required=True, type=pathlib.Path)
    p.add_argument("--out", type=pathlib.Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    report = aggregate_jsonl_file(args.jsonl)
    print(format_report_text(report))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"wrote: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
