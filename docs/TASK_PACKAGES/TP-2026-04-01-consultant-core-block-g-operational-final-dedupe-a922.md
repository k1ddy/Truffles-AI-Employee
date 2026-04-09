# TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922

- Status: `in_progress`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> RCA -> implementation -> closure`
- Block ID: `block-g-operational-final-dedupe`

## Название/цель
Закрыть только `Block G — Operational Final Dedupe` в active worktree `a922`: все live operational outbox entry surfaces должны идти через один канонический runtime boundary без локального co-ownership scoped process/preview semantics в `console.py` и без low-level execution residue вне `outbox_runtime_service.py`.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/app/outbox_service_app.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/test_admin_legacy_auth.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`

## Invariant
- Do not reopen `Block A`..`Block F`.
- Do not change booking/fact/boundary/continuity/user-facing consultant behavior.
- Do not introduce new outbox entry surfaces or new low-level claim/process/archive ownership outside `truffles-api/app/services/outbox_runtime_service.py`.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until this block is fully proven.

## Scope
- canonical operational boundary for scoped outbox preview + execute semantics
- console outbox job path
- operational guard tightening for low-level import/call residue
- focused deterministic proof on admin / outbox_service / console / worker / service-app surfaces

## Out of scope
- replay or human semantic audit
- provider transport behavior
- enqueue/build-inbound helpers
- changes to user-facing webhook runtime
- deletion of `outbox_service_app.py`, admin route, outbox service route, or console job type

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922.md`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
- `scripts/operational_entrypoint_dedupe_guard.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org Python dataclasses frozen keyword-only official documentation`
- Date/time: `2026-04-01 16:14:00 +0500 (Asia/Almaty)`
- Sources opened:
  - `https://docs.python.org/3/library/dataclasses.html`
- Source quality:
  - Python official documentation / primary source
