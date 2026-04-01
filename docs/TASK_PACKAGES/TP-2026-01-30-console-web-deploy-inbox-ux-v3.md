# Task Package: Console web deploy (Inbox UX v3 + build info)

Title/Goal
- Deploy merged console-web changes so Inbox UX v3 and Settings build info appear in prod.

Canon refs
- AGENTS.md
- STATE.md (NOW: Inbox UX implementation done; user still sees no change)
- TECH.md (Console Web deploy)

Invariant
- UI-only deploy; no API/RBAC/DB changes.
- Selection gating remains fail-closed.
- No changes to core pipeline.

Scope
- Sync /home/zhan/truffles-main with origin/main.
- Rebuild/restart console-web with build args for SHA/time (if already wired).
- Verify prod bundles contain Inbox UX v3 labels and Settings build info is non-unknown.
- Record evidence in STATE.md.

Out of scope
- Any new UI/UX changes beyond deploy.
- Backend/contract changes.
- Live-checks or Playwright runs (unless needed).

Touch-list
- docs/SESSIONS/SESSION-2026-01-30-console-web-deploy-inbox-ux-v3-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-console-web-deploy-inbox-ux-v3.md
- STRUCTURE.md
- STATE.md

Plan
1) Commit existing untracked Task Packages + STRUCTURE update (doc-only).
2) Fetch and merge origin/main into main (no rebase).
3) Rebuild/restart console-web.
4) Verify bundles + Settings build info.
5) Update STATE with evidence; close session.

DoD
- Console Settings shows real build SHA/time (not unknown).
- Inbox page bundle includes v3 RU labels (e.g., "Быстрые ответы", "Контекст", "Диагностика").
- console-web container is running after restart.

Checks
- git status -sb
- git fetch --prune
- git merge origin/main
- docker compose -f truffles-api/docker-compose.yml up -d console-web
- docker ps | rg console-web
- curl -s https://console.truffles.kz/inbox | rg -o "/_next/static/chunks/app/inbox/page-[^\"']+\\.js"
- curl -s https://console.truffles.kz/_next/static/chunks/app/inbox/page-*.js | rg "Быстрые ответы|Контекст|Диагностика"
- curl -s https://console.truffles.kz/_next/static/chunks/app/settings/page-*.js | rg "Build:"

Evidence
- /tmp/console_web_inbox_chunk_20260130.txt
- /tmp/console_web_settings_buildinfo_20260130.txt
- STATE.md updated with SHA/time + chunk refs.

Rollback
- git revert <commit> and rebuild/restart console-web.

No-go
- Editing API/DB or core pipeline.
- Rebase or destructive git operations.

Branch
- main

Worktree path
- /home/zhan/truffles-main

Base ref
- origin/main

Merge policy
- Doc-only fast-forward to main (no PR).

Cleanup
- Update session log status to done and run scripts/session_end.sh if needed.

Risks/Blockers
- main is behind origin; merge required.
- console-web rebuild might need env vars present.
