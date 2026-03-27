# File Analysis: `truffles-api/tests/test_outbox_service_app.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This file is the dedicated contract test for the separate outbox service app mounted from `app.outbox_service_app`: `truffles-api/tests/test_outbox_service_app.py:9`, `truffles-api/tests/test_outbox_service_app.py:13`, `truffles-api/app/outbox_service_app.py:18`.
- `FACT`: It covers worker health, disabled/401 gating, and the happy-path `/outbox/process` flow: `truffles-api/tests/test_outbox_service_app.py:17`, `truffles-api/tests/test_outbox_service_app.py:27`, `truffles-api/tests/test_outbox_service_app.py:33`, `truffles-api/tests/test_outbox_service_app.py:40`.
- `INFERENCE`: This is mostly active service-contract coverage, not stale wrapper residue.

## 2. Why This File Exists
- `FACT`: The file exists to prove the dedicated outbox worker app responds correctly and orchestrates the outbox-processing flow under env/token conditions: `truffles-api/tests/test_outbox_service_app.py:17`, `truffles-api/tests/test_outbox_service_app.py:27`, `truffles-api/tests/test_outbox_service_app.py:33`, `truffles-api/tests/test_outbox_service_app.py:40`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only visible caller.
- `FACT`: The test exercises `app.outbox_service_app.app`, not `app.main.app`: `truffles-api/tests/test_outbox_service_app.py:9`, `truffles-api/tests/test_outbox_service_app.py:13`.

## 4. Control Path Owned By This File
- `FACT`: The happy-path test pins `outbox_service.process_outbox(...)` calling the package export `app.routers.webhook._process_outbox_rows`: `truffles-api/tests/test_outbox_service_app.py:54`, `truffles-api/tests/test_outbox_service_app.py:57`, `truffles-api/tests/test_outbox_service_app.py:66`.
- `INFERENCE`: The file is active evidence that repo-contract memory still treats the package export as the supported worker entrypoint.

## 5. Data Reads
- `FACT`: The test reads env flags, dependency overrides for `get_db`, and the mounted service app: `truffles-api/tests/test_outbox_service_app.py:13`, `truffles-api/tests/test_outbox_service_app.py:17`, `truffles-api/tests/test_outbox_service_app.py:45`.

## 6. Data Writes And Side Effects
- `FACT`: The test monkeypatches `release_stale_processing`, `claim_pending_outbox_batches`, `schedule_inbound_syncs`, `process_reminder_jobs`, and `app.routers.webhook._process_outbox_rows`: `truffles-api/tests/test_outbox_service_app.py:54`, `truffles-api/tests/test_outbox_service_app.py:57`, `truffles-api/tests/test_outbox_service_app.py:60`, `truffles-api/tests/test_outbox_service_app.py:63`, `truffles-api/tests/test_outbox_service_app.py:66`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No semantic authority is involved here.
- `FACT`: The test does pin deterministic worker-gate and batch-orchestration behavior.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carrier is asserted here; the file only checks service-health flags and outbox-processing counters: `truffles-api/tests/test_outbox_service_app.py:23`, `truffles-api/tests/test_outbox_service_app.py:71`.

## 9. Violations Against The Target Canon
- `FACT`: The happy-path test patches `app.routers.webhook._process_outbox_rows` instead of the direct implementation module `app.routers.webhook.outbox._process_outbox_rows`: `truffles-api/tests/test_outbox_service_app.py:66`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `INFERENCE`: The test preserves the package-export seam even though the real helper module is already directly testable elsewhere.

## 10. Salvageable Parts
- `FACT`: Health/disabled/token coverage for the dedicated service app is reusable and aligned with the worker boundary: `truffles-api/tests/test_outbox_service_app.py:17`, `truffles-api/tests/test_outbox_service_app.py:27`, `truffles-api/tests/test_outbox_service_app.py:33`.

## 11. Demotion / Removal Candidates
- `FACT`: The patch target `app.routers.webhook._process_outbox_rows` is a demotion candidate once callers intentionally move to the direct module export: `truffles-api/tests/test_outbox_service_app.py:66`, `truffles-api/app/routers/webhook/outbox.py:446`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: This file proves the outbox-service contract itself is live and useful.
- `INFERENCE`: The remaining debt here is not the existence of the dedicated service test, but the repo-contract pin to the package export seam.

## 13. Open Questions
- `UNKNOWN`: Whether the separate outbox-service app remains a long-term product boundary or only transitional deployment infrastructure.
