# TP-2026-02-01-pack-compiler-dsl

- Название/цель: DEC + спецификация Pack-Compiler, Policy/Signal DSL и auto-ingest в packs (без реализации).
- Canon refs: `STATE.md` (NOW/PLAN), `docs/IMPERIUM_DECISIONS.yaml` (DEC-019 draft), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/CONSULTANT.md`.
- Invariant: runtime pipeline и порядок стадий не меняем; `_legacy.py` остаётся adapter-only; facts только из packs/tools; trace/meta обязательны.
- Scope:
  - Зафиксировать DEC-019: компиляция packs -> индекс/сигнальный граф; runtime читает только compiled artifacts.
  - Специфицировать Policy/Signal DSL (schema, versioning, validation).
  - Специфицировать compiler pipeline (inputs/outputs, hashing, determinism, upgrade path).
  - Специфицировать auto-ingest: диалоги -> candidate cases -> approval -> packs (gating/roles).
  - Сформировать evidence/DoD для перехода к реализации (golden eval + chaos-sim + shadow replay по trace/meta).
- Out of scope: реализация compiler/runtime, изменения routing/LLM/DB схем, прод-роллаут, миграции packs.
- Touch-list:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `SPECS/ARCHITECTURE.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `SPECS/CONSULTANT.md`
  - `SPECS/ACTIVE_LEARNING.md`
  - `STRATEGY/REQUIREMENTS.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-01-pack-compiler-dsl-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Инвентаризировать текущий pack-index/Signal Snapshot contract и gaps.
  2) Описать DSL schema (Policy/Signal) + versioning + validation rules.
  3) Описать compiler pipeline (inputs/outputs, deterministic hash, build artifacts).
  4) Описать auto-ingest flow + approvals/roles + safety gates.
  5) Описать runtime contract (compiled artifacts only) + fallback path.
  6) Зафиксировать DEC-019 и обновить owner docs.
- DoD:
  - DEC-019 добавлен в `docs/IMPERIUM_DECISIONS.yaml`.
  - DSL + compiler + auto-ingest спецификации описаны в canonical docs.
  - Evidence/DoD для реализации сформированы в Task Package/STATE.md.
- Checks:
  - Doc diff + `rg`/линты по необходимости (без кода).
- Evidence:
  - DEC-019 entry + doc updates; запись в `STATE.md` (Top Architect).
- Rollback: revert doc commit.
- No-go:
  - Любые runtime/DB изменения.
  - Изменение порядка стадий без отдельного DEC + tests.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-01-pack-compiler-dsl-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-01-pack-compiler-dsl-a1`
  - Base: `origin/main`
  - Merge: PR -> main
  - Cleanup: Top Architect
- Риски/блокеры: высокая сложность и риск дрейфа без строгого контракта; требуется DEC и доказательства до реализации.
