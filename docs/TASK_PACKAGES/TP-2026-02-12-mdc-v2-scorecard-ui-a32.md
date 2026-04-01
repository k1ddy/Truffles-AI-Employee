# TP-2026-02-12 Minimum Data Contract v2 + Scorecard UI (a32)

## Название/цель
Реализовать `Minimum Data Contract v2` в формате `domain_slug-first` (beauty как эталон + generic template), перевести readiness на строгий контракт полноты данных и вывести onboarding scorecard в Console UI с hard-stop в autopilot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Go-live и activation остаются fail-closed.
- `demo_salon` остается канарейкой, runtime core не фиксируется на demo-only данных.
- Existing onboarding endpoints не теряют обратную совместимость по контрактам API.

## Scope
- Добавить `minimum_data_contract.v2` с domain profile (`beauty`, `generic`) и строгой проверкой required fields.
- Перевести server readiness calculations на v2 contract.
- Добавить hard-stop в onboarding autopilot при fail scorecard.
- Показать scorecard в Console provisioning UI и блокировать действия при `status=fail`.
- Добавить/обновить backend/frontend tests.

## Out of scope
- Полная миграция всех legacy `/admin/*` в CI/runbooks.
- Расширение доменных профилей beyond `beauty` + `generic`.
- Редизайн других Console страниц вне onboarding/provisioning.

## Touch-list
- `truffles-api/app/services/knowledge_validation.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/services/onboarding_intake_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_minimum_data_contract.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `console-web/src/app/settings/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.d.ts` (if required by contract usage)
- `console-web` tests for settings/provisioning flow (if present)

## Plan
1. Проанализировать текущий MDC/readiness и спроектировать v2 domain profiles.
2. Имплементировать backend v2 contract и wiring в onboarding readiness.
3. Добавить autopilot hard-stop по scorecard fail.
4. Имплементировать scorecard блок в Console Settings/Provisioning UI.
5. Добавить/обновить тесты и прогнать целевой validation suite.

## DoD
- Readiness опирается на `minimum_data_contract.v2` профили, а не на salon-legacy aliases как primary oracle.
- Autopilot не активирует/не продолжает flow при scorecard fail, возвращает явные missing причины.
- UI показывает scorecard pass/fail + missing и блокирует действия, пока fail.
- Таргетные backend/frontend тесты проходят.

## Checks
- `ruff check` для измененных backend файлов.
- `pytest -q truffles-api/tests/test_minimum_data_contract.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
- дополнительные таргетные тесты по onboarding/intake при необходимости.
- `npm --prefix console-web run test -- --runInBand` (или таргетные tests, если есть).
- `bash scripts/doc_truth_gate.sh`

## Evidence
- Логи pytest/frontend test runs.
- DIFF по backend readiness + autopilot gate.
- Скрин/лог API payload scorecard в UI flow (через тесты).

## Rollback
- `git revert` коммита PR.

## No-go
- Не ослаблять fail-closed gate до warning-only.
- Не вводить demo-only hardcode в generic/domain-neutral контур.
- Не менять unrelated runtime routing.

## Риски/блокеры
- Возможный контрактный дрейф фронтенд-типов, если потребуется регенерация API types.
