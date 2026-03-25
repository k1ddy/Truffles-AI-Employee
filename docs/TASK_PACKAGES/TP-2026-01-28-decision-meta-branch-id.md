# TP-2026-01-28 — Decision meta branch_id for RAG messages

Название/цель (1–2 предложения)
- Добавить `decision_meta.branch_id` (и `knowledge_tag` при наличии) в RAG‑метаданные для user‑сообщений, чтобы CA‑13 evidence не теряла ветку при rag_search.

Invariant
- Поведение core/LLM/LAW/policy не меняется.
- `_legacy.py` и entrypoints без новой оркестрации.
- Trace/meta пишется на каждом раннем возврате.

Scope
- Обновить запись `decision_meta` при `_record_rag_meta` с `branch_id/knowledge_tag` из `timing_context`.
- Добавить тест на наличие `decision_meta.branch_id` в RAG‑пути.
- Зафиксировать evidence в `STATE.md` (тесты/логи).

Out of scope
- Изменение бизнес‑логики/маршрутизации.
- Обновления схем/контрактов/миграций.

Touch-list (files/tables)
- truffles-api/app/routers/webhook/response.py
- truffles-api/tests/test_message_endpoint.py
- docs/TASK_PACKAGES/TP-2026-01-28-decision-meta-branch-id.md
- docs/SESSIONS/SESSION-2026-01-28-decision-meta-branch-id-a1.md
- docs/SESSION_INDEX.md
- STATE.md

Plan (1..N)
1) Добавить `branch_id/knowledge_tag` в `_record_rag_meta` (не затирать существующие значения).
2) Обновить тест `test_rag_rewrite_and_scores_logged` или добавить новый, чтобы `decision_meta.branch_id` фиксировался при rag_trace.
3) Запустить targeted pytest.
4) Обновить `STATE.md` и session docs с evidence.

DoD
- Для RAG‑пути `decision_meta.branch_id` присутствует, если `timing_context` содержит `branch_id`.
- Тесты проходят.
- Evidence указан в `STATE.md`.

Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "rag_rewrite_and_scores_logged or record_rag_meta_sets_branch_id"`

Evidence
- Вывод pytest (или CI).
- Обновление `STATE.md` с reference на тест.

Rollback
- Откат коммита.

No-go
- Любая новая оркестрация в `_legacy.py` или entrypoints.

Branch + Worktree + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-01-28-decision-meta-branch-id-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-decision-meta-branch-id-a1`
- Base ref: `origin/main`
- Merge: merge commit (code change)
- Cleanup: удалить worktree/branch после merge
