# TP-2026-02-16-console-cases-index-wave-a88

- Название/цель: отдельная DB wave для снижения p95 по `/console/v1/cases` за счёт индексов под текущий query shape (без изменения контрактов API/UX).
- Canon refs: `STATE.md` (NOW/GAP Console latency + runtime), `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`, `docs/TASK_PACKAGES/TP-2026-02-16-console-plane-p0-2-p0-3-a1.md`, `AGENTS.md`.

## Invariant
- Не менять функциональное поведение `/cases` и RBAC/tenant isolation.
- Не менять структуру response contract (`items/cursor/has_more/total`).
- Никаких data-cleanup/trace cleanup ради метрик.

## Scope
- Подготовить и применить безопасные `CREATE INDEX CONCURRENTLY` для hot-path `/cases`.
- Подтвердить планом `EXPLAIN ANALYZE` улучшение `list`/`count` p95.
- Обновить perf-report и `STATE.md` фактами после index wave.

## Out of scope
- Рефактор query логики роутера.
- Изменение polling/React Query слоя.
- Массовый reindex всех таблиц платформы.

## Touch-list
- `truffles-api/migrations/` (новая миграция index wave)
- `truffles-api/app/routers/console.py` (только при необходимости hint/порядок фильтров)
- `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`
- `STATE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

## Candidate indexes (from current query shape)
- `messages`: `(client_id, conversation_id, created_at DESC)`
- `messages`: `(client_id, role, conversation_id, created_at DESC)`
- `outbox_messages`: `(client_id, conversation_id, status)`
- `handovers`: `(client_id, status, created_at DESC)`
- `conversations`: `(client_id, branch_id)`

## Baseline fact (before index wave)
- Current index inventory captured in: `/tmp/console_perf_baseline_20260216/current_indexes_cases_wave.tsv`.
- Existing indexes include only single-column paths for `messages.client_id`, `messages.conversation_id`, `messages.created_at`; and `outbox_messages.status,next_attempt_at` without `(client_id,conversation_id,status)` composite.

## Plan
1. Зафиксировать `EXPLAIN ANALYZE` baseline на production-like dataset (`demo_salon`).
2. Добавить миграцию с `CREATE INDEX CONCURRENTLY` для candidate indexes.
3. Применить миграцию в controlled window и переснять `EXPLAIN ANALYZE`.
4. Сравнить p50/p95 до/после и проверить отсутствие regressions в `/cases` filters/sort/cursor.
5. Обновить report + `STATE.md` (FACT/GAP) и подготовить rollback SQL.

## DoD
- Индексы применены без блокирующих table locks (`CONCURRENTLY`).
- `EXPLAIN ANALYZE` показывает снижение p95 для `/cases` list/count относительно baseline.
- `/cases` deterministic checks зелёные.
- Есть evidence-файлы (before/after explain + timing + migration output).

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py`
- `pytest -q truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_console_rbac.py`
- SQL replay scripts from `/tmp/console_perf_baseline_20260216/*`

## Evidence
- `EXPLAIN ANALYZE` before/after (`list` + `count`) with stats files.
- migration apply output + `pg_indexes` diff.
- updated report/STATE entries.

## Rollback
- `DROP INDEX CONCURRENTLY IF EXISTS <index_name>` for each added index.
- Re-run baseline queries to confirm rollback state.

## No-go
- Нельзя выполнять `CREATE INDEX` без `CONCURRENTLY` на боевой БД.
- Нельзя смешивать DB wave с UX refactor в одном пакете.
- Нельзя объявлять победу без before/after evidence.

## Риски/блокеры
- `CONCURRENTLY` может выполняться долго на больших таблицах; нужен maintenance window.
- Возможна необходимость `ANALYZE`/autovacuum stabilization before measuring.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-16-expected-reply-controller-a88` (текущая ветка по решению пользователя)
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR -> main (no rebase)
- Cleanup: Brain/Top Architect после merge
