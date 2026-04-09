# TP-2026-04-01-consultant-core-block-e-real-pack-runtime-separation-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> implementation -> closure`
- Block ID: `block-e-real-pack-runtime-separation`

## Название/цель
Закрыть только `Block E — Real Pack/Runtime Separation` в active worktree `a922`: live fact/runtime callers on the hot path must consume one narrow pack-runtime boundary, and the selected pack adapter must become the sole behavior authority beneath that boundary.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
- `scripts/pack_runtime_separation_guard.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`

## Invariant
- Do not reopen `Block A`, `Block B`, `Block C`, `Block C.5`, or `Block D`.
- Do not add domain-label or phrase-hardcoded business control into core/runtime.
- Active hot-path callers may use only one narrow pack-runtime boundary object; they may not import a spread of pack helper functions from the facade.
- The selected pack adapter may remain pack-specific, but it must be reached only through the pack-runtime boundary, not through hidden demo/neutral co-ownership on the live hot path.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until code + focused tests + minimal proof for this block exist.

## Scope
- materialize one narrow runtime-facing pack boundary in `pack_runtime_service.py`
- route active hot-path helper behavior through slug-selected adapter dispatch instead of direct neutral-adapter imports
- move live hot-path callers (`turn_executor.py`, `tool_registry_service.py`) onto that boundary
- freeze the narrowed caller/import seam in the pack/runtime separation guard
- prove the touched hot path with focused deterministic checks, and run one minimal replay only if the touched behavior path changes product-visible output

## Out of scope
- legacy mesh drain or adapter deletion
- info router legacy cleanup beyond the touched hot path
- new fact-family policy work
- continuity / boundary closure already proven in Blocks C and D
- operational dedupe
- broad whole-system replay or governance sync before block proof

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e-real-pack-runtime-separation-a922.md`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
- `scripts/pack_runtime_separation_guard.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org Python typing Protocol structural subtyping narrow service interface`
- Date/time: `2026-04-01 11:40:27 +0500 (Asia/Almaty)`
- Sources opened:
  - `https://docs.python.org/3.12/library/typing.html`
- Source quality:
  - Python official documentation / primary source
- Found ready-made solutions:
  - structural subtyping via `typing.Protocol` is appropriate when callers should depend on a narrow behavioral interface instead of a concrete implementation module;
  - a boundary object can keep callers typed against the small surface they need while allowing internal adapter dispatch to vary beneath it.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing slug-based adapter resolver in `pack_runtime_default.get_pack_adapter(...)`;
  - integrate it under one `Protocol`-backed runtime boundary in `pack_runtime_service.py`;
  - build only the missing narrow boundary object, hot-path caller migration, and updated guard/tests.
- Rejected options:
  - more web searches
  - keeping direct neutral-adapter imports as the active helper authority
  - moving hot-path callers straight to `get_pack_adapter(...)`
  - widening into legacy deletion

## Input baseline (FACT)
1. Live helper-authority split:
- `truffles-api/app/services/pack_runtime_service.py` imports broad helper behavior directly from `app.services.pack_runtime_neutral_adapter` (`build_info_combined_reply`, `format_reply_from_truth`, `build_quiet_hours_notice`, `build_evening_greeting`, signal helpers, truth loaders).
- `truffles-api/app/services/pack_runtime_default.py` already exposes slug-based `get_pack_adapter(client_slug)` routing to explicit pack adapters.
2. Live hot-path callers:
- `truffles-api/app/core/turn_executor.py` imports multiple broad pack helpers directly from `pack_runtime_service` on the active fact path.
- `truffles-api/app/services/tool_registry_service.py` imports a wide helper surface from `pack_runtime_service` and uses it on `catalog.location` / `catalog.service_query`.
3. Concrete drift proof already reproduced in the active worktree:
- `pack_runtime_service.build_info_combined_reply(client_slug='demo_salon', include_parking=True)` returns a different text/meta contract than `pack_runtime_default.build_info_combined_reply(...)`.
- `pack_runtime_service.format_reply_from_truth('promotions'|'hours', client_slug='demo_salon')` differs from `pack_runtime_default.format_reply_from_truth(...)`.
- `pack_runtime_service.build_quiet_hours_notice(client_slug='demo_salon', now_utc=2026-04-01T20:00Z)` returns `None` while `pack_runtime_default.build_quiet_hours_notice(...)` returns the demo-salon quiet-hours notice.
- `pack_runtime_service.build_evening_greeting(client_slug='demo_salon', now_utc=2026-04-01T20:00Z)` returns `Добрый вечер!` while `pack_runtime_default.build_evening_greeting(...)` returns `None`.
4. Existing guard still snapshots the old partial state:
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml` only tracks `pack_runtime_service.py` and `tool_registry_service.py` and still forbids `pack_runtime_default` imports in the service.

## Exact Path Map (mandatory)
1. Input
- User asks a fact/service question or policy-info interrupt on the live fact path.
2. Owner output
- Policy/core emits a fact decision or tool action such as `catalog.location`, `catalog.service_query`, or pack fallback.
3. Validator / interrupt arbitration
- Blocks A-D already preserve canonical owner/boundary behavior; the surfaced family is not at the semantic-owner or boundary layer.
4. Continuity preservation
- Blocks B/C/C.5/D already preserve continuity/fact scope on the touched envelopes; continuity is not the failing layer here.
5. Fallback / degrade
- `TurnExecutor._execute_fact(...)` imports pack helper behavior from `pack_runtime_service`.
- `tool_registry_service.execute_tool_action(...)` handles `catalog.location` and `catalog.service_query` using a wide helper import set from `pack_runtime_service`.
- `pack_runtime_service` then serves part of that behavior directly from `pack_runtime_neutral_adapter`, bypassing the selected pack adapter.
6. Final response
- The final fact reply/meta on the hot path can differ from the selected adapter contract because the facade itself is a second behavior owner.
7. Trace/meta evidence
- Tool path remains `catalog.location` / `catalog.service_query`; the drift happens underneath the tool layer in helper ownership.
8. Layer classification
- Primary: `fact_composition_error`
- Mechanism layer: `pack_runtime_boundary_error`
- Not this block: `owner_error`, `boundary_fallback_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- Live fact/runtime callers depend on a pack facade that still re-owns broad helper behavior through direct neutral-adapter imports instead of delegating through the selected pack adapter.

