# TP-2026-02-03-console-redeploy-verify

- Название/цель: Пересобрать console-web после merge PR #509 и повторно проверить, что build включает merge коммит.
- Canon refs: `STATE.md` (GAP: build не включает PR #509), PR #509.
- Invariant:
  - Не менять код/API/DB.
  - Только rebuild/restart console-web + проверки.
  - Без неожиданных файлов в diff.
- Scope:
  - `scripts/restart_console_web.sh` (build + restart).
  - Проверка build SHA/time и ancestry к merge PR #509.
  - Обновление `STATE.md` + evidence.
- Out of scope:
  - Любые изменения backend/контрактов/БД.
  - Миграции или перезапуск других сервисов.
- Touch-list:
  - `docs/TASK_PACKAGES/TP-2026-02-03-console-redeploy-verify.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-03-console-redeploy-verify-a5.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1. `git fetch origin` и зафиксировать merge SHA PR #509.
  2. `scripts/restart_console_web.sh` (build/restart) с логом в `/tmp/console_web_redeploy_20260203.txt`.
  3. Проверить settings bundle: build SHA/time + merge ancestry, записать `/tmp/console_build_verify_20260203b.txt`.
  4. Обновить `STATE.md` (DONE или GAP) + сессионные доки.
- DoD:
  - `STATE.md` содержит запись с evidence (build SHA/time + merge ancestry).
  - Сессия закрыта, `docs/SESSION_INDEX.md` обновлен.
- Checks:
  - `scripts/restart_console_web.sh`
  - `curl -s https://console.truffles.kz/settings`
  - `git merge-base --is-ancestor fd46d09005ab362bb94bde64b82cd1836655d39a 8078016f176e350f25edd81d36d1d875a2e1f422`
- Evidence:
  - `/tmp/console_web_redeploy_20260203.txt`
  - `/tmp/console_build_verify_20260203b.txt`
- Rollback:
  - Повторный restart с предыдущим SHA (если нужен).
- No-go:
  - Любые изменения кода/конфигов.
  - Действия вне console-web.
- Риски/блокеры:
  - Build в проде не обновится (кеш/прокси/перезапуск не применился).
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-redeploy-verify-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-redeploy-verify-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
