# TP-2026-01-27-session-tp-prestart-a1 — enforce TP before session start

- **Название/цель:** Require Task Package readiness before session start and block placeholder TPs from commit.
- **Canon refs:** `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`.
- **Invariant:** No change to core pipeline behavior; env check via `curl ifconfig` remains required.
- **Scope:** Session ritual ordering + explicit rule in `AGENTS.md`; placeholder guard in `scripts/session_check.sh`.
- **Out of scope:** Changes to `scripts/session_start.sh` behavior or any core business logic.
- **Touch-list:**
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `scripts/session_check.sh`
  - `docs/SESSIONS/SESSION-2026-01-27-session-tp-prestart-a1.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Reorder session ritual to require Task Package before session start.
  2) Add explicit rule in `AGENTS.md`.
  3) Block commits when Task Package still has placeholders.
  4) Update session log/index.
  5) Run `scripts/session_check.sh`.
- **DoD:**
  - `docs/SESSION_START_PROMPT.txt` states TP-before-session-start.
  - `AGENTS.md` states TP readiness requirement before `session_start.sh`.
  - `scripts/session_check.sh` fails if TP has placeholders.
  - Session log and index updated in same commit.
- **Checks:** `scripts/session_check.sh`.
- **Evidence:** `scripts/session_check.sh` output + `git status -sb` + `git diff --stat`.
- **Rollback:** Revert commit; remove session log/index entries.
- **No-go:** No core pipeline changes; no change to env check requirement.
- **Риски/блокеры:** None.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-tp-prestart-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-tp-prestart-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
