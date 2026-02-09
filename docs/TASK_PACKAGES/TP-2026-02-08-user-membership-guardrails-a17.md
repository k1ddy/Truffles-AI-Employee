# TP-2026-02-08 User Membership Guardrails (a17)

## Название/цель
Закрыть критичные дыры user-management: запретить некорректные операции с `platform_admin` memberships и устранить fallback, из-за которого agent мог сохранять доступ при отключенных memberships.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: PR-2/PR-2b merged, Team user-management in use)
- `STRUCTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- `platform_admin` остается системной ролью уровня agent, а не membership-toggle.
- Отключение membership должно реально убирать доступ (если membership-модель используется для этого агента).
- Tenant isolation и RBAC не ослабляются.

## Scope
- Backend guardrails в Console admin API:
  - запрет create/update membership с ролью `platform_admin`;
  - запрет mutate memberships для agents с ролью `platform_admin`.
- Auth fix:
  - legacy fallback применяется только к агентам без membership записей вообще;
  - агенты с только inactive memberships не получают legacy-доступ автоматически.
- Минимальные unit tests на новые правила.

## Out of scope
- Полный redesign модели ролей/идентичностей (DEC-level).
- Массовая миграция исторических данных.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_auth_access.py`
- `docs/TASK_PACKAGES/TP-2026-02-08-user-membership-guardrails-a17.md`
- `docs/SESSIONS/SESSION-2026-02-08-user-membership-guardrails-a17.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить runtime guards для membership role/agent role (`platform_admin`).
2. Исправить legacy fallback selection в `get_console_context`.
3. Добавить unit tests на guardrails + fallback behavior.
4. Прогнать targeted pytest + session_check, открыть PR.

## DoD
- API больше не позволяет deactivate/update memberships для `platform_admin` agents.
- API не принимает `platform_admin` как membership role.
- Agent с inactive memberships не получает legacy fallback access.
- Тесты подтверждают правила.

## Checks
- `cd truffles-api && pytest tests/test_console_access_admin_pr2.py -q`
- `cd truffles-api && pytest tests/test_console_auth_access.py -q`
- `SESSION_AGENT=a17 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- pytest outputs
- PR URL

## Rollback
- Revert commit этого PR.

## No-go
- Не ослаблять существующие permission checks.
- Не вносить silent policy changes без тестов.

## Риски/блокеры
- Риск: исторические агенты без memberships должны продолжить работать.
- Митигация: fallback сохраняется только для truly-legacy (без membership rows вообще), покрываем тестом.

## Branch/Worktree
- Branch: `feat/2026-02-08-user-membership-guardrails-a17`
- Worktree: `/home/zhan/worktrees/2026-02-08-user-membership-guardrails-a17`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P2-14 (`PR Task Package gate`): соблюдается через TP + session artifacts.
- P1-8 (`decision_meta required`) и другие core pipeline FF не затрагиваются напрямую.
