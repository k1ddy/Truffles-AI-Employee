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
