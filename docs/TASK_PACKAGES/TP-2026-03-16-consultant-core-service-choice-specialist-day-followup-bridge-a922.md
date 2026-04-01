# TP-2026-03-16-consultant-core-service-choice-specialist-day-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-DAY-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-WEEKDAY-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-weekday-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SERVICE-CHOICE-SPECIALIST-DAYPART-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded specialist-availability seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-choice specialist day followups вида `Какой мастер будет делать маникюр в субботу?` и `Какой мастер будет делать маникюр завтра?`, но только когда `reply_slot=service`, resume-contract остаётся booking-owned, service grounding уже явен в самом тексте, а temporal token нормализуется в чистый day token без daypart/exact-time. Frozen router должен получать уже готовый collect-contract (`next_question=datetime`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=specific_time`, `resolution_mode=clarify_missing_time`, `pending_question_target=specialist`) вместо первого policy-core LLM pass на этих turns, при этом weekday/weekend followups, daypart followups, grounded specialist transitions, specialist date-range followups, active-name booking followups и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-weekday-followup-bridge-a922.md`
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
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '6787,6855p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '24720,24890p' truffles-api/tests/test_message_endpoint.py`
  - `python3 - <<'PY' ... detect_policy_core_route_snapshot("Какой мастер будет делать маникюр в субботу?", ...) ... PY`
  - `python3 - <<'PY' ... detect_policy_core_route_snapshot("Какой мастер будет делать маникюр завтра вечером?", ...) ... PY`
- `FACT findings`:
  - frozen `decision.py` already preserves `service_choice_specialist_availability_followup` for `goal=info`, `collect_slot=datetime`, `expected_reply_type=service`, `resolution_mode=clarify_missing_time`, `pending_question_target=specialist`, `capability=live_availability`, and `temporal_scope in {specific_time, day, weekday, weekend}`.
  - `test_llm_policy_core_service_choice_master_availability_followup_keeps_time_collect` already proves the downstream specialist-followup contract for the explicit day family and shows the frozen owner converts it into `booking_specialist_availability_followup` with `expected_reply_type=time`.
  - ingress already owns the neighboring weekend and weekday seams, but explicit day-only variants like `в субботу` and `завтра` still fall through to the grounded `master_query` fact bridge.
  - `normalize_resolved_datetime_value(...)` plus `extract_relative_date_token(...)` already separate pure day tokens from daypart tokens, so ingress can reuse existing normalization instead of inventing a new parser.
- `Detected drift (docs vs code)`: the next contract-compatible service-choice specialist seam after weekday/weekend followups is the explicit day-only followup family, and ingress still lacks its own day-specific collect override branch.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org 3.12 str.strip documentation`
- **Date/time (local):** `2026-03-16 18:40 +0500`
- **Why this query is precise:** this block needs one narrow normalized-token gate over trimmed string values while staying bounded and not widening into a new parser.
- **Sources opened (from this query):**
  - `Built-in Types — str.strip` — `https://docs.python.org/3.12/library/stdtypes.html#str.strip`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `str.strip()` is the standard primitive for trimming bounded string values before equality checks and token gating; the repo already layers this through normalized text helpers.
- **Decision:** `reuse + integrate` — reuse `normalize_resolved_datetime_value(...)`, `extract_relative_date_token(...)`, `resolve_master_intent(...)`, request-scoped policy overrides, and the frozen downstream specialist-followup owner predicate; add only one narrow day detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case explicit day specialist followups
  - widening this block into weekday/weekend/daypart specialist routing
  - widening this block into grounded specialist transition or active-name followup ownership
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit service-grounded specialist day followups still start with the grounded `master_query` fact branch instead of the preserved service-choice specialist collect contract.
- **Minimal reproduction:**
  1. Load a conversation with `expected_reply_type=service` and booking-owned resume context.
  2. Send `Какой мастер будет делать маникюр в субботу?` through `reasoning_core`.
  3. Observe that ingress currently has no day-specific service-choice specialist branch, so the turn falls through to the grounded `master_query` fact bridge instead of the preserved collect contract.
