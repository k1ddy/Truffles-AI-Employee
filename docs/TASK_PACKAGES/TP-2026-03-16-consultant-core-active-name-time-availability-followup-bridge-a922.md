# TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-TIME-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOOKABILITY-TIME-COLLECT-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-bookability-time-collect-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-ACTIVE-AVAILABILITY-FOLLOWUP-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded availability followup seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit specific-time availability followups вида `А есть ли свободные слоты на 15:00?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, `expected_reply_type=name`, и `expected_reply_reason=booking_time_availability_followup`. Frozen router должен получать уже готовый collect-contract (`next_question=name`, `temporal_scope=specific_time`, `active_question_relation=ask_about_requested_slot`) вместо первого policy-core LLM pass на этих turns, при этом live slot execution ownership, specialist-choice execution, partial-date/day-range availability, named-specialist turns и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-bookability-time-collect-policy-override-bridge-a922.md`
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
  - `sed -n '128,160p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '856,930p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '84,150p' truffles-api/app/core/intent_routing.py`
  - `sed -n '278,548p' truffles-api/app/core/intent_routing.py`
  - `sed -n '515,575p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '1832,1888p' truffles-api/tests/test_intent.py`
  - `sed -n '6840,6918p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - ingress already owns active booking plus service referent projection and the bounded missing-temporal-scope collect bridge, but explicit specific-time availability followups under active-name resume still fall through to the first policy-core LLM pass inside frozen `decision.py`.
  - `ReasoningCoreConversationSnapshot` already projects `expected_reply_type`, but not `expected_reply_reason`; frozen runtime uses `booking_time_availability_followup` to preserve this exact owner family.
  - `route_llm_policy_core(...)` already accepts `pending_question_act`, `pending_question_target`, and `active_question_relation`, but `PolicyCoreRouteSnapshot` does not yet carry them.
  - deterministic tests already codify the exact semantic contract for this family: `goal=booking`, `next_question=name`, `temporal_scope=specific_time`, `pending_question_act=ask_about_requested_slot`, `pending_question_target=time`, `active_question_relation=ask_about_requested_slot`, `resolution_mode=referent_followup`.
- `Detected drift (docs vs code)`: active-name specific-time availability followups are still semantic-owned by the first policy-core LLM pass in frozen runtime even though the ingress snapshot gate and request-scoped override transport already exist.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python all function documentation`
- **Date/time (local):** `2026-03-16 16:00 +05`
- **Why this query is precise:** this block needs a conjunctive gate over active booking state, service referent, expected-reply resume state, and a narrow text detector; the implementation should stay a short-circuit composition layer instead of another branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#all`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `all(iterable)` is the standard short-circuit composition primitive and matches the bounded gate style already used in routing-neutral helpers.
- **Decision:** `reuse + integrate` — reuse existing booking/time signal helpers, the active conversation snapshot, and the request-scoped policy override seam; add only one bounded specific-time followup detector, one snapshot projection field, and one policy snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case this followup family
  - widening this block into live availability execution or specialist-choice execution
  - using LLM specialist-hint extraction in ingress just to disambiguate this family
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit specific-time availability followups under active-name resume still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, `expected_reply_type=name`, and `expected_reply_reason=booking_time_availability_followup`.
  2. Send `А есть ли свободные слоты на 15:00?` through `reasoning_core`.
  3. Observe that, before this block, ingress had no bounded followup snapshot for this exact family and delegated the first semantic decision to frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded active-name time-availability followup override before delegate execution when the snapshot resume state matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit specific-time followups route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `temporal_scope="specific_time"`, `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, `active_question_relation="ask_about_requested_slot"`, `resolution_mode="referent_followup"`
  - turns without the active-name resume state do not get this override
  - turns with explicit date scope stay outside this slice
  - neighboring pricing/duration/master/hours/location/promotions/contact seams stay unchanged
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress only bridges earlier booking collect/fact seams today.
  2. Why does that matter? Because frozen `decision.py` still owns the first semantic decision for a common active-booking followup family.
  3. Why not migrate broader availability now? Because live slot execution and specialist routing would widen the block beyond a safe bounded slice.
  4. Why can ingress own this safely now? Because the active conversation snapshot already exposes the needed booking/service resume state and the policy override seam already transports the exact contract fields.
  5. Why does this reduce drift? Because another explicit followup decision moves out of frozen runtime and into a typed ingress-owned contract with explicit resume-state gating.
- **Root cause statement:** active-name specific-time availability followups remained in frozen `decision.py` because ingress lacked both the narrow resume-state gate and the bounded specific-time detector needed to emit the exact collect contract before delegate execution.
- **Fix mechanism:**
  - project `expected_reply_reason` into the read-only active conversation snapshot
  - extend `PolicyCoreRouteSnapshot` with the existing pending-question followup fields already accepted by `route_llm_policy_core(...)`
  - add a narrow detector for explicit specific-time availability followups and gate it by the active-name resume state
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.reply_slot`
  - existing active booking plus service referent projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing booking/time helpers: `extract_time_token(...)`, `has_explicit_date_signal(...)`, `normalize_resolved_datetime_value(...)`
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, master
  - existing `route_llm_policy_core(...)` schema validation for `pending_question_act`, `pending_question_target`, and `active_question_relation`
