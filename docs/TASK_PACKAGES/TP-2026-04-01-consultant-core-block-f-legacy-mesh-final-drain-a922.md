# TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> RCA -> implementation -> closure`
- Block ID: `block-f-legacy-mesh-final-drain`

## Название/цель
Закрыть только `Block F — Legacy Mesh Final Drain` в active worktree `a922`: every remaining legacy webhook surface on the live import/caller topology must receive one exact machine-readable fate from the finite set `{adapter_only, observer_only, unreachable, removed}`, with no ambiguous intermediate legacy roles left on the mounted runtime boundary.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e6-post-grounding-service-reply-exactness-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`

## Invariant
- Do not reopen `Block A`..`Block E.6`.
- Do not change business semantics, fact composition, boundary behavior, continuity ownership, or pack/runtime reply logic.
- Do not add new legacy router authority or new eager imports from mounted runtime into legacy webhook surfaces.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until this block itself is fully proven.

## Scope
- exact import/caller proof for `truffles-api/app/routers/webhook/__init__.py`
- exact fate proof for `truffles-api/app/routers/webhook/decision.py`
- exact fate proof for `truffles-api/app/routers/webhook/info.py`
- exact fate proof for `truffles-api/app/routers/webhook/context_manager.py`
- exact fate proof for `truffles-api/app/routers/webhook/session_memory.py`
- one shared machine-readable fate taxonomy plus deterministic guard/test proof

## Out of scope
- replay or human semantic audit
- operational dedupe
- prompt/owner changes
- fact-plane/runtime reply changes
- deletion of `_legacy.py`, `decision.py`, `info.py`, `context_manager.py`, or `session_memory.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md`
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `scripts/legacy_drain_closure_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org importlib import_module lazy loading module package exports`
- Date/time: `2026-04-01 14:55:00 +0500 (Asia/Almaty)`
- Sources opened:
  - `https://docs.python.org/3/library/importlib.html`
- Source quality:
  - Python official documentation / primary source
- Found ready-made solutions:
  - `importlib.import_module()` is the supported programmatic import path for package-level compatibility exports;
  - `importlib.util.LazyLoader` exists but is discouraged outside startup-critical cases because it postpones errors out of context;
  - for compatibility surfaces, a narrow `import_module()`-based lazy export gate is preferable to eager package-root imports or custom loader tricks.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate`
  - reuse the existing package-root `__getattr__` + `import_module()` compatibility export seam;
  - integrate it with one exact machine-readable fate contract instead of adding new import machinery.
- Rejected options:
  - extra web searches
  - eager package-root imports of legacy modules
  - `LazyLoader`/custom importer machinery for a repo-local compatibility drain

## Input baseline (FACT)
1. `Block E.6` is closed and the next admissible block is `Block F — Legacy Mesh Final Drain`.
2. Live-code caller proof already shows:
- `truffles-api/app/main.py` mounts `truffles-api/app/routers/webhook/__init__.py`;
- `truffles-api/app/core/consultant_runtime.py` imports only `app.routers.webhook.http` and `app.routers.webhook.session_memory` from the legacy package surface;
- `truffles-api/app/routers/webhook/decision.py` has no live runtime callers and only app-side importer `truffles-api/app/routers/webhook/_legacy.py`;
- `truffles-api/app/routers/webhook/info.py` and `truffles-api/app/routers/webhook/context_manager.py` have no live runtime callers and are reached only by sibling legacy/shadow modules;
- `truffles-api/app/routers/webhook/session_memory.py` remains the only live adapter/helper import on the touched legacy seam.
3. Machine-readable registries are still partial on final-fate truth:
- `dead_surface_registry.json` uses intermediate classifications like `mounted_live_package_surface`, `live_legacy_control_turn_helper`, and `unmounted_legacy_helper_surface`;
- the required final finite-set fate for the remaining surfaces is not expressed explicitly as one exact machine-readable field.

## Exact Path Map (mandatory)
1. Input
- app startup imports `truffles-api/app/main.py` -> `truffles-api/app/routers/webhook/__init__.py`
- runtime control-turn seam imports `truffles-api/app/core/consultant_runtime.py` -> `truffles-api/app/routers/webhook/http.py` and `truffles-api/app/routers/webhook/session_memory.py`
2. Owner output
- not applicable: this block is structural import/caller topology, not owner semantic behavior
3. Validator / interrupt arbitration
- not applicable
4. Continuity preservation
- continuity behavior is out of scope; only the import/caller boundary around legacy surfaces is in scope
5. Fallback / degrade
- package-root compatibility access uses `__getattr__` + `import_module()` lazy exports
- legacy sibling imports keep `decision.py`, `info.py`, and `context_manager.py` reachable only through unreachable/shadow surfaces
6. Final response
- not a dialog family; the observable output is machine-readable fate classification plus import/caller proof
7. Trace/meta evidence
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `scripts/legacy_drain_closure_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/core/consultant_runtime.py`
8. Layer classification
- Primary: `legacy_behavior_authority`
- Mechanism layer: `legacy_mesh_topology_and_fate_contract`
- Not this block: `owner_error`, `boundary_fallback_error`, `fact_composition_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- The active worktree already narrowed the live runtime off the old router mesh, but the remaining legacy webhook surfaces still do not have one exact machine-readable final fate from the finite closure set.

