Title: Console↔Telegram P0 contract alignment (health/trail/branch fields)
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (NOW/GAP: Console↔Telegram contract mismatch; missing 2026-01-17 doc -> GAP if unresolved)
- docs/CONSOLE_GUIDE.md (Console data flow + endpoints)
- SPECS/ARCHITECTURE.md (Telegram routing + topic_id + handover fields)
- SPECS/ESCALATION.md (Telegram escalation invariants)
- SPECS/SYSTEM_REFERENCE.md (ops/debug SOP)
- contracts/console_api/openapi.v1.yaml (contract source of truth)

Invariant:
- Web Console remains source of truth; Telegram stays paging/fallback only.
- No changes to core decision pipeline behavior.
- RBAC/tenant isolation is preserved (client/branch scope enforced).
- Idempotency and audit remain intact for console mutations.

Scope:
- Add Console API contract + schema for telegram health, telegram trail in case detail, and branch telegram_chat_id/instance_id.
- Implement Console API endpoint /console/v1/telegram/health.
- Implement telegram_trail mapping in case detail (optional in list).
- Update Console UI/types to match the contract (no new UI flows yet).
- Document “where what lives” and diagnostics in docs/CONSOLE_GUIDE.md.

Out of scope:
- Connector verification/test/migration wizard flows.
- Agent↔Telegram identity linking.
- Notification rules editor.
- Any changes to Telegram webhook handling or core escalation logic.

Touch-list (files/tables):
- contracts/console_api/openapi.v1.yaml
- truffles-api/app/schemas/console.py
- truffles-api/app/routers/console.py
- truffles-api/app/services/telegram_service.py (health helper)
- console-web/src/components/OpsPage.tsx
- console-web/src/components/CaseView.tsx
- console-web/src/app/settings/page.tsx
- console-web/src/types/api.generated.ts
- truffles-api/tests/test_console_telegram_helpers.py
- docs/CONSOLE_GUIDE.md
- STRUCTURE.md
- STATE.md

Plan:
1) Update docs/CONSOLE_GUIDE.md with Console↔Telegram map + diagnostics (add GAP note if 2026-01-17 doc not found).
2) Update Console API contract (OpenAPI) for Telegram health/trail + branch fields.
3) Implement API schema/endpoint + mapping in console.py.
4) Update UI/types to match contract (regenerate OpenAPI types if possible).
5) Add unit test(s) for telegram link/trail helper; run checks.
6) Record evidence + update STATE.md.

DoD:
- /console/v1/telegram/health is defined in OpenAPI and implemented in console API.
- Case detail returns telegram_trail with message_id/topic_id (and optional link).
- Branch entries include telegram_chat_id and instance_id.
- UI does not error on OpsPage/CaseView/Settings due to missing fields.
- Docs updated with locations and diagnostics steps.
- At least one test added and passing; evidence recorded in STATE.md.

Checks:
- pytest -q truffles-api/tests/test_console_telegram_helpers.py
- (optional) npm --prefix console-web run generate:api

Evidence:
- Test output + OpenAPI diff summary.
- If CI used: CI run URL (recorded by Brain/Top Architect).
- Update STATE.md with what changed and references.

Rollback:
- Revert contract/schema/API/UI changes; restore previous OpenAPI and console schema.

No-go:
- Changes to core webhook/decision pipeline.
- Adding logic to webhook entrypoints/_legacy.py.
- Any direct Telegram token exposure to frontend.

Risks/Blockers:
- Missing 2026-01-17 canon doc (record as GAP if not found).
- Telegram health metrics limited by available DB signals (documented fallback).

Branch/Worktree:
- Branch: feature/console-telegram-p0
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
