# TP-2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922

## Название / цель
Материализовать полный machine-readable caller proof для live legacy mesh consultant-core и зафиксировать adapter-only law для frozen legacy surfaces до любых runtime constriction slices. Этот блок должен доказать, какие frozen webhook-era surfaces реально еще вызываются, какими путями они достигаются, какие поверхности уже unmounted/shadow-only, и какие legacy surfaces остаются только adapter/transport/trace seams, а не behavioral owners.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/DECISIONS/DEC-2026-03-30-consultant-core-architecture-recovery-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/failure_family_registry.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com anti-corruption layer adapter strangler fig legacy callers`
- Date/time (local): `2026-03-30 15:05:00 +0500`
- Sources opened:
  - `https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html`
- Source quality:
  - primary architecture source / Martin Fowler
- Ready solutions found:
  - transitional legacy seams must keep legacy interfaces explicit instead of ambient;
  - legacy mimic / anti-corruption layers should isolate translation and compatibility rather than silently preserving old business ownership;
  - caller seams must be discovered explicitly before a surface can be honestly called transitional or safe to delete.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the current authority/dead-surface registries and forensic packet evidence;
  - integrate exact caller proof into the existing machine-readable governance base;
  - build deterministic guards/tests only where the repo still lacks enforceable caller-proof checks.
- Rejected options:
  - assume frozen legacy files are adapter-only because they are old or small;
  - delete or demote surfaces before exact caller proof exists;
  - treat import absence alone as enough when route registration, dynamic exports, or helper indirection still keep the surface live.

## Invariant
- Do not change runtime behavior in this block.
- Do not mark a surface `adapter-only`, `shadow-only`, or `dead` without exact caller/import/route evidence.
- Do not close the block while any frozen legacy surface still lacks a current caller classification.
- Do not leave `_legacy.py`, `decision.py`, `reasoning_core.py`, or `app/webhook.py` with narrative-only status.
- Do not widen or relax the frozen-surface law to make caller proof easier.

## Scope
- Upgrade the authority/dead-surface governance base so legacy mesh status includes exact caller proof.
- Enumerate the live caller envelope for the frozen webhook-era surfaces:
  - mounted router/package paths
  - direct importers
  - dynamic export seams
  - sibling helper/fallback paths
  - test-only or shadow-only residue
- Classify each frozen surface as one of:
  - mounted-live adapter surface
  - unmounted compatibility wrapper
  - live legacy behavior owner
  - shadow-only residue
  - removed
- Wire the caller-proof law into source-of-truth, agent packet, guards, and deterministic tests.

## Out of scope
- Runtime behavior constriction.
- Planner/executor semantic cutover.
- Boundary/degrade constriction.
- Fact-plane implementation.
- Deletion of legacy files.
- Rewriting the mounted ingress.

## Touch-list
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/LEGACY_SUNSET.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/arch_guard.py`
- `scripts/recovery_execution_guard.py`
- `scripts/legacy_freeze_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `docs/REPORTS/2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Map exact live callers and route registrations for every frozen legacy surface.
2. Separate mounted ingress, adapter-only seams, live behavior-owning seams, shadow-only residue, and removed paths.
3. Upgrade machine-readable registries so caller proof is part of the active operating base.
4. Record the explicit phase advance in the lock/waiver layer while keeping `r35f` and runtime pause unchanged.
5. Wire the active block and required statuses into source-of-truth and generated packet.
6. Add deterministic validation and tests that fail when caller proof drifts from live code.

## Root cause (mandatory)
### Symptom
The repo now has an authority map and truth-carrier freeze law, but the live legacy mesh still lacks one enforceable caller-proof map. That allows old surfaces to keep ambient authority while the repo only describes them narratively as “legacy”, “frozen”, or “probably adapter-only”.

### Minimal reproduction
1. Read the current machine-readable registries.
2. Ask which frozen legacy files are still behaviorally live and by which exact callers.
3. Observe that the answer is still partial: mounted/unmounted status exists, but exact caller proof and adapter-only classification are not fully machine-readable.
4. Ask which surfaces are safe compatibility seams versus still-live owner-adjacent behavior paths.
5. Observe that the answer still depends on code search and older narrative audits rather than one enforced registry contract.

