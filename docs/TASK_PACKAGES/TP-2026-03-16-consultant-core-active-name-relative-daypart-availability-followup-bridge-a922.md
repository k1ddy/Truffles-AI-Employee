# TP-2026-03-16-consultant-core-active-name-relative-daypart-availability-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-RELATIVE-DAYPART-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-RELATIVE-DATE-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-date-availability-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-ACTIVE-AVAILABILITY-FOLLOWUP-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded active-availability seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit relative-date + daypart availability followups вида `У вас есть свободные слоты на завтра вечером?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, `reply_slot=name`, и active booking exact-time token. Frozen router должен получать уже готовый collect-contract (`next_question=name`, `capability=bookability`, `temporal_scope=specific_time`, `resolution_mode=referent_followup`) вместо первого policy-core LLM pass на этих turns, при этом explicit exact-time turns, pure relative-date turns, deictic-time/day turns, weekend/date-range turns, live slot execution ownership и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-date-availability-followup-bridge-a922.md`
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
  - `sed -n '700,820p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '560,660p' truffles-api/app/core/intent_routing.py`
  - `sed -n '909,1005p' truffles-api/tests/test_intent.py`
  - `sed -n '3005,3115p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1128,1165p' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - ingress already owns explicit exact-time, relative-date, deictic-time, and deictic-day active-name availability followups under request-scoped policy overrides.
  - relative-date + daypart followups like `У вас есть свободные слоты на завтра вечером?` are still outside the ingress seam because the current relative-date detector explicitly excludes daypart.
  - the current read-only snapshot already provides the exact-time anchor needed to preserve active-name followup ownership without adding a new continuity writer.
  - booking contract tests already treat `завтра вечером` as a grounded datetime, so this surface can stay contract-compatible with the existing frozen downstream owner.
- `Detected drift (docs vs code)`: the next explicit relative-date + daypart availability followup seam is still legacy-owned although ingress already has the exact-time snapshot anchor, request-scoped override transport, and normalized datetime helpers needed to express it as a bounded contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any function documentation`
- **Date/time (local):** `2026-03-16 17:27 +0500`
- **Why this query is precise:** this block needs one narrow disjunctive detector over neighboring-seam exclusions and daypart-specific wording without widening into a regex forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3.12/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `any(iterable)` is the standard short-circuit primitive for compact gating over multiple exclusion predicates and neighbor-seam guards.
- **Decision:** `reuse + integrate` — reuse the existing active-name availability seam, request-scoped policy override transport, normalized datetime helpers, and neighboring exclusion helpers; add only one narrow relative-date + daypart detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case relative-date + daypart followups
  - widening this block into weekend/date-range availability ownership
  - changing downstream active-name owner predicates in frozen runtime
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit relative-date + daypart availability followups under active-name resume still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, `reply_slot="name"`, and active booking exact-time token `15:00`.
  2. Send `У вас есть свободные слоты на завтра вечером?` through `reasoning_core`.
  3. Observe that ingress currently has no bounded snapshot for this family because the relative-date bridge explicitly excludes daypart, so the first semantic decision still falls into frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded relative-date + daypart availability override before delegate execution when the snapshot gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit relative-date + daypart followups route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `capability="bookability"`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
  - turns without the active booking exact-time token do not get this override
  - pure relative-date turns continue to route through the previous bounded seam
  - explicit exact-time and deictic-time/day turns continue to route through their existing seams
  - weekend/date-range turns stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress currently bridges pure relative-date followups but intentionally excludes daypart-bearing variants.
  2. Why does that matter? Because frozen `decision.py` still owns the first semantic decision for another common active-booking followup family.
  3. Why not migrate weekend/date-range handling now? Because that would widen the block beyond a safe bounded slice and start competing with richer scheduling semantics.
  4. Why can ingress own this safely now? Because the exact-time snapshot anchor and request-scoped policy override seam already exist, and `завтра вечером` is already a grounded datetime in booking contract tests.
  5. Why does this reduce drift? Because another explicit booking followup decision moves out of frozen runtime and into a typed ingress-owned contract without introducing a new writer or execution owner.
