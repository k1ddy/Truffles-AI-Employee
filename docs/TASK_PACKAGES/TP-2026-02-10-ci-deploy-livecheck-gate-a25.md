# TP-2026-02-10-ci-deploy-livecheck-gate-a25

- Название/цель: Устранить ложноположительный запуск post-deploy проверок: `console-contract-live` и `ci-livecheck` должны стартовать только при успешном `deploy`.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`, run `21851446052`.

## Invariant
- `deploy_required` path-фильтр и skip-политика остаются без изменений.
- Post-deploy проверки не выполняются на недеплоенном SHA.
- Поведение `build-push` не меняется.

## Scope
- Поправить условия запуска `console-contract-live` и `ci-livecheck` в CI.
- Зафиксировать сессию/индекс и открыть PR.

## Out of scope
- Изменение deploy-скрипта на VPS.
- Чистка/ремедиация server worktree drift.
- Изменение состава livecheck suite/matrix.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-10-ci-deploy-livecheck-gate-a25.md`
- `docs/SESSIONS/SESSION-2026-02-10-ci-deploy-livecheck-gate-a25.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Подтвердить root cause по run `21851446052` (deploy failed, downstream started).
2. Изменить job-level `if` для `console-contract-live` и `ci-livecheck`: добавить `needs.deploy.result == 'success'`.
3. Локально проверить синтаксис workflow и пройти `scripts/session_check.sh`.
4. Commit/push и открыть PR с evidence.

## DoD
- При `deploy=failure` job `console-contract-live` и `ci-livecheck` получают `skipped`.
- При `deploy=success` оба job продолжают запускаться штатно.
- Session gates проходят.

## Checks
- `python3 - <<'PY'\nimport yaml\nfor p in ['.github/workflows/ci.yml']:\n    yaml.safe_load(open(p, 'r', encoding='utf-8'))\nprint('ok')\nPY`
- `scripts/session_check.sh`

## Evidence
- Workflow run `21851446052` + deploy jobs `63058913026` / `63059317749` (падения).
- Diff `.github/workflows/ci.yml`.
- PR URL.

## Rollback
- Revert commit с изменением условий job-level `if` в `.github/workflows/ci.yml`.

## No-go
- Не ослаблять `deploy` gate.
- Не заменять строгий check на `always()`-логики без deploy-result проверки.

## Риски/блокеры
- Возможен `queued`/`cancelled` шум в истории rerun; не влияет на корректность условий запуска.
