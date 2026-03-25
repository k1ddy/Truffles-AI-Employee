# TP-2026-03-05-e2d-acceptance-process-unblock-a1

## Название/цель
Убрать process-level deadlock в acceptance lock-цикле (E2d): дать строго ограниченный recovery-путь для повторного lock при non-canonical process-fail без ослабления acceptance quality gates.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: `Block E / E2`, `Block E / E2c canonical acceptance path`)
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2c-canonical-replay-canary-a1.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`

## One web search (mandatory before implementation)
- Query: `AWS Builders Library retries idempotent operations backoff`
- Date/time (UTC): `2026-03-04T06:35:41Z`
- Sources opened:
  - `https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/`
- Ready solutions found:
  - Ретраи допустимы только для идемпотентных/безопасных операций и должны быть явно ограничены условием применения.
  - Recovery-путь должен быть наблюдаемым (причина, контекст, явное включение), иначе ретраи маскируют корень.
- Decision:
  - `integrate`: добавить explicit forensic-override только для lock-повтора после process/preflight non-canonical stop-reason.
- Rejected alternatives:
  - `allow_no_code_delta` в acceptance (нарушает quality constant contract).
  - Неограниченный lock retry без reason-code фильтра.

## Root cause (mandatory)
- Symptom:
  - `E2c` lock/replay циклы блокируются до semantic verdict: `invalid_run_economy_preflight` -> `invalid_quality_constant_preflight`.
- Minimal reproduction:
  1. Выполнить acceptance lock, получить non-canonical process stop.
  2. Запустить следующий lock на том же кодовом fingerprint.
  3. Получить `lock_fingerprint_unchanged_after_non_canonical`.
  4. Попытаться обойти через `--allow-no-code-delta` и получить `acceptance_disallows_allow_no_code_delta`.
- Evidence:
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r17/summary.json`
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r18/summary.json`
  - Код: `ops/diagnose.py` (`_llm_quality_build_run_economy_status`, `_llm_quality_build_quality_constant_status`)
- Five Whys:
  1. Почему lock не перезапускается канонично?  
     Потому что fingerprint совпадает после non-canonical lock.
  2. Почему это блокирует повтор?  
     Run-economy block запрещает неизменный fingerprint после non-canonical lock.
  3. Почему нельзя использовать существующий override?  
     Acceptance lane запрещает `allow_no_code_delta` quality-constant gate.
  4. Почему возник deadlock?  
     Нет узкого recovery-механизма для process-only non-canonical lock.
  5. Почему это системная проблема?  
     Процессные preflight-сбои и semantic-сбои обрабатываются одинаково на шаге lock-retry.
- Root cause statement:
  - В acceptance lock loop отсутствовал контрактный, узко-ограниченный retry-path для process-only non-canonical lock; существующий обход конфликтовал с quality-constant правилами.
- Fix mechanism:
  1. Ввести отдельный флаг `--allow-non-canonical-lock-retry`.
  2. Разрешать lock retry только при `previous_lock_canonical=false` и stop-reason из process/preflight allowlist.
  3. В acceptance разрешить этот override только для lock-mode (не replay).
  4. Добавить контрактные тесты на allowed/blocked ветки.

## Invariant
- Acceptance gates fail-closed остаются включены.
- `allow_no_code_delta` в acceptance по-прежнему запрещен.
- Override не применяется к semantic non-canonical lock.

## Scope
- `ops/diagnose.py` run-economy + quality-constant preflight contract.
- Контрактные тесты `truffles-api/tests/test_booking_quality_status_gate.py`.

## Out of scope
- Semantic фикс policy-core (`wrong_action`, `booking_flow_break` и т.п.).
- Изменения chain step ordering (`lock -> replay -> canary -> full`).

## Touch-list (файлы/таблицы)
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2d-acceptance-process-unblock-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `STATE.md`

## Plan (1..N)
1. Добавить узкий forensic override аргумент в `llm-quality` и `llm-quality-gates`.
2. Реализовать eligibility-фильтр process stop-reason в run-economy lock retry.
3. Ограничить override в acceptance только lock-mode на quality-constant слое.
4. Добавить и прогнать контрактные тесты.
5. Синхронизировать TP/STATE с evidence.

## DoD
- Новый override не ломает существующие run-economy/quality-constant контракты.
- Есть тесты на:
  - process-eligible lock retry -> `valid=true`.
  - non-process stop reason -> `valid=false`.
  - acceptance replay + override -> fail-closed.
- `ruff` + целевые `pytest` зеленые.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "non_canonical_lock_retry or run_economy_blocks_lock_with_unchanged_non_canonical_fingerprint or run_economy_allows_lock_with_unchanged_canonical_fingerprint or quality_constant_acceptance_lane_requires_canonical_envelope"`
- `ruff check ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`

## Evidence
- Code diff:
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
- Test result:
  - `6 passed, 82 deselected`
  - `ruff: All checks passed`

## Release safety (mandatory)
- Rollout strategy: не требуется (изменение acceptance tooling/quality pipeline).
- Go/no-go signals: тесты и run-economy/quality-constant contract behavior.
- Rollback: revert commit с E2d-изменениями.

## Rollback
- `git revert <commit_sha>` для E2d-блока.

## No-go
- Нельзя ослаблять acceptance quality-constant требования.
- Нельзя использовать override для replay/canary/full.
- Нельзя применять override для semantic non-canonical stop-reason.

## Риски/блокеры
- Даже после process-unblock semantic-блокеры E2 (`r13`) могут остаться.
- Scenario-generation stall может потребовать отдельного SLA-guard в следующем блоке.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - Непрозрачная длительность scenario generation перед runtime phase.
- Why not in this block:
  - Блок фокусируется на deadlock между run-economy и quality-constant.
- Risk if deferred:
  - Возможны дорогие lock-прогоны с ранним manual abort.
- Linked follow-up Task Package(s):
  - `TP-2026-03-06-e2e-scenario-generation-sla-guard-a1` (to create).
- Expiry/trigger to stop deferral:
  - Если следующий acceptance lock снова упирается в scenario-generation stall > SLA.

## Next-block contract (mandatory)
- Next block objective:
  - Провести канонический `lock -> replay` после E2d на firebreak runtime и проверить снятие process blocker.
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "non_canonical_lock_retry"`
- Blocked-by conditions:
  - Нет актуального firebreak runtime (`LLM_POLICY_CORE_ENABLED=1`, `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=1`).
  - Наличие незакрытого pending manual audit для последнего acceptance run.
- Owner role for closure:
  - Hands (runtime execution + artifacts), Brain/Top Architect (acceptance sign-off).
