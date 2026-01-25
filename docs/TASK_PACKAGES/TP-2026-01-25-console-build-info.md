Title: Console UI build info + deployment diagnosis (Settings)
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- STATE.md (Phase 2 UI evidence blocked)
- docs/CONSOLE_GUIDE.md (Console UI map)
- SPECS/CONTROL_PLANE.md (Web-first console)
- STRATEGY/REQUIREMENTS.md (quality + evidence)
- TECH.md (console deploy + env)

Invariant:
- No backend/API contract changes.
- Web Console remains source of truth; UI changes are diagnostic-only.
- Fail-closed behavior unchanged.

Scope:
- Diagnose current prod Settings bundle for Provisioning Wizard presence.
- Add build info line in Settings UI (shows build SHA/time from env).
- Wire console-web Docker build args for `NEXT_PUBLIC_BUILD_SHA/TIME`.
- Document build info in Console Guide.

Out of scope:
- Deploying console-web or changing infra/CI.
- Backend/DB changes.

Touch-list (files/tables):
- console-web/src/app/settings/page.tsx
- console-web/Dockerfile
- truffles-api/docker-compose.yml
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-01-25-console-build-info.md
- STRUCTURE.md
- STATE.md

Plan:
1) Verify prod bundle: `curl https://console.truffles.kz/settings` and inspect `/_next/.../settings/page-*.js` for wizard strings.
2) Add Settings build info line (SHA/time) using `NEXT_PUBLIC_BUILD_SHA`/`NEXT_PUBLIC_BUILD_TIME`.
3) Add build args wiring in console-web Dockerfile/compose.
4) Update docs and record evidence in STATE.md.

DoD:
- Settings shows build info line with SHA/time (or "unknown" if missing).
- Docker build args wired for build SHA/time.
- No changes to API behavior or contracts.
- Evidence captured for prod bundle state (wizard missing).

Checks:
- `npm --prefix console-web run lint`

Evidence:
- Curl output for current prod settings bundle (no wizard strings).
- Screenshot/HTML proof of build info once deployed (if available).

Rollback:
- Revert Settings UI change + doc note.

No-go:
- No backend or infra changes in this task.

Risks/Blockers:
- Prod deploy lag keeps wizard hidden until console-web is rebuilt.

Branch/Worktree:
- Branch: feat/console-build-info
- Worktree: /home/zhan/worktrees/console-build-info
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
