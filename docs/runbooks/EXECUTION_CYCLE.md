# EXECUTION CYCLE — Единый рабочий цикл для людей и агентов

## 1) Зачем документ

Этот runbook устраняет главный источник хаоса: разброс правил по разным документам.

Используйте его как единую операционную карту:
- что делать перед началом,
- что делать после каждого прогона,
- что фиксировать после каждой сессии,
- как закрывать фазу без потери качества.

Канон остаётся в `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/*`.  
Этот файл не заменяет канон, а связывает его в исполняемый цикл.

## 2) Golden Path (для нового человека/агента)

1. Прочитать в порядке:
   - `AGENTS.md` -> `STATE.md` (NOW) -> `STRUCTURE.md` -> профильные `SPECS/*`.
2. Выбрать ровно одну проблему из `STATE.md` (или сначала оформить GAP).
3. Подготовить `Task Package` (invariant/scope/touch-list/plan/DoD/checks/evidence/rollback/no-go + FACT pre-check + doc sync plan).
4. Выполнить FACT pre-check до первой правки:
   - проверить актуальный код/контракты/тесты по touch-list,
   - запустить baseline команды,
   - зафиксировать findings в report (`Input baseline (FACT)` + `FACT pre-check evidence`).
5. Запустить сессию:
   - `SESSION_AGENT=<agent> scripts/session_start.sh --session-id ... --task-package ...`
   - `scripts/install_hooks.sh`
   - `session_start` автоматически проверяет sync `main` с `origin/main` и блокирует дубли активного `BLOCK_ID` (если TP содержит block identity).
6. Выполнить one-issue flow:
   - 1 проблема -> 1 правка -> 1 проверка -> 1 запись evidence.
7. Закрыть сессию:
   - обновить `docs/SESSIONS/*` + `docs/SESSION_INDEX.md` + `STATE.md`,
   - `scripts/session_check.sh`,
   - commit.

Если трек использует zero-context blocks:
- включить session-scoped enforcement через поля `zero_context_*` в `docs/SESSIONS/SESSION-...md`;
- это не затрагивает параллельные сессии, где флаг не включен.

## 3) Что делать после каждого прогона

### 3.0 FACT pre-check (до первой правки блока)

Перед любыми изменениями обязательно:
1. Сверить `touch-list` с реальным кодом и контрактами.
2. Выполнить baseline-команды по затрагиваемому блоку (минимум один тест/проверка из planned checks).
3. Зафиксировать baseline как FACT в report:
   - `Input baseline (FACT)`,
   - `FACT pre-check evidence` (команда -> результат + file refs).
4. Если найден drift между docs и кодом:
   - зафиксировать в TP/report,
   - добавить doc sync в scope текущего блока или явный GAP/follow-up.

### 3.1 Local deterministic run (pytest/lint/typecheck)

После каждого прогона обязательно:
1. Зафиксировать точную команду.
2. Зафиксировать итог (`pass/fail`, числа тестов).
3. Если fail: сохранить пакет stop-the-line:
   - failed step, 5–15 строк ошибки, команда, окружение.
4. Обновить phase report (`docs/REPORTS/...phase...md`):
   - секции `Checks`, `Evidence`, `GAP` при провале.

### 3.2 Local realism run (core behavior)

После каждого realism-прогона обязательно:
1. Зафиксировать run command и run-id.
2. Сохранить артефакты (`summary.json`, `brief.md`, trace/meta evidence).
3. Проверить quality validity gate:
   - `infra_valid=true`, `semantic_valid=true`, `judge.enabled=true`.
4. При невалидном preflight:
   - статус `INVALID`, baseline/compare запрещены.
5. Обновить `STATE.md` как `FACT` только при наличии evidence.

### 3.2.1 LLM-quality lane policy (mandatory)

1. Работать по lane-модели:
   - `L0` static/contracts,
   - `L1` deterministic targeted,
   - `L2` micro fail-fast,
   - `L3` acceptance (`lock -> replay -> full`).
