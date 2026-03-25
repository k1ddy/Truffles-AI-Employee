# TP-2026-03-18-consultant-core-semantic-arbitration-residual-package-a922

## Goal
Delete or bypass the remaining post-hoc semantic arbitration family from frozen `truffles-api/app/routers/webhook/decision.py` by converging the live semantic override / interrupt arbitration / hint backfill / direct-info referent ownership into the typed `turn_planner` path plus existing validation and execution owners, without creating a new semantic helper forest.

## Canon refs
- `STATE.md` NOW: consultant core `policy_core_guard_orchestration` runtime family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the targeted semantic-arbitration runtime lane plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Move Function" "Split Phase"`
- **Date/time (local):** `2026-03-18 13:37:23 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/splitPhase.html`
- **Source quality:**
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- **Found ready-made solutions:**
  - `Move Function`: move behavior to the module that already owns the dominant semantic invariant instead of leaving meaning split across caller and callee
  - `Split Phase`: separate semantic interpretation from later validation / realization so the runtime stops re-parsing and repairing the same intent mid-flight
- **Decision:** `reuse + integrate`
  - reuse the existing typed `PolicyDecision` / `TurnPlanner` seam in `truffles-api/app/core/turn_planner.py`
  - reuse the existing `reasoning_core` owner-cutover path that already consumes `route_llm_policy_core(...)` outputs for safe semantic families
  - reuse existing validation / execution owners (`policy_validation_boundary_service.py`, `truffles-api/app/core/boundary_validator.py`, `truffles-api/app/core/turn_executor.py`) only for validate/block/degrade/materialize responsibilities
  - do not build a new semantic arbitration helper service; the truthful destination is the existing `turn_planner` path plus bounded existing owners
- **Rejected options:**
  - new `truffles-api/app/services/semantic_arbitration_service.py`: rejected because the master residual ledger explicitly prefers `turn_planner` plus existing owners and a new service would become a second semantic hotspot
  - extend `truffles-api/app/services/policy_validation_boundary_service.py` or `truffles-api/app/core/boundary_validator.py` into semantic ownership: rejected because boundary owners must validate/block/degrade, not reinterpret meaning
  - extend `truffles-api/app/services/state_service.py`: rejected because continuity ownership is a different family
  - prompt-only repair in `prompts/llm_policy_core.md` without runtime cutover: rejected because the live post-hoc semantic rewrite would still remain in frozen `decision.py`
  - wrapper-only extraction inside frozen `decision.py`: rejected because it renames the seam without deleting authority

## Root cause (mandatory)
- **Symptom:**
  - frozen `decision.py` still repairs or reinterprets `llm_policy_core` meaning after the prompt returns
  - the surviving family includes post-hoc semantic override enforcement, booking-interrupt collect/info arbitration, inline LLM hint backfills for service/specialist/customer arguments, and direct-info service referent arbitration
- **Minimal reproduction:**
  - `rg -n "semantic_owner_post_hoc_override_blocked|policy_collect_info_interrupt_owner|llm_policy_semantic_delta|service_query_hint|specialist_hint|customer_name_hint|direct_info_service_query = policy_service_query" truffles-api/app/routers/webhook/decision.py`
- **Evidence:**
  - `truffles-api/app/routers/webhook/decision.py:12868-12925` still blocks style-reference and collect-slot recovery by rewriting plan intent/tool ownership after LLM output
  - `truffles-api/app/routers/webhook/decision.py:13314-13410` still promotes collect/list-slots/name-stage plans into booking or blocks them as post-hoc semantic overrides
  - `truffles-api/app/routers/webhook/decision.py:17036-17272` still owns inline service/specialist/customer hint resolution and writes semantic hint trace/meta in the frozen router
  - `truffles-api/app/routers/webhook/decision.py:19313-19359` still finalizes tool replies with reply-source / turn-outcome semantics derived in the frozen router
  - `truffles-api/app/routers/webhook/decision.py:19742-19821` still rewrites collect-to-info interrupt ownership and carries service query from booking state inline
  - `truffles-api/app/routers/webhook/decision.py:19972-20018` still owns the direct-info service referent arbitration for non-booking info replies
  - helper definitions that support these residuals also still live in frozen `decision.py`: `_derive_policy_info_refs(...)`, `_resolve_policy_collect_interrupt_arbitration(...)`, `_policy_has_style_reference_hint(...)`, and `_record_semantic_override_block(...)`
  - repo truth in `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md` already marks the preferred destination as `turn_planner` plus existing boundary/validation owners, not a new helper forest
- **Five Whys:**
  1. Why is semantic owner closure still partial? Because the prompt returns richer semantic fields, but frozen `decision.py` still re-decides meaning after parse.
  2. Why is that re-decision still in the frozen router? Because prior safe owner cutovers only removed bounded semantic families, while richer post-hoc arbitration remained on the legacy path.
  3. Why can't validation/boundary owners absorb it? Because they are contract enforcers and materializers; making them semantic owners would violate the boundary determinism gate.
  4. Why isn't a new semantic service the right answer? Because it would duplicate `turn_planner` semantics and create another mixed hotspot instead of converging the existing typed seam.
  5. Why is the `turn_planner` path the truthful destination? Because `truffles-api/app/core/turn_planner.py` already defines the typed `PolicyDecision` contract, and `truffles-api/app/services/reasoning_core.py` already owns the approved safe semantic cutover lanes that consume `route_llm_policy_core(...)` without post-hoc router rewrites.