### Minimal reproduction
1. Compare `pack_runtime_service.build_info_combined_reply(..., client_slug='demo_salon')` with `pack_runtime_default.build_info_combined_reply(..., client_slug='demo_salon')`.
2. Compare `pack_runtime_service.format_reply_from_truth('promotions'|'hours', client_slug='demo_salon')` with the same calls through `pack_runtime_default`.
3. Compare `pack_runtime_service.build_quiet_hours_notice(...)` / `build_evening_greeting(...)` with `pack_runtime_default` for the same `demo_salon` inputs.
4. Inspect `turn_executor.py` and `tool_registry_service.py` and observe active hot-path imports from the broad helper surface in `pack_runtime_service.py`.

### Evidence
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_demo_adapter.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`

### Five Whys
1. Why do live fact replies drift from the selected pack adapter?
   - Because active hot-path callers use helper functions from `pack_runtime_service`.
2. Why does `pack_runtime_service` drift from the selected adapter?
   - Because the facade imports broad helper behavior directly from `pack_runtime_neutral_adapter`.
3. Why is that possible despite existing adapter routing?
   - Because `pack_runtime_default.get_pack_adapter(...)` exists but is not the behavior authority beneath the facade.
4. Why does this matter on the live product path?
   - Because `turn_executor.py` and `tool_registry_service.py` use those helpers on `catalog.location`, `catalog.service_query`, and pack fallback execution.
5. Why is this one shared mechanism instead of scenario-specific bugs?
   - Because every helper served directly from the neutral facade can bypass the selected adapter in the same way.

### Broken invariant
- Active pack/runtime behavior on the hot path must flow through one selected pack boundary, not through direct neutral imports inside the public facade.

### Shared mechanism
- `pack_runtime_service` bypasses adapter dispatch for broad helper behavior, while hot-path callers import that broad facade directly.

### Why the surfaced family belongs to that mechanism
- Location / hours / promotions / quiet-hours / evening-greeting drift all come from the same authority split beneath the live fact/tool path.

### Open-world envelope expected to improve
- any slug-selected pack-specific helper behavior on the live fact/service path
- `catalog.location` and `catalog.service_query` rendering
- pack fallback decisions and direct truth formatting used by active runtime callers
- future non-demo packs that rely on pack-specific adapter behavior under the same seam

### Root cause statement
- The pack/runtime seam is only partial because `pack_runtime_service` still serves broad helper behavior from direct neutral-adapter imports while active hot-path callers import that broad helper surface directly; therefore the selected pack adapter is not the sole behavior authority on the live fact path.

### Fix mechanism
- reuse the existing slug-based adapter resolver in `pack_runtime_default`;
- add one `Protocol`-backed runtime boundary object in `pack_runtime_service.py` that delegates helper behavior through the selected adapter;
- migrate active hot-path callers (`turn_executor.py`, `tool_registry_service.py`) to import only that boundary;
- update pack/runtime separation guard and focused tests to freeze the narrowed seam.

## Plan
1. Author this TP and keep governance docs untouched until Block E proof exists.
2. Materialize the narrow pack-runtime boundary in `pack_runtime_service.py` and route broad helper behavior through adapter dispatch.
3. Migrate active hot-path callers in `turn_executor.py` and `tool_registry_service.py` to the boundary.
4. Update the pack/runtime separation guard and focused tests.
5. Run focused deterministic checks.
6. If the touched behavior path changed product-visible output, run exactly one minimal replay on the affected fact/helper family.
7. Only after proof, sync state/governance/docs for `Block E`.

## DoD
- `pack_runtime_service.py` exposes one narrow runtime-facing boundary for active callers.
- Active hot-path callers no longer import a spread of pack helper functions from `pack_runtime_service`; they consume the narrow boundary instead.
- Broad helper behavior used on the active hot path delegates through the selected pack adapter instead of direct neutral imports.
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml` + `scripts/pack_runtime_separation_guard.py` freeze the narrowed seam.
- Focused deterministic tests are green.
- One minimal replay is run only if the touched behavior path changed visible output.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_runtime_service.py -k "pack_runtime_service or adapter or quiet_hours or greeting or info_combined"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "pack_runtime or catalog_location or service_query or direct_truth"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`
- `python3 scripts/pack_runtime_separation_guard.py`
- `git diff --check`
- focused replay command only if the touched behavior path changes product-visible output

## Evidence
- focused deterministic test output
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
- `scripts/pack_runtime_separation_guard.py`
- touched runtime code in `pack_runtime_service.py`, `turn_executor.py`, `tool_registry_service.py`
- one minimal replay directory under `/tmp/booking_quality/` only if needed
- closure replay proof: `/tmp/booking_quality/a922-block-e-replay-20260401h/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,family_registry.json}`

## Rollback
- revert only the touched files in this TP and return to the proven post-`Block D` base

## No-go
- no scenario patches
- no new `if demo_salon ...` behavior branches in runtime-core
- no direct `get_pack_adapter(...)` calls from active hot-path callers outside `pack_runtime_service.py`
- no widening into legacy deletion or operational dedupe
- no governance/state sync before full proof

## Risks / blockers
- focused tests may encode the previous neutral-adapter behavior and need contract-oriented updates
- hot-path callers may have hidden import assumptions that need caller-proof updates
- a minimal replay may surface an unrelated first-fail family; if so, record evidence only and do not hotfix it mid-block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- legacy webhook/info mesh still imports broad pack helpers outside the active hot path
- demo-salon knowledge code still exists as pack-specific adapter implementation
- operational dedupe and whole-system acceptance remain open

### Why not in this block
- this block narrows only the active runtime seam; legacy surface fate belongs to `Block F`, and demo-pack existence itself is not the bug once it sits fully behind the adapter boundary

### Risk if deferred
- without this block, active fact behavior still has a hidden second authority and later legacy drain remains unsafe or dishonest

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e5-owner-service-referent-grounding-a922.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (planned)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922.md` (planned)

