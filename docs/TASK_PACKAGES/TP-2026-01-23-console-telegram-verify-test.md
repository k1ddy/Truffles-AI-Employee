Title: Console Telegram connector + branch verify/test + audit events (P0)
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (NOW/GAP: Console↔Telegram Web-first canon doc missing)
- docs/CONSOLE_GUIDE.md (Console↔Telegram map)
- SPECS/ARCHITECTURE.md (Telegram routing/topic_id)
- SPECS/ESCALATION.md (Telegram escalation invariants)
- SPECS/SYSTEM_REFERENCE.md (ops/debug SOP)
- contracts/console_api/openapi.v1.yaml (contract source of truth)
- contracts/console_api/errors.v1.json (error model)

Invariant:
- Web Console remains source of truth; Telegram is paging/fallback only.
- RBAC/tenant/branch isolation preserved; owner/admin only for connector actions.
- No changes to core decision pipeline behavior.

Scope:
- Add Console API endpoints for Telegram verify/test.
- Add audit events for verify/test success/failure.
- Update OpenAPI contract + errors registry if new codes introduced.
- Document endpoints and diagnostics in Console Guide.

Out of scope:
- Agent↔Telegram identity linking.
- Notification rules editor.
- Migration wizard legacy telegram_chat_id.
- Changes to Telegram webhook handling or core escalation logic.

Touch-list (files/tables):
- contracts/console_api/openapi.v1.yaml
- contracts/console_api/errors.v1.json
- truffles-api/app/schemas/console.py
- truffles-api/app/routers/console.py
- truffles-api/app/services/telegram_service.py
- truffles-api/app/services/audit_service.py
- console-web/src/lib/api-client.ts (if new error codes)
- console-web/src/types/api.generated.ts
- truffles-api/tests/test_console_telegram_connector.py
- docs/CONSOLE_GUIDE.md
- STRUCTURE.md
- STATE.md

Plan:
1) Contract-first: define verify/test endpoints + request/response schemas and errors.
2) Implement API endpoints with RBAC + audit events.
3) Add unit tests for helper logic; avoid live Telegram calls.
4) Update Console Guide with new endpoints and troubleshooting.
5) Record evidence in STATE.md.

DoD:
- POST /console/v1/telegram/verify and /console/v1/telegram/test exist in OpenAPI and API.
- Requests use branch chat_id or client fallback; missing config returns contract error.
- Audit events recorded for verify/test (success/failure).
- Tests added and passing locally.
- Docs updated with endpoint usage and diagnostics.

Checks:
- pytest -q truffles-api/tests/test_console_telegram_connector.py

Evidence:
- Local test output (CI pending).
- STATE.md updated with evidence summary.

Rollback:
- Revert API/contract/docs/test changes.

No-go:
- Telegram bot token exposure to frontend.
- Any changes to core webhook pipeline.

Risks/Blockers:
- Missing 2026-01-17 canon doc (recorded GAP).
- Telegram API unavailable during tests (tests must mock).

Branch/Worktree:
- Branch: feature/console-telegram-p0
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
