# TP-2026-01-30-unified-reasoning-core-dec

- Название/цель: DEC для Unified Reasoning Core + канон Signal Snapshot/pack-index/LLM pack-ref-only (data-driven, без бизнес-хардкода).
- Canon refs: `STATE.md` (PLAN consult-quality), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard-LAW/policy/pending pre-LLM; decision_meta/trace на каждом раннем возврате; без оркестрации в entrypoints/_legacy.py; порядок стадий сохраняется.
- Scope:
  - Добавить DEC для Unified Reasoning Core (signals -> gates -> actions -> compose -> trace).
  - Зафиксировать Signal Snapshot Layer и pack-index как обязательные в каноне.
  - Зафиксировать LLM contract: pack-ref-only (LLM не создаёт факты).
  - Обновить STATE/STRUCTURE для отражения DEC.
- Out of scope: любые изменения кода/паков/LLM routing/тестов.
- Touch-list:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `SPECS/ARCHITECTURE.md`
  - `SPECS/CONSULTANT.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-01-30-unified-reasoning-core-dec.md`
  - `docs/SESSIONS/SESSION-2026-01-30-unified-reasoning-core-dec-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Добавить DEC entry.
  2) Обновить канон (Signal Snapshot + pack-index + pack-ref-only LLM).
  3) Обновить STATE/STRUCTURE.
  4) session_check + doc-only commit + fast-forward в main.
- DoD:
  - DEC entry добавлен и связан со SPECS.
  - Канон фиксирует data-driven и запрет бизнес-лексикона в коде.
  - STATE/STRUCTURE обновлены, без кода.
- Checks: `scripts/session_check.sh`.
- Evidence: commit hash + запись в `STATE.md`.
- Rollback: `git revert COMMIT_SHA`.
- No-go: не менять код/пакеты/стадии, не трогать `_legacy.py`.
- Branch/worktree: `docs/2026-01-30-unified-reasoning-core-dec-a1`, `/home/zhan/worktrees/2026-01-30-unified-reasoning-core-dec-a1`, base `origin/main`, doc-only fast-forward в main, cleanup Top Architect.
- Риски/блокеры: несогласованность формулировок канона с DEC-010 (LLM-first understanding) — требуется явное уточнение, что LLM only pack-ref.
