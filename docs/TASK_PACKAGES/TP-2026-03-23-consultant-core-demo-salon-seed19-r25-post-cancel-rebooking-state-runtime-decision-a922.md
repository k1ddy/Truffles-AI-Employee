# TP-2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Runtime Decision A922

## Title/goal
Classify the first surviving blocker from fresh replay `r25` after the fallback-JID proof closure and lock the next bounded runtime family.

## Canon refs
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-canary-replay-a922.md`

## Invariant
Do not reopen proof tooling first once fresh replay already proves the fallback-JID family is closed and `infra_valid=true`.

## Scope
Truthful classification of dialog `2`, turn `8` on `r25`, plus canon sync to the next bounded runtime implementation family.

## Out of scope
- new proof tooling changes
- frozen router edits
- acceptance lock/full runs

## Touch-list
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan
1. Record the truthful closure of the old fallback-JID proof family on `r25`.
2. Classify dialog `2`, turn `8` as runtime or oracle/proof using the fresh row evidence.
3. Lock the next bounded runtime family and keep proof/runtime separation intact.

## DoD
- canon points at the new runtime-decision block
- next move no longer points at `ops/diagnose.py`
- `r25` is described as runtime-blocking after the proof family closed

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: fresh replay and strict audit already exist; this block only classifies the new first blocker.
- `Family handled in this block`: `seed19 r25 post-cancel rebooking state runtime decision`
- `Closure artifact expected from this mode`: one decision TP/report pair and canon sync to the next runtime implementation family.

## One web search (mandatory before implementation)
- **Query (exact):** `n/a — decision-only closure block after the already-executed proof implementation family`
- **Date/time (local):** `2026-03-23 11:45 +05:00`
- **Sources opened (from this query):**
  - `https://stackoverflow.com/questions/74622031/whatsapp-business-api-cloud-how-do-i-register-a-customers-phonenumber-via-api`
  - `https://developers.facebook.com/docs/whatsapp/cloud-api/get-started#sent-test-message`
- **Source quality:** `reuse of the single implementation-family query already recorded in the parent TP; no new query executed in this closure block`
- **Existing solutions found:** the old proof family is already closed; this block only classifies the surviving runtime row.
- **Decision:** `reuse fresh replay artifact and local source analysis; no new search in this decision block`
- **Reuse / integrate / build decision:** `reuse the fresh replay artifact and local trace/state evidence to classify the next runtime family before any new implementation`
- **Rejected options:** `opening another search for a closure-only block`, `reopening proof tooling before classifying the runtime row`

## Root cause (mandatory)
- Symptom: fresh replay `r25` reaches dialog `2`, turn `8`, but the row fails strict state expectation even though the product reply is a valid `booking_prompt` collect.
- Minimal reproduction: inspect message `LLM-QUAL-a922-go2f-seed19-r25-002-08-a600b7` in `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl` and confirm `decision_meta.action='booking_prompt'`, `decision_meta.expected_reply_type='service_choice'`, and `conversation_state='pending'` while the scenario expects `state='bot_active'`.
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:3321`
  - `truffles-api/app/services/reasoning_core.py:5005`
  - `truffles-api/app/services/reasoning_core.py:8440`
  - `truffles-api/app/services/reasoning_core.py:10095`
- Five Whys:
  1. Why did `r25` stop semantic-red? Because dialog `2`, turn `8` fails `expected_state_mismatch`.
  2. Why does the state mismatch happen? Because runtime leaves `conversation_state=pending`.
  3. Why is that a contract issue? The same row already returns the correct collect action and `expected_reply_type=service_choice`, so only continuity state remains wrong.
  4. Why is this not proof/oracle drift? The replay is `infra_valid=true`, the old proof family is closed, and the scenario expectation only requires `bot_active` while allowing any reply action.
  5. Why is this runtime debt family-sensitive? The live path crosses shadowed explicit-handoff and booking-prompt owner defs in `reasoning_core.py`, so stale pending/handoff continuity can survive beneath a superficially correct reply.
- Root cause statement: post-cancel rebooking reentry now reaches the correct `booking_prompt` collect path, but runtime continuity still preserves `pending` state instead of restoring `bot_active` before the new booking collect contract is written.
- Fix mechanism: next block must repair pending-to-bot-active continuity on the post-cancel rebooking path in the executable non-frozen owner chain and lock it with deterministic regression before another replay.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `responses.jsonl` and strict audit from `/tmp/booking_quality/a922-go2f-seed19-r25`
  - existing replay closure evidence in `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-canary-replay-a922.md`
  - existing non-frozen owner surfaces in `truffles-api/app/services/reasoning_core.py`
- External reuse:
  - `https://stackoverflow.com/questions/74622031/whatsapp-business-api-cloud-how-do-i-register-a-customers-phonenumber-via-api`
  - `https://developers.facebook.com/docs/whatsapp/cloud-api/get-started#sent-test-message`
- Why not reinvent the wheel:
  - the proof family is already closed and the next work is purely about runtime continuity in the existing owner chain; no new auxiliary infrastructure is needed before classification.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` in this decision block
- Max replay runs: `1` already consumed by `r25`
- Stop condition: if the surviving blocker is runtime on fresh `infra_valid=true` evidence, open a bounded runtime implementation family and stop closure work.

## Release safety (mandatory for non-doc changes)
- Strategy: `no production rollout in this decision block; classify only and keep replay runtime local on 127.0.0.1:18186`
- Go/no-go signals: `r25` must prove the old proof family closed before any runtime reopening`
- Rollback: `revert canon sync if later evidence disproves the runtime classification`
- Post-release monitoring window: `n/a for this decision block`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r25 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md`

## Rollback
Revert canon/session updates if the blocker classification proves wrong.

## No-go
- no new proof tooling changes first
- no frozen router edits
- no acceptance-gate weakening

## Risks/blockers
- the live path crosses shadowed owner names in `reasoning_core.py`, so the implementation block must verify which duplicate definition is executable before editing.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- downstream dialog `2+` rows after turn `8` remain unresolved until the runtime family is repaired
- `reasoning_core.py` duplicate top-level defs remain deferred structural debt

### Why not in this block
This block is classification only.

### Risk if deferred
The next implementation could mis-target proof tooling even though fresh replay already proves the blocker is runtime continuity.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md`

### Expiry/trigger to stop deferral
Immediate; no more proof work is admissible before the post-cancel rebooking state family is repaired.

## Next-block contract (mandatory)
### Next block objective
Repair post-cancel rebooking continuity so the collect reply at dialog `2`, turn `8` restores `bot_active` instead of preserving `pending`.

### First deterministic check command
`pytest -q truffles-api/tests/test_reasoning_core.py -k "cancel or check_booking or pending"`

### Blocked-by conditions
Unresolved disagreement about runtime vs proof; stale local replay runtime; missing `r25` audit.

### Owner role for closure
Brain / Top Architect
