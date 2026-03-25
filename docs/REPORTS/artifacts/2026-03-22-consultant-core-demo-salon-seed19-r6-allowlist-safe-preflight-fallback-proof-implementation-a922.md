# Report - 2026-03-22 - Consultant Core Demo Salon Seed19 R6 Allowlist-Safe Preflight Fallback Proof Implementation A922

## Outcome
- Implemented bounded proof-only fallback repair in `ops/diagnose.py`.
- Added deterministic regressions in `truffles-api/tests/test_booking_quality_jid_mode.py`.
- Fresh reruns proved the old non-allowlist fallback bug is closed, but exposed a new earlier blocker in runtime/session-reset behavior.

## Code changes
- `ops/diagnose.py`
  - contaminated replay fallback now prefers remaining allowlist JIDs while outbox is enabled
  - fallback iteration can advance across multiple tried allowlist candidates before failing closed
- `truffles-api/tests/test_booking_quality_jid_mode.py`
  - added allowlist-safe fallback coverage, outbox-enabled refusal coverage, skip-outbox synthetic fallback coverage, and tried-candidate skipping coverage

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py` -> pass
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py` -> `10 passed`

## Fresh evidence
- `/tmp/booking_quality/a922-go2f-seed19-r6/manual_audit.json`
  - old blocker: contaminated replay switched to non-allowlist JID and became non-canonical
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`
  - after the fix, replay no longer surfaced the non-allowlist transport failure; it stopped earlier as `infra_valid=false` / `run_incomplete` on contaminated preflight
- runtime logs on fresh local listener
  - allowlist JIDs now hit real provider transport and return `Your plan has been expired please renew.`

## Truthful conclusion
- the bounded proof family is closed: replay fallback no longer self-sabotages by generating a non-allowlist target while outbox is enabled
- the next blocker is not more proof fallback work; it is a runtime/session-reset simulation transport family surfaced by `r7`

## Next move
- `implement_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_runtime_family`
