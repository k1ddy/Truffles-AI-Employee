# TP-2026-01-25 — Thanks Typo Normalization (Smalltalk)

## Название/цель
Сделать fast smalltalk устойчивым к опечаткам в коротких “спасибо/рахмет” сообщениях и убрать ложные OOD в chaos-sim.

## Invariant
- Hard-LAW: мед/жалобы/возвраты/оплата → только эскалация.
- decision_meta/decision_trace пишутся на каждый inbound.
- Никакой оркестрации в `_legacy.py`.

## Scope
- Нормализация коротких фраз: схлопывание повторов символов.
- Распознавание благодарности в 1–2 токенах без вопросительных/цифровых маркеров.
- Booking chaos-sim smoke с `--sim-time` для подтверждения (1 кейс).

## Out of scope
- Изменение доменной логики booking/consult/policy.
- Изменение эвристик out_of_domain или evaluator.
- Любые UI/Console изменения.

## Touch-list
- `truffles-api/app/services/ai_service.py`
- `docs/TASK_PACKAGES/TP-2026-01-25-thanks-typo-smalltalk.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Усилить `normalize_for_matching` для опечаток (повторные символы).
2) Обновить `is_thanks_message` под 1–2 токена с guard на `?`/digits.
3) Прогнать booking chaos-sim (1 кейс) с `--sim-time`.
4) Записать evidence в `STATE.md`.

## DoD
- Опечатка вроде “спасиббо” распознаётся как thanks.
- Chaos-sim booking smoke с `--sim-time` завершился без failures.

## Checks
- `python3 ops/diagnose.py chaos-sim --count 1 --kinds booking --sim-time "2026-01-24T12:00:00+06:00" --manager-mode skip --timeout 20 --output-dir /tmp/chaos_booking_simtime_override_1c`

## Evidence
- `/tmp/chaos_booking_simtime_override_1c/summary.json` (failures=0)

## Rollback
- Revert коммита.

## No-go
- Красные тесты.
- Нет evidence/артефактов.

## Риски/блокеры
- Возможны редкие ложные классификации коротких “спасибо + слово”; если проявятся — усилим guard.

## Branch/Worktree
- Branch: `feat/thanks-typo-smalltalk`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base: `origin/main`
- Merge policy: PR + CI green; merge делает Brain
- Cleanup: Brain после merge
