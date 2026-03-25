# TP-2026-02-07-pack-runtime-de-demo-a13

- Название/цель: De-demoize pack runtime: убрать прямую зависимость `pack_runtime_service` от `demo_salon_knowledge` и ввести нейтральный adapter/core с сохранением обратной совместимости.
- Canon refs: `STATE.md` (remaining gap: demo-centric resolver/runtime), `SPECS/MULTI_TENANT.md`, `AGENTS.md` (P0/P1), `docs/IMPERIUM_DECISIONS.yaml` (DEC-016/DEC-024).
- Invariant:
  - FACT/COLLECT/HANDOFF поведение и trace/meta не деградируют.
  - Existing runtime pack entrypoints (`get_pack_*`) остаются совместимыми.
  - Backward compatibility для `DemoSalonDecision`/legacy imports сохранена.
- Scope:
  - Ввести нейтральные runtime types (`PackDecision`).
  - Ввести нейтральный default adapter module для pack-runtime.
  - Переписать `pack_runtime_service` как adapter facade без прямого импорта `demo_salon_knowledge`.
  - Сохранить back-compat aliases.
  - Добавить targeted tests на adapter facade + back-compat.
- Out of scope:
  - Полный перенос логики из `demo_salon_knowledge.py` в новую доменную реализацию.
  - Изменение бизнес-правил policy/booking.
  - Onboarding/tenant isolation/DB changes.
- Touch-list (files/tables):
  - `truffles-api/app/services/pack_runtime_types.py` (new)
  - `truffles-api/app/services/pack_runtime_default.py` (new)
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/tests/test_pack_runtime_service.py` (new)
  - `truffles-api/tests/test_policy_handler_runtime.py` (if needed for compatibility)
  - `STATE.md`
- Plan:
  1) Вынести нейтральный тип `PackDecision`.
  2) Ввести default adapter module (neutral name) поверх текущего demo implementation.
  3) Перевести `pack_runtime_service` на adapter facade + compatibility aliases.
  4) Добавить тесты adapter delegation/back-compat.
  5) Прогнать checks, обновить `STATE.md` evidence, открыть PR.
- DoD:
  - `pack_runtime_service.py` не импортирует `demo_salon_knowledge` напрямую.
  - Runtime API (`get_pack_*`, helper functions, `PackDecision`) доступен через neutral facade.
  - Existing imports `DemoSalonDecision` не ломаются.
  - Targeted tests зелёные.
- Checks:
  - `ruff check truffles-api/app/services/pack_runtime_types.py truffles-api/app/services/pack_runtime_default.py truffles-api/app/services/pack_runtime_service.py truffles-api/app/services/demo_salon_knowledge.py truffles-api/tests/test_pack_runtime_service.py`
  - `pytest -q truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_knowledge_runtime.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "consult_pack_flow_records_trace_and_meta or consult_snapshot_shadow_disabled"`
- Evidence:
  - `/tmp/pytest_pack_runtime_de_demo_20260207.txt`
  - запись в `STATE.md` NOW с путями к коду/тестам.
- Rollback:
  - revert commit в PR.
- No-go:
  - Не ослаблять tenant/provider contracts.
  - Не менять `_legacy.py` orchestration.
  - Не менять бизнес-policy ради прохождения тестов.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-pack-runtime-de-demo-a13`
  - Worktree: `/home/zhan/worktrees/2026-02-07-pack-runtime-de-demo-a13`
  - Base: `origin/main`
  - Merge policy: PR в `main` после green checks.
  - Cleanup: `scripts/session_end.sh --status done` после merge.
- Риски/блокеры:
  - Возможны скрытые импорты на `DemoSalonDecision` в тестах/маршрутах; держим alias для совместимости.
