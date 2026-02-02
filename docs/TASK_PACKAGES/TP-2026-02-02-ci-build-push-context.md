# TP-2026-02-02-ci-build-push-context

- Название/цель: Починить CI `build-push` (main) после смены Dockerfile контекста на repo-root.
- Canon refs: `STATE.md` (NOW: CI build-push failure on main), `TECH.md` (CI), `.github/workflows/*`.
- Invariant: без изменений runtime/поведения; livecheck не трогаем; Dockerfile не меняем.
- Scope:
  - Обновить CI build-push шаги на context repo-root и явный путь к Dockerfile.
- Out of scope:
  - Любые изменения `truffles-api` runtime/Dockerfile, livecheck, tests.
- Touch-list:
  - `.github/workflows/ci.yml` (или файл, где определен build-push).
- Plan:
  1) Найти build-push job/steps в CI workflow.
  2) Поменять build context на `.` и сохранить `file: truffles-api/Dockerfile`.
  3) Обновить `STATE.md` (GAP -> DONE) после CI green.
  4) PR + CI.
- DoD:
  - `build-push` job в CI проходит на main.
  - Не затронуты livecheck и runtime/Dockerfile.
- Checks:
  - CI run на PR (build-push success).
- Evidence:
  - CI run URL + build-push job log.
  - Запись в `STATE.md` с evidence.
- Rollback: `git revert HEAD` (или revert merge).
- No-go:
  - Изменения livecheck, Dockerfile, runtime-кода.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-ci-build-push-context-a1`
  - Worktree: создается `scripts/session_start.sh`
  - Base: `origin/main`
  - Merge: PR -> main
  - Cleanup: `scripts/session_end.sh` + remove worktree/branch
- Риски/блокеры: нет.
