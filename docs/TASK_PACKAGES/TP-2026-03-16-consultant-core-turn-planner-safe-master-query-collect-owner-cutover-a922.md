# TP-2026-03-16-consultant-core-turn-planner-safe-master-query-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-FACT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NEXT-COLLECT-OWNER-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Расширить `turn_planner` owner replacement с bounded FACT-среза на первый bounded COLLECT normal path: deterministic `master_query` `service_clarify`. Если ingress уже имеет existing `master_query` collect policy override, `reasoning_core` должен завершать turn напрямую, материализуя canonical collect state через `DialogStateService`, а не заходить в frozen `truffles-api/app/routers/webhook/decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/semantic_bridge_growth_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1825,1905p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '193,320p' truffles-api/app/core/dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'master_query_owner'`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'collect_owner_state'`
- `FACT findings`:
  - Existing `reasoning_core` already owns grounded `master_query` FACT turns, but explicitly falls back when the shared master helper returns collect-like `service_clarify`.
  - Existing bounded `master_query` collect policy override already gives a typed `PolicyDecision` candidate via `TurnPlanner.build_from_policy_override(...)`.
  - Existing `context_manager._set_expected_reply_context(...)` plus `DialogStateService` already own the expected-reply/question-contract/session-memory shaping needed for a bounded collect path.
- `Detected drift (docs vs code)`: the new core already has enough information to realize the deterministic `service_clarify` collect path, but frozen `decision.py` still owns it only because the current owner finalizer is FACT-only.

## One web search (mandatory before implementation)
- **Query (exact):** `Pydantic BaseModel model_validate model_dump official docs`
- **Date/time (local):** `2026-03-16 23:19 +0500`
- **Why this query is precise:** the block extends typed runtime ownership and must keep collect-state shaping contract-first instead of ad-hoc dict mutation.
- **Sources opened (from this query):**
  - `Models - Pydantic` — `https://docs.pydantic.dev/latest/concepts/models/`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** `model_validate` / typed `BaseModel` construction is the intended path for preserving schema-checked runtime state when building a new collect owner state.
- **Decision:** `reuse + integrate` — add a typed collect-state builder to `DialogStateService` and reuse existing expected-reply/context sync helpers instead of inventing a new runtime dict path.
- **Rejected options:**
  - new ingress phrase bridge family for collect owner routing
  - direct raw context mutation inside `reasoning_core`
  - touching frozen `decision.py` / `booking.py` / `pending.py`
  - widening immediately into `service_not_found` or broader collect families
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic `master_query` `service_clarify` replies still enter frozen `decision.py` even though the same policy override, reply builder, and continuity primitives already exist outside legacy.
- **Minimal reproduction:**
  1. Prime an explicit `master_query` collect override with `tool_action="collect"`, `next_question="service"`, and `open_questions=["service"]`.
  2. Let `build_master_reply_from_pack(...)` return a deterministic `service_clarify` collect reply.
  3. Observe that `reasoning_core` still delegates because current owner replacement only accepts FACT replies and has no typed collect-state finalizer.
- **Evidence to capture:**
  - `reasoning_core` bypasses frozen `decision.py` for safe `service_clarify` collect replies
  - conversation context and canonical dialog state receive the expected bounded collect contract
  - `service_not_found` collect replies still fall back to legacy delegate
- **Five Whys (or equivalent):**
  1. Why does the deterministic collect reply still hit legacy? Because the current master-query owner cutover only accepts `service_match` FACT results.
  2. Why is that no longer sufficient? Because the typed planner seam and continuity writer are now strong enough to materialize one bounded collect path safely.
  3. Why not cut over all collect paths now? Because broader collect families still require wider stateful booking/outcome ownership.
  4. Why is this block safe? Because it accepts only one deterministic collect envelope: `master_query_contract == masters_catalog.v1` with `master_reply_mode == service_clarify`.
  5. Why do this now? Because it deletes another real legacy semantic seam without adding any bridge growth.
