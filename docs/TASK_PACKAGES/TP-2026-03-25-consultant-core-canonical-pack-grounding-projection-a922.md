# TP-2026-03-25 Consultant Core Canonical Pack Grounding Projection A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-PACK-GROUNDING-PROJECTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `fa9e4db8`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md`
- `UNLOCKS`: one bounded cross-layer proof that `pack/grounding -> executor -> runtime continuity -> trace/meta` now uses the same canonical referent/entity substrate as `policy-core`

## Название/цель
Убрать remaining pack/grounding semantic dialect на active consultant-runtime path: pack runtime must emit canonical grounding (`entity_refs`, `referents`, provenance) in the same substrate vocabulary that runtime/state/trace already uses, and executor/runtime must consume that directly instead of interpreting `resolver_contract`, `slot_candidates`, and legacy `entity_refs{id,type,label}` as a parallel semantic language.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`

## FACT pre-check (before implementation)
- `git log --oneline -5` shows the latest bounded tool-slice commit `fa9e4db8`.
- `git status --short --branch` is clean on `feat/2026-03-15-consultant-core-governance-lock-a922`.
- Current active pack runtime still emits a separate grounding dialect in `truffles-api/app/services/pack_runtime_service.py`:
  - `resolver_contract.entity_refs` uses legacy `id/type/label`
  - `resolver_contract.slot_candidates` uses a separate slot-oriented dialect
  - `resolver_candidates`, `fact_bundle`, and legacy `provenance` duplicate semantic grounding outside the canonical substrate
- Current typed runtime path does not merge pack grounding into the canonical runtime `semantic_contract`:
  - `truffles-api/app/core/turn_executor.py` attaches pack meta as side metadata only
  - `truffles-api/app/core/dialog_state_service.py` builds runtime semantic contract mainly from `decision.meta["semantic_contract"]` plus booking/tool arg shadows, not canonical pack grounding
- Repo scan confirms the active typed runtime path in `app/core/*` has no direct readers of `resolver_contract`, `resolver_candidates`, `slot_candidates`, `fact_bundle`, or legacy `provenance`; surviving direct reads are compatibility-only in `pack_runtime_service` helpers and frozen/legacy webhook surfaces.

## One web search (mandatory before implementation)
- **Query (exact):** `JSON Schema object additionalProperties official docs`
- **Date/time (local):** `2026-03-25 22:04:00 +05`
- **Sources opened (from this query):**
  - JSON Schema official docs, `Additional Properties: Objects | A Tour of JSON Schema` — `https://tour.json-schema.org/content/03-Objects/02-Additional-Properties`
- **Existing solutions found:** strict object contracts should define explicit allowed properties and reject undeclared semantic carriers; extra semantic payloads should not grow implicitly beside the canonical object.
- **Decision:** reuse the existing canonical referent/entity vocabulary and emit one explicit grounding object from pack runtime instead of growing more sidecar semantic keys beside `resolver_contract`.
- **Rejected options:**
  - keep `resolver_contract` / `resolver_candidates` as the primary grounding contract and only mirror it into trace/meta
  - add another pack-only semantic object with new vocabulary instead of reusing canonical referents/entities
  - keep `slot_candidates` as the pack semantic source-of-truth for grounded service meaning
- **Source quality:** official JSON Schema documentation only

## Root cause (mandatory)
- **Symptom:** after the tool protocol slice, pack runtime still emits grounding meaning in its own dialect, so the active runtime path still has two semantic languages: canonical `semantic_contract` and pack-native `resolver_contract` / `slot_candidates` / legacy `entity_refs`.
- **Minimal reproduction:** inspect `ensure_resolver_meta()` in `truffles-api/app/services/pack_runtime_service.py`, then inspect the pack reply path in `truffles-api/app/core/turn_executor.py` and runtime continuity merge in `truffles-api/app/core/dialog_state_service.py`.
- **Evidence:**
  - `truffles-api/app/services/pack_runtime_service.py:1243-1548`
  - `truffles-api/app/core/turn_executor.py` pack fallback path
  - `truffles-api/app/core/dialog_state_service.py` runtime semantic-contract merge path
  - `truffles-api/tests/test_pack_runtime_service.py`
  - `truffles-api/tests/test_pack_query_engine_contract.py`
  - `truffles-api/tests/test_pack_grounding_contract.py`
- **Root-cause classification (mandatory):**
  - A. pack/grounding dialect: `semantic protocol/model` mismatch — chosen for this block
  - B. legacy `expected_reply_*` / `last_question_type` projections: `continuity/state` + `observability` mismatch — deferred until pack slice lands
  - C. final cross-layer closure proof: `evaluation/process` gap — deferred until pack slice lands and is verified
- **Five Whys:**
  1. Why is pack grounding still a separate language? Because `ensure_resolver_meta()` still materializes grounding into `resolver_contract`, `resolver_candidates`, `slot_candidates`, and legacy `provenance`.
  2. Why is that a real semantic mismatch? Because runtime/state/trace already speak canonical `semantic_contract` with canonical `entity_refs` and `referents`.
  3. Why does the mismatch survive after the tool slice? Because pack reply handling still attaches pack grounding as side metadata instead of merging it into the canonical semantic substrate.
  4. Why does continuity not fully absorb it? Because runtime semantic-contract construction still reads mostly from decision-level semantic contract and booking/tool projections, not canonical pack grounding.
  5. Why does this keep semantic unification incomplete? Because grounded service/provenance facts from packs still enter runtime through a second pack-specific dialect.
- **Root cause statement:** the remaining active defect is a pack-grounding protocol mismatch: pack runtime still emits grounded entities/referents/provenance through pack-specific carriers, so executor/runtime/trace do not consume one canonical grounding substrate end-to-end.
- **Fix mechanism:** emit canonical grounding from pack runtime using the existing referent/entity vocabulary, merge that grounding into the runtime semantic contract in the executor, and persist the same contract through continuity and trace/meta while demoting `resolver_contract` and related pack-native carriers to compatibility projection only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `semantic_contract.v1` referent/entity vocabulary
  - existing `TurnExecutor` semantic-contract attachment path
  - existing `DialogStateService` runtime semantic-contract writer
  - existing `ConsultantRuntime` trace/meta projection
- **External reuse:** JSON Schema official object-contract guidance
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** the repo already has the canonical semantic substrate, but pack runtime still does not emit or merge into it directly.

## Invariant
- Policy-core remains the only semantic owner.
- Pack runtime may contribute grounded entities/referents/provenance only; it must not become a second semantic owner.
- Deterministic layers may normalize, merge, project, and persist canonical grounding; they must not reinterpret user text.
- No new regex/phrase branching in core.

## Scope
- add canonical grounding payload to `pack_runtime_service.ensure_resolver_meta()`
- merge canonical pack grounding into executor/runtime semantic contract on the active typed runtime path
- make continuity/state/trace/meta carry the same canonical pack-grounded referents/entities/provenance
- add targeted tests proving runtime no longer depends semantically on `resolver_contract` / `slot_candidates` / legacy pack `entity_refs`

## Out of scope
- deleting all compatibility projections in frozen/non-active webhook paths
- legacy expected-reply projection shrinkage
- acceptance replay / lock reset
- retrieval backend algorithm changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-pack-grounding-projection-a922.md`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_pack_query_engine_contract.py`
- `truffles-api/tests/test_pack_grounding_contract.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Add canonical pack grounding payload (`entity_refs`, `referents`, provenance) to `pack_runtime_service` while keeping legacy resolver fields as compatibility projection only.
2. Update executor pack-reply handling to merge canonical pack grounding into the active runtime `semantic_contract`.
3. Update runtime continuity/state merge so execution-time canonical grounding persists into runtime state and later policy-core memory/trace.
4. Add focused regressions for `pack_runtime -> canonical grounding`, `pack grounding -> executor semantic contract`, and `runtime trace/meta carries the same grounded contract`.
5. Run the required deterministic suites and update `STATE.md` before merge if green.

## DoD
- pack runtime emits canonical grounding using the same referent/entity vocabulary as `semantic_contract.v1`
- executor/runtime consume canonical pack grounding directly on the active typed runtime path
- runtime trace/meta expose canonical pack-grounded semantic state
- legacy `resolver_contract` / `resolver_candidates` / `slot_candidates` are no longer semantic source-of-truth on the active runtime path

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/pack_runtime_service.py truffles-api/app/core/turn_executor.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/app/services/intent_service.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_grounding_contract.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_runtime_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_query_engine_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pack_grounding_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff + single commit
- targeted unit/contract test outputs
- required local suite outputs
- runtime test proof that canonical pack grounding reaches semantic contract + trace/meta

## Rollback
- `git revert <commit>` for the bounded pack-grounding migration commit
- if pack/runtime continuity regresses, reopen RCA instead of reintroducing pack-native semantic carriers as runtime truth

## No-go
- no new pack-only semantic vocabulary
- no runtime semantic repair layer
- no retrieval/backend rewrite
- no treating `resolver_contract` / `slot_candidates` as canonical semantic state after this block
- no closure claim without cross-layer runtime evidence

## Risks/Blockers
- pack runtime tests currently assert legacy resolver fields and will need explicit migration or compatibility framing
- runtime continuity may currently ignore execution-time semantic grounding and require a merge-path adjustment
- some non-active/frozen callers may still inspect legacy pack meta fields even after the active path stops depending on them

## Which semantic dialect is being eliminated in this block?
- The pack/grounding dialect: `resolver_contract`, `resolver_candidates`, `slot_candidates`, and legacy pack `entity_refs{id,type,label}` as semantic grounding carriers on the active runtime path.

## Which layers will speak one language after this block?
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- policy-core memory normalization path in `truffles-api/app/services/intent_service.py`
- runtime trace/meta emitted from `consultant_runtime`

## Which semantic dialect still remains afterward, if any, and why?
- legacy `expected_reply_*` / `last_question_type` compatibility projections still remain afterward because this block is bounded to pack grounding first.
- compatibility projections inside frozen/non-active webhook paths may still carry legacy pack fields, but they will no longer be the semantic source-of-truth on the active typed runtime path.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: legacy expected-reply projection fields and frozen/non-active compatibility readers of old pack meta.
- `Why not in this block`: this block is bounded to canonicalizing active pack grounding first.
- `Risk if deferred`: compatibility surfaces can still reintroduce drift outside the active typed runtime path.
- `Linked follow-up Task Package(s)`: follow with a dedicated legacy projection reduction block after the pack slice lands green.
- `Expiry/trigger to stop deferral`: before claiming one canonical semantic protocol across owner/state/tools/packs/trace end-to-end.

## Next-block contract (mandatory)
- `Next block objective`: reduce remaining legacy expected-reply and question-type compatibility projections so canonical semantic/question contracts become the only runtime source-of-truth.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/core truffles-api/app/services`
- `Blocked-by conditions`: failing required local suites or evidence that active runtime still depends on pack-native semantic carriers
- `Owner role for closure`: Brain / Top Architect
