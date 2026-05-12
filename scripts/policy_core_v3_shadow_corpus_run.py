#!/usr/bin/env python3
"""Replay a corpus of messy dialogs through Policy-Core v3 shadow-run.

Reads a JSONL of `policy_core_v3_corpus.CorpusDialog` records, replays each
turn through `run_shadow` with an oracle/drift mock LLM, and writes a JSONL
of `ComparisonRecord` to the output path.

Pure infrastructure: does not touch consultant_runtime, does not call a real
LLM unless explicitly extended. SCRIPTED_TECHNICAL_PROOF only.

Usage:
    python3 scripts/policy_core_v3_shadow_corpus_run.py \\
        --corpus truffles-api/tests/corpora/beauty_salon_pilot_v0.jsonl \\
        --pack packs/beauty_salon_v1 \\
        --out /tmp/shadow_run.jsonl \\
        [--mode oracle|drift|degrade] \\
        [--drift-rate 0.2]
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "truffles-api"))


from app.pack_v1 import load_pack  # noqa: E402
from app.policy_core_v3_corpus import (  # noqa: E402
    OracleLLMConfig,
    OracleLLMMode,
    load_corpus_jsonl,
    run_corpus,
)
from app.policy_core_v3_shadow import JsonlArtifactSink  # noqa: E402


_LLM_CHOICES = ["oracle", "drift", "degrade", "openai"]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", required=True, type=pathlib.Path)
    p.add_argument("--pack", required=True, type=pathlib.Path)
    p.add_argument("--out", required=True, type=pathlib.Path)
    p.add_argument(
        "--llm",
        choices=_LLM_CHOICES,
        default="oracle",
        help="oracle/drift/degrade use mock LLM; openai uses real OpenAIProvider.",
    )
    p.add_argument("--drift-rate", type=float, default=0.2)
    p.add_argument("--openai-model", default="gpt-4o-mini",
                   help="Model id for --llm openai.")
    p.add_argument("--openai-max-tokens", type=int, default=1500)
    p.add_argument("--openai-timeout", type=float, default=60.0)
    p.add_argument("--openai-temperature", type=float, default=0.0)
    p.add_argument(
        "--env-file",
        type=pathlib.Path,
        default=pathlib.Path("/home/zhan/truffles-main/truffles-api/.env"),
        help="Optional .env to source OPENAI_API_KEY from for --llm openai.",
    )
    return p.parse_args()


def _load_openai_api_key(env_file: pathlib.Path | None) -> str:
    """Find OPENAI_API_KEY: env var first, then env-file fallback."""
    import os

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if env_file and env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "OPENAI_API_KEY not set and not found in env-file. "
        "Set OPENAI_API_KEY or pass --env-file pointing to a real .env."
    )


def _build_openai_llm(args: argparse.Namespace):
    from app.policy_core_v3_shadow import SyncToAsyncLLMAdapter
    from app.services.llm.openai_provider import OpenAIProvider

    api_key = _load_openai_api_key(args.env_file)
    provider = OpenAIProvider(api_key=api_key, default_model=args.openai_model)
    return SyncToAsyncLLMAdapter(
        provider,
        model=args.openai_model,
        temperature=args.openai_temperature,
        max_tokens=args.openai_max_tokens,
        timeout_seconds=args.openai_timeout,
        response_format={"type": "json_object"},
    )


async def _run(args: argparse.Namespace) -> int:
    dialogs = load_corpus_jsonl(args.corpus)
    pack = load_pack(args.pack)
    sink = JsonlArtifactSink(args.out)

    if args.llm == "openai":
        llm = _build_openai_llm(args)
        records = await run_corpus(
            dialogs=dialogs,
            pack=pack,
            sink=sink,
            llm_override=llm,
        )
    else:
        config = OracleLLMConfig(
            mode=OracleLLMMode(args.llm),
            drift_rate=args.drift_rate,
        )
        records = await run_corpus(
            dialogs=dialogs,
            pack=pack,
            sink=sink,
            config=config,
        )
    print(
        f"corpus_run: dialogs={len(dialogs)} records={len(records)} "
        f"llm={args.llm} out={args.out}"
    )
    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
