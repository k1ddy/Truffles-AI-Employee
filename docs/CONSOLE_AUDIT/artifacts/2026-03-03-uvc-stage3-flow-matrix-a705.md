# UVC Stage 3 Flow Matrix (a705)

Date: `2026-03-03`
Parent TP: `TP-2026-03-03-uvc-ux-stage3-cross-tab-flows-a705.md`

## Goal
Закрыть сквозные loop-переходы между текущими вкладками без dead-end и без дублирующих точек выполнения.

## Canonical Ownership

| Tab | Role | Allowed action class | Not allowed |
|---|---|---|---|
| `Tenants` | orchestration | выбрать приоритет и передать контекст | выполнять provider execute-действия |
| `Integrations` | fact layer | показать факты/следующий шаг и передать контекст | отдельная execute-очередь |
| `Company Workspace` | execute layer | выполнить действие (dry-run/execute) | дублировать оркестрацию или verify-поток |
| `Ops` | verify layer | подтвердить состояние/инцидент и вернуть в loop | запускать конкурирующий execute-поток |

## Loop Contracts

### Loop A: `Tenants -> Workspace -> Ops -> Tenants`
1. Entry: `tenants-action-queue` -> `Открыть Workspace`.
2. Execute: `workspace-recommended-open-execute`.
3. Verify next-step: `workspace-next-step-ops`.
4. Return: `ops-back-tenants`.

Acceptance selectors:
- `tenants-action-queue`
- `workspace-recommended-open-execute`
- `workspace-next-step-ops`
- `ops-back-tenants`

### Loop B: `Integrations -> Workspace -> Tenants`
1. Fact entry: `integrations-row-open-workspace` (branch-scoped).
2. Empty-state return path (when no active recommendation):
- `workspace-return-tenants`
- `workspace-return-integrations`
3. Header CTA requires explicit scope context: `integrations-open-workspace-scope`.

Acceptance selectors:
- `integrations-row-open-workspace`
- `integrations-open-workspace-scope`
- `workspace-empty-next-steps`
- `workspace-return-tenants`
- `workspace-return-integrations`

## Keep / Move / Remove delta

| Item | Decision | Reason |
|---|---|---|
| Integrations row CTA -> Workspace | keep | лучший факт->execute handoff с branch context |
| Integrations header CTA without context | replace | предотвращает переход без контекста |
| Workspace empty state plain text only | replace | добавлен явный return-path |
| Ops standalone status page | keep + augment | добавлен возврат в action loop |

## Evidence pointers
- e2e spec: `console-web/e2e/platform-admin.spec.ts`
- Integrations handoff changes: `console-web/src/app/integrations/page.tsx`
- Workspace next-step and return-path: `console-web/src/app/company-workspace/page.tsx`
- Tenants onboarding loop hint: `console-web/src/app/tenants/tenants-page-view.tsx`
- Ops return-path links: `console-web/src/components/OpsPage.tsx`
