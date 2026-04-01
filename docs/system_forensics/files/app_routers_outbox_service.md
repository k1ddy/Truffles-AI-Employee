# File Analysis: `truffles-api/app/routers/outbox_service.py`

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
- `FACT`: `outbox_service.py` is a dedicated `/outbox/process` worker endpoint, not part of the main public app router. It is mounted by `app.outbox_service_app`, not by `app.main`: `truffles-api/app/routers/outbox_service.py:40`, `truffles-api/app/outbox_service_app.py:8`, `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/main.py:101`, `truffles-api/app/main.py:104`.
- `FACT`: The endpoint performs operational orchestration only: release stale processing, schedule inbound syncs, claim batches, call `_process_outbox_rows(...)`, and run reminder jobs: `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:64`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/outbox_service.py:79`.
- `INFERENCE`: This file is a live operational caller surface that keeps the package export `_process_outbox_rows` alive.

## 2. Why This File Exists
- `FACT`: The file provides a token-gated, env-gated worker endpoint for processing pending outbox batches outside the main app process: `truffles-api/app/routers/outbox_service.py:24`, `truffles-api/app/routers/outbox_service.py:28`, `truffles-api/app/routers/outbox_service.py:41`.
- `INFERENCE`: Architecturally it exists as a transport/worker entrypoint, not as a semantic runtime surface.

## 3. Active Callers And Entrypoints
- `FACT`: `app.outbox_service_app` is the visible mounting entrypoint for this router: `truffles-api/app/outbox_service_app.py:8`, `truffles-api/app/outbox_service_app.py:18`.
- `FACT`: `tests/test_outbox_service_app.py` exercises the mounted endpoint through `TestClient(app)`: `truffles-api/tests/test_outbox_service_app.py:9`, `truffles-api/tests/test_outbox_service_app.py:13`, `truffles-api/tests/test_outbox_service_app.py:40`.
- `FACT`: The same operational flow is duplicated in `admin.py`, which also imports `app.routers.webhook._process_outbox_rows`: `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/admin.py:544`.
- `UNKNOWN`: Which deployment path actually invokes `app.outbox_service_app` in production.

## 4. Control Path Owned By This File
- `FACT`: The live worker path here is `outbox_service_app -> outbox_service.process_outbox(...) -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/routers/outbox_service.py:40`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/decision.py:8576`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `INFERENCE`: The remaining `_process_outbox_rows` package-export chain is not test-only; it is on a live worker/control path.

## 5. Data Reads
- `FACT`: The file reads env switches and worker limits (`OUTBOX_SERVICE_ENABLED`, token, batch limits, retry settings, stale-processing window): `truffles-api/app/routers/outbox_service.py:24`, `truffles-api/app/routers/outbox_service.py:28`, `truffles-api/app/routers/outbox_service.py:45`, `truffles-api/app/routers/outbox_service.py:49`.
- `FACT`: It reads pending work from `claim_pending_outbox_batches(...)` and inbound sync/reminder services: `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:64`, `truffles-api/app/routers/outbox_service.py:79`.

## 6. Data Writes And Side Effects
- `FACT`: The endpoint triggers stale-processing release, inbound sync scheduling, outbox row processing, and reminder-job execution as side effects: `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/outbox_service.py:79`.
- `FACT`: It also exposes operational result counters in the HTTP response (`calendar_inbound`, `reminder_jobs`, `released_stale`, `failed_stale`): `truffles-api/app/routers/outbox_service.py:80`, `truffles-api/app/routers/outbox_service.py:84`, `truffles-api/app/routers/outbox_service.py:86`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: This file does not own semantic meaning for user turns.
- `FACT`: It does own deterministic worker gating and orchestration order around `_process_outbox_rows(...)`: `truffles-api/app/routers/outbox_service.py:41`, `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:71`.
- `INFERENCE`: It is operational authority, not semantic authority.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carrier is created here. The file only passes operational counters and delegated processing results through the HTTP response: `truffles-api/app/routers/outbox_service.py:73`, `truffles-api/app/routers/outbox_service.py:79`, `truffles-api/app/routers/outbox_service.py:86`.

## 9. Violations Against The Target Canon
- `FACT`: The file imports `_process_outbox_rows` from the webhook package export rather than from the direct helper module: `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The same operational endpoint logic is duplicated in `admin.py`: `truffles-api/app/routers/outbox_service.py:45`, `truffles-api/app/routers/admin.py:519`, `truffles-api/app/routers/admin.py:542`.
- `INFERENCE`: This slice still preserves avoidable compatibility/duplication debt even though the actual transport helper already lives in `webhook/outbox.py`.

## 10. Salvageable Parts
- `FACT`: The dedicated worker gate (`OUTBOX_SERVICE_ENABLED` + token enforcement) is reusable as a bounded transport-service boundary: `truffles-api/app/routers/outbox_service.py:24`, `truffles-api/app/routers/outbox_service.py:28`, `truffles-api/app/routers/outbox_service.py:41`.
- `FACT`: The orchestration order around stale release, claim, process, reminder jobs, and result aggregation is reusable if it is rewired onto a direct helper import: `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/outbox_service.py:79`.

## 11. Demotion / Removal Candidates
- `FACT`: The package-export import seam `from app.routers.webhook import _process_outbox_rows` is a demotion candidate once callers move to a direct helper module: `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The duplicated admin-side `/outbox/process` flow is another demotion/consolidation candidate: `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:542`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The `_process_outbox_rows` export chain is still live because a real worker endpoint uses it, not just tests.
- `INFERENCE`: The remaining debt in this slice is live caller-surface duplication and package-export compatibility, not hidden semantic authority.

## 13. Open Questions
- `UNKNOWN`: Whether the separate outbox service app is still required as a product deployment surface or can converge with the admin endpoint.
- `UNKNOWN`: Whether callers can move directly to `app.routers.webhook.outbox._process_outbox_rows(...)` without preserving the package export.
