Название/цель:
- Platform Admin UX Wave 1-4: закрыть P0 incident visibility, снизить error-friction в provisioning, завершить унификацию context storage и начать декомпозицию tenants без изменения backend-контрактов.

Canon refs:
- AGENTS.md (Task Package + one-issue flow + stop-the-line)
- STATE.md NOW + docs/CONSOLE_AUDIT/UX_BACKLOG.md (UX-08, UX-09, UX-10, UX-11)
- docs/REPORTS/2026-02-15-platform-admin-baseline-v1.md

Invariant:
- Не менять backend API contracts и RBAC semantics.
- Не ухудшить tenant isolation и selection gate behavior.
- Не ломать существующие platform_admin сценарии (`integrations`, `company-workspace`, `tenants`, `settings`).

Scope:
- `console-web` Platform Admin UX: incident runbook surface, persistent inline errors in provisioning, context storage finalization, initial tenants decomposition.

Out of scope:
- Новые backend endpoints.
- Полная декомпозиция всех больших страниц.
- Изменение бизнес-политик и workflow state-машин.

Touch-list (files/tables):
- console-web/src/components/ConsoleShell.tsx
- console-web/src/components/ProvisioningWizard.tsx
- console-web/src/app/tenants/page.tsx
- console-web/src/lib/console-context-storage.ts
- console-web/src/lib/use-console-context-scope.ts
- console-web/src/lib/use-inline-error-summary.ts
- console-web/src/lib/api.ts
- console-web/src/app/integrations/page.tsx
- console-web/src/app/company-workspace/page.tsx
- console-web/src/app/settings/page.tsx (if needed for provisioning wiring)
- docs/SESSIONS/SESSION-2026-02-15-platform-admin-wave14-a1.md
- docs/SESSION_INDEX.md

Plan (1..N):
1) Усилить `ConsoleShell` incident banner до runbook-секции с severity/age/CTA и telemetry marks.
2) Внедрить persistent inline error summary в критические provisioning-потоки вместо toast-only.
3) Добить унификацию context storage: убрать прямые обращения к localStorage на целевых страницах.
4) Начать декомпозицию `tenants`: выделить высоко-изменяемый UI-блок в отдельный модуль без изменения поведения.
5) Прогнать lint/build + целевые e2e и подготовить evidence в PR.

DoD:
- При деградированном health Platform Admin видит инцидентный блок с actionable CTA в shell.
- В provisioning есть видимый persistent error summary минимум в основных мутационных потоках.
- На целевых страницах нет прямого дублирования context key logic; используется shared module.
- `tenants/page.tsx` сокращён за счёт вынесения как минимум одного самостоятельного блока.
- `npm --prefix console-web run lint` и `npm --prefix console-web run build` проходят.

Checks:
- npm --prefix console-web run lint
- npm --prefix console-web run build
- targeted Playwright checks for incident/error/context surfaces

Evidence:
- PR URL + commit SHA
- вывод lint/build
- targeted e2e output
- diff stat по изменённым platform_admin файлам
- STATE.md update by Brain/Top Architect if required after merge

Rollback:
- Revert PR merge commit.

No-go:
- Не вводить временные hardcode-пороги без объяснимой логики в коде.
- Не добавлять новые localStorage keys вне shared context module.
- Не менять API payload contracts для backend.

Риски/блокеры:
- Высокая связность `ProvisioningWizard` и `tenants` может вызвать регрессии UI state.
- Требуется аккуратная проверка на mobile layout после декомпозиции.

Branch / Worktree / Base / Merge / Cleanup:
- Branch: feat/2026-02-15-platform-admin-wave14-a1
- Worktree: /home/zhan/worktrees/2026-02-15-platform-admin-wave14-a1
- Base ref: origin/main
- Merge policy: squash or merge commit via PR after green CI
- Cleanup: удалить branch/worktree после merge (Brain/Top Architect)
