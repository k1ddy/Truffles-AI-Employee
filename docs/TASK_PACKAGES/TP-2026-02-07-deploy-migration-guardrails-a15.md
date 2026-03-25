# TP-2026-02-07 Deploy Migration Guardrails (a15)

## Название/цель
Убрать schema drift при деплое: миграции БД должны применяться автоматически и fail-fast до переключения `truffles-api` контейнера, чтобы новые endpoint'ы не падали из-за отсутствующих таблиц.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: incident `console_ops_jobs` table missing after merge/deploy)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md` (§4.2 Release SOP, §4.2.1 Deploy Guardrails)
- `TECH.md` (CI/deploy flow)

## Invariant
- Деплой не должен уводить API в `500` из-за непримененных SQL миграций.
- При ошибке миграции текущий API контейнер остается рабочим (no early stop).
- Контейнерный anti-drift (`REQUIRE_GHCR`, `VERIFY_VERSION`) сохраняется.
- Core webhook/decision pipeline не затрагивается.

## Scope
- Добавить deterministic migration runner для `truffles-api/migrations/*.sql` с tracking в `schema_migrations`.
- Включить migration step в `restart_api.sh` до `docker rm -f truffles-api`.
- Убрать ранний `docker rm -f truffles-api` из CI deploy шага, чтобы не создавать downtime при migration fail.
- Обновить `truffles-api/Dockerfile`, чтобы image содержал `migrations/` и `scripts/`.
- Добавить unit tests для migration runner (discovery/checksum/plan-level contract).
- Обновить docs (`TECH.md`, `SPECS/SYSTEM_REFERENCE.md`) под новый deploy contract.

## Out of scope
- Переход на Alembic/Flyway в этом срезе.
- Любые core-изменения runtime decision pipeline.
- Перенос SRE surface в Console UI.
- Ретро-миграция/cleanup старых ops migration практик.

## Touch-list
- `scripts/restart_api.sh`
- `.github/workflows/ci.yml`
- `truffles-api/Dockerfile`
- `truffles-api/scripts/apply_sql_migrations.py` (new)
- `truffles-api/tests/test_apply_sql_migrations.py` (new)
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Plan
1. Реализовать `apply_sql_migrations.py` (tracking table + checksum guard + ordered apply).
2. Подключить runner в `restart_api.sh` до контейнерного переключения.
3. Обновить CI deploy script: убрать преждевременное удаление API контейнера.
4. Добавить/прогнать target tests для migration runner.
5. Обновить docs о новом release-contract.

## DoD
- `restart_api.sh` по умолчанию запускает миграции и прерывает деплой при ошибке до удаления старого API.
- Deploy из `.github/workflows/ci.yml` не делает `docker rm -f truffles-api` до migration gate.
- API image содержит `migrations` и migration runner script.
- Есть автотест(ы) на migration runner.
- Документация фиксирует новый порядок `migrate -> restart -> deploy-verify`.

## Checks
- `PYTEST_ARGS='/app/tests/test_apply_sql_migrations.py' scripts/test_api_container.sh`
- `python3 -m py_compile truffles-api/scripts/apply_sql_migrations.py`
- `SESSION_AGENT=a15 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- Лог pytest для migration runner
- Лог py_compile
- CI run URL после PR

## Rollback
- Revert commit с migration runner/deploy wiring.
- Временный ручной rollback: применить нужную миграцию `psql -f ...` и перезапустить `restart_api.sh`.

## No-go
- Не трогать webhook/core логику.
- Не добавлять orchestration в `_legacy.py`.
- Не делать destructive git-команды.

## Риски/блокеры
- SQL-файлы с несовместимыми DDL могут требовать отдельной тактики (вне текущего среза).
- Если `.env` не содержит валидный `DATABASE_URL`, migration runner должен падать явно и рано.

## Branch/Worktree
- Branch: `feat/2026-02-07-deploy-migration-guardrails-a15`
- Worktree: `/home/zhan/worktrees/2026-02-07-deploy-migration-guardrails-a15`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P1-10 (`env contract / fail-fast`): migration runner fail-fast при проблемах DSN/DDL.
- P2-12 (`No orchestration in entrypoints`): orchestration остаётся в deploy script, не в API роутерах.
- P2-14 (`PR Task Package gate`): работа ведется только в рамках этого TP.
