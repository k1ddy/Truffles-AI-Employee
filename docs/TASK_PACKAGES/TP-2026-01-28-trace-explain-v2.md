# TP-2026-01-28 — Trace/Explain v2 (Case Details)

- Название/цель: сделать Explain/Trace в карточке заявки понятным (summary “что/почему/что использовано”) + таймлайн по сообщениям.
- Canon refs: `STATE.md` (Phase 5 Explain/Trace exists), `SPECS/CONTROL_PLANE.md` (Inbox UX → Explain/Trace).
- Invariant: RBAC/тенант‑изоляция и selection gates не меняются; API/контракты/миграции не трогаем.
- Scope:
  - UI‑перепаковка Explain/Trace в Case details (summary + timeline).
  - Привязка к сообщениям (message‑level view) и базовые визуальные метки.
- Out of scope: backend changes, contracts, migrations, Inbox layout redesign.
- Touch-list:
  - `console-web/src/components/CaseDetailsPanel.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/types.ts` (если потребуется)
  - (опционально) `console-web/src/lib/trace_format.ts`
- Branch/Worktree/Base:
  - Branch: `feat/2026-01-28-trace-explain-v2-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-trace-explain-v2-a2`
  - Base ref: `origin/main`
  - Merge policy: merge commit
  - Cleanup: удалить ветку + worktree после merge
- Plan:
  1) Зафиксировать текущие поля decision_trace/decision_meta и UX-каркас.
  2) Сформировать summary‑карты (что произошло/почему/что использовано/статусы).
  3) Добавить timeline по сообщениям (стадии/статусы) в карточку заявки.
  4) Локальные проверки: lint (по необходимости) + smoke‑проверка UI.
- DoD:
  - Explain/Trace в карточке заявки дают понятную картину по каждому сообщению.
  - Есть summary + timeline, без поломки текущего UX.
  - Нет изменений API/контрактов.
- Checks:
  - `npm --prefix console-web run lint`
  - Ручной smoke: Inbox → case → details.
- Evidence:
  - Скрин/описание UI (при необходимости — в `docs/REPORTS/`).
  - CI run URL (после PR).
- Rollback: revert merge commit.
- No-go: любые API/контракт/миграции; скрытие обязательных gating.
- Риски/блокеры:
  - Недостаточность decision_trace/decision_meta для полноценного summary (UI должен деградировать безопасно).
