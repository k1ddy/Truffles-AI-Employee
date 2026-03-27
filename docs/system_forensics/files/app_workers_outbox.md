# File Analysis: `truffles-api/app/workers/outbox.py`

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
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `app/workers/outbox.py` is the live standalone outbox worker loop. Repo deployment surfaces invoke it as `python -m app.workers.outbox`, and the file enters `run_worker()` from its own `__main__` block: `truffles-api/docker-compose.yml:41`, `scripts/restart_workers.sh:54`, `docs/runbooks/OUTBOX.md:80`, `truffles-api/app/workers/outbox.py:134`, `truffles-api/app/workers/outbox.py:310`.
- `FACT`: The worker loop is not just a sender. It performs startup safety checks, OTel setup, stale-lock release, inbound calendar sync scheduling, metrics-daily scheduling, batch claiming, and then delivery processing: `truffles-api/app/workers/outbox.py:145`, `truffles-api/app/workers/outbox.py:152`, `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:214`, `truffles-api/app/workers/outbox.py:230`, `truffles-api/app/workers/outbox.py:268`, `truffles-api/app/workers/outbox.py:278`.
- `INFERENCE`: This file is a live operational caller of the `_process_outbox_rows` package seam and also a scheduler bundle, not a thin delivery wrapper.

## 2. Why This File Exists
- `FACT`: The file exists to keep outbox delivery and adjacent background maintenance off the HTTP request path by running a continuous loop over runtime-mode gates, DB claims, and helper processing: `truffles-api/app/workers/outbox.py:134`, `truffles-api/app/workers/outbox.py:136`, `truffles-api/app/workers/outbox.py:145`, `truffles-api/app/workers/outbox.py:268`, `truffles-api/app/workers/outbox.py:278`.
- `FACT`: Repo references still describe it as the dedicated outbox worker entrypoint: `SPECS/SYSTEM_REFERENCE.md:1013`, `SPECS/SYSTEM_REFERENCE.md:1034`.

## 3. Active Callers And Entrypoints
- `FACT`: The visible runtime entrypoint is module execution (`python -m app.workers.outbox`) from compose/runtime scripts, and there are no other visible Python callers of `run_worker()`: `truffles-api/docker-compose.yml:41`, `scripts/restart_workers.sh:54`, `truffles-api/app/workers/outbox.py:134`, `truffles-api/app/workers/outbox.py:312`.
- `FACT`: Visible repo-contract coverage is narrow and settings-focused. `test_outbox_worker_settings.py` imports `app.workers.outbox` directly and only checks env parsing plus the startup safety guard: `truffles-api/tests/test_outbox_worker_settings.py:3`, `truffles-api/tests/test_outbox_worker_settings.py:6`, `truffles-api/tests/test_outbox_worker_settings.py:18`, `truffles-api/tests/test_outbox_worker_settings.py:29`.
- `UNKNOWN`: Whether any non-repo deployment surface still invokes this worker with a different entry contract than the visible module command.

## 4. Control Path Owned By This File
- `FACT`: The active worker processing path is `python -m app.workers.outbox -> run_worker() -> assert_outbox_worker_startup_safe() -> _setup_otel() -> app.routers.webhook._process_outbox_rows -> decision._process_outbox_rows(...) -> webhook.outbox._process_outbox_rows(...)`: `truffles-api/docker-compose.yml:41`, `truffles-api/app/workers/outbox.py:145`, `truffles-api/app/workers/outbox.py:152`, `truffles-api/app/workers/outbox.py:154`, `truffles-api/app/workers/outbox.py:278`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: Before calling the helper chain, the loop also runs release-stale, inbound-calendar scheduling, and optional metrics-daily snapshot logic inside the same worker cycle: `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:214`, `truffles-api/app/workers/outbox.py:230`.
- `INFERENCE`: This is another live operational owner of the wrapper/export seam, and it also proves the seam is embedded in a broader worker bundle rather than an isolated outbox adapter.

## 5. Data Reads
- `FACT`: The worker reads runtime mode, startup safety inputs, OTel env, outbox interval/limit/retry env, metrics-daily env, and DB state through the outbox/calendar/metrics services: `truffles-api/app/workers/outbox.py:19`, `truffles-api/app/workers/outbox.py:28`, `truffles-api/app/workers/outbox.py:71`, `truffles-api/app/workers/outbox.py:93`, `truffles-api/app/workers/outbox.py:136`, `truffles-api/app/workers/outbox.py:145`, `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:230`, `truffles-api/app/workers/outbox.py:268`.

