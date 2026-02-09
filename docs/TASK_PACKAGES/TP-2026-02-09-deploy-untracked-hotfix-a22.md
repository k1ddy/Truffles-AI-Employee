# TP-2026-02-09-deploy-untracked-hotfix-a22

- Название/цель: Hotfix для CI deploy: устранить падение `git pull --ff-only` на хосте при конфликте с untracked файлами.
- Canon refs: `AGENTS.md`, `STATE.md`, `TECH.md`, `.github/workflows/ci.yml`.

## Invariant
- Deploy остаётся fail-fast для tracked изменений и parity checks.

## Scope
- Только deploy step в `.github/workflows/ci.yml`.
- Добавить безопасную обработку untracked конфликтов перед `git pull --ff-only`.

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
3. Проверить YAML синтаксис.
4. Push + PR.

## DoD
- Deploy step больше не падает на `untracked files would be overwritten by merge`.
- При tracked dirty deploy по-прежнему останавливается.

## Checks
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml')`

## Evidence
- Run URL c ошибкой: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21825629877`.
- Новый PR с diff и CI.

## Rollback
- Revert hotfix commit.

## No-go
- Не использовать `git clean -fd` без таргетинга.
- Не ослаблять parity gate.

## Риски/блокеры
- На хосте могут накапливаться backup-файлы; решается отдельным cleanup runbook.
