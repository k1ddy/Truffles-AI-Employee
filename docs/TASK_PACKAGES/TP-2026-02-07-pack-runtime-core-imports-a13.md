# TP-2026-02-07-pack-runtime-core-imports-a13

- Название/цель: De-demoization step 2 — убрать прямое использование `DemoSalonDecision` из core webhook модулей и перевести их на нейтральный `PackDecision`/`pack_runtime_service`.
- Canon refs: `STATE.md` (remaining gap: demo-centric runtime coupling), `SPECS/MULTI_TENANT.md`, `AGENTS.md` (P0/P1: no behavior regression, trace/meta intact), `docs/IMPERIUM_DECISIONS.yaml` (DEC-016/DEC-024).
- Invariant:
  - Поведение FACT/COLLECT/HANDOFF, decision_meta/trace и booking/info/policy flow без регрессии.
  - Backward compatibility для legacy imports `DemoSalonDecision` сохранена.
  - Никаких изменений бизнес-правил; только de-coupling import/type-level.
- Scope:
  - Перевести core webhook модули (`policy/booking/info/response`) с `DemoSalonDecision` на `PackDecision` из `pack_runtime_service`.
  - Добавить import-hygiene test, чтобы предотвратить возврат прямого demo type import в core.
  - Обновить `STATE.md` evidence.
- Out of scope:
  - Полный перенос всей логики из `demo_salon_knowledge.py` в новый engine.
  - Onboarding, physical isolation, UI/RBAC функциональные изменения.
  - Изменение content/политик ответов.
- Touch-list (files/tables):
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/tests/test_pack_runtime_import_hygiene.py` (new)
  - `truffles-api/tests/test_message_endpoint.py` (if imports need alignment)
  - `STATE.md`
- Plan:
  1) Найти и заменить direct `DemoSalonDecision` imports/usages в core webhook files на `PackDecision`.
  2) Добавить guard test на import hygiene.
  3) Прогнать targeted lint/tests и зафиксировать evidence.
  4) Обновить `STATE.md`, session log, открыть PR.
- DoD:
  - Core webhook files не импортируют `DemoSalonDecision` из `demo_salon_knowledge`.
  - Core uses `PackDecision` from `pack_runtime_service`.
  - Targeted tests зелёные.
- Checks:
  - `ruff check truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/response.py truffles-api/tests/test_pack_runtime_import_hygiene.py`
  - `pytest -q truffles-api/tests/test_pack_runtime_import_hygiene.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_policy_handler_runtime.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "consult_pack_flow_records_trace_and_meta or consult_snapshot_shadow_disabled"`
- Evidence:
  - `/tmp/pytest_pack_runtime_core_imports_20260207.txt`
  - запись в `STATE.md` NOW.
- Rollback:
  - revert commit в PR.
- No-go:
  - Не менять routing/policy business behavior.
  - Не вносить orchestration в `_legacy.py`.
  - Не трогать onboarding/DB schema.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-pack-runtime-core-imports-a13`
  - Worktree: `/home/zhan/worktrees/2026-02-07-pack-runtime-core-imports-a13`
  - Base: `origin/main`
  - Merge policy: PR -> `main` после green checks.
  - Cleanup: `scripts/session_end.sh --status done` после merge.
- Риски/блокеры:
  - Возможны скрытые места с локальными import внутри функций; покрываем grep + import-hygiene test.
