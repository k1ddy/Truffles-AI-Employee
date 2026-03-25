# TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-DEICTIC-TIME-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-TIME-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-ACTIVE-AVAILABILITY-FOLLOWUP-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded availability followup seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit deictic-time availability followups вида `А есть ли у вас места в это время?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, `reply_slot=name`, и active booking datetime с exact time token. Frozen router должен получать уже готовый collect-contract (`next_question=name`, `temporal_scope=specific_time`, `resolution_mode=referent_followup`) вместо первого policy-core LLM pass на этих turns, при этом live slot execution ownership, alternate-time offers, day/date-range availability, named-specialist turns и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922.md`
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
  - `sed -n '132,160p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '864,910p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '278,590p' truffles-api/app/core/intent_routing.py`
  - `sed -n '560,660p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '25420,25890p' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - ingress already owns explicit specific-time availability followups when the user supplies a new time token under active-name resume.
  - deictic-time availability followups like `А есть ли у вас места в это время?` still start from the first policy-core LLM pass inside frozen `decision.py`, even though the exact contract is already deterministic in existing runtime tests.
  - `ReasoningCoreConversationSnapshot` already projects service referent and reply slot, but it does not yet project the active booking datetime token needed to bind this deictic followup to a specific requested time.
  - `route_llm_policy_core(...)` already accepts the exact contract fields needed for this seam; ingress only lacks the snapshot projection plus the narrow deictic detector.
- `Detected drift (docs vs code)`: this active-name deictic-time followup family is still legacy-owned although the ingress snapshot seam and request-scoped override transport are already in place.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any function documentation`
- **Date/time (local):** `2026-03-16 17:10 +05`
- **Why this query is precise:** this block needs a short-circuit conjunctive gate over booking-active state, service referent, active booking datetime, reply slot, and a narrow deictic detector without growing another branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `any(iterable)` is the standard short-circuit primitive for small deictic-phrase groups and supports a narrow detector without widening this block.
- **Decision:** `reuse + integrate` — reuse the existing active conversation snapshot, request-scoped policy override seam, and neighboring exclusion helpers; add only one active booking datetime projection, one narrow deictic detector, and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case this followup family
  - widening this block into live availability execution or alternate-slot generation
  - adding a generic deictic followup bridge that also covers day/date-range wording in the same block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit deictic-time availability followups under active-name resume still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, `reply_slot="name"`, and active booking datetime `15:00`.
  2. Send `А есть ли у вас места в это время?` through `reasoning_core`.
  3. Observe that, before this block, ingress had no bounded snapshot for this exact family and delegated the first semantic decision to frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded deictic-time availability override before delegate execution when the snapshot gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit deictic-time followups route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
  - turns without the active booking datetime do not get this override
  - explicit new time tokens stay in the already-landed specific-time followup slice instead of this one
  - neighboring pricing/duration/master/hours/location/promotions/contact seams remain unchanged
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress currently only bridges followups that either ask for missing time or supply a new explicit time token.
  2. Why does that matter? Because frozen `decision.py` still owns the first semantic decision for a common active-booking followup family.
  3. Why not migrate broader availability now? Because alternate-slot generation and live execution would widen the block beyond a safe bounded slice.
  4. Why can ingress own this safely now? Because the active conversation snapshot already carries most of the required booking state and only needs the current exact-time token projected in read-only form.
  5. Why does this reduce drift? Because another explicit booking followup decision moves out of frozen runtime and into a typed ingress-owned contract with exact snapshot gating.
- **Root cause statement:** active-name deictic-time availability followups remained in frozen `decision.py` because ingress lacked the active booking datetime projection and the narrow deictic-time detector needed to emit the exact collect contract before delegate execution.
- **Fix mechanism:**
  - project the active booking exact-time token into the read-only conversation snapshot
  - add a narrow detector for explicit deictic-time availability followups with neighboring-seam exclusions
  - emit a bounded policy snapshot branch keyed by active booking datetime instead of a newly supplied time token
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.reply_slot`
  - existing active booking plus service referent projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing booking/time helpers: `extract_time_token(...)`, `has_explicit_date_signal(...)`, `normalize_resolved_datetime_value(...)`
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, master
  - existing `route_llm_policy_core(...)` schema validation for `resolution_mode`, `temporal_scope`, and followup fields
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the snapshot seam, override transport, and neighboring exclusion helpers; this block only needs one extra read-only state token, one narrow deictic detector, and one bounded snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one extra snapshot token, one detector, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden deictic-time availability followups.
- No override bleed across requests or unrelated message text.
- No override when the active booking exact-time token is absent.
- No widening into live availability execution or alternate-slot generation.

## Scope
- Project the active booking exact-time token into `ReasoningCoreConversationSnapshot`.
- Add a narrow detector for explicit deictic-time availability followups.
- Add a bounded policy snapshot branch and deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- live slot execution ownership
- alternate-slot generation
- day/date-range availability followups
- named-specialist availability followups
- frozen-router edits
- proof-path work
- continuity work beyond read-only snapshot projection

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
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
2. Project the active booking exact-time token into `ReasoningCoreConversationSnapshot`.
3. Add a narrow deictic-time detector and a bounded active-name deictic-time snapshot branch.
4. Add deterministic tests for detection, snapshot gating, explicit-time exclusion, delegate priming, override consumption, and reset safety.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded deictic-time availability override before delegate execution when the snapshot gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit deictic-time followups route to `next_question="name"`, `open_questions=["name"]`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
- turns without the active booking exact-time token do not get this override
- turns with explicit new time tokens stay outside this slice
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
- bounded deictic-time detector in `truffles-api/app/services/info_signal_service.py`
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
  - active block metadata must match the actual deictic-time availability followup bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous active-name specific-time followup bridge only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into day/date-range followups in the same block
- no heuristic spillover into unrelated info seams

## Risks / blockers
- deictic phrasing can easily overfit if the detector grows past explicit `это время` wording
- if the snapshot cannot provide a stable exact-time token, the block must stop instead of guessing

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- explicit deictic day/date-range availability followups remain legacy-owned
- alternate-slot and occupancy followups remain legacy-owned
- broader planner/outcome ownership still remains in frozen `decision.py`

### Why not in this block
- those families need either broader temporal anchoring or live availability execution behavior and would widen the block beyond a safe bounded cut

### Risk if deferred
- frozen runtime still owns neighboring booking followup families, so semantic drift surface remains non-zero

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922.md`
- next bounded availability followup TP after this block

### Expiry/trigger to stop deferral
- stop deferral once the next availability followup seam can be expressed with the existing snapshot plus one extra bounded detector and no frozen-router edits

## Next-block contract (mandatory)
### Next block objective
- take the next bounded active availability followup seam after deictic-time, preferably deictic day/date-range only if it can stay read-only and ingress-owned

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'active_name_deictic_time_availability or active_name_time_availability_followup'`

### Blocked-by conditions
- missing stable active booking temporal anchor in the read-only snapshot
- detector widening into alternate-slot generation or live execution semantics
- any need to edit frozen router files

### Owner role for closure
- `Top Architect`
