# Console Onboarding Wave 1+2 Report (2026-02-17)

## Summary

Реализованы шаги `1` и `2`:

1. Контракт и UI для `onboarding_autopilot` синхронизированы с новыми полями intake:
   - `field_states[]`
   - `question_queue[]`
2. Добавлен `Document Ingestion Gate` в scorecard/go-no-go:
   - scorecard API теперь отдает `document_ingestion`.
   - при `knowledge_upload=true` и невалидном ingestion в missing добавляется `document_ingestion_invalid`.

## Key Changes

- Backend:
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
- Tests:
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
- Contract:
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/types/api.generated.ts`
- Console Plane UI:
  - `console-web/src/components/ProvisioningWizard.tsx`

## Verification

- `python3 -m py_compile ...` -> pass
- `ruff check ...` -> pass
- `pytest -q truffles-api/tests/test_console_onboarding_state.py` -> `21 passed`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot"` -> `7 passed`
- `pytest -q truffles-api/tests/test_onboarding_intake_service.py` -> `11 passed`
- `pytest -q truffles-api/tests/test_minimum_data_contract.py truffles-api/tests/test_safe_mode_gate.py` -> `6 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass
- `npm --prefix console-web run generate:api` -> pass
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx` -> pass
- `npm --prefix console-web run build` -> pass

## Result

- Console onboarding теперь показывает не только `missing_fields/questions`, но и статусы подтвержденности данных + приоритетную очередь вопросов.
- Scorecard теперь явно отражает состояние document ingestion и формирует прозрачный блокер для go-live.
