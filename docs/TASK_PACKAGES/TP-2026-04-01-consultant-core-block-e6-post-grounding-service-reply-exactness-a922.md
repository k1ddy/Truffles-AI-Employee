# TP-2026-04-01-consultant-core-block-e6-post-grounding-service-reply-exactness-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> RCA -> implementation -> closure`
- Block ID: `block-e6-post-grounding-service-reply-exactness`

## Название/цель
Закрыть только `Block E.6 — Post-Grounding Service Reply Exactness` в active worktree `a922`: once the owner has already grounded a service referent and selected `catalog.service_query`, the downstream pack/runtime reply path must emit exact non-clarifying `duration` / `master` facts from one canonical service referent view instead of falling into generic service clarify text or `service_not_found` admin deferral.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e5-owner-service-referent-grounding-a922.md`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/summary.json`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/responses.jsonl`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/manual_audit.md`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/manual_audit.json`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Invariant
- Do not reopen `Block A`..`Block E.5`.
- Do not move meaning ownership out of policy-core; owner grounding is already fixed in `Block E.5`.
- Do not patch replay scenarios, oracle thresholds, or prompt wording as a substitute for pack/runtime reply repair.
- Do not widen into legacy mesh drain or operational dedupe.
- Do not update `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries, or reports until this block itself is fully proven.

## Scope
- pack-side canonical service referent exactness for already-grounded `catalog.service_query` fact replies
- one shared runtime mechanism that covers both surfaced sibling turns:
  - `duration` reply exactness after grounding
  - `master` reply exactness after grounding
- focused deterministic checks and exactly one focused replay on this post-grounding reply family

## Out of scope
- owner grounding / prompt changes already closed in `Block E.5`
- legacy mesh fate
- operational dedupe
- broad whole-system replay

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e6-post-grounding-service-reply-exactness-a922.md`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org Python functools cache lru_cache immutable lookup table`
- Date/time: `2026-04-01 13:57:00 +0500 (Asia/Almaty)`
- Sources opened:
  - `https://docs.python.org/3/library/functools.html`
- Source quality:
  - Python official documentation / primary source
- Found ready-made solutions:
  - `functools.cache` / `lru_cache(maxsize=None)` is appropriate for immutable derived lookup tables reused across repeated calls;
  - cached pure functions are suitable when the index is computed from stable inputs and reused on hot paths.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing pack truth surfaces (`services_catalog`, `price_list`, `masters_catalog`, `domain_pack.service_taxonomy`);
  - integrate them behind one canonical cached referent view in the pack/runtime layer;
  - build only the missing shared index/normalization helpers and the touched reply-path rewiring.
- Rejected options:
  - extra web searches
  - owner/prompt patches for a pack-side reply bug
  - scenario-specific hardcodes for `укладка`

## Input baseline (FACT)
1. `Block E.5` replay proof exists at `/tmp/booking_quality/a922-block-e5-replay-20260401f` with `infra_valid=true` and `semantic_valid=true`.
2. Owner grounding is fixed on the touched turns:
- `LLM-QUAL-a922-block-e5-replay-20260401f-001-01-633ff6` emits `intent=duration`, `action=fact`, `tool_action=catalog.service_query`, `tool_decision=duration`, `requested_fact_refs=["duration"]`.
- `LLM-QUAL-a922-block-e5-replay-20260401f-002-02-232284` preserves booking continuity with `expected_reply_type="time"` while the duration interrupt stays on the fact path.
- `LLM-QUAL-a922-block-e5-replay-20260401f-003-01-5b7ce9` emits `intent=master_query`, `action=fact`, `tool_action=catalog.service_query`, `tool_decision=master`.
3. Human semantic audit is red for a new unrelated family:
- grounded `duration` still appends `Какая именно?` after the service is already resolved;
- grounded `master_query` still falls into `service_not_found` / admin deferral.

