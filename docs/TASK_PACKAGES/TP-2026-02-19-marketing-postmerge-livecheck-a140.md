# TP-2026-02-19-marketing-postmerge-livecheck-a140

- Название/цель: Подтвердить post-merge runtime behavior для Wave 3 Marketing (`create/preview/execute + reply-context`) и зафиксировать FACT/GAP в `STATE.md`.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/ARCHITECTURE.md`, `TECH.md`, `docs/TASK_PACKAGES/TP-2026-02-19-wave3-marketing-full-a140.md`.
- CA_ID: N/A.

## Invariant
- Никакого cross-tenant/cross-branch leakage.
- Проверка должна быть на runtime (`main`) с реальным Console API токеном.
- Любой GAP фиксируется как GAP, без приукрашивания.

## Scope
- Runtime smoke для `/console/v1/admin/marketing/campaigns`:
  - create
  - preview
  - execute (`confirm_send=true`)
- Runtime проверка inbound reply-context:
  - `decision_meta`
  - `conversations.context.marketing_context`
  - `conversations.context.decision_trace` stage check
- Обновление `STATE.md` и session artifacts.

## Out of scope
- Кодовые изменения core behavior.
- UI redesign.
- Любые migration/schema изменения.

## Touch-list
- `STATE.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-marketing-postmerge-livecheck-a140.md`
- `docs/SESSIONS/SESSION-2026-02-19-marketing-postmerge-livecheck-a140.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Получить bearer через Keycloak password grant и выполнить `/marketing` create/preview/execute.
2. Проверить delivery rows в БД и сделать inbound reply в ту же conversation.
3. Проверить `decision_meta`/`marketing_context`/`decision_trace` stage.
4. Зафиксировать FACT/GAP в `STATE.md` + session docs.

## DoD
- Есть runtime evidence для marketing lifecycle на `main`.
- Есть evidence для inbound reply-context.
- `STATE.md` обновлен (FACT + GAP, если обнаружен).

## Checks
- Runtime API calls (`curl`) на `https://api.truffles.kz/console/v1/admin/marketing/campaigns*`.
- SQL checks через `docker exec -i truffles_postgres_1 psql ...`.

## Evidence
- `/tmp/marketing-live-20260219-131840/create_response.json`
- `/tmp/marketing-live-20260219-131840/preview_response.json`
- `/tmp/marketing-live-20260219-131840/execute_response.json`
- `/tmp/marketing-live-20260219-131840/diagnostics_response.json`
- `/tmp/marketing-live-20260219-131840/sql_campaign_deliveries.tsv`
- `/tmp/marketing-live-20260219-131840/sql_campaign_deliveries_after_reply.tsv`
- `/tmp/marketing-live-20260219-131840/reply2_result.json`
- `/tmp/marketing-live-20260219-131840/reply2_context_summary.json`
- `/tmp/marketing-live-20260219-131840/sql_reply2_trace_full.json`

## Rollback
- Doc-only: revert commit в `main`.

## No-go
- Не маскировать найденный GAP по trace stage.
- Не использовать ручные DB правки для "красивого" evidence.

## Риски/блокеры
- Runtime trace retention может выкидывать stage до фиксации evidence.

## Branch / Worktree / Merge
- Branch: `main` (doc-only fast path)
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: fast-forward push в `main` (doc-only)
- Cleanup: N/A
