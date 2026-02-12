# Web Console — Canon vs Implemented (comparison)

Scope
- Сопоставление канона (Control Plane + Console Guide) с фактической реализацией Web Console.
- Только реализованное поведение; без планов и wish‑листов.

Sources (canon)
- `SPECS/CONTROL_PLANE.md` (roles/RBAC, IA, onboarding, UX standards).
- `docs/CONSOLE_GUIDE.md` (phase contracts, UI/API mapping, tenancy rules).
- `STRATEGY/REQUIREMENTS.md` (жёсткие продуктовые ограничения).

Sources (implemented)
- `docs/CONSOLE_AUDIT/INDEX.md` + `docs/CONSOLE_AUDIT/pages/*` + `docs/CONSOLE_AUDIT/roles/*`.

Legend
- [match] реализовано как в каноне.
- [partial] частично реализовано или отличается по деталям.
- [missing] отсутствует в реализации.
- [ahead] реализовано шире, чем описано в каноне (канон/notes устарели).

---

## 1) Roles & RBAC

### Runtime roles
- [match] Реальные роли в коде: platform_admin/owner/admin/manager/support/specialist/viewer. Canon: `SPECS/CONTROL_PLANE.md` (Runtime roles). Impl: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.

### Platform Admin
- [match] Доступ к Tenants, Ops, Audit, Inbox, Settings/Provisioning, Knowledge, Team, Calendar, Insights. Canon: `SPECS/CONTROL_PLANE.md` (RBAC + IA). Impl: `docs/CONSOLE_AUDIT/roles/platform_admin.md`.
- [match] Integrations registry (nav/страница) реализован для platform_admin. Canon: `SPECS/CONTROL_PLANE.md` (IA: Integrations). Impl: `console-web/src/components/ConsoleShell.tsx`.

### Owner/Admin
- [match] Полный доступ к Inbox/Calendar/Knowledge/Team/Settings/Ops/Audit. Canon: `SPECS/CONTROL_PLANE.md` (RBAC). Impl: `docs/CONSOLE_AUDIT/roles/owner.md`, `docs/CONSOLE_AUDIT/roles/admin.md`.
- [partial] Integrations страница есть в IA, но RBAC ограничен platform_admin (owner/admin без доступа). Canon: `SPECS/CONTROL_PLANE.md` (IA). Impl: `console-web/src/components/ConsoleShell.tsx`, `console-web/src/lib/api-client.ts`.

### Manager
- [match] Inbox + Calendar (read/write). Canon: `SPECS/CONTROL_PLANE.md` (RBAC). Impl: `docs/CONSOLE_AUDIT/roles/manager.md`.
- [partial] Knowledge read-only: реализовано как read, без write. Canon: `SPECS/CONTROL_PLANE.md` (Manager: read‑only Knowledge). Impl: `docs/CONSOLE_AUDIT/pages/knowledge.md`.
- [match] Team directory (read-only). Canon: `SPECS/CONTROL_PLANE.md` (IA: Manager includes Team directory). Impl: `console-web/src/lib/api-client.ts`, `console-web/src/app/team/page.tsx`.

### Support
- [match] Read-only Inbox + Ops + Audit, diagnostics visible. Canon: `SPECS/CONTROL_PLANE.md` (RBAC). Impl: `docs/CONSOLE_AUDIT/roles/support.md`.
- [match] Read-only Provisioning (support). Canon: `SPECS/CONTROL_PLANE.md` (Provisioning read includes support). Impl: `console-web/src/app/settings/page.tsx`.

---

## 2) Tenant context & selection gate

- [match] Context bar (Company/Client/Branch), localStorage keys, selection gate based on `/console/v1/me`. Canon: `docs/CONSOLE_GUIDE.md` (Tenancy rules). Impl: `docs/CONSOLE_AUDIT/pages/global-shell.md`.
- [ahead] Company selection в UI реализован (selector + gate). Canon note: `SPECS/CONTROL_PLANE.md` (Implementation note: company selection отсутствует) — устаревшее. Impl: `docs/CONSOLE_AUDIT/pages/global-shell.md`.
- [match] Fail‑closed: при selection_required UI блокирует контент. Canon: `SPECS/CONTROL_PLANE.md` §3. Impl: `ConsoleShell` gate.

---

## 3) Navigation / IA

- [match] Реализованные пункты навигации: Inbox, Calendar, Knowledge, Team, Settings, Ops, Audit, Insights, Tenants, Integrations. Canon: `SPECS/CONTROL_PLANE.md` IA. Impl: `console-web/src/components/ConsoleShell.tsx`.
- [partial] Integrations доступен только platform_admin (owner/admin не включены в текущий RBAC). Canon: `SPECS/CONTROL_PLANE.md` IA. Impl: `console-web/src/lib/api-client.ts`.
- [match] Insights/Analytics (optional). Canon: `SPECS/CONTROL_PLANE.md` IA. Impl: `console-web/src/app/insights/page.tsx`, `console-web/src/components/ConsoleShell.tsx`.

---

## 4) Pages & flows

