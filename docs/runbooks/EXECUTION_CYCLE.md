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
3. Подготовить `Task Package` (invariant/scope/touch-list/plan/DoD/checks/evidence/rollback/no-go).
4. Запустить сессию:
   - `SESSION_AGENT=<agent> scripts/session_start.sh --session-id ... --task-package ...`
   - `scripts/install_hooks.sh`
5. Выполнить one-issue flow:
   - 1 проблема -> 1 правка -> 1 проверка -> 1 запись evidence.
6. Закрыть сессию:
   - обновить `docs/SESSIONS/*` + `docs/SESSION_INDEX.md` + `STATE.md`,
   - `scripts/session_check.sh`,
   - commit.

Если трек использует zero-context blocks:
- включить session-scoped enforcement через поля `zero_context_*` в `docs/SESSIONS/SESSION-...md`;
- это не затрагивает параллельные сессии, где флаг не включен.

## 3) Что делать после каждого прогона

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
4. Обновить phase/master report.
5. Запустить `scripts/session_check.sh`.
6. Только после этого commit/push.

## 5) Что делать после каждой фазы

1. Создать phase report с вердиктом (`Passed/Blocked`).
2. Зафиксировать:
   - contract delta,
   - что проверили,
   - residual risks/GAP.
3. Обновить master report (execution status + next phase).
4. Подготовить следующий Task Package до начала следующей кодовой волны.

## 6) Единый артефактный минимум (Definition of Evidence)

Для каждой завершённой задачи должны существовать:
1. Task Package (`docs/TASK_PACKAGES/TP-...md`).
2. Report (`docs/REPORTS/...md`).
3. Проверки (команды + фактический результат).
4. Session log (`docs/SESSIONS/SESSION-...md` + индекс).
5. `STATE.md` запись с FACT/GAP.

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
