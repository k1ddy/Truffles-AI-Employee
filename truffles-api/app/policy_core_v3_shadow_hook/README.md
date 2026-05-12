# policy_core_v3_shadow_hook — bridge

**Status:** PoC bridge module. Imports both legacy and shadow types.
**Spec:** [`SPECS/SHADOW_RUN_V3.md`](../../../SPECS/SHADOW_RUN_V3.md) §4 + Phase B.2.b
**Activation:** dual-gate (`settings.policy_core_v3_enabled = True` AND `POLICY_CORE_V3_SHADOW_PACK_PATH` env set).

This package is the only place allowed to import both `app.policy_core_v3_shadow`
(which preserves its independence guard) and legacy `app.services` / `app.core`.

## Files

| File | Responsibility |
|---|---|
| `dispatcher.py` | `dispatch_fire_and_forget(...)` — single function called from `consultant_runtime`. Never raises; schedules a shadow-run task on the running event loop and returns. |
| `wiring.py` | Lazy module-level singletons for pack, JSONL sink, invoker. All env-var driven; missing config → silent no-op. |

## Invariants

- The dispatcher never propagates exceptions to the hot path.
- The dispatcher never blocks the event loop.
- Wiring is opt-in. With no env vars set, the hook is silent.
- The mock LLM is used by default; setting `POLICY_CORE_V3_SHADOW_USE_LLM=true`
  attempts to wire the real provider. Failure to wire falls back to mock with
  a warning log.
- Tests use `wiring.reset_singletons()` to forget cached state between cases.

## Env vars

- `POLICY_CORE_V3_SHADOW_PACK_PATH` — directory containing `pack.yaml`. Required.
- `POLICY_CORE_V3_SHADOW_JSONL_PATH` — file path to append `ComparisonRecord` JSONL. Required.
- `POLICY_CORE_V3_SHADOW_USE_LLM` — `true` to wire `OpenAIProvider`; default uses inert mock.
- `POLICY_CORE_V3_SHADOW_MODEL`, `_MAX_TOKENS`, `_TIMEOUT` — optional real-LLM tuning.
