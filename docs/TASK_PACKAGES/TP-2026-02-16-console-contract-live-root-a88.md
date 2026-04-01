# TP-2026-02-16 Console Contract Live Root Cause Fix (a88)

## Название/цель
Устранить повторный `401` в `console-contract-live` после merge: исправить экспорт переменных в `GITHUB_ENV`, чтобы токен и заголовки селекции (`X-Client-Id`, `X-Branch-Id`) резолвились стабильно.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `TECH.md`
- failing run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/22080707510`

## Invariant
- `console-contract-live` остаётся строгой post-deploy проверкой.
- Не отключаем и не ослабляем auth/selection preflight.
- Изменяем только механизм экспорта env-переменных.

## Scope
- Починить запись env-переменных в `.github/workflows/ci.yml`:
  - `CONSOLE_API_TOKEN`
  - `SCHEMATHESIS_TOKEN`
  - `SCHEMATHESIS_TOKEN_SOURCE`
  - `SCHEMATHESIS_CLIENT_ID`
  - `SCHEMATHESIS_BRANCH_ID`

## Out of scope
- Изменение runtime-кода API/Console.
- Изменение секретов GitHub.
- Изменение матрицы/логики `ci-livecheck`.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-16-console-contract-live-root-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-console-contract-live-root-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Подтвердить root cause по логам failing run.
2. Исправить `\\n` на `\n` в Python-блоках записи в `GITHUB_ENV`.
3. Прогнать локальные проверки валидности workflow и session-gate.
4. Открыть PR и дождаться green `console-contract-live`.

## DoD
- `SCHEMATHESIS_TOKEN_SOURCE` передаётся в следующий шаг, не `unknown`.
- `SCHEMATHESIS_TOKEN` не содержит хвост `\\n...` и проходит `/console/v1/me`.
- `Resolve console selection headers` не падает из-за ошибочного экспорта env.
- `scripts/session_check.sh` проходит.

## Checks
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml') ... PY`
- `rg -n "\\\\n\\\"\\)" .github/workflows/ci.yml` (подтверждение отсутствия `\\n` в export-точках)
- `scripts/session_check.sh`

## Evidence
- failing job log (`console-contract-live`): `token_source=unknown` + `HTTP Error 401` на `/console/v1/me`
- patch в `.github/workflows/ci.yml`
- новый PR + CI run URL

## Rollback
- `git revert HEAD` (или конкретный SHA fix-коммита)

## No-go
- Не переводить job в skip при ошибке auth/selection.
- Не маскировать проблему отключением `Resolve console selection headers`.

## Риски/блокеры
- Если реальные креды/доступ сломаны, job останется красным по правильной причине (не из-за env-export бага).
