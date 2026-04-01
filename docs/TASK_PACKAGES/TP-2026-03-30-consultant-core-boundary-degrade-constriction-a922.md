# TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922

## Название / цель
Сузить и зафиксировать live boundary/degrade authority so the active hot path uses typed boundary overrides only for explicit degrade/block control, while reply-kind forcing and boundary-author growth are reduced and machine-readably guarded. Этот блок не материализует fact plane и не нормализует всю continuity; он должен закрыть boundary law на текущем root-first hot path и сделать future drift harder.

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
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com fail fast validation boundary derived data contract architecture`
- Date/time (local, recorded): `2026-03-30 16:18:03 +0500`
- Sources opened:
  - site-filtered `martinfowler.com` boundary / fail-fast architecture result set surfaced by the query
- Source quality:
  - high-signal architecture source class / Martin Fowler
- Ready solutions found:
  - fail-fast validation should surface invalid or out-of-contract states early instead of carrying them deeper into runtime;
  - boundary/output shaping must stay explicit and narrow so derived transport behavior does not become a second semantic source of truth;
  - the correct move is constriction and contract-freeze, not a broad runtime rewrite.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the typed boundary seam already present in `boundary_validator.py`, `consultant_runtime.py`, `response_realizer.py`, and `turn_executor.py`;
  - integrate one machine-readable boundary guard plus narrow runtime cuts so boundary can no longer force `fact/collect` reply kinds on the degrade path and the invalid-outcome degrade path is explicit.
- Rejected options:
  - broad runtime rewrite before constricting the current typed boundary seam;
  - leaving boundary-author growth unguarded because the current code “already mostly looks narrow”;
  - widening this block into fact-plane or continuity-normalization work.

## Invariant
- Do not introduce a second semantic owner.
- Deterministic boundary may validate, deny, degrade with explicit reason-code, request replan, or preserve canonical continuity artifacts only.
- Boundary may not invent new pending-question meaning, widen fact scope, or force new `fact/collect` reply semantics on degrade paths.
- Do not widen this block into fact-plane work, family-specific fixes, or legacy deletion.
- Do not add new semantic/fact/continuity logic to frozen legacy files.

## Scope
- Materialize the active boundary/degrade seam set in one machine-readable guard.
- Narrow the live runtime boundary so degrade reply-kind forcing cannot widen into `fact/collect`.
- Make `planner:invalid_outcome` degrade explicit and observable through a typed boundary override, not an implicit later fallback.
- Refresh authority/source-of-truth/canon/report/state so the active block matches live repo truth.
- Add deterministic proof for boundary reply-kind narrowing, ignored-path coverage, invalid-outcome degrade, and boundary-guard snapshot enforcement.

## Out of scope
- Fact-plane materialization.
- Continuity normalization beyond explicit boundary preserve/degrade proof.
- Legacy timeout/guard service deletion.
- `location / hours / parking` or any other family slice.
- Broad runtime cleanup outside the declared boundary mechanism envelope.

## Touch-list
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/recovery_execution_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/boundary_degrade_guard.py`
- `scripts/arch_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-boundary-degrade-constriction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Freeze the exact live boundary/degrade seam set and boundary-author callsites in `docs/BOUNDARY_DEGRADE_GUARD.yaml`.
2. Add a deterministic guard script that blocks new boundary-author growth and new override-meta reads outside the current snapshot.
3. Narrow the live runtime boundary so degrade reply-kind forcing cannot produce `fact/collect`, and make `planner:invalid_outcome` degrade explicit at the planner boundary seam.
4. Add deterministic tests for ignored-path turn outcomes, response-realizer fallback behavior, invalid-outcome degrade, and the boundary/degrade guard snapshot.
5. Sync authority registry / source-of-truth / packet / report / state to the new active block.

## Root cause (mandatory)
### Symptom
The repo already has a typed boundary seam, but the current root-first program still lacks one enforceable freeze over the live boundary author set and still allows the degrade path to force reply kinds broader than a strict boundary should own.

### Minimal reproduction
1. Inspect `truffles-api/app/core/boundary_validator.py` and observe that semantic/continuity/fact meta is stripped, but `reply_kind` is still treated as a generic override meta key.
2. Inspect `truffles-api/app/core/response_realizer.py` and observe that degrade overrides can force any `reply_kind` in `{fact, collect, handoff, system}`.
3. Inspect `truffles-api/app/core/consultant_runtime.py` and observe that `planner:invalid_outcome` currently degrades via a later generic planner-degrade fallback instead of one explicit typed boundary override path.
4. Inspect the repo and observe there is no dedicated machine-readable guard that freezes the live boundary/degrade seam set and boundary-author callsites.

### Evidence
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`

### Five Whys
1. Why is boundary/degrade still open after typed boundary work already landed?
   - Because the root-first program requires the live author set and its limits to be explicit, guarded, and proved, not merely present in code.
2. Why is the current seam still too broad?
   - Because degrade reply-kind forcing can still shape `fact/collect` visible behavior even though boundary law should only own narrow safe fallback behavior.
