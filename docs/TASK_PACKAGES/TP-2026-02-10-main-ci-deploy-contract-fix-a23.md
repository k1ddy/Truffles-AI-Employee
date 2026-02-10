# TP-2026-02-10-main-ci-deploy-contract-fix-a23

- Название/цель: Убрать красный main CI после merge #604: исправить deploy parity-check чтение `console_commit` и синхронизировать OpenAPI контракт `fleet/attention limit` с runtime-ограничением.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`, `contracts/console_api/openapi.v1.yaml`, run `21848964722`.

## Invariant
- Merge skip-логика `core-eval` не меняется.
- Deploy parity-check остается fail-closed при реальном mismatch.
- Runtime поведение `fleet/attention` (limit 1..100) не ослабляется.

## Scope
- Точечный фикс quoting в deploy шаге CI.
- Точечная фиксация `minimum/maximum` для query `limit` в console OpenAPI.
- Session artifacts.

## Out of scope
- Изменение runtime бизнес-логики attention scoring.
- Изменение livecheck сценариев.
- Широкий рефактор CI.

## Touch-list
- `.github/workflows/ci.yml`
- `contracts/console_api/openapi.v1.yaml`
- `docs/TASK_PACKAGES/TP-2026-02-10-main-ci-deploy-contract-fix-a23.md`
- `docs/SESSIONS/SESSION-2026-02-10-main-ci-deploy-contract-fix-a23.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Подтвердить root cause из job logs (`deploy`, `console-contract-live`).
2. Исправить `console_commit` shell-команду в deploy parity-check.
3. Добавить `minimum=1`, `maximum=100` для `fleet/attention limit` в OpenAPI.
4. Прогнать локальные проверки (YAML parse + session check + targeted contract sanity).
5. Push и открыть PR.

## DoD
- Больше нет deploy fail из-за лишних кавычек в `console_commit`.
- Schemathesis не валится на `limit > 100` для `fleet/attention` как schema mismatch.
- Session gates проходят.

## Checks
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml')`
- `python3 - <<'PY' ... yaml.safe_load('contracts/console_api/openapi.v1.yaml')`
- `./scripts/session_check.sh`

## Evidence
- Main run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21848964722`
- Deploy job: `63051317397` (`console build sha=""...""` mismatch)
- Console contract live job: `63051539007` (`limit=1088` -> 400)

## Rollback
- Revert commit с изменениями `ci.yml` и `openapi.v1.yaml`.

## No-go
- Не отключать deploy parity-check.
- Не исключать `fleet/attention` из contract-live smoke.

## Риски/блокеры
- Возможны независимые flake в livecheck pools; не блокируют данный hotfix.