### Expiry / trigger to stop deferral
- stop deferral immediately if any new active hot-path caller imports broad pack helper names instead of the pack-runtime boundary

## Next-block contract (mandatory)
### Next block objective
- `Block E.5 — Owner Service Referent Grounding`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
rg -n "service_missing_for_duration_query|clarify_missing_subject|duration|master" truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py
```

### Blocked-by conditions
- owner-side service referent grounding still fails on the focused fact-question family
- `Block E.5` does not yet have one exact web search and one proven RCA

### Owner role for closure
- Brain / Top Architect

## Closure evidence
- Mechanism landed:
  - `truffles-api/app/services/pack_runtime_service.py` now exposes `PackRuntimeBoundary` via `get_pack_runtime(client_slug)` and routes the active helper surface through selected-adapter dispatch instead of direct neutral helper ownership.
  - `truffles-api/app/core/turn_executor.py` now consumes the narrow boundary on the active fact path.
  - `truffles-api/app/services/tool_registry_service.py` now consumes the narrow boundary on the active `catalog.location` / `catalog.service_query` path.
- Deterministic proof:
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922/truffles-api && PYTHONPATH=. pytest -q tests/test_pack_runtime_service.py` -> `30 passed`
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922/truffles-api && PYTHONPATH=. pytest -q tests/test_consultant_core_runtime_contracts.py -k 'pack_runtime or catalog_location or service_query or direct_truth'` -> `10 passed`
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922 && PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_pack_runtime_separation_guard.py` -> `3 passed`
  - `cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922 && python3 scripts/pack_runtime_separation_guard.py` -> `Pack/runtime separation guard: OK`
  - `git diff --check` -> clean
- Focused replay proof:
  - invalid infra stubs `/tmp/booking_quality/a922-block-e-replay-20260401b`, `c`, `d`, `e`, `f`, and `g` are explicitly closed as non-evidence in their `manual_audit.json` artifacts
  - valid focused replay: `/tmp/booking_quality/a922-block-e-replay-20260401h`
  - `block-e-1` proves exact `hours` fact delivery through `catalog.location`
  - `block-e-3` proves `promotions` fact delivery through `catalog.service_query` while preserving booking continuity with `expected_reply_type="time"`
  - first remaining fail `LLM-QUAL-a922-block-e-replay-20260401h-002-01-c73b66` is `owner_error` (`service_missing_for_duration_query`) before pack/runtime boundary execution, so it does not reopen `Block E`
