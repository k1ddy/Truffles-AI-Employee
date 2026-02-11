# TP-2026-02-11 Deploy Ephemeral Source (a27)

## Название/цель
Убрать постоянный deploy clone (`/home/zhan/truffles-main-deploy`) из CI, чтобы deploy не загрязнял прод-сервер и не падал на git ownership/safe.directory.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSIONS/SESSION-2026-02-10-deploy-clean-source-a27.md`

## Invariant
- `/home/zhan/truffles-main` остается единственным постоянным runtime-repo на сервере.
- Deploy parity checks (api/console sha) сохраняются.
- Build/push/deploy gate логика в CI не ослабляется.

## Scope
- Обновить deploy script в `.github/workflows/ci.yml`:
  - заменить persistent `DEPLOY_SOURCE_ROOT=/home/zhan/truffles-main-deploy` на ephemeral `mktemp` в `/tmp`;
  - добавить `trap` cleanup для удаления временного каталога.

## Out of scope
- Изменение runtime API/console кода.
- Изменение product UX вкладки Knowledge.
- Массовая чистка существующих серверных директорий вне одноразового remediation.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-11-deploy-ephemeral-source-a27.md`
- `docs/SESSIONS/SESSION-2026-02-11-deploy-ephemeral-source-a27.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Перевести deploy source checkout на ephemeral tmp dir с auto-cleanup.
2. Прогнать YAML parse и локальную проверку diff.
3. Открыть PR и запустить CI для проверки deploy job.
4. После merge выполнить разовый cleanup старого `/home/zhan/truffles-main-deploy`.

## DoD
- В workflow нет жесткой привязки к `/home/zhan/truffles-main-deploy`.
- Deploy script использует временную директорию и удаляет ее на `EXIT`.
- PR открыт, CI run стартовал.

## Checks
- `python3 -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())"`
- `git diff -- .github/workflows/ci.yml`
- `gh pr create ...`

## Evidence
- PR URL
- CI run URL
- `git diff --stat`

## Rollback
- Revert commit с изменением `.github/workflows/ci.yml`.

## No-go
- Не использовать bypass hooks (`--no-verify`).
- Не вносить изменения в runtime сервисы/миграции.

## Риски/блокеры
- Если в репозитории защитные правила требуют дополнительные checks, deploy пройдет после полного CI цикла.
