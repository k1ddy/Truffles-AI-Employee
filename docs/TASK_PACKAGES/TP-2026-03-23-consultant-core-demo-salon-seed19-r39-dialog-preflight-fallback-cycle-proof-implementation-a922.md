# TP-2026-03-23 Consultant Core Demo Salon Seed19 R39 Dialog Preflight Fallback Cycle Proof Implementation A922

## Title/goal
Repair bounded replay fallback-JID bookkeeping so contaminated dialog preflight can exhaust allowlist candidates and reach a fresh dialog JID without cycling, allowing truthful replay closure to continue past dialog `1`.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-decision-a922.md`
- CA_ID `a922-go2f-seed19-r39-dialog-preflight-fallback-cycle-proof-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python collections deque rotate documentation`
- **Date/time (local):** `2026-03-23 15:27 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3/library/collections.html#collections.deque.rotate`
- **Found ready-made solutions:** Python's docs frame rotation as deterministic sequence traversal; the practical reuse here is to carry explicit visited-state while rotating over a bounded candidate list.
- **Decision:** `build` a bounded proof-tooling fix in local replay fallback selection.
- **Why:** the replay engine already has the correct phases and candidate generation; the bug is visited-state bookkeeping.
- **Rejected options:** runtime changes, acceptance-gate weakening, skipping contaminated preflight.

## Root cause (mandatory)
- **Symptom:** replay `r39` remains non-canonical because contaminated dialog preflight keeps rotating among fallback JIDs before the next truthful blocker can surface.
- **Minimal reproduction:** `r39` shows dialog `1` strict-green through turn `15`, but dialog `2` never records a row while stdout repeats `preflight_clear` plus `preflight_fallback_jid` on contaminated JIDs.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r39/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r39/manual_audit.json`
  - `ops/diagnose.py:3288`
  - `ops/diagnose.py:19258`
- **Five Whys:**
  - Why does replay stall? Contaminated preflight keeps picking another fallback JID.
  - Why does it keep picking more JIDs? The selector still sees earlier contaminated allowlist entries as available.
  - Why are earlier entries still available? The shared tried set only contains chosen fallback candidates, not the current contaminated JID.
  - Why is that a bug? Allowlist rotation can revisit already-failed JIDs and delay/loop fresh non-allowlist generation.
  - Why is this the right layer? No runtime behavior is being reclassified here; only replay isolation bookkeeping is wrong.
- **Root cause statement:** replay fallback-JID rotation does not persist the current contaminated JID in the shared tried set, so repeated preflight contamination can revisit allowlist entries instead of exhausting them.
- **Fix mechanism:** persist the current contaminated JID inside `_llm_quality_select_fallback_jid(...)`, add deterministic coverage for allowlist exhaustion across repeated selector calls, and then re-run replay.

## Reuse-first plan (mandatory)
- **Internal reuse:** `_llm_quality_select_fallback_jid(...)`, `_llm_quality_generate_unique_jid(...)`, existing JID-mode tests.
- **External reuse:** `https://docs.python.org/3/library/collections.html#collections.deque.rotate`
- **Why not reinvent the wheel:** candidate generation and allowlist-first policy already exist; only state tracking is wrong.

## Invariant
Do not change runtime behavior, do not weaken replay/oracle gates, and do not promote non-canonical replay artifacts to closure evidence.

## Scope
`ops/diagnose.py` fallback-JID bookkeeping plus deterministic proof coverage in `truffles-api/tests/test_booking_quality_jid_mode.py`.

## Out of scope
- runtime `reasoning_core.py` edits
- acceptance lock/full runs
- baseline updates

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Persist the current contaminated JID in the shared tried-set inside fallback selection.
2. Add deterministic regression that repeated selector calls exhaust the allowlist before minting a fresh dialog JID.
3. Rerun focused proof tests.
4. Run one fresh replay to verify the old dialog-preflight loop no longer blocks dialog progression.

## DoD
- repeated fallback-JID selection no longer revisits contaminated allowlist JIDs;
- focused deterministic proof is green;
- partial replay evidence proves progression beyond the old `r39` stall boundary.

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` during implementation; replay closure stays in the next block.
- **Max focused deterministic reruns:** `2` before stop-the-line and RCA refresh.
- **Stop condition:** if focused proof regressions fail or replay still cannot progress past the old `r39` stall boundary without new evidence, stop and refresh RCA before further runs.

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py`
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`

## Evidence
- code diff in `ops/diagnose.py`
- deterministic proof in `truffles-api/tests/test_booking_quality_jid_mode.py`
- partial replay evidence in `/tmp/booking_quality/a922-go2f-seed19-r40/{responses.jsonl,manual_audit.json}`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only proof-tooling repair in replay isolation before any acceptance evidence reuse.
- **Go/no-go signals:** focused deterministic proof is green; replay fallback no longer stalls at the old `r39` boundary; frozen routers remain untouched.
- **Rollback:** revert the bounded fallback-JID bookkeeping change and paired regression if replay isolation regresses.
- **Post-release monitoring window:** no production rollout in this block; monitor only the next fresh local replay and strict audit artifact.

## Rollback
Revert the bounded fallback-JID bookkeeping change and its paired regression.

## No-go
- no runtime edits
- no replay gate weakening
- no claims that interrupted replay is canonical closure

## Risks/blockers
- replay closure remains slow because each contaminated candidate still needs a real session-reset round-trip.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** truthful next runtime blocker is still unknown because replay `r40` was manually interrupted after proving broader progression only.
- **Why not in this block:** this block repairs proof-tooling isolation only.
- **Risk if deferred:** the team keeps burning time on non-canonical replay churn instead of the next surfaced blocker.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-canary-replay-a922.md`
- **Expiry/trigger to stop deferral:** immediate; the next step must be one fresh replay to completion or until the first truthful blocker surfaces.

## Next-block contract (mandatory)
- **Next block objective:** rerun the seed-`19` replay with the repaired fallback-JID selector and classify the first truthful blocker after dialog-preflight isolation.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r41 --status done --strict-artifacts`
- **Blocked-by conditions:** stale runtime parity, unaudited interrupted replay artifact, or failing focused proof regressions.
- **Owner role for closure:** Brain / Top Architect