- **Evidence to capture:**
  - ingress primes a bounded service-choice specialist day override before delegate execution when the gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit service-grounded day specialist turns route to `goal="info"`, `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, and `resolution_mode="clarify_missing_time"`
  - turns without `reply_slot=service` or with explicit daypart/exact-time stay outside this slice
  - weekday/weekend and other specialist seams stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress has no explicit day-only branch ahead of the grounded `master_query` fact bridge.
  2. Why can it be moved safely now? Because the frozen owner predicate already preserves this service-choice specialist collect contract for explicit day-driven followups.
  3. Why not handle it in the generic grounded `master_query` bridge? Because explicit day specialist followups need collect ownership with `next_question=datetime`, not fact ownership.
  4. Why is this a bounded slice? Because the service is grounded in the text, the expected reply slot is already `service`, and pure day tokens can be distinguished from daypart/exact-time using existing normalization helpers.
  5. Why does this reduce drift? Because another specialist-followup collect contract moves out of frozen runtime and into a typed ingress-owned override without widening execution ownership.
- **Root cause statement:** service-choice specialist explicit day followups remained in frozen runtime because ingress lacked the narrow day detector needed to distinguish them from the grounded `master_query` fact bridge and convert the already-grounded service signal into the preserved collect contract before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit service-grounded specialist day followups with neighbor-seam exclusions and daypart/exact-time rejection
  - emit a bounded policy snapshot branch keyed by `reply_slot=service` plus grounded service query plus explicit day scope
  - verify priming, exclusion, downstream contract compatibility, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing `resolve_master_intent(...)` service grounding
  - existing `normalize_resolved_datetime_value(...)` + `extract_relative_date_token(...)`
  - existing neighbor-seam exclusions for services-overview, location, hours, promotions, contact, duration, pricing, and reschedule/cancel
  - existing frozen downstream specialist-followup owner predicate and message-endpoint evidence
- **External reuse:**
  - official Python `str.strip` documentation
- **Why not reinvent the wheel:** the repo already has the grounded service signal, day-token normalization, override transport, and downstream owner contract; this block only needs one day detector and one bounded collect branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, focused deterministic tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden service-choice specialist day turns.
- No override bleed across requests or unrelated message text.
- No override when `reply_slot` is not `service`.
- No widening into weekday/weekend/daypart routing or other specialist seams.

## Scope
- Add a narrow detector for explicit service-grounded specialist day followups.
- Add a bounded policy snapshot branch for `reply_slot=service` day specialist collect.
- Add deterministic intent/reasoning tests and reuse the existing downstream message-endpoint contract check.
- Sync required canon/session artifacts.

## Out of scope
- weekday/weekend specialist followups
- daypart specialist followups
- grounded specialist transition
- specialist date-range followups
- active-name booking-time followups
- generic hours routing
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-day-followup-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_reasoning_core.py`
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
2. Add a narrow service-choice specialist day detector and a bounded collect snapshot branch.
3. Add deterministic tests for detection, snapshot gating, daypart exclusion, delegate priming, override consumption, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded service-choice specialist day override before delegate execution when the gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit service-grounded day specialist turns route to `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, and `resolution_mode="clarify_missing_time"`
- turns without `reply_slot=service` or with explicit daypart/exact-time do not get this override
- weekday/weekend and other specialist seams stay outside this slice
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'service_choice_master_availability_followup_keeps_time_collect or service_choice_specialist_weekday_followup_keeps_time_collect or service_choice_specialist_weekend_followup_keeps_time_collect'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded day detector in `truffles-api/app/services/info_signal_service.py`
- bounded collect snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests, reused downstream message-endpoint contract check, and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into daypart/generic hours routing or other specialist families, stop and split
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
  - active block metadata must match the actual service-choice specialist day bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into weekday/weekend/daypart or other specialist seams in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- explicit day specialist wording can overlap with the grounded `master_query` fact bridge if the detector is widened carelessly
- downstream preservation still depends on the frozen service-choice specialist-followup owner predicate, so the collect contract must stay exact

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - service-choice specialist daypart followups still remain frozen-runtime owned
  - broader booking outcome semantics still remain in frozen `decision.py`
  - continuity is still not a single writer
- **Why not in this block:**
  - daypart would widen the slice into a separate normalization family and should be cut independently
- **Risk if deferred:**
  - one neighboring specialist availability family remains in frozen runtime a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-service-choice-specialist-daypart-followup-bridge-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next daypart seam can reuse the same owner predicate without new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded service-choice specialist daypart seam after the day-only followup, only if it can remain read-only and contract-compatible with the existing specialist owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k 'service_choice and specialist and daypart'`
- **Blocked-by conditions:** frozen-router edits, generic hours routing drift, or continuity-writer expansion
- **Owner role for closure:** `Top Architect`
