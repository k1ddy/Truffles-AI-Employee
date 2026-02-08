# TP-2026-02-08 Console Contract Gate Hardening (a17)

## Название/цель
Убрать повторяющийся red-main сценарий, когда `console-contract` проверяет live prod API до deploy новых endpoint'ов из merge-коммита, и переводит pipeline в deadlock (`build-push skipped` -> `deploy gate failed`).

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: release governance/deploy gate hardening)
- `STRUCTURE.md`
- `TECH.md` (CI flow)
- `SPECS/SYSTEM_REFERENCE.md` (CI/release SOP)
- CI evidence: run `21794414566` (failed `console-contract` on `GET /admin/memberships` 404 before deploy)

## Invariant
- Контрактные проверки OpenAPI не ослабляются.
- Новые endpoint'ы не должны блокировать deploy на `main` из-за pre-deploy live smoke.
- Live contract smoke остается обязательной проверкой после успешного deploy.
- Бизнес/runtime логика API не меняется.

## Scope
- Разделить `console-contract` на два контура:
  - `pre-deploy` (schema + contract drift/static checks) для PR/main;
  - `post-deploy live` (Schemathesis GET smoke against prod) только после успешного deploy.
- Обновить gating `build-push` на pre-deploy контракт job.
- Добавить явную sequencing-зависимость, чтобы live smoke запускался только при `deploy.outputs.deployed=true`.

## Out of scope
- Изменение endpoint поведения/авторизации.
- Перестройка всей CI архитектуры.
- Staging/preview environment rollout.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-08-console-contract-gate-hardening-a17.md`
- `docs/SESSIONS/SESSION-2026-02-08-console-contract-gate-hardening-a17.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Вынести текущие live Schemathesis шаги в отдельный post-deploy job.
2. Оставить в pre-deploy job только статические контрактные проверки.
3. Переключить `build-push` gate на pre-deploy job.
4. Прогнать локальный workflow syntax sanity-check и session gate.

## DoD
- `main` не падает на pre-deploy 404 для новых endpoint'ов, добавленных в merge.
- `build-push`/`deploy` больше не зависят от pre-deploy live Schemathesis к undeployed API.
- После deploy запускается live `console-contract` smoke и фейлит run при реальной постдеплойной несовместимости.
- PR path сохраняет обязательную статическую валидацию OpenAPI.

## Checks
- `python3 -m py_compile scripts/check_migration_governance.py`
- `python3 scripts/check_migration_governance.py --strict`
- `python3 - <<'PY' ... yaml safe-load .github/workflows/ci.yml ... PY`
- `SESSION_AGENT=a17 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- Логи локальных checks
- CI run URL после PR

## Rollback
- Revert PR целиком (workflow-only rollback).

## No-go
- Не отключать полностью live Schemathesis.
- Не обходить deploy gate через permissive condition.
- Не менять production API код в рамках этого TP.

## Риски/блокеры
- Риск: post-deploy live smoke станет flaky по внешнему auth/network.
- Митигация: оставить auth guard + ограниченный GET smoke + фиксированный timeout/retries, и трактовать fail как post-deploy incident с явным evidence.

## Branch/Worktree
- Branch: `feat/2026-02-08-console-contract-gate-hardening-a17`
- Worktree: `/home/zhan/worktrees/2026-02-08-console-contract-gate-hardening-a17`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P1-10 (`env contract / fail-fast`): сохраняем fail-fast контрактные проверки, но в корректной фазе (post-deploy live).
- P2-14 (`PR Task Package gate`): изменение CI только в рамках Task Package + session artifacts.
