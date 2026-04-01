# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R6 Allowlist-Safe Preflight Fallback Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R6-ALLOWLIST-SAFE-PREFLIGHT-FALLBACK-PROOF-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `UNLOCKS`: `classify_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_runtime_family`

## Name / goal
Close one bounded proof/infra family in `ops/diagnose.py`: when contaminated replay preflight falls back under `--jid-mode unique --allow-non-allowlist` with outbox enabled, it must stay on allowlist-safe JIDs instead of silently generating a non-allowlist target that the TEST_MODE outbound guard will reject.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r6/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r6/manual_audit.json`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`

## One web search (mandatory before implementation)
- **Query (exact):** `Twilio WhatsApp sandbox only send messages to joined users official documentation`
- **Date/time (local):** `2026-03-22T21:31:00+05:00`
- **Sources opened:** `https://www.twilio.com/docs/documents/591/Twilio_Restricted_API_Keys_Permissions_-_Voice_Permissions.pdf`
- **Reuse / integrate / build decision:** `build`
- **Why:** official sandbox/testing guidance reinforces that test transport should stay inside an approved recipient envelope; the repo-specific fix still belongs in our replay harness.
- **Rejected options:** no provider-side workaround was reused because the failure is in local replay fallback selection, not vendor configuration.

## Root cause (mandatory)
- **Symptom:** replay `r6` stopped at dialog `1`, turn `1` after contaminated preflight switched from allowlist JID `77000000002@s.whatsapp.net` to generated non-allowlist JID `99945912441@s.whatsapp.net`, then the runtime degraded into terminal handoff with failed outbound transport.
- **Minimal reproduction:** run the exact `r6` replay command from `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md` against fresh local runtime; inspect preflight JSON and `/tmp/booking_quality/a922-go2f-seed19-r6/manual_audit.json`.
- **Evidence:** `preflight_fallback_jid` emitted a non-allowlist `remote_jid_after`; server logs then showed TEST_MODE outbound guard skipping that target; strict audit marked the replay non-canonical.
- **Five Whys:** contaminated preflight needed a fresh dialog target; fallback logic generated a synthetic JID; the generator ignored the fact that outbox was still enabled; TEST_MODE guard only allows configured allowlist JIDs; the replay harness therefore created its own transport failure before runtime semantics were re-evaluated.
- **Root cause statement:** `_llm_quality_select_fallback_jid(...)` in `ops/diagnose.py` did not preserve allowlist-safe transport constraints during contaminated replay preflight.
- **Fix mechanism:** keep fallback selection on remaining allowlist JIDs while outbox is enabled; only generate a synthetic non-allowlist JID when outbox is skipped.

## Invariant
- Do not touch runtime semantics, frozen routers, oracle thresholds, or scenario expectations.
- Do not allow replay preflight to weaken transport gates or bypass TEST_MODE safety.

## Scope
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- doc/report/canon sync for this proof family

## Out of scope
- runtime booking continuity fixes
- acceptance lock/go-to-full evidence work
- frozen-router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan
1. Publish this implementation TP.
2. Patch contaminated preflight fallback selection so outbox-enabled replay stays on allowlist JIDs.
3. Add deterministic fallback-selection regressions.
4. Rerun the exact replay family.
5. Reclassify the next first admissible blocker.

## Work mode
- `implementation`

## DoD
- contaminated replay fallback no longer generates non-allowlist JIDs while outbox is enabled
- deterministic fallback-selection tests pass
- next truthful replay advances past the old non-allowlist transport failure or proves a different blocker

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py`
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py`

## Evidence
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `/tmp/booking_quality/a922-go2f-seed19-r6/manual_audit.json`

## Rollback
1. Revert `ops/diagnose.py` and `truffles-api/tests/test_booking_quality_jid_mode.py`.
2. Rebuild the agent packet and rerun focused tests.

## No-go
- no runtime semantic edits
- no frozen-router edits
- no second query for this proof family
- no acceptance claim from deterministic tests alone

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- contaminated replay reset still depends on live runtime session-reset semantics
- direct runtime send paths may still ignore simulation transport constraints

### Why not in this block
- this block only removes the harness-side non-allowlist fallback bug

### Risk if deferred
- fresh replay can still stop earlier on runtime reset/transport behavior even after proof fallback is corrected

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next fresh replay still fails before turn execution

## Next-block contract (mandatory)
### Next block objective
- classify the next first admissible blocker after the allowlist-safe fallback repair on a fresh replay

### First deterministic check command
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r7 --status done --strict-artifacts`

### Blocked-by conditions
- no fresh replay artifact exists after the proof fix

### Owner role for closure
- `Brain / Top Architect`