3. Why does the invalid-outcome path matter?
   - Because an implicit planner-degrade fallback leaves one live degrade route less explicit and less observable than the other guard-triggered degrade routes.
4. Why is a machine-readable guard needed?
   - Because new boundary-author callsites or new override-meta reads can silently reintroduce boundary authority drift.
5. Why must this happen before fact-plane work?
   - Because later fact-plane closure depends on boundary already being narrow enough to stop widening or reshaping visible fact behavior.

### Broken invariant
Deterministic boundary may not become a second semantic router or a general visible-reply authoring surface beyond explicit narrow degrade/block control.

### Shared mechanism
Boundary/degrade constriction.

### Why this surfaced family belongs to that mechanism
This is not one local reply bug. It is the missing contract-freeze and narrowing layer for the mechanism that validates or degrades owner output before visible runtime delivery.

### Open-world envelope expected to improve after the fix
- new boundary author paths cannot appear silently in the hot path;
- degrade overrides cannot force `fact/collect` reply kinds on the visible path;
- invalid planner outcomes take one explicit typed degrade path instead of an implicit later fallback;
- the active machine-readable authority map reflects the real live/shadow boundary topology.

### Root cause statement
The repository already contains a typed boundary seam, but boundary/degrade closure is still incomplete because the live boundary-author set is not frozen machine-readably, one visible reply-kind override remains broader than the boundary law permits, and one planner invalid-outcome path still relies on a less explicit degrade fallback route.

### Fix mechanism
- freeze boundary/degrade hotspots and callsites in `docs/BOUNDARY_DEGRADE_GUARD.yaml`;
- add `scripts/boundary_degrade_guard.py` to enforce that snapshot;
- narrow degrade reply-kind handling to `handoff/system` only;
- make `planner:invalid_outcome` emit one explicit typed boundary override path;
- sync governance registries and deterministic proof.

## DoD
- `docs/BOUNDARY_DEGRADE_GUARD.yaml` machine-readably freezes the current boundary/degrade seam set and boundary-author callsites.
- `scripts/boundary_degrade_guard.py` fails on boundary-author growth or new override-meta reply shaping outside the current snapshot.
- degrade reply-kind forcing can no longer coerce `fact` or `collect` on the boundary path.
- `planner:invalid_outcome` has explicit typed boundary override proof on the live runtime path.
- `authority_registry.json`, active canon/program, packet, report, and state are synced to this block.
- deterministic tests cover ignored-path boundary outcome, response-realizer boundary fallback, invalid-outcome degrade, and boundary guard snapshot.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "boundary or invalid_outcome or handoff or ignored_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `scripts/boundary_degrade_guard.py`
- updated `docs/system_forensics/authority_registry.json`
- updated source-of-truth / active canon / packet / report / state
- updated deterministic runtime and architecture tests

## Rollback
- revert touched files in the touch-list and restore the previous active block docs only

## No-go
- do not widen this block into fact-plane or family-specific fixes
- do not add new semantic/fact/continuity logic to frozen legacy surfaces
- do not claim full architecture closure if shadow/test boundary artifact builders or later fact-plane debt remain
- do not weaken existing semantic/continuity/freeze guards to make tests pass

## Risks / blockers
- older tests may implicitly assume degrade reply-kind overrides can force non-handoff visible reply kinds
- the repo still contains shadow/test compatibility boundary artifact builders, so registry wording must stay precise about live vs shadow authority
- guard configuration that is too broad will create noisy failures; too narrow will miss drift

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- shadow/test compatibility boundary artifact builders still exist in `turn_executor.py` and `reasoning_core.py`
- boundary/degrade continuity-heavy recovery still exists in later legacy timeout/guard services outside the active hot-path constriction slice
- first-class fact plane is still missing
- touched-slice continuity normalization is still open

### Why not in this block
This block constricts the typed hot-path boundary and freezes its author set. It does not yet drain all shadow compatibility builders or perform fact-plane / continuity follow-up blocks.

### Risk if deferred
New boundary authority can silently regrow through extra callsites or broader override meta and later block fact-plane closure again.

### Linked follow-up Task Package(s)
- fact-plane materialization block
- touched-slice continuity normalization block
- legacy drain and proof closure block

### Expiry / trigger to stop deferral
- stop deferral immediately if a new app runtime file starts authoring boundary overrides or if degrade paths start forcing `fact/collect` reply kinds again

## Next-block contract (mandatory)
### Next block objective
Materialize the first-class fact plane so owner-requested fact scope, binding-allowed emitted scope, and resolver/renderer emitted scope become explicit contracts.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/BOUNDARY_DEGRADE_GUARD.yaml').exists()
assert Path('scripts/boundary_degrade_guard.py').exists()
print('boundary_block_ready')
PY`

### Blocked-by conditions
- boundary/degrade seam set not frozen machine-readably
- live degrade path still able to force `fact/collect` reply kinds
- invalid-outcome degrade path not proven through explicit typed boundary override

### Owner role for closure
Brain / Top Architect
