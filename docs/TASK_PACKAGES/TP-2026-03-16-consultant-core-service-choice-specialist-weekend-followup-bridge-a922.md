# TP-2026-03-16-consultant-core-service-choice-specialist-weekend-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-WEEKEND-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-GROUNDED-SPECIALIST-TRANSITION-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-grounded-specialist-transition-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SPECIALIST-AVAILABILITY-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded specialist-availability seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-choice specialist weekend followups вида `Какой мастер будет делать маникюр на выходных?`, но только когда `reply_slot=service`, resume-contract остаётся booking-owned, и service grounding уже явен в самом тексте. Frozen router должен получать уже готовый collect-contract (`next_question=datetime`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=weekend`, `resolution_mode=clarify_missing_time`, `pending_question_target=specialist`) вместо первого policy-core LLM pass на этих turns, при этом grounded specialist transition, specialist date-range followups, active-name booking followups, and frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-grounded-specialist-transition-bridge-a922.md`
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
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '6787,6838p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '24779,24915p' truffles-api/tests/test_message_endpoint.py`
  - `sed -n '820,930p' truffles-api/app/core/intent_routing.py`
  - `python3 - <<'PY' ... resolve_master_intent("Какой мастер будет делать маникюр на выходных?") ... PY`
- `FACT findings`:
  - frozen `decision.py` already preserves `service_choice_specialist_availability_followup` for `goal=info`, `collect_slot=datetime`, `expected_reply_type=service`, `resolution_mode=clarify_missing_time`, `pending_question_target=specialist`, `capability=live_availability`, and `temporal_scope in {specific_time, day, weekday, weekend}`.
  - `test_llm_policy_core_service_choice_master_availability_followup_keeps_time_collect` already proves the downstream specialist-followup contract for the service-grounded specific-time family and shows the frozen owner converts it into `booking_specialist_availability_followup` with `expected_reply_type=time`.
  - `resolve_master_intent(...)` already classifies `Какой мастер будет делать маникюр на выходных?` as an explicit master signal with grounded `service_query='Маникюр'`, which means ingress can reuse the existing service grounding instead of inventing new semantic hardcode.
  - ingress currently has no bounded weekend detector in front of the grounded `master_query` fact bridge, so these turns still reach frozen runtime for the first policy-core decision.
- `Detected drift (docs vs code)`: the next contract-compatible specialist seam after grounded transition is the service-choice specialist weekend followup, and ingress still lacks its own weekend-specific collect override branch.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org 3.12 str.startswith documentation`
- **Date/time (local):** `2026-03-16 18:26 +0500`
- **Why this query is precise:** this block needs one narrow weekend-marker gate over normalized text while staying bounded and not widening into a regex forest.
- **Sources opened (from this query):**
  - `Built-in Types — str.startswith` — `https://docs.python.org/3.12/library/stdtypes.html#str.startswith`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python string prefix checks are standard and side-effect-free for bounded lexical gates; repo helpers already layer this pattern through tokenized prefix matching.
- **Decision:** `reuse + integrate` — reuse the existing `resolve_master_intent(...)`, grounded service query semantics, request-scoped policy override seam, and frozen downstream specialist-followup owner predicate; add only one narrow weekend detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case weekend specialist followups
  - widening this block into generic hours/weekend service capability routing
  - widening this block into grounded specialist transition or date-range ownership that is already covered by other bridges
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit service-grounded specialist weekend followups still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load a conversation with `expected_reply_type=service` and booking-owned resume context.
  2. Send `Какой мастер будет делать маникюр на выходных?` through `reasoning_core`.
  3. Observe that ingress currently has no weekend-specific service-choice specialist branch, so the turn falls through to the frozen delegate for the first policy-core decision.
