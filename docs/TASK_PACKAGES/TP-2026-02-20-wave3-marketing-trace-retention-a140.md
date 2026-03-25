# TP-2026-02-20-wave3-marketing-trace-retention-a140

- Название/цель: Закрыть runtime GAP Wave 3, где `decision_meta.marketing_reply_context=true`, но stage `marketing_reply_context` теряется в `decision_trace` при retention; подтвердить фикс повторным live smoke.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW GAP по Wave 3 trace retention), `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `docs/TASK_PACKAGES/TP-2026-02-19-marketing-postmerge-livecheck-a140.md`.
- CA_ID: N/A.

## Invariant
- Не ломаем существующий lifecycle маркетинга (`create -> preview -> execute`) и outbox safety.
- `decision_meta`/`marketing_context` остаются корректными.
- Trace retention остается bounded (`DECISION_TRACE_MAX`) без роста payload.

## Scope
- Минимальный runtime фикс retention в `webhook/trace.py` для stage `marketing_reply_context`.
- Дет. тесты на retention поведения для `marketing_reply_context`.
- Повторный runtime smoke и SQL/meta/trace проверка для того же сценария.
- Обновление `STATE.md` + session artifacts по результату.

## Out of scope
- Новые marketing features (segmentation/automation/AB).
- Изменения в UI.
- Рефактор всего decision entrypoint.

## Touch-list
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/test_webhook_trace.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-02-20-wave3-marketing-trace-retention-a140.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Исправить retention policy для сохранения stage `marketing_reply_context` в bounded trace.
2. Добавить/обновить unit tests для нового retention поведения.
3. Прогнать targeted deterministic checks.
4. Выполнить runtime smoke: campaign reply-context + SQL verification (`decision_meta`, `marketing_context`, `decision_trace` stage).
5. Зафиксировать FACT/GAP в `STATE.md` и закрыть сессию.

## DoD
- Для reply к marketing delivery stage `marketing_reply_context` присутствует в `decision_trace` (runtime факт).
- `decision_meta.marketing_reply_context` и `marketing_context` не регрессируют.
- Targeted tests проходят.
- `STATE.md` обновлен с evidence (FACT и/или GAP).

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/trace.py`
- `pytest -q truffles-api/tests/test_webhook_trace.py`
- `pytest -q truffles-api/tests/test_webhook_marketing_reply_context.py`
- Runtime smoke commands (Console API + SQL via `docker exec ... psql`), как в `TP-2026-02-19-marketing-postmerge-livecheck-a140.md`.

## Evidence
- Test outputs (pytest/py_compile).
- Runtime artifacts under `/tmp/marketing-live-20260220-*/`:
  - campaign create/preview/execute responses
  - SQL deliveries before/after reply
  - webhook replay result
  - `decision_meta`/`marketing_context`/`decision_trace` extracts
- `STATE.md` entry с абсолютными идентификаторами (`campaign_id`, `conversation_id`, `delivery_id`).

## Rollback
- Revert commit с trace retention fix.
- При runtime проблеме оставить marketing flow без изменения и вернуть предыдущий retention набор.

## No-go
- Нельзя принимать фикс без runtime evidence по `decision_trace`.
- Нельзя менять БД/trace вручную для имитации результата.
- Нельзя расширять scope beyond trace-retention bugfix.

## Риски/блокеры
- Runtime webhook secret/source mismatch для live smoke.
- Production backlog может влиять на скорость/стабильность smoke.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-20-wave3-marketing-trace-retention-a140`
- Worktree: `/home/zhan/worktrees/2026-02-20-wave3-marketing-trace-retention-a140`
- Base ref: `origin/main`
- Merge policy: PR to `main` (merge-only, no rebase)
- Cleanup: Brain/Top Architect после merge
