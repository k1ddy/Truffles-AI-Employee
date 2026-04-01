# File Analysis: `truffles-api/app/routers/webhook/__init__.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: The package explicitly declares itself as a minimal export surface for the single-runtime ingress and exports only `router` and `_process_outbox_rows`: `truffles-api/app/routers/webhook/__init__.py:1`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:4`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `INFERENCE`: This file is the canonical proof that the package surface was intentionally narrowed after the old megafile era.

## 2. Why This File Exists
- `FACT`: It exists to present a tiny public package surface while the underlying webhook implementation lives in submodules: `truffles-api/app/routers/webhook/__init__.py:1`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:4`.
- `INFERENCE`: The file tries to enforce a clean package contract even though tests and compatibility files still reference broader historical surfaces.

## 3. Active Callers And Entrypoints
- `FACT`: `app.main` consumes `webhook.router` from this package and mounts it on the live FastAPI app: `truffles-api/app/main.py:26`, `truffles-api/app/main.py:37`, `truffles-api/app/main.py:104`.
- `FACT`: `app/routers/outbox_service.py` imports `_process_outbox_rows` directly from this package on a live service path: `truffles-api/app/routers/outbox_service.py:71`, `truffles-api/app/routers/outbox_service.py:73`.
- `FACT`: Multiple tests import the package itself via `from app.routers import webhook`, including `test_booking_chaos_dialogs.py`, `test_webhook_response.py`, `test_webhook_booking.py`, and `test_webhook_dedup.py`: `truffles-api/tests/test_booking_chaos_dialogs.py:1`, `truffles-api/tests/test_webhook_response.py:4`, `truffles-api/tests/test_webhook_booking.py:3`, `truffles-api/tests/test_webhook_dedup.py:7`.

## 4. Control Path Owned By This File
- `FACT`: The file owns package-level export control only; it does not route requests itself: `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:4`, `truffles-api/app/routers/webhook/__init__.py:6`.
- `INFERENCE`: Its real architectural importance is contract control: which names the repo treats as public package surface.

## 5. Data Reads
- `FACT`: None beyond importing `decision._process_outbox_rows` and `http.router`: `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/__init__.py:4`.

## 6. Data Writes And Side Effects
- `FACT`: The file writes the package public namespace through `__all__`: `truffles-api/app/routers/webhook/__init__.py:6`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file has no semantic or deterministic routing authority beyond package export control: `truffles-api/app/routers/webhook/__init__.py:6`.
- `INFERENCE`: That export control matters because stale test surfaces still assume the package exposes far more than it actually does.

## 8. Truth Carriers Touched Here
- `FACT`: No truth carriers are created or mutated here.

## 9. Violations Against The Target Canon
- `FACT`: The package contract is already narrow, but repo tests still expect old helper names on the package object, such as `_buffer_user_message`, `_maybe_append_booking_cta`, `_get_expected_reply_type`, and `_handle_webhook_payload`: `truffles-api/app/routers/webhook/__init__.py:6`, `truffles-api/tests/test_webhook_dedup.py:56`, `truffles-api/tests/test_webhook_response.py:13`, `truffles-api/tests/test_webhook_booking.py:12`, `truffles-api/tests/test_booking_chaos_dialogs.py:6`.
- `INFERENCE`: The remaining violation is not inside this file; it is repo-contract drift between the narrowed package surface and stale test expectations.

## 10. Salvageable Parts
- `FACT`: The minimal package surface itself is salvageable and aligned with cutover goals: `truffles-api/app/routers/webhook/__init__.py:1`, `truffles-api/app/routers/webhook/__init__.py:6`.

## 11. Demotion / Removal Candidates
- `INFERENCE`: The demotion targets are stale caller/test assumptions around this package, not the file's current contents.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The active package contract is already small: `router` for ingress and `_process_outbox_rows` for outbox replay.
- `INFERENCE`: This narrows the remaining cutover question to repo callers and tests that still preserve broader webhook-package expectations.

## 13. Open Questions
- `UNKNOWN`: Whether any out-of-repo importer still expects legacy helper names on `app.routers.webhook`.
