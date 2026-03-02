# TP-2026-03-02-s4-cross-domain-contract-suite-a1

## Block identity
- `BLOCK_ID`: SIG-S4-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-s2-s3-signal-compiler-and-gate-v2-a1
- `UNLOCKS`: final P7 closure sync in parent TP

## Название/цель
Закрыть `S4 Cross-domain Contract Suite`: зафиксировать масштабируемость после firebreak через deterministic + quality contracts для минимум двух non-salon pack без runtime hardcode drift.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s2-s3-signal-compiler-and-gate-v2-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `ops/diagnose.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/services/booking_signal_service.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/tests/test_cross_domain_capability_isolation.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
- `Baseline commands`:
  - `rg -n "S4 Cross-domain Contract Suite|pending" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `rg -n "def _run_llm_quality_matrix|--client-slugs" ops/diagnose.py`
  - `rg --files truffles-api/app/knowledge`
- `FACT findings`:
  - Parent TP фиксирует `S4` как pending: dedicated non-salon deterministic/quality suite отсутствует.
  - В `app/knowledge` физически есть `demo_salon` и `generic`; нет оформленного контракта под два non-salon pack.
  - `llm-quality-matrix` поддерживает multi-slug запуск, но не валидирует cross-domain contract (min two non-salon).

## One web search (mandatory before implementation)
- **Query (exact):** pytest documentation parametrize multiple test data sets
- **Date/time (local):** 2026-03-02 09:54 +05
- **Why this query is precise:** для S4 нужен компактный deterministic suite, который проверяет одинаковый контракт на нескольких pack-конфигурациях без дублирования кода.
- **Sources opened (from this query):**
  - Pytest docs, parametrization guide: https://docs.pytest.org/en/stable/how-to/parametrize.html
