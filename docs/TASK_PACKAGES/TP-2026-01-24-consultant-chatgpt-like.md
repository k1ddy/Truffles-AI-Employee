# TP-2026-01-24 Consultant canon: ChatGPT-like domain-bound + slot-lock

## Название/цель
Обновить канон поведения консультанта: ChatGPT-like естественность, но строго domain-bound; slot-lock/подтверждение слотов; строгая эскалация LAW (мед/юрид/возвраты/жалобы) без офферов.

## Invariant
- LAW/Policy — выше всего, любые мед/юрид/возвраты/жалобы = только handoff.
- Booking-цель не теряется на перебивках.
- Никаких фактов вне pack; LLM только смысл/перефраз.

## Scope
- Обновить канон в `SPECS/CONSULTANT.md`.
- Зафиксировать архитектуру слотов и подтверждения в `SPECS/ARCHITECTURE.md`.
- Добавить Task Package в `STRUCTURE.md`.

## Out of scope
- Реализация slot-extract/confirm в коде.
- Автотесты/CI/live-check.

## Touch-list
- `SPECS/CONSULTANT.md`
- `SPECS/ARCHITECTURE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-consultant-chatgpt-like.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Внести изменения в канон поведения (ChatGPT-like domain-bound, slot-lock, strict LAW escalation).
2) Внести архитектурные уточнения по slot_extract/validate/confirm и trace/meta.
3) Обновить `STRUCTURE.md` (список Task Packages).
4) Сформировать краткий отчёт и подготовить дальнейший TP на реализацию.

## DoD
- Канон явно описывает ChatGPT-like domain-bound поведение и slot-lock/booking_confirm.
- LAW-ветки однозначно требуют handoff без офферов.
- Архитектурные контракты описаны (trace/meta поля и стадии).

## Checks
- `rg -n "ChatGPT-like|slot-lock|booking_confirm" SPECS/CONSULTANT.md SPECS/ARCHITECTURE.md`

## Evidence
- Diff в PR + ссылки на обновлённые секции.

## Rollback
- Откат коммита(ов) с изменениями канона.

## No-go
- Не менять runtime код и не подгонять поведение под тесты.
- Не добавлять новые требования без фиксации в каноне.

## Риски/блокеры
- Требуется согласование формулировок Owner/Brain.

## Branch / Worktree
- Branch: `docs/consultant-chatgpt-like`
- Worktree: `/home/zhan/worktrees/consultant-chatgpt-like`
- Base ref: `origin/main`
- Merge policy: PR + CI green (если требуется)
- Cleanup: Brain после merge
