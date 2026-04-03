# TP-2026-04-01-consultant-core-block-d-boundary-purification-a922

- Status: `active`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> implementation -> closure`
- Block ID: `block-d-boundary-purification`

## Название/цель
Закрыть только `Block D — Boundary Purification` в active worktree `a922`: boundary must stop minting visible business meaning on the live hot path, and stale boundary continuity-restore helpers must stay off the active runtime path.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `scripts/boundary_degrade_guard.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/consultant_core_v2.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_boundary_degrade_guard.py`

## Invariant
- Do not reopen `Block A`, `Block B`, `Block C`, or `Block C.5`.
- Do not add new semantic routing branches or text/regex business control in core runtime.
- Boundary may validate, block, degrade, or preserve the already-authored canonical artifact; it may not mint a second semantic outcome surface via override metadata.
- Do not widen into `Block E` pack/runtime separation or `Block F` legacy mesh fate work.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until code + focused tests + one focused replay proof exist for this block.

## Scope
- Live boundary meaning on the `consultant_core_v2 -> ConsultantRuntime -> ResponseRealizer` hot path.
- Boundary override sanitization and response realization on degrade/block paths.
- Explicit executor-requested handoff degradation so visible handoff meaning comes from the canonical decision artifact, not boundary override meta.
- Caller-proof that stale boundary continuity helpers in `state_service.py` stay off the active app runtime path.
- Focused deterministic tests plus exactly one focused replay on the live manager-active / degrade envelope, while caller-proof keeps stale re-entry helpers off the active path.

## Out of scope
- semantic-owner arbitration
- fact-plane scope/materialization
- continuity writer collapse already closed in `Block C`
- pack/runtime adapter separation
- legacy router fate/removal
- operational/outbox dedupe

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-d-boundary-purification-a922.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_boundary_degrade_guard.py`

## One web search (mandatory before implementation)
- Query: `site:w3.org SCXML history state previous active configuration restore instead of recomputing state`
- Date/time: `2026-04-01 22:16:00 +05 (Asia/Almaty)`
- Sources opened:
  - `https://www.w3.org/TR/scxml/`
- Source quality:
  - W3C primary specification
- Found ready-made solutions:
  - a resume/boundary transition should return to the stored state configuration instead of recomputing a new state from side data;
  - history-state transitions are explicit control transfers, not a license to invent a new state configuration or parallel meaning channel.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the typed controlled-degrade decision artifact and the existing block/degrade boundary seam;
  - integrate boundary so it only carries reason/public-message/provenance while visible outcome comes from the canonical decision artifact;
  - build only the missing executor-handoff degrade cut and guard proof that stale boundary continuity helpers remain non-runtime residue.
- Rejected options:
  - more web searches
  - keeping `reply_kind` / `activate_handoff` as live business-control keys in boundary override meta
  - reintroducing boundary-driven continuity writes
  - widening into pack/runtime or legacy cleanup

## Input baseline (FACT)
1. Live runtime path:
- `truffles-api/app/routers/webhook/decision.py:7216-7228` delegates inbound handling to `app.core.consultant_core_v2.handle_webhook_payload(...)`.
- `truffles-api/app/core/consultant_core_v2.py:22-48` delegates directly to `ConsultantRuntime.handle_webhook_payload(...)`.
2. Live boundary meaning minting:
- `truffles-api/app/core/consultant_runtime.py:556-565`, `576-585`, `594-602`, `613-622`, `626-634` build degrade overrides with `meta={"activate_handoff": True, "reply_kind": "handoff", ...}` even though `TurnPlanner.build_controlled_degrade(...)` already returns a canonical `HANDOFF` decision.
- `truffles-api/app/core/consultant_runtime.py:1048-1058` preserves a non-handoff decision and mints a new degrade override with `activate_handoff` / `reply_kind` when execution requests handoff.
- `truffles-api/app/core/consultant_runtime.py:1061-1075` activates handoff from `boundary_override.meta.activate_handoff`.
- `truffles-api/app/core/response_realizer.py:36-42` derives visible degrade `reply_kind` from `override.meta.reply_kind`.
3. Boundary continuity restore residue is not on the active path:
- `truffles-api/app/services/state_service.py` still defines boundary restore helpers, but `rg -n '_resolve_pending_resume_boundary_activation\\(|_resolve_resolved_handoff_resume_boundary_restore\\(|_resolve_pending_timeout_resume_boundary_payload\\(' truffles-api/app` shows definitions only and no app callsites.
- The only non-test repo references are import stubs in `truffles-api/app/routers/webhook/decision.py:678-687`; the active webhook path does not call them.

