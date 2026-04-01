# Universal Control Plane v1 — Phase 2 Slice 2 Analysis (a500)

Date
- 2026-02-22

Goal
- Build FACT map for remaining `/admin/*` role boundaries after Phase 2 slice 1.

Method
- Endpoint inventory:
  - `rg -n '"/admin/' truffles-api/app/routers/console.py`
- Guard map extraction (per-route scan for `require_console_permission` and `_require_platform_admin`).

FACT snapshot
- Platform-admin explicit hard-gate already enforced for:
  - tenant listing/fleet ops (`/admin/companies|clients|branches` list, provider lifecycle, integrations, incidents, weekly snapshots, sensitive access);
  - tenant hierarchy write (`create/update company`, `create/update/archive/restore client`);
  - capabilities write (`PATCH /admin/capabilities`).
- Generic provisioning write (without explicit platform-admin hard-gate) remains for:
  - branch provisioning and branch change workflow:
    - `/admin/branches` (create/update),
    - `/admin/branch-changes/*`,
    - `/admin/branches/{branch_id}/go-live/*`;
  - identity/membership management:
    - `/admin/agents*`,
    - `/admin/memberships*`;
  - onboarding/reference governance:
    - `/admin/onboarding-contract` (GET/PATCH),
    - `/admin/webhook-secret`,
    - `/admin/onboarding/autopilot`,
    - `/admin/onboarding-blueprints`,
    - `/admin/reference-packs*`.
- Marketing endpoints under `/admin/marketing/*` use dedicated guard (`_require_marketing_access`) and are not governed by platform-admin hard-gate.

Risk matrix (for next implementation wave)
- P0 risk: over-tightening branch provisioning could break owner/admin day-to-day operations.
- P0 risk: leaving reference/onboarding governance too broad may allow contract drift outside platform control.
- P1 risk: inconsistent RBAC semantics across `/admin/*` increases operator confusion and audit noise.

Recommended implementation order (Phase 2 slice 2+)
1. Lock governance endpoints to `platform_admin`:
   - `/admin/reference-packs*`,
   - `/admin/onboarding-blueprints`,
   - `/admin/webhook-secret`.
2. Normalize identity endpoints:
   - keep platform-admin-only for cross-tenant/role-escalation operations;
   - preserve explicit deny for platform role assignment by non-platform users.
3. Keep branch provisioning owner/admin-capable but tighten explicit client/branch scope checks and test matrix.
4. Define target contract for onboarding-contract/autopilot (`platform-only` vs `owner/admin within client`) before code change.

GAP
- Final policy decision for `onboarding-contract/autopilot` and `marketing /admin` governance class still needs explicit canonical lock in next slice.

Outputs
- Next TP prepared: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-a500.md`.
