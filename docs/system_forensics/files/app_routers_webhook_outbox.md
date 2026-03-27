# File Analysis: `truffles-api/app/routers/webhook/outbox.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `webhook/outbox.py` is the actual implementation owner for `_process_outbox_rows(...)`; the package export and the `decision.py` wrapper only delegate into this module: `truffles-api/app/routers/webhook/outbox.py:446`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/decision.py:8576`, `truffles-api/app/routers/webhook/__init__.py:3`.
- `FACT`: The module is a transport/delivery subsystem, not a semantic runtime owner. It validates outbox payloads, enforces tenant context, handles provider delivery, calendar/knowledge sync events, and writes outbox/message metadata: `truffles-api/app/routers/webhook/outbox.py:366`, `truffles-api/app/routers/webhook/outbox.py:660`, `truffles-api/app/routers/webhook/outbox.py:1027`, `truffles-api/app/routers/webhook/outbox.py:1073`, `truffles-api/app/routers/webhook/outbox.py:1149`, `truffles-api/app/routers/webhook/outbox.py:1644`.
- `INFERENCE`: This file is a live operational boundary with direct deterministic authority over outbound delivery and replay behavior.

## 2. Why This File Exists
- `FACT`: The module exists to process outbox rows, handle enqueue-only accept paths, persist skip-persist behavior, and integrate transport/provider/calendar/knowledge side effects around outbound messages: `truffles-api/app/routers/webhook/outbox.py:155`, `truffles-api/app/routers/webhook/outbox.py:252`, `truffles-api/app/routers/webhook/outbox.py:446`.

## 3. Active Callers And Entrypoints
- `FACT`: `_process_outbox_rows(...)` is called through the package-export chain by `outbox_service.py` and `admin.py`: `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/webhook/decision.py:8576`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The module is also used directly inside `decision.py` for `_prepare_skip_persist(...)` and `_handle_enqueue_only_accept(...)`: `truffles-api/app/routers/webhook/decision.py:223`, `truffles-api/app/routers/webhook/outbox.py:155`, `truffles-api/app/routers/webhook/outbox.py:252`.
- `FACT`: Tests already import this module directly as `outbox_router` and exercise `_process_outbox_rows(...)` without going through the package export: `truffles-api/tests/test_provider_gateway_integration.py:13`, `truffles-api/tests/test_provider_gateway_integration.py:184`, `truffles-api/tests/test_outbox_transport_degraded.py:1`, `truffles-api/tests/test_outbox_transport_degraded.py:5`.

