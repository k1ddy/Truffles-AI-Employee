# TP-2026-02-09-deploy-untracked-hotfix-a22

- Название/цель: Hotfix для CI deploy + anti-repeat `core-eval` на merge: устранить падение `git pull --ff-only` на хосте и не дублировать `core-eval`, если PR уже прошёл его успешно.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`.

## Invariant
- Deploy остаётся fail-fast для tracked изменений и parity checks.
- `core-eval` не пропускается для PR и прямых push, но не дублируется на merge в `main`, если PR check уже `success`.

## Scope
- Deploy step в `.github/workflows/ci.yml`.
- Добавить безопасную обработку untracked конфликтов перед `git pull --ff-only`.
- Добавить merge-gate для `core-eval`: на push в `main` после merge PR пропускать `core-eval`, если у PR head SHA есть `core-eval=success`.

## Out of scope
- Изменения runtime API/Console.
- Изменения livecheck/contract сценариев.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/SESSIONS/SESSION-2026-02-09-deploy-untracked-hotfix-a22.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Воспроизвести причину падения по логам CI.
2. Добавить pre-pull guard: fail на tracked dirty, move conflicting untracked to backup dir.
3. Разобрать причину `build-push/deploy skipped` на merge run через `changes` outputs.
4. Добавить merge-gate `core-eval` с проверкой статуса check-run на PR head SHA.
5. Проверить YAML синтаксис.
6. Push + PR.

## DoD
- Deploy step больше не падает на `untracked files would be overwritten by merge`.
- При tracked dirty deploy по-прежнему останавливается.
- На merge commit в `main` job `core-eval` помечается `skipped`, если в соответствующем PR `core-eval` уже был `success`.

## Checks
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml')`

## Evidence
- Run URL c ошибкой: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21825629877`.
- Run URL со `skipped` deploy/build: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21827059129`.
- Новый PR с diff и CI.

## Rollback
- Revert hotfix commit.

## No-go
- Не использовать `git clean -fd` без таргетинга.
- Не ослаблять parity gate.

## Риски/блокеры
- На хосте могут накапливаться backup-файлы; решается отдельным cleanup runbook.
