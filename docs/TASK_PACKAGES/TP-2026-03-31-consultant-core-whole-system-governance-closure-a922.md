# TP-2026-03-31-consultant-core-whole-system-governance-closure-a922

## Название / цель
Закрыть финальный whole-system architecture block так, чтобы recovered semantic / continuity / fact / boundary / legacy / operational slices стали одной machine-readable stop-the-line base, а единственным admissible следующим ходом остались fresh replay и полный human semantic audit.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com architectural fitness function software architecture`
- Date/time (local): `2026-03-31 20:28 +0500`
- Sources opened:
  - `https://www.martinfowler.com/ieeeSoftware/mda-thomas.pdf`
- Source quality:
  - high-signal architecture source hosted by Martin Fowler archive
- Ready solutions found:
  - architecture closure must become executable through repeatable fitness checks rather than narrative summaries only;
  - final closure should freeze one explicit next move instead of leaving multiple “almost done” lanes open.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing registry/guard pattern already established by earlier blocks;
  - integrate all recovered slices into one final machine-readable closure base;
  - build only the missing final closure guard and final block artifacts.
- Rejected options:
  - replay before final governance closure;
  - narrative-only closeout without deterministic final guard;
  - leaving more than one admissible next move after architecture closure.

## Invariant
- Do not reopen runtime semantic, continuity, fact, boundary, pack/runtime, legacy, shadow, or operational blocks.
- Do not claim product/practical green.
- Do not run replay or human audit in this block.
- Do not leave multiple admissible next moves after block closeout.

## Scope
- publish the final whole-system governance-closure TP/report/guard
- phase-advance the active block from `Operational Entrypoint Dedupe` to `Whole-System Governance Closure`
- promote registries to their final machine-readable architecture-closure status
- advance all authority mechanisms to the acceptance lane `replay_and_human_audit_acceptance`
- wire the final guard into the active guard chain and architecture tests
- sync active canon/program/state/packet once after the block is fully green

## Out of scope
- replay
- human semantic audit
- new runtime behavior changes
- new family-specific fixes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-governance-closure-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-whole-system-governance-closure-a922.md`
- `docs/WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
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
- `scripts/recovery_execution_guard.py`
- `scripts/whole_system_governance_closure_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_whole_system_governance_closure_guard.py`

## Root cause (mandatory)
### Symptom
All implementation slices are materially closed repo-side, but the repo still lacks one final machine-readable closure base that says “architecture work is done; only acceptance remains.”

### Minimal reproduction
1. Read the active operational-entrypoint-dedupe block.
2. Observe that the next block is still only narratively described.
3. Observe that registries still point to `whole_system_governance_closure` as the next phase instead of the acceptance lane.
4. Observe that without one final closure guard the repo can still drift into partial reopenings or premature replay claims.

### Evidence
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`

### Five Whys
1. Why is architecture closure still not final after the operational block?
  - Because the repo still points to another architecture phase rather than one locked acceptance lane.
2. Why is that a problem?
  - Because “almost final” governance lets future work re-open architecture slices without an explicit stop-the-line base.
3. Why can’t replay start from the current state directly?
  - Because the repo still needs one final machine-readable closure statement that all guards and registries agree on.
4. Why is narrative status not enough?
  - Because previous drift already proved that narrative-only active docs are not a sufficient enforcement layer.
5. Why is a final guard the right fix?
  - Because the final block is governance-only: it must prove one next move and one closure base, not invent new runtime behavior.

### Broken invariant
After the last architecture implementation slice closes, the repo must expose one final machine-readable closure base and one admissible next move only.

### Shared mechanism
Whole-System Governance Closure.

### Why the surfaced family belongs to that mechanism
The open issue is no longer a runtime behavior defect; it is missing final closure law across active docs, registries, and guards.

### Open-world envelope expected to improve after the fix
- the repo exposes one final architecture-closure base;
- every active registry points only to replay/human-audit acceptance next;
- future agents cannot honestly reopen architecture work without an explicit new waiver.

### Root cause statement
The repo completed the architecture implementation sequence but still lacked the final machine-readable closure block that freezes the recovered topology and advances the program to acceptance only.

### Fix mechanism
Create the final governance-closure guard and advance all active docs/registries to one final architecture-closure base whose only remaining next move is replay + full human semantic audit.

## Plan
1. Author the final TP/report/guard for whole-system governance closure.
2. Advance the execution lock, waiver, source-of-truth, and active canon/program to the final architecture block.
3. Promote all governance registries to final closure statuses and advance mechanism next-phase pointers to `replay_and_human_audit_acceptance`.
4. Wire the final closure guard into `arch_guard` and recovery-execution expectations.
5. Sync packet/state/structure once after all final checks pass.

## DoD
- Active block is `Consultant Core Whole-System Governance Closure`.
- `authority_registry.json`, `compatibility_carrier_inventory.json`, `dead_surface_registry.json`, and `legacy_caller_surface.json` all use final status `machine_readable_whole_system_governance_closure_base`.
- `governance_delta.json` uses final status `machine_readable_governance_closure_delta_base`.
- every authority mechanism points next to `replay_and_human_audit_acceptance`.
- the only active non-negotiable next move is fresh replay + full human semantic audit.
- the final closure guard is green and part of `arch_guard`.
- state/canon/report/packet are synced once at block closeout.

## Work mode
- implementation

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
- `python3 scripts/shadow_lane_elimination_guard.py`
- `python3 scripts/operational_entrypoint_dedupe_guard.py`
- `python3 scripts/whole_system_governance_closure_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_whole_system_governance_closure_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-whole-system-governance-closure-a922.md`
- `docs/WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml`
- `scripts/whole_system_governance_closure_guard.py`
- updated active docs/registries/packet
- `truffles-api/tests/architecture/test_whole_system_governance_closure_guard.py`

## Rollback
- restore the operational-entrypoint-dedupe operating base and remove the final closure guard if the final governance closure is rejected

## No-go
- do not run replay
- do not run human audit
- do not add new runtime behavior changes
- do not reopen already closed architecture blocks

## Risks / blockers
- practical/product closure still depends on replay + human audit after this block
- baseline relabel remains forbidden until a valid acceptance run exists

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- no additional repo-side architecture debt is accepted in this block
- only the acceptance lane remains after closeout

### Why not in this block
Replay and human semantic audit are acceptance work, not architecture implementation.

### Risk if deferred
Without this block the repo keeps an unnecessary “almost final” governance state and can drift before acceptance.

### Linked follow-up Task Package(s)
- future replay / human-audit acceptance TP

### Expiry / trigger to stop deferral
- stop deferral before any product-quality claim or baseline update.

## Next-block contract (mandatory)
### Next block objective
Run fresh replay on the locked corpus and complete the full human semantic audit before any practical/product closure claim.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/_generated/AGENT_PACKET.json').exists()
print('whole_system_governance_closure_complete_repo_side')
PY`

### Blocked-by conditions
- whole-system governance closure block not accepted
- active docs still allow any next move other than replay + human audit
- final closure guard not green

### Owner role for closure
Brain / Top Architect
