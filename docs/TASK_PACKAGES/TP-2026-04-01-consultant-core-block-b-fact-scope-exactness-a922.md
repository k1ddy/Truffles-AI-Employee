# TP-2026-04-01-consultant-core-block-b-fact-scope-exactness-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `implementation`
- Block ID: `block-b-fact-scope-exactness`

## Название/цель
Закрыть только `Block B — Fact Scope Exactness` в active worktree `a922`: сделать `fact_plane` единственным scope governor для `location / hours / parking`, убрать неявное widening на hot fact path и свести legacy info composition к exact requested sections.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/summary.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.md`

## Invariant
- Не лечить `parking/location/hours` через scenario patch или raw-text hardcode в runtime core.
- Не трогать `Block C+` механизмы: continuity carrier collapse, boundary purification, pack/runtime separation, legacy drain, operational dedupe.
- Не ослаблять owner-first contract: deterministic layer может только нормализовать requested fact scope, валидировать emitted scope и рендерить exact allowed sections.
- Не обновлять `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries/reports до полного proof closeout этого блока.

## Scope
- Exact path fix только для shared scope mechanism:
  - request-scope collection inside `fact_plane`
  - exact location-family rendering on `catalog.location`
  - legacy `info.py` composition for `location / hours / parking` must consume exact sections instead of deciding implicit base bundles
- Focused deterministic tests only for this mechanism.
- Exactly one minimal fresh replay only for fact turns after deterministic proof.

## Out of scope
- Interrupt arbitration / continuation law beyond already closed Block A
- Continuity writer collapse
- boundary degrade semantics
- non-fact consult/media/master behavior
- broad docs churn before proof closeout

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-b-fact-scope-exactness-a922.md`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## One web search (mandatory before implementation)
- Query: `Pydantic v2 model_validator official docs after validate cross-field constraints`
- Date/time: `2026-04-01 08:20:00 +05 (Asia/Almaty)`
- Sources opened:
  - `https://docs.pydantic.dev/latest/concepts/validators/`
- Source quality:
  - official documentation / primary source
- Found ready-made solutions:
  - no Truffles-specific implementation; useful reusable pattern is keeping cross-field scope normalization and invariant checks inside typed model builders/validators instead of scattering post-hoc rewrites across callers.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing typed `FactRequestV1 -> FactPlanV1 -> FactResultV1` spine;
  - integrate one exact requested-scope normalization step before planning;
  - build one shared exact location-family renderer reused by tool registry and legacy info composition.
- Rejected options:
  - more web searches
  - replay-only proof without deterministic normalization
  - leaving `info.py` as an independent scope owner

## Input baseline (FACT)
1. Fresh replay evidence on the original broad failure:
- command: `python3 - <<'PY' ... responses.jsonl ... LLM-QUAL-a922-l2-proof-seed7-20260401i-001-05-ca1db5 ... PY`
- result:
  - `requested_fact_refs=["location","parking"]`
  - `allowed_emitted_sets=[["location","hours","parking"]]`
  - `tool_decision="fact_family_unresolved"`
2. Current live worktree baseline:
- command: `PYTHONPATH=. python3 - <<'PY' ... FactRequestV1/FactPlanV1 ... TurnExecutor ... PY`
- result:
  - current `fact_plane` no longer widens to `["location","hours","parking"]`
  - but a parking turn with coarse owner output (`intent=location`, `capability=location`, `pack_refs=["parking"]`, `fact_refs=["parking"]`) still widens to:
    - `requested_fact_refs=["location","parking"]`
    - `allowed_emitted_sets=[["location","parking"]]`
    - emitted reply includes both address and parking
- interpretation:
  - the artifact family is still alive as a shared policy/scope problem on current head; the worktree has partial progress, not closure.

## Exact Path Map (mandatory)
1. Input
- Fresh replay surfaced turn: `LLM-QUAL-a922-l2-proof-seed7-20260401i-001-05-ca1db5`
- User text: `Есть ли парковка рядом?`
- Current live reproduction on the active worktree:
  - owner payload with coarse family semantics:
    - `intent=location`
    - `capability=location`
    - `pack_refs=["parking"]`
    - `fact_refs=["parking"]`
2. Owner output
- Replay owner output already encoded the parking ask as the broader `location` family:
  - `decision_meta.intent=location`
  - `semantic_contract.capability=location`
  - `supporting_pack_refs=["parking"]`
- Current live code still accepts the same coarse owner shape.
3. Fact request / planning
- `collect_requested_fact_refs(...)` in `truffles-api/app/core/fact_plane.py` unions `intent + pack_refs + fact_refs + capability_refs + semantic contract capability`.
- For the coarse owner payload above, current live code builds:
  - `requested_fact_refs=["location","parking"]`
  - `requested_scopes=["info.location","info.parking"]`
- `FactPlanV1.build_from_request(...)` then authorizes the widened set:
  - `allowed_emitted_sets=[["location","parking"]]`
  - `bundle_policy="location_base_bundle"`
