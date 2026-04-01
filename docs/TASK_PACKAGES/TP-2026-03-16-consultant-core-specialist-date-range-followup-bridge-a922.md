# TP-2026-03-16-consultant-core-specialist-date-range-followup-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SPECIALIST-DATE-RANGE-FOLLOWUP-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACTIVE-NAME-RELATIVE-DAYPART-AVAILABILITY-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-daypart-availability-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SPECIALIST-AVAILABILITY-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий richer bounded booking seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit specialist-availability date-range followups вида `Какой мастер свободен на этой неделе?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, и `reply_slot=time`. Frozen router должен получать уже готовый collect-contract (`next_question=datetime`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=date_range`, `resolution_mode=referent_followup`, `pending_question_target=specialist`, `active_question_relation=specialist_availability_followup`) вместо первого policy-core LLM pass на этих turns, при этом grounded specialist transitions, active-name booking-time followups, weekend specialist turns, and frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-daypart-availability-followup-bridge-a922.md`
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
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '6720,6935p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '24532,24715p' truffles-api/tests/test_message_endpoint.py`
  - `python3 - <<'PY' ... resolve_master_intent("Какой мастер свободен на этой неделе?") ... PY`
  - `sed -n '520,700p' truffles-api/app/core/intent_routing.py`
  - `sed -n '700,860p' truffles-api/app/services/info_signal_service.py`
- `FACT findings`:
  - frozen `decision.py` already preserves `specialist_availability_followup` owner axes for `goal=booking`, `collect_slot=datetime|name`, `subject_kind=specialist`, `capability in {live_availability, bookability}`, and `temporal_scope in {specific_time, day, weekday, weekend, date_range}`.
  - frozen `decision.py` does **not** preserve active-name followup ownership for `temporal_scope=weekend|date_range`; that path is hard-blocked by the current predicate requiring `temporal_scope=specific_time`.
  - `test_llm_policy_core_specialist_availability_followup_keeps_time_collect` already proves the downstream contract for `Какой мастер свободен на этой неделе?` with `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=date_range`, `pending_question_target=specialist`, and `active_question_relation=specialist_availability_followup`.
  - `resolve_master_intent(...)` already classifies `Какой мастер свободен на этой неделе?` as an explicit master signal with `needs_service_clarify=True`, which means ingress can reuse that semantic cue while sourcing the missing service from the active conversation snapshot instead of inventing new semantic hardcode.
