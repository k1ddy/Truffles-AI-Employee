# TP-2026-02-10-ci-merge-skip-core-eval-a23

- Название/цель: Исправить CI merge-поведение: не запускать дублирующий `core-eval` после merge PR с уже green `core-eval`, и сделать причину skipped deploy/build прозрачной.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`.

## Invariant
- PR quality gates не ослабляются.
- `core-eval` обязан выполняться для PR и для push, которые не являются merge-коммитом green PR.
- Deploy/build не запускаются без `deploy_required=true`.

## Scope
- Только `.github/workflows/ci.yml`.
- Только логика `changes` outputs + `core-eval` condition + summary/диагностика skipped.

## Out of scope
- Runtime API/Console код.
- Изменения deploy фильтра по бизнес-логике (что именно считается deploy-required).

## Touch-list
- `.github/workflows/ci.yml`
- `docs/SESSIONS/SESSION-2026-02-10-ci-merge-skip-core-eval-a23.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать факт по run `21845489527` (outputs и реальные условия).
2. Переписать gate в детерминированный `run_core_eval` output (`true|false`) без двусмысленных сравнений.
3. Добавить явный debug summary для `deploy_required`/`core_eval` решений.
4. Прогнать session check + YAML parse + dry-run логики на merge commit.
5. Push + PR.

## DoD
- В merge run с green PR `core-eval` имеет `skipped`.
- В run summary видна причина почему `build-push/deploy` skipped.
- CI workflow валиден и не ломает текущие required checks.

## Checks
- `./scripts/session_check.sh`
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml')`
- Локальная dry-проверка merge-gate (GitHub API check-runs).

## Evidence
- Problem run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21845489527`
- PR с diff и успешным CI.

## Rollback
- Revert commit с изменением workflow.

## No-go
- Не отключать `core-eval` глобально.
- Не запускать deploy/build принудительно на workflow-only изменениях без отдельного решения.

## Риски/блокеры
- Ограничения GitHub expression/типов могут приводить к ложной оценке условий; обходим через явный output `run_core_eval`.
