# TP-2026-01-27-session-start-require-tp-a1 — require existing TP for session_start

- **Название/цель:** Make `scripts/session_start.sh` require an existing Task Package and stop auto-creating placeholder TPs.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`.
- **Invariant:** No change to core pipeline behavior; session logs/index remain required.
- **Scope:** `scripts/session_start.sh` validation + docs updates.
- **Out of scope:** Changes to core business logic or runtime behavior.
- **Touch-list:**
  - `scripts/session_start.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSIONS/SESSION-2026-01-27-session-start-require-tp-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Require `--task-package` and verify file exists before creating worktree.
  2) Remove auto-created TP template from `session_start.sh`.
  3) Update docs to state `--task-package` is mandatory.
  4) Update session log/index and run `scripts/session_check.sh`.
- **DoD:**
  - `session_start.sh` errors if `--task-package` missing or file does not exist.
  - No auto-generated TP files in new sessions.
  - Docs mention required `--task-package`.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** Do not loosen session log/index requirements.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-start-require-tp-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-start-require-tp-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