- `Detected drift (docs vs code)`: the next contract-compatible weekend/date-range-like seam is not active-name booking followup; it is specialist-availability date-range followup, and ingress does not yet own its first semantic decision despite already having the needed service referent snapshot and request-scoped override transport.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any function documentation`
- **Date/time (local):** `2026-03-16 17:43 +0500`
- **Why this query is precise:** this block needs one narrow disjunctive gate over date-range phrases and neighbor-seam exclusions without widening into a branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3.12/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `any(iterable)` is the standard short-circuit primitive for compact phrase-group gating over bounded date-range markers and exclusion checks.
- **Decision:** `reuse + integrate` — reuse the existing active service snapshot, request-scoped policy override transport, `resolve_master_intent(...)`, and frozen downstream specialist-followup contract; add only one narrow date-range detector and one bounded snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case specialist availability followups
  - widening this block into active-name weekend/date-range ownership even though the frozen owner predicate rejects those scopes
  - widening this block into grounded specialist transitions or weekend specialist turns
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit specialist-availability date-range followups under active booking/service context still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, and `reply_slot="time"`.
  2. Send `Какой мастер свободен на этой неделе?` through `reasoning_core`.
  3. Observe that ingress currently has no bounded specialist-date-range snapshot branch, so the first semantic decision still falls into frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded specialist-availability date-range override before delegate execution when the snapshot gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit specialist date-range followups route to `goal="booking"`, `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="date_range"`, `resolution_mode="referent_followup"`, `pending_question_target="specialist"`, and `active_question_relation="specialist_availability_followup"`
  - turns without active service referent or without `reply_slot=time` do not get this override
  - grounded specialist transitions stay outside this slice
  - active-name booking-time followups stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress currently owns booking-time followups and info/fact seams, but not specialist-followup collect contracts.
  2. Why not continue with active-name weekend/date-range? Because the frozen owner predicate for active-name followups contractually rejects non-`specific_time` scopes.
  3. Why is specialist date-range the next safe seam? Because frozen downstream already has a preserved contract for `specialist_availability_followup` with `temporal_scope=date_range`.
  4. Why can ingress own this safely now? Because `resolve_master_intent(...)` already exposes the explicit specialist cue and the active conversation snapshot already carries the missing service referent.
  5. Why does this reduce drift? Because another richer booking collect contract moves out of frozen runtime and into a typed ingress-owned override without changing execution ownership or adding writers.
- **Root cause statement:** specialist-availability date-range followups remained in frozen `decision.py` because ingress lacked the narrow detector needed to combine the existing master-intent signal, active service referent snapshot, and downstream-preserved specialist contract into one bounded collect override before delegate execution.
- **Fix mechanism:**
  - add a narrow detector for explicit specialist-availability date-range followups with neighboring-seam exclusions
  - emit a bounded policy snapshot branch keyed by active service referent plus `reply_slot=time`
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing active conversation snapshot projection for `service_referent` and `reply_slot`
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing `resolve_master_intent(...)` signal resolution
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, and reschedule/cancel neighbors
  - existing `route_llm_policy_core(...)` schema validation for `subject_kind`, `capability`, `temporal_scope`, and pending-question fields
  - existing frozen downstream specialist-followup contract evidenced in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the service-referent snapshot, override transport, master-intent signal resolution, and downstream specialist-followup contract; this block only needs one narrow date-range detector and one bounded snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one snapshot branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden specialist date-range followups.
- No override bleed across requests or unrelated message text.
- No override when active service referent is absent.
- No widening into grounded specialist transitions or active-name weekend/date-range ownership.

## Scope
- Add a narrow detector for explicit specialist-availability date-range followups.
- Add a bounded policy snapshot branch that reuses the active service referent snapshot.
- Add deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- grounded specialist availability transitions
- weekend specialist turns
- active-name booking-time followups
- live slot execution ownership
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-specialist-date-range-followup-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
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
2. Add a narrow specialist date-range detector and a bounded snapshot branch that reuses the active service referent snapshot.
3. Add deterministic tests for detection, snapshot gating, neighbor exclusions, delegate priming, override consumption, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded specialist-availability date-range override before delegate execution when the snapshot gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit specialist date-range followups route to `next_question="datetime"`, `open_questions=["datetime"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="date_range"`, and `resolution_mode="referent_followup"`
- turns without active service referent or without `reply_slot=time` do not get this override
- grounded specialist transitions and active-name booking-time followups stay outside this slice
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
- bounded specialist date-range detector in `truffles-api/app/services/info_signal_service.py`
- bounded followup snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into weekend specialist turns or grounded specialist transitions, stop and split
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
  - active block metadata must match the actual specialist date-range followup bridge being executed.

## Rollback
1. Revert `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into weekend specialist turns or grounded specialist transitions in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- specialist date-range wording can accidentally overlap with generic master-query or hours/fact paths if the detector is widened carelessly
- downstream preservation still depends on frozen specialist-followup owner predicates, so this block must stay contract-compatible with that exact shape

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - grounded specialist availability transitions remain frozen-runtime owned
  - weekend specialist turns remain frozen-runtime owned
  - broader booking outcome semantics still remain in frozen `decision.py`
- **Why not in this block:**
  - each of those surfaces would widen this bounded bridge into a mixed semantic/execution refactor
- **Risk if deferred:**
  - first semantic ownership for neighboring specialist availability families remains in frozen runtime a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-next-specialist-availability-seam-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next bounded specialist-availability seam needs the same snapshot anchors and no new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded specialist-availability seam after explicit date-range followups, prioritizing grounded specialist transition or weekend specialist turns only if they can remain read-only and contract-compatible with the existing specialist owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k specialist`
- **Blocked-by conditions:**
  - if the next seam needs frozen-router edits
  - if the next seam requires new continuity writers
  - if the next seam cannot preserve contract compatibility with the existing specialist followup owner predicate
- **Owner role for closure:** `Top Architect`
