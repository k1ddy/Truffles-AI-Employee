# policy_core_v3_shadow — PoC

**Status:** PoC, not wired into runtime.
**Spec:** [`SPECS/SHADOW_RUN_V3.md`](../../../SPECS/SHADOW_RUN_V3.md)
**Phase:** B.1

Observation-only shadow-run for Policy-Core v3. Runs in parallel with the
legacy intent_service and emits a typed `ComparisonRecord` per turn. Never
affects the customer reply.

## Files

| File | Responsibility |
|---|---|
| `llm_adapter.py` | Wraps a sync LLM provider into an async `LLMCallable` |
| `turn_input_builder.py` | Pure `to_policy_turn_input(LegacyTurnContext) -> PolicyTurnInput` |
| `comparison_artifact.py` | `ComparisonRecord`, `ArtifactSink`, `InMemoryArtifactSink` |
| `shadow_runner.py` | `run_shadow(...)` — never raises into caller |

## Invariants

- No imports from `app.services`, `app.core`, `app.adapters`.
- No DB, no network beyond the LLM call.
- Shadow path never affects the customer reply (`run_shadow` swallows all
  exceptions and surfaces them as `degrade` records with notes).
- Gated by `settings.policy_core_v3_enabled` at the future call site
  (Phase B.2). The module itself does not read the flag.

## What this module does NOT do (yet)

- Hook into `consultant_runtime` (Phase B.2).
- Convert real demo_salon data into a pack (Phase B.2).
- Run the approved corpus (Phase B.3).
- Provide a JSONL/Postgres sink (Phase B.2).

## Dry-run

`scripts/policy_core_v3_shadow_dryrun.py` exercises the full wiring on the
example pack with a mock LLM and prints a JSON `ComparisonRecord`.
