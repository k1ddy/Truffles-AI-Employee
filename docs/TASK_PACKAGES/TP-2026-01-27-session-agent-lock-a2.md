# TP-2026-01-27-session-agent-lock-a2 — agent identity lock for parallel sessions

- **Название/цель:** Prevent cross-agent worktree confusion by locking session identity to an agent suffix and validating it in session_start/resume/check.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `STRUCTURE.md`.
- **Invariant:** No change to core pipeline behavior.
- **Scope:** `scripts/session_start.sh`, `scripts/session_resume.sh`, `scripts/session_check.sh` + docs updates.
- **Out of scope:** Business logic or runtime behavior changes.
- **Touch-list:**
  - `scripts/session_start.sh`
  - `scripts/session_resume.sh`
  - `scripts/session_check.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-agent-lock-a2.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Require `--agent` or `SESSION_AGENT` in session_start and ensure session_id suffix matches.
  2) Block new sessions only when open sessions exist for the same agent (unless --force-new).
  3) session_resume defaults to SESSION_AGENT, supports --all, and blocks cross-agent resume.
  4) session_check enforces agent suffix match (warn on legacy no-suffix).
  5) Update docs and session log/index, run `scripts/session_check.sh`.
- **DoD:**
  - Agent identity enforced in session_start/resume/check.
  - Parallel agents can work without blocking each other.
  - Docs mention SESSION_AGENT usage.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** Do not relax session log/index requirements.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-agent-lock-a2
  - Worktree: /home/zhan/worktrees/2026-01-27-session-agent-lock-a2
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
