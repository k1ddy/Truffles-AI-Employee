# TP-2026-03-16-consultant-core-service-choice-specialist-exact-time-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-EXACT-TIME-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-DAYPART-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-daypart-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SPECIALIST-EXACT-TIME-NEIGHBOR-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded specialist-availability seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-choice specialist exact-time followups вида `Какой мастер будет делать маникюр завтра в 18:00?` и `Какой мастер будет делать маникюр в субботу в 18:00?`, но только когда `reply_slot=service`, resume-contract остаётся booking-owned, service grounding уже явен в самом тексте, temporal token остаётся pure day без daypart, и точное время уже присутствует в самом inbound. Frozen router должен получать уже готовый collect-contract на переход к выбору мастера (`next_question=name`, `open_questions=[name]`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=specific_time`, `resolution_mode=referent_followup`, `active_question_relation=specialist_availability_followup`) вместо первого policy-core LLM pass на этих turns, при этом pure day/daypart specialist followups, weekday/weekend hybrids, grounded specialist transitions, active-name booking followups и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-daypart-followup-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/booking_signal_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `python3 - <<'PY' ... detect_policy_core_route_snapshot("Какой мастер будет делать маникюр завтра в 18:00?", ...) ... PY`
  - `python3 - <<'PY' ... detect_policy_core_route_snapshot("Какой мастер будет делать маникюр в субботу в 18:00?", ...) ... PY`
  - `sed -n '25420,25540p' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - frozen `decision.py` already preserves the specialist-availability owner for `goal=booking`, `next_question=name`, `pending_question_target=specialist`, `active_question_relation=specialist_availability_followup`, `capability in {live_availability, bookability}`, and `temporal_scope=specific_time`; the existing grounded specialist transition test proves that downstream contract.
  - ingress already owns service-choice day, daypart, weekday, and weekend specialist followups, but explicit exact-time turns like `завтра в 18:00` still fall through to the grounded `master_query` fact bridge.
  - `extract_relative_date_token(...)`, `normalize_resolved_datetime_value(...)`, and `extract_time_token(...)` already separate pure day + exact-time turns from daypart + exact-time and weekday/weekend hybrid turns, so ingress can reuse existing normalization rather than inventing a new parser.
- `Detected drift (docs vs code)`: the next contract-compatible service-choice specialist seam after the daypart bridge is the pure day + exact-time family, and ingress still lacks its own direct specialist-name collect override branch for that family.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org 3.12 str.join documentation`
- **Date/time (local):** `2026-03-16 19:12 +0500`
- **Why this query is precise:** this block needs one narrow way to compose an already-normalized day token with an already-extracted exact-time token into a bounded datetime string without introducing a new parser.
- **Sources opened (from this query):**
  - `Built-in Functions — str.join` — `https://docs.python.org/3.12/library/stdtypes.html#str.join`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `str.join()` is the standard primitive for composing a deterministic bounded string from known parts while skipping parser widening.
- **Decision:** `reuse + integrate` — reuse `resolve_master_intent(...)`, `extract_relative_date_token(...)`, `normalize_resolved_datetime_value(...)`, `extract_time_token(...)`, request-scoped policy overrides, and the frozen downstream specialist-availability owner predicate; add only one narrow exact-time detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case service-choice specialist exact-time followups
  - widening this block into weekday/weekend exact-time hybrids
  - widening this block into daypart+exact-time or active-name ownership
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit service-grounded specialist exact-time followups still start with the grounded `master_query` fact branch instead of the preserved specialist-name collect contract.
- **Minimal reproduction:**
  1. Load a conversation with `expected_reply_type=service` and booking-owned resume context.
  2. Send `Какой мастер будет делать маникюр завтра в 18:00?` through `reasoning_core`.
  3. Observe that ingress currently has no exact-time service-choice specialist branch, so the turn falls through to the grounded `master_query` fact bridge instead of the preserved collect-name contract.
- **Evidence to capture:**
  - ingress primes a bounded specialist exact-time override before delegate execution when the gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit service-grounded exact-time specialist turns route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, and `resolution_mode="referent_followup"`
  - pure day/daypart specialist followups, weekday/weekend hybrids, turns without `reply_slot=service`, and daypart+exact-time turns stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress has no explicit exact-time branch ahead of the grounded `master_query` fact bridge.
  2. Why can it be moved safely now? Because the frozen owner predicate already preserves the downstream specialist-name collect contract for `goal=booking`, `next_question=name`, and `active_question_relation=specialist_availability_followup`.
  3. Why not leave it inside the generic `master_query` bridge? Because exact-time specialist followups need collect ownership toward name selection, not fact ownership.
  4. Why is this a bounded slice? Because the service is grounded in the text, the expected reply slot is already `service`, and pure day + exact-time tokens can be distinguished from daypart or hybrid scopes using existing normalization helpers.
  5. Why does this reduce drift? Because another specialist-selection collect contract moves out of frozen runtime and into a typed ingress-owned override without widening execution ownership.
