# TP-2026-01-27-session-end-noop-a1 — session_end no-op + summary accuracy

- **Название/цель:** Make `session_end` idempotent once status is done and require summaries to reflect actual diffs.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`.
- **Invariant:** No change to core pipeline behavior; no impact on live/CI logic.
- **Scope:** `scripts/session_end.sh` behavior + docs clarification.
- **Out of scope:** Any core product logic or test behavior.
- **Touch-list:**
  - `scripts/session_end.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSIONS/SESSION-2026-01-27-session-end-noop-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Make `session_end` a no-op when status already done and no notes are provided.
  2) Block status changes after done and block adding notes after done.
  3) Clarify summary-matches-diff rule in docs.
  4) Update session log/index and run `scripts/session_check.sh`.
- **DoD:**
  - `session_end` exits without changes if already done and no notes requested.
  - `session_end` errors if trying to change status or add notes after done.
  - Docs state summary must match actual diff.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** No weakening of session log/index requirements.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-end-noop-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-end-noop-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
