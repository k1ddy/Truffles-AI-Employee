# TP-2026-02-02-hybrid-llm-plan-implementation

- Название/цель: Реализовать Hybrid LLM‑plan (plan → validate → tool → compose) с tool‑first и pack‑only ответами, без расширения лексиконов.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC‑020), `STATE.md` (Plan: Hybrid LLM‑plan implementation), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ESCALATION.md`.
- Invariant: факты только через packs/tools; лексиконы не расширяем (fallback‑механика); LLM — pack‑ref‑only; порядок стадий неизменен (stage order snapshot сохраняется); trace/meta пишутся на ранних возвратах; `_legacy.py` adapter‑only.
- Scope:
  - Новый JSON‑контракт LLM‑плана (outcome/tool_action/tool_args/pack_refs/language/confidence/goal/slot_state/open_questions).
  - План‑валидатор (safety/state/pack_refs/tool_args) + tool‑first правило.
  - Интеграция plan‑stage в decision pipeline без смены порядка стадий.
  - Хранение LLM‑плана в `decision_meta` для аудита.
  - Минимальный what‑if набор (подтверждение/идемпотентность/конфликт слота/перенос/отмена/low‑signal).
  - Тесты на plan‑валидатор и expected_reply_type + tool‑idempotency.
- Out of scope: новые инструменты/провайдеры, live‑check, изменение DSL/pack‑compiler, миграции БД.
- Touch-list (ожидаемое):
  - `contracts/llm/` (новый schema для LLM‑плана)
  - `prompts/` (новый prompt для LLM‑плана)
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/services/chatflow_service.py` (tool‑send contract, при необходимости)
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_demo_salon_eval.py`
- Plan:
  1) Добавить контракт LLM‑плана + валидатор (pack_refs/tool_args/outcome).
  2) Встроить plan‑stage в pipeline (без смены stage order hash).
  3) Реализовать tool‑first исполнение (валидный tool_action → инструмент выполняется всегда).
  4) Обновить decision_meta/trace для plan/validator/tool.
  5) Добавить тесты (plan validation + expected_reply_type + idempotency).
  6) Прогнать targeted pytest + chaos‑sim (logic) с evidence.
- DoD:
  - Plan‑контракт валиден, ошибки → deterministic COLLECT/clarify.
  - Tool‑first работает: валидный tool_action вызывает инструмент; без args → COLLECT.
  - Лексиконы не расширены; pack‑only и tool‑only ответы соблюдены.
  - Trace/meta на ранних возвратах и plan‑stage.
  - Тесты зелёные; evidence зафиксировано; `STATE.md` обновлён (Brain/Top Architect).
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply_type or plan or tool"`
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py -k "golden_eval"`
  - `python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" --manager-mode skip --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_hybrid_llm_plan`
- Evidence:
  - `/tmp/pytest_message_endpoint_hybrid_llm_plan.txt`
  - `/tmp/pytest_golden_eval_hybrid_llm_plan.txt`
  - `/tmp/chaos_hybrid_llm_plan` (summary/report/failures)
  - `STATE.md` запись (с путями evidence)
- Rollback: revert merge commit; откатить schema/prompt и pipeline‑изменения.
- No-go:
  - Любые словари в коде (только packs).
  - Изменение порядка стадий без обновления snapshot‑hash.
  - Логика в `_legacy.py`.
  - Live‑check/прод‑интеграции в рамках этой задачи.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-hybrid-llm-plan-implementation-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-hybrid-llm-plan-implementation-a1`
  - Base: `feat/2026-02-02-hybrid-llm-plan-dec-a1`
  - Merge: PR -> main
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: риск переобучения валидатора или рост false‑positive; нужно аккуратно ограничить правилами pack/tools.
