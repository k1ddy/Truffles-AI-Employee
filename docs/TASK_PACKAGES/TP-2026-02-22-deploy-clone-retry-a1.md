# TP-2026-02-22-deploy-clone-retry-a1

- Название/цель: Устранить красный `deploy` в CI из-за флейка `git clone` на VPS (`HTTP/2 stream ... early EOF`) через устойчивый clone/retry механизм без ослабления deploy parity и safety-gates.
- Canon refs: `AGENTS.md`, `STATE.md` (Stop-the-line + CI fail package), `TECH.md` (CI), `.github/workflows/ci.yml`, `docs/TASK_PACKAGES/TP-2026-02-12-deploy-fetch-main-a32.md`.
- CA_ID: N/A.

## Invariant
- Deploy на `main` остается обязательным при `deploy_required=true`.
- Deploy source остается только из `origin/main`.
- `EXPECTED_GIT_COMMIT` parity-check не ослабляется.
- Никаких изменений runtime product logic/marketing.

## Scope
- Только hotfix deploy script в `.github/workflows/ci.yml`:
  - retry `git clone` с backoff;
  - fallback на `git -c http.version=HTTP/1.1 clone` при сетевом/HTTP2 флейке;
  - явная ошибка, если все попытки исчерпаны.

## Out of scope
- Изменение restart scripts (`scripts/restart_*.sh`).
- Изменение deploy secrets/infra конфигурации.
- Любые backend/frontend продуктовые правки.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/SESSIONS/SESSION-2026-02-22-deploy-clone-retry-a1.md`
- `docs/SESSION_INDEX.md`
- `STATE.md` (факт локально + CI run evidence)

## Plan
1. Зафиксировать root-cause из run `22274706720` и failed job `deploy`.
2. Внести минимальный deploy hotfix (retry + HTTP/1.1 fallback).
3. Проверить YAML parse/статический lint workflow.
4. Commit/push/PR.
5. Дождаться CI и зафиксировать результат/evidence.

## DoD
- `deploy` не падает на единичном HTTP2 clone флейке (есть retry/fallback).
- При исчерпании попыток ошибка явная и диагностируемая.
- Остальные deploy guard/parity проверки не изменены.
- CI для PR зелёный минимум по lint/unit/workflow checks.

## Checks
- `python3 - <<'PY'\nimport pathlib, yaml\nyaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())\nprint('YAML_PARSE_OK')\nPY`
- `git diff -- .github/workflows/ci.yml`
- CI run для PR.

## Evidence
- Red run URL: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/22274706720`.
- Failed job/step: `deploy` / `Deploy to VPS`.
- Error lines from log: `RPC failed; curl 92 HTTP/2 stream ...`, `fatal: early EOF`, `fetch-pack: invalid index-pack output`.
- PR URL + CI run URL после фикса.

## Rollback
- Revert commit, меняющий `.github/workflows/ci.yml`.

## No-go
- Не отключать deploy job как обход.
- Не ослаблять parity-check (`api_commit/console_commit`).
- Не добавлять "ignore failure" для clone.

## Риски/блокеры
- Если у VPS нестабильная сеть длительно, deploy может падать даже после retry; тогда нужен infra RCA по каналу VPS->GitHub.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-22-deploy-clone-retry-a1`
- Worktree: `/home/zhan/worktrees/2026-02-22-deploy-clone-retry-a1`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect after merge
