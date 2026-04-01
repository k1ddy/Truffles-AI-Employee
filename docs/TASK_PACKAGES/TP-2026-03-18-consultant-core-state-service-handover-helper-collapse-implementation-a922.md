# TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-STATE-SERVICE-HANDOVER-HELPER-COLLAPSE-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-OWNER-CONVERGENCE-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-HANDOVER-FROZEN-COMPAT-SEAM-REDUCTION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Collapse the residual handover-owned helper cluster out of `truffles-api/app/services/state_service.py` so the new handover owner surface stops depending on state-service-local handover helpers. This block counts only if old handover helper authority becomes deleted from `state_service.py`, not if it is merely rewrapped there.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/escalation_service.py`
- `truffles-api/tests/test_state_service.py`

## FACT pre-check (before implementation)
- `Baseline commands`:
  - `rg -n "_apply_handover_contract_to_message|_build_handover_meta|_build_simulated_topic_id|_find_recent_resolved_handover|_get_latest_user_message|_get_recent_user_messages|_record_handover_contract_trace|_reopen_handover|_sync_pending_resume_on_handover_reuse" truffles-api/app/services/state_service.py truffles-api/app/services/handover_owner_service.py truffles-api/app/services/escalation_service.py`
  - `sed -n '300,710p' truffles-api/app/services/state_service.py`
  - `sed -n '1028,1115p' truffles-api/app/services/state_service.py`
  - `sed -n '1,220p' truffles-api/app/services/handover_owner_service.py`
  - `sed -n '180,340p' truffles-api/app/services/escalation_service.py`
- `FACT findings`:
  - `truffles-api/app/services/state_service.py` still owns `_build_handover_meta`, `_apply_handover_contract_to_message`, `_record_handover_contract_trace`, `_get_latest_user_message`, `_get_recent_user_messages`, `_build_simulated_topic_id`, `_sync_pending_resume_on_handover_reuse`, `_find_recent_resolved_handover`, and `_reopen_handover`.
  - `truffles-api/app/services/handover_owner_service.py` still imports those handover helpers from `state_service.py`, so the owner family still depends on a mixed module for handover-local behavior.
  - `truffles-api/app/services/escalation_service.py` already contains duplicate handover metadata/message/topic helper implementations for `_build_handover_meta`, `_get_latest_user_message`, `_get_recent_user_messages`, and `_build_simulated_topic_id`.
  - No non-owner runtime code besides tests currently calls the residual state-service handover helper cluster directly.

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Move Function" "Extract Class"`
- **Date/time (local):** `2026-03-18 09:02 +0500`
- **Why this query is precise:** the block is a narrow helper-cluster ownership collapse, so the needed primary-source guidance is specifically about moving cohesive functions to the module that actually owns the lifecycle.
- **Sources opened (from this query):**
  - `Catalog of Refactorings` — `https://refactoring.com/catalog/`
  - `Extract Class` — `https://refactoring.com/catalog/extractClass.html`
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary source from Martin Fowler's refactoring catalog.
- **Existing solutions found:** move behavior to the module whose data and lifecycle it belongs to, and separate a cohesive responsibility into its own class/module when the host file is mixed.
- **Decision:** `reuse/integrate` — reuse existing escalation-service helper implementations where they already match the handover family, move the remaining handover-only helpers into `handover_owner_service.py`, and delete the obsolete state-service copies.
- **Rejected options:**
  - leave the helpers in `state_service.py` and keep importing them from the owner surface
  - create another intermediate helper module just for this slice
  - broad rewrite of transport or frozen router surfaces in this block

## Root cause (mandatory)
- **Symptom:** after owner convergence, `state_service.py` still contains the handover helper bodies that the owner surface relies on.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/handover_owner_service.py` imports and confirm it still imports handover-owned helpers from `state_service.py`.
  2. inspect `truffles-api/app/services/state_service.py:300-710` and `:1051-1112` and confirm the helper bodies are still defined there.
  3. inspect `truffles-api/app/services/escalation_service.py:207-328` and confirm part of the same helper family already exists outside `state_service.py`, proving state ownership is accidental rather than essential.
- **Evidence:** current code still leaves handover helper authority in a mixed state module even though live runtime entrypoints already moved to the owner surface.
- **Five Whys:**
  1. Why is `state_service.py` still part of the family? Because the first owner-convergence block moved entrypoints first and reused existing helper definitions in place.
  2. Why were those helpers left behind? Because they were convenient to import and reduced immediate rewrite size.
  3. Why is that now a problem? Because the owner surface still depends on a mixed module for handover-local behavior, so the family is not actually closed.
  4. Why can this be fixed narrowly? Because the residual helper cluster has no remaining non-owner runtime callers besides tests, and duplicate equivalents already exist for part of the cluster in `escalation_service.py`.
  5. Why is helper deletion the right progress unit? Because it makes old handover authority in `state_service.py` unreachable instead of merely renaming imports.
- **Root cause statement:** the previous block converged callsites but intentionally deferred the handover-specific helper bodies, leaving `state_service.py` as a residual handover authority host.
- **Fix mechanism:** move the handover-only helper bodies into `handover_owner_service.py`, reuse the already-existing helper implementations from `escalation_service.py` where appropriate, retarget tests, and delete the obsolete helper definitions from `state_service.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse `escalation_service.py` helpers for `_build_handover_meta`, `_get_latest_user_message`, `_get_recent_user_messages`, and `_build_simulated_topic_id`
  - keep `state_service.py` as owner of generic continuity/state primitives such as `_capture_pending_resume_context`, `_restore_pending_resume_context`, `transition_state`, and `force_state`
  - reuse existing owner-surface tests in `truffles-api/tests/test_state_service.py` by repointing imports/patches instead of inventing new broad suites
