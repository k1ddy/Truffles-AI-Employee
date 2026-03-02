# TP-2026-03-02-p5b-distributed-retrieval-backend-a1

## Block identity
- `BLOCK_ID`: SIG-P5B-DISTRIBUTED-RETRIEVAL-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-p5-pack-query-engine-v2-a1
- `UNLOCKS`: closure of P5 residual debt and production-grade multi-tenant retrieval scale path

## Название/цель
Закрыть residual `P5b`: перевести pack query retrieval из runtime-local candidate scan к distributed/index-backed backend с тем же contract-first интерфейсом (`retrieval_meta`, tenant/branch strict filters, provenance).

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p5-pack-query-engine-v2-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/app/services/knowledge_runtime.py`
  - `truffles-api/tests/test_pack_query_engine_contract.py`
  - `truffles-api/tests/test_pack_runtime_service.py`
- `Baseline commands`:
  - `rg -n "_build_pack_query_candidates|hybrid_sparse_semantic_rerank|engine_version" truffles-api/app/services/pack_runtime_service.py`
  - `rg -n "engine_version|retrieval_meta|filters" truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_runtime_service.py`
- `FACT findings`:
  - `P5` реализован как runtime-local hybrid engine в `pack_runtime_service.py`.
  - В коде отсутствуют backend connectors/orchestrators для distributed retrieval.
  - Residual официально зафиксирован в P5 TP как `TP-P5b`.
- `Detected drift (docs vs code)`: none.

## One web search (mandatory before implementation)
- **Query (exact):** `Elasticsearch reciprocal rank fusion retriever hybrid search documentation`
- **Date/time (local):** `2026-03-02 14:52, Asia/Almaty`
- **Why this query is precise:** нужен production reference для dense+sparse fusion в distributed backend.
- **Sources opened (from this query):**
  - Elastic docs, RRF retriever: `https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever`
  - Elastic docs, hybrid semantic search: `https://www.elastic.co/guide/en/elasticsearch/reference/current/semantic-text-hybrid-search.html`
- **Existing solutions found:**
  - distributed dense+sparse fusion через RRF;
  - staged rollout с backward-compatible retrieval contract.
- **Decision:** `integrate`
  - Ввести backend adapter interface и контрактно совместимый retrieval payload.
- **Rejected options:**
  - Оставить runtime-local retrieval как единственный production path.
- **Open questions:**
  - целевой backend в прод-контуре (`qdrant/opensearch/elastic`) фиксируется отдельным infra decision record.

## Root cause (mandatory)
- **Symptom:** `P5` закрыт по runtime contract, но scale backend отсутствует.
- **Minimal reproduction:**
  - `rg -n "qdrant|opensearch|elasticsearch|vector" truffles-api/app/services/pack_runtime_service.py`
- **Evidence to capture:** adapter interface diff + fallback behavior tests + contract parity tests.
- **Five Whys (or equivalent):**
  1. Почему residual остался? P5 scope ограничен runtime-local path.
  2. Почему это риск? рост dataset/tenants увеличит latency/cost и усложнит ranking quality.
  3. Почему не закрыт в P5? высокий infra blast radius.
  4. Почему отдельный TP? нужен staged rollout + rollback plan.
  5. Почему сейчас важно? без этого блокируется production-scale path.
- **Root cause statement:** отсутствует distributed retrieval adapter, сохраняющий текущий contract-first интерфейс.
- **Fix mechanism:** ввести retrieval backend abstraction + strict contract mapping + fail-safe fallback на current runtime-local engine.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `PackQuerySemanticMatch`, `retrieval_meta`, `_build_pack_query_retrieval_meta`, filter contract.
- **External reuse:** RRF/hybrid pattern from Elastic docs.
- **Why not reinvent the wheel:** reuse contract layer и staged adapter вместо полной замены runtime.

## Invariant
- `resolver_contract.retrieval` backward compatibility.
- strict tenant/branch filters остаются обязательными.
- fail-safe fallback без silent behavior drift.

## Scope
- Add backend adapter interface (`pack_query_backend_service.py` or equivalent).
- Add config-driven backend selection with default `runtime_local`.
- Keep `semantic_service_match/get_pack_service_hint` API unchanged.
- Add deterministic contract parity tests (`runtime_local` vs backend stub).

## Out of scope
- Реальный infra provisioning/cluster ops.
- Acceptance L3 runs в этом блоке.
- Изменения webhook router semantics.

## Touch-list
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_query_backend_service.py` (new)
- `truffles-api/tests/test_pack_query_engine_contract.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить backend adapter contract (`search`, `suggest`, `meta`).
2. Подключить adapter в pack runtime через feature/config switch.
3. Сохранить strict scope filters и retrieval metadata parity.
4. Добавить deterministic parity tests + fallback tests.
5. Обновить TP/STATE фактами.

## DoD
- Есть backend adapter слой и config switch.
- Current runtime-local path остается default и проходит прежние тесты.
- Contract parity tests green.
- Residual `P5b` переведен в implemented/ready-for-infra-rollout state.

## Checks
- `pytest -q truffles-api/tests/test_pack_query_engine_contract.py`
- `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "pack_query_engine or retrieval"`
- `ruff check truffles-api/app/services/pack_runtime_service.py truffles-api/app/services/pack_query_backend_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_runtime_service.py`

## Evidence
- Adapter interface/code diff.
- Contract parity tests output.
- Parent TP + `STATE.md` updates.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** deterministic contract tests only
- **Stop condition:** parity regressions in retrieval contract
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** feature-flagged phased rollout (`runtime_local` -> `backend_shadow` -> `backend_primary`).
- **Go/no-go signals:** parity tests + no increase in abstain mismatches.
- **Rollback:** switch backend mode to `runtime_local` + revert if needed.
- **Post-release monitoring window:** first 24h with retrieval parity telemetry.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P5b` status updated only after deterministic parity evidence.

## Rollback
- Set backend mode back to `runtime_local`; revert block commits.

## No-go
- Нельзя ломать retrieval contract keys.
- Нельзя отключать strict filters ради recall.
- Нельзя делать hidden fallback без reason/meta.

## Risks/Blockers
- Backend choice ambiguity (needs owner decision).
- Latency overhead if adapter call path not cached.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: backend infra provisioning and ops playbooks may remain outside app repo.
- `Why not in this block`: app-level remediation separated from infra deployment wave.
- `Risk if deferred`: no production-scale search path for large tenants.
- `Linked follow-up Task Package(s)`: infra rollout TP (to be created after backend contract merge).
- `Expiry/trigger to stop deferral`: before enabling backend mode in production.

## Next-block contract (mandatory)
- `Next block objective`: infra rollout TP with canary and rollback scripts.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_pack_query_engine_contract.py -k "backend"`
- `Blocked-by conditions`: missing backend decision / credentials.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: adapter interface skeleton in `pack_query_backend_service.py`.
- `Do not touch`: existing policy-core and webhook routing logic.
- `Open risks`: backend mismatch vs contract format.
- `First command to verify`: `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "retrieval"`
