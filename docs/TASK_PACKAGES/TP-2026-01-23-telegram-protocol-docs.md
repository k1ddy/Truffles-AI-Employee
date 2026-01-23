Title: Telegram/Console protocol & plan documentation (Web-first)
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (NOW/GAP + evidence ownership)
- SPECS/ESCALATION.md (escalation canon)
- docs/PROCESSES.md (process contracts)
- AGENTS.md (one-issue flow, stop-the-line)

Invariant:
- No behavior change in runtime; documentation-only update.
- Web Console remains the control plane; Telegram is paging/fallback.

Scope:
- Document Web-first Telegram/Console protocol and sync requirements.
- Document target process contracts (take/resolve/return, client notifications).
- Provide a clear execution plan for future sessions/agents.

Out of scope:
- Any code changes, migrations, or UI work.

Touch-list (files/tables):
- SPECS/ESCALATION.md
- docs/PROCESSES.md
- docs/TASK_PACKAGES/TP-2026-01-23-telegram-protocol-docs.md
- STRUCTURE.md
- STATE.md

Plan:
1) Add a canon decision and invariants in SPECS/ESCALATION.md (Web-first + sync).
2) Add target process contracts and execution plan in docs/PROCESSES.md.
3) Register Task Package in STRUCTURE.md and STATE.md.

DoD:
- Protocol is explicit (what must happen on take/resolve/return).
- Sync requirements between Console ↔ Telegram ↔ WhatsApp are documented.
- Implementation plan for next sessions is present and unambiguous.

Checks:
- None (docs-only).

Evidence:
- Git diff + commit.

Rollback:
- Revert the commit.

No-go:
- Introducing new behavior claims without marking as target/plan.

Branch/Worktree:
- Branch: docs/telegram-protocol
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
