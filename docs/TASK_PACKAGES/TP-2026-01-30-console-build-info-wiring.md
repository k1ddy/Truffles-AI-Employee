# Task Package: Console build info wiring (Settings)

Title/Goal
- Ensure Settings shows real build SHA/time instead of `unknown` by wiring build args into the console-web build/deploy pipeline.

Canon refs
- AGENTS.md
- STATE.md (NOW: console build info exists; runtime shows unknown)
- TECH.md (deploy/CI references)

Invariant
- No API/RBAC/DB changes.
- No behavior changes outside Settings build info.

Scope
- Wire `NEXT_PUBLIC_BUILD_SHA` + `NEXT_PUBLIC_BUILD_TIME` into console-web build.
- Update related deploy scripts/workflows if needed.
- Add evidence of non-unknown build info in bundle or runtime.

Out of scope
- Any other console UX changes.
- Backend or contract changes.

Touch-list
- console-web/Dockerfile
- docker-compose.console.yml (if used for deploy)
- .github/workflows/ci.yml (if console-web build happens here)
- docs/SESSIONS/SESSION-2026-01-30-console-build-info-wiring-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-console-build-info-wiring.md
- STATE.md (update evidence)
- STRUCTURE.md (if new files are added)

Plan
1) Identify the console-web build path used in deploy (CI/build scripts/compose).
2) Pass build args for SHA + build time into Docker build.
3) Verify bundle contains build info or Settings page renders non-unknown values.
4) Run checks and capture evidence.

DoD
- Settings shows non-unknown build SHA/time.
- Evidence recorded (bundle grep or UI screenshot).

Checks
- npm --prefix console-web run lint (if UI touched)

Evidence
- Build args wiring diff.
- Bundle grep showing build info OR UI screenshot.
- STATE.md updated with evidence.

Rollback
- git revert COMMIT_SHA

No-go
- Changing auth, API, or selection gating.
- Hardcoding build info in UI.

Branch
- feat/2026-01-30-console-build-info-wiring-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-console-build-info-wiring-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Build path might live outside repo (infra); may require coordination.
