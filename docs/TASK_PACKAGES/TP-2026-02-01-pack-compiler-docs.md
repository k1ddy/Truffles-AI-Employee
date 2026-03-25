# TP-2026-02-01-pack-compiler-docs

- Название/цель: Синхронизировать owner‑docs под DEC‑019 и подготовить Task Package для реализации Pack‑Compiler/DSL.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC‑019), `STATE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ACTIVE_LEARNING.md`.
- Invariant: runtime pipeline и порядок стадий не меняем; `_legacy.py` adapter-only; facts только из packs/tools; trace/meta обязательны.
- Scope:
  - Обновить owner‑docs с упоминанием DEC‑019 (pack compiler + DSL + auto‑ingest).
  - Зафиксировать runtime contract: compiled artifacts only.
  - Создать Task Package для реализации (код) с DoD/Checks/Evidence.
  - Обновить `STATE.md`/`STRUCTURE.md`/session docs.
- Out of scope: реализация compiler/runtime, изменения routing/LLM/DB, прод‑роллаут.
- Touch-list:
  - `SPECS/ARCHITECTURE.md`
  - `SPECS/CONSULTANT.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `SPECS/ACTIVE_LEARNING.md`
  - `STRATEGY/REQUIREMENTS.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-02-01-pack-compiler-implementation.md`
  - `docs/SESSIONS/SESSION-2026-02-01-pack-compiler-docs-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Найти места в owner‑docs, где фиксируется контракт данных/pack‑index/ingest.
  2) Вставить DEC‑019 (pack compiler + DSL + auto‑ingest) и runtime contract.
  3) Сформировать Task Package для реализации (compiler/DSL/runtime consumption/eval).
  4) Обновить `STATE.md`/`STRUCTURE.md`.
- DoD:
  - DEC‑019 отражён в owner‑docs.
  - Task Package на реализацию добавлен и готов к старту.
  - Запись в `STATE.md` с указанием TP.
- Checks: doc‑only.
- Evidence: doc diff + запись в `STATE.md` (Top Architect).
- Rollback: revert doc commit.
- No-go: любые runtime/DB изменения.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-01-pack-compiler-docs-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-01-pack-compiler-docs-a1`
  - Base: `feat/2026-02-01-pack-compiler-dec019-a1`
  - Merge: PR -> main
  - Cleanup: Top Architect
- Риски/блокеры: DEC‑019 ещё не синхронизирован в owner‑docs; не начинать реализацию без согласованных контрактов.
