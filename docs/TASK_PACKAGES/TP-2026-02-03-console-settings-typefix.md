# TP-2026-02-03-console-settings-typefix

- Название/цель: Исправить TypeScript ошибку в Settings (learning_consent_status undefined) и успешно пересобрать console-web.
- Canon refs: `STATE.md` GAP (console-web rebuild failed), PR #509 merge.
- Invariant:
  - Не менять API/DB.
  - Минимальная правка UI (типобезопасность).
  - Без неожиданных файлов в diff.
- Scope:
  - Исправить тип значения для ConfigCard на Settings странице.
  - Устранить типовую ошибку в Provisioning Wizard (working_hours day keys).
  - Пересобрать/перезапустить console-web.
  - Повторно проверить build SHA + merge ancestry.
  - Обновить `STATE.md` и сессию.
- Out of scope:
  - Любые изменения backend/контрактов.
  - Миграции или перезапуск других сервисов.
- Touch-list:
  - `console-web/src/app/settings/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `docs/TASK_PACKAGES/TP-2026-02-03-console-settings-typefix.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-03-console-settings-typefix-a5.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1. Исправить `learning_consent_status` (fallback к null).
  2. Исправить тип day key фильтра в Provisioning Wizard.
  3. Запустить `scripts/restart_console_web.sh` и сохранить лог.
  4. Проверить build SHA/time и merge ancestry; сохранить evidence.
  5. Обновить `STATE.md` + сессионные доки.
- DoD:
  - console-web build проходит.
  - Build SHA включает merge PR #509.
  - `STATE.md` содержит DONE с evidence.
- Checks:
  - `scripts/restart_console_web.sh`
  - `curl -s https://console.truffles.kz/settings`
  - `git merge-base --is-ancestor fd46d09005ab362bb94bde64b82cd1836655d39a ab4675825a7b9bf6423be711320d1f7b5b46bf24`
- Evidence:
  - `/tmp/console_web_redeploy_20260203c.txt`
  - `/tmp/console_build_verify_20260203c.txt`
- Rollback:
  - Реверт коммита или rebuild с предыдущим SHA.
- No-go:
  - Изменения API/DB.
  - Любые действия вне console-web.
- Риски/блокеры:
  - Build кеш не обновится или в проде останется старый bundle.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-settings-typefix-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-settings-typefix-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
