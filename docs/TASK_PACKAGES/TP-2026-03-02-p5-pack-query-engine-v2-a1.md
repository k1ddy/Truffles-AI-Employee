# TP-2026-03-02-p5-pack-query-engine-v2-a1

## Block identity
- `BLOCK_ID`: SIG-P5-PACK-QUERY-V2-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-s4-cross-domain-contract-suite-a1
- `UNLOCKS`: P5 closure in parent TP + P10/P12 acceptance lane progression

## Название/цель
Закрыть `P5 Pack Query Engine v2` как отдельный delivery block: внедрить гибридный retrieval (`sparse recall + semantic rerank`), добавить строгий tenant/branch filtering контракт и расширить provenance/meta для resolver без domain-hardcode в core.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s4-cross-domain-contract-suite-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/tests/test_pack_query_engine_contract.py`
  - `truffles-api/tests/test_pack_query_engine_abstain.py`
  - `truffles-api/tests/test_pack_runtime_service.py`
- `Baseline commands`:
  - `rg -n "semantic_service_match|ensure_resolver_meta|fact_bundle|abstain_reason" truffles-api/app/services/pack_runtime_service.py`
  - `rg -n "pack_query_engine|resolver_contract|abstain" truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_query_engine_abstain.py`
- `FACT findings`:
  - В `pack_runtime_service.py` есть resolver contract/provenance/fact_bundle, но retrieval path `hybrid + rerank + tenant/branch filters` отсутствует.
  - `pack_runtime_default/neutral` используют базовый semantic/service-match без explicit v2 retrieval meta.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenSearch hybrid search reranking docs`
- **Date/time (UTC):** `2026-03-02T08:45:21Z`
- **Why this query is precise:** нужен reference для реализации `hybrid retrieval` и `rerank` как отдельного engine path.
- **Sources opened:**
  - OpenSearch docs, hybrid search: `https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/`
  - OpenSearch docs, rerank processor: `https://docs.opensearch.org/latest/search-plugins/search-pipelines/rerank-processor/`
- **Existing solutions found:**
  - Hybrid combine нескольких retrieval-сигналов (sparse+dense).
  - Rerank как отдельный этап после candidate recall.
- **Decision:** `integrate`
  - Реализовать v2 path в pack runtime: deterministic sparse recall + adapter semantic signal + final rerank score.
- **Rejected options:**
  - Оставить single-path `semantic_service_match` без candidate fusion.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** P5 в parent TP оставался незакрытым: retrieval contract ограничивался semantic match и не имел explicit hybrid/rerank/filter semantics.
- **Minimal reproduction:**
  - `rg -n "semantic_service_match\(|get_pack_service_hint\(" truffles-api/app/services/pack_runtime_service.py`
  - `rg -n "hybrid|rerank|tenant|branch" truffles-api/app/services/pack_runtime_service.py`
- **Evidence to capture:** code diff + deterministic tests for hybrid/filter/provenance.
- **Five Whys (or equivalent):**
  1. Почему P5 считался open? Нет отдельного v2 query engine path.
  2. Почему это риск? Решение не масштабируется на multi-pack без явного filtering contract.
  3. Почему текущий слой недостаточен? Он enrich-ит meta, но не управляет retrieval stage.
  4. Почему нужно сейчас? Это прямой dependency для quality/acceptance contract и de-hardcoding стратегии.
  5. Почему не позже? Оставляет архитектурный debt и повышает риск локальных костылей в core.
- **Root cause statement:** отсутствовал единый runtime query-engine v2 с hybrid candidate fusion, rerank и strict context filtering.
- **Fix mechanism:** добавить engine в `pack_runtime_service.py` и переключить exported `semantic_service_match/get_pack_service_hint` на v2 path с fallback.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `semantic_service_match/get_pack_service_hint` из adapter как dense/fallback path.
  - `load_yaml_truth` и existing service catalog shape.
  - `RuntimeTruth` (`client_slug`, `branch_id`) из `knowledge_runtime.py`.