### Minimal reproduction
1. Inspect `docs/system_forensics/dead_surface_registry.json` entries for `__init__.py`, `decision.py`, `info.py`, `context_manager.py`, and `session_memory.py`.
2. Observe that the registry still uses intermediate classifications instead of one explicit final fate field from `{adapter_only, observer_only, unreachable, removed}`.
3. Inspect live imports in `truffles-api/app/core/consultant_runtime.py` and `truffles-api/app/routers/webhook/__init__.py`.
4. Observe that the live boundary is already narrow, but the machine-readable closure proof still leaves partial/fuzzy fate labels.

### Evidence
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `scripts/legacy_drain_closure_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/core/consultant_runtime.py`
- live import scan:
  - `consultant_runtime.py -> app.routers.webhook.http`
  - `consultant_runtime.py -> app.routers.webhook.session_memory`
  - `decision.py` app-side importer -> `_legacy.py` only
  - `info.py` app-side importers -> `booking.py`, `booking_signal_runtime.py`, `decision.py`, `expected_reply_interrupt_runtime.py`
  - `context_manager.py` app-side importers -> sibling legacy/shadow modules only

### Five Whys
1. Why is legacy mesh final drain still open after earlier drain guards?
   - Because the repo still proves only partial drain properties, not one exact final fate for each remaining surface.
2. Why does that matter if live runtime callers are already narrow?
   - Because ambiguous intermediate classifications let legacy surfaces remain "partially alive" in governance truth even when the live boundary is already narrower.
3. Why is the exact final-fate contract the right mechanism?
   - Because this block is about explicit disposition of every remaining legacy surface, not about another behavior rewrite.
4. Why is this one shared mechanism instead of per-file cleanup?
   - Because all surfaced residue belongs to one topology/proof contract: each remaining surface must map to the same finite fate taxonomy under one import/caller law.
5. Why not widen into deletion now?
   - Because these surfaces still have compatibility/shadow callers; final deletion belongs only after the caller-proof contract is explicit and stable.

### Broken invariant
- Every remaining legacy webhook surface must have one exact machine-readable fate from `{adapter_only, observer_only, unreachable, removed}` based on live import/caller proof.

### Shared mechanism
- Legacy mesh topology and fate contract.

### Why the surfaced family belongs to that mechanism
- The remaining residue is not a scenario bug. It is one structural gap: the same legacy mesh still lacks one explicit finite-set fate law across all remaining surfaces.

### Open-world envelope expected to improve
- package-root compatibility exports remain honest as adapter-only
- live control-turn helper seams remain explicit as adapter-only instead of fuzzy legacy helpers
- unreachable/shadow router helpers stop looking partially live in governance truth

### Root cause statement
- The live code already narrowed legacy imports, but the repo still encodes the remaining webhook surfaces through intermediate classifications instead of one exact finite-set fate contract, so legacy mesh closure remains partial and can drift back into ambiguous authority claims.

