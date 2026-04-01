# TP-2026-01-25 — Human Dialog Generator + Chaos Suite

## Название/цель
Сделать генерацию и тесты “живых” диалогов (10–15 ходов, перебивки, правки слотов), сохраняя Hard‑LAW и slot‑lock.

## Invariant
- Hard‑LAW: мед/жалобы/возвраты/оплата → только эскалация.
- decision_meta/decision_trace пишутся на каждый inbound.
- Никакой оркестрации в `_legacy.py`.

## Scope
- Обновить генератор `chaos-sim` (human‑like фразы, перебивки, исправления слотов).
- Расширить unit‑suite для booking chaos диалога (реальные формулировки).
- Добавить опцию dump/артефакт генерации для дальнейшего LLM‑eval (без LLM в unit).

## Out of scope
- Изменение прод‑логики пайплайна.
- Изменение client packs / политики / RAG данных.
- UI/Console изменения.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `docs/TASK_PACKAGES/TP-2026-01-25-human-dialog-tests.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Обновить chaos‑generator (human‑like templates + slot corrections + interruptions).
2) Укрепить booking chaos unit‑suite (10–15 ходов, noise, перебивки).
3) Добавить артефакт генерации (dump) для LLM‑eval подмножества.
4) Прогнать локальные тесты + dry‑run генерации.
5) Записать evidence в `STATE.md`.

## DoD
- `chaos-sim` генерирует диалоги с перебивками/исправлениями/неидеальными слотами.
- Booking chaos unit‑suite отражает “живые” сообщения и проходит локально.
- Артефакт генерации доступен для LLM‑eval (не в unit).

## Checks
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`

## Evidence
- Локальный `pytest` output.
- Артефакт генерации (paths) + sample dialog (для LLM‑eval).
- Запись в `STATE.md`.

## Rollback
- Revert коммита(ов).

## No-go
- Красные тесты.
- Изменение прод‑логики вместо тестов/генератора.

## Риски/блокеры
- Генератор может давать ложные ожидания → фиксируем через trace/meta, а не текст.
- LLM‑eval требует ключи и запускается отдельно (не в unit/CI).

## Branch/Worktree
- Branch: `feat/slot-lock-booking-confirm`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base: `origin/main`
- Merge policy: PR + CI green; merge делает Brain
- Cleanup: Brain после merge
