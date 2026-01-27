# TP-2026-01-27-session-resume-protocol-a1 — resume after compaction

- **Название/цель:** Add a deterministic resume protocol and prevent starting a new session when an active one exists for the same agent suffix.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `STRUCTURE.md`.
- **Invariant:** No change to core pipeline behavior; no impact on runtime logic.
- **Scope:** New resume script + session_start guard + docs updates.
- **Out of scope:** Any business logic or test behavior changes.
- **Touch-list:**
  - `scripts/session_start.sh`
  - `scripts/session_resume.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-resume-protocol-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Add `scripts/session_resume.sh` to list open sessions and show worktree/branch.
  2) Block `session_start` if an open session exists for the same agent suffix.
  3) Document resume protocol in AGENTS + session prompt + STRUCTURE.
  4) Update session log/index and run `scripts/session_check.sh`.
- **DoD:**
  - `session_resume.sh` lists open sessions and prints resume instructions.
  - `session_start.sh` errors if an open session exists for the same agent suffix.
  - Docs updated to mention resume protocol and new script.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** Do not loosen existing session gates.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-resume-protocol-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-resume-protocol-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