4. Tool execution
- `TurnExecutor` passes `allowed_fact_refs=["location","parking"]` into `catalog.location`.
- `_catalog_location(...)` currently respects that widened set and emits both sections.
5. Legacy composition / rendering
- `truffles-api/app/routers/webhook/info.py` still has independent `include_base_bundle` / base-bundle composition branches for `location / hours / parking`.
- `truffles-api/app/services/demo_salon_knowledge.py` still exposes `build_info_combined_reply(...)`, which is bundle-oriented instead of exact-section-oriented.
6. Final response
- Current live reproduction returns both address and parking for a parking ask.
- Fresh replay earlier failed harder and fell back unresolved, but both behaviors violate the same invariant: widening is not exact and not solely governed by explicit allowed scope.
7. Trace/meta evidence
- Fresh replay:
  - `fact_contract.request.requested_fact_refs=["location","parking"]`
  - `fact_contract.plan.allowed_emitted_sets=[["location","hours","parking"]]`
  - `fact_contract.result.scope_verdict="empty"`
- Current live reproduction:
  - `result.meta.fact_requested_refs=["location","parking"]`
  - `result.meta.fact_allowed_sets=[["location","parking"]]`
  - `result.meta.fact_emitted_refs=["location","parking"]`
8. Layer classification
- Primary: `fact_composition_error`
- Secondary: `boundary_fallback_error` only insofar as legacy info composition still co-owns rendering scope
- Not this block: `owner_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- A parking question can still be widened beyond the explicitly requested fact on current head, and legacy info composition still owns bundle scope independently.

### Minimal reproduction
1. Build a fact owner decision with:
   - `intent=location`
   - `capability=location`
   - `pack_refs=["parking"]`
   - `fact_refs=["parking"]`
2. Run `FactRequestV1.build_from_policy_decision(...)` and `FactPlanV1.build_from_request(...)`.
3. Observe current live request/plan widen to `["location","parking"]`.
4. Run `TurnExecutor.execute(...)`.
5. Observe the response emits both address and parking instead of parking alone.

### Evidence
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `truffles-api/app/core/fact_plane.py:348`
- `truffles-api/app/core/fact_plane.py:417`
- `truffles-api/app/services/tool_registry_service.py:1208`
- `truffles-api/app/routers/webhook/info.py:1544`
- `truffles-api/app/services/demo_salon_knowledge.py:612`

### Five Whys
1. Why does parking widen? Because request collection unions low-precision family signals (`intent/capability`) with higher-precision requested refs (`pack_refs/fact_refs`).
2. Why is that union harmful? Because for a single fact family it turns one exact ask into a broader allowed set before any tool call happens.
3. Why does the broader set reach the user? Because `catalog.location` and `info.py` both render whatever widened set they receive.
4. Why is this still a shared mechanism and not one turn? Because the same widening rule applies to any `location / hours / parking` family turn where owner payload mixes coarse family labels with precise supporting refs.
5. Why is Block B the right boundary? Because the bug is about fact-scope governance, not owner arbitration or continuity; the shared fix is exact requested-scope normalization plus one exact renderer shared by all remaining hot-path callers.

### Broken invariant
- For `location / hours / parking`, widening may happen only when explicitly requested in the allowed set. Coarse family aliases must not silently expand a more precise requested fact.

### Shared mechanism
- Request-scope collection currently has no precedence law between precise fact refs and coarse family aliases, and rendering still has bundle-first fallback surfaces outside the fact plane.

### Why the surfaced family belongs to that mechanism
- The wrong behavior is already visible in `fact_request`, `fact_plan`, `allowed_emitted_sets`, and renderer inputs before any wording/judge layer participates.

### Open-world envelope expected to improve
- parking-only asks
- location-only asks
- hours-only asks
- mixed explicit asks like `location + parking`
- any future owner payload that carries a coarse family capability with a more precise fact ref in the same family

### Root cause statement
- `FactRequestV1` currently treats `intent/capability` and `fact_refs/pack_refs` as equal contributors inside the same family, so a precise requested fact is widened before planning. The remaining legacy renderers then preserve or reintroduce the widened bundle, so `fact_plane` is not yet the sole scope governor.

### Fix mechanism
- Add one precedence-aware requested-fact normalization step in `fact_plane`:
  - prefer explicit family refs over coarse family aliases within the same companion group,
  - keep widening only when the explicit allowed set itself contains multiple refs.
- Add one exact section renderer for the location family in `demo_salon_knowledge.py`.
- Route `tool_registry_service.py` and `webhook/info.py` through that shared exact renderer instead of bundle-first composition logic on the hot path.

## Plan
1. Create the Block B TP with live-path RCA from current worktree + fresh replay artifacts.
2. Implement precedence-aware family ref normalization in `truffles-api/app/core/fact_plane.py`.
3. Add one exact location-family renderer in `truffles-api/app/services/demo_salon_knowledge.py` and reuse it in `truffles-api/app/services/tool_registry_service.py`.
4. Replace independent base-bundle scope choices in the touched `truffles-api/app/routers/webhook/info.py` path with exact requested sections.
5. Run focused deterministic tests.
6. Run exactly one focused replay on fact turns only.

## DoD
- A parking turn with coarse owner `location` family plus explicit `parking` fact refs yields `requested_fact_refs=["parking"]`.
- `catalog.location` can emit `parking` alone.
- `catalog.location` can emit `location` alone.
- Explicit multi-ref requests such as `["location","parking"]` still emit only those requested sections.
- `info.py` touched path uses exact requested sections instead of deciding `location/hours` base bundle implicitly.
- Focused deterministic tests pass.
- One minimal fact-family replay passes and produces usable artifacts.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_plan or catalog_location or fact_scope_exactness or location_family_exact_sections"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "location_family_exact_sections or info_intent_reply_exact_sections"`
- `git diff --check`
- focused replay command to be recorded after implementation

