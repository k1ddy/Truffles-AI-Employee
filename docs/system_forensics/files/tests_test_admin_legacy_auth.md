# File Analysis: `truffles-api/tests/test_admin_legacy_auth.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file is a focused admin-router contract test. It mounts `admin_router.router` into a local FastAPI app and verifies token-guard behavior for selected legacy admin routes: `truffles-api/tests/test_admin_legacy_auth.py:9`, `truffles-api/tests/test_admin_legacy_auth.py:14`, `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/tests/test_admin_legacy_auth.py:66`, `truffles-api/tests/test_admin_legacy_auth.py:78`.
- `FACT`: The covered routes are `/admin/prompt/*`, `/admin/settings/*`, `/admin/heal`, `/admin/health`, and `/admin/version`; `/admin/outbox/process` is not included: `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:36`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/tests/test_admin_legacy_auth.py:73`, `truffles-api/tests/test_admin_legacy_auth.py:80`.
- `INFERENCE`: This file is the repo-backed proof that visible admin-auth coverage exists, but it does not currently pin the duplicated admin outbox route.

## 2. Why This File Exists
- `FACT`: The file exists to ensure legacy admin routes require `X-Admin-Token` when `ALERTS_ADMIN_TOKEN` is configured, while public admin health/version remain open: `truffles-api/tests/test_admin_legacy_auth.py:39`, `truffles-api/tests/test_admin_legacy_auth.py:54`, `truffles-api/tests/test_admin_legacy_auth.py:66`, `truffles-api/tests/test_admin_legacy_auth.py:78`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only visible caller.
- `FACT`: The test mounts `admin_router.router` directly rather than going through `app.main.app`: `truffles-api/tests/test_admin_legacy_auth.py:14`, `truffles-api/tests/test_admin_legacy_auth.py:15`.

## 4. Control Path Owned By This File
- `FACT`: The file pins `_require_admin_token(...)` behavior on a selected subset of admin endpoints by exercising the mounted router with and without `X-Admin-Token`: `truffles-api/tests/test_admin_legacy_auth.py:39`, `truffles-api/tests/test_admin_legacy_auth.py:54`, `truffles-api/tests/test_admin_legacy_auth.py:73`, `truffles-api/app/routers/admin.py:172`.
- `FACT`: It does not pin the live `/admin/outbox/process` branch even though that route exists in the same router: `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/app/routers/admin.py:513`.
- `INFERENCE`: This is a selective admin contract test, not full coverage for the mounted admin surface.

## 5. Data Reads
- `FACT`: The file reads `admin_router.router`, `admin_router.get_db`, and env var `ALERTS_ADMIN_TOKEN`: `truffles-api/tests/test_admin_legacy_auth.py:9`, `truffles-api/tests/test_admin_legacy_auth.py:20`, `truffles-api/tests/test_admin_legacy_auth.py:40`, `truffles-api/tests/test_admin_legacy_auth.py:55`, `truffles-api/tests/test_admin_legacy_auth.py:67`, `truffles-api/tests/test_admin_legacy_auth.py:79`.

## 6. Data Writes And Side Effects
- `FACT`: The file overrides `get_db` with a fake DB and monkeypatches `check_and_heal_conversations(...)` for the `/admin/heal` path: `truffles-api/tests/test_admin_legacy_auth.py:17`, `truffles-api/tests/test_admin_legacy_auth.py:20`, `truffles-api/tests/test_admin_legacy_auth.py:68`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No semantic authority is involved here.
- `FACT`: The test pins deterministic admin-auth gating and the explicit public/private split of selected admin endpoints: `truffles-api/tests/test_admin_legacy_auth.py:39`, `truffles-api/tests/test_admin_legacy_auth.py:54`, `truffles-api/tests/test_admin_legacy_auth.py:73`, `truffles-api/tests/test_admin_legacy_auth.py:80`.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carriers are asserted here; the file only checks HTTP statuses and one small `/admin/heal` response body: `truffles-api/tests/test_admin_legacy_auth.py:41`, `truffles-api/tests/test_admin_legacy_auth.py:63`, `truffles-api/tests/test_admin_legacy_auth.py:74`.

## 9. Violations Against The Target Canon
- `FACT`: The file does not cover `/admin/outbox/process` even though that route is mounted on the same live admin router and duplicates the outbox worker orchestration: `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/app/routers/admin.py:513`, `truffles-api/app/main.py:109`.
- `INFERENCE`: This file is now evidence of weak visible admin-route coverage around the duplicated outbox entrypoint family.

## 10. Salvageable Parts
- `FACT`: The existing token-guard coverage for prompt/settings/heal and public health/version is reusable and valid for the mounted admin router surface: `truffles-api/tests/test_admin_legacy_auth.py:32`, `truffles-api/tests/test_admin_legacy_auth.py:48`, `truffles-api/tests/test_admin_legacy_auth.py:66`, `truffles-api/tests/test_admin_legacy_auth.py:78`.

## 11. Demotion / Removal Candidates
- `INFERENCE`: No direct removal target lives in this file; the value is in exposing the missing `/admin/outbox/process` contract coverage.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The repo does already carry mounted-admin contract coverage, but it is selective.
- `INFERENCE`: The admin outbox route is now explicitly classified as a live duplicate route with weak visible repo-contract coverage, not as an already-tested admin surface.

## 13. Open Questions
- `UNKNOWN`: Whether omission of `/admin/outbox/process` in this file is intentional because another hidden test covers it, or simply stale coverage debt.