### Evidence
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/files/app_routers_webhook_init.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_services_reasoning_core.md`

### Five Whys
1. Why can legacy authority still drift? Because frozen legacy surfaces are not yet governed by one exact caller-proof contract.
2. Why is that dangerous? Because a file can look “legacy” while still being mounted, imported indirectly, or dynamically re-exported into live behavior.
3. Why are mounted/unmounted labels alone insufficient? Because they do not prove whether sibling import paths or package exports still keep the surface behaviorally live.
4. Why must this be solved before runtime constriction? Because later owner/boundary/fact work can still be bypassed through undisclosed legacy callers.
5. Why must the proof be machine-readable? Because later guards and future agents need deterministic drift detection, not manual recollection.

### Broken invariant
No legacy surface may be treated as adapter-only, shadow-only, or delete-ready without exact live caller proof in the active governance base.

### Shared mechanism
Legacy-mesh caller proof and adapter-only boundary governance.

### Why this surfaced family belongs to that mechanism
This is not a one-file cleanup. It is the missing control surface for the entire legacy mesh envelope.

### Open-world envelope expected to improve after the fix
- future runtime slices start from exact legacy caller proof;
- frozen surfaces cannot silently regain ambient ownership;
- delete/shadow-only claims become evidence-based rather than narrative.

### Root cause statement
The consultant-core repo already knows the legacy mesh is live, but it still lacks one enforceable machine-readable map of exact live callers and adapter-only boundaries for frozen webhook-era surfaces. Without that, future work can still under-scope the legacy envelope and overstate closure.

### Fix mechanism
- capture exact caller proof in the existing registries;
- align source-of-truth / packet / sunset law to that proof;
- add guards/tests that fail when new legacy callers appear or a registry classification goes stale.

## DoD
- every frozen legacy surface has machine-readable caller proof or explicit proof of absence.
- `authority_registry.json` and `dead_surface_registry.json` distinguish mounted adapter surfaces, live behavior-owning legacy surfaces, unmounted wrappers, shadow-only residue, and removed paths.
- the recovery execution lock and waiver now point to this block while keeping `r35f` and runtime pause unchanged.
- `docs/SOURCE_OF_TRUTH.yaml` and generated packet switch the active block to this TP.
- architecture guards/tests fail when caller proof or classification drifts from live code.
- no runtime behavior changed.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `git diff --check`

## Evidence
- this TP
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/dead_surface_registry.json`
- updated source-of-truth / agent packet / guards / tests
- `docs/REPORTS/2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md`

## Rollback
- revert the caller-proof registry fields and restore the previous active block in the source-of-truth stack

## No-go
- do not start semantic or fact cutover in this block
- do not delete legacy files in this block
- do not mark `reasoning_core.py` or `_legacy.py` adapter-only without exact caller proof
- do not trust stale docs over current live code

## Risks / blockers
- dynamic exports may hide effective legacy callers beyond direct imports
- some callers may be package-export or route-registration based rather than import-based
- frozen-surface tests can still miss sibling helper routes if the registry is under-specified

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- legacy modules still co-own visible runtime behavior
- post-owner reconstruction is still open
- boundary/degrade overreach is still open
- fact plane is still missing

### Why not in this block
This block proves the legacy caller envelope before any runtime constriction or deletion.

### Risk if deferred
Later constriction blocks can still miss live sibling caller paths and claim false closure.

### Linked follow-up Task Package(s)
- post-owner reconstruction constriction block
- boundary/degrade constriction block
- fact-plane materialization block

### Expiry / trigger to stop deferral
- stop deferral before any runtime cut that assumes the legacy mesh is already only adapter/shadow-only

## Next-block contract (mandatory)
### Next block objective
Constrict post-owner reconstruction so planner/executor/runtime shell stop rebuilding semantic-adjacent artifacts after the owner output.

### First deterministic check command
`python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('docs/system_forensics/dead_surface_registry.json').read_text())
assert data['entries'], 'dead surface registry must not be empty'
print('legacy_surface_registry_present')
PY`

### Blocked-by conditions
- caller proof still missing for any frozen legacy surface
- mounted/unmounted classifications still rely on stale docs instead of live code
- guards/tests do not fail on new legacy caller drift

### Owner role for closure
Brain / Top Architect
