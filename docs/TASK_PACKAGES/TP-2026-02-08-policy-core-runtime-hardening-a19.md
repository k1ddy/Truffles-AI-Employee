# TP-2026-02-08-policy-core-runtime-hardening-a19

- Название/цель: сделать LLM policy core реально primary в runtime без silent fallback: бюджетный резерв под обязательные LLM-стадии, обязательный action-envelope для рискованных веток, явный degraded режим в `decision_meta`, hard-gate judge для strict replay.
- Canon refs: `STATE.md` (GAP: policy_core не primary + strict artifacts с `llm_used_true=1/138`, `judge.mode=off`), `AGENTS.md` (P0/P1 fitness), `SPECS/SYSTEM_REFERENCE.md` (trace/meta contracts), `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.

## Invariant
- FACT/COLLECT/HANDOFF контракт не нарушается; safety-приоритет hard-LAW/policy/pending сохраняется.
- Критичные действия (booking progression/commit, pending-escape без оснований) не выполняются при невалидном policy envelope.
- `decision_meta`/`decision_trace` остаются полными на ранних возвратах и деградациях.
- Изменения не привязываются к одному языку/клиенту (без client_slug хардкодов; язык через model output и pack data).

## Scope
- Добавить budget reserve scheduler для `multi_intent_llm` с резервом под `policy_core` и `answer_interpreter`.
- Усилить policy envelope contract (`intent` + обязательные action/tool_action/confidence/slots) и его runtime validation.
- Ввести явный runtime режим в `decision_meta`: `policy_core` vs `degraded_fallback` + причина деградации.
- Добавить critical-state degraded guard: при невалидном envelope в booking/pending-контексте разрешать только безопасный collect/clarify/handoff path.
- Включить strict replay judge hard gate в `ops/diagnose.py`: strict replay без judge считается невалидным run.
- Добавить/обновить тесты для новых правил.

## Out of scope
- Полный рефактор всего decision pipeline.
- Новые БД-миграции.
- Переписывание всех лексиконов в packs в одном PR.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/intent.py`
- `contracts/llm/llm_policy_core_output.v1.jsonschema`
- `ops/diagnose.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_ai_service.py`

## Plan
1) Ввести explicit envelope contract + валидацию (schema + pydantic + runtime checks).
2) Доработать budget reserve для ранних LLM стадий, чтобы не выжигать budget до policy_core/answer_interpreter.
3) Добавить `policy_core_mode`/`policy_core_degrade_reason` в decision meta + trace stage.
4) Внедрить degraded critical guard для booking/pending-контуров (safe collect/clarify only, кроме явного handoff).
5) В `ops/diagnose.py` сделать strict replay invalid при `judge.enabled=false` (с явным override флагом для debug).
6) Добавить/починить регрессионные тесты и прогнать таргетные suites.

## DoD
- В strict replay нет silent `judge=off`: run падает как invalid без явного override.
- На пользовательском turn всегда пишется `policy_core_mode` + причина деградации при fallback.
- Без валидного envelope в critical booking/pending нет рискованных действий.
- `llm_policy_core_output` валидируется по обновленному контракту.
- Таргетные тесты зелёные.

## Checks
- `pytest -q truffles-api/tests/test_llm_policy_core.py`
- `pytest -q truffles-api/tests/test_ai_service.py -k "reserves_budget_for_controller"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core or policy_core or pending"`
- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/intent_service.py truffles-api/app/schemas/intent.py`

## Evidence
- Логи pytest/py_compile.
- JSON фрагмент `decision_meta` с `policy_core_mode` и `policy_core_degrade_reason`.
- Пример strict replay validation ошибки при `judge=off`.
- Запись в `STATE.md` делает Brain/Top Architect до merge (core behavior change).

## Rollback
- `git revert SHA_FROM_THIS_BRANCH` в feature branch.
- Откатить контракт/schema + runtime guard одним revert.

## No-go
- Никаких хардкодов под demo_salon или конкретный язык.
- Никаких silent fallback без явной причины в meta/trace.
- Никакого ослабления safety/pending/hard-law ради pass-rate.

## Branch / Worktree
- Branch: `feat/2026-02-08-policy-core-runtime-hardening-a19`
- Worktree: `/home/zhan/worktrees/2026-02-08-policy-core-runtime-hardening-a19`
- Base ref: `origin/main`
- Merge policy: PR -> `main`, no rebase
- Cleanup: `scripts/session_end.sh --status done` + cleanup worktree/branch после merge

## Риски/блокеры
- Возможна регрессия в booking UX (более частые clarify при деградации).
- Ужесточение envelope может увеличить `validation_error` до стабилизации prompt.
- Judge hard gate требует ключ в strict replay окружениях.
