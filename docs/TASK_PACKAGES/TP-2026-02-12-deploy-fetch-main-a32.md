# TP-2026-02-12 Deploy Fetch Main Hotfix (a32)

## Название/цель
Исправить падение deploy в CI на шаге SSH deploy из-за permission-denied при `git fetch origin` в runtime repo на VPS.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `TECH.md`
- `docs/SESSIONS/SESSION-2026-02-11-deploy-ephemeral-source-a27.md`
- `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21929854541`

## Invariant
- Deploy продолжает брать код только из `origin/main`.
- Runtime repo на VPS остается `/home/zhan/truffles-main`.
- Release flow (`restart_release.sh`) и image deploy не ослабляются.

## Scope
- Обновить deploy script в `.github/workflows/ci.yml`:
  - убрать hard-fail на `git fetch origin`;
  - ограничить prefetch веткой `main` и сделать его non-blocking.
- Зафиксировать сессию и пакет в `docs/SESSIONS` + `docs/SESSION_INDEX.md`.

## Out of scope
- Изменения API/console runtime кода.
- Изменения бизнес-логики Tenants.
- Изменения production данных или ручные операции на VPS.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-12-deploy-fetch-main-a32.md`
- `docs/SESSIONS/SESSION-2026-02-12-deploy-fetch-main-a32.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Внести точечный hotfix в deploy шаг CI.
2. Прогнать локальные checks для session gate и YAML parse.
3. Закоммитить, запушить ветку, открыть PR.
4. Проверить новый CI run до зелёного deploy.

## DoD
- В workflow больше нет blocking failure из-за stale/permission-broken feature refs в `refs/remotes/origin/*`.
- `scripts/session_check.sh` проходит.
- PR открыт с описанием причины, фикса и expected impact.

## Checks
- `scripts/session_check.sh`
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `git diff -- .github/workflows/ci.yml`

## Evidence
- Failing run URL: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21929854541`
- Ошибка: `cannot update the ref 'refs/remotes/origin/feat/...': ... Permission denied`
- PR URL с hotfix.
- Новый CI run URL после PR.

## Rollback
- Revert commit, который меняет `.github/workflows/ci.yml`.

## No-go
- Не использовать `--no-verify`.
- Не редактировать production refs/permissions вручную как "фикс" CI.
- Не расширять scope за пределы deploy hotfix.

## Риски/блокеры
- Если у runtime repo некорректный `remote.origin.url`, deploy по-прежнему упадет корректно и явно.