- **Existing solutions found:** `pytest.mark.parametrize` как канонический способ зафиксировать один контракт на множестве domain datasets.
- **Decision:** reuse — построить S4 deterministic suite как параметризованный контракт по двум non-salon slug.
- **Rejected options:** копировать почти одинаковые тесты под каждый slug вручную (drift risk, хуже supportability).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** после S0/S1/S2/S3 нет доказательства, что сигнал/quality контракты масштабируются за пределы salon-домена.
- **Minimal reproduction:**
  - `rg -n "S4 Cross-domain Contract Suite" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `rg -n "demo_salon" truffles-api/tests | head`
  - `rg -n "llm-quality-matrix" ops/diagnose.py`
- **Evidence to capture:** new deterministic suite for 2 non-salon slug + matrix quality contract tests + parent TP status update.
- **Five Whys (or equivalent):**
  1. Почему S4 остался открытым? — не было отдельного artifact suite для non-salon packs.
  2. Почему это не поймали раньше? — focus был на firebreak (S0-S3), а не на cross-domain proof.
  3. Почему это риск? — возможен hidden salon bias в signal/tool/runtime path.
  4. Почему это мешает масштабированию? — без cross-domain контрактов любой новый pack требует ручной проверки.
  5. Почему чинить сейчас? — это последний блок для закрытия P7 continuity contract без residual ambiguity.
- **Root cause statement:** отсутствовал enforce-имый cross-domain contract suite (deterministic + quality gate) для non-salon packs.
- **Fix mechanism:** добавить parameterized deterministic suite с двумя non-salon pack datasets и quality-matrix cross-domain gate с test coverage.

## Reuse-first plan (mandatory)
- **Internal reuse:** существующий `llm-quality-matrix`, runtime truth context (`knowledge_runtime`), текущие signal/tool helper APIs.
- **External reuse:** pytest official parametrization pattern.
- **Why not reinvent the wheel:** расширяем текущий quality tooling и test contract, без нового фреймворка/параллельного раннера.

## Invariant
- Не ослаблять S3 hardcode gate.
- Не добавлять новые domain literals в runtime/core/signal.
- Сохранить backward compatibility `llm-quality-matrix` для explicit non-enforced режимов.

## Scope
- Добавить S4 deterministic suite для `info/booking/tool_registry` контракта на 2 non-salon pack datasets.
- Добавить в quality tooling cross-domain matrix contract validator (min non-salon packs) с mode `off|warn|block`.
- Добавить deterministic tests для нового matrix contract validator.
- Синхронизировать parent TP/status/session/STATE по факту S4.

## Out of scope
- Дорогие L3 acceptance run.
- Изменение бизнес-логики ответов вне контрактного scope S4.
- Создание production onboarding для реальных новых клиентов.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/SESSIONS/SESSION-2026-02-19-llm-first-firebreak-a1.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Добавить cross-domain matrix contract helper + parser args (`off|warn|block`) в `ops/diagnose.py`.
2. Покрыть helper deterministic тестами (валид/invalid/warn semantics).
3. Добавить parameterized deterministic suite для двух non-salon pack datasets, включая info/booking/tool usage contract.
4. Прогнать целевые test/lint/compile checks.
5. Обновить parent TP + state/session evidence по факту закрытия S4.

## DoD
- Есть отдельный deterministic suite, который проверяет минимум 2 non-salon pack datasets.
- `llm-quality-matrix` умеет fail-closed валидировать cross-domain contract в `block` режиме.
- Все checks из секции `Checks` зеленые.
- Parent TP отражает `S4 done` с evidence.

## Checks
- `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "cross_domain_matrix_contract"`
- `python3 -m py_compile ops/diagnose.py`
- `ruff check ops/diagnose.py truffles-api/tests/test_cross_domain_signal_contract_suite.py truffles-api/tests/test_booking_quality_status_gate.py`
- `scripts/session_check.sh`

## Evidence
- Diff runtime quality contract + new deterministic suite.
- Outputs всех checks.
- Обновленный статус в parent TP + STATE/session.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** deterministic only for this block.
- **Stop condition:** если изменение требует дорогих acceptance прогонов для базовой валидации S4 implementation.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** локальный deterministic contract-first rollout.
- **Go/no-go signals:** green checks + no regression in existing gate tests.
- **Rollback:** `git revert <commit>`.
- **Post-release monitoring window:** next quality matrix usage in dev lane.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `docs/SESSIONS/SESSION-2026-02-19-llm-first-firebreak-a1.md`
  - `STATE.md`
  - `STRUCTURE.md`
- `Drift closeout rule`:
  - S4 status sync делается в этом же блоке, без deferred doc debt.

## Rollback
- `git revert <commit>`

## No-go
- Не считать `generic` вторым non-salon pack для S4 closure.
- Не добавлять hardcode phrase/regex в runtime/core/signal для прохождения тестов.
- Не запускать expensive acceptance chain без отдельного PG checklist контекста.

## Risks/Blockers
- В репозитории нет реальных non-salon knowledge packs; mitigation: deterministic runtime-truth datasets в тестах.
- Возможен false-positive matrix gate в legacy usage; mitigation: explicit `off|warn|block` mode.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: non-salon quality runs в live/dev окружении пока не part of this implementation block.
- `Why not in this block`: требует отдельный environment readiness (keys/base-url/client availability), выходит за deterministic scope.
- `Risk if deferred`: S4 code-contract закрыт, но operational cadence matrix runs может отставать.
- `Linked follow-up Task Package(s)`: parent TP execution lane (L0-L3) with explicit matrix run evidence.
- `Expiry/trigger to stop deferral`: до следующего acceptance-candidate promotion.

## Next-block contract (mandatory)
- `Next block objective`: run matrix in controlled lane with real non-salon clients and attach evidence package.
- `First deterministic check command`: `python3 ops/diagnose.py llm-quality-matrix --client-slugs clinic_pack,dental_pack --cross-domain-contract block -- --mode llm --count 1 --base-url http://localhost:8000 --skip-outbox`
- `Blocked-by conditions`: missing runtime clients / missing judge key / no safe base-url.
- `Owner role for closure`: Brain + Top Architect.

