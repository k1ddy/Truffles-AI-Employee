# TP-2026-02-03-console-merge-verify

- Название/цель: Пост-merge проверка: PR #509 (Provisioning Wizard UX) задеплоен, build консоли использует актуальный коммит.
- Canon refs: `STATE.md` (NOW: Web Console audit/UX fixes), PR #509.
- Invariant:
  - Не меняем код/API/DB и конфиги деплоя.
  - Только проверки + документация/evidence.
  - Без неожиданных файлов в diff.
- Scope:
  - Проверить merge PR #509 в `origin/main`.
  - Проверить build info в Settings и наличие новых UI строк в bundle.
  - Зафиксировать evidence в `/tmp` и `STATE.md`.
- Out of scope:
  - Любые изменения backend/frontend/инфры.
  - Перезапуск контейнеров, миграции, деплой.
- Touch-list:
  - `docs/TASK_PACKAGES/TP-2026-02-03-console-merge-verify.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-03-console-merge-verify-a5.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1. `git fetch origin`, подтвердить merge PR #509 и SHA.
  2. `curl` Settings bundle, извлечь build SHA/time и ключевые строки UI.
  3. Проверить, что build SHA содержит merge-коммит (merge-base).
  4. Записать evidence в `/tmp`, обновить `STATE.md` и `STRUCTURE.md`.
- DoD:
  - В `STATE.md` есть запись с evidence (build SHA/time, ссылки, /tmp логи).
  - Документация сессии обновлена, `SESSION_INDEX.md` обновлен.
- Checks:
  - `git fetch origin`
  - `curl -s https://console.truffles.kz/_next/static/chunks/app/settings/page-*.js`
  - `git merge-base --is-ancestor fd46d09005ab362bb94bde64b82cd1836655d39a 8078016f176e350f25edd81d36d1d875a2e1f422`
- Evidence:
  - `/tmp/console_build_verify_20260203.txt`
  - `/tmp/console_build_strings_20260203.txt`
  - запись в `STATE.md`.
- Rollback:
  - Реверт doc-коммита.
- No-go:
  - Изменения кода/контрактов/БД.
  - Любые действия на проде, кроме read-only проверок.
- Риски/блокеры:
  - Build еще не обновлен на проде (SHA не совпадает) -> фиксируем как GAP.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-merge-verify-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-merge-verify-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
