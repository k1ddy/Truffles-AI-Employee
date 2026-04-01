# TP-2026-03-31-consultant-core-legacy-mesh-drain-a922

## Название / цель
Осушить router-side legacy mesh на live app/runtime boundary так, чтобы mounted webhook package и app runtime больше не зависели от `decision.py`, а `decision.py` и `_legacy.py` остались только shadow/test residual surfaces до следующего блока `Shadow Lane Elimination`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org module __getattr__ lazy import packages Python official docs`
- Date/time (local): `2026-03-31 17:22 +0500`
- Sources opened:
  - `https://docs.python.org/3/reference/datamodel.html#customizing-module-attribute-access`
- Source quality:
  - official Python language reference / primary source
- Ready solutions found:
  - package-root compatibility exports can stay lazy through module `__getattr__` while the actual implementation is moved behind a narrower helper module;
  - lazy package exports are acceptable as a compatibility boundary only when the mounted package root does not directly depend on the heavy legacy module being drained;
  - the drain should sever the import edge first, then keep the remaining legacy surface as shadow/test residue until the later deletion block.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing package-root lazy export pattern;
  - integrate it with a narrower dedicated helper module for expected-reply info interrupts;
  - build only the missing helper module, guard, and closure proof.
- Rejected options:
  - leaving `__init__.py` lazily coupled to `decision.py`;
  - deleting `decision.py` or `_legacy.py` in this block;
  - widening this block into `reasoning_core.py` or `app/webhook.py` shadow-wrapper cleanup.

## Invariant
- Do not reopen fact contract, continuity normalization, post-owner semantic constriction, boundary constriction, or pack/runtime separation.
- Do not add new semantic, continuity, fact-scope, or boundary logic to frozen router legacy files.
- `decision.py` and `_legacy.py` may survive only as shadow/test residual surfaces after this block.
- Do not sync `STATE.md`, active canon/program, packet, or reports before the full block is green.

## Scope
- sever the remaining package-root dependency from `app.routers.webhook.__init__` to `decision.py`
- move the package-root expected-reply info-interrupt helper to a narrower helper module
- prove that app runtime decision imports shrink to `_legacy.py` only and `_legacy.py` has no app runtime importers
- freeze that topology under a dedicated deterministic guard
- close the block with one full sync after checks pass

## Out of scope
- `reasoning_core.py` or `app/webhook.py` deletion
- broader legacy helper deletion (`booking.py`, `info.py`, `response.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`)
- replay or human semantic audit
- operational entrypoint dedupe
- broader fact-family migration

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/LEGACY_MESH_DRAIN_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/build_agent_packet.py`
- `scripts/recovery_execution_guard.py`
- `scripts/legacy_mesh_drain_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/expected_reply_interrupt_runtime.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
The active hot path is already fact-plane, continuity, boundary, and pack/runtime constrained, but the mounted webhook package still keeps one compatibility edge into `decision.py` through the package-root export of `_should_block_expected_reply_by_info`.

### Minimal reproduction
1. Inspect `truffles-api/app/routers/webhook/__init__.py`.
2. Observe that `_should_block_expected_reply_by_info` is still lazily imported from `app.routers.webhook.decision`.
3. Scan app-runtime imports of `app.routers.webhook.decision` and observe that `__init__.py` is still the remaining mounted package dependency, while `_legacy.py` is already test-only.
4. Observe that this keeps `decision.py` attached to the mounted package boundary even though the live runtime no longer routes through it.