- **Root cause statement:**
  - semantic ownership is still split between `prompts/llm_policy_core.md` and frozen `decision.py` because the legacy router continues to reinterpret the prompt result through inline semantic override blocks, interrupt arbitration, hint backfills, and direct-info referent rewriting instead of converging those meanings into the typed `turn_planner` path and existing validation owners.
- **Fix mechanism:**
  - route the remaining semantic arbitration family through the existing `turn_planner` / `reasoning_core` typed owner path
  - keep existing validation / boundary owners responsible only for validate/block/degrade/materialize responsibilities
  - delete or bypass the frozen inline semantic override / interrupt / hint / direct-info authority so the old post-hoc semantic seam becomes unreachable

## Invariant
- Frozen `decision.py` must lose live post-hoc semantic authority, not gain another helper/wrapper layer.
- Boundary owners must remain validators/blockers/degraders, not semantic deciders.
- `state_service.py` must not grow.
- No prompt-only patch may count as progress if the old runtime semantic rewrite remains live.
- If the truthful destination requires a new semantic god-file, stop and publish `GAP`.

## Scope
- Introduce one package-level implementation plan for the remaining `semantic_arbitration_residual` family
- Converge the residual semantic ownership to `truffles-api/app/core/turn_planner.py` plus the existing `truffles-api/app/services/reasoning_core.py` owner-cutover path and existing validation/execution owners
- Delete or bypass the frozen inline post-hoc semantic override / interrupt / hint / direct-info family
- Update only directly impacted tests/docs/contracts for this family

