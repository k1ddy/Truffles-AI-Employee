"""Lazy singletons for the shadow-run hook.

All wiring is opt-in via environment variables. If a variable is unset, the
corresponding singleton returns None and the dispatcher becomes a no-op.

Env vars:
- POLICY_CORE_V3_SHADOW_PACK_PATH — directory containing pack.yaml
- POLICY_CORE_V3_SHADOW_JSONL_PATH — file path for ComparisonRecord JSONL
- POLICY_CORE_V3_SHADOW_USE_LLM — "true" to wire the real LLM provider; default
  uses an inert mock that returns a degrade-shaped response so we observe
  end-to-end wiring without spending tokens.

Dual-gate: the dispatcher must check `settings.policy_core_v3_enabled` AND
require POLICY_CORE_V3_SHADOW_PACK_PATH to be set. This prevents accidental
shadow-run activation in environments where the flag is on but no pack is
configured.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any

from app.policy_core_v3 import PolicyCoreV3Invoker
from app.policy_core_v3_shadow import (
    ArtifactSink,
    JsonlArtifactSink,
)


logger = logging.getLogger(__name__)


# Module-level singletons. `reset_singletons()` clears them (used by tests).
_pack: Any | None = None
_pack_attempted: bool = False
_sink: ArtifactSink | None = None
_sink_attempted: bool = False
_invoker: PolicyCoreV3Invoker | None = None
_invoker_attempted: bool = False


def reset_singletons() -> None:
    """Test-only: forget cached singletons so env-var changes take effect."""
    global _pack, _pack_attempted, _sink, _sink_attempted, _invoker, _invoker_attempted
    _pack = None
    _pack_attempted = False
    _sink = None
    _sink_attempted = False
    _invoker = None
    _invoker_attempted = False


def get_shadow_pack() -> Any | None:
    """Return a loaded `PackV1` or None if not configured / load failed."""
    global _pack, _pack_attempted
    if _pack_attempted:
        return _pack
    _pack_attempted = True

    raw = os.environ.get("POLICY_CORE_V3_SHADOW_PACK_PATH")
    if not raw:
        return None
    try:
        from app.pack_v1 import load_pack

        _pack = load_pack(pathlib.Path(raw))
    except Exception as exc:
        logger.warning("policy_core_v3 shadow: pack load failed (%s); shadow disabled", exc)
        _pack = None
    return _pack


def get_shadow_sink() -> ArtifactSink | None:
    """Return a JSONL sink or None if not configured."""
    global _sink, _sink_attempted
    if _sink_attempted:
        return _sink
    _sink_attempted = True

    raw = os.environ.get("POLICY_CORE_V3_SHADOW_JSONL_PATH")
    if not raw:
        return None
    try:
        _sink = JsonlArtifactSink(pathlib.Path(raw))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("policy_core_v3 shadow: sink init failed (%s); shadow disabled", exc)
        _sink = None
    return _sink


async def _mock_llm(prompt: str) -> str:
    """Inert mock LLM used when POLICY_CORE_V3_SHADOW_USE_LLM is not "true".

    Returns a fixed v3-shaped degrade so the comparison record exercises the
    full pipeline without spending tokens. The shadow-runner translates this
    into a `degrade_reason=intent_not_in_enum` followed by a degrade after
    one retry — that is fine for B.2.b wiring proof.
    """
    return json.dumps(
        {
            "intent": "shadow_mock_unwired",
            "slots": {},
            "candidate_action": {"tool": "none", "args": {}},
            "evidence_refs": [],
            "message_draft": "(shadow mock — real LLM not wired)",
            "uncertainty": "high",
            "notes": "policy_core_v3_shadow_hook mock",
        },
        ensure_ascii=False,
    )


def get_shadow_invoker() -> PolicyCoreV3Invoker | None:
    """Return an invoker. Real LLM if explicitly enabled, otherwise a mock."""
    global _invoker, _invoker_attempted
    if _invoker_attempted:
        return _invoker
    _invoker_attempted = True

    use_real = (os.environ.get("POLICY_CORE_V3_SHADOW_USE_LLM", "").strip().lower() == "true")
    if not use_real:
        _invoker = PolicyCoreV3Invoker(_mock_llm)
        return _invoker

    try:
        from app.policy_core_v3_shadow import SyncToAsyncLLMAdapter
        from app.services.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        adapter = SyncToAsyncLLMAdapter(
            provider,
            model=os.environ.get("POLICY_CORE_V3_SHADOW_MODEL") or None,
            temperature=0.0,
            max_tokens=int(os.environ.get("POLICY_CORE_V3_SHADOW_MAX_TOKENS", "1500")),
            timeout_seconds=float(os.environ.get("POLICY_CORE_V3_SHADOW_TIMEOUT", "30.0")),
        )
        _invoker = PolicyCoreV3Invoker(adapter)
    except Exception as exc:
        logger.warning(
            "policy_core_v3 shadow: real LLM init failed (%s); falling back to mock",
            exc,
        )
        _invoker = PolicyCoreV3Invoker(_mock_llm)
    return _invoker