### Evidence
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/_legacy.py`
- `docs/system_forensics/dead_surface_registry.json`

### Five Whys
1. Why is legacy mesh drain still open after pack/runtime separation?
  - Because the mounted webhook package still depends on `decision.py` for one compatibility export.
2. Why does that matter if ingress no longer routes through `decision.py`?
  - Because the package boundary still keeps the legacy router megafile in the live import graph.
3. Why is package-root dependency the right cut line here?
  - Because this block is about draining router legacy authority from mounted runtime composition, not about deleting every old file immediately.
4. Why not delete `decision.py` and `_legacy.py` now?
  - Because tests and shadow callers still depend on them, and that belongs to the next block `Shadow Lane Elimination`.
5. Why add a dedicated guard?
  - Because without a deterministic import-topology proof, `decision.py` can silently re-enter the mounted runtime package graph.

### Broken invariant
Mounted webhook package exports must not keep `decision.py` inside the live app/runtime dependency graph once the runtime hot path no longer needs it.

### Shared mechanism
Legacy Mesh Drain.

### Why the surfaced family belongs to that mechanism
This is not a scenario patch. It is one import-topology authority seam: package-root compatibility export still keeps the router legacy mesh attached to mounted runtime composition.

### Open-world envelope expected to improve after the fix
- mounted webhook package no longer imports `decision.py`
- app runtime decision imports shrink to shadow-only `_legacy.py`
- `_legacy.py` remains test-only with no app runtime importers
- router legacy mesh can now be represented honestly as shadow/unmounted residue while the next block focuses on wrapper lanes

### Root cause statement
Even after the active runtime moved away from the old router stack, package-root compatibility export still routed one helper through `decision.py`, so the router legacy mesh was not fully drained from the mounted runtime boundary.

### Fix mechanism
- extract the expected-reply info-interrupt helper cluster into a dedicated helper module
- re-point `app.routers.webhook.__init__` lazy export to that helper module
- keep `decision.py` as a shadow/test wrapper for compatibility callers only
- freeze the resulting import topology with a dedicated guard and registry proof

## Plan
1. Author this TP and keep active docs untouched until full block closeout.
2. Extract the package-root expected-reply info-interrupt helper cluster into `expected_reply_interrupt_runtime.py`.
3. Re-point `app.routers.webhook.__init__` lazy export to the new helper module.
4. Make `decision.py` delegate to the new helper cluster so test/package callers stay consistent.
5. Add deterministic proof that app runtime decision imports shrink to `_legacy.py` only and `_legacy.py` has no app runtime importers.
6. Close the block only after guard chain, targeted runtime tests, architecture tests, packet, and diff checks are green.

## DoD
- `truffles-api/app/routers/webhook/__init__.py` no longer imports `app.routers.webhook.decision`.
- package-root `_should_block_expected_reply_by_info` resolves through `expected_reply_interrupt_runtime.py`.
- app-runtime decision importers shrink to `truffles-api/app/routers/webhook/_legacy.py` only.
- app runtime has no `_legacy.py` importers.
- `docs/LEGACY_MESH_DRAIN_GUARD.yaml` and `scripts/legacy_mesh_drain_guard.py` freeze that topology.
- machine-readable registries represent `decision.py` and `_legacy.py` as shadow/test or unmounted residual surfaces rather than live package-boundary dependencies.
- active docs and packet move from `Pack / Runtime Separation Completion` to `Legacy Mesh Drain` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/pack_runtime_separation_guard.py`
- `python3 scripts/legacy_mesh_drain_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py::test_expected_reply_info_block_detects_booking_interrupt_info_turns truffles-api/tests/test_booking_info_interrupt_contract.py::test_decision_expected_reply_block_check_is_localized_to_single_contract_site`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "question_like_hour_reply_not_blocked_for_expected_time or question_like_daypart_reply_not_blocked_for_expected_time or declarative_daypart_reply_not_blocked_for_expected_time or question_like_daypart_exact_time_reply_not_blocked_for_expected_time or duration_question_without_booking_signal_stays_blocked_for_expected_time or booking_verification_handoff_intent_detection"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_eager_decision_import or app_runtime_has_no_eager_decision_importers"`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/LEGACY_MESH_DRAIN_GUARD.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/build_agent_packet.py`
- `scripts/legacy_mesh_drain_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/expected_reply_interrupt_runtime.py`
- updated architecture and targeted runtime tests
- updated `docs/system_forensics/dead_surface_registry.json`
- updated `docs/system_forensics/legacy_caller_surface.json`
- updated `docs/system_forensics/governance_delta.json`

## Rollback
- restore package-root helper export back to `decision.py`
- remove `expected_reply_interrupt_runtime.py` if the extracted seam proves invalid
- restore `Pack / Runtime Separation Completion` as the active block if this drain proof is rejected

## No-go
- do not delete `decision.py` or `_legacy.py` in this block
- do not widen this block into `reasoning_core.py` or `app/webhook.py` cleanup
- do not reopen pack/runtime, boundary, continuity, or fact-contract work
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- some tests still pin direct `decision.py` or `_legacy.py` exports, so the block must preserve compatibility while severing the mounted package dependency
- full legacy authority closure still depends on the next shadow-wrapper block
- broader fact families and other unmounted legacy helper clusters remain open after this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `reasoning_core.py` remains a shadow wrapper surface
- `app/webhook.py` remains a wrapper/delete-candidate surface
- broader fact families remain open
- operational entrypoint dedupe remains open
- replay and human semantic audit remain closed

### Why not in this block
This block drains only the router legacy mesh from the mounted package/runtime boundary. Wrapper-lane deletion belongs to `Shadow Lane Elimination`.

### Risk if deferred
Without this block, `decision.py` remains attached to mounted runtime composition through the package root, so the legacy mesh is still not honestly drained.

### Linked follow-up Task Package(s)
- future shadow lane elimination TP
- future operational entrypoint dedupe TP
- future whole-system governance closure TP

### Expiry / trigger to stop deferral
- stop deferral immediately if `app.routers.webhook.__init__` regains any import path to `decision.py` or if `_legacy.py` gains an app runtime importer.

## Next-block contract (mandatory)
### Next block objective
Eliminate the remaining shadow wrapper lanes so `reasoning_core.py` and `app/webhook.py` no longer preserve hidden runtime authority.

### First deterministic check command
`python3 scripts/legacy_mesh_drain_guard.py`

### Blocked-by conditions
- mounted webhook package still imports `decision.py`
- app runtime decision importers are wider than `_legacy.py` only
- `_legacy.py` still has app runtime importers
- registry proof is not aligned to the drained topology

### Owner role for closure
- Top Architect / Brain
