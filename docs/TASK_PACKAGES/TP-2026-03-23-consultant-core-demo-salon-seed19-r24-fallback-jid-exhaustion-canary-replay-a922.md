# TP-2026-03-23 Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Canary Replay A922

## Title/goal
Run one fresh exact replay after the bounded fallback-JID proof repair and classify the first surviving blocker on truthful `r25` evidence.

## Canon refs
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`

## Invariant
Do not reopen proof code once fresh replay already proves fallback-JID generation is active on the live surface.

## Scope
One fresh exact replay on the locked seed-`19` scenarios plus strict audit and truthful reclassification.

## Out of scope
- new implementation changes before replay
- frozen router edits
- acceptance evidence work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md`
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
- `Why this mode`: the proof family implementation and focused deterministic proof were already complete; this block only validates closure on the exact replay surface.
- `Family handled in this block`: `seed19 r24 fallback-JID exhaustion replay closure`
- `Closure artifact expected from this mode`: one replay TP/report pair plus truthful classification of the new first blocker.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r25 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/runtime_state.json`

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- downstream dialog `2+` runtime families remain unresolved until replay finishes and the first surviving blocker is classified

### Why not in this block
This block is replay/audit only.

### Risk if deferred
The team could reopen proof work even after the fallback-JID family is already closed on live evidence.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md`

### Expiry/trigger to stop deferral
Immediate; classify the first surviving blocker from `r25` before any new code.

## Next-block contract (mandatory)
### Next block objective
Classify the first surviving blocker after `r25` and lock the next bounded family in the correct layer.

### First deterministic check command
`python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r25 --status done --strict-artifacts`

### Blocked-by conditions
Missing `r25` artifact audit; stale local runtime parity; replay not yet complete.

### Owner role for closure
Brain / Top Architect
