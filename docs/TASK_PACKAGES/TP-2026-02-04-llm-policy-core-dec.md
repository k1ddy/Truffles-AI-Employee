# TP-2026-02-04-llm-policy-core-dec

- Название/цель: Зафиксировать DEC по переходу на LLM policy core (LLM принимает решение action/slots/next_question) и подготовить план/контракты для имплементации без детерминированных гейтов.
- Canon refs: `STATE.md` (NOW/GAP по booking диалогам), `docs/IMPERIUM_DECISIONS.yaml` (DEC-010/DEC-018/DEC-020), `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: продуктовый контракт FACT/COLLECT/HANDOFF сохраняется; факты только через packs/tools; policy/LAW gate остаётся жёстким; trace/meta пишутся на ранних возвратах; `_legacy.py` adapter-only.
- Scope:
  - DEC-023: LLM policy core (LLM принимает action/slots/next_question; deterministic code = schema-валидация + safety + tool execution).
  - Контракт LLM policy core output (JSON schema) + правила валидации/ошибок.
  - План отключения expected-reply/pending/router overrides при включённом LLM policy core.
  - План перехода эскалаций: только явный запрос менеджера или policy risk.
  - План тестирования (LLM генерирует сценарии, проверка только по decision_meta/trace).
  - Обновление `STATE.md` + `STRUCTURE.md`.
- Out of scope: реализация в коде, изменения в проде, live-check, миграции БД, обновление pack-compiler.
- Touch-list:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `docs/TASK_PACKAGES/TP-2026-02-04-llm-policy-core-dec.md`
  - `STATE.md` (обновление только Brain/Top Architect)
  - `STRUCTURE.md`
  - (будущая имплементация) `contracts/llm/llm_policy_core_output.v1.jsonschema`
  - (будущая имплементация) `truffles-api/app/routers/webhook/decision.py`
  - (будущая имплементация) `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`
- Plan:
  1) Зафиксировать DEC-023 в `docs/IMPERIUM_DECISIONS.yaml`.
  2) Описать контракт LLM policy core output + правила валидации (schema + hard safety).
  3) Определить флаг/режим для отключения expected-reply/pending/router overrides.
  4) Зафиксировать правила эскалации: только явный запрос менеджера или policy risk.
  5) Зафиксировать LLM-тестирование: генерация сценариев + детерминированный verify по decision_meta/trace.
  6) Обновить `STATE.md` и `STRUCTURE.md`.
- DoD:
  - DEC-023 записан в `docs/IMPERIUM_DECISIONS.yaml`.
  - TP зафиксирован с планом/контрактами для имплементации.
  - `STATE.md` и `STRUCTURE.md` обновлены.
- Checks:
  - `scripts/session_check.sh` (doc-only).
- Evidence:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `docs/TASK_PACKAGES/TP-2026-02-04-llm-policy-core-dec.md`
  - запись в `STATE.md`
- Rollback: revert doc-commit.
- No-go:
  - Любые runtime/behavior изменения без отдельного TP.
  - Изменение порядка стадий без отдельного DEC и тестов.
  - Live-check/прод-изменения в рамках этого TP.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-04-llm-policy-core-dec-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-04-llm-policy-core-dec-a6`
  - Base: `origin/main`
  - Merge: doc-only fast-forward в `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: конфликт с DEC-010/DEC-018 (детерминированные гейты). Требуется явное позиционирование как замена decision_model и фиксация safety-гейтов.
