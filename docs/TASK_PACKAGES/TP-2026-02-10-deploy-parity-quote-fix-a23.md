# TP-2026-02-10-deploy-parity-quote-fix-a23

- Название/цель: Исправить падение deploy в main CI (`actions/runs/21848271351`) из-за синтаксической ошибки в parity-check, не меняя продуктовую логику деплоя.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`, run `21848271351`.

## Invariant
- Merge-run с green PR по `core-eval` остается `skipped` (без регресса #602).
- Deploy gate остается fail-closed: при реальном mismatch parity должен падать.
- Build/deploy orchestration не ослабляется.

## Scope
- Точечная правка shell/python quoting в deploy parity-check шаге CI.
- Обновление session artifacts под новый фикс.

## Out of scope
- Изменение бизнес-правил `deploy_required`.
- Изменение runtime API/console кода.
- Переработка livecheck/console-contract стратегии.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-10-deploy-parity-quote-fix-a23.md`
- `docs/SESSIONS/SESSION-2026-02-10-deploy-parity-quote-fix-a23.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Подтвердить root cause по deploy job log (`63049260962`).
2. Исправить команду получения `api_commit` в deploy step.
3. Локально провалидировать YAML и отсутствие синтаксического дефекта в inline-команде.
4. Прогнать `scripts/session_check.sh`, закоммитить, открыть PR.

## DoD
- Deploy шаг больше не падает на `SyntaxError` в python `-c`.
- CI workflow остается валидным.
- Session gates проходят.

## Checks
- `python3 - <<'PY'` + `yaml.safe_load('.github/workflows/ci.yml')`
- `rg`/manual inspection строки parity-check
- `./scripts/session_check.sh`

## Evidence
- Fail run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21848271351`
- Fail job: `deploy` (`63049260962`) error: `SyntaxError` в `python3 -c` parity-check.
- PR с фиксом и green checks.

## Rollback
- Revert commit с правкой `.github/workflows/ci.yml`.

## No-go
- Не отключать parity-check.
- Не менять критерий успешного deploy.

## Риски/блокеры
- Возможен отдельный независимый fail в `console-contract-live` (контракт/схема), не должен блокировать этот hotfix.
