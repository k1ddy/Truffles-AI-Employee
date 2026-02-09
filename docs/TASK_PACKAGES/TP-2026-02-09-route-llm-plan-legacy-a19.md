# TP-2026-02-09-route-llm-plan-legacy-a19

- Название/цель: Убрать runtime-двусмысленность планировщиков: изолировать `route_llm_plan` как legacy-only API и зафиксировать тестом, что webhook runtime использует только `route_dialogue_controller` + `route_llm_policy_core`.
- Canon refs: `AGENTS.md`; `STATE.md` NOW (policy-core runtime hardening уже в `main`), follow-up после merge PR #589.

- Invariant:
  - Runtime routing решений в webhook не должен деградировать: единственный LLM runtime-контур — `route_dialogue_controller` + `route_llm_policy_core`.
  - Trace/meta контракты и текущие policy-core guardrails не меняются.
  - Никакой новой orchestration-логики в `_legacy.py` и entrypoints.

- Scope:
  - Изоляция legacy-планировщика `route_llm_plan` в `intent_service` (без runtime-использования).
  - Тест-охранa wiring для runtime planner path.

- Out of scope:
  - Большие архитектурные перестройки (DEC).
  - Рефактор всего intent-service.
  - Полный cleanup всех старых plan-артефактов вне минимально нужного diff.

- Touch-list (files/tables):
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/tests/test_*` (новый/обновлённый тест wiring)
  - `STATE.md` (evidence line при необходимости)
  - `docs/SESSIONS/SESSION-2026-02-09-route-llm-plan-legacy-a19.md`
  - `docs/SESSION_INDEX.md`

- Plan (1..N):
  1. Поднять session/worktree по протоколу и проверить текущие references `route_llm_plan`.
  2. Изолировать `route_llm_plan` как legacy-retired API (fail-closed + явная причина), не трогая runtime controller/policy-core path.
  3. Добавить тест-охрану, что webhook runtime wiring не использует `route_llm_plan`.
  4. Прогнать targeted checks + compile.
  5. Зафиксировать evidence и подготовить handoff.

- DoD:
  - `route_llm_plan` не участвует в runtime decision path.
  - Есть автоматический тест на planner wiring (runtime использует только controller + policy-core).
  - Targeted pytest + py_compile зелёные.

- Checks:
  - `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/app/routers/webhook/decision.py`
  - `pytest -q truffles-api/tests/test_llm_policy_core.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_collect_sets_expected_reply_type or llm_policy_core_allows_plan_with_expected_reply or llm_policy_core_degraded_booking_guard_uses_safe_collect"`
  - `pytest -q truffles-api/tests/test_planner_wiring.py`

- Evidence:
  - `git status -sb`
  - `git diff --stat`
  - pytest outputs + compile command outputs
  - ссылка на PR/commit
  - запись в `STATE.md` (для core behavior change)

- Rollback:
  - Revert commit(ы) ветки; runtime возвращается к предыдущему состоянию без миграций.

- No-go:
  - Не включать `route_llm_plan` обратно в runtime.
  - Не добавлять fallback guessing в критичных ветках.
  - Не менять policy-core envelope contract.

- Риски/блокеры:
  - Возможные скрытые оффлайн-скрипты, которые всё ещё используют старый планировщик; mitigated через backward-compatible legacy stub с явным `error`.

- Branch + Worktree path + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-02-09-route-llm-plan-legacy-a19`
  - Worktree: `/home/zhan/worktrees/2026-02-09-route-llm-plan-legacy-a19`
  - Base ref: `origin/main`
  - Merge policy: PR в `main`, без rebase, только merge from base
  - Cleanup: после merge удалить ветку и worktree
