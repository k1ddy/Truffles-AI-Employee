# TP-2026-01-30-signal-snapshot-layer

- Название/цель: Реализовать Signal Snapshot Layer (DEC-018) — единая сборка сигналов (pack‑index/anchors, semantic/RAG, LLM pack‑ref) и запись источников/версий в decision_meta/trace.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-018), `STATE.md` (PLAN: Unified Reasoning Core), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard‑LAW/policy/pending pre‑LLM; decision_meta/trace на каждый ранний возврат; без оркестрации в entrypoints/_legacy.py; порядок стадий не меняем.
- Scope:
  - Ввести Signal Snapshot объект/структуру на уровне decision pipeline.
  - Собрать сигналы из: domain_router anchors (client_config), pack‑lexicon/anchors (через snapshot), semantic/RAG, consult resolver, LLM pack‑ref output.
  - Писать в decision_meta: источники сигналов, thresholds/scores, pack versions/hash, fallback_reason.
  - Обеспечить, что OOD/booking/intent decisions используют snapshot как единый источник.
- Out of scope: pack‑index build/compile, LLM router schema enforcement, изменения паков/контента, refactor stage order.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/services/knowledge_snapshot_service.py`
  - `truffles-api/app/services/demo_salon_knowledge.py` (только если нужен доступ к pack lexicon)
  - `truffles-api/tests/test_message_endpoint.py`
- Plan:
  1) Найти точки генерации сигналов (domain_router, semantic, consult resolver, intent_decomp) и определить snapshot schema.
  2) Реализовать сборку snapshot и запись в decision_meta/trace.
  3) Подключить snapshot к OOD/booking/info routing (без изменения stage order).
  4) Добавить тесты на decision_meta.signal_snapshot.* и fallback_reason.
  5) Прогнать targeted pytest; зафиксировать evidence.
- DoD:
  - decision_meta содержит signal_snapshot с источниками/версиями паков.
  - OOD/booking решения используют snapshot (trace/meta подтверждают источник).
  - Тесты проходят; evidence в STATE.md до merge.
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot"`
- Evidence:
  - pytest output + decision_meta/trace пример (локально).
- Rollback: `git revert COMMIT_SHA`.
- No-go:
  - Никаких бизнес‑лексиконов в коде; только data‑driven.
  - Не менять порядок стадий; не добавлять логику в `_legacy.py`/entrypoints.
- Branch/worktree: `feat/2026-01-30-signal-snapshot-a1`, `/home/zhan/worktrees/2026-01-30-signal-snapshot-a1`, base `origin/main`, merge policy PR+CI, cleanup by Brain/Top Architect.
- Риски/блокеры: pack‑index ещё не внедрён — потребуется временная шина поверх текущих pack snapshot/anchors с явной пометкой источника.
