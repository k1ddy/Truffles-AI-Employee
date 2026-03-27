# File Analysis: `truffles-api/app/routers/console.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `console.py` is the mounted `/console/v1` router on the main app: `truffles-api/app/routers/console.py:895`, `truffles-api/app/main.py:110`.
- `FACT`: In the outbox slice, the file is not read-only UI support. It defines incident actions for `outbox_process`, registers the `outbox_process` job type, and executes that job through `_run_outbox_process_job(...)`: `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:9651`, `truffles-api/app/routers/console.py:10505`, `truffles-api/app/routers/console.py:18215`, `truffles-api/app/routers/console.py:18253`, `truffles-api/app/routers/console.py:18254`.
- `INFERENCE`: For this forensic family, `console.py` is a fourth live outbox execute surface, not just an observability page.

## 2. Why This File Exists
- `FACT`: The file exists as the broad console API router, including ops surfaces for queue inspection, retries, incidents, and operator-triggered jobs: `truffles-api/app/routers/console.py:17759`, `truffles-api/app/routers/console.py:17832`, `truffles-api/app/routers/console.py:18128`, `truffles-api/app/routers/console.py:18215`.
- `FACT`: The outbox-specific reason this file matters is that the incident/readiness surfaces explicitly instruct operators to run `outbox_process`, not just inspect data: `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:9652`.

## 3. Active Callers And Entrypoints
- `FACT`: The router is live through `app.main`: `truffles-api/app/main.py:110`, `truffles-api/app/routers/console.py:895`.
- `FACT`: Visible direct repo-contract coverage exists in `test_console_ops_jobs.py`; it hits both `run_ops_job(...)` and `_run_outbox_process_job(...)`: `truffles-api/tests/test_console_ops_jobs.py:59`, `truffles-api/tests/test_console_ops_jobs.py:73`, `truffles-api/tests/test_console_ops_jobs.py:75`, `truffles-api/tests/test_console_ops_jobs.py:341`, `truffles-api/tests/test_console_ops_jobs.py:387`.
- `FACT`: Additional repo-contract surfaces also pin `outbox_process` as a product/admin action code or job record in business/control-tower/readiness flows: `truffles-api/tests/test_console_owner_business.py:1648`, `truffles-api/tests/test_console_control_tower_program.py:50`, `truffles-api/tests/test_console_access_admin_pr2.py:1540`, `truffles-api/tests/test_console_access_admin_pr2.py:1575`, `truffles-api/tests/test_console_access_admin_pr2.py:1617`.

## 4. Control Path Owned By This File
- `FACT`: The live execute path is `app.main -> console.router -> POST /console/v1/ops/jobs/run -> run_ops_job(...) -> _run_outbox_process_job(...) -> _claim_scoped_outbox_rows(...) -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/app/main.py:110`, `truffles-api/app/routers/console.py:18215`, `truffles-api/app/routers/console.py:18253`, `truffles-api/app/routers/console.py:18254`, `truffles-api/app/routers/console.py:10505`, `truffles-api/app/routers/console.py:10591`, `truffles-api/app/routers/console.py:10610`, `truffles-api/app/routers/console.py:10612`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The same file also creates the operator-facing dry-run action and job-type envelope that route humans toward that execute path: `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:9004`, `truffles-api/app/routers/console.py:9651`, `truffles-api/app/routers/console.py:9652`.
- `INFERENCE`: `console.py` is simultaneously a control-plane surface and a live outbox execution caller.

## 5. Data Reads
- `FACT`: `_run_outbox_process_job(...)` reads job params, branch scope, env-derived outbox limits/backoff values, and scoped queue rows before processing: `truffles-api/app/routers/console.py:10510`, `truffles-api/app/routers/console.py:10517`, `truffles-api/app/routers/console.py:10524`, `truffles-api/app/routers/console.py:10531`, `truffles-api/app/routers/console.py:10557`, `truffles-api/app/routers/console.py:10591`.
- `FACT`: The file also reads queue/incident state to propose `outbox_process` actions upstream in the console UX: `truffles-api/app/routers/console.py:8985`, `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:9100`, `truffles-api/app/routers/console.py:18253`.

