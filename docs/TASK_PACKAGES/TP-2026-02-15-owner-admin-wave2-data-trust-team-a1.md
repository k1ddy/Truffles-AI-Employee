# TP-2026-02-15-owner-admin-wave2-data-trust-team-a1

- Название/цель: Расширить owner/admin control layer Wave-2: `Data Trust` (качество данных и доверие к метрикам) и `Team Performance` (скорость и нагрузка менеджеров) с бизнес-ориентированными действиями.
- Canon refs: `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-16), `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`, `docs/REPORTS/2026-02-15-owner-admin-wave1-implementation-v1.md`.

## Invariant
- Не ослаблять RBAC/tenancy gates (`X-Company-Id`, `X-Client-Id`, `X-Branch-Id`, selection gates).
- Не менять billing/ops бизнес-логику; только owner/admin read-model + UX прозрачность.
- Не вводить технический жаргон в owner/admin критичные блоки без бизнес-пояснений.

## Scope
- Backend read-model endpoints:
  - `GET /console/v1/business/data-trust`
  - `GET /console/v1/business/team-performance`
- Frontend pages:
  - `/business/data-trust`
  - `/business/team-performance`
- Дополнить `/business` быстрыми CTA на Wave-2 страницы.
- Обновить docs/backlog и evidence по UX-16.

## Out of scope
- Изменения в канале отправки сообщений и provider remediation.
- Переписывание `insights` или `metrics_daily` pipeline.
- Любые write-операции для owner/admin в новых разделах.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/app/business/page.tsx`
- `console-web/src/app/business/data-trust/page.tsx` (new)
- `console-web/src/app/business/team-performance/page.tsx` (new)
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/api-client.ts`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_AUDIT/*`
- `docs/REPORTS/2026-02-15-owner-admin-wave2-data-trust-team-v1.md` (new)

## Plan
1. Спроектировать response contract и helper-метрики для Data Trust и Team Performance.
2. Добавить backend endpoints + pydantic schemas + RBAC checks.
3. Добавить frontend pages и навигацию/CTA для owner/admin.
4. Обновить OpenAPI и regenerate TS types.
5. Добавить targeted tests и прогнать проверки.
6. Обновить audit/backlog/report + session evidence.

## DoD
- Owner/Admin видит страницы `Data Trust` и `Team Performance` с actionable статусом.
- Новые API endpoints возвращают данные в branch scope и fail-closed при отсутствии доступа.
- Есть deterministic tests для permission/logic branch.
- OpenAPI/check и frontend lint/build проходят.
- UX-16 в backlog обновлён на основании фактического diff.

## Checks
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

## Evidence
- PR #679 updates (API + UI + docs) + test command outputs.
- Updated `docs/CONSOLE_AUDIT/pages/*` + `UX_BACKLOG.md`.
- Wave-2 implementation report with KPI contracts and owner/admin outcomes.

## Rollback
- Revert commits that add Wave-2 routes/pages/types; keep Wave-1 untouched.

## No-go
- No hardcoded tenant/client IDs.
- No role bypass via frontend-only guards.
- No placeholder synthetic metrics presented as factual business KPIs.

## Risks/блокеры
- `console.py` remains large; endpoint additions should stay read-model only and isolated.
- Sparse analytics rows can produce nulls; UX must show explicit `нет данных` instead of implicit zero.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-business-audit-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-business-audit-a1`
- Base ref: `origin/main`
- Merge policy: existing PR update (`#679`) with additional Wave-2 commits.
- Cleanup: Brain/Top Architect after merge.
