# TP-2026-02-01-scn-multiturn-eval

- Название/цель: добавить multi-turn oracle SCN1–SCN5 и внедрить "soft pending" (pending не блокирует in-domain info/booking/consult).
- Canon refs: `STATE.md` (OPEN: chaos-sim residuals), `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ARCHITECTURE.md`.
- Invariant:
  - Hard-LAW/Policy по-прежнему эскалирует; новые handover не создаём в `pending`.
  - `decision_meta/decision_trace` пишутся на каждом раннем возврате.
  - `_legacy.py` и entrypoints не трогаем.
- Scope:
  - multi-turn SCN1–SCN5 (`turns`) в `EVAL.yaml`.
  - soft pending: в `pending` разрешить ответы по in-domain запросам (info/booking/consult) без новых handover.
  - правка текста policy-pack, чтобы не обещать "бот не отвечает" при soft pending.
  - синхронизация SPECS под soft pending.
- Out of scope:
  - перестановка стадий decision-graph.
  - изменения LLM контрактов/индексации packs.
- Touch-list:
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `truffles-api/app/knowledge/demo_salon/EVAL.yaml`
  - `SPECS/CONSULTANT.md`
  - `SPECS/ESCALATION.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `docs/SESSIONS/SESSION-2026-02-01-scn-multiturn-eval-a4.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-01-scn-multiturn-eval.md`
- Plan:
  1) Обновить TP/сессию под soft pending.
  2) Разрешить soft pending в routing + pending guard; обновить policy-pack фразу.
  3) Обновить SPECS (pending guard исключения, trace/meta).
  4) Прогнать `EVAL_TIER=chaos` и зафиксировать evidence.
- DoD:
  - SCN1–SCN5 multi-turn oracle присутствует.
  - В `pending` in-domain запросы получают обычные ответы, без новых handover.
  - EVAL прогоны зафиксированы.
- Checks:
  - `EVAL_TIER=chaos pytest -q truffles-api/tests/test_demo_salon_eval.py::test_demo_salon_eval_cases`
- Evidence:
  - `/tmp/pytest_scn_multiturn_20260201.txt`
  - `/tmp/pytest_scn_multiturn_soft_pending_20260201e.txt`
- Rollback:
  - `git revert COMMIT_SHA`
- No-go:
  - правки `_legacy.py`/entrypoints.
  - "словарные" хардкоды в коде вместо pack-сигналов.
- Branch/worktree:
  - branch: `feat/2026-02-01-scn-multiturn-eval-a4`
  - worktree: `/home/zhan/worktrees/2026-02-01-scn-multiturn-eval-a4`
  - base: `origin/main`
  - merge: PR (no rebase)
  - cleanup: Brain/Top Architect
- Риски/блокеры:
  - `pending` больше не "мьютит" ответы, нужно явно закрепить канон + QA через trace/meta.