- **External reuse:** OpenSearch hybrid+rereank model as architectural pattern (not vendor coupling).
- **Why not reinvent the wheel:** повторное использование существующего adapter-слоя и truth schema, минимальный surface change.

## Invariant
- Никаких новых domain phrase/regex branchings в core/webhook.
- Existing resolver contract keys остаются совместимыми.
- При отсутствии уверенного match — fail-safe collect/handoff behavior без guessing.

## Scope
- В `pack_runtime_service.py`:
  - v2 query engine helpers: candidate extraction, sparse scoring, semantic signal fusion, rerank.
  - strict filter contract: client_slug + optional branch scope.
  - retrieval provenance/meta в resolver payload.
  - exported `semantic_service_match` и `get_pack_service_hint` используют v2 engine с fallback.
- Deterministic tests для v2 контракта.

## Out of scope
- Qdrant schema/storage migrations.
- L3 expensive acceptance runs.
- Изменения webhook policy/router бизнес-ветвлений.

## Touch-list
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/tests/test_pack_query_engine_contract.py`
- `truffles-api/tests/test_pack_query_engine_abstain.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить v2 query engine helpers и retrieval metadata contract.
2. Подключить v2 path в `semantic_service_match/get_pack_service_hint` с fallback.
3. Добавить deterministic tests (hybrid/rerank/filter/provenance).
4. Прогнать targeted test/lint/compile checks.
5. Обновить parent TP + STATE фактами и evidence.

## DoD
- `pack_runtime_service.semantic_service_match` использует v2 hybrid path.
- `get_pack_service_hint` использует тот же candidate engine.
- Есть tenant filter и optional branch filter в engine contract.
- Resolver/fact metadata включает retrieval provenance (`engine`, `method`, `scores`, `candidate_count`, `filters`).
- Все целевые deterministic тесты зеленые.

## Checks
- `pytest -q truffles-api/tests/test_pack_query_engine_contract.py`
- `pytest -q truffles-api/tests/test_pack_query_engine_abstain.py`
- `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "pack_query_engine or semantic_service_match or get_pack_service_hint"`
- `python3 -m py_compile truffles-api/app/services/pack_runtime_service.py`
- `ruff check truffles-api/app/services/pack_runtime_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_query_engine_abstain.py truffles-api/tests/test_pack_runtime_service.py`

## Evidence
- Code diff for P5 v2 engine.
- Outputs of all commands from `Checks`.
- Parent TP status delta + STATE FACT entry.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** deterministic only in this block
- **Stop condition:** regression in existing pack/runtime contract tests
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic-first rollout in branch PR.
- **Go/no-go signals:** all `Checks` pass; no contract regressions.
- **Rollback:** `git revert <commit>`
- **Post-release monitoring window:** next deterministic + CI pass for pack/runtime suites.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - P5 status update only after green deterministic evidence.

## Rollback
- Revert P5 commit(s) and rerun the same deterministic check set.

## No-go
- Не добавлять core phrase/regex business branching.
- Не ослаблять hardcode/deterministic gates.
- Не делать acceptance claims без P5 deterministic evidence.

## Risks/Blockers
- Возможен behavior drift в service hint heuristics; mitigation: targeted contract tests with fallback guarantees.
- Dataset может не содержать branch metadata; mitigation: strict branch filter применяется только при explicit scope в data/context.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:` full dense+sparse infra retrieval backend (external index orchestration) остаётся вне scope.
- `Why not in this block:` нужен отдельный infra rollout и migration plan.
- `Risk if deferred:` v2 engine останется runtime-local без distributed retrieval backend.
- `Linked follow-up Task Package(s):` TP-P5b infra-index rollout (to be created after this PR merge).
- `Expiry/trigger to stop deferral:` before production-grade multi-tenant heavy-load rollout.

## Next-block contract (mandatory)
- `Next block objective:` P9 text-oracle migration packet for remaining tests.
- `First deterministic check command:` `rg -n "must_include|contains|in response" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_demo_salon_eval.py`
- `Blocked-by conditions:` P5 checks not green.
- `Owner role for closure:` Brain + Top Architect.