### Fix mechanism
- add one exact machine-readable fate field and guard contract for the remaining legacy webhook surfaces, keep the package root and session-memory seam explicitly adapter-only, and mark the remaining router helpers explicitly unreachable/observer-only/removed according to live import/caller proof.

## Plan
1. Reconstruct the live import/caller proof for the five Block F surfaces in the active worktree.
2. Implement one exact finite-set fate contract in the machine-readable guard/registry layer.
3. Tighten touched code comments/seams only where needed to keep package-root and session-memory roles explicitly adapter-only.
4. Add focused architecture proof for the exact final fates.
5. Run deterministic guard/tests only.
6. Sync governance/docs only after full Block F proof.

## DoD
- each touched legacy surface has one exact machine-readable fate from `{adapter_only, observer_only, unreachable, removed}`
- `__init__.py` is proven adapter-only on the mounted runtime boundary
- `session_memory.py` is proven adapter-only on the live control-turn seam
- `decision.py`, `info.py`, and `context_manager.py` are proven unreachable on the live runtime boundary
- deterministic guard/tests are green

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `python3 scripts/legacy_drain_closure_guard.py`
- `git diff --check`

## Evidence
- focused deterministic test output
- exact import/caller proof from live code
- updated machine-readable guard/registry artifacts after closure

## Rollback
- revert only the touched legacy-mesh guard/registry/code-comment changes and return to the proven post-`Block E.6` base

## No-go
- no behavior fixes
- no replay
- no prompt/runtime semantic changes
- no deletion of legacy files in this block
- no governance/state sync before full proof

## Risks / blockers
- some surfaces may require a distinct `observer_only` fate instead of `unreachable` after exact import/caller proof
- test-only imports can be mistaken for live runtime callers unless the proof is kept app-only

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- operational dedupe and whole-system acceptance remain open

### Why not in this block
- this block is only about explicit final fates for the remaining legacy webhook mesh

### Risk if deferred
- later closure claims would keep inheriting ambiguous legacy-surface status

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`

### Expiry / trigger to stop deferral
- stop deferral immediately if a new live app/core importer appears for any surface that is supposed to be unreachable or observer-only

## Next-block contract (mandatory)
### Next block objective
- `Block G — Operational Final Dedupe`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
rg -n "outbox_runtime_service|admin.py|outbox_service.py|workers/outbox.py|claim|process" truffles-api/app/services/outbox_runtime_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/outbox_service.py truffles-api/app/workers/outbox.py truffles-api/app/routers/console.py
```

### Blocked-by conditions
- any Block F surface reappears on the live app/core runtime boundary after closeout
- operational claim/process callers are not yet collapsed behind one canonical execution seam

### Owner role for closure
- Brain / Top Architect

## Closure evidence
- Mechanism landed:
  - `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml` plus `scripts/legacy_drain_closure_guard.py` now encode one exact finite-set fate contract for the touched legacy surfaces.
  - `truffles-api/app/routers/webhook/__init__.py` is explicitly adapter-only: mounted router import plus lazy `import_module()` compatibility exports only.
  - `truffles-api/app/routers/webhook/session_memory.py` is explicitly adapter-only on the live control-turn seam.
  - `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/info.py`, and `truffles-api/app/routers/webhook/context_manager.py` are explicitly unreachable from the live runtime boundary.
- Deterministic proof:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_drain_closure_guard.py` -> `4 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py` -> `3 passed`
  - `python3 scripts/legacy_drain_closure_guard.py` -> `OK`
  - `git diff --check` -> clean
- Import/caller proof:
  - live runtime keeps `truffles-api/app/routers/webhook/__init__.py` as the adapter-only mounted package root
  - `truffles-api/app/core/consultant_runtime.py` remains the only live runtime importer of `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/routers/webhook/decision.py` app-side importer set remains `_legacy.py` only
  - `truffles-api/app/routers/webhook/info.py` and `truffles-api/app/routers/webhook/context_manager.py` remain reachable only through sibling legacy/shadow modules
