"""Corpus runner — replays CorpusDialogs through run_shadow.

Spec: SPECS/SHADOW_RUN_V3.md (Phase B.3).

This is a pure-async helper consumed by `scripts/policy_core_v3_shadow_corpus_run.py`.
It does NOT touch consultant_runtime; it builds shadow inputs directly from
corpus fixtures and calls `run_shadow` with an oracle/drift LLM.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.pack_v1 import PackV1
from app.policy_core_v3 import LLMCallable, PolicyCoreV3Invoker
from app.policy_core_v3_shadow import (
    ArtifactSink,
    ComparisonRecord,
    LegacyTurnContext,
    run_shadow,
)

from .oracle_llm import OracleLLMConfig, OracleRegistry, build_oracle_llm
from .schema import CorpusDialog


async def run_corpus(
    *,
    dialogs: list[CorpusDialog],
    pack: PackV1,
    sink: ArtifactSink,
    config: OracleLLMConfig | None = None,
    llm_override: LLMCallable | None = None,
) -> list[ComparisonRecord]:
    """Replay every turn of every dialog through `run_shadow`.

    If `llm_override` is provided, the oracle/drift/degrade mock is bypassed
    and v3 receives prompts driven by the real (or any) LLM. The `config`
    argument is then ignored. Use this for live shadow runs against an
    `OpenAIProvider`-wrapped adapter.

    Returns the list of emitted records (also persisted via `sink`).
    """
    if llm_override is not None:
        registry = None
        llm = llm_override
    else:
        registry = OracleRegistry()
        llm = build_oracle_llm(registry, config)
    invoker = PolicyCoreV3Invoker(llm)

    out: list[ComparisonRecord] = []
    now = datetime.now(timezone.utc)

    for dialog in dialogs:
        for turn in dialog.turns:
            if registry is not None:
                registry.set_active(
                    turn.oracle_v3,
                    token=f"{dialog.dialog_id}:{turn.turn_index}:{turn.current_message}",
                )
            try:
                ctx = LegacyTurnContext(
                    tenant_id="corpus",
                    conversation_id=dialog.dialog_id,
                    current_message=turn.current_message,
                    pack=pack,
                    now=now,
                    history=list(turn.history),
                    state_slots=dict(turn.state_slots),
                    evidence_bundle=list(turn.evidence_bundle),
                    locale=dialog.locale,
                    policy_version="corpus-runner",
                )
                record = await run_shadow(
                    ctx=ctx,
                    legacy_summary=turn.legacy_summary,
                    invoker=invoker,
                    sink=sink,
                    turn_index=turn.turn_index,
                    notes=f"corpus_runner:{dialog.status}",
                )
                out.append(record)
            finally:
                if registry is not None:
                    registry.clear()

    return out
