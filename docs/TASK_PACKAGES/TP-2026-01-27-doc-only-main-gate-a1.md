# TP-2026-01-27-doc-only-main-gate-a1 — allow doc-only main with session log

- **Название/цель:** Allow doc-only commits on `main` while still requiring session log + index, so fast-path works without breaking guardrails.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `scripts/session_check.sh`, `scripts/session_gate.sh`.
- **Invariant:** No change to core pipeline behavior or env checks; non-doc changes still blocked on `main`.
- **Scope:** `scripts/session_check.sh` doc-only detection for `main`; docs clarification for doc-only main requirements.
- **Out of scope:** Changes to `session_start.sh` or `session_gate.sh` logic; no changes to core code.
- **Touch-list:**
  - `scripts/session_check.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSIONS/SESSION-2026-01-27-doc-only-main-gate-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Add doc-only detection for `main` in `scripts/session_check.sh`.
  2) Require session log + index in doc-only `main` commits.
  3) Clarify doc-only main rule in docs.
  4) Update session log/index and run `scripts/session_check.sh`.
- **DoD:**
  - Doc-only `main` commits pass `scripts/session_check.sh` when session log + index are included.
  - Non-doc changes on `main` still fail `scripts/session_check.sh`.
  - Docs updated to reflect doc-only main requirement.
- **Checks:** `SESSION_ALLOW_DONE=1 scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** No bypass for non-doc changes on `main`.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-doc-only-main-gate-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-doc-only-main-gate-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