- **External reuse:** Martin Fowler `Move Function` / `Extract Class`
- **Why not build from scratch:** the runtime behavior already exists and passed targeted validation; the missing step is deletion of the obsolete helper host, not new functionality.

## Invariant
- no `truffles-api/app/routers/webhook/booking.py` edits
- no new semantic hardcode
- no new owner surface besides `handover_owner_service.py`
- `state_service.py` keeps only generic continuity/state helpers after this block
- a compatibility alias left in `state_service.py` for the deleted handover helper bodies does not count as progress

## Scope
- move handover-only helper bodies out of `truffles-api/app/services/state_service.py`
- reduce `handover_owner_service.py` imports from `state_service.py` to generic state/continuity primitives only
- reuse matching helper implementations from `truffles-api/app/services/escalation_service.py` where that avoids unnecessary duplication
- update affected tests/import patch points

## Out of scope
- frozen `decision.py` seam reduction
- transport/orchestration redesign in `escalation_service.py`
- proof bundle / multi-pack validation
- broad continuity-owner rewrite beyond the handover helper residuals

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_state_service.py`

## Plan (1..N)
1. Author this TP and register it in repo docs.
2. Move the handover-only helper bodies from `state_service.py` into `handover_owner_service.py` or reuse matching implementations from `escalation_service.py`.
3. Remove the obsolete helper definitions from `state_service.py`.
4. Update test imports/patch points to the new owner/helper locations.
5. Run targeted compile/tests and the required guards.
6. Record which old `state_service.py` handover seam became deleted or unreachable.

## DoD
- `truffles-api/app/services/handover_owner_service.py` no longer imports the handover-only helper cluster from `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/state_service.py` no longer defines the deleted handover helper cluster
- targeted tests covering handover/pending-resume/manager transitions remain green
- required packet/guard/session checks remain green

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `python3 -m py_compile truffles-api/app/services/handover_owner_service.py truffles-api/app/services/state_service.py truffles-api/tests/test_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'handover or pending_resume or escalation or manager_'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_escalation_reuses_active_handover or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- diff showing the handover helper cluster deleted from `truffles-api/app/services/state_service.py`
- owner-service imports reduced to generic state/continuity primitives only
- targeted test and guard results

## Rollback
1. Restore the deleted helper definitions in `truffles-api/app/services/state_service.py`.
2. Revert `handover_owner_service.py` helper migration/import changes.
3. Revert test import changes.
4. Regenerate agent packet and rerun targeted checks.

## No-go
- no helper wrappers left behind in `state_service.py`
- no broad rewrite outside the residual helper cluster
- no new mixed landing zone for the moved helpers
- no correctness claim beyond the targeted family checks

## Risks / blockers
- owner-service growth could become another god-file if unrelated behavior is pulled in with the helpers
- helper reuse from `escalation_service.py` must not introduce import cycles
- tests still named `test_state_service.py` may obscure that handover ownership has moved; import updates must stay explicit

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded local-only helper collapse with no change to frozen router ownership in this block
- **Go/no-go signals:** deleted helper defs in `state_service.py`, owner surface imports reduced, targeted tests/guards green
- **Rollback:** revert helper moves/import changes and rerun checks
- **Post-release monitoring window:** local deterministic/runtime checks only; no product-level acceptance claim

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** compile + targeted handover/runtime/architecture checks only
- **Stop condition:** if helper deletion requires leaving a compatibility alias in `state_service.py`, stop with `GAP`
- **Escalation path:** `Top Architect`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `decision.py` compatibility wrappers remain; `handover_owner_service.py` still reuses transport/query helpers from `escalation_service.py`; proof bundle remains open
- **Why not in this block:** this block is strictly about deleting the residual `state_service.py` handover helper authority
- **Risk if deferred:** `state_service.py` remains a mixed authority host and the owner convergence claim stays incomplete
- **Linked follow-up Task Package(s):** `TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922` (to be authored after this block)
- **Expiry/trigger to stop deferral:** before any next handover-family change or any claim that continuity ownership has materially converged

## Next-block contract (mandatory)
- **Next block objective:** reduce the remaining frozen compatibility seam in `decision.py` after the `state_service.py` residual helper host is gone
- **First deterministic check command:** `rg -n "def get_active_handover|def _reuse_active_handover|def _create_pending_escalation_with_notification|resolve_active_handover_rejection|manager_resolve" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/handover_owner_service.py`
- **Blocked-by conditions:** if `state_service.py` still contains any deleted handover helper body after this block, or if owner-service import cycles appear
- **Owner role for closure:** `Top Architect`