### Inbox (Cases)
- [match] 2‑pane default + details toggle (desktop), details drawer on mobile. Canon: `SPECS/CONTROL_PLANE.md` §9.1. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Queue signals: имя/телефон, превью, SLA, tags “Нужно ответить / На связи / Ошибка”. Canon: `SPECS/CONTROL_PLANE.md` §9.2. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Default sort by activity + filters (status/assigned/search/advanced). Canon: `SPECS/CONTROL_PLANE.md` §9.2. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Branch filter только при «All branches». Canon: `SPECS/CONTROL_PLANE.md` §9.2. Impl: `console-web/src/components/CaseList.tsx`.
- [match] Action bar: “Взять/Закрыть/Передать/Эскалировать” (role‑based). Canon: `SPECS/CONTROL_PLANE.md` §9.3. Impl: `console-web/src/components/CaseConversation.tsx`.
- [match] Quick replies/macros + управление в Inbox. Canon: `SPECS/CONTROL_PLANE.md` §9.3. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Context strip (“Суть запроса/Последнее сообщение”). Canon: `SPECS/CONTROL_PLANE.md` §9.3. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Diagnostics tab gated for support/admin/owner/platform_admin. Canon: `SPECS/CONTROL_PLANE.md` §9.5. Impl: `docs/CONSOLE_AUDIT/pages/inbox.md`.
- [match] Consultant tab: assigned/status + first_response/resolve метрики. Canon: `SPECS/CONTROL_PLANE.md` §9.4. Impl: `console-web/src/components/CaseDetailsPanel.tsx`.

### Case deep link
- [match] `/cases/{id}` открывает тот же UX без очереди. Canon: `docs/CONSOLE_GUIDE.md` (Case view). Impl: `docs/CONSOLE_AUDIT/pages/case-detail.md`.

### Calendar
- [match] Специалист → слоты → создать запись. Canon: `SPECS/CONTROL_PLANE.md` §8. Impl: `docs/CONSOLE_AUDIT/pages/calendar.md`.

### Knowledge Studio
- [match] Draft → Validate → Preview → Publish → History → Rollback. Canon: `SPECS/CONTROL_PLANE.md` §7 и `docs/CONSOLE_GUIDE.md` (Phase 3). Impl: `docs/CONSOLE_AUDIT/pages/knowledge.md`.
- [match] Publish gate + warning ack + confirmation for rollback. Canon: `SPECS/CONTROL_PLANE.md` §7 + §5. Impl: `docs/CONSOLE_AUDIT/pages/knowledge.md`.

### Team
- [partial] Users list + roles + Telegram linking есть; отсутствуют invite/disable. Canon: `SPECS/CONTROL_PLANE.md` §8. Impl: `docs/CONSOLE_AUDIT/pages/team.md`.
- [partial] Specialists list есть, но нет управления working_hours/availability. Canon: `SPECS/CONTROL_PLANE.md` §8. Impl: `docs/CONSOLE_AUDIT/pages/team.md`.
- [match] Team directory доступен для manager (read-only). Canon: `SPECS/CONTROL_PLANE.md` IA. Impl: `console-web/src/lib/api-client.ts`, `console-web/src/app/team/page.tsx`.

### Settings + Provisioning Wizard
- [match] Wizard steps и server‑side onboarding flow. Canon: `SPECS/CONTROL_PLANE.md` §5 + `docs/CONSOLE_GUIDE.md` (Phase 2). Impl: `docs/CONSOLE_AUDIT/pages/settings.md`.
- [match] Capabilities tri‑state editor + effective view. Canon: `SPECS/CONTROL_PLANE.md` §6. Impl: `docs/CONSOLE_AUDIT/pages/settings.md`.
- [match] Support read‑only provisioning реализован через `provisioning:read`. Canon: `SPECS/CONTROL_PLANE.md` (Provisioning read includes support). Impl: `console-web/src/app/settings/page.tsx`.

### Ops / Status
- [match] Owner/admin/support видят короткий статус; platform_admin — полный Ops. Canon: `SPECS/CONTROL_PLANE.md` §10. Impl: `console-web/src/components/OpsPage.tsx`.

### Audit
- [match] Read‑only Audit доступен owner/admin/support. Canon: `SPECS/CONTROL_PLANE.md` (RBAC). Impl: `docs/CONSOLE_AUDIT/pages/audit.md`.

### Tenants (platform admin)
- [match] Управление company/client/branch + подтверждения для destructive. Canon: `SPECS/CONTROL_PLANE.md` (Platform Admin scope + safeguards). Impl: `docs/CONSOLE_AUDIT/pages/tenants.md`.

---

## 5) Cross‑cutting safeguards

- [match] Destructive confirmations (branch deactivation, knowledge rollback). Canon: `SPECS/CONTROL_PLANE.md` §5. Impl: `docs/CONSOLE_AUDIT/pages/tenants.md`, `docs/CONSOLE_AUDIT/pages/knowledge.md`.
- [match] Idempotency для console‑мутаций (client‑side idempotency key). Canon: `docs/CONSOLE_GUIDE.md` (Phase 2). Impl: `console-web/src/lib/api.ts`.

---

## 6) GAP summary (canon vs implemented)

- Integrations page реализована, но RBAC уже канона (owner/admin без доступа).
- Team Users не поддерживает invite/disable; Specialists без управления working_hours/availability.