## Exact Path Map (mandatory)
1. Input
- user asks a grounded service fact question after `Block E.5`, for example `Сколько времени занимает укладка?` or `Кто делает укладку?`
2. Owner output
- policy-core already emits grounded `fact` decisions with `catalog.service_query` and resolved service referents (`укладка`)
3. Validator / interrupt arbitration
- no boundary or interrupt rewrite participates in the surfaced failure
4. Continuity preservation
- continuity remains intact; `Block E.5` already preserved the carried-service interrupt path
5. Fallback / degrade
- `duration` path: `tool_registry_service.execute_tool_action(... catalog.service_query ...)` calls `pack_runtime.build_runtime_service_duration_reply(...)`
- `master` path: `turn_executor.py` calls `pack_runtime.resolve_master_intent(...)` then `pack_runtime.build_master_reply_from_pack(...)`
6. Final response
- `duration` returns a generic clarify tail even though the service is already grounded
- `master` returns `service_not_found` / admin deferral even though the service was grounded and the tool path stayed factual
7. Trace/meta evidence
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/responses.jsonl`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/trace_bundle.jsonl`
- `truffles-api/app/services/pack_runtime_service.py:556`
- `truffles-api/app/services/pack_runtime_service.py:815`
- `truffles-api/app/services/pack_runtime_service.py:1680`
- `truffles-api/app/services/tool_registry_service.py:2274`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:732`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:823`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:922`
8. Layer classification
- Primary: `fact_composition_error`
- Mechanism layer: `pack_runtime_boundary_error`
- Not this block: `owner_error`, `boundary_fallback_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- After owner grounding succeeds, the downstream fact reply still degrades into generic clarify/admin-deferral behavior on styling service turns.

### Minimal reproduction
1. Replay `LLM-QUAL-a922-block-e5-replay-20260401f-001-01-633ff6` and inspect the final bot text for grounded `duration`.
2. Replay `LLM-QUAL-a922-block-e5-replay-20260401f-003-01-5b7ce9` and inspect `decision_meta.master_reply_mode` / final bot text for grounded `master_query`.
3. Inspect `truffles-api/app/services/pack_runtime_service.py` and `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`.

### Evidence
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/summary.json`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/responses.jsonl`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-block-e5-replay-20260401f/manual_audit.md`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
- active published runtime truth on replay branch `b7f75692-951e-421a-aae6-f5db97394799` (`knowledge_version=033ba3b8-a19a-4887-8587-aa761243f29c`) shows:
  - `effective_pack.services_catalog` has no styling/`Укладка` service row
  - `effective_pack.price_list` contains `Укладка феном`
  - `effective_pack.team.hair` exists
  - `effective_pack.masters_catalog` is absent

### Five Whys
1. Why does grounded `duration` still ask `Какая именно?`
   - Because the duration reply builder falls through to generic `duration_clarify` when the grounded service resolves only through compiled `price_list`/service-hint surfaces and not through a duration-bearing `services_catalog` row.
2. Why does the duration builder miss the grounded service?
   - Because runtime exactness is anchored to `services_catalog`, while the replayed styling referent is present only as an exact `price_list` item (`Укладка феном`) in the active published `effective_pack`.
3. Why does grounded `master_query` still hit `service_not_found`?
   - Because master reply matching depends on `masters_catalog.specialists[].services`, but the active published `effective_pack` used on replay has no `masters_catalog`; it exposes only coarse `team` summaries, and the current master reply path cannot bridge a grounded service referent into that compiled pack surface.
4. Why is this one shared mechanism instead of two unrelated bugs?
   - Because both surfaced failures start after owner grounding has already succeeded and then drift only when downstream pack/runtime reply builders consume different compiled pack surfaces (`services_catalog`, exact `price_list` items, coarse `team`) without one canonical post-grounding referent bridge.
5. Why is this not a new owner bug?
   - Because replay trace already shows grounded service referents and the correct factual tool path before the reply drifts.

### Broken invariant
- Once a service referent is already grounded and `catalog.service_query` is selected, downstream pack/runtime reply builders must not ask for the service again or pretend the service is unknown.

### Shared mechanism
- Pack-side post-grounding reply builders are still coupled to precompiled truth surfaces (`services_catalog`, `masters_catalog`) and do not reuse one canonical referent bridge across the actual published `effective_pack` surfaces (`services_catalog`, exact `price_list` items, coarse `team`).

### Why the surfaced family belongs to that mechanism
- The grounded styling turns fail only after control passes from the owner to pack/runtime reply builders, and both failures are explained by mismatched service surfaces inside the pack/runtime layer.

### Open-world envelope expected to improve
- grounded `duration` fact replies for services that resolve through generic category/taxonomy aliases
- grounded `master` fact replies for the same services
- future pack-specific service synonyms that span multiple truth surfaces

### Root cause statement
- The next live blocker is a pack-side post-grounding referent-bridge gap: after owner grounding succeeds, downstream reply builders still consume precompiled service surfaces directly and do not bridge grounded referents into the actual published `effective_pack` surfaces (`services_catalog`, exact `price_list` items, coarse `team`), so grounded service facts degrade into generic clarify or `service_not_found` behavior.

### Fix mechanism
- build one canonical pack-side post-grounding referent bridge from existing published truth surfaces and route both grounded `duration` and grounded `master` reply builders through it, so exact `price_list` referents and coarse `team` summaries can satisfy factual replies without re-opening owner or legacy layers.

## Plan
1. Reconstruct the exact grounded `duration` and `master` live paths from replay `a922-block-e5-replay-20260401f`.
2. Implement one shared pack-side referent exactness mechanism.
3. Add focused deterministic tests for grounded `duration` and `master` reply behavior.
4. Run focused deterministic checks.
5. Run exactly one focused replay on this post-grounding reply family.
6. Only after proof, sync state/governance/docs for `Block E.6`.

## DoD
- Grounded `duration` replies no longer ask `Какая именно?` when the service is already resolved.
- Grounded `master` replies no longer fall into `service_not_found` for the same surfaced service family.
- The fix is clearly pack-side/runtime-side and does not reopen `Block E.5` owner grounding.
- Focused deterministic checks are green.
- One focused replay exists with full human semantic audit.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_runtime_service.py -k "duration or master or styling or canonical_referent"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "catalog_service_query or duration or master or grounded_service"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "duration or master or service_query"`
- one focused replay command to be locked at block start

