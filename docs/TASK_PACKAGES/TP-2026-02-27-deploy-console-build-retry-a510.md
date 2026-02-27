# TP-2026-02-27-deploy-console-build-retry-a510

## Block identity
- `BLOCK_ID`: n/a
- `PARENT_BLOCK_ID`: n/a
- `DEPENDS_ON`: n/a
- `UNLOCKS`: n/a

## Название/цель
Устранить падение `deploy` после merge в `main`, вызванное флейком DNS/Docker Hub при сборке `console-web`, без ослабления deploy parity/verification.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `TECH.md`
- `.github/workflows/ci.yml`
- `scripts/restart_console_web.sh`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/restart_console_web.sh`
  - deploy step в `.github/workflows/ci.yml` (использует этот скрипт)
- `Baseline commands`:
  - `gh run view 22488503592 --job 65146223446 --log`
  - `rg -n "restart_console_web|VERIFY_CONSOLE_BUILD" .github/workflows/ci.yml scripts/restart_console_web.sh`
- `FACT findings`:
  - deploy fail в шаге `Deploy to VPS` после API deploy/migrations, на `docker compose build console-web`.
  - root error: `failed to resolve source metadata for docker.io/library/node:18-alpine` + `lookup registry-1.docker.io ... server misbehaving`.
  - текущий `scripts/restart_console_web.sh` делает только один build attempt без retry.
- `Detected drift (docs vs code)`: нет, это reliability hardening для transient infra fail.

## One web search (mandatory before implementation)
- **Query (exact):** `docker compose build retry network errors best practices`
- **Date/time (local):** `2026-02-27 19:05, Asia/Almaty`
- **Why this query is precise:** таргетирует именно transient network ошибки при build/pull и практики стабильного деплоя.
- **Sources opened (from this query):**
  - Docker Build checks: `FromAsCasing` (official docs) — https://docs.docker.com/reference/build-checks/from-as-casing/
  - Docker BuildKit configuration (official docs) — https://docs.docker.com/build/buildkit/configure/
- **Existing solutions found:** retry/backoff around image metadata/pull stages и снижение зависимости от единичного сетевого запроса в release path.
- **Decision:** `reuse + integrate` — усилить существующий `restart_console_web.sh` ретраями без изменения deploy contracts.
- **Rejected options:**
  - отключить verify/parity: нарушает deploy safety gates.
  - убрать сборку console-web из deploy полностью: требует отдельной image-distribution программы (вне hotfix scope).
- **Open questions:** нет.

## Root cause (mandatory)
- **Symptom:** deploy job падает при `docker compose build console-web` на transient DNS/Docker Hub ошибке.
- **Minimal reproduction:** CI log run `22488503592`, job `65146223446`, step `Deploy to VPS`.
- **Evidence to capture:** job log lines + script diff + shell syntax check.
- **Five Whys (or equivalent):**
  1. Почему упал deploy? `console-web` build завершился ошибкой резолва base image.
  2. Почему ошибка резолва критична? Скрипт делает один attempt и сразу `exit 1`.
  3. Почему это не компенсируется deploy workflow? retry для clone есть, для console build нет.
  4. Почему это проявилось после merge? transient DNS/registry failure совпал с релизом.
  5. Почему нужно менять код? чтобы transient сетевой сбой не становился deterministic deploy-fail.
- **Root cause statement:** отсутствует retry/backoff механизм в console restart path.
- **Fix mechanism:** добавить детерминированный retry loop для `docker compose build/up console-web` с ограниченным числом попыток и явной диагностикой при исчерпании.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `scripts/restart_console_web.sh`, текущий deploy flow из `.github/workflows/ci.yml`.
- **External reuse:** общие best practices retry/backoff для сетевых операций build/pull.
- **Why not reinvent the wheel:** фиксируем только reliability gap в текущем скрипте; не вводим новую deploy architecture.

## Invariant
- Deploy parity checks (`EXPECTED_GIT_COMMIT`) не ослабляются.
- Проверка `VERIFY_CONSOLE_BUILD` остается обязательной.
- Scope ограничен только deploy/restart reliability.

## Scope
- Изменить `scripts/restart_console_web.sh`: добавить retry/backoff для build/up.
- Зафиксировать evidence в session/TP.

## Out of scope
- Изменение runtime/API логики.
- Изменение CI pipeline структуры (новые jobs/infra).
- Снятие verify checks.

## Touch-list
- `scripts/restart_console_web.sh`
- `docs/TASK_PACKAGES/TP-2026-02-27-deploy-console-build-retry-a510.md`
- `docs/SESSIONS/SESSION-2026-02-27-deploy-console-build-retry-a510.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Добавить retry/backoff параметры в `restart_console_web.sh`.
2. Реализовать loop вокруг `docker compose build` + `docker compose up -d`.
3. Проверить `bash -n` и session gates.
4. Commit/push/PR и приложить run evidence.

## DoD
- Скрипт делает несколько попыток при transient build/up failure.
- При исчерпании попыток ошибка остается явной и fail-closed.
- `VERIFY_CONSOLE_BUILD` и commit parity не изменены.
- Session checks проходят.

## Checks
- `bash -n scripts/restart_console_web.sh`
- `scripts/session_check.sh`
- `git diff -- scripts/restart_console_web.sh`

## Evidence
- CI log: run `22488503592`, job `65146223446`, step `Deploy to VPS`.
- Diff `scripts/restart_console_web.sh`.
- PR URL + CI result.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2`
- **Fail-fast / scenario lock:** только targeted checks (`bash -n`, session gate, CI deploy job evidence).
- **Stop condition:** 2 попытки без нового сигнала -> stop и эскалация на infra RCA.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased via PR -> merge -> next `main` deploy job.
- **Go/no-go signals:** deploy job проходит, `Deploy parity OK`, нет `console-web restart failed after N attempts`.
- **Rollback:** revert hotfix commit in `scripts/restart_console_web.sh`.
- **Post-release monitoring window:** 1-2 deploy cycles на `main`.

## Rollback
- `git revert` коммита с retry loop в `scripts/restart_console_web.sh`.

## No-go
- Не отключать verification шаги.
- Не добавлять silent-success при провале всех попыток.
- Не трогать unrelated deploy/runtime paths.

## Risks/Blockers
- Если VPS DNS системно нестабилен, даже retry может исчерпаться; нужен infra-level RCA.
