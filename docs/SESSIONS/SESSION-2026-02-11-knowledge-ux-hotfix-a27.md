# SESSION 2026-02-11-knowledge-ux-hotfix-a27 — Knowledge UX Hotfix

- status: active
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-02-11-knowledge-ux-hotfix-a27.md
- branch: fix/2026-02-11-knowledge-ux-hotfix-a27
- worktree: /home/zhan/truffles-main
- base_ref: origin/main
- scope: Исправить UX и контекстную логику вкладки Knowledge для Platform Admin + gateway error recovery.
- done:
  - Обновлена логика `console-web/src/app/knowledge/page.tsx`: effective values, branch diff gating, context refresh для specialists, gateway retry banner.
  - Прогнаны `npm run lint` и `npm run build` в `console-web`.
- next:
  - Проверить `scripts/session_check.sh`.
  - Сформировать commit и открыть PR.
- evidence:
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web` lint/build outputs
- last_updated: 2026-02-11