## 6. Data Writes And Side Effects
- `FACT`: `run_ops_job(...)` writes a `ConsoleOpsJob` row, stores request/result payloads, records audit, commits, and refreshes the job record: `truffles-api/app/routers/console.py:18232`, `truffles-api/app/routers/console.py:18247`, `truffles-api/app/routers/console.py:18333`, `truffles-api/app/routers/console.py:18349`, `truffles-api/app/routers/console.py:18350`.
- `FACT`: The outbox job path can archive pending rows, claim scoped rows, and invoke downstream outbox processing side effects: `truffles-api/app/routers/console.py:10581`, `truffles-api/app/routers/console.py:10591`, `truffles-api/app/routers/console.py:10612`.
- `FACT`: Final outbox status/meta mutations still happen downstream in `webhook.outbox._process_outbox_rows(...)`, not in this file: `truffles-api/app/routers/console.py:10612`, `truffles-api/app/routers/webhook/outbox.py:570`, `truffles-api/app/routers/webhook/outbox.py:968`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file is not a semantic owner.
- `FACT`: In this slice it is deterministic operational authority: it exposes queue views, operator actions, scoped dry-run/execute behavior, job persistence, and audit around outbox processing: `truffles-api/app/routers/console.py:17759`, `truffles-api/app/routers/console.py:17832`, `truffles-api/app/routers/console.py:18128`, `truffles-api/app/routers/console.py:18215`, `truffles-api/app/routers/console.py:18253`, `truffles-api/app/routers/console.py:18333`.

## 8. Truth Carriers Touched Here
- `FACT`: The file introduces no semantic truth carrier for the consultant runtime.
- `FACT`: It writes operational control-plane carriers only: `ConsoleOpsJob.request_payload`, `ConsoleOpsJob.result_payload`, outbox dry-run summaries, and incident/action metadata: `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:10379`, `truffles-api/app/routers/console.py:10568`, `truffles-api/app/routers/console.py:18232`, `truffles-api/app/routers/console.py:18323`.

## 9. Violations Against The Target Canon
- `FACT`: The file keeps the `_process_outbox_rows` package export seam alive from a mounted control-plane route: `truffles-api/app/routers/console.py:10610`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: `console.py` is another mixed-responsibility megafile: the outbox execute path lives inside a very large mounted router rather than a thin dedicated boundary: `truffles-api/app/routers/console.py:895`, `truffles-api/app/routers/console.py:10505`, `truffles-api/app/routers/console.py:18215`.
- `INFERENCE`: The debt here is another live operational caller surface plus control-plane megafile coupling, not semantic ambiguity.

## 10. Salvageable Parts
- `FACT`: `_claim_scoped_outbox_rows(...)`, dry-run summaries, and the `ConsoleOpsJob` envelope are reusable if console-triggered operations remain product-required: `truffles-api/app/routers/console.py:10267`, `truffles-api/app/routers/console.py:10285`, `truffles-api/app/routers/console.py:10379`, `truffles-api/app/routers/console.py:18232`.
- `FACT`: The incident action and job catalog entries for `outbox_process` are reusable as thin UI/control-plane metadata if execution is moved behind a shared service boundary: `truffles-api/app/routers/console.py:9000`, `truffles-api/app/routers/console.py:9651`.

## 11. Demotion / Removal Candidates
- `FACT`: The direct package import inside `_run_outbox_process_job(...)` is a demotion target because the real helper owner already lives in `webhook/outbox.py`: `truffles-api/app/routers/console.py:10610`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `INFERENCE`: The outbox execute body should become a thin wrapper over a shared boundary instead of another embedded caller inside `console.py`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The `_process_outbox_rows` seam is also preserved by the mounted console control plane, not only by worker/admin/service paths.
- `FACT`: Repo-contract memory for this surface is richer than a single route test: there is direct ops-job coverage plus indirect business/control-tower/readiness references to `outbox_process`: `truffles-api/tests/test_console_ops_jobs.py:59`, `truffles-api/tests/test_console_ops_jobs.py:341`, `truffles-api/tests/test_console_owner_business.py:1648`, `truffles-api/tests/test_console_control_tower_program.py:50`, `truffles-api/tests/test_console_access_admin_pr2.py:1540`.
- `INFERENCE`: After this block, the next unresolved question in the outbox slice is which direct test pins must move when worker/console stop importing the package seam.

## 13. Open Questions
- `UNKNOWN`: Whether console should keep live `execute` capability for `outbox_process` long-term or shrink to dry-run/trigger-only behavior.
- `UNKNOWN`: Whether the indirect `outbox_process` references in owner/control-tower/readiness tests are product-essential or just residual contract memory.
