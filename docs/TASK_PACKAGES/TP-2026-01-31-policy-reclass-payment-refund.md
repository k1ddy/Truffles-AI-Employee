# TP-2026-01-31-policy-reclass-payment-refund

- Название/цель: Разделить payment_info (policy gate) и refund/payment‑issue (Hard‑LAW) в demo_salon pack без изменений логики.
- Canon refs: `STATE.md` (DEC‑018 план P0), `STRATEGY/REQUIREMENTS.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard‑LAW остаётся для возвратов/подтверждения транзакций; policy gate остаётся pack‑driven; decision_meta/trace пишутся на каждом policy‑gate.
- Scope:
  - Обновить `policy.hard_law.intents` в demo_salon pack (убрать `payment`).
  - Расширить `policy.guard_topics.refund` для payment‑issue (ошибка оплаты/двойное списание и т.п.).
  - Обновить тесты policy gate (ожидания по payment_info vs hard_law).
- Out of scope: изменения `policy.py`/entrypoints, новые секции policy в коде, изменения stage order, LLM/pack‑index.
- Touch-list:
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `truffles-api/app/knowledge/demo_salon/EVAL.yaml` (только если нужен апдейт oracle)
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_knowledge_validation.py`
- Plan:
  1) Обновить pack: убрать `payment` из hard_law, расширить refund guard topics.
  2) Обновить тесты на policy gate (payment_info ожидается как policy_gate).
  3) При необходимости обновить EVAL/oracle.
  4) Прогнать targeted pytest.
  5) Зафиксировать evidence в `STATE.md` (до merge).
- DoD:
  - `policy_gate=payment_info` для payment‑info запросов, `action=escalate` при `allow=false`.
  - refund/payment‑issue остаются Hard‑LAW.
  - Тесты зелёные; evidence записан в `STATE.md`.
- Checks:
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py -k "policy_gates_discount_and_payment"`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "payment_info"`
  - `pytest -q truffles-api/tests/test_knowledge_validation.py`
- Evidence:
  - вывод pytest (команды выше) + запись в `STATE.md` (Top Architect) до merge.
- Rollback: `git revert COMMIT_SHA`.
- No-go:
  - Не трогать `policy.py`/entrypoints/`_legacy.py`.
  - Не добавлять бизнес‑лексиконы в код.
  - Не менять порядок стадий.
- Branch/worktree: `feat/2026-01-31-policy-reclass-a1`, `/home/zhan/worktrees/2026-01-31-policy-reclass-a1`, base `origin/main`, merge policy PR+CI, cleanup by Brain/Top Architect.
- Риски/блокеры: недостаточные refund‑keywords могут пропускать payment‑issue; покрыть тестами.