## Out of scope
- `continuity_broader_collapse`
- `public_entrypoint_materialization_contract`
- `debounce_buffer_owner_convergence`
- `proof_black_box_completion`
- `multi_pack_acceptance`
- full retirement of the legacy `/webhook` materialization path
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-semantic-arbitration-residual-package-a922.md`
- `STATE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- any directly impacted semantic-owner tests/docs only if required

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/app/services/intent_service.py` hint extractors (`extract_service_query_hint_llm`, `extract_specialist_hint_llm`, `extract_customer_name_hint_llm`) as existing secondary-LLM utilities only
  - existing `reasoning_core` owner-cutover patterns that already bypass frozen `decision.py` for safe semantic families
- **External reuse:**
  - Martin Fowler refactoring guidance for `Move Function` and `Split Phase`, limited to the single mandatory query above
- **Why this reuse mix is truthful:**
  - the typed `PolicyDecision` seam already exists and is the documented semantic target
  - the existing owner-cutover path already knows how to carry semantic intent into runtime outcomes without post-hoc router rewrites
  - validation/execution owners already exist for contract enforcement and materialization, so no new semantic helper forest is needed

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. Map the remaining semantic arbitration family into exact typed turn-planner responsibilities versus validation/materialization responsibilities.
3. Implement the runtime convergence by moving or bypassing the inline semantic override / interrupt / hint / direct-info authority from frozen `decision.py` into the `turn_planner` path plus existing validation/execution owners.
4. Reduce frozen `decision.py` to bounded payload collection and owner-surface invocation only for the affected semantic family.
5. Add or tighten targeted semantic-owner regression coverage.
6. Run the targeted semantic-owner runtime lane, runtime-contract checks if ownership/boundary surfaces change, and the required guards.
7. Record evidence in `STATE.md` only if the old live semantic arbitration seam is actually deleted or unreachable.

## DoD
- frozen `decision.py` no longer owns live post-hoc semantic override enforcement for the residual family
- frozen `decision.py` no longer owns live collect-to-info interrupt arbitration for the residual family
- frozen `decision.py` no longer owns live service/specialist/customer hint backfill orchestration for booking tool args in the residual family
- frozen `decision.py` no longer owns live direct-info service referent arbitration for the residual family
- the truthful destination is the existing typed `turn_planner` path plus existing validation/execution owners, not a new semantic helper service
- targeted semantic-owner runtime tests pass
- if `reasoning_core` / `boundary_validator` / `turn_executor` / validation ownership changes, `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` passes
- required architecture/session guards pass
- `STATE.md` records the deleted/unreachable old semantic seam with evidence

## Checks
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '12860,12930p;13310,13420p;17030,17280p;19310,19360p;19735,19825p;19970,20020p'`
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'policy_collect_interrupt_arbitration_rewrites_master_query_to_info or policy_collect_interrupt_arbitration_rewrites_active_time_duration_question_to_info or llm_policy_core_info_style_reference_without_pack_refs_routes_to_portfolio or llm_policy_core_info_style_intent_without_pack_refs_routes_to_portfolio or llm_policy_core_info_name_slot_without_pack_refs_normalizes_to_collect or booking_interrupt_hours_contract_blocks_price_takeover or llm_policy_core_collect_with_full_slots_normalizes_to_book_slot or llm_policy_core_list_slots_name_stage_normalizes_to_book_slot or llm_policy_core_book_slot_backfills_required_args_from_slots_and_specialist_hint or llm_policy_core_book_slot_uses_service_query_hint_when_missing or llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist or llm_policy_core_master_query_normalizes_to_master_info_under_booking or llm_policy_core_service_query_non_service_refs_routes_to_info or llm_policy_core_service_query_without_master_override_reason_keeps_plan_reply or llm_policy_core_active_time_slot_question_hours_phrase_keeps_booking_guidance or llm_policy_core_active_time_duration_info_interrupt_preserves_time_resume'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the deleted or bypassed frozen semantic arbitration seam and the surviving typed owner surfaces
- green targeted semantic-owner runtime lane plus runtime-contract checks (if touched) plus required guards
- `STATE.md` entry that names the deleted/unreachable old semantic seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Cheap deterministic gates first:** hotspot inspection command plus `python3 -m py_compile`
- **Targeted lane next:** the semantic-owner `test_message_endpoint.py` selection above
- **Contract lane after targeted pass:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` when ownership / boundary surfaces change
- **Stop condition:** if two consecutive iterations fail without new structural evidence that the frozen semantic family actually shrank, stop and return to RCA instead of grinding runs
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - the residual semantic hotspots no longer live as authority in frozen `decision.py`
  - the targeted semantic-owner runtime selection passes
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` passes if ownership/boundary surfaces changed
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's changes to the touched semantic-owner runtime files plus synced docs
  - rerun the targeted semantic-owner runtime selection and `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` if ownership/boundary surfaces changed
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'policy_collect_interrupt_arbitration_rewrites_master_query_to_info or llm_policy_core_info_style_reference_without_pack_refs_routes_to_portfolio or llm_policy_core_collect_with_full_slots_normalizes_to_book_slot or llm_policy_core_book_slot_uses_service_query_hint_when_missing or llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist or llm_policy_core_master_query_normalizes_to_master_info_under_booking'`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **Post-release monitoring window:** first post-merge consultant-core block only; do not advance to the next package if the deleted semantic arbitration family reappears in frozen `decision.py`

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted semantic-owner/runtime checks.

## No-go
- Do not build a new semantic helper/service forest.
- Do not move semantic decision-making into `policy_validation_boundary_service.py`, `boundary_validator.py`, or `turn_executor.py` as the primary owner.
- Do not grow `state_service.py`.
- Do not accept a prompt-only fix while the frozen runtime still rewrites meaning post-hoc.
- Do not leave wrapper-only semantic helpers in frozen `decision.py` and count that as progress.
- Do not claim consultant correctness, full semantic closure, or full runtime retirement from this block.

## Risks / blockers
- `truffles-api/app/services/reasoning_core.py` is already large; if the implementation cannot stay bounded around the existing typed turn-planner seam, stop and publish `GAP` instead of migrating the hotspot.
- Some residual hint logic currently shares helper utilities in frozen `decision.py`; if truthful deletion requires those helpers to remain as thin read-only adapters for one more block, the runtime package must prove that the old authority still died instead of merely moving line numbers.
- The direct-info referent slice and the collect-to-info interrupt slice share booking continuity context; if the implementation breaks that continuity or pushes it into boundary owners, the block is invalid.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `continuity_broader_collapse` still remains after this package
- `public_entrypoint_materialization_contract`, `debounce_buffer_owner_convergence`, `proof_black_box_completion`, and `multi_pack_acceptance` remain open after this package
- legacy `/webhook` materialization compatibility still remains even if semantic arbitration converges to the typed owner path

### Why not in this block
- this package deletes one exact semantic authority family only
- collapsing continuity or public-entrypoint materialization into the same block would blur owner boundaries again

### Risk if deferred
- frozen `decision.py` continues to reinterpret the prompt contract after parse
- new semantic drift can still accrete in the legacy router even though the typed `turn_planner` seam already exists elsewhere

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922` (to be authored only after this package either lands or truthfully blocks)
- `TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922` (only after the ordered backlog reaches it)

### Expiry/trigger to stop deferral
- stop deferral if any new post-hoc semantic rewrite lands in frozen `decision.py` or if the implementation requires a new semantic helper/service file to proceed

## Next-block contract (mandatory)
### Next block objective
- implement the `semantic_arbitration_residual` runtime family convergence defined by this TP and delete or bypass the old post-hoc semantic arbitration seam from frozen `decision.py`

### First deterministic check command
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '12860,12930p;13310,13420p;17030,17280p;19310,19360p;19735,19825p;19970,20020p'`

### Blocked-by conditions
- inability to keep the truthful destination inside the existing `turn_planner` path plus existing validation/execution owners
- any proposal that creates a new semantic helper/service forest
- any implementation that leaves the frozen post-hoc semantic branches live or moves them into another mixed hotspot
- any implementation that requires boundary owners to reinterpret semantic meaning instead of validating/materializing it

### Owner role for closure
- Brain / Top Architect
