# TP-2026-02-15-owner-admin-wave6-automation-a1

- Название/цель: Wave-6 phase A — перевести owner/admin control-loop к semi-automation, добавить бизнес-цели в Settings для быстрых действий без техсложности и ввести backend preflight-gate для безопасного knowledge publish.
- Canon refs: `STATE.md` NOW (outbox critical), `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`.

## Invariant
- Не ослаблять RBAC (`settings:write`, `knowledge:write`).
- Не менять billing формулу и текущий subscription contract.
- Knowledge publish остаётся branch-scoped и trace/audit-friendly.

## Scope
- Automation:
  - добавить orchestration script `ops/owner_admin_control_loop.py` для `t0`/`t24` контуров (snapshot + compare + optional gate).
- Owner UX:
  - добавить в `Settings` понятный goal-mode блок (цели бизнеса -> автоматический SLA профиль).
- Knowledge safety:
  - enforce backend preflight for publish: publish требует свежий validate event для того же draft hash (с управляемым override флагом).

## Out of scope
- Полный fleet scheduler/cron deployment на проде.
- Полный redesign Knowledge Studio.
- Изменение core routing/LLM behavior.

## Touch-list
- `ops/owner_admin_control_loop.py` (new)
- `console-web/src/app/settings/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_knowledge_preflight.py` (new)
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_knowledge_preflight.py` (new)
- `contracts/console_api/openapi.v1.yaml`
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave6-automation-v1.md` (new)
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-wave6-automation-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Создать session/worktree для wave6.
2. Реализовать control-loop orchestration script с t0/t24 режимами.
3. Добавить goal-mode section в Settings (quick apply business goals).
4. Внедрить knowledge publish preflight gate (hash + recent validate evidence).
5. Обновить контракты/тесты/доки и собрать evidence.

## DoD
- Есть runnable script для owner/admin control-loop orchestration.
- В Settings есть goal-mode block с быстрым применением целей.
- Publish без свежего preflight blockируется корректной ошибкой, с override работает.
- Добавлены/обновлены тесты и все checks green.

## Checks
- `python3 -m py_compile ops/owner_admin_control_loop.py truffles-api/app/services/console_knowledge_preflight.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_knowledge_preflight.py truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_knowledge_preflight.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_knowledge_preflight.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- `/tmp/owner_admin_wave6_t0.json`
- `/tmp/owner_admin_wave6_t24.json` (when available)
- `/tmp/owner_admin_wave6_control_loop_t0.log`
- `/tmp/owner_admin_wave6_control_loop_t24.log`
- PR diff + report.

## Rollback
- Revert wave6 commit(s); fallback to wave5 behavior (manual loop + no preflight enforcement).

## No-go
- Нельзя обходить preflight через silent backend default.
- Нельзя превращать goal-mode в новый сложный wizard.
- Нельзя ломать существующие owner/admin smoke surfaces.

## Risks/блокеры
- Existing UI may depend on direct publish; preflight gate needs compatibility path.
- Prod runtime backlog still critical; automation does not replace remediation capacity.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-wave6-automation-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-wave6-automation-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main` after green checks.
- Cleanup: Brain/Top Architect after merge.
