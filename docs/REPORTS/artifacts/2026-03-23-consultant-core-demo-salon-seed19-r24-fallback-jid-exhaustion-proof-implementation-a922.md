# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Proof Implementation A922

## Summary
- Landed one bounded proof-only implementation family in `ops/diagnose.py`; runtime code and frozen routers stayed untouched.
- Allowlist-first replay fallback is preserved, but exact replay can now mint deterministic fresh dialog JIDs after allowlist exhaustion when `allow_non_allowlist=true` is already explicit.
- Added targeted deterministic proof in `truffles-api/tests/test_booking_quality_jid_mode.py`.
- The next honest move after this implementation was one fresh exact replay on the locked seed-`19` scenarios.

## Code changes
### `ops/diagnose.py`
- `_llm_quality_select_fallback_jid(...)` no longer hard-stops after allowlist exhaustion when non-allowlist fallback is explicitly allowed.
- The helper still prefers untried allowlist JIDs first.
- When allowlist candidates are exhausted, it now uses `_llm_quality_generate_unique_jid(...)` with deterministic fallback salts until it finds a fresh dialog JID not already tried.

### `truffles-api/tests/test_booking_quality_jid_mode.py`
- Replaced the old outbox-enabled hard-stop expectation with a regression proving fallback-JID generation is allowed once `allow_non_allowlist=true` is explicit.
- Added regression proving the helper skips already-tried generated fallback JIDs.
- Added regression proving the helper still returns `None` when non-allowlist fallback is disabled.

## Deterministic evidence
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py` -> `pass`
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"` -> `12 passed`

## Canon result
- This block only changed proof-path helper logic and deterministic proof.
- No runtime family was reopened in this implementation step.
- Closure was deferred to the fresh exact replay that produced `r25`.

## Residual debt
- the live replay still had to prove the old proof family was actually closed on the full surface
- downstream runtime classification remained blocked until that replay completed

## Next move
- `rerun_consultant_core_demo_salon_seed19_r24_fallback_jid_exhaustion_canary_replay`
