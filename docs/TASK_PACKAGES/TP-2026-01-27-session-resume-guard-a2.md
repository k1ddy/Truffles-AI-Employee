# TP-2026-01-27-session-resume-guard-a1 — prevent new sessions after compaction

- **Название/цель:** Prevent accidental new sessions after compaction by requiring explicit override when open sessions exist, and improve resume listing.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `STRUCTURE.md`.
- **Invariant:** No change to core pipeline behavior.
- **Scope:** `scripts/session_start.sh` guard + `scripts/session_resume.sh` improvements + docs updates.
- **Out of scope:** Business logic or test behavior changes.
- **Touch-list:**
  - `scripts/session_start.sh`
  - `scripts/session_resume.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-resume-guard-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Add `--force-new` to `session_start` and block new sessions when any open sessions exist.
  2) Make `session_resume` list open sessions by default and show dirty status.
  3) Document the rule and resume flow.
  4) Update session log/index and run `scripts/session_check.sh`.
- **DoD:**
  - `session_start` errors if open sessions exist unless `--force-new`.
  - `session_resume` lists open sessions (dirty/clean) without args.
  - Docs updated to reflect the new guard.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** Do not loosen session log/index requirements.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-resume-guard-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-resume-guard-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
