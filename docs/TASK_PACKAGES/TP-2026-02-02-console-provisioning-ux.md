# TP-2026-02-02-console-provisioning-ux

- Название/цель: Закрыть UX-04/UX-05 в Provisioning Wizard — guided inputs для JSON-полей + читаемый preview effective capabilities.
- Canon refs: `STATE.md` (UX backlog), `docs/CONSOLE_AUDIT/UX_BACKLOG.md`.
- Invariant:
  - Без изменений API/DB.
  - Поведение существующих JSON-полей сохранено (advanced JSON остаётся доступным).
  - Без неожиданных файлов в diff.
- Scope:
  - Guided inputs для `billing_info`, `working_hours`, `booking_settings`.
  - Читаемый preview effective capabilities + raw JSON в details.
  - Обновление UX backlog и STATE.
- Out of scope:
  - Изменения backend, контрактов или схем.
  - Новый функционал календаря/интеграций.
- Touch-list:
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-console-provisioning-ux.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-provisioning-ux-a5.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Добавить guided inputs и синхронизацию JSON (apply/sync).
  2. Улучшить preview effective capabilities (table/rows + JSON details).
  3. Обновить docs + CI.
- DoD:
  - UX-04/UX-05 помечены Fixed с PR/CI.
  - CI зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - CI на PR.
- Evidence:
  - CI run URL.
  - Локальный lint лог (если запускался).
- Rollback:
  - Реверт коммита или отключение guided inputs.
- No-go:
  - Изменения API/DB.
  - Тесты вне необходимости.
- Риски/блокеры:
  - Несоответствие JSON схемам; минимальный набор полей, advanced JSON остаётся доступным.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-02-console-provisioning-ux-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-provisioning-ux-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
