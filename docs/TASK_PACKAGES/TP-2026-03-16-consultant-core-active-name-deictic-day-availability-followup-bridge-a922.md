# TP-2026-03-16-consultant-core-active-name-deictic-day-availability-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-DEICTIC-DAY-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-DEICTIC-TIME-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-ACTIVE-AVAILABILITY-FOLLOWUP-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded availability followup seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit deictic-day availability followups вида `У вас есть свободные слоты на этот день?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, `reply_slot=name`, и active booking exact-time token. Frozen router должен получать уже готовый collect-contract (`next_question=name`, `capability=bookability`, `temporal_scope=specific_time`, `resolution_mode=referent_followup`) вместо первого policy-core LLM pass на этих turns, при этом live slot execution ownership, alternate-slot generation, explicit new-date turns, named-specialist turns и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '140,160p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '872,925p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '548,640p' truffles-api/app/core/intent_routing.py`
  - `sed -n '620,700p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '25686,25890p' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - ingress already owns explicit specific-time availability followups and deictic-time availability followups under active-name resume.
  - explicit deictic-day followups like `У вас есть свободные слоты на этот день?` still start from the first policy-core LLM pass inside frozen `decision.py`, even though existing runtime tests already pin the exact collect contract and owner axes.
  - the current read-only snapshot already provides the exact-time anchor needed for this seam; no new continuity writer is required.
  - the legacy runtime test for this family expects `capability=bookability`, `temporal_scope=specific_time`, `next_question=name`, `pending_question_act=ask_about_requested_slot`, `pending_question_target=time`, and `active_question_relation=ask_about_requested_slot`.
- `Detected drift (docs vs code)`: this active-name deictic-day followup family is still legacy-owned although ingress now has the exact-time snapshot anchor and override transport needed to express it as a bounded contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python all function documentation`
- **Date/time (local):** `2026-03-16 16:36 +05`
- **Why this query is precise:** this block needs a conjunctive detector over deictic-day wording, availability wording, exact-time snapshot presence, and neighboring-seam exclusions without widening into a branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#all`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `all(iterable)` is the standard short-circuit primitive for compact conjunctive gating over multiple exclusion predicates.
- **Decision:** `reuse + integrate` — reuse the exact-time snapshot anchor from the previous block, the request-scoped policy override seam, and existing neighboring exclusion helpers; add only one narrow deictic-day detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case this followup family
  - widening this block into live slot execution or alternate-slot generation
  - folding explicit deictic-day and explicit new-date followups into one detector
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit deictic-day availability followups under active-name resume still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, `reply_slot="name"`, and active booking exact-time token `03:00`.
  2. Send `У вас есть свободные слоты на этот день?` through `reasoning_core`.
  3. Observe that, before this block, ingress had no bounded snapshot for this family and delegated the first semantic decision to frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded deictic-day availability override before delegate execution when the snapshot gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit deictic-day followups route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `capability="bookability"`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
  - turns without the active booking exact-time token do not get this override
  - turns with explicit new date/day scope stay outside this slice
  - neighboring pricing/duration/master/hours/location/promotions/contact seams remain unchanged
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress currently only bridges missing-time, explicit specific-time, and deictic-time followups.
  2. Why does that matter? Because frozen `decision.py` still owns the first semantic decision for another common active-booking followup family.
  3. Why not migrate broader day/date availability now? Because explicit new-date turns and alternate-slot generation would widen the block beyond a safe bounded slice.
  4. Why can ingress own this safely now? Because the exact-time snapshot anchor needed for this family already exists from the previous block.
  5. Why does this reduce drift? Because another explicit booking followup decision moves out of frozen runtime and into a typed ingress-owned contract without introducing a new writer or execution owner.
- **Root cause statement:** active-name deictic-day availability followups remained in frozen `decision.py` because ingress lacked the narrow deictic-day detector needed to reuse the already-projected exact-time snapshot anchor and emit the exact collect contract before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit deictic-day availability followups with neighboring-seam exclusions
  - emit a bounded policy snapshot branch keyed by the existing active booking exact-time token
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.booking_time_token`
  - existing active booking plus service referent projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing booking/time helpers: `extract_time_token(...)`, `has_explicit_date_signal(...)`, `normalize_resolved_datetime_value(...)`
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, master
  - existing `route_llm_policy_core(...)` schema validation for `capability`, `temporal_scope`, and followup fields
- **External reuse:**
  - official Python `all(...)` documentation
- **Why not reinvent the wheel:** the repo already has the exact-time snapshot anchor, override transport, and neighboring exclusion helpers; this block only needs one narrow deictic-day detector and one bounded snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden deictic-day availability followups.
- No override bleed across requests or unrelated message text.
- No override when the active booking exact-time token is absent.
- No widening into live slot execution or alternate-slot generation.

## Scope
- Add a narrow detector for explicit deictic-day availability followups.
- Add a bounded policy snapshot branch that reuses the existing active booking exact-time token.
- Add deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- live slot execution ownership
- alternate-slot generation
- explicit new-date/daypart/day-range availability turns
- named-specialist availability followups
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-day-availability-followup-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add a narrow deictic-day detector and a bounded snapshot branch that reuses the active booking exact-time token.
3. Add deterministic tests for detection, snapshot gating, explicit-date exclusion, delegate priming, override consumption, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded deictic-day availability override before delegate execution when the snapshot gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit deictic-day followups route to `next_question="name"`, `open_questions=["name"]`, `capability="bookability"`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
- turns without the active booking exact-time token do not get this override
- turns with explicit new date/day scope stay outside this slice
- neighboring pricing/duration/master/hours/location/promotions/contact seams remain unchanged
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded deictic-day detector in `truffles-api/app/services/info_signal_service.py`
- bounded followup snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into live availability/alternate-slot execution ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + runtime-contracts + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's signal/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to doc-heavy micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual deictic-day availability followup bridge being executed.

## Rollback
1. Revert `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous deictic-time availability bridge only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into explicit new-date/daypart/date-range followups in the same block
- no heuristic spillover into unrelated info seams

## Risks / blockers
- deictic-day phrasing can easily overfit if the detector grows past explicit `этот день` wording
- if the detector starts capturing explicit new-date turns, the block must stop instead of widening

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- explicit new-date/daypart/day-range availability followups remain legacy-owned
- alternate-slot and occupancy followups remain legacy-owned
- broader planner/outcome ownership still remains in frozen `decision.py`

### Why not in this block
- those families need broader temporal anchoring or live availability execution behavior and would widen the block beyond a safe bounded cut

### Risk if deferred
- frozen runtime still owns neighboring booking followup families, so semantic drift surface remains non-zero

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922.md`
- next bounded availability followup TP after this block

### Expiry/trigger to stop deferral
- stop deferral once the next availability followup seam can be expressed with the existing exact-time snapshot anchor plus one narrow detector and no frozen-router edits

## Next-block contract (mandatory)
### Next block objective
- take the next bounded active availability followup seam after deictic-day, preferably explicit new-date/day-range only if it can stay read-only and ingress-owned

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'active_name_deictic_day_availability or active_name_deictic_time_availability'`

### Blocked-by conditions
- detector widening into explicit new-date routing or alternate-slot generation
- any need to edit frozen router files
- any need for new continuity writers or live execution ownership

### Owner role for closure
- `Top Architect`
