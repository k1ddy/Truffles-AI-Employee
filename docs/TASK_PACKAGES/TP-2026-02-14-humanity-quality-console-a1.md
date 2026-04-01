# TP-2026-02-14-humanity-quality-console-a1

- Название/цель: Console quality PR-2 — сделать управление действиями Platform Admin проще и безопаснее: перенос рекомендованного действия из Today mode в Workspace, human-readable playbook по блокерам, снижение ручных ошибок.
- Canon refs: AGENTS.md; STATE.md NOW/GAP (console onboarding/integrations UX); PR #665 follow-up.
- Invariant: Не ломаем tenant isolation, hard-stop go-live, provider ops confirmation flow, существующие Console API контракты.
- Scope:
  - Frontend Console UX: Integrations Today -> Company Workspace handoff.
  - Workspace: явный «recommended action» + playbook по блокерам.
  - Небольшой safety слой для кликабельного UX без авто-исполнения операций.
- Out of scope:
  - Архитектурный rewrite Console Plane.
  - Изменения provider-side API ChatFlow.
  - Масштабные backend миграции.
- Touch-list (файлы/таблицы):
  - console-web/src/app/integrations/page.tsx
  - console-web/src/app/company-workspace/page.tsx
  - docs/SESSIONS/SESSION-2026-02-14-humanity-quality-console-a1.md
  - docs/SESSION_INDEX.md
- Plan (1..N):
  1. Добавить handoff recommended action из Today mode в Workspace через устойчивый context key.
  2. В Workspace показать явный блок «следующее действие» и кнопки открытия соответствующего action dialog.
  3. Добавить human-readable playbook по блокерам (RU labels, шаги, без тех-жаргона).
  4. Проверить мобильную/desktop читаемость (без горизонтального скролла критичных блоков).
  5. Прогнать lint/build и зафиксировать evidence.
- DoD:
  - Из Today mode можно перейти в Workspace с сохранённым контекстом и рекомендованным действием.
  - Workspace показывает понятный next action и playbook по текущим блокерам.
  - Нет regressions в provider action flow, hard-stop/go-live кнопках.
  - Frontend lint/build green.
- Checks:
  - cd console-web && npm run lint
  - cd console-web && npm run build
- Evidence:
  - GitHub PR URL
  - Локальные команды lint/build с pass
  - Короткая UX-сводка по изменениям в отчёте
- Rollback:
  - Откат PR целиком (revert merge commit) либо revert отдельных frontend коммитов.
- No-go:
  - Не добавлять авто-выполнение provider ops при открытии Workspace.
  - Не менять backend security/tenant checks без отдельного TP.
- Риски/блокеры:
  - Возможные несовпадения ожиданий по UX-текстам/терминологии.
  - Риск поломки e2e селекторов — минимизировать через сохранение существующих data-testid.
