# TP-2026-02-12 Console Contract Live Fallback (a32)

## Название/цель
Устранить падение `console-contract-live` в main CI, когда `/console/v1/me` возвращает 401 для токена из Keycloak, но fallback IDs не подхватываются в job env.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `TECH.md`
- `docs/TASK_PACKAGES/TP-2026-02-12-deploy-fetch-main-a32.md`
- CI run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21930218302`

## Invariant
- `console-contract-predeploy` и `console-contract-live` остаются обязательными контрактными проверками после deploy.
- `ci-livecheck` остается независимым и не блокирует этот фикс.
- Основной deploy flow не меняется.

## Scope
- Добавить отсутствующие env fallback secrets в job `console-contract-live`:
  - `SCHEMATHESIS_FALLBACK_CLIENT_ID`
  - `SCHEMATHESIS_FALLBACK_BRANCH_ID`
- Обновить session артефакты для новой ветки.

## Out of scope
- Изменение бизнес-логики API.
- Изменение livecheck-suite и его oracle.
- Ротация/создание секретов в GitHub вручную.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-12-console-contract-live-fallback-a32.md`
- `docs/SESSIONS/SESSION-2026-02-12-console-contract-live-fallback-a32.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Применить точечный patch в `console-contract-live` env.
2. Прогнать `scripts/session_check.sh` и YAML parse.
3. Открыть PR, дождаться зелёного `console-contract-live`.

## DoD
- `console-contract-live` больше не падает из-за пустых fallback env при 401 на `/me`.
- `scripts/session_check.sh` проходит.
- PR открыт и привязан к failing run.

## Checks
- `scripts/session_check.sh`
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `gh pr checks 637` (после открытия PR заменить на актуальный номер)

## Evidence
- failing run URL + failed job/step + error excerpt
- PR URL
- новый CI run URL (где `console-contract-live` green)

## Rollback
- `git revert` commit с этим hotfix в `.github/workflows/ci.yml`.

## No-go
- Не ослаблять `console-contract-live` до skip без причины.
- Не трогать unrelated jobs (`deploy`, `core-eval`, `livecheck`) в этом fix.

## Риски/блокеры
- Если секреты `CONSOLE_SCHEMATHESIS_CLIENT_ID/BRANCH_ID` реально не заданы, step может продолжить фейлиться по существующей guard-логике.