- **Root cause statement:** active-name relative-date + daypart availability followups remained in frozen `decision.py` because ingress lacked the narrow detector needed to combine the existing relative-date seam, daypart-normalized datetime helper, and exact-time snapshot anchor into one bounded collect contract before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit relative-date + daypart availability followups with neighboring-seam exclusions
  - emit a bounded policy snapshot branch keyed by the existing active booking exact-time token
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.booking_time_token`
  - existing active booking plus service referent projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing booking/time helpers: `extract_relative_date_token(...)`, `normalize_resolved_datetime_value(...)`, `extract_time_token(...)`, `has_explicit_date_signal(...)`
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, master
  - existing `route_llm_policy_core(...)` schema validation for `capability`, `temporal_scope`, and followup fields
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the exact-time snapshot anchor, override transport, normalized datetime helpers, and neighboring exclusion helpers; this block only needs one narrow relative-date + daypart detector and one bounded snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden relative-date + daypart availability followups.
- No override bleed across requests or unrelated message text.
- No override when the active booking exact-time token is absent.
- No widening into weekend/date-range or live slot execution ownership.

## Scope
- Add a narrow detector for explicit relative-date + daypart availability followups.
- Add a bounded policy snapshot branch that reuses the existing active booking exact-time token.
- Add deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- live slot execution ownership
- alternate-slot generation
- pure relative-date followups already covered by previous block
- deictic-time/day followups already covered by previous blocks
- weekend/date-range turns
- named-specialist availability followups
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-daypart-availability-followup-bridge-a922.md`
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
2. Add a narrow relative-date + daypart detector and a bounded snapshot branch that reuses the active booking exact-time token.
3. Add deterministic tests for detection, snapshot gating, explicit-time exclusion, delegate priming, override consumption, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded relative-date + daypart availability override before delegate execution when the snapshot gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit relative-date + daypart followups route to `next_question="name"`, `open_questions=["name"]`, `capability="bookability"`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`
- turns without the active booking exact-time token do not get this override
- pure relative-date, exact-time, and deictic-time/day turns continue to route through their existing seams
- weekend/date-range turns stay outside this slice
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
- bounded relative-date + daypart detector in `truffles-api/app/services/info_signal_service.py`
- bounded followup snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into weekend/date-range or live availability ownership, stop and split
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
  - active block metadata must match the actual relative-date + daypart availability followup bridge being executed.

## Rollback
1. Revert `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous availability bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into weekend/date-range followups in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- relative-date + daypart wording can accidentally overlap with weekend/date-range or broader scheduling semantics if the detector is widened carelessly
- downstream active-name followup preservation still depends on frozen-owner predicates that require `temporal_scope=specific_time`, so this block must stay contract-compatible

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - explicit weekend/date-range availability turns remain frozen-runtime owned
  - live slot execution and alternate-slot generation remain frozen-runtime owned
  - the broader booking outcome semantics still remain in frozen `decision.py`
- **Why not in this block:**
  - each of those surfaces would widen this bounded bridge into a mixed semantic/execution refactor
- **Risk if deferred:**
  - first semantic ownership for those neighboring availability families remains in frozen runtime a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-next-active-availability-followup-seam-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next bounded active-availability seam needs the same snapshot anchors and no new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded active-availability seam after explicit relative-date + daypart followups, prioritizing weekend/date-range only if it can remain read-only and contract-compatible with the existing active-name owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k active_name`
- **Blocked-by conditions:**
  - if the next seam needs frozen-router edits
  - if the next seam requires new continuity writers
  - if the next seam cannot preserve contract compatibility with the existing active-name followup owner predicate
- **Owner role for closure:** `Top Architect`
