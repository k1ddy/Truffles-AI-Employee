# TP-2026-02-08 Release Governance Hardening (a16)

## Название/цель
Закрыть системные причины production drift и ручных ошибок деплоя одним срезом: ужесточить CI/deploy гейты, сделать единый release-оркестратор API+workers по одному image reference и формализовать migration governance без ручных SQL-операций.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: deploy guardrails есть, но были инциденты с old image/no deploy и ручным migration baseline)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md` (качество>скорость, no drift)
- `SPECS/SYSTEM_REFERENCE.md` (§4.2 Release SOP, §4.2.1 Deploy Guardrails)
- `TECH.md` (CI/deploy flow)

## Invariant
- Деплой не должен завершаться "green" без фактического rollout нужного образа.
- API и workers после релиза должны быть на одном и том же image reference.
- Миграционный контур должен fail-fast и не требовать ручных SQL-вставок в проде.
- Core webhook/decision runtime и бизнес-поведение бота не изменяются.

## Scope
- CI workflow hardening:
  - расширить `deploy_required`/`livecheck_required` path filters для migration/release файлов;
  - сделать deploy gate строгим для `main` (если deploy_required=true, silent skip недопустим);
  - запускать livecheck только при фактическом deploy (`deploy.outputs.deployed=true`);
  - не блокировать `build-push`/deploy из-за `core-eval` fail (допустимый риск по текущему процессу).
- Release orchestration:
  - добавить единый скрипт релиза API+workers с parity check;
  - поддержать GHCR digest reference и строгую валидацию image reference в `restart_api.sh`/`restart_workers.sh`.
- Migration governance:
  - добавить детерминированный bootstrap mode в migration runner для legacy DB без ручного SQL;
  - добавить migration lint (naming/duplicate-prefix guard с явными legacy-исключениями);
  - добавить CI шаг migration governance.
- Docs alignment:
  - обновить `TECH.md` и `SPECS/SYSTEM_REFERENCE.md` под новый release contract и migration governance.

## Out of scope
- Переход на Alembic/Flyway/Kubernetes.
- Перенос SRE-поверхности в Console UI.
- Изменения бизнес-логики webhook/decision pipeline.
- Массовое переименование исторических migration-файлов в этом PR.

## Touch-list
- `.github/workflows/ci.yml`
- `scripts/restart_api.sh`
- `scripts/restart_workers.sh`
- `scripts/restart_release.sh` (new)
- `scripts/check_migration_governance.py` (new)
- `truffles-api/scripts/apply_sql_migrations.py`
- `truffles-api/tests/test_apply_sql_migrations.py`
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Plan
1. Добавить migration governance script и расширить migration runner bootstrap режим.
2. Добавить единый `restart_release.sh` и доработать `restart_api.sh`/`restart_workers.sh` под digest + parity.
3. Обновить CI workflow: новые гейты deploy/livecheck + migration governance check + release orchestration.
4. Обновить документацию и прогнать таргетные локальные проверки.

## DoD
- CI не может показать успешный `deploy` на `main`, если deploy_required=true и rollout фактически не выполнен.
- Livecheck выполняется только после подтвержденного deploy.
- Release одним скриптом обновляет API+workers и валидирует parity image reference.
- Migration runner умеет controlled bootstrap legacy state без ручного SQL в БД.
- Migration governance check ловит новые неканоничные migration-файлы.
- Документация отражает новый SOP.

## Checks
- `python3 -m py_compile scripts/check_migration_governance.py truffles-api/scripts/apply_sql_migrations.py`
- `python3 scripts/check_migration_governance.py --strict`
- `cd truffles-api && pytest -q tests/test_apply_sql_migrations.py`
- `bash -n scripts/restart_api.sh scripts/restart_workers.sh scripts/restart_release.sh`
- `SESSION_AGENT=a16 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- Логи проверок из раздела Checks
- CI run URL после PR

## Rollback
- Revert PR целиком.
- Временный fallback: `restart_api.sh` + `restart_workers.sh` по явному image reference при `REQUIRE_GHCR=1`.

## No-go
- Не изменять runtime decision/webhook behavior.
- Не добавлять orchestration в роутеры/`_legacy.py`.
- Не делать destructive git-команды.

## Риски/блокеры
- Migration bootstrap для legacy DB должен быть строго gated, чтобы не маскировать реальный schema drift.
- CI условия не должны ломать workflow_dispatch сценарии и PR-пайплайн.

## Branch/Worktree
- Branch: `feat/2026-02-08-release-governance-hardening-a16`
- Worktree: `/home/zhan/worktrees/2026-02-08-release-governance-hardening-a16`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P1-10 (`env contract / fail-fast`): fail-fast гейты деплоя/миграций.
- P1-11 (`provider adapter contract tests + mock provider`): не затрагивается.
- P2-12 (`No orchestration in entrypoints`): orchestration только в scripts/CI, не в API entrypoints.
- P2-14 (`PR Task Package gate`): работа полностью внутри этого TP.