## Exact Path Map (mandatory)
1. Input
- A turn reaches the live hot path through `decision.py -> consultant_core_v2 -> ConsultantRuntime`.
- The boundary family is surfaced on degrade/control turns: planner guards, existing degrade decisions, or executor-requested handoff.
2. Owner output
- For planner guard failures, `TurnPlanner.build_controlled_degrade(...)` already emits the canonical control artifact: `outcome="HANDOFF"`, `action="handoff"`, `tool_action="handoff"`, `binding_outcome_type="degrade"`.
- For executor-requested handoff, execution can still surface `request_handoff=True` while the current decision remains `FACT` / `COLLECT`.
3. Validator / boundary
- `BoundaryValidator.validate(...)` normalizes the typed seam but still allows business-control meta keys to survive.
- `ConsultantRuntime._plan_turn(...)` duplicates handoff meaning into boundary override meta even when the decision is already a controlled degrade.
- `ConsultantRuntime._apply_execution_boundary_override(...)` currently preserves the original decision and authors new handoff meaning only in boundary override meta.
4. Continuity preservation / fallback
- The active hot path does not call the state-service boundary restore helpers; they are compatibility residue.
- The remaining live boundary overreach is visible-reply/handoff shaping via override meta, not active continuity restoration.
5. Final response
- `ResponseRealizer.realize(...)` maps `override.meta.reply_kind` onto the visible reply on degrade paths, so boundary meta becomes a second visible meaning channel.
- `_should_activate_handoff(...)` can also activate handoff from boundary override meta, not just from the canonical decision artifact.
6. Trace/meta evidence
- Code evidence: `truffles-api/app/core/consultant_runtime.py`, `truffles-api/app/core/response_realizer.py`, `truffles-api/app/core/boundary_validator.py`, `truffles-api/app/services/state_service.py`, `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/core/consultant_core_v2.py`.
- Deterministic proof target: `truffles-api/tests/test_consultant_core_runtime_contracts.py`, `truffles-api/tests/architecture/test_boundary_degrade_guard.py`.
7. Layer classification
- Primary: `boundary_fallback_error`
- Secondary: guarded `compatibility residue` for unreachable state-service boundary restore helpers
- Not this block: `owner_error`, `fact_composition_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- Boundary control on the active runtime path still co-owns visible handoff meaning through override metadata, and stale state-service boundary restore helpers remain present as compatibility residue even though the active runtime no longer uses them.

### Minimal reproduction
1. Inspect `TurnPlanner.build_controlled_degrade(...)` and note that the canonical decision already carries `HANDOFF`.
2. Inspect `ConsultantRuntime._plan_turn(...)` and observe planner degrade paths still add `reply_kind` / `activate_handoff` to boundary override meta.
3. Inspect `ConsultantRuntime._apply_execution_boundary_override(...)` and observe executor-requested handoff preserves a non-handoff decision and adds the visible handoff only through boundary override meta.
4. Inspect `ResponseRealizer.realize(...)` and observe degrade reply kind is still read from override meta.
5. Inspect app callsites and observe the boundary continuity helpers in `state_service.py` are not called by the active runtime path.

### Evidence
- `truffles-api/app/core/turn_planner.py:704-738`
- `truffles-api/app/core/consultant_runtime.py:526-636`
- `truffles-api/app/core/consultant_runtime.py:1041-1075`
- `truffles-api/app/core/response_realizer.py:25-52`
- `truffles-api/app/core/boundary_validator.py:57-90`
- `truffles-api/app/routers/webhook/decision.py:678-687`
- `truffles-api/app/routers/webhook/decision.py:7216-7228`
- `truffles-api/app/core/consultant_core_v2.py:22-48`
- `truffles-api/app/services/state_service.py:731-1034`

### Five Whys
1. Why is boundary still partial after the earlier degrade-constriction block?
   - Because the typed seam exists, but visible handoff meaning still rides both the canonical decision and boundary override meta.
2. Why is that a problem if both paths point to handoff today?
   - Because boundary meta becomes a second business-control channel; runtime can preserve a non-handoff decision and still hand off through override metadata.
3. Why does executor-requested handoff matter specifically?
   - Because it is the live path where boundary currently mints a new handoff outcome without converting the canonical decision artifact.
4. Why mention `state_service.py` if those helpers are not on the active path?
   - Because the residual functions are real compatibility code, but the exact call map shows they are not runtime authority anymore; the block must preserve that non-reachability instead of silently letting them re-enter the hot path.
5. Why is this one shared mechanism instead of separate symptoms?
   - Because both the visible reply and handoff activation still depend on boundary-side metadata rather than one canonical degraded decision artifact, while compatibility residue must stay outside the active path.

### Broken invariant
- Boundary may not mint visible business meaning via override metadata; visible degrade/handoff outcome must derive from the canonical decision artifact, and stale boundary restore helpers must not participate in the active runtime path.

### Shared mechanism
- Boundary meaning is still encoded twice: once in the canonical controlled-degrade decision and again in boundary override metadata, while old boundary continuity helpers remain as unguarded compatibility residue.

### Why the surfaced family belongs to that mechanism
- The live code shows one concrete duplication law across planner degrade, executor-requested handoff, response realization, and handoff activation. The stale state-service helpers matter only as a reachability guard around that same boundary envelope.

### Open-world envelope expected to improve
- planner degrade turns on the live runtime path
- executor-requested handoff turns
- visible reply-kind realization on degrade/block paths
- manager-active and executor-handoff degrade turns where boundary should preserve or degrade, not author new meaning

### Root cause statement
- The active boundary seam is still not pure because the live runtime carries handoff meaning both in the canonical degraded decision and in boundary override metadata, and the repo does not yet guard the stale boundary continuity helpers as non-runtime residue.

### Fix mechanism
- strip business-control keys from boundary override metadata;
- make degrade reply realization depend on the boundary decision class plus the canonical policy decision, not override-meta `reply_kind`;
- convert executor-requested handoff into an explicit controlled-degrade `HANDOFF` decision before realization/handoff activation;
- add deterministic guard proof that the old state-service boundary restore helpers remain off the active app runtime path.

## Plan
1. Keep `Block D` bounded to active boundary purification only.
2. Purify the live degrade path so handoff meaning comes from the canonical decision artifact, not override meta.
3. Update focused deterministic tests and boundary guard snapshots.
4. Run exactly one focused replay on the live manager-active / degrade envelope.
5. Only after proof, sync state/governance/docs for `Block D`.

## DoD
- Boundary override meta no longer carries live business-control keys for visible reply/handoff behavior on the active hot path.
- Executor-requested handoff is converted into an explicit controlled-degrade `HANDOFF` decision before realization.
- `ResponseRealizer` does not read override meta to choose degrade reply kind.
- Focused deterministic tests prove both the purified live boundary path and the no-runtime-caller guard for stale state-service boundary helpers.
- One focused replay proves the live manager-active / degrade envelope without reopening prior blocks.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "boundary_validator or response_realizer or execution_boundary_override or invalid_outcome or manager_active or handoff"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `git diff --check`
- focused replay command to be fixed after deterministic proof

## Evidence
- focused deterministic test output
- one focused replay directory under `/tmp/booking_quality/`
- replay artifacts:
  - `summary.json`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `manual_audit.md`
  - `manual_audit.json`
  - `family_registry.json`

## Rollback
- revert only the touched files in this TP and return to the proven post-`Block C.5` base

## No-go
- no scenario patches
- no new reply-kind business control via boundary override meta
- no reintroduction of active boundary continuity writes
- no widening into pack/runtime, legacy drain, or operational dedupe

## Risks / blockers
- existing tests and guards still snapshot `reply_kind` meta behavior and will need synchronized narrowing
- executor-requested handoff must remain observable in trace/meta even after boundary meta loses business-control power
- focused replay may surface a new unrelated first-fail family; if so, record evidence only and do not hotfix mid-block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- state-service boundary restore helpers still exist as compatibility residue
- pack/runtime separation, legacy mesh drain, and operational dedupe remain open
- whole-system acceptance remains open

### Why not in this block
- this block is only about active boundary meaning and reachability proof; deleting every compatibility residue belongs to later legacy/mesh work

### Risk if deferred
- if the caller-proof is not guarded, stale boundary continuity helpers can silently re-enter the app runtime path

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e-pack-runtime-separation-a922.md` (planned)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (planned)

### Expiry / trigger to stop deferral
- stop deferral immediately if any app runtime caller invokes the stale boundary restore helpers again or if boundary override meta regains visible business-control keys

## Next-block contract (mandatory)
### Next block objective
- `Block E — Real Pack/Runtime Separation`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
rg -n 'get_pack_adapter|pack_runtime|demo_salon_knowledge' truffles-api/app/services/pack_runtime_service.py truffles-api/app/services truffles-api/app/routers/webhook/info.py
```

### Blocked-by conditions
- boundary override meta still carries visible business-control semantics
- executor-requested handoff still preserves a non-handoff decision and relies on boundary meta to escalate
- focused live manager-active / degrade replay not yet proven

### Owner role for closure
- Brain / Top Architect
