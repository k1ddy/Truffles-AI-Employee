# TP-2026-02-04-llm-policy-fastpath

## Название/цель
Ускорить достижение готовности: LLM policy core принимает action/slots/next_question, override-гейты становятся guard-only, unknown_state не оставляет диалог без ответа.

## Canon refs
- `STATE.md` (GAP: booking dialogs missing replies + LLM dialog gaps).
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-023).
- `STRATEGY/REQUIREMENTS.md`.
- `SPECS/CONSULTANT.md`.
- `SPECS/ARCHITECTURE.md`.
- `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- FACT/COLLECT/HANDOFF сохраняется.
- Hard-LAW/policy gates остаются жесткими.
- decision_meta/trace пишутся на ранних возвратах.
- `_legacy.py` = adapter-only, без оркестрации.
- Stage order snapshot не меняется.

## Scope
- Контракт и нормализация LLM policy core output.
- LLM policy core как источник истины для action/slots при валидном контракте.
- expected_reply/pending/minimum_data/policy -> guard-only в LLM policy path.
- unknown_state -> clarify/reply fallback при allow_bot_reply.
- Тесты на LLM policy routing + unknown_state fallback.

## Out of scope
- Изменения packs/policy контента.
- Миграции БД.
- Деплой/CI livecheck.
- Консоль/Control Plane.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `contracts/llm/llm_policy_core_output.v1.jsonschema` (new)
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_intent.py` (if touched)
- `STATE.md` (evidence before merge)
- `docs/SESSIONS/SESSION-*.md`, `docs/SESSION_INDEX.md`

## Plan
1) Добавить schema + валидатор для LLM policy core output.
2) Подключить policy output в decision pipeline; перевести override-гейты в guard-only.
3) Ввести fallback для unknown_state -> clarify/reply с trace/meta.
4) Обновить/добавить тесты.
5) Прогнать тесты.
6) Прогнать 5 LLM booking dialogs + анализ (reply rate, unknown_state, outbox).
7) Обновить `STATE.md` с evidence (Brain/Top Architect до merge).

## DoD
- unknown_state не оставляет bot_response пустым при allow_bot_reply.
- LLM policy core используется при валидном контракте, hard-LAW/policy соблюдены.
- `pytest -q truffles-api/tests/test_message_endpoint.py` проходит.
- LLM dialog run (5 диалогов) показывает >=80% ответов; иначе фиксируется GAP с evidence и без merge.
- `STATE.md` обновлен evidence (до merge).

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_intent.py` (если меняли intent_service)
- LLM dialogs (evidence):
  - `python3 scripts/booking_dialog_scenarios.py --mode llm --count 5 --min-turns 10 --max-turns 15 --include-media --media-mode text --output /tmp/booking_dialogs_llm.json`
  - webhook run + `ops/diagnose.py dialog-report` (evidence in `/tmp/booking_dialog_runs_allowlist_20260204-142305/`, reports in `/tmp/dialog-report-*-142305.md`)

## Evidence
- pytest output in `/tmp/`
- LLM dialog run summary + dialog-report bundle
- запись в `STATE.md`

## Rollback
- revert commit(s).

## No-go
- Оркестрация в entrypoints/_legacy.py.
- Ослабление hard-LAW/policy.
- Изменение порядка стадий без отдельного DEC+tests.

## Branch + Worktree
- Branch: `feat/2026-02-04-llm-policy-fastpath-a9`
- Worktree: `/home/zhan/worktrees/2026-02-04-llm-policy-fastpath-a9`
- Base ref: `origin/main`
- Merge policy: PR -> main (Brain/Top Architect)
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch

## Риски/блокеры
- Риск регрессии в booking/pending при неправильном guard-only режиме.
- LLM timeout/fallback может привести к clarify-loop; нужен лимит.