- Found ready-made solutions:
  - `@dataclass` supports `frozen=True` and `kw_only=True`, which is appropriate for immutable request contracts crossing a service boundary.
  - keyword-only fields keep boundary construction explicit and reduce positional drift on multi-parameter contracts.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate`
  - reuse Python stdlib dataclass facilities for a narrow immutable scoped-process contract instead of introducing custom config carriers or extra parsing layers.
- Rejected options:
  - extra web searches
  - ad-hoc tuple/dict contracts for scoped outbox execution
  - framework-specific request objects for a repo-local service boundary

## Input baseline (FACT)
1. `Block F` is closed and the next admissible block is `Block G — Operational Final Dedupe`.
2. Current live caller topology is already narrowed on execute paths:
- `truffles-api/app/routers/admin.py:518` -> `run_default_outbox_process(...)`
- `truffles-api/app/routers/outbox_service.py:41` -> `run_default_outbox_process(...)`
- `truffles-api/app/workers/outbox.py:216` -> `run_outbox_worker_cycle(...)`
- `truffles-api/app/routers/console.py:10590` -> `run_scoped_outbox_process(...)`
- `truffles-api/app/services/outbox_runtime_service.py:176,223,278` -> `run_canonical_outbox_process(...)`
3. Current remaining co-ownership is console-side preview semantics:
- `truffles-api/app/routers/console.py:10386` defines `_query_scoped_outbox_message_rows(...)`
- `truffles-api/app/routers/console.py:10404` defines `_build_outbox_dry_run_summary(...)`
- `truffles-api/app/routers/console.py:10450` defines `_build_outbox_archive_preview(...)`
- `truffles-api/app/routers/console.py:867` still imports low-level `archive_pending_outbox`
4. Current runtime boundary is still too wide for Block G closure:
- `truffles-api/app/services/outbox_runtime_service.py:2103-2109` still exports low-level and high-level helpers together in `__all__`, so the narrow public seam is not explicit enough.

## Exact Path Map (mandatory)
1. Input
- `/admin/outbox/process`
- `/outbox/process`
- `console -> outbox_process job`
- `workers/outbox.py -> run_worker()` loop
2. Owner output
- `admin.py` and `outbox_service.py` delegate to `run_default_outbox_process(...)`
- `console.py` execute delegates to `run_scoped_outbox_process(...)`
- `workers/outbox.py` delegates to `run_outbox_worker_cycle(...)`
3. Validator / interrupt arbitration
- admin/outbox tokens gate route access
- console auth context gates branch/client scope
- worker startup safety gates worker mode
4. Continuity preservation
- not applicable; this is an operational runtime block, not dialog continuity
5. Fallback / degrade
- default/scoped helpers return zero-processed payloads when no rows are claimable
- worker cycle releases stale rows and may schedule inbound syncs before processing
6. Final response
- shared dict payload returned from runtime helpers to admin/outbox/console surfaces
- worker loop consumes `OutboxWorkerCycleResult`
7. Trace/meta evidence
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
- `scripts/operational_entrypoint_dedupe_guard.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
8. Layer classification
- Primary: `operational_execution_authority`
- Mechanism layer: `shared_outbox_runtime_boundary`
- Not this block: `owner_error`, `boundary_fallback_error`, `fact_composition_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- Live execute callsites already converge on runtime helpers, but `console.py` still rebuilds scoped outbox preview semantics locally and still carries low-level outbox import residue, so the operational mechanism is not yet fully collapsed behind one narrow runtime boundary.

### Minimal reproduction
1. Inspect `truffles-api/app/routers/console.py:10386-10590`.
2. Observe that dry-run uses `_query_scoped_outbox_message_rows(...)`, `_build_outbox_dry_run_summary(...)`, and `_build_outbox_archive_preview(...)` locally instead of delegating to `outbox_runtime_service.py`.
3. Observe `truffles-api/app/routers/console.py:867` still imports `archive_pending_outbox` from `app.services.outbox_service`.
4. Inspect `truffles-api/app/services/outbox_runtime_service.py:2103-2109` and observe that low-level helpers remain exported together with the high-level boundary.

### Evidence
- `truffles-api/app/routers/console.py:867`
- `truffles-api/app/routers/console.py:10386`
- `truffles-api/app/routers/console.py:10404`
- `truffles-api/app/routers/console.py:10450`
- `truffles-api/app/routers/console.py:10513`
- `truffles-api/app/services/outbox_runtime_service.py:246`
- `truffles-api/app/services/outbox_runtime_service.py:309`
- `truffles-api/app/services/outbox_runtime_service.py:2103`
- `truffles-api/app/routers/admin.py:518`
- `truffles-api/app/routers/outbox_service.py:41`
- `truffles-api/app/workers/outbox.py:216`

### Five Whys
1. Why is `Block G` still open if execute callsites were already narrowed?
  - Because only execute delegation was narrowed; scoped preview logic remained locally reconstructed in console.
2. Why does local preview logic matter for the same mechanism?
  - Because it re-encodes the same scope/archive semantics that define what the operator will process, so console still co-owns the operational contract.
3. Why is that a shared mechanism instead of a console-only cleanup?
  - Because the missing piece is a canonical scoped operational contract owned by `outbox_runtime_service.py`, not just one stray helper.
4. Why does low-level import residue matter if it is unused?
  - Because it weakens the boundary contract and allows silent drift back toward router-owned operational behavior.
5. Why not accept the current state as already closed?
  - Because the block objective is one canonical service boundary for all live operational surfaces, and current console dry-run semantics still sit outside that boundary.

### Broken invariant
- Every live outbox operational surface must rely on one canonical runtime boundary for scoped execution semantics; entry surfaces may validate/auth/scope, but they may not own local claim/process/archive preview mechanics.

### Shared mechanism
- canonical scoped outbox runtime boundary

### Why the surfaced family belongs to that mechanism
- admin/outbox/worker are already thin, while console dry-run still duplicates the same scoped operational semantics. That residue is part of the same operational mechanism and must be collapsed into the shared runtime owner.

### Open-world envelope expected to improve
- console dry-run and execute stay aligned on one scoped operational contract
- low-level outbox helpers stop leaking as quasi-public entry-surface affordances
- future operational surfaces inherit one boundary instead of rebuilding preview/execute semantics locally

### Root cause statement
- The repo previously deduped live execution paths but stopped short of creating one runtime-owned scoped operational contract, leaving console dry-run semantics and low-level import residue outside the canonical outbox boundary.

### Fix mechanism
- introduce one immutable scoped outbox request/preview contract in `outbox_runtime_service.py`, move console dry-run preview logic behind that service boundary, and tighten the operational guard so low-level imports/calls cannot silently reappear on entry surfaces.

## Plan
1. Add a narrow immutable scoped outbox contract to `outbox_runtime_service.py` and move scoped dry-run preview there.
2. Rewire `console.py::_run_outbox_process_job(...)` dry-run path to delegate through the shared runtime preview helper.
3. Remove low-level outbox import residue from `console.py`.
4. Tighten the operational guard to freeze import/call topology around the narrowed boundary.
5. Add focused deterministic tests for the new shared preview helper and console delegation.
6. Run deterministic proof only.
7. Sync governance/docs only after full Block G proof.

## DoD
- `console.py` no longer owns local scoped outbox preview helpers.
- `console.py` no longer imports low-level `archive_pending_outbox`.
- scoped dry-run and execute both delegate through `truffles-api/app/services/outbox_runtime_service.py`.
- operational guard freezes the narrowed import/call topology.
- focused deterministic tests are green and `git diff --check` is clean.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py -k "scoped_outbox_process or preview_scoped_outbox_process or run_default_outbox_process or run_outbox_worker_cycle"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "run_outbox_process_job"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_admin_legacy_auth.py -k "admin_outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- `python3 scripts/operational_entrypoint_dedupe_guard.py`
- `git diff --check`

## Evidence
- focused deterministic test output
- exact caller/import proof from the touched operational surfaces
- updated guard snapshot after Block G proof

## Rollback
- revert only the touched outbox runtime/console/guard/test changes and return to the post-Block-F operational topology

## No-go
- no replay
- no user-facing dialog changes
- no new outbox entry surfaces
- no low-level claim/process/archive logic back in routers or worker
- no governance/state sync before full proof

## Risks / blockers
- console dry-run output shape must remain compatible with existing console contract
- moving preview logic without a narrow contract can just relocate duplication instead of removing it

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- whole-system final acceptance remains open

### Why not in this block
- this block is only about the operational outbox execution seam

### Risk if deferred
- operator surfaces can drift between preview and execute semantics or reintroduce low-level outbox logic outside the runtime owner

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md` (to be authored after `Block G` closeout)

### Expiry / trigger to stop deferral
- stop deferral immediately if any non-runtime entry surface regains low-level claim/process/archive imports or if a new operational caller appears outside the guard allowlist

## Next-block contract (mandatory)
### Next block objective
- `Block H — Final Acceptance`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
python3 scripts/build_agent_packet.py --check
```

### Blocked-by conditions
- `Block G` deterministic proof not green
- any live outbox entry surface still owns low-level operational semantics outside `outbox_runtime_service.py`

### Owner role for closure
- Brain / Top Architect
