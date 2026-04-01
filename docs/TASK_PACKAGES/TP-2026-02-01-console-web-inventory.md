# Task Package: Web Console inventory (implemented UI + capabilities)

Title/Goal
- Produce a full, implementation-backed map of Web Console UI by role and by page (tabs, buttons, elements), with code/API/data links and system interactions, so future redesigns can avoid drift.

Canon refs
- AGENTS.md
- STATE.md (add GAP: Web Console inventory/audit missing; close with docs)
- STRUCTURE.md
- SPECS/CONTROL_PLANE.md (IA/RBAC reference only; implementation is source of truth here)
- docs/CONSOLE_GUIDE.md
- contracts/console_api/openapi.v1.yaml

Invariant
- Doc-only changes; no runtime/UI/API/DB behavior changes.
- Only implemented features documented; no planned/canon-only items presented as real.
- Tenant selection + RBAC gates remain unchanged.

Scope
- Create docs/CONSOLE_AUDIT/ with index + role docs + page docs.
- Role coverage: platform_admin, owner, admin, manager, support.
- Page coverage: Inbox/Cases, Case detail, Calendar, Knowledge, Team, Settings, Audit, Ops, Tenants, plus global shell/selection gates.
- For each UI element: label, behavior, visibility rules, API endpoint, backend handler, and data sources.
- Document system interactions (Telegram, WhatsApp/outbox, knowledge publish, media) based on implemented code paths.

Out of scope
- Any code changes in console-web or truffles-api.
- Comparing to canon/plans or proposing improvements.
- Runtime verification, screenshots, or tests beyond doc sanity.

Touch-list
- docs/CONSOLE_AUDIT/INDEX.md
- docs/CONSOLE_AUDIT/roles/*.md
- docs/CONSOLE_AUDIT/pages/*.md
- docs/CONSOLE_AUDIT/system/*.md
- STRUCTURE.md
- STATE.md
- docs/SESSIONS/SESSION-2026-02-01-console-web-inventory-a4.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-02-01-console-web-inventory.md

Plan
1) Create audit folder structure + index skeleton.
2) Extract role navigation and selection gates from ConsoleShell + console_auth; fill role docs.
3) Map each page route to UI components; document layout, elements, and actions.
4) Trace each action to API endpoint + backend handler + data sources.
5) Add system interaction notes (Telegram, outbox, knowledge publish, media) with code references.
6) Update STRUCTURE.md + STATE.md (GAP recorded/resolved) and session log.

DoD
- docs/CONSOLE_AUDIT contains index + role docs + page docs with links to code and API.
- Each page doc lists UI elements and actions with endpoint + backend handler + data sources.
- Role docs show exact navigation, access restrictions, and selection gates.
- Content is implementation-backed only; planned items excluded or marked as not present.
- STRUCTURE.md and STATE.md updated with the new audit docs.

Checks
- rg --files docs/CONSOLE_AUDIT

Evidence
- docs/CONSOLE_AUDIT/** files
- STRUCTURE.md update (doc map)
- STATE.md update (GAP resolved)

Rollback
- git revert COMMIT_SHA

No-go
- Any edits to runtime code (console-web, truffles-api) or contracts.
- Introducing non-implemented features as if they exist.
- Changes to RBAC/tenancy behavior.

Branch
- feat/2026-02-01-console-web-inventory-a4

Worktree path
- /home/zhan/worktrees/2026-02-01-console-web-inventory-a4

Base ref
- origin/main

Merge policy
- Doc-only fast-forward to main (no PR); no rebase.

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- UI labels in RU may require non-ASCII for accuracy.
- Some behavior is spread across UI + backend; risk of missing hidden elements.
