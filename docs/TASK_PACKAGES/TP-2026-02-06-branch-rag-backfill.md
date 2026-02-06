# TP-2026-02-06-branch-rag-backfill

- Название/цель: Добавить безопасный скрипт backfill для branch‑RAG (re‑sync Qdrant по опубликованным knowledge_versions с `branch_id`/`knowledge_tag`).
- Canon refs: `SPECS/MULTI_TENANT.md` (RAG strict branch filter + backfill), `STATE.md` (GAP branch‑RAG backfill), `SPECS/SYSTEM_REFERENCE.md`.
- Invariant:
  - Никаких изменений поведения core/LLM/LAW/policy.
  - Tenant isolation не ослабляется.
  - Никаких ручных правок БД/decision_trace ради evidence.
- Scope:
  - Скрипт `ops/backfill_branch_rag.py` с dry‑run по умолчанию.
  - Использование published knowledge_versions для каждого branch.
  - Логи + summary по branches.
- Out of scope:
  - Реальный запуск backfill на проде.
  - Live‑check/CA‑13 evidence.
  - Изменения паков/консоли.
- Touch-list (files/tables):
  - `ops/backfill_branch_rag.py` (new)
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-02-06-branch-rag-backfill.md`
  - `docs/SESSIONS/SESSION-2026-02-06-runtime-capabilities-a10.md`
- Plan:
  1) Реализовать скрипт backfill (dry‑run by default, `--execute` to run).
  2) Проверить локальный запуск в dry‑run режиме.
  3) Обновить session log.
- DoD:
  - Скрипт выводит список branches с published knowledge и план синка.
  - При `--execute` вызывает `sync_qdrant_from_pack` для каждого branch.
- Checks:
  - `python3 ops/backfill_branch_rag.py --dry-run` (локально).
- Evidence:
  - `/tmp/backfill_branch_rag_dryrun_20260206.txt` (dry‑run лог).
- Rollback:
  - Нет (dry‑run). Для реального запуска — повторный sync из published версии.
- No-go:
  - Любые изменения БД/trace ради evidence.
  - Запуск без явного `--execute`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-06-runtime-capabilities-a10`
  - Worktree: `/home/zhan/worktrees/2026-02-06-runtime-capabilities-a10`
  - Base: `origin/main`
  - Merge: PR
  - Cleanup: `scripts/session_end.sh --status done` + удалить worktree/branch
- Риски/блокеры:
  - Требуются доступы к DB/Qdrant/BGE для реального запуска.
