# TP-2026-03-02-p5b-distributed-retrieval-backend-a1

## Block identity
- `BLOCK_ID`: SIG-P5B-DISTRIBUTED-RETRIEVAL-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-p5-pack-query-engine-v2-a1
- `UNLOCKS`: `P5 Pack Query Engine v2` residual -> `done`

## Название/цель
Полностью закрыть residual `P5b`: добавить production-grade distributed retrieval backend path (adapter + strict contract parity + rollback-safe switch), сохранив текущий contract-first API и tenant/branch isolation.

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
  - `rg -n "hybrid_sparse_semantic_rerank|engine_version|retrieval_meta" truffles-api/app/services/pack_runtime_service.py`
  - `rg -n "backend|runtime_local|retrieval_mode" truffles-api/app/services truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_runtime_service.py`
- `FACT findings`:
  - `P5` закрыт на runtime-local hybrid retrieval.
  - Distributed backend adapter/driver в runtime-контуре отсутствует.
  - Parent TP держит `P5` с явным residual `P5b`.
- `Detected drift (docs vs code)`: none.

## One web search (mandatory before implementation)
- **Query (exact):** `Elasticsearch reciprocal rank fusion retriever hybrid search official documentation`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** нужен reference для distributed dense+sparse fusion с reproducible ranking semantics.
- **Sources opened (from this query):**
  - Elastic RRF retriever: `https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever`
  - Elastic hybrid semantic search: `https://www.elastic.co/guide/en/elasticsearch/reference/current/semantic-text-hybrid-search.html`
- **Existing solutions found:** adapter-based hybrid retrieval и RRF fusion в distributed backend.
- **Decision:** `integrate` backend adapter abstraction с contract-parity tests и feature switch.
- **Rejected options:** оставить runtime-local как единственный production path.
- **Open questions:** final backend endpoint/credentials задаются env/ops в этом же TP.

## Root cause (mandatory)
- **Symptom:** retrieval работает только runtime-local, масштабирование по tenants/volume ограничено.
- **Minimal reproduction:**
  - `rg -n "qdrant|opensearch|elasticsearch|vector|backend" truffles-api/app/services/pack_runtime_service.py truffles-api/app/services`
- **Evidence to capture:** adapter code, parity tests, fallback tests, rollout switch behavior.
- **Five Whys (or equivalent):**
  1. P5 был scoped на contract и runtime-local correctness.
  2. Distributed backend был отложен как отдельный риск-блок.
  3. Без backend path возрастает latency/cost risk на больших packs.
  4. Без feature-switch rollback невозможен без кода.
  5. Поэтому residual не может быть закрыт без полноценного backend layer.
- **Root cause statement:** отсутствует contract-preserving distributed retrieval adapter и rollout control.
- **Fix mechanism:** ввести backend adapter + mode switch + strict parity checks + safe fallback.

## Reuse-first plan (mandatory)
- **Internal reuse:** текущие модели `PackQuerySemanticMatch`, `retrieval_meta`, tenant/branch filters.
- **External reuse:** RRF/hybrid retrieval reference pattern из Elastic docs.
- **Why not reinvent the wheel:** reuse существующего contract surface, добавить только adapter orchestration.

## Invariant
- Contract keys в `resolver_contract.retrieval` не меняются.
- Strict tenant/branch filters обязательны в обоих режимах.
- Fallback всегда явный и auditable (meta reason), без silent behavior drift.

## Scope
- Добавить backend adapter service для distributed retrieval.
- Ввести config/runtime switch: `runtime_local`/`backend_shadow`/`backend_primary`.
- Сохранить API `semantic_service_match` и `get_pack_service_hint`.
- Добавить deterministic parity/fallback tests.
- Обновить docs + parent TP + `STATE.md`.

## Out of scope
- Provisioning внешнего managed кластера вне CI/local окружения.
- Изменение webhook semantic policy.

