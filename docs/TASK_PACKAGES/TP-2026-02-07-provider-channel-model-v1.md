# TP-2026-02-07-provider-channel-model-v1

- Название/цель: Зафиксировать Provider/Channel abstraction v1: канонический channel-contract + runtime typed model (enum) для provider gateway inbound/outbound/status.
- Canon refs: `STATE.md` (remaining gap: Provider/Channel abstraction), `SPECS/MULTI_TENANT.md`, `docs/IMPERIUM_DECISIONS.yaml` (DEC-016), `contracts/integrations/provider_inbound.v1.jsonschema`, `contracts/integrations/provider_outbound.v1.jsonschema`, `contracts/events/provider_status.v1.jsonschema`.
- Invariant:
  - tenant_context guards остаются fail-closed.
  - provider gateway inbound/status/outbound не принимают невалидный channel.
  - outbox/provider path не падает exception на невалидном channel (возвращает предсказуемую contract error).
- Scope:
  - Добавить единый typed channel model (enum) в runtime schemas.
  - Применить model в provider gateway pydantic schemas.
  - Обновить provider contracts (jsonschema) для channel enum.
  - Добавить runtime guard в provider outbound payload builder на invalid channel.
  - Обновить/добавить unit tests.
  - Зафиксировать DEC и evidence.
- Out of scope:
  - Полная миграция всех DB channel/text колонок на enum.
  - Новые каналы кроме `whatsapp|telegram|instagram|web`.
  - Provider onboarding/ops automation.
- Touch-list (files/tables):
  - `truffles-api/app/schemas/channel.py` (new)
  - `truffles-api/app/schemas/provider_gateway.py`
  - `truffles-api/app/services/provider_gateway_service.py`
  - `contracts/integrations/provider_inbound.v1.jsonschema`
  - `contracts/integrations/provider_outbound.v1.jsonschema`
  - `contracts/events/provider_status.v1.jsonschema`
  - `truffles-api/tests/test_provider_gateway_inbound.py`
  - `truffles-api/tests/test_provider_gateway_outbound.py`
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `STATE.md`
- Plan:
  1) Ввести shared channel enum schema/model.
  2) Подключить в provider schemas + outbound builder fail-closed guard.
  3) Обновить contracts jsonschema channel enum.
  4) Добавить/обновить тесты на valid/invalid channel.
  5) Прогнать ruff + targeted pytest и зафиксировать evidence.
- DoD:
  - Provider inbound/outbound/status используют typed channel model.
  - Contract schemas ограничивают channel canonical enum.
  - Invalid channel в outbound path возвращает controlled error, не exception.
  - Targeted tests зелёные.
- Checks:
  - `ruff check truffles-api/app/schemas/channel.py truffles-api/app/schemas/provider_gateway.py truffles-api/app/services/provider_gateway_service.py truffles-api/tests/test_provider_gateway_inbound.py truffles-api/tests/test_provider_gateway_outbound.py`
  - `pytest -q truffles-api/tests/test_provider_gateway_inbound.py truffles-api/tests/test_provider_gateway_outbound.py truffles-api/tests/test_provider_gateway_integration.py`
- Evidence:
  - `/tmp/pytest_provider_channel_model_v1_20260207.txt`
  - запись в `STATE.md` NOW + DEC запись в `docs/IMPERIUM_DECISIONS.yaml`.
- Rollback:
  - revert touch-files commit в PR.
- No-go:
  - Не ослаблять tenant_context contract.
  - Не добавлять новый канал без DEC/contract.
  - Не трогать orchestration в `_legacy.py`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-provider-channel-model-v1-a13`
  - Worktree: `/home/zhan/worktrees/2026-02-07-provider-channel-model-v1-a13`
  - Base: `origin/main`
  - Merge policy: PR в `main` после green CI.
  - Cleanup: `scripts/session_end.sh --status done` после merge.
- Риски/блокеры:
  - Возможны legacy payloads с non-canonical channel; будут explicit reject.
