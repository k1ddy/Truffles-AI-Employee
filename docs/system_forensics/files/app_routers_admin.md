# File Analysis: `truffles-api/app/routers/admin.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `admin.py` is the mounted `/admin` router on the main app: `truffles-api/app/routers/admin.py:30`, `truffles-api/app/main.py:109`.
- `FACT`: Inside that broad admin router, `/admin/outbox/process` duplicates the outbox worker orchestration: it enforces `ALERTS_ADMIN_TOKEN`, releases stale rows, schedules inbound syncs, claims batches, and then imports `app.routers.webhook._process_outbox_rows`: `truffles-api/app/routers/admin.py:172`, `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:527`, `truffles-api/app/routers/admin.py:533`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/admin.py:544`.
- `INFERENCE`: This file is a mixed admin-surface hotspot with an embedded duplicate outbox entrypoint.

## 2. Why This File Exists
- `FACT`: The router exists for prompt/settings/admin maintenance endpoints and general admin operations: `truffles-api/app/routers/admin.py:30`, `truffles-api/app/routers/admin.py:240`, `truffles-api/app/routers/admin.py:309`, `truffles-api/app/routers/admin.py:513`.
- `INFERENCE`: For this forensic family, the important part is that outbox processing is duplicated inside a general-purpose admin router instead of staying isolated to one worker boundary.

## 3. Active Callers And Entrypoints
- `FACT`: The router is mounted in the main public app through `app.main`: `truffles-api/app/main.py:109`.
- `FACT`: Visible repo coverage for the admin router is `tests/test_admin_legacy_auth.py`, but that file only covers prompt/settings/heal/public health/version guards and does not visibly exercise `/admin/outbox/process`: `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:36`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/tests/test_admin_legacy_auth.py:66`, `truffles-api/tests/test_admin_legacy_auth.py:78`.
- `INFERENCE`: The duplicated admin outbox path is live via the mounted app, but visible repo contract coverage for that specific route is weak or absent.

## 4. Control Path Owned By This File
- `FACT`: The admin outbox path is `app.main -> admin.router -> process_outbox(...) -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/app/main.py:109`, `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The orchestration body is materially duplicated from `app/routers/outbox_service.py`: both endpoints read the same env limits and call the same stale-release / inbound-sync / claim / `_process_outbox_rows(...)` sequence: `truffles-api/app/routers/admin.py:519`, `truffles-api/app/routers/admin.py:527`, `truffles-api/app/routers/admin.py:533`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/outbox_service.py:45`, `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:71`.

## 5. Data Reads
- `FACT`: The outbox admin path reads `ALERTS_ADMIN_TOKEN`, the same outbox env limits/backoff settings as `outbox_service.py`, and pending outbox batches from the DB services: `truffles-api/app/routers/admin.py:172`, `truffles-api/app/routers/admin.py:519`, `truffles-api/app/routers/admin.py:527`, `truffles-api/app/routers/admin.py:533`.

## 6. Data Writes And Side Effects
- `FACT`: The outbox admin path triggers stale-release, inbound sync scheduling, outbox row processing, and result aggregation side effects just like the dedicated worker endpoint: `truffles-api/app/routers/admin.py:527`, `truffles-api/app/routers/admin.py:533`, `truffles-api/app/routers/admin.py:544`, `truffles-api/app/routers/admin.py:550`, `truffles-api/app/routers/admin.py:552`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file is not a semantic owner.
- `FACT`: The outbox admin route is deterministic operational authority: token-gated orchestration over outbox processing using the same helper/export chain as the worker service: `truffles-api/app/routers/admin.py:172`, `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:542`.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carrier is introduced here; the outbox admin route only passes operational result counters and stale-release summaries through the HTTP response: `truffles-api/app/routers/admin.py:544`, `truffles-api/app/routers/admin.py:550`, `truffles-api/app/routers/admin.py:552`.

## 9. Violations Against The Target Canon
- `FACT`: `/admin/outbox/process` duplicates the worker orchestration already present in `app/routers/outbox_service.py`: `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/outbox_service.py:40`.
- `FACT`: The route still depends on the same compatibility export seam `from app.routers.webhook import _process_outbox_rows`: `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`.
- `INFERENCE`: The debt here is duplicate operational entrypoints plus wrapper/export indirection, not semantic ambiguity.

## 10. Salvageable Parts
- `FACT`: `_require_admin_token(...)` is a reusable bounded admin-guard helper for mounted admin routes: `truffles-api/app/routers/admin.py:172`.
- `FACT`: If admin-triggered outbox processing is still required, the route can remain as a thin trigger wrapper once duplicated orchestration is collapsed to one shared boundary: `truffles-api/app/routers/admin.py:513`, `truffles-api/app/routers/admin.py:544`.

## 11. Demotion / Removal Candidates
- `FACT`: The duplicated orchestration body inside `/admin/outbox/process` is a demotion/consolidation candidate because it duplicates `outbox_service.py` almost line-for-line: `truffles-api/app/routers/admin.py:519`, `truffles-api/app/routers/admin.py:527`, `truffles-api/app/routers/admin.py:533`, `truffles-api/app/routers/admin.py:542`, `truffles-api/app/routers/outbox_service.py:45`, `truffles-api/app/routers/outbox_service.py:51`, `truffles-api/app/routers/outbox_service.py:58`, `truffles-api/app/routers/outbox_service.py:71`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The `_process_outbox_rows` wrapper/export seam is preserved by the mounted admin app too, not only by the separate outbox service app.
- `INFERENCE`: The remaining blocker in this family is now clearly duplicated live entrypoints plus thin-wrapper absence, not uncertainty about the underlying helper owner.

## 13. Open Questions
- `UNKNOWN`: Whether `/admin/outbox/process` is still required as a product/admin operation once the dedicated outbox service exists.
- `UNKNOWN`: Whether the missing visible repo coverage for `/admin/outbox/process` is intentional or stale test debt.
