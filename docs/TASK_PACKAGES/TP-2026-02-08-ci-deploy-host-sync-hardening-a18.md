# TP-2026-02-08 CI Deploy Host-Sync Hardening (a18)

## Название/цель
Убрать ложный "успешный" deploy при отсутствии release-скрипта на прод-хосте: перед deploy синхронизировать repo на хосте, включить строгий shell fail-fast, убрать fallback на неканоничный путь скрипта и добавить явную проверку наличия release-script.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: release governance merged, but deploy incident with missing `/home/zhan/restart_release.sh` fallback)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `TECH.md` (CI/deploy flow)
- `SPECS/SYSTEM_REFERENCE.md` (§4.2 Release SOP, §4.2.1 Deploy Guardrails)

## Invariant
- CI deploy не должен проходить green, если фактический rollout не выполнен.
- Прод релиз использует только канонический `scripts/restart_release.sh` из `/home/zhan/truffles-main`.
- При любой ошибке в remote deploy script job падает (fail-fast).
- Core runtime/webhook behavior не меняется.

## Scope
- Обновить `.github/workflows/ci.yml` deploy step:
  - `set -euo pipefail` в remote script;
  - `git fetch + pull --ff-only` repo на хосте перед deploy;
  - убрать fallback на `/home/zhan/restart_release.sh`;
  - добавить явный `test -f /home/zhan/truffles-main/scripts/restart_release.sh` и hard fail.
- Локально проверить синтаксис workflow и smoke-проверки (targeted).
- Обновить `STATE.md` evidence про инцидент/фикс.

## Out of scope
- Любые изменения release runtime scripts (`restart_release.sh`, `restart_api.sh`, `restart_workers.sh`).
- Изменения бизнес-логики API/Console.
- Перестройка CI pipeline beyond deploy robustness.

## Touch-list
- `.github/workflows/ci.yml`
- `STATE.md`
- `docs/TASK_PACKAGES/TP-2026-02-08-ci-deploy-host-sync-hardening-a18.md`
- `docs/SESSIONS/SESSION-2026-02-08-ci-deploy-host-sync-hardening-a18.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Внести remote deploy hardening в `ci.yml` (host repo sync + strict script).
2. Прогнать локальные checks по workflow diff.
3. Зафиксировать evidence в `STATE.md`.
4. Открыть PR, дождаться CI.

## DoD
- Deploy step не имеет fallback на неканоничный `/home/zhan/restart_release.sh`.
- Deploy step синхронизирует `/home/zhan/truffles-main` перед запуском release script.
- Любая ошибка remote script приводит к fail job.
- `STATE.md` содержит факт и evidence по фиксу.

## Checks
- `python3 -m py_compile scripts/check_migration_governance.py`
- `python3 scripts/check_migration_governance.py --strict`
- `cd truffles-api && pytest -q tests/test_apply_sql_migrations.py`
- `SESSION_AGENT=a18 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- CI run URL после PR
- Логи локальных checks
- Прод proof после deploy (`/admin/version`, container parity)

## Rollback
- Revert PR.

## No-go
- Не менять core/webhook runtime.
- Не добавлять fallback paths для deploy scripts.
- Не использовать destructive git-команды.

## Риски/блокеры
- Если на хосте есть локальные несинхронизированные изменения в `/home/zhan/truffles-main`, `git pull --ff-only` будет падать (это ожидаемая stop-line защита).

## Branch/Worktree
- Branch: `feat/2026-02-08-ci-deploy-host-sync-hardening-a18`
- Worktree: `/home/zhan/worktrees/2026-02-08-ci-deploy-host-sync-hardening-a18`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P1-10 (`env contract / fail-fast`): deploy fail-fast при любой ошибке remote script.
- P2-12 (`No orchestration in entrypoints`): без изменений runtime entrypoints.
- P2-14 (`PR Task Package gate`): фикс строго в рамках TP.
