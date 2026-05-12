# policy_core_v3 — PoC

**Status:** PoC, not wired into runtime.
**Spec:** [`SPECS/POLICY_CORE_V3.md`](../../../SPECS/POLICY_CORE_V3.md)
**Feature flag:** `policy_core_v3_enabled` in `app/config.py` (default `False`).

This package replaces the legacy scenario-driven `intent_service.py` with a
typed, pure, vertical-agnostic LLM invoker that owns one and only one job:
turn a `PolicyTurnInput` into a `PolicyDecisionV3` or a `DegradeVerdict`.

## Invariants

- No I/O except calling the `LLMCallable` passed in.
- No imports from `app/services/`, `app/core/`, or any pack-runtime adapter.
- Pure `build_prompt` — same input → byte-equal output.
- Deterministic retry policy, no scenario branches.
- Maximum 2 LLM calls per turn.

## Files

| File | Responsibility |
|---|---|
| `pack_view.py` | Minimum `PackView` Protocol + dataclasses for evidence/tools/turns |
| `schema.py` | `PolicyTurnInput`, `PolicyDecisionV3`, `DegradeVerdict`, enums |
| `prompt_builder.py` | Pure-function prompt composer |
| `retry_policy.py` | Deterministic retry decision table |
| `invoker.py` | `PolicyCoreV3Invoker.invoke()` — the public entrypoint |

## What this PoC deliberately does NOT do

- Hook into `consultant_runtime`.
- Replace any existing test, intent, or boundary code.
- Validate booking business rules (boundary's job).
- Render the customer-facing message (response realizer's job).
- Touch `intent_service.py`'s forced-fields functions (cleanup belongs to
  Phase D; see spec section 8).

## Next phases

See `SPECS/POLICY_CORE_V3.md` section 8.
