# Console Cases Index Wave v1 (2026-02-16)

Status
- `FACT` (DB + timing evidence)
- Scope: `/console/v1/cases` hot-path DB wave (no API/UI contract change)
- Branch/worktree: `feat/2026-02-16-console-cases-index-wave-a88` / `/home/zhan/worktrees/2026-02-16-console-cases-index-wave-a88`

## 1) Goal

Reduce p95 latency for `/console/v1/cases` list + total count by adding composite indexes matching the current query shape.

## 2) Applied migration

Migration
- `truffles-api/migrations/030_add_console_cases_hotpath_indexes.sql`

Result
- `CREATE INDEX` x5 (successful)
- Evidence: `/tmp/console_perf_baseline_20260216/migration_030_apply.txt`

Created indexes
- `idx_messages_client_conversation_created_desc`
- `idx_messages_client_role_conversation_created_desc`
- `idx_outbox_messages_client_conversation_status`
- `idx_handovers_client_status_created_desc`
- `idx_conversations_client_branch`
- Evidence: `/tmp/console_perf_baseline_20260216/current_indexes_cases_wave_after.tsv`

Migration runner compatibility
- `truffles-api/scripts/apply_sql_migrations.py` updated to support `CONCURRENTLY` migrations (autocommit execution path + per-statement split for multi-statement SQL files).
- Unit coverage expanded in `truffles-api/tests/test_apply_sql_migrations.py`.
- Runner evidence after apply:
  - `/tmp/console_perf_baseline_20260216/schema_migrations_030.txt`
  - `/tmp/console_perf_baseline_20260216/migration_runner_check_after_030.txt`

## 3) Measurement protocol

Dataset and mode
- `demo_salon` production-like dataset
- 20 iterations per query family

Query families
- `cases_list` (list path)
- `cases_total_count` (count path)

Artifacts
- Baseline stats: `/tmp/console_perf_baseline_20260216/cases_list_after_stats.txt`, `/tmp/console_perf_baseline_20260216/cases_total_count_after_stats.txt`
- Index-wave stats: `/tmp/console_perf_baseline_20260216/cases_list_index_wave_stats.txt`, `/tmp/console_perf_baseline_20260216/cases_total_count_index_wave_stats.txt`
- Delta summary: `/tmp/console_perf_baseline_20260216/index_wave_delta_summary.txt`
- Post-index explain: `/tmp/console_perf_baseline_20260216/cases_list_index_wave_explain.txt`, `/tmp/console_perf_baseline_20260216/cases_total_count_index_wave_explain.txt`
- Post-index analyze: `/tmp/console_perf_baseline_20260216/analyze_after_index_wave.txt`

## 4) Before vs after

Baseline (before index wave)
- `cases_list_after`: p50 `248.127ms`, p95 `303.548ms`, avg `256.301ms`
- `cases_total_count_after`: p50 `1.447ms`, p95 `1.680ms`, avg `1.467ms`

After index wave
- `cases_list_index_wave`: p50 `42.908ms`, p95 `51.485ms`, avg `44.309ms`
- `cases_total_count_index_wave`: p50 `0.176ms`, p95 `0.227ms`, avg `0.188ms`

Combined delta
- baseline combined p50/p95/avg: `249.574/305.228/257.768 ms`
- index-wave combined p50/p95/avg: `43.084/51.712/44.497 ms`
- delta: `-82.7% / -83.1% / -82.7%`

## 5) Explain highlights

`cases_list_index_wave_explain.txt` shows index-only/index scans on the new composites:
- `idx_messages_client_conversation_created_desc`
- `idx_messages_client_role_conversation_created_desc`
- `idx_outbox_messages_client_conversation_status`
- `idx_handovers_client_status_created_desc`

`cases_total_count_index_wave_explain.txt` shows the count path starts from `idx_handovers_client_status_created_desc` and stays sub-millisecond in execution.

## 6) Risks and follow-up

Open risks
1. This wave optimizes DB read path only; frontend rendering and websocket/polling stalls remain separate UX streams.
2. Additional tenant scales may require follow-up index selectivity checks and periodic `ANALYZE` verification.

Recommended next wave
1. Add API-level timing histogram per `/cases` filters (`status/owner/branch`) to detect regressions by segment.
2. Profile React rendering in Inbox list under 500+ rows to isolate UI-side stalls independent from DB latency.
# Console Plane Performance Baseline v1

Date
- 2026-02-16

Scope
- Quick baseline for operator pain (`slow UI`, `freezes`, `late reload`) before P0 optimization wave.
- Hot path focus: inbox queue (`/console/v1/cases`) + health path + polling pressure.

Environment
- Repo: `/home/zhan/truffles-main`
- DB: `truffles_postgres_1` (`chatbot`)
- Client sample (largest workload): `demo_salon` (`client_id=c839d5dd-65be-4733-a5d2-72c9f70707f0`)

## 1) SQL hot path baseline (`/cases`)

Method
- Reproduced router SQL shape from `truffles-api/app/routers/console.py` (`list_cases`) with `EXPLAIN ANALYZE`.
- Measured 20 iterations for:
  - queue page query (`items + joins + order + limit`),
  - `total_count` query (same joined graph).
- Artifacts:
  - `/tmp/console_perf_baseline_20260216/query_cases_list.sql`
  - `/tmp/console_perf_baseline_20260216/query_cases_total_count.sql`
  - `/tmp/console_perf_baseline_20260216/cases_list_times_ms.txt`
  - `/tmp/console_perf_baseline_20260216/cases_total_count_times_ms.txt`