- **External reuse:**
  - official Python `all(...)` documentation
- **Why not reinvent the wheel:** the repo already has the resume-state projection, followup schema fields, and override transport; this block only needs one extra projected state token, one narrow detector, and one bounded snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with small snapshot/schema expansion, one detector, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden active-name specific-time followups.
- No override bleed across requests or unrelated message text.
- No override when the active-name resume state is absent.
- No widening into live availability execution or specialist-choice execution.

## Scope
- Project `expected_reply_reason` into the read-only conversation snapshot.
- Extend `PolicyCoreRouteSnapshot` with pending-question followup fields already accepted downstream.
- Add a narrow detector for explicit active-name specific-time availability followups.
- Add a bounded policy snapshot branch and deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- live slot execution ownership
- specialist-choice execution ownership
- partial-date/day-range availability followups
- frozen-router edits
- proof-path work
- continuity work beyond read-only snapshot projection

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922.md`
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
2. Project the extra resume-state token into `ReasoningCoreConversationSnapshot` and extend `PolicyCoreRouteSnapshot` with existing pending-question followup fields.
3. Add a narrow specific-time followup detector and a bounded active-name followup snapshot branch.
4. Add deterministic tests for detection, resume-state gating, explicit-date exclusion, delegate priming, override consumption, and reset safety.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded active-name specific-time availability followup override before delegate execution when the snapshot resume state matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit specific-time followups route to `next_question="name"`, `open_questions=["name"]`, `temporal_scope="specific_time"`, `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, `active_question_relation="ask_about_requested_slot"`, `resolution_mode="referent_followup"`
- turns without the active-name resume state do not get this override
- explicit date-scope turns remain outside this slice
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
- bounded active-name specific-time detector in `truffles-api/app/services/info_signal_service.py`
- bounded followup snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into live availability/specialist execution ownership, stop and split
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
  - active block metadata must match the actual active-name specific-time followup bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bookability collect bridges.

## No-go
- no edits in `truffles-api/app/routers/webhook/decision.py`
- no edits in `truffles-api/app/routers/webhook/booking.py`
- no edits in `truffles-api/app/routers/webhook/pending.py`
- no override when the active-name resume state is missing
- no widening into live availability execution, specialist-choice execution, or partial-date/day-range followups
- no proof/continuity side quests in this block

## Риски/блокеры
- a too-broad detector could hijack specialist-choice or live availability turns that need broader semantics.
- missing resume-state gating could leak this override into unrelated `expected_reply_type=name` flows.
- named-specialist turns are intentionally left outside this slice and must stay delegated.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- live availability execution remains frozen-runtime-owned.
- named-specialist and day-range availability followups remain outside ingress ownership.
- broader booking planner and boundary ownership remain legacy-mixed.

### Why not in this block
- those paths combine live slot execution, specialist routing, and richer temporal arbitration that would widen this bounded followup slice into a much larger migration.

### Risk if deferred
- active-booking availability followups are only partially ingress-owned until adjacent specific-day and specialist followup seams are migrated.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-day-availability-followup-bridge-a922.md` (planned)

### Expiry/trigger to stop deferral
- stop deferral once the next bounded availability followup seam can be expressed without taking live slot execution ownership.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether a bounded active-name specific-day availability followup can migrate next without taking live execution ownership.
- **First deterministic check command:** `rg -n "specific_day|day-range|booking_time_availability_followup|ask_about_requested_slot|calendar.list_slots" truffles-api/app/services/info_signal_service.py truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** active-name specific-time followup bridge must land green first; the next seam must keep live slot execution and named-specialist execution outside scope.
- **Owner role for closure:** `Top Architect`
