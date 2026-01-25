Title: Console-web build fix (Settings TypeScript error)
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- STATE.md (blocker: console-web build failure)
- SPECS/CONTROL_PLANE.md (Provisioning Wizard UI)
- docs/CONSOLE_GUIDE.md (Settings page)

Invariant:
- No backend/API contract changes.
- Preserve existing Settings UX and Provisioning Wizard logic.
- Fail-closed behavior unchanged.

Scope:
- Fix TypeScript type error in `console-web/src/app/settings/page.tsx`.
- Ensure Docker build (`npm run build`) succeeds for console-web.

Out of scope:
- Deploy console-web.
- Any backend/DB changes.
- UI redesign or behavior changes beyond typing fix.

Touch-list (files/tables):
- console-web/src/app/settings/page.tsx
- console-web/src/types/api.generated.ts (if regen is required)
- docs/CONSOLE_GUIDE.md (if UI/contract changes)
- docs/TASK_PACKAGES/TP-2026-01-25-console-web-build-fix.md
- STATE.md
- STRUCTURE.md

Plan:
1) Reproduce TypeScript error on `npm run build` or Docker build.
2) Fix typings for capabilities providers merge (no behavior change).
3) Re-run lint/build and record evidence.
4) Update STATE.md with evidence.

DoD:
- `npm --prefix console-web run build` passes.
- Provisioning Wizard UI still renders as before.
- Evidence recorded in STATE.md (build output + CI if available).

Checks:
- `npm --prefix console-web install`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

Evidence:
- Build output showing successful compile.
- CI run URL (if merged).

Rollback:
- Revert UI change.

No-go:
- No backend/API changes.

Branch/Worktree:
- Branch: feat/console-web-build-fix
- Worktree: /home/zhan/worktrees/console-web-build-fix
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