- **Root cause statement:** service-choice specialist explicit exact-time followups remained in frozen runtime because ingress lacked the narrow day+time detector needed to distinguish them from both the day/daypart specialist info-followup seams and the grounded `master_query` fact bridge before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit service-grounded specialist exact-time followups with neighbor-seam exclusions and daypart/weekend/weekday rejection
  - emit a bounded policy snapshot branch keyed by `reply_slot=service` plus grounded service query plus normalized day+time scope
  - verify priming, exclusion, downstream contract compatibility, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing `resolve_master_intent(...)` service grounding
  - existing `extract_relative_date_token(...)`, `normalize_resolved_datetime_value(...)`, and `extract_time_token(...)`
  - existing frozen downstream specialist-availability owner predicate and grounded transition evidence
  - existing neighbor-seam exclusions for services-overview, location, hours, promotions, contact, duration, pricing, and reschedule/cancel
- **External reuse:**
  - official Python `str.join` documentation
- **Why not reinvent the wheel:** the repo already has the grounded service signal, time/day normalization, override transport, and downstream owner contract; this block only needs one exact-time detector and one bounded collect branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `26`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, focused deterministic tests, one downstream contract test, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden service-choice specialist exact-time turns.
- No override bleed across requests or unrelated message text.
- No override when `reply_slot` is not `service`.
- No widening into weekday/weekend exact-time hybrids or active-name ownership.

## Scope
- Add a narrow detector for explicit service-grounded specialist exact-time followups.
- Add a bounded policy snapshot branch for `reply_slot=service` exact-time specialist collect-to-name.
- Add deterministic intent/reasoning/message-endpoint tests for the new seam.
- Sync required canon/session artifacts.

## Out of scope
- pure day specialist followups
- pure daypart specialist followups
- weekday/weekend hybrid exact-time specialist followups
- daypart+exact-time specialist followups
- grounded specialist transition
- active-name booking-time followups
- generic hours routing
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-exact-time-followup-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
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
2. Add a narrow service-choice specialist exact-time detector and a bounded collect-to-name snapshot branch.
3. Add deterministic tests for detection, snapshot gating, daypart/hybrid exclusions, delegate priming, downstream collect-owner preservation, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded service-choice specialist exact-time override before delegate execution when the gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit service-grounded exact-time specialist turns route to `next_question="name"`, `open_questions=["name"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, and `resolution_mode="referent_followup"`
- pure day/daypart specialist followups, weekday/weekend hybrids, turns without `reply_slot=service`, and daypart+exact-time turns do not get this override
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'service_choice_master_availability_followup_keeps_time_collect or service_choice_specialist_weekday_followup_keeps_time_collect or service_choice_specialist_weekend_followup_keeps_time_collect or service_choice_specialist_daypart_followup_keeps_time_collect or service_choice_specialist_exact_time_followup_transitions_to_name_collect'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded exact-time detector in `truffles-api/app/services/info_signal_service.py`
- bounded collect-to-name snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal/message-endpoint tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into weekday/weekend exact-time hybrids, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + focused message-endpoint + runtime-contracts + architecture suite + packet + arch guard + session check all green
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
  - active block metadata must match the actual service-choice specialist exact-time bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution in ingress
- no widening this detector into weekday/weekend exact-time or daypart+exact-time families in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- exact-time specialist wording can overlap with the grounded `master_query` fact bridge if the detector is widened carelessly
- downstream preservation still depends on the frozen specialist-availability owner predicate, so the collect-to-name contract must stay exact

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - weekday/weekend hybrid exact-time specialist followups remain outside ingress ownership
  - broader booking outcome semantics still remain in frozen `decision.py`
  - continuity is still not a single writer
- **Why not in this block:**
  - weekday/weekend hybrid exact-time routing is a separate signal family and should stay split
- **Risk if deferred:**
  - one neighboring specialist-selection family remains on the legacy-first path a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-next-specialist-exact-time-neighbor-seam-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next specialist exact-time seam can reuse the same owner predicate without new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded specialist-availability seam after the pure exact-time followup, only if it can remain read-only and contract-compatible with the existing specialist owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k 'specialist and exact_time'`
- **Blocked-by conditions:** frozen-router edits, generic hours routing drift, or continuity-writer expansion
- **Owner role for closure:** `Top Architect`