## Evidence
- focused deterministic test output
- one focused replay directory under `/tmp/booking_quality/`
- full manual audit artifacts for that replay

## Rollback
- revert only the touched pack/runtime files in this TP and return to the proven post-`Block E.5` base

## No-go
- no prompt or owner hardcodes for `укладка`
- no scenario-only patch
- no reopening of legacy mesh or operational paths
- no governance/state sync before full proof

## Risks / blockers
- the surfaced family may split between truth data gaps and runtime normalization gaps after exact code inspection
- runtime pack truth loaded under env/config may differ from static local truth and must be verified before coding

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- legacy mesh drain, operational dedupe, and whole-system acceptance still remain open later blocks

### Why not in this block
- this block is only about post-grounding pack-side reply exactness on the touched `catalog.service_query` family

### Risk if deferred
- subsequent blocks would be built on a false assumption that grounded service fact delivery is already product-correct

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`

### Expiry / trigger to stop deferral
- stop deferral immediately if the next focused replay shows any already-grounded `catalog.service_query` fact reply asking for the service again or deferring it as unknown

## Next-block contract (mandatory)
### Next block objective
- `Block F — Legacy Mesh Final Drain`

### First deterministic check command
```bash
cd /home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922
rg -n "app\\.routers\\.webhook|context_manager|session_memory|decision|info|response|_legacy|include_router|APIRouter" truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/core/consultant_runtime.py
```

### Blocked-by conditions
- any reclassification of `/tmp/booking_quality/a922-block-e6-replay-20260401r` from evaluator-only disagreement into a real product/runtime failure
- legacy mesh caller proof is not yet reconstructed from live code before edits begin

### Owner role for closure
- Brain / Top Architect

## Closure evidence
- Mechanism landed:
  - `truffles-api/app/services/pack_runtime_service.py` now resolves grounded service referents through one canonical post-grounding bridge spanning published `effective_pack` surfaces: `services_catalog`, exact `price_list` items, and coarse `team` summaries.
  - grounded `duration` replies now reuse exact `price_list` referents without re-asking for the service when the owner already grounded the referent.
  - grounded `master` replies now stay factual via `team_match` when the published pack has no `masters_catalog` specialist profiles but does expose a matching coarse `team` summary.
- Deterministic proof:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_runtime_service.py -k "duration or master or styling or canonical_referent"` -> `12 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "catalog_service_query or duration or master or grounded_service"` -> `5 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "duration or master or service_query"` -> `8 passed`
  - `git diff --check` -> clean
- Focused replay proof:
  - valid focused replay: `/tmp/booking_quality/a922-block-e6-replay-20260401r`
  - `infra_valid=true`, `semantic_valid=true`, `manual_audit_status=done`, `human_semantic_valid=true`
  - `LLM-QUAL-a922-block-e6-replay-20260401r-001-01-39b9bb` proves exact non-clarifying `duration` delivery for `Укладка феном`
  - `LLM-QUAL-a922-block-e6-replay-20260401r-002-01-1c35c0` proves factual team-backed `master` delivery with `master_reply_mode="team_match"` and no admin deferral
  - evaluator/judge disagreement remains on the team-backed master turn, but `oracle_winner=contract` plus full human audit keep that residual outside the product/runtime blocker set