2. `L3` не использовать как debug-цикл; это только release-gate.
3. Перед любым `L3` обязательны `PG0..PG6` (Go-to-Full checklist из `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`).
4. Canonical entrypoint для llm-quality:
   - `scripts/llm_quality_guarded.sh`.
5. `python3 ops/diagnose.py llm-quality` допустим только для dev/forensic и не является acceptance evidence.
6. Если run `INVALID/NON-CANONICAL`:
   - не запускать следующий expensive run,
   - вернуться в `L1/L2`,
   - закрыть manual forensic SOP.

### 3.3 CI run

После каждого CI-прогона:
1. Сохранить run URL.
2. Зафиксировать статус по jobs.
3. При fail: stop-the-line пакет (run/job/step/error snippet/команда/матрица).
4. Обновить report + session log.

### 3.4 Live-check run

После каждого live-check:
1. Сохранить `conversation_id`.
2. Сохранить `decision_meta` и фрагмент `decision_trace`.
3. Зафиксировать outbox status (`queued/sent/failed`) при наличии.
4. Не сравнивать “красоту текста”; проверка по trace/meta контракту.

## 4) Что делать после каждой сессии

Обязательный чеклист:
1. `git status -sb` и `git diff --stat`.
2. Обновить session log:
   - `done`, `next`, `evidence`.
3. Обновить `STATE.md`:
   - `FACT` только с evidence, иначе `PLAN`/`GAP`.
4. Обновить phase/master report:
   - `Canon/doc sync updates` заполнен,
   - drift закрыт (или вынесен в явный GAP с owner/follow-up block).
5. Запустить `scripts/session_check.sh`.
6. Только после этого commit/push.

## 5) Что делать после каждой фазы

1. Создать phase report с вердиктом (`Passed/Blocked`).
2. Зафиксировать:
   - contract delta,
   - что проверили,
   - residual risks/GAP.
3. Закрыть doc/code drift по фазе:
   - обновить канон/спеки/аудит-доки по фактическому поведению,
   - либо зафиксировать explicit drift GAP (owner + follow-up block).
4. Обновить master report (execution status + next phase).
5. Подготовить следующий Task Package до начала следующей кодовой волны.

## 6) Единый артефактный минимум (Definition of Evidence)

Для каждой завершённой задачи должны существовать:
1. Task Package (`docs/TASK_PACKAGES/TP-...md`).
2. Report (`docs/REPORTS/...md`).
3. FACT pre-check evidence (команды + результаты + file refs до правок).
4. Проверки (команды + фактический результат).
5. Session log (`docs/SESSIONS/SESSION-...md` + индекс).
6. `STATE.md` запись с FACT/GAP.
7. Doc/code drift closeout (`Canon/doc sync updates` или explicit GAP).

Если любой пункт отсутствует, задача не считается закрытой.

Дополнительно для zero-context блоков:
- `scripts/zero_context_gate.sh --tp <task_package.md> --report <report.md>`
- обновление `docs/BLOCK_GRAPH.yaml` (status/depends/unlocks)

## 7) Типовые ошибки и как их предотвратить

1. Много параллельных задач в одной сессии.
   - Решение: держать one-issue flow.
2. Прогоны есть, а evidence не записан.
   - Решение: после каждого прогона сразу обновлять report.
3. Доки и код расходятся.
   - Решение: canon sync в той же фазе, не “потом”.
4. PASS локально, но нет CI/live контекста.
   - Решение: фиксировать full evidence contour по типу изменений.

## 8) Минимальный handoff формат (обязательный)

В конце сессии сдаём:
1. `git status -sb`
2. `git diff --stat`
3. Что изменили (1–3 пункта)
4. Как проверили (команды)
5. Evidence (файлы/URL/trace/meta)
6. Что осталось (GAP/риски/следующий шаг)