- **Evidence to capture:**
  - ingress primes a bounded service-choice specialist weekend override before delegate execution when the gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit service-grounded weekend specialist turns route to `goal="info"`, `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="weekend"`, and `resolution_mode="clarify_missing_time"`
  - turns without `reply_slot=service` or without explicit service grounding do not get this override
  - grounded specialist transition and specialist date-range followups stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress has no weekend-specific branch ahead of the grounded `master_query` fact bridge.
  2. Why can it be moved safely now? Because the frozen owner predicate already preserves this service-choice specialist collect contract for `temporal_scope=weekend`.
  3. Why not handle it in the generic grounded `master_query` bridge? Because weekend specialist followups need collect ownership with `next_question=datetime`, not fact ownership.
  4. Why is this a bounded slice? Because the service is grounded in the text, the expected reply slot is already `service`, and no new continuity writer or frozen-router edit is required.
  5. Why does this reduce drift? Because another specialist-followup collect contract moves out of frozen runtime and into a typed ingress-owned override without widening execution ownership.
- **Root cause statement:** service-choice specialist weekend followups remained in frozen `decision.py` because ingress lacked the narrow weekend detector needed to distinguish them from the existing grounded `master_query` fact bridge and convert the already-grounded service signal into the preserved collect contract before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit service-grounded specialist weekend followups with neighbor-seam exclusions
  - emit a bounded policy snapshot branch keyed by `reply_slot=service` plus grounded service query plus weekend scope
  - verify priming, exclusion, downstream contract compatibility, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing `resolve_master_intent(...)` service grounding
  - existing neighbor-seam exclusions for services-overview, location, hours, promotions, contact, duration, pricing, and reschedule/cancel
  - existing frozen downstream specialist-followup owner predicate and message-endpoint evidence
- **External reuse:**
  - official Python `str.startswith` documentation
- **Why not reinvent the wheel:** the repo already has the grounded service signal, override transport, and downstream owner contract; this block only needs one weekend detector and one bounded collect branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `25`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, one focused downstream contract test, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden service-choice specialist weekend turns.
- No override bleed across requests or unrelated message text.
- No override when `reply_slot` is not `service`.
- No widening into hours/weekend service capability routing or other specialist seams.

## Scope
- Add a narrow detector for explicit service-grounded specialist weekend followups.
- Add a bounded policy snapshot branch for `reply_slot=service` weekend specialist collect.
- Add deterministic tests, including one downstream focused message-endpoint contract test.
- Sync required canon/session artifacts.

## Out of scope
- grounded specialist transition
- specialist date-range followups
- active-name booking-time followups
- generic hours/weekend info routing
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-weekend-followup-bridge-a922.md`
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
2. Add a narrow service-choice specialist weekend detector and a bounded collect snapshot branch.
3. Add deterministic tests for detection, snapshot gating, delegate priming, downstream contract compatibility, exclusion, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded service-choice specialist weekend override before delegate execution when the gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit service-grounded weekend specialist turns route to `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="weekend"`, and `resolution_mode="clarify_missing_time"`
- turns without `reply_slot=service` or without explicit service grounding do not get this override
- grounded specialist transition and specialist date-range followups stay outside this slice
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'service_choice_master_availability_followup or grounded_specialist_availability_transitions_to_name_collect'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded weekend detector in `truffles-api/app/services/info_signal_service.py`
- bounded collect snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal/message-endpoint tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into generic hours routing or other specialist families, stop and split
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
  - active block metadata must match the actual service-choice specialist weekend bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into generic weekend hours or other specialist seams in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- weekend specialist wording can overlap with hours/weekend service capability turns if the detector is widened carelessly
- downstream preservation still depends on the frozen service-choice specialist-followup owner predicate, so the collect contract must stay exact

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader specialist weekend/date-range families still remain partially frozen-runtime owned
  - broader booking outcome semantics still remain in frozen `decision.py`
  - continuity is still not a single writer
- **Why not in this block:**
  - each of those surfaces would widen this bounded bridge into a mixed semantic/execution or continuity refactor
- **Risk if deferred:**
  - neighboring specialist availability families remain in frozen runtime a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-next-specialist-availability-seam-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next specialist seam can reuse the same owner predicate without new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded specialist-availability seam after service-choice weekend followup, prioritizing weekday/day specialist followups only if they can remain read-only and contract-compatible with the existing specialist owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k specialist`
- **Blocked-by conditions:**
  - if the next seam needs frozen-router edits
  - if the next seam requires new continuity writers
  - if the next seam cannot preserve contract compatibility with the existing specialist followup owner predicate
- **Owner role for closure:** `Top Architect`
