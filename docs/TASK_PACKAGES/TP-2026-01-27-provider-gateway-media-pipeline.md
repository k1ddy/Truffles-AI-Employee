# TP-2026-01-27 — Provider Gateway Media Pipeline (Canary)

- Название/цель: включить outbound media pipeline через Provider Gateway (signed URL + TTL + async outbox) на canary demo_salon без изменения core-поведения.
- Canon refs: `AGENTS.md`, `STATE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `TECH.md`, `contracts/integrations/media_send.v1.jsonschema`.
- Invariant:
  - Hard-LAW/policy/pending остаются fail-closed до LLM.
  - tenant_context обязателен для outbound media.
  - outbox idempotency и trace/meta не ломаются.
  - media send не блокирует webhook (async, outbox-only).
- Scope:
  - Provider Gateway outbound media payload + metadata (signed_url/TTL).
  - Outbox media event uses Provider Gateway when enabled (canary env-gate).
  - Tests for media payload + gateway adapter.
  - Evidence: live-check or simulated outbox with trace/meta.
- Out of scope:
  - Inbound media via Provider Gateway.
  - Полный cutover всего трафика на gateway.
  - Новые провайдеры кроме ChatFlow.
- Touch-list:
  - `truffles-api/app/adapters/provider_gateway.py`
  - `truffles-api/app/services/provider_gateway_service.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/services/manager_message_service.py`
  - `contracts/integrations/media_send.v1.jsonschema`
  - `truffles-api/tests/test_provider_gateway_outbound.py`
  - `truffles-api/tests/test_outbox_media_gateway.py` (new, if needed)
  - `TECH.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Plan:
  1) Map current media outbox path and ensure tenant_context + signed_url/TTL are passed when gateway enabled.
  2) Extend gateway payload builder/tests to validate media_send fields and error paths.
  3) Wire outbox media event to gateway adapter with media_meta (signed_url/TTL) and keep ChatFlow fallback.
  4) Add/adjust tests for media payload and outbox gateway integration.
  5) Live-check (preferred) or simulated outbox send with trace/meta evidence.
  6) Update docs/STATE with evidence.
- DoD:
  - Outbox media events route to Provider Gateway when enabled and include signed_url + TTL.
  - tenant_context present in outbound payload.
  - Tests green for gateway media payload paths.
  - Evidence recorded in `STATE.md`.
- Checks:
  - `pytest -q truffles-api/tests/test_provider_gateway_outbound.py`
  - `pytest -q truffles-api/tests/test_outbox_media_gateway.py` (if added)
- Evidence:
  - Live-check or simulated outbox run (trace bundle + outbox status) captured in `STATE.md`.
- Rollback:
  - Disable `PROVIDER_GATEWAY_OUTBOUND_ENABLED` or revert PR.
- No-go:
  - Media send without signed URL/TTL.
  - Missing tenant_context in outbound media payload.
- Риски/блокеры:
  - Нет доступного канала для live media-check (Telegram manager media) → разрешить simulated inbound/outbox.
- Branch / Worktree:
  - Branch: `feat/2026-01-27-provider-gateway-media-pipeline-arch`
  - Worktree: `/home/zhan/worktrees/2026-01-27-provider-gateway-media-pipeline-arch`
  - Base ref: `origin/main`
  - Merge policy: merge commit, no rebase
  - Cleanup: удалить ветку и worktree после merge (Brain/Top Architect)
