# File Analysis: `truffles-api/app/outbox_service_app.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `app/outbox_service_app.py` is a separate FastAPI composition root for the dedicated outbox worker service. It mounts `app.routers.outbox_service.router`, not the main webhook/router stack: `truffles-api/app/outbox_service_app.py:7`, `truffles-api/app/outbox_service_app.py:8`, `truffles-api/app/outbox_service_app.py:12`, `truffles-api/app/outbox_service_app.py:18`.
- `FACT`: The file exposes only `/health` plus whatever `outbox_service.router` mounts; it contains no semantic runtime logic: `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/outbox_service_app.py:27`.
- `INFERENCE`: This is a deployment/worker entrypoint, not a semantic or user-facing ingress surface.

## 2. Why This File Exists
- `FACT`: The file exists to boot a dedicated outbox-processing service with its own FastAPI app metadata and health endpoint: `truffles-api/app/outbox_service_app.py:12`, `truffles-api/app/outbox_service_app.py:13`, `truffles-api/app/outbox_service_app.py:14`, `truffles-api/app/outbox_service_app.py:27`.

## 3. Active Callers And Entrypoints
- `FACT`: `tests/test_outbox_service_app.py` imports this app directly and exercises `/health` plus `/outbox/process`: `truffles-api/tests/test_outbox_service_app.py:9`, `truffles-api/tests/test_outbox_service_app.py:14`, `truffles-api/tests/test_outbox_service_app.py:29`, `truffles-api/tests/test_outbox_service_app.py:69`.
- `UNKNOWN`: Which deployment/runtime process currently launches `app.outbox_service_app` outside repo tests.

## 4. Control Path Owned By This File
- `FACT`: The worker control path here is `app.outbox_service_app -> outbox_service.router -> outbox_service.process_outbox(...) -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/routers/outbox_service.py:40`, `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `INFERENCE`: This file keeps one half of the duplicated live outbox entrypoint family alive.

## 5. Data Reads
- `FACT`: The file reads env state only for `/health` reporting through `_is_env_enabled(...)` and `OUTBOX_SERVICE_ENABLED`: `truffles-api/app/outbox_service_app.py:21`, `truffles-api/app/outbox_service_app.py:27`, `truffles-api/app/outbox_service_app.py:33`.

## 6. Data Writes And Side Effects
- `FACT`: The file itself only mounts the router and returns health payload; all outbox-processing side effects are delegated to `outbox_service.py`: `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/outbox_service_app.py:29`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: There is no semantic authority here.
- `FACT`: The file owns only worker-app composition and a simple env-derived health response: `truffles-api/app/outbox_service_app.py:12`, `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/outbox_service_app.py:27`.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carriers are introduced here; the file exposes only operational health state (`status`, `service`, `outbox_enabled`): `truffles-api/app/outbox_service_app.py:29`, `truffles-api/app/outbox_service_app.py:31`, `truffles-api/app/outbox_service_app.py:32`.

## 9. Violations Against The Target Canon
- `FACT`: The file is a separate operational entrypoint for the same outbox-processing flow that is also exposed from the mounted admin router: `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/routers/admin.py:513`, `truffles-api/app/main.py:109`.
- `INFERENCE`: The issue is not semantic ownership, but duplicated operational entrypoints around the same helper chain.

## 10. Salvageable Parts
- `FACT`: The dedicated service-app wrapper and its health endpoint are salvageable if the system still needs a separate worker process boundary: `truffles-api/app/outbox_service_app.py:12`, `truffles-api/app/outbox_service_app.py:18`, `truffles-api/app/outbox_service_app.py:27`.

## 11. Demotion / Removal Candidates
- `UNKNOWN`: Whether this separate app should remain once the duplicated admin outbox path is fully mapped.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The `_process_outbox_rows` export seam is preserved by a real second app boundary, not just by tests.
- `INFERENCE`: Outbox duplication is partly deployment-surface debt, not only package-export debt.

## 13. Open Questions
- `UNKNOWN`: Whether this separate worker app is still required in production or only legacy/shadow infrastructure.
