# TP-2026-02-02-minimum-data-safe-mode

- Название/цель: Реализовать runtime Minimum Data Contract и SAFE_MODE gate (DEC-021) с трассировкой, health и тестами.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-021), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `STATE.md` (PLAN).
- Invariant: truth-first; pack-only; LLM не коммитит решения/факты; trace/meta пишутся на каждом раннем возврате; gate must fire.
- Scope:
  - Ввести Minimum Data Contract (schema + validator) для филиала/pack.
  - Добавить SAFE_MODE gate в runtime (ранняя стадия) с decision_trace/decision_meta.
  - Экспортировать readiness status в `/admin/health` и в decision_meta.
  - Тесты на contract validation, gate поведение, health.
  - Обновить runtime docs при необходимости.
- Out of scope: создание/правка pack-данных, авто-ингест, UI/console, LLM промпты.
- Touch-list:
  - `truffles-api/app/contracts/`
  - `truffles-api/app/schemas/`
  - `truffles-api/app/services/knowledge_validation.py`
  - `truffles-api/app/services/consult_pack_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/health_service.py`
  - `truffles-api/app/models/`
  - `truffles-api/tests/`
  - `SPECS/CONSULTANT.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STATE.md`
- Plan:
  1) Зафиксировать schema Minimum Data Contract (jsonschema + python validator).
  2) Добавить readiness вычисление и SAFE_MODE gate в pipeline (trace/meta обязательны).
  3) Прокинуть readiness в `/admin/health` + decision_meta.
  4) Покрыть тестами: валидатор, gate, health.
  5) Обновить docs + STATE.md (evidence).
- DoD:
  - Missing обязательные данные → SAFE_MODE с trace/meta.
  - Валидатор контракта покрыт тестами.
  - `/admin/health` отражает readiness.
  - CI/tests green; запись в `STATE.md` с evidence (Brain/Top Architect).
- Checks:
  - `pytest -q truffles-api/tests/test_minimum_data_contract.py`
  - `pytest -q truffles-api/tests/test_safe_mode_gate.py`
  - `pytest -q truffles-api/tests/test_admin_health.py`
- Evidence:
  - CI run + test logs.
  - decision_trace/decision_meta sample (safe_mode=true).
  - `/admin/health` output.
- Rollback: revert commit; SAFE_MODE gate disabled by config if needed.
- No-go: скрытая деградация (нет trace/meta), новый LLM-оркестр, расширение словарей.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-minimum-data-safe-mode-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-minimum-data-safe-mode-a1`
  - Base: `origin/main`
  - Merge: PR to `main` (code)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: нет явных данных по обязательным полям → нужен Minimum Data Contract из Vertical Pack Kit.
