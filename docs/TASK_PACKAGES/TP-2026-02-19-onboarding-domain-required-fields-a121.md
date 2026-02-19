# TP-2026-02-19-onboarding-domain-required-fields-a121

- Название/цель: Убрать cross-niche блокер в onboarding minimum-data gate: beauty-специфичные поля должны быть обязательны только для соответствующих доменов, при этом fail-closed поведение для неизвестного домена сохраняется.
- Canon refs: `AGENTS.md`, `STATE.md` (GAP: legacy required pack fields для onboarding), `SPECS/VERTICAL_PACK_KIT.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Не ослаблять hard go/no-go gate и policy required fields.
  - Не вводить demo-specific hardcode.
  - Сохранить fail-closed режим для неизвестного/пустого `domain_slug`.
- Scope:
  - Domain-scoped required fields в `knowledge_validation`.
  - Синхронизация onboarding intake/scorecard через существующий `get_required_fields_for_domain`.
  - Unit tests для подтверждения cross-domain поведения (beauty vs legal/ecom).
- Out of scope:
  - DB миграции.
  - Редизайн Provisioning Wizard.
  - Изменение runtime decision flow вне minimum-data validation.
- Touch-list:
  - `truffles-api/app/services/knowledge_validation.py`
  - `truffles-api/tests/test_knowledge_validation.py`
  - `truffles-api/tests/test_onboarding_intake_service.py`
  - `truffles-api/tests/test_minimum_data_contract.py`
- Plan:
  1) Зафиксировать domain-specific набор обязательных полей и fail-closed default profile.
  2) Обновить minimum-data вычисление так, чтобы домен учитывался в required fields.
  3) Добавить/обновить тесты для legal/ecom (без beauty-only полей) и beauty (без регрессии).
  4) Прогнать целевые тесты и подтвердить отсутствие регрессий onboarding/intake.
- DoD:
  - `get_missing_required_fields(..., domain_slug="legal")` не требует beauty-only полей (`guest_policy`, `safety.medical_note`, `pricing.price_from_reason`, `quality.expectations_photo`) по умолчанию.
  - Для `domain_slug="beauty"` эти поля остаются обязательными.
  - Для неизвестного/пустого домена сохраняется fail-closed профиль.
  - Целевые тесты green.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/knowledge_validation.py`
  - `pytest -q truffles-api/tests/test_knowledge_validation.py`
  - `pytest -q truffles-api/tests/test_onboarding_intake_service.py -k "legal or booking"`
  - `pytest -q truffles-api/tests/test_minimum_data_contract.py`
- Evidence:
  - Вывод целевых `pytest` команд.
  - Diff по `knowledge_validation` + тестам.
- Rollback:
  - `git revert SHA_DOMAIN_REQUIRED_FIELDS` после merge.
- No-go:
  - Не делать bypass go-live/document ingestion.
  - Не удалять policy required fields.
  - Не менять поведение через hardcoded `demo_salon`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-19-onboarding-domain-required-fields-a121`
  - Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-domain-required-fields-a121`
  - Base: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: `scripts/session_end.sh --status done` в финальном рабочем коммите; удаление worktree/branch после merge
- Риски/блокеры:
  - Возможен drift с reference-pack metadata для non-beauty доменов; если проявится, нужен follow-up на integrity migration.
