# TP-2026-02-19-platform-health-remediation-a120

- Название/цель: Убрать шумный/бесполезный P1-баннер и сделать incident UX операционно полезным: корректный Redis-сигнал, 30m hide без всплытия, без режима "свернуть", быстрый refresh и actionable remediation в OPS/Workspace.
- Canon refs: `STATE.md` NOW (runtime/ops blockers), `AGENTS.md` (Stop-the-line, one-issue flow, fitness), live evidence `/tmp/console_incident_analysis_2026-02-19/*`.

## Invariant
- Не ломаем текущие RBAC права и навигационные контракты Console.
- Не ослабляем P0/P1 detection для реального backlog (критерии backlog остаются жесткими).
- Redis обязателен: недоступность/невалидность Redis остаётся инцидентом.

## Scope
- Health incident banner UX: hide на 30 минут должен полностью убирать баннер; убираем toggle "Свернуть/Развернуть".
- Refresh UX: делаем быстрый отклик кнопки и ограничиваем "залипание" состояния обновления.
- Incident semantics: учитываем обязательность Redis в причине/ранбуке.
- OPS/Workspace value layer: показываем быстрые remediation шаги (по reason_code/reason_label), fallback-гайд где и как чинить.

## Out of scope
- Полная перестройка domain-model инцидентов.
- Масштабный redesign страниц Console.
- Изменение бизнес-процессов маркетинга (Wave 3/4).

## Touch-list
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/lib/api-client.ts`
- `truffles-api/app/routers/console.py`
- `console-web/tests/e2e/*` (точечный тест/обновление)

## Plan
1. Подправить backend health contract: Redis обязательный, explicit причина.
2. Переделать banner behavior (always-expanded, true hide-30m, refresh UX guard).
3. Привязать incident actions/reason к OPS/Workspace с быстрым runbook-блоком.
4. Добавить/обновить e2e/unit тесты на hide/CTA/useful guidance.
5. Прогнать targeted checks и собрать evidence.

## DoD
- Кнопка `Скрыть на 30м` полностью убирает баннер ровно на 30 минут.
- Кнопки `Развернуть/Свернуть` отсутствуют; баннер по умолчанию всегда показывает полный reason+runbook.
- `Обновить health` не зависает в долгом state; UI возвращается в стабильное состояние даже при медленном запросе.
- При деградации Redis причина и шаги remediation явно отражены (не generic).
- OPS и Workspace показывают actionable guidance: что делать сейчас, где смотреть, что запускать dry-run/execute.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && npm run test -- --runInBand` (если есть suite)
- `cd console-web && npx playwright test tests/e2e/platform-admin.spec.ts --grep "health incident|ops|workspace"`
- `pytest -q truffles-api/tests/test_console_ops_jobs.py`
- `python3 -m py_compile truffles-api/app/routers/console.py`

## Evidence
- Скриншоты до/после и click-path: banner -> OPS/Workspace.
- JSON evidence: `/api/proxy/health`, `/api/proxy/admin/incidents`, `/api/proxy/business/incidents`.
- Тестовые логи (lint/playwright/pytest/py_compile).
- STATE update фиксирует Brain/Top Architect.

## Rollback
- Revert коммита с TP-изменениями.
- Временный fallback: отключить banner-incident rendering feature-флагом (если потребуется hotfix).

## No-go
- Не игнорировать Redis как необязательный dependency.
- Не оставлять generic runbook без reason-specific подсказок.
- Не добавлять неиспользуемые CTA/кнопки без измеримой пользы.

## Branch / Worktree
- Branch: `feat/2026-02-19-platform-health-remediation-a120`
- Worktree: `/home/zhan/worktrees/2026-02-19-platform-health-remediation-a120`
- Base ref: `origin/main`
- Merge policy: PR в `main` после локальных checks + evidence.
- Cleanup: после merge удалить ветку/worktree.
