# TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922

## Название / цель
Сузить whole-system operational outbox execution к одному shared runtime owner так, чтобы `outbox_service`, `admin`, `console`, и `worker` больше не держали собственные low-level orchestration paths и могли существовать только как thin entry surfaces над `outbox_runtime_service.py`.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-shadow-lane-elimination-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`

## One web search (mandatory before implementation)
- Query: `FastAPI include_router multiple FastAPI apps shared APIRouter official docs`
- Date/time (local): `2026-03-31 20:02 +0500`
- Sources opened:
  - `https://fastapi.tiangolo.com/advanced/sub-applications/`
- Source quality:
  - official FastAPI documentation / primary source
- Ready solutions found:
  - a separate FastAPI service boundary can remain valid if it is only a mounted sub-application/composition root and does not duplicate execution logic;
  - the safe dedupe move is to keep the composition root thin while converging execution into shared runtime helpers;
  - multiple operational surfaces are acceptable only when they delegate to one owner instead of keeping local orchestration.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse `outbox_service_app.py` as a thin dedicated service-app composition root;
  - integrate all live outbox execution surfaces through shared public helpers in `outbox_runtime_service.py`;
  - build only the missing scoped runtime helper, deterministic guard, and repo-contract coverage.
- Rejected options:
  - deleting `outbox_service_app.py` without deployment proof;
  - leaving `console.py` with local claim/process/archive orchestration;
  - treating `/admin/outbox/process` coverage debt as acceptable residual silence;
  - widening this block into replay, whole-system governance closure, or legacy router deletion.

## Invariant
- Do not reopen shadow-lane, legacy-mesh, pack/runtime, fact-plane, or continuity blocks.
- `outbox_runtime_service.py` must remain the only owner of low-level outbox row claiming/processing on app runtime paths.
- `outbox_service.py`, `admin.py`, `console.py`, `outbox_service_app.py`, and `workers/outbox.py` may survive only as thin operational entry surfaces.
- Do not sync `STATE.md`, active canon/program, packet, or reports before the full block is green.

## Scope
- add one public scoped-execution helper to `truffles-api/app/services/outbox_runtime_service.py`
- rewire `truffles-api/app/routers/console.py` execute mode to the shared scoped helper
- keep `truffles-api/app/routers/outbox_service.py` and `truffles-api/app/routers/admin.py` as explicit thin delegates to `run_default_outbox_process(...)`
- preserve `truffles-api/app/outbox_service_app.py` as a thin dedicated composition root only
- add visible repo-contract coverage for `/admin/outbox/process`
- freeze the resulting outbox operational topology with a dedicated guard
- close the block with one full sync after checks pass

