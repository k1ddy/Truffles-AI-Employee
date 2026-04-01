# TP-2026-01-31-booking-mismatch-signals

- Название/цель: убрать код‑лексиконы из booking mismatch, опереться на out_of_domain_signal/DecisionSignals и pack‑данные; обновить mismatch‑тесты через trace/meta.
- Canon refs: `STATE.md` (NOW: DEC‑018 Unified Reasoning Core), `docs/IMPERIUM_DECISIONS.yaml` (DEC‑018), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant:
  - decision_meta/decision_trace пишутся на каждом user‑message, включая ранние возвраты.
  - booking flow не ломается: активная запись продолжает идти, Hard‑LAW/policy приоритет сохраняется.
  - `_legacy.py` остаётся adapter‑only; без оркестрации в entrypoints.
- Scope:
  - заменить BOOKING/SERVICE hardcode на pack‑лексиконы (domain + system), без бизнес‑слов в коде.
  - добавить preflight gate для booking_signal по out_of_domain_signal и DecisionSignals (greeting/thanks/ack/low‑signal).
  - обновить mismatch‑тесты на проверку `decision_meta.signal_snapshot`.
  - добавить минимальный system‑lexicon pack (booking_request).
- Out of scope:
  - изменения LLM routing/контрактов, policy‑gates, стадий пайплайна.
  - изменения схемы/версии pack‑index.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_cases.json` (если нужно для сигналов)
  - `docs/SESSIONS/SESSION-2026-01-31-booking-mismatch-signals-a4.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Добавить system‑lexicon pack и loader; смёрджить с domain‑lexicon.
  2) Убрать code‑lexicons из booking signal; добавить preflight gate на out_of_domain/DecisionSignals.
  3) Обновить mismatch‑тесты на `decision_meta.signal_snapshot`.
  4) Прогнать targeted pytest и сохранить evidence.
- DoD:
  - В коде нет бизнес‑лексиконов для booking/service; сигнал берётся из pack‑данных.
  - booking gate использует out_of_domain_signal/DecisionSignals; в trace/meta виден blocked_reason.
  - Тесты mismatch опираются на signal_snapshot и проходят.
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_signal or booking_info_interrupt or signals"`
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py -k "booking"`
- Evidence:
  - pytest outputs: `/tmp/pytest_booking_signal_20260131.txt`, `/tmp/pytest_booking_eval_20260131.txt`
  - запись в `STATE.md` (Brain/Top Architect) до merge.
- Rollback: `git revert HEAD` (or revert the PR merge commit).
- No-go:
  - новые бизнес‑лексиконы в коде.
  - изменения в `_legacy.py`/entrypoints.
  - ручное «подгоняние» trace/DB ради evidence.
- Branch/worktree:
  - branch: `feat/2026-01-31-booking-mismatch-signals-a4`
  - worktree: `/home/zhan/worktrees/2026-01-31-booking-mismatch-signals-a4`
  - base: `origin/main`
  - merge: PR (no rebase)
  - cleanup: Brain/Top Architect
- Риски/блокеры:
  - system‑pack новый → обновить `STRUCTURE.md` и `STATE.md` (карта документов).
