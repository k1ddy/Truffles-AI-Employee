# Control Plane Review — UX, RBAC, Safety, Scale

**Date:** 2026-01-27  
**Scope:** Console UX + IA, tenant selection, RBAC, safety gates, performance, and test harness.  
**Sources:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`, `STATE.md`, current code.

---

## 1) Current state (code-backed)

**Implemented and working (in code):**
- Company → Client → Branch selection with gates (`/console/v1/me`, `X-Company-Id`, `X-Client-Id`, `X-Branch-Id`).
- Server-side onboarding state machine (`/onboarding/status`, `/onboarding/advance`).
- Destructive safeguards (confirmations) for rollback / branch deactivate.
- 3-pane Inbox UI, Knowledge Studio UI, Provisioning Wizard.

**Automated checks executed (local):**
- `pytest -q truffles-api/tests/test_console_*` → **69 passed** (warnings on `datetime.utcnow`).
- Playwright smoke (live): `PLAYWRIGHT_BASE_URL=https://console.truffles.kz` → **13 passed**.
- Schemathesis GET-only contract → **FAILED** (multiple 404s for console endpoints; see failures in command output). This indicates a prod contract mismatch or routing/token issue and must be investigated.

---

## 2) UX problems observed (user feedback + code review)

1) **Company/Client/Branch selection is unclear and feels slow.**
   - No strong feedback that context was applied; gating feels like a blocking error instead of a guided step.
   - Latency gives impression of instability.

2) **Duplicate Branch filters in Cases.**
   - Global context already selects branch; extra branch filter adds confusion.

3) **Knowledge page keeps showing `Branch Selection Required`.**
   - No dedicated UX for required branch selection inside Knowledge.

4) **Knowledge Validate returns `Failed to reach API`.**
   - Likely missing branch context or proxy error; current error message is too generic.

5) **Inbox is noisy and hard to scan.**
   - Search controls dominate; trace/explain feels technical and not helpful to operators.
   - 3-pane layout is not intuitive without clear hierarchy and scrolling.
   - Mixed RU/EN strings and technical errors visible to end users.

---

## 3) Target UX / IA (how it should work)

### 3.1 Global context bar (Company/Client/Branch)
- **Always visible** and **single source of truth** for scope.
- **Guided selection:** If selection is required, show a clear CTA (“Select company/client/branch to continue”).
- **Immediate feedback:** After selection, show a brief “Context applied” toast and a visible loading state.
- **Auto-apply with progress** (no silent delays). Optionally add an explicit “Apply” button for slower orgs.
- **Branch = All** only for owner/admin. For branch-scoped roles, hide branch selector completely.

### 3.2 Cases (Inbox)
- **Remove the redundant branch filter** from Cases by default.
- If `branch = All`, move branch filter into **Advanced Filters** (collapsed by default).
- Make list column scroll independent (sticky search bar, list scrolls only).
- Reduce cognitive noise: **Diagnostics (Trace/Explain)** hidden by default; move to a separate “Diagnostics” tab.

### 3.3 Knowledge
- **Branch is mandatory** (Knowledge is branch-specific), but UX must be explicit:
  - If `branch_selection_required=true`, show a clean inline selector instead of an error.
  - Remember last used branch for Knowledge (`console:knowledge_branch_id`) to minimize friction.
- **Validate error** must map to clear causes:
  - Missing branch → show “Select branch to validate”.
  - API down → show “API unavailable, try again” with retry.

### 3.4 Localization
- All end-user UI text must be RU (operators), technical texts only in Diagnostics or admin-only views.

---

## 4) RBAC (clear separation)

**Runtime roles:** owner, admin, manager, support (as implemented).  
**Target (future):** platform admin/support, specialist/viewer.

**Matrix (target, enforce at API + UI):**

| Section | Read | Write | Notes |
|---|---|---|---|
| Inbox | owner/admin/manager/support | owner/admin/manager | support read-only |
| Knowledge | owner/admin/manager | owner/admin | manager read-only |
| Team | owner/admin | owner/admin | hide from manager/support |
| Calendar | owner/admin/manager | owner/admin/manager | manager branch-scoped |
| Settings | owner/admin | owner/admin | hide from manager/support |
| Ops | owner/admin/support | owner/admin | support read-only |
| Audit | owner/admin/support | — | support read-only |
| Provisioning | owner/admin/support (read) | owner/admin | support read-only |

**Must be enforced** at API (fail-closed) and mirrored in UI (navigation + CTA gating).

---

## 5) Safety & Scalability

**Safety (already in place, refine UX):**
- Server-side onboarding state machine blocks out-of-order actions.
- Destructive actions require confirmations with reason + TTL.

**Scalability:**
- Avoid refetch storms on context change: use `react-query` caching with `staleTime`, prefetch on selection.
- Use explicit “context applied” state to prevent repeated re-renders.
- Cases list should be paginated and virtualized when large.

---

## 6) Implementation plan (phased)

**Phase UX-1 (context clarity & gating)**
- Add guided selection overlays and “context applied” feedback.
- Remove branch filter from Cases or move to Advanced Filters.
- Knowledge page: inline branch selector instead of error.

**Phase UX-2 (Inbox usability)**
- Sticky search bar, list-only scroll, compact filters.
- Hide Diagnostics by default; add explicit “Diagnostics” tab.
- RU translations for end-user surface.

**Phase UX-3 (Performance & stability)**
- Prefetch after context selection; reduce full-page refetches.
- Add loading skeletons for list/details.

**Phase QA-1 (test harness improvements)**
- Fix Schemathesis 404 (routing/token/tenant) and stabilize contract checks.
- Add e2e cases for context selection flow + Knowledge gating.

---

## 7) Automated testing (how to see current state)

**API unit:**
```
pytest -q truffles-api/tests/test_console_*
```

**Contract (Schemathesis):**
```
set -a
source /home/zhan/secrets/console-contract.env
set +a
/home/zhan/.venv-schemathesis/bin/schemathesis --config-file contracts/console_api/schemathesis.toml \
  run contracts/console_api/openapi.v1.yaml \
  --url https://api.truffles.kz/console/v1 \
  --include-method=GET \
  --exclude-path /ops/outbox \
  --exclude-path /admin/capabilities \
  --exclude-path /onboarding/status \
  --exclude-path /onboarding/advance \
  --checks all \
  --request-timeout 10 \
  --max-examples=3 \
  --header "Authorization: Bearer ${CONSOLE_API_TOKEN}"
```

**UI e2e (live):**
```
set -a
source /home/zhan/secrets/console-e2e.env
set +a
export PLAYWRIGHT_BASE_URL=https://console.truffles.kz
export PLAYWRIGHT_WEB_SERVER=0
export E2E_USE_STORAGE_STATE=1
npm --prefix console-web run test:e2e:smoke
```

---

## 8) Risks
- Schemathesis failures indicate prod contract mismatch or routing/auth issues → blocks reliable API validation.
- Context selection UX remains confusing if not centralized; reduces operator trust.
- Knowledge branch selection friction will continue without explicit selector UX.

---

## 9) Decision needed
- Remove branch filter from Cases or move to Advanced Filters?
- Knowledge: default to last used branch or require explicit selection each time?
- RU localization scope (all user-facing vs admin/diagnostics only)?