## Out of scope
- deleting `outbox_service_app.py`
- deleting `/admin/outbox/process`
- deleting console `outbox_process` job type
- replay or human semantic audit
- whole-system governance closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
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
- `scripts/operational_entrypoint_dedupe_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/test_admin_legacy_auth.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
The outbox operational mechanism still had multiple live caller surfaces with uneven repo-contract coverage, and the mounted console execution path still reconstructed scoped claim/archive/process logic locally instead of delegating through one shared runtime owner.

### Minimal reproduction
1. Inspect `outbox_runtime_service.py`, `console.py`, `admin.py`, `outbox_service.py`, `workers/outbox.py`, and `outbox_service_app.py`.
2. Observe that worker/service/admin were already partly narrowed to shared helpers.
3. Observe that `console.py::_run_outbox_process_job(...)` still assembled its own scoped execution path from low-level helpers.
4. Observe that visible admin-route tests still omitted `/admin/outbox/process`.
5. Observe that the next whole-system block cannot truthfully close governance while operational caller topology remains only narratively described.

### Evidence
- `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/outbox_service_app.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_admin_legacy_auth.py`

### Five Whys
1. Why was operational dedupe still open after shadow-lane elimination?
  - Because several live outbox entry surfaces remained, and not all of them delegated through one public runtime owner.
2. Why is that a blocker?
  - Because duplicated operational orchestration lets different surfaces drift in behavior or coverage even when they target the same mechanism.
3. Why was console the main remaining hotspot?
  - Because it still parsed params and then directly called low-level archive/claim/process helpers instead of one shared scoped runtime entrypoint.
4. Why is missing admin route coverage important?
  - Because `/admin/outbox/process` is a live mounted route for the same mechanism, and leaving it unpinned preserves silent drift risk.
5. Why not delete the extra entry surfaces now?
  - Because repo truth still justifies a dedicated worker/service boundary and scoped operator surface; this block only narrows them to one shared owner instead of guessing at deployment removal.

### Broken invariant
One operational mechanism may expose multiple bounded surfaces only if they all delegate to one shared execution owner and do not keep local orchestration logic.

### Shared mechanism
Operational Entrypoint Dedupe.

### Why the surfaced family belongs to that mechanism
The outbox problem here is not semantic ownership; it is duplicated operational authority and uneven caller proof around one shared transport mechanism.

### Open-world envelope expected to improve after the fix
- all live outbox execute surfaces converge on `outbox_runtime_service.py`
- console execute no longer carries its own low-level orchestration
- admin outbox route gains visible repo-contract coverage
- the next admissible whole-system block can focus on governance closure instead of unresolved operational topology

### Root cause statement
The repo had already narrowed most outbox execution toward shared helpers, but the mechanism was still not fully deduped because console kept a local scoped execution path and admin outbox routing still lacked explicit repo-contract proof.

### Fix mechanism
- add one public scoped outbox runtime helper
- route console execute through it
- keep admin/service/worker surfaces thin and guarded
- add visible admin outbox coverage
- freeze the resulting topology with a dedicated deterministic guard

## Plan
1. Author this TP and keep active docs untouched until full block closeout.
2. Add `run_scoped_outbox_process(...)` to `truffles-api/app/services/outbox_runtime_service.py` so scoped operator execution has one public owner.
3. Rewire `truffles-api/app/routers/console.py::_run_outbox_process_job(...)` execute mode to delegate to the new shared helper.
4. Add explicit repo-contract coverage for `/admin/outbox/process` token gating and thin delegation.
5. Add a dedicated guard that freezes outbox service/admin/console/worker/service-app topology and the repo callsite set.
6. Sync registries, active docs, and packet once after the full block is green.

## DoD
- `truffles-api/app/services/outbox_runtime_service.py` owns public `run_default_outbox_process(...)`, `run_scoped_outbox_process(...)`, and `run_outbox_worker_cycle(...)`.
- `truffles-api/app/routers/outbox_service.py` and `truffles-api/app/routers/admin.py` stay thin delegates to `run_default_outbox_process(...)`.
- `truffles-api/app/routers/console.py::_run_outbox_process_job(...)` executes only through `run_scoped_outbox_process(...)`.
- `truffles-api/app/workers/outbox.py` executes only through `run_outbox_worker_cycle(...)`.
- `/admin/outbox/process` has visible repo-contract coverage.
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml` and `scripts/operational_entrypoint_dedupe_guard.py` freeze the resulting topology.
- machine-readable registries advance from `Shadow Lane Elimination` to `Operational Entrypoint Dedupe` only after checks pass.
- the next admissible block becomes `Whole-System Governance Closure`.

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
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py -k "run_scoped_outbox_process_uses_shared_runtime_helpers"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_admin_legacy_auth.py -k "admin_outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "run_outbox_process_job_execute"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "outbox_worker_and_console_use_shared_runtime_settings or console_router_has_no_local_outbox_claim_helper or outbox_request_wrappers_are_thin"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
- `scripts/operational_entrypoint_dedupe_guard.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/test_admin_legacy_auth.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- updated machine-readable registries and generated packet

## Rollback
- revert `run_scoped_outbox_process(...)` and repoint `console.py` back to the previous low-level helper path
- restore the prior active block if operational dedupe proof is rejected
- leave admin/service/worker surfaces on the previous shared helpers while reverting the new guard

## No-go
- do not widen this block into whole-system governance closure or replay
- do not delete `outbox_service_app.py` or disable console/admin entry surfaces without separate proof
- do not reintroduce local claim/process/archive orchestration into `console.py`
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- `outbox_service_app.py` remains a separate composition root because repo truth does not yet prove it removable
- console `outbox_process` execute remains live as a scoped operator surface, so this block must freeze it as thin delegate rather than pretend it is gone
- broader whole-system governance closure remains open after this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `outbox_service_app.py` remains a separate dedicated service-app composition root
- console `outbox_process` execute remains a live scoped operator surface
- broader fact families and pack-specific truth/catalog residue remain open
- whole-system governance closure remains open
- replay and human semantic audit remain forbidden

### Why not in this block
This block narrows operational execution topology only. Deletion of surviving service/operator surfaces and final global freeze alignment belongs to whole-system governance closure.

### Risk if deferred
Without this block, console/operator execution and admin/service coverage can keep drifting independently around the same outbox mechanism.

### Linked follow-up Task Package(s)
- future whole-system governance closure TP

### Expiry / trigger to stop deferral
- stop deferral immediately if any app surface outside `outbox_runtime_service.py` regains low-level outbox execution logic or if a new outbox execute surface appears without registry/guard updates.

## Next-block contract (mandatory)
### Next block objective
Close `Whole-System Governance Closure` so the now-recovered system-wide slices become one final machine-readable stop-the-line base before replay or human audit can resume.

### First deterministic check command
`python3 scripts/arch_guard.py`

### Blocked-by conditions
- operational entrypoint dedupe not yet synced into `SOURCE_OF_TRUTH` / recovery lock / packet
- operational entrypoint dedupe guard not green
- admin/console/worker/service outbox topology still drifts outside shared runtime owners

### Owner role for closure
- Architect / Brain
