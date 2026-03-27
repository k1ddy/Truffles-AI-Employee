# File Analysis: `truffles-api/tests/test_outbox_transport_degraded.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: This is a tiny direct-module contract test for `app.routers.webhook.outbox._classify_transport_degradation(...)`: `truffles-api/tests/test_outbox_transport_degraded.py:1`, `truffles-api/tests/test_outbox_transport_degraded.py:4`, `truffles-api/tests/test_outbox_transport_degraded.py:17`, `truffles-api/app/routers/webhook/outbox.py:143`.
- `FACT`: The file imports the real outbox helper module directly (`from app.routers.webhook import outbox as outbox_router`), not the package export `_process_outbox_rows`: `truffles-api/tests/test_outbox_transport_degraded.py:1`.
- `INFERENCE`: This is another proof that direct helper-module coverage already exists around `webhook.outbox`.

## 2. Why This File Exists
- `FACT`: The file exists to pin billing-blocked transport degradation normalization and the no-op path for unrelated errors: `truffles-api/tests/test_outbox_transport_degraded.py:4`, `truffles-api/tests/test_outbox_transport_degraded.py:17`.

## 3. Active Callers And Entrypoints
- `FACT`: Pytest is the only visible caller.
- `FACT`: The contract under test is `_classify_transport_degradation(...)`, which is used by `_process_outbox_rows(...)` when delivery exceptions occur: `truffles-api/tests/test_outbox_transport_degraded.py:5`, `truffles-api/app/routers/webhook/outbox.py:1347`, `truffles-api/app/routers/webhook/outbox.py:1349`.

## 4. Control Path Owned By This File
- `FACT`: The file pins a narrow direct helper contract for the real outbox implementation module, not a wrapper/export seam: `truffles-api/tests/test_outbox_transport_degraded.py:1`, `truffles-api/app/routers/webhook/outbox.py:143`, `truffles-api/app/routers/webhook/outbox.py:1667`.
- `INFERENCE`: This test is supportive direct-module coverage, not a blocker that keeps the wrapper/export seam alive by itself.

## 5. Data Reads
- `FACT`: The file reads only the direct helper module and fixed input strings, including the `CHATFLOW_BILLING_BLOCKED` marker contract: `truffles-api/tests/test_outbox_transport_degraded.py:1`, `truffles-api/tests/test_outbox_transport_degraded.py:6`.
- `FACT`: The helper itself reads provider classification policy from `provider_error_policy.py`: `truffles-api/app/routers/webhook/outbox.py:143`, `truffles-api/app/services/provider_error_policy.py:56`, `truffles-api/app/services/provider_error_policy.py:60`.

## 6. Data Writes And Side Effects
- `FACT`: The test performs no DB/network side effects; it asserts returned dict shape only: `truffles-api/tests/test_outbox_transport_degraded.py:9`, `truffles-api/tests/test_outbox_transport_degraded.py:18`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: No semantic authority is involved here.
- `FACT`: The file pins one deterministic delivery-classification helper that feeds outbox transport degradation behavior: `truffles-api/tests/test_outbox_transport_degraded.py:5`, `truffles-api/app/routers/webhook/outbox.py:143`, `truffles-api/app/routers/webhook/outbox.py:148`.

## 8. Truth Carriers Touched Here
- `FACT`: No semantic truth carrier is asserted here; the file only checks the operational degradation meta payload (`delivery_state`, `delivery_error_code`, `delivery_error_class`, `delivery_error_kind`): `truffles-api/tests/test_outbox_transport_degraded.py:9`, `truffles-api/tests/test_outbox_transport_degraded.py:10`, `truffles-api/tests/test_outbox_transport_degraded.py:13`.

## 9. Violations Against The Target Canon
- `FACT`: No wrapper/export compatibility violation is pinned by this file; it already tests the direct helper module.
- `INFERENCE`: The value here is evidence that not all outbox repo-contract tests depend on package-export indirection.

## 10. Salvageable Parts
- `FACT`: The direct helper coverage for transport degradation classification is fully salvageable as a bounded transport-boundary contract: `truffles-api/tests/test_outbox_transport_degraded.py:4`, `truffles-api/tests/test_outbox_transport_degraded.py:17`.

## 11. Demotion / Removal Candidates
- `INFERENCE`: No demotion target is created by this file; it already uses the direct helper surface.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The repo has another direct helper test around `webhook.outbox`, this time for `_classify_transport_degradation(...)` rather than `_process_outbox_rows(...)`.
- `INFERENCE`: The next unresolved outbox-seam question is no longer about direct helper tests; it is about the remaining live callers that still import the package seam.

## 13. Open Questions
- `UNKNOWN`: Whether additional live callers beyond worker/admin/service/console still import `_process_outbox_rows` through the package seam.
