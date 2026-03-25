# TP-2026-01-31-llm-wording-clarify

- Название/цель: Уточнить формулировки про роль LLM (смысл vs коммит), чтобы убрать двусмысленность.
- Canon refs: `AGENTS.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: Не менять смысл канона; только прояснить текст.
- Scope: Правки формулировок в `STRATEGY/REQUIREMENTS.md` и `AGENTS.md` (repo + `/home/zhan/AGENTS.md`).
- Out of scope: Любые изменения поведения/логики/конфигов.
- Touch-list:
  - `STRATEGY/REQUIREMENTS.md`
  - `AGENTS.md`
  - `docs/TASK_PACKAGES/TP-2026-01-31-llm-wording-clarify.md`
  - `docs/SESSIONS/SESSION-2026-01-31-llm-wording-clarify-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Уточнить формулировку в `STRATEGY/REQUIREMENTS.md`.
  2) Добавить уточнение в `AGENTS.md` (repo + `/home/zhan/AGENTS.md`).
  3) Зафиксировать сессию (doc-only).
- DoD:
  - Формулировки снимают двусмысленность про “LLM только формулирует”.
  - Нет изменений поведения.
- Checks: не требуется (doc-only).
- Evidence: diff + commit.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Никаких изменений в коде/поведении/LLM-пайплайне.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `main` (doc-only)
  - Worktree: `/home/zhan/truffles-main`
  - Base ref: `origin/main`
  - Merge policy: fast-forward
  - Cleanup: не требуется
- Риски/блокеры: нет.