## 4. Control Path Owned By This File
- `FACT`: The live outbox processing path terminates here after the compatibility wrapper chain: `outbox_service/admin -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: Inside this function, the module resolves conversation/simulation context, validates payload and tenant contract, chooses provider transport or event handlers, and writes outbox status / retry scheduling: `truffles-api/app/routers/webhook/outbox.py:456`, `truffles-api/app/routers/webhook/outbox.py:660`, `truffles-api/app/routers/webhook/outbox.py:968`, `truffles-api/app/routers/webhook/outbox.py:1027`, `truffles-api/app/routers/webhook/outbox.py:1073`, `truffles-api/app/routers/webhook/outbox.py:1149`, `truffles-api/app/routers/webhook/outbox.py:1626`.

## 5. Data Reads
- `FACT`: The module reads outbox rows, conversations, users, payload JSON, tenant context, transport env switches, and provider-specific payload fields: `truffles-api/app/routers/webhook/outbox.py:456`, `truffles-api/app/routers/webhook/outbox.py:497`, `truffles-api/app/routers/webhook/outbox.py:660`, `truffles-api/app/routers/webhook/outbox.py:1149`.
- `FACT`: It also still reads legacy message lookup helpers through `_legacy` to resolve message/evidence attachment: `truffles-api/app/routers/webhook/outbox.py:221`, `truffles-api/app/routers/webhook/outbox.py:540`, `truffles-api/app/routers/webhook/outbox.py:553`.

## 6. Data Writes And Side Effects
- `FACT`: The module writes outbox status, retry scheduling, transport latency, outbox meta, decision-trace/message meta, and provider/media transport side effects: `truffles-api/app/routers/webhook/outbox.py:570`, `truffles-api/app/routers/webhook/outbox.py:894`, `truffles-api/app/routers/webhook/outbox.py:968`, `truffles-api/app/routers/webhook/outbox.py:996`, `truffles-api/app/routers/webhook/outbox.py:1178`, `truffles-api/app/routers/webhook/outbox.py:1296`, `truffles-api/app/routers/webhook/outbox.py:1644`.
- `FACT`: It can also trigger calendar inbound/outbound sync and knowledge-sync side effects via event payloads: `truffles-api/app/routers/webhook/outbox.py:1027`, `truffles-api/app/routers/webhook/outbox.py:1032`, `truffles-api/app/routers/webhook/outbox.py:1073`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: This file does not decide user semantic meaning.
- `FACT`: It does own deterministic delivery decisions: payload guards, tenant-context contract checks, provider selection, transport degradation classification, retry scheduling, and outbox result counters: `truffles-api/app/routers/webhook/outbox.py:124`, `truffles-api/app/routers/webhook/outbox.py:366`, `truffles-api/app/routers/webhook/outbox.py:660`, `truffles-api/app/routers/webhook/outbox.py:1149`, `truffles-api/app/routers/webhook/outbox.py:1626`.
- `INFERENCE`: This is a legitimate deterministic boundary module, but the caller/export chain around it is still legacy-shaped.

## 8. Truth Carriers Touched Here
- `FACT`: The module writes operational/evidence carriers (`outbox.meta`, message decision metadata, decision trace) rather than semantic truth carriers: `truffles-api/app/routers/webhook/outbox.py:570`, `truffles-api/app/routers/webhook/outbox.py:583`, `truffles-api/app/routers/webhook/outbox.py:894`.

## 9. Violations Against The Target Canon
- `FACT`: The live caller surface still reaches this implementation through `app.routers.webhook.__init__` plus `decision.py` wrapper indirection instead of importing the module directly: `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/admin.py:542`.
- `FACT`: The module still depends on `_legacy` message-lookup helpers for evidence attachment: `truffles-api/app/routers/webhook/outbox.py:221`, `truffles-api/app/routers/webhook/outbox.py:540`, `truffles-api/app/routers/webhook/outbox.py:553`.
- `INFERENCE`: The transport helper itself is salvageable, but the export/caller chain and `_legacy` coupling remain compatibility debt.

## 10. Salvageable Parts
- `FACT`: `_process_outbox_rows(...)` is the right concrete transport-processing anchor for this family: `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: `_classify_transport_degradation(...)`, payload validation, tenant-context validation, and provider/event processing logic are all reusable as bounded transport-delivery helpers: `truffles-api/app/routers/webhook/outbox.py:124`, `truffles-api/app/routers/webhook/outbox.py:366`, `truffles-api/app/routers/webhook/outbox.py:660`, `truffles-api/app/routers/webhook/outbox.py:1027`, `truffles-api/app/routers/webhook/outbox.py:1073`, `truffles-api/app/routers/webhook/outbox.py:1149`.

## 11. Demotion / Removal Candidates
- `FACT`: The `decision.py` wrapper around `_process_outbox_rows(...)` is a demotion target because it only forwards to this module: `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/decision.py:8576`.
- `FACT`: The package export `app.routers.webhook._process_outbox_rows` is another demotion target once callers move to the direct module: `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:6`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The repo already has direct test coverage against the real outbox helper module.
- `INFERENCE`: The remaining package-export chain exists mainly for live caller compatibility and duplication, not because the transport helper itself lacks a stable direct module surface.

## 13. Open Questions
- `UNKNOWN`: Whether `_legacy` message lookup helpers used here can be replaced with narrower direct dependencies.
- `UNKNOWN`: Whether admin and outbox-service callers can collapse onto a shared direct import without preserving the package export seam.