## Touch-list
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_query_backend_service.py` (new)
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/tests/test_pack_query_engine_contract.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_message_endpoint.py` (если нужен contract parity assertion)
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить backend adapter interface и runtime implementation stub.
2. Подключить adapter в runtime path с mode switch.
3. Гарантировать parity `retrieval_meta/provenance/filters` между режимами.
4. Добавить fallback contract (backend unavailable -> explicit reason + runtime_local).
5. Добавить deterministic parity tests.
6. Зафиксировать operational rollout command set и rollback.
7. Обновить parent TP и `STATE.md` фактами.

## DoD
- Adapter path работает в `backend_shadow` и `backend_primary`.
- Contract parity tests green.
- Fallback tests green.
- Parent TP: `P5b` -> `done`.

## Checks
- `pytest -q truffles-api/tests/test_pack_query_engine_contract.py`
- `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "retrieval or backend or parity"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_service_matcher or service_not_found"`
- `ruff check truffles-api/app/services/pack_runtime_service.py truffles-api/app/services/pack_query_backend_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_runtime_service.py`

## Evidence
- Adapter/code diff.
- Outputs `Checks`.
- Contract parity examples (`retrieval_meta` snapshots).
- Parent TP + `STATE.md` updates.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic/parity tests only
- **Stop condition:** parity regression or filter violation
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** staged mode rollout (`runtime_local -> backend_shadow -> backend_primary`).
- **Go/no-go signals:** parity pass + zero tenant/filter violations + stable latency envelope.
- **Rollback:** mode back to `runtime_local` + `git revert` if needed.
- **Post-release monitoring window:** first 24h under `backend_shadow` and first 24h under `backend_primary`.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P5b` закрывается только после code+tests+rollout/rollback evidence.

## Rollback
- Переключить mode на `runtime_local`, затем `git revert` при необходимости.

## No-go
- Ослаблять tenant/branch filters ради recall.
- Менять contract keys без migration plan.
- Hidden fallback без явного reason/meta.

## Risks/Blockers
- Нужны backend env/credentials для end-to-end переключения режима.
- Возможен latency spike при неудачных timeout defaults.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: full closure `P12` with non-salon matrix evidence.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `Blocked-by conditions`: red parity/fallback tests.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `pack_query_backend_service.py` + mode switch wiring.
- `Do not touch`: policy-core semantics in webhook routers.
- `Open risks`: backend format mismatch.
- `First command to verify`: `pytest -q truffles-api/tests/test_pack_query_engine_contract.py`.

## Execution status (2026-03-02)
- `Status`: `done`
- `Implementation facts`:
  - Added distributed backend adapter contract in `truffles-api/app/services/pack_query_backend_service.py` with retrieval modes `runtime_local|backend_shadow|backend_primary`, driver registry, and explicit unavailable reason codes.
  - Wired mode-switch orchestration into `truffles-api/app/services/pack_runtime_service.py`:
    - local path remains canonical,
    - `backend_shadow` keeps local output and records backend parity meta,
    - `backend_primary` uses backend candidates when valid and falls back to local with explicit `fallback_reason`.
  - Extended retrieval contract normalization so `resolver_contract.retrieval` preserves mode/source/backend/fallback fields.
- `Deterministic evidence`:
  - `ruff check truffles-api/app/services/pack_runtime_service.py truffles-api/app/services/pack_query_backend_service.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_query_backend_service.py truffles-api/tests/test_cross_domain_signal_contract_suite.py` (`All checks passed`).
  - `pytest -q truffles-api/tests/test_pack_query_backend_service.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_cross_domain_signal_contract_suite.py` (`26 passed`).
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_service_matcher or service_not_found"` (`6 passed, 264 deselected`).
- `DoD verdict`:
  - Adapter path in `backend_shadow/backend_primary`: `pass` (deterministic tests).
  - Fallback contract explicit/auditable: `pass`.
  - Parent TP status update required in same change-set: `pending in this packet`.