## 6. Data Writes And Side Effects
- `FACT`: The worker releases stale processing locks, schedules inbound syncs, writes metrics-daily snapshots, processes claimed outbox rows, and logs operational results/errors: `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:230`, `truffles-api/app/workers/outbox.py:278`, `truffles-api/app/workers/outbox.py:285`, `truffles-api/app/workers/outbox.py:304`.
- `FACT`: Final outbox status/meta writes still happen downstream in `webhook.outbox._process_outbox_rows(...)`, not in this file: `truffles-api/app/workers/outbox.py:278`, `truffles-api/app/routers/webhook/outbox.py:570`, `truffles-api/app/routers/webhook/outbox.py:968`.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The file is not a semantic owner.
- `FACT`: It is deterministic operational authority for worker enable/disable, startup safety, scheduling cadence, stale-release behavior, metrics scheduling, batch claiming, and delivery processing invocation: `truffles-api/app/workers/outbox.py:136`, `truffles-api/app/workers/outbox.py:145`, `truffles-api/app/workers/outbox.py:171`, `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:214`, `truffles-api/app/workers/outbox.py:268`, `truffles-api/app/workers/outbox.py:278`.

## 8. Truth Carriers Touched Here
- `FACT`: The file introduces no semantic truth carriers.
- `FACT`: It only transports operational counters/result payloads and lets the downstream outbox helper mutate outbox status/meta surfaces: `truffles-api/app/workers/outbox.py:285`, `truffles-api/app/workers/outbox.py:304`, `truffles-api/app/routers/webhook/outbox.py:570`, `truffles-api/app/routers/webhook/outbox.py:968`.

## 9. Violations Against The Target Canon
- `FACT`: The file still imports `app.routers.webhook._process_outbox_rows` through the package export seam instead of depending on the real helper module directly: `truffles-api/app/workers/outbox.py:154`, `truffles-api/app/routers/webhook/__init__.py:3`, `truffles-api/app/routers/webhook/decision.py:8567`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `FACT`: The worker bundle mixes outbox delivery with inbound calendar scheduling and metrics-daily scheduling inside one long-lived loop: `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:214`, `truffles-api/app/workers/outbox.py:230`, `truffles-api/app/workers/outbox.py:268`.
- `INFERENCE`: The debt here is operational coupling plus wrapper/export indirection, not semantic ambiguity.

## 10. Salvageable Parts
- `FACT`: `_get_outbox_worker_settings(...)`, `_get_metrics_daily_settings(...)`, and the startup safety gate are reusable bounded worker-boundary helpers: `truffles-api/app/workers/outbox.py:71`, `truffles-api/app/workers/outbox.py:93`, `truffles-api/app/workers/outbox.py:145`.
- `FACT`: A dedicated background worker loop remains salvageable if the system still needs async outbox processing outside request/response paths: `truffles-api/app/workers/outbox.py:134`, `truffles-api/app/workers/outbox.py:268`, `truffles-api/app/workers/outbox.py:278`.

## 11. Demotion / Removal Candidates
- `FACT`: The package-export import (`from app.routers.webhook import _process_outbox_rows`) is a demotion target because the real helper owner already lives in `webhook/outbox.py`: `truffles-api/app/workers/outbox.py:154`, `truffles-api/app/routers/webhook/outbox.py:446`.
- `INFERENCE`: The co-located calendar/metrics scheduler work is a separation candidate if the future worker boundary is meant to be outbox-only.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The remaining `_process_outbox_rows` seam is not only an HTTP/admin/service problem; it is also a background-worker deployment problem.
- `FACT`: The active worker bundle still couples delivery processing with inbound-sync and metrics scheduling in one loop: `truffles-api/app/workers/outbox.py:177`, `truffles-api/app/workers/outbox.py:192`, `truffles-api/app/workers/outbox.py:214`, `truffles-api/app/workers/outbox.py:230`, `truffles-api/app/workers/outbox.py:268`.
- `INFERENCE`: After this block, the next unresolved question in the outbox slice shifts from live caller discovery to the direct repo-contract pins around worker and console caller surfaces.

## 13. Open Questions
- `UNKNOWN`: Whether calendar inbound scheduling and metrics-daily scheduling should remain in this worker after seam collapse.
- `UNKNOWN`: Whether the worker should keep calling a package export at all once direct helper-module imports are normalized.
