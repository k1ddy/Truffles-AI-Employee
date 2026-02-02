# TP-2026-02-02-console-pr-cleanup

- Название/цель: Чистая ветка для PR #504 (console inbox send state + e2e selection gate) без лишних файлов, чтобы починить красный CI.
- Canon refs: `STATE.md` NOW (блокер console-e2e-live), `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/SESSION_START_PROMPT.txt`.
- Invariant:
  - Нет новых фич/поведения, только перенос уже сделанных правок.
  - Никаких неожиданных файлов в diff.
  - CI остаётся единственным источником приёмки.
- Scope:
  - Создать чистую ветку от `origin/main`.
  - Перенести только нужные коммиты (inbox send state + e2e gate + refresh status).
  - Обновить PR #504 на чистую ветку и получить зелёный CI.
- Out of scope:
  - Любые новые UX/feature изменения.
  - Правки API/DB вне уже сделанных изменений.
- Touch-list:
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/components/ChatInterface.tsx`
  - `console-web/e2e/smoke.spec.ts`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-console-pr-cleanup.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-pr-cleanup-a5.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Создать новый worktree/branch от `origin/main`.
  2. Cherry-pick только нужные коммиты из старой ветки.
  3. Обновить PR #504 (новая чистая ветка или заменённый head).
  4. Проверить CI статус, при падении собрать причину и предложить фикс.
- DoD:
  - PR #504 указывает на чистую ветку без лишних файлов.
  - `console-e2e-live` зелёный или есть точный root-cause с ссылкой на run.
  - Документы сессии обновлены.
- Checks:
  - CI: `console-e2e-live` на PR.
  - Локально (если понадобятся изменения): `npm --prefix console-web run lint`, `npm --prefix console-web run test:e2e:smoke`.
- Evidence:
  - Ссылка на CI run + job.
  - Логи из `/tmp` при локальных проверках (если будут).
- Rollback:
  - Закрыть PR #504 или вернуть head на старую ветку.
- No-go:
  - Merge в `main`.
  - Force-merge без зелёного CI.
  - Любые изменения вне scope.
- Риски/блокеры:
  - `console-e2e-live` может падать из-за `CLIENT_SELECTION_REQUIRED` (см. STATE).
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-02-console-pr-cleanup-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-pr-cleanup-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only, без rebase
  - Cleanup: удалить worktree/branch после merge
