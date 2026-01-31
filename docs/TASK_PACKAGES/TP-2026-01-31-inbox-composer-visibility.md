# Task Package — Inbox composer visibility at 100% zoom

- Title/goal: Restore Inbox chat composer (input + Send) visibility at 1920x1080 @100% zoom after selecting a case, without breaking macros or layout.
- Canon refs: `STATE.md` (add GAP + evidence), `SPECS/CONTROL_PLANE.md` (Inbox UX standard).
- Invariant:
  - Composer input + Send button visible at 100% zoom on 1920x1080.
  - Message send works; macros panel remains usable.
  - No regressions to case list/details layout.
- Scope:
  - Console Inbox chat layout and composer container sizing/overflow.
  - Remove obsolete Task Package per owner request: `docs/TASK_PACKAGES/TP-2026-01-31-inbox-macros-ui-fix.md`.
- Out of scope:
  - Console API/DB changes.
  - Macro logic changes or new features.
  - Broad layout redesign.
- Touch-list (files):
  - `console-web/src/components/ChatInterface.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/InboxView.tsx`
  - `docs/TASK_PACKAGES/TP-2026-01-31-inbox-macros-ui-fix.md` (delete)
  - `docs/SESSIONS/SESSION-2026-01-31-inbox-composer-visibility-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- Plan:
  1) Add GAP entry in `STATE.md` for composer visibility regression.
  2) Inspect Inbox chat layout (flex/overflow/height) and identify clipping at 100% zoom.
  3) Implement minimal layout fix to keep composer visible.
  4) Run `npm --prefix console-web run lint`.
  5) Rebuild/restart console-web; capture build info and update `STATE.md` with evidence.
- DoD:
  - At 1920x1080 @100% zoom, composer input + Send button visible without scroll/zoom.
  - Send works; macros remain visible and usable.
  - Lint clean; build info recorded.
- Checks:
  - `npm --prefix console-web run lint`
- Evidence:
  - Lint log (`/tmp/console_web_lint_inbox_composer_visibility_YYYYMMDD.txt`).
  - Console build info (Settings screenshot or log path).
  - `STATE.md` entry with evidence paths.
- Rollback:
  - `git revert COMMIT_SHA` and run `scripts/restart_console_web.sh`.
- No-go:
  - No API/DB/schema changes.
  - No hidden layout changes unrelated to composer visibility.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-01-31-inbox-composer-visibility-a1`
  - Worktree: `/home/zhan/worktrees/2026-01-31-inbox-composer-visibility-a1`
  - Base: `origin/main`
  - Merge policy: PR to `main` after `scripts/session_check.sh`
  - Cleanup: remove worktree + delete branch after merge
- Risks/blockers:
  - Risk: layout fix could reintroduce macro panel clipping; verify in Inbox at 100% zoom.
