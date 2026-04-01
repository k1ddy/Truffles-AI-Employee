# File Analysis: `truffles-api/tests/test_provider_gateway_integration.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file is direct integration coverage for provider-status update logic plus the real `webhook.outbox` transport helper module: `truffles-api/tests/test_provider_gateway_integration.py:10`, `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:62`, `truffles-api/tests/test_provider_gateway_integration.py:129`.
- `FACT`: The file imports `app.routers.webhook.outbox` directly as `outbox_router` instead of using the package export `app.routers.webhook._process_outbox_rows`: `truffles-api/tests/test_provider_gateway_integration.py:13`.
- `INFERENCE`: This is the clearest repo-backed proof that direct-module testing already exists for the real outbox helper implementation.

## 2. Why This File Exists
- `FACT`: The file validates provider-status tenant enforcement and the live behavior of `_process_outbox_rows(...)` across provider selection, tenant-context rejection, and billing-blocked transport degradation paths: `truffles-api/tests/test_provider_gateway_integration.py:62`, `truffles-api/tests/test_provider_gateway_integration.py:84`, `truffles-api/tests/test_provider_gateway_integration.py:129`, `truffles-api/tests/test_provider_gateway_integration.py:258`, `truffles-api/tests/test_provider_gateway_integration.py:496`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only visible caller.
- `FACT`: The direct helper under test is `app.routers.webhook.outbox._process_outbox_rows(...)`: `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:184`, `truffles-api/tests/test_provider_gateway_integration.py:560`.

## 4. Control Path Owned By This File
- `FACT`: The file pins the direct implementation contract for `_process_outbox_rows(...)` without going through `app.routers.webhook.__init__` or `decision.py`: `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:184`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`.
- `INFERENCE`: This makes the remaining package-export chain look like compatibility debt, not a testing necessity.

## 5. Data Reads
- `FACT`: The file reads real `OutboxMessage`, `Conversation`, `ProviderStatus`, and direct helper exports from `webhook.outbox`: `truffles-api/tests/test_provider_gateway_integration.py:9`, `truffles-api/tests/test_provider_gateway_integration.py:11`, `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:14`.

## 6. Data Writes And Side Effects
- `FACT`: The tests monkeypatch direct module dependencies such as `ProviderGatewayAdapter.send_text`, `mark_outbox_status`, `record_outbox_latency`, and legacy lookup helpers to observe the direct helper behavior: `truffles-api/tests/test_provider_gateway_integration.py:178`, `truffles-api/tests/test_provider_gateway_integration.py:179`, `truffles-api/tests/test_provider_gateway_integration.py:180`, `truffles-api/tests/test_provider_gateway_integration.py:181`, `truffles-api/tests/test_provider_gateway_integration.py:182`, `truffles-api/tests/test_provider_gateway_integration.py:303`, `truffles-api/tests/test_provider_gateway_integration.py:553`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No semantic authority is involved here.
- `FACT`: The file pins deterministic transport, tenant-contract, and delivery-degradation behavior of the outbox helper: `truffles-api/tests/test_provider_gateway_integration.py:258`, `truffles-api/tests/test_provider_gateway_integration.py:319`, `truffles-api/tests/test_provider_gateway_integration.py:381`, `truffles-api/tests/test_provider_gateway_integration.py:436`, `truffles-api/tests/test_provider_gateway_integration.py:496`.

## 8. Truth Carriers Touched Here
- `FACT`: The file asserts outbox status/meta and transport result counters, not semantic truth carriers: `truffles-api/tests/test_provider_gateway_integration.py:79`, `truffles-api/tests/test_provider_gateway_integration.py:316`, `truffles-api/tests/test_provider_gateway_integration.py:564`.

## 9. Violations Against The Target Canon
- `FACT`: The file still patches `_legacy` lookup helpers indirectly through the direct outbox module path: `truffles-api/tests/test_provider_gateway_integration.py:12`, `truffles-api/tests/test_provider_gateway_integration.py:181`, `truffles-api/tests/test_provider_gateway_integration.py:182`.
- `INFERENCE`: The direct module coverage is good evidence for helper ownership, but it also proves the helper still depends on legacy lookup seams.

## 10. Salvageable Parts
- `FACT`: Direct-module coverage of `_process_outbox_rows(...)` is highly salvageable because it already tests the real helper without package-export indirection: `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:184`, `truffles-api/tests/test_provider_gateway_integration.py:560`.
- `FACT`: The tenant-context and provider-degradation checks are reusable as transport-boundary contract coverage: `truffles-api/tests/test_provider_gateway_integration.py:258`, `truffles-api/tests/test_provider_gateway_integration.py:319`, `truffles-api/tests/test_provider_gateway_integration.py:381`, `truffles-api/tests/test_provider_gateway_integration.py:436`, `truffles-api/tests/test_provider_gateway_integration.py:496`.

## 11. Demotion / Removal Candidates
- `INFERENCE`: No direct-module coverage in this file needs demotion. The demotion pressure belongs to the package export and `decision.py` wrapper seams around the helper, not to this direct test.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The repo already has a stable direct test surface for the real outbox transport helper module.
- `INFERENCE`: This weakens any argument that `app.routers.webhook._process_outbox_rows` or `decision._process_outbox_rows(...)` must stay for testability.

## 13. Open Questions
- `UNKNOWN`: Whether the remaining `_legacy` lookup dependency inside `webhook.outbox` can be replaced with narrower direct helpers without breaking these transport contracts.
