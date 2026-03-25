# TP-2026-01-25-booking-signal-llm-docs

- Название/цель: Зафиксировать в каноне правила booking‑signal и область применения LLM slot_extract, чтобы избежать словарных костылей и удерживать slot‑lock/booking_confirm без риска Hard‑LAW.
- Invariant: Hard‑LAW = только эскалация; slot‑lock не теряется; LLM не создаёт факты.
- Scope: Уточнить правила в `SPECS/CONSULTANT.md` и `SPECS/ARCHITECTURE.md` про booking‑signal, slot_extract gating и приоритет Hard‑LAW/pending.
- Out of scope: Любые изменения кода/логики/тестов, обновления packs, CI, live‑check.
- Touch-list:
  - `SPECS/CONSULTANT.md`
  - `SPECS/ARCHITECTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-01-25-booking-signal-llm-docs.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1) Обновить канон в `SPECS/CONSULTANT.md` (booking‑signal, slot_extract scope).
  2) Обновить канон в `SPECS/ARCHITECTURE.md` (slot_extract gating).
  3) Добавить TP в `STRUCTURE.md` и отметку в `STATE.md` как PLAN.
- DoD:
  - В SPECS явно описан booking‑signal и условия запуска slot_extract.
  - Нет противоречий с Hard‑LAW/Policy/pending приоритетом.
  - Док‑карта обновлена (STRUCTURE/STATE).
- Checks:
  - `rg -n "booking signal|slot_extract" SPECS/CONSULTANT.md SPECS/ARCHITECTURE.md`
- Evidence:
  - `git diff --stat` + ссылки на обновлённые разделы в SPECS.
- Rollback:
  - Revert коммита с изменениями в SPECS/STRUCTURE/STATE.
- No-go:
  - Любые правки логики/кода/тестов.
  - Расширение словарей/regex ради покрытия диалогов.
  - Любое смягчение Hard‑LAW.
- Риски/блокеры:
  - Риск несоответствия между каноном и текущей реализацией; решается отдельным TP на код.

Branch: `docs/booking-llm-canon`
Worktree: `/home/zhan/worktrees/docs-booking-llm-canon`
Base ref: `origin/main`
Merge policy: PR + CI green (docs-only)
Cleanup: удалить ветку + worktree после merge