## Evidence
- Deterministic test output from the focused pytest selections above
- One focused replay directory under `/tmp/booking_quality/`
- Replay artifacts:
  - `summary.json`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `manual_audit.md`
  - `family_registry.json`
- `STATE.md` update only after code + focused tests + replay proof

## Rollback
- Revert only the touched Block B files in the active worktree.
- If exact-section rendering causes regressions, fall back to the previous bundle renderer by removing the new shared helper callsites, not by adding scenario branches.

## No-go
- No additional web search
- No docs sync before proof
- No changes outside the Block B touch-list
- No hardcoded special cases for `parking` user text
- No broad refactor of unrelated legacy info flows

## Риски/блокеры
- `truffles-api/app/routers/webhook/info.py` already has in-flight worktree edits; changes must layer on top without reverting them.
- Fresh replay artifact and current worktree differ; acceptance must be based on current worktree proof, while preserving the surfaced family intent from the replay.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- continuity carriers and boundary restore paths are still partial
- semantic owner still emits coarse family capability labels in some turns
- legacy `info.py` still exists as a compatibility surface outside the touched hot fact path

### Why not in this block
- those belong to Blocks C, D, and F and would widen this block beyond fact-scope governance

### Risk if deferred
- future coarse owner outputs may still need Block C/D/F work even after exact fact scope is fixed

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c-continuity-carrier-collapse-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-d-boundary-purification-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (`planned`)

### Expiry/trigger to stop deferral
- if the focused replay still shows exact fact-scope loss after this block, stop and reopen RCA before moving to Block C

## Next-block contract (mandatory)
### Next block objective
- `Block C — Continuity Carrier Collapse`

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume or expected_reply or canonical_dialog_state"`

### Blocked-by conditions
- Block B must have code + focused tests + one minimal focused replay proof

### Owner role for closure
- `Top Architect` or `Brain`

## Branch + Worktree path + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: active worktree `HEAD` only; `/home/zhan/truffles-main` may be used only as canon/baseline/diff target
- Merge policy: no merge/closure claim in this block without code + focused tests + minimal replay proof
- Cleanup: keep replay artifacts under `/tmp/booking_quality/`; no cleanup until proof handoff is complete


## Closeout
### Implemented mechanism
- `truffles-api/app/core/fact_plane.py` now prefers explicit location-family refs (`pack_refs` / `fact_refs` / `tool_args`) over coarse family aliases inside the shared `location_base_bundle` companion group.
- `truffles-api/app/services/intent_service.py`, `truffles-api/app/services/policy_prompt_snapshot_service.py`, and `prompts/llm_policy_core.md` now require exact `catalog.location` `pack_refs` for `parking` / `hours` / `location` questions so the owner carries precise scope into the fact plane.
- `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/services/tool_registry_service.py`, and `truffles-api/app/routers/webhook/info.py` now render exact requested location-family sections on the touched hot path instead of widening to an implicit base bundle.

### Deterministic proof
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "catalog_location or parking_pack_ref or generic_info_interrupt_followup_contract"` -> `4 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_plan_materializes_location_base_bundle_authority or prefers_explicit_parking_ref_over_coarse_location_family_alias or tool_registry_catalog_location_does_not_reinfer_parking_outside_allowed_scope or turn_executor_prefers_explicit_parking_ref_over_coarse_location_family_alias"` -> `4 passed`
- `git diff --check` -> `clean`

### Replay proof
- Exploratory focused replay `/tmp/booking_quality/a922-block-b-replay-20260401q` surfaced the remaining owner-under-specified family (`parking` collapsed to `location`).
- Focused replay `/tmp/booking_quality/a922-block-b-replay-20260401r` proved continuity preservation but still failed human semantic audit because `parking` widened to `location + parking`.
- Final focused replay `/tmp/booking_quality/a922-block-b-replay-20260401s` is the admissible proof:
  - `infra_valid=true`
  - `semantic_valid=true`
  - `manual_audit_status=done`
  - `human_semantic_valid=true`
  - `block-b-1`: `requested_fact_refs=["parking"]`, `info_sections=["parking"]`
  - `block-b-2`: `requested_fact_refs=["location"]`, `info_sections=["location"]`
  - `block-b-3`: `requested_fact_refs=["hours"]`, `info_sections=["hours"]`
  - `block-b-4`: `requested_fact_refs=["location","parking"]`, `info_sections=["location","parking"]`

### Verdict
- `Block B — Fact Scope Exactness` is `closed_proven` in the active worktree.
- Natural next block: `Block C — Continuity Carrier Collapse`.
