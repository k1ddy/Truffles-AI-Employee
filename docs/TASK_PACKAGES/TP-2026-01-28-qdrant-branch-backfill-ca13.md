# TP-2026-01-28 — Qdrant branch backfill + CA-13 evidence

Название/цель (1–2 предложения)
- Пересинхронизировать Qdrant для всех веток с published knowledge, чтобы metadata содержала `branch_id`/`knowledge_tag`, и зафиксировать CA-13 evidence (branch isolation) после backfill.

Invariant
- Поведение core/LLM/LAW/policy не меняется.
- Tenant isolation не ослабляется; `branch_id` обязателен в trace/meta.
- Никаких ручных правок БД/decision_trace ради evidence.

Scope
- Qdrant backfill по всем веткам с published knowledge (используем `sync_qdrant_from_pack`).
- Проверка Qdrant metadata (`branch_id`/`knowledge_tag`) на canary.
- Live-check + trace-bundle для CA-13 после backfill.
- Документация evidence в `STATE.md`.

Out of scope
- Provider Gateway outbound canary (нет `PROVIDER_GATEWAY_OUTBOUND_URL`).
- Физическая декомпозиция БД/очередей.
- Любые изменения бизнес-логики.

Touch-list (files/tables)
- docs/TASK_PACKAGES/TP-2026-01-28-qdrant-branch-backfill-ca13.md
- docs/SESSIONS/SESSION-2026-01-28-qdrant-branch-backfill-ca13-a1.md
- docs/SESSION_INDEX.md
- STATE.md

Plan (1..N)
1) Снять список веток с published knowledge + проверить доступность Qdrant/BGE.
2) Выполнить Qdrant backfill через `sync_qdrant_from_pack` для каждой ветки; сохранить лог `/tmp/qdrant_backfill_20260128.txt`.
3) Проверить Qdrant metadata фильтром по `client_slug` + `branch_id` (canary) и сохранить результат.
4) Выполнить live-check (demo_salon) и снять trace-bundle; убедиться, что `decision_meta.branch_id` и `rag_filter` использует branch.
5) Обновить `STATE.md` + session docs, приложить evidence paths.

DoD
- Для canary ветки есть Qdrant записи с `metadata.branch_id` (и `knowledge_tag`, если задан).
- Trace-bundle содержит `message.branch_id` и `decision_meta.rag_scores.bm25_filter.filter_reason=branch_id|knowledge_tag`.
- `decision_trace.rag_retrieve.rag_filter` использует branch filter (branch_id/knowledge_tag).
- Если `decision_meta.branch_id` не записывается для rag‑сообщений — фиксируем GAP (вне scope).
- Evidence (логи/trace-bundle) указаны в `STATE.md`.

Checks
- `python3 ops/diagnose.py livecheck-auto --suite ca06-consult --client-slug demo_salon`
- `python3 ops/diagnose.py trace-bundle --client-slug demo_salon --message-id sim-branch-a4-1768878520 --output /tmp/trace_bundle_ca13_branch_a_20260128.json`
- `python3 ops/diagnose.py trace-bundle --client-slug demo_salon --message-id sim-branch-b4-1768878534 --output /tmp/trace_bundle_ca13_branch_b_20260128.json`

Evidence
- `/tmp/qdrant_backfill_20260128.txt`
- `/tmp/qdrant_demo_salon_branch_a_points_20260128.json`
- `/tmp/qdrant_demo_salon_branch_b_points_20260128.json`
- `/tmp/trace_bundle_ca13_branch_a_20260128.json`
- `/tmp/trace_bundle_ca13_branch_b_20260128.json`
- `STATE.md` entry with CI/live-check metadata (conv_id/msg_id/outbox_id).

Rollback
- Повторный sync Qdrant из предыдущего published version.
- Восстановление Qdrant snapshot (ops/backup_qdrant.sh) при необходимости.

No-go
- Нет published knowledge для ветки.
- Live-check без allowlist/TEST_MODE.

Branch + Worktree + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-01-28-qdrant-branch-backfill-ca13-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-qdrant-branch-backfill-ca13-a1`
- Base ref: `origin/main`
- Merge: fast-forward (doc-only) после evidence
- Cleanup: удалить worktree/branch после merge
