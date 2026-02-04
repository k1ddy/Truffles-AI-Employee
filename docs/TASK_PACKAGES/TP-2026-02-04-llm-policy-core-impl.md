# TP-2026-02-04-llm-policy-core-impl

- Название/цель: Реализовать DEC-023 в runtime: контракт LLM policy core (action/slots/next_question/needs_manager) + hard-safety валидация + отключение override-гейтов (expected_reply/pending/minimum_data/policy/resolve_action) в пользу guard-only.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-023), `STATE.md` (GAP: LLM policy core override-gates), `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: FACT/COLLECT/HANDOFF контракт; hard-LAW/policy/pending/manager_active всегда выше; факты только из packs/tools; trace/meta пишутся на каждом раннем возврате; `_legacy.py` adapter-only; gate must fire; порядок стадий сохраняется.
- Scope:
  - Ввести JSON-schema + Pydantic контракт LLM policy core output (action, slots, next_question, needs_manager, risk_signals, pack_refs/tool_refs, confidence).
  - Добавить LLM policy core вызов + валидатор (schema + hard-safety/policy/pending/manager_active) как первичный источник decision.action.
  - Перевести expected_reply/pending/minimum_data/policy/ood/truth-gate в режим guard-only (валидация/возможный veto) без override маршрута.
  - Перенастроить routing: `_resolve_action` не принимает финальное решение до LLM policy; `escalate` только при explicit request или policy risk.
  - Обновить decision_trace/meta: запись LLM policy payload/validation, guard rejections, action_source.
  - Тесты: контракт LLM policy + guard порядок (pending/expected_reply/LAW) + stage order snapshot; обновить/добавить кейсы в booking/decision tests.
  - Обновить SPECS при необходимости (контракт/trace поля).
- Out of scope: изменения packs/knowledge, новые бизнес-правила, миграции БД, провайдер gateway, live-check/прод деплой, полная переработка pipeline.
- Touch-list:
  - `contracts/llm/llm_policy_core_output.v1.jsonschema`
  - `truffles-api/app/schemas/`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/services/ai_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/tests/`
  - `SPECS/ARCHITECTURE.md`
  - `SPECS/CONSULTANT.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Plan:
  1) Зафиксировать контракт LLM policy core (jsonschema + pydantic) и подключить валидатор.
  2) Встроить LLM policy core в decision pipeline как primary action source; добавить safety veto (hard-LAW/policy/pending/manager_active).
  3) Перевести override-гейты в guard-only: expected_reply/pending/minimum_data/ood/truth не меняют action, а валидируют/обогащают.
  4) Обновить trace/meta: llm_policy_payload, llm_policy_valid, action_source, guard_rejection_reason.
  5) Покрыть тестами: контракт LLM policy, guard порядок, stage order snapshot, booking expected_reply без override.
  6) Обновить SPECS/STATE/STRUCTURE с evidence после CI.
- DoD:
  - LLM policy core contract валиден, схема проверяется в коде.
  - Решение action берется из LLM policy core; override-гейты не перехватывают маршрут.
  - Hard-LAW/policy/pending/manager_active корректно veto-ят LLM решения и пишут trace/meta.
  - expected_reply/booking slot extract работает без изменения action, только как slot/guard.
  - decision_trace/meta содержит action_source + llm_policy_* поля.
  - Тесты + CI green; запись в `STATE.md` с evidence (Brain/Top Architect).
- Checks:
  - `pytest -q truffles-api/tests/test_reasoning_core.py`
  - `pytest -q truffles-api/tests/test_webhook_booking.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py`
  - `pytest -q truffles-api/tests/test_llm_policy_core.py`
- Evidence:
  - CI run URL + logs.
  - decision_trace/decision_meta sample (llm_policy_* + guard veto) via `ops/diagnose.py explain`.
  - запись в `STATE.md` (до merge для core).
- Rollback: `git revert` PR; при необходимости временно выключить `LLM_POLICY_CORE_ENABLED` (если будет введён флаг).
- No-go: обход hard-LAW/pending/manager_active; оркестрация в `_legacy.py`; расширение словарей ради покрытия; правки БД ради evidence.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-04-llm-policy-core-impl-a7`
  - Worktree: `/home/zhan/worktrees/2026-02-04-llm-policy-core-impl-a7`
  - Base: `origin/main`
  - Merge: PR to `main` (no rebase)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: конфликт с ожидаемым booking flow (expected_reply_type) и pending gate; нужен чёткий guard-only порядок и тесты на goal_drop/booking_interrupt.