- **Root cause statement:** the new runtime has a typed decision plus deterministic reply and continuity-shaping primitives for `master_query service_clarify`, but lacks a bounded collect finalizer that can persist the collect contract and reply without re-entering frozen legacy code.
- **Fix mechanism:**
  - add a typed collect-state builder in `DialogStateService`
  - extend the shared owner finalizer so bounded collect owner paths can sync expected-reply/canonical state before send
  - add a new master-query collect owner cutover that accepts only deterministic `service_clarify`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `TurnPlanner.build_from_policy_override(...)`
  - `DialogStateService`
  - `context_manager._set_expected_reply_context(...)`
  - existing owner finalizer in `truffles-api/app/services/reasoning_core.py`
  - `resolve_master_intent(...)`
  - `build_master_reply_from_pack(...)`
- **External reuse:**
  - official Pydantic typed model construction docs
- **Why not reinvent the wheel:** the block only adds the missing typed collect-state seam and reuses existing context/state helpers.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement cutover plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Only deterministic `master_query` `service_clarify` becomes direct-owner.
- `service_not_found` and broader collect/handoff/stateful booking paths still fall back to legacy.

## Scope
- Add a typed collect-owner dialog-state builder.
- Extend the shared owner finalizer so bounded collect owner paths can persist canonical collect state.
- Add one bounded `master_query service_clarify` owner cutover in `reasoning_core`.
- Add focused regression coverage and sync canon/session artifacts.

## Out of scope
- `master_query` `service_not_found`
- pricing/duration collect owner cutover
- booking collect/handoff owner cutover
- frozen legacy semantic files
- new semantic bridge families

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-collect-owner-cutover-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
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
2. Add a typed collect-owner dialog-state builder in `DialogStateService`.
3. Extend the shared owner finalizer to sync bounded collect continuity state.
4. Add a bounded `master_query service_clarify` owner cutover in `reasoning_core`.
5. Add regression coverage for safe collect bypass and unsupported collect fallback.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic `master_query service_clarify` replies bypass frozen `decision.py`
- collect owner path writes expected reply + canonical dialog state contract through existing continuity owner
- `service_not_found` still falls back to legacy delegate
- no new bridge family is introduced

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'collect_owner_state'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'master_query_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core tests proving safe collect bypass and unsupported collect fallback
- dialog-state test proving typed collect owner state contract
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** dialog-state + reasoning-core + contracts + architecture only for this bounded block
- **Stop condition:** if safe collect realization needs broader booking-state mutation, handoff creation, or new bridge growth, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement extension only; no new entrypoints or semantic bridges
- **Go/no-go signals:** dialog-state + reasoning-core + contracts + architecture suites green; semantic bridge and continuity guards green
- **Rollback:** revert the collect-state builder, owner-finalizer extension, collect cutover, tests, and doc sync
- **Post-release monitoring window:** next block should either extend another safe owner seam or move to a larger planner/outcome cutover without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe master-query collect owner cutover and generated packet output.

## Rollback
1. Revert the `DialogStateService` collect-state builder, `reasoning_core` collect owner path, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into `service_not_found`, booking, or handoff semantics
- no counting this block as done unless deterministic `service_clarify` becomes direct-owner and unsupported collect replies still fall back

## Risks / blockers
- if collect owner realization still depends on hidden state-restore semantics, direct-owner cutover would be unsafe
- if the collect acceptance gate is too broad, other collect-like master replies could bypass legacy incorrectly

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader collect/handoff stateful outcomes still remain on the legacy delegate
  - proof path is still not fully black-box
  - boundary owner is still legacy-mixed
- **Why not in this block:**
  - this block only extends one deterministic collect envelope and one typed continuity seam
- **Risk if deferred:**
  - frozen `decision.py` would keep owning a collect path that the new core can already realize safely and contract-first
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement TP after this cutover, or larger planner/outcome TP if no next safe seam remains
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate needs handoff creation, booking mutation, or new bridge growth

## Next-block contract (mandatory)
- **Next block objective:** next richer owner-replacement seam that deletes another legacy semantic path without new bridge growth; if no bounded semantic seam remains, switch to boundary-owner cutover instead of returning to micro-bridges
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k 'owner_cutover and not delegate'`
- **Blocked-by conditions:** any candidate that needs booking mutation, handoff queue creation, or frozen-router edits
- **Owner role for closure:** `Top Architect`
