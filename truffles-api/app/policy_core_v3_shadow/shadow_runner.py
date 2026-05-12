"""Shadow-run orchestrator.

Spec: SPECS/SHADOW_RUN_V3.md section 3 (run_shadow) + rule §1
(shadow never affects the hot path).
"""
from __future__ import annotations

import time
import traceback

from app.policy_core_v3 import (
    DegradeVerdict,
    PolicyCoreV3Invoker,
    PolicyDecisionV3,
)
from app.policy_core_v3.schema import DegradeReason

from .comparison_artifact import ArtifactSink, ComparisonRecord
from .divergence import compute_divergence
from .legacy_summary import LegacySummary
from .turn_input_builder import LegacyTurnContext, to_policy_turn_input


async def run_shadow(
    *,
    ctx: LegacyTurnContext,
    legacy_summary: LegacySummary,
    invoker: PolicyCoreV3Invoker,
    sink: ArtifactSink,
    turn_index: int = 0,
    notes: str = "",
) -> ComparisonRecord:
    """Invoke v3 in parallel with the legacy decision and emit a record.

    Never raises into the caller. Any internal failure is captured as a
    `degrade` outcome with `provider_error` and the trace recorded in
    `notes`.
    """
    record_notes = notes
    started = time.perf_counter()
    v3_outcome_kind = "degrade"
    v3_decision_dump: dict | None = None
    v3_degrade_dump: dict | None = None
    attempts = 0
    v3_outcome_for_divergence: PolicyDecisionV3 | DegradeVerdict

    try:
        turn_input = to_policy_turn_input(ctx)
        result = await invoker.invoke(turn_input)
        if isinstance(result, PolicyDecisionV3):
            v3_outcome_kind = "decision"
            v3_decision_dump = result.model_dump(mode="json")
            attempts = 1  # successful path uses at least one call;
            # exact attempt count is owned by the invoker; keep it monotonic
            v3_outcome_for_divergence = result
        elif isinstance(result, DegradeVerdict):
            v3_outcome_kind = "degrade"
            v3_degrade_dump = result.model_dump(mode="json")
            attempts = result.attempts
            v3_outcome_for_divergence = result
        else:  # pragma: no cover - defensive
            v3_outcome_kind = "degrade"
            fallback = DegradeVerdict(
                degrade_reason=DegradeReason.provider_error,
                attempts=1,
                notes="invoker returned unexpected type",
            )
            v3_degrade_dump = fallback.model_dump(mode="json")
            attempts = 1
            v3_outcome_for_divergence = fallback
    except Exception as exc:
        v3_outcome_kind = "degrade"
        fallback = DegradeVerdict(
            degrade_reason=DegradeReason.provider_error,
            attempts=1,
            notes=f"shadow_runner_exception: {type(exc).__name__}",
        )
        v3_degrade_dump = fallback.model_dump(mode="json")
        attempts = 1
        v3_outcome_for_divergence = fallback
        record_notes = (
            f"{record_notes}\nexception:\n{traceback.format_exc()}"
        ).strip()

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    divergence = compute_divergence(legacy_summary, v3_outcome_for_divergence)

    record = ComparisonRecord(
        tenant_id=ctx.tenant_id,
        conversation_id=ctx.conversation_id,
        turn_index=turn_index,
        current_message=ctx.current_message,
        legacy_summary=legacy_summary,
        v3_outcome_kind=v3_outcome_kind,
        v3_decision=v3_decision_dump,
        v3_degrade=v3_degrade_dump,
        v3_latency_ms=elapsed_ms,
        v3_attempts=attempts,
        divergence=divergence,
        policy_version=ctx.policy_version,
        pack_id=ctx.pack.pack_id,
        pack_version=ctx.pack.pack_version,
        notes=record_notes,
    )

    try:
        await sink.emit(record)
    except Exception:  # pragma: no cover - sink errors must not propagate
        # The shadow path must never affect the hot path. Sink failures
        # are silently swallowed; the returned record is still available
        # to inline callers that want to log it.
        pass

    return record
