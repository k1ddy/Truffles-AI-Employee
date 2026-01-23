Title: Console UI wiring for Telegram verify/test (Settings/Ops)
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (NOW/GAP: Console↔Telegram workstream)
- docs/CONSOLE_GUIDE.md (Console↔Telegram map)
- SPECS/ESCALATION.md (Telegram escalation invariants)
- SPECS/ARCHITECTURE.md (Telegram routing/topic_id)
- contracts/console_api/openapi.v1.yaml (contract source of truth)
- contracts/console_api/errors.v1.json (error model)

Invariant:
- Web Console remains source of truth; Telegram is paging/fallback only.
- RBAC/tenant/branch isolation preserved; owner/admin only for connector actions.
- No core webhook/decision pipeline changes.

Scope:
- Wire Console UI to call /console/v1/telegram/verify and /console/v1/telegram/test.
- Add client-level actions and branch-level actions in Settings/Ops.
- Use typed Console API client + error handling.
- Document UI locations in Console Guide.

Out of scope:
- New connectors page or redesign.
- Agent↔Telegram identity linking.
- Notification rules editor.
- Migration wizard legacy telegram_chat_id.
- Backend changes.

Touch-list (files/tables):
- console-web/src/app/settings/page.tsx
- console-web/src/components/OpsPage.tsx
- console-web/src/lib/api-client.ts
- console-web/src/lib/api-hooks.ts
- console-web/src/types/api.generated.ts
- docs/CONSOLE_GUIDE.md
- STRUCTURE.md
- STATE.md

Plan:
1) Add typed telegram API client helpers + hooks with error handling.
2) Add client/branch verify/test actions in Settings/Ops UI.
3) Update docs + record evidence/waiver in STATE.md.

DoD:
- UI can send verify/test for client and branch scope via Console API.
- Errors surfaced via contract error model (toast).
- No Telegram tokens exposed in UI.
- Docs updated with UI locations.

Checks:
- Waiver: no automated UI tests in this slice; relies on contract-typed calls. (Record in STATE.md)

Evidence:
- Local screenshots not required; record local change summary in STATE.md (CI pending).

Rollback:
- Revert UI wiring + API client changes.

No-go:
- Direct Telegram API calls from browser.
- Any changes to core webhook pipeline.

Risks/Blockers:
- Missing 2026-01-17 canon doc (recorded GAP).
- UI test coverage deferred (explicit waiver).

Branch/Worktree:
- Branch: feature/console-telegram-p0
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
