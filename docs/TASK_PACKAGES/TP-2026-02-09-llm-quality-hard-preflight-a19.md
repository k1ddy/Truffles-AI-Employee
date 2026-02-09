# TP-2026-02-09-llm-quality-hard-preflight-a19

- Название/цель: Закрыть корневой разрыв в `ops/diagnose.py llm-quality`: hard preflight webhook-secret branch-match, разделение infra/semantic валидности, канонический baseline только judge-on, root regression на `missed_question`, fail-rule по `policy_core_mode=degraded_fallback`.
- Canon refs: `STATE.md` NOW (policy-core runtime hardening + strict replay gate), follow-up на quality gate integrity; `AGENTS.md` (P0/P1 fitness, stop-the-line), `SPECS/SYSTEM_REFERENCE.md` (trace/meta evidence).

## Invariant
- Runtime-контракт FACT/COLLECT/HANDOFF и safety guardrails в webhook не меняются.
- `llm-quality` не должен давать «валидные» выводы при infra-проблеме (secret mismatch/network/trace-fetch errors).
- Сравнение метрик допускается только на валидной инфраструктуре и каноническом baseline (judge-on).

## Scope
- `ops/diagnose.py`: добавить hard preflight для webhook_secret branch/client match перед запуском dialog loop.
- `ops/diagnose.py`: ввести `infra_valid` и `semantic_valid`; блокировать metric comparison при infra-fail.
- `ops/diagnose.py`: baseline сравнение только с judge-on baseline; judge-off baseline помечать non-canonical.
- `ops/diagnose.py`: fail-rule по `degraded_fallback_rate` (пороговый gate).
- Тесты: добавить/обновить регрессии в `truffles-api/tests/test_booking_quality_*` и `truffles-api/tests/test_message_endpoint.py` (missed_question collect-policy contract).

## Out of scope
- Рефактор runtime decision pipeline.
- Новые БД-миграции.
- Полная переработка сценариев quality runner.

## Touch-list (files/tables)
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_progress_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_message_endpoint.py`
- (опционально новый) `truffles-api/tests/test_booking_quality_status_gate.py`

## Plan (1..N)
1. Добавить helper-слой в `ops/diagnose.py`: secret resolve+preflight match, baseline canonical judge-on check, quality status computation.
2. Подключить в `_run_llm_quality`: hard stop на secret mismatch; собрать `infra_valid/semantic_valid`; заблокировать delta/regression при infra-fail.
3. Добавить `degraded_fallback_rate` в метрики/thresholds/regression и fail-rule gate.
4. Обновить baseline logic: non-canonical baseline (judge-off) не использовать для сравнения.
5. Добавить тесты на новые gate/helper правила и regression test для collect-policy (`next_question/open_questions/expected_reply_type`).
6. Прогнать targeted checks и собрать evidence.

## DoD
- `llm-quality` завершает run как INVALID при webhook_secret mismatch до отправки сценариев.
- В summary есть разделённые статусы `infra_valid` и `semantic_valid` + причина блокировки сравнения.
- Baseline judge-off не участвует в canonical comparison (явный status/reason).
- `degraded_fallback_rate` выше порога вызывает gate fail.
- Regression test подтверждает collect-policy contract для missed_question-случая.

## Checks
- `python3 -m py_compile ops/diagnose.py`
- `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_collect_sets_expected_reply_type"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core"`

## Evidence
- Вывод hard preflight mismatch (INVALID RUN).
- `summary.json` c `infra_valid/semantic_valid` и blocked comparison reason.
- pytest outputs по обновлённым/новым тестам.
- `git status -sb`, `git diff --stat`, PR ссылка.

## Rollback
- Revert одного коммита ветки (`git revert COMMIT_SHA_FROM_THIS_BRANCH`), без миграций.

## No-go
- Не ослаблять runtime safety/policy guards ради green quality-run.
- Не возвращать скрытые fallback/guessing ветки.
- Не подменять baseline/метрики вручную вне кода runner.

## Риски/блокеры
- Старый baseline judge-off может сразу блокировать regression compare (ожидаемое изменение поведения).
- Ужесточение infra gate может поднять частоту INVALID RUN при нестабильной среде — это полезный сигнал, но потребует операционной дисциплины.

## Branch / Worktree
- Branch: `feat/2026-02-09-llm-quality-hard-preflight-a19`
- Worktree: `/home/zhan/worktrees/2026-02-09-llm-quality-hard-preflight-a19`
- Base ref: `origin/main`
- Merge policy: PR в `main`, без rebase.
- Cleanup: после merge — `scripts/session_end.sh --status done`, удалить worktree/branch.