Results
- `cases_list`: `p50=232.108ms`, `p95=252.300ms`, `avg=235.581ms`.
- `cases_total_count`: `p50=149.262ms`, `p95=186.045ms`, `avg=154.399ms`.
- Combined per refresh (list + count): `p50=386.539ms`, `p95=414.119ms`, `avg=389.981ms`.

Observation
- The query scans almost full `messages` and `outbox_messages` even when visible open handovers are small.
- `total_count` is expensive because it runs over the same joined graph.

## 2) Health path baseline

Method
- 20 `curl` iterations per endpoint (`time_total`).
- Artifacts:
  - `/tmp/console_perf_baseline_20260216/local_admin_health_seconds.txt`
  - `/tmp/console_perf_baseline_20260216/local_console_health_full_seconds.txt`
  - `/tmp/console_perf_baseline_20260216/prod_console_health_full_seconds.txt`
  - `/tmp/console_perf_baseline_20260216/local_admin_health_snapshot.json`
  - `/tmp/console_perf_baseline_20260216/local_health_full_snapshot.json`
  - `/tmp/console_perf_baseline_20260216/prod_health_full_snapshot.json`

Results
- `http://localhost:8000/admin/health/check`: `p50=29.6ms`, `p95=148.5ms`, max outlier `2269.4ms`.
- `http://localhost:3000/api/health/full`: `p50=47.7ms`, `p95=3367.9ms`, max `5018.7ms`.
- `https://console.truffles.kz/api/health/full`: `p50=2346.0ms`, `p95=5313.6ms`, max `5344.3ms`.

Snapshot facts
- Local admin health reports outbox warning: `pending=1852`, `failed=1363`, `qdrant.latency_ms=1917`.
- `health/full` endpoints hit 5s abort window and return `api.status=unreachable` in sampled window.

## 3) Polling pressure baseline (code-level)

Current intervals
- `CaseList`: `refetchInterval=10000` (`console-web/src/components/CaseList.tsx`).
- `useCaseData case`: `refetchInterval=10000` + background (`console-web/src/hooks/useCaseData.ts`).
- `useCaseData messages`: `refetchInterval=5000` + background (`console-web/src/hooks/useCaseData.ts`).
- `ConsoleShell health`: `refetchInterval=30000` for ops-readable roles (`console-web/src/components/ConsoleShell.tsx`).

Estimated request load (single open inbox session)
- Manager: ~24 req/min (`cases + case + messages`).
- Owner/Admin (ops readable): ~26 req/min (`+ health banner`).
- Ops screen adds several 30s pollers in parallel (`health`, `telegram`, `outbox`, `jobs`, `incidents`).

## 4) Summary

- Main latency risk is backend query cost + frequent polling, not JS bundle size.
- Queue refresh currently pays ~`390ms p50` / `414ms p95` on SQL path before network/UI render.
- Health routes show timeout-prone behavior under current runtime degradation, amplifying perceived UI slowness.

## 5) After P0-2/P0-3 patch (local SQL replay)

Patch scope
- Backend (`/cases`): lightweight count-path + client-scoped message/outbox subqueries.
- Frontend (Inbox): lower polling cadence, no background refetch for case/messages, scoped cache invalidation on context switch.

After replay (20 iterations)
- `cases_list_after`: `p50=248.127ms`, `p95=303.548ms`, `avg=256.301ms`.
- `cases_total_count_after`: `p50=1.447ms`, `p95=1.680ms`, `avg=1.467ms`.
- Combined per refresh after patch: `p50=249.654ms`, `p95=304.942ms`, `avg=257.769ms`.

Before vs after (combined SQL path)
- `p50`: `386.539ms -> 249.654ms` (`-35.4%`).
- `p95`: `414.119ms -> 304.942ms` (`-26.4%`).
- `avg`: `389.981ms -> 257.769ms` (`-33.9%`).

Additional artifacts
- `/tmp/console_perf_baseline_20260216/query_cases_list_after.sql`
- `/tmp/console_perf_baseline_20260216/query_cases_total_count_after.sql`
- `/tmp/console_perf_baseline_20260216/cases_list_after_stats.txt`
- `/tmp/console_perf_baseline_20260216/cases_total_count_after_stats.txt`

## 6) P0-1 runtime remediation (`/admin/health/check`)

Patch scope
- Added short-lived cache for health payload (`ADMIN_HEALTH_CACHE_TTL_SECONDS`, default `10s`).
- Added bounded Qdrant timeout for health check (`ADMIN_HEALTH_QDRANT_TIMEOUT_SECONDS`, default `1.5s`).
- Replaced dual outbox counts (`PENDING` + `FAILED`) with one grouped query.

Code evidence
- `truffles-api/app/main.py` (`/admin/health/check` + `_compute_admin_health_payload`).
- `truffles-api/tests/test_admin_health_cache.py` (cache contract tests).

Checks
- `python3 -m py_compile truffles-api/app/main.py`
- `pytest -q truffles-api/tests/test_admin_health_cache.py` (`2 passed`)

After metrics (local uvicorn with patched code, 20 samples)
- First uncached sample: `latency_ms=253` (payload field from endpoint response).
- Cached poll window: `p50=3.533ms`, `p95=4.061ms`, `avg=3.540ms`, `max=4.109ms`.

After artifacts
- `/tmp/console_perf_baseline_20260216/local_admin_health_after_snapshot.json`
- `/tmp/console_perf_baseline_20260216/local_admin_health_after_seconds.txt`
- `/tmp/console_perf_baseline_20260216/local_admin_health_after_stats.txt`

Notes
- This reduces health-tail pressure for Console polling path, but does not by itself resolve runtime backlog (`outbox.pending/failed`) issues.
