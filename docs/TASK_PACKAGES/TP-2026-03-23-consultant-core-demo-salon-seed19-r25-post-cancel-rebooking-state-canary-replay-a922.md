# TP-2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Canary Replay A922

## Title/goal
Run one truthful fresh replay after the bounded post-cancel rebooking state repair and classify the first surviving blocker on seed-`19` evidence.

## Canon refs
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md`

## Invariant
Do not reopen runtime code during this block; this block is replay/audit only.

## Scope
- audit stale/non-canonical replay attempts if they block the manual-audit gate
- start a fresh local runtime on `127.0.0.1:18186` with canonical env parity
- run one fresh exact replay on `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- strict-audit the resulting artifact and classify the first surviving blocker

## Out of scope
- new implementation changes before replay
- frozen router edits
- acceptance evidence work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: the runtime repair and focused deterministic proof were already complete; this block only validates closure on the exact replay surface.
- `Family handled in this block`: `seed19 r25 post-cancel rebooking replay closure`
- `Closure artifact expected from this mode`: one replay TP/report pair plus truthful classification of the new first blocker.

## Checks
- `curl -sf http://127.0.0.1:18186/admin/version`
- `curl -sf http://127.0.0.1:18186/admin/health`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r29 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r26/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r27/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r28/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate top-level defs in `reasoning_core.py` remain deferred
- stale/non-canonical replay attempts can still consume manual-audit gate budget before truthful closure begins

### Why not in this block
This block is replay/audit only; no runtime cleanup is admissible here.

### Risk if deferred
Fresh replay can keep surfacing adjacent owner families on the hotspot without duplicate cleanup.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`

### Expiry/trigger to stop deferral
Immediate; classify the first surviving blocker from fresh replay before any new runtime code.

## Next-block contract (mandatory)
### Next block objective
Lock the first surviving blocker after truthful replay `r29` and choose the next admissible runtime family.

### First deterministic check command
`python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r29 --status done --strict-artifacts`

### Blocked-by conditions
Stale local runtime parity; unaudited stale replay artifacts; missing strict audit on the fresh replay.

### Owner role for closure
Brain / Top Architect
