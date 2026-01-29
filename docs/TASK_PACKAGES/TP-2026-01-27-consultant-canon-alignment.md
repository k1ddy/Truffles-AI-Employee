# TP-2026-01-27 — Consultant Canon Alignment + Media/ASR Ordering

- Название/цель: привести консультанта и медиа-потоки к канонам (consult-first, pack-first, no-dictionaries) + устойчивость для фото/аудио и уведомлений.
- Canon refs: `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`, `STATE.md` (NOW/GAP).
- NOW (2026-01-27):
  - Тесты:
    - `pytest -q truffles-api/tests/test_message_endpoint.py` → 112 passed.
    - `pytest -q truffles-api/tests/test_message_endpoint.py::test_consult_precedence_over_booking_flow` → passed.
    - `pytest -q truffles-api/tests/test_demo_salon_eval.py::test_consult_pack_only_and_short_circuit` → passed.
    - `EVAL_TIER=core pytest -q truffles-api/tests/test_demo_salon_eval.py::test_demo_salon_eval_cases` → passed.
    - `pytest -q truffles-api/tests/test_webhook_response.py` → 6 passed.
    - `docker exec truffles-api pytest -q /app/tests/test_message_endpoint.py` → 37 failed, 73 passed (container code).
    - `docker compose exec truffles-api pytest -q /app/tests/test_message_endpoint.py` → 7 failed, 105 passed (worktree image, service env).
    - `docker compose exec -e OPENAI_API_KEY= -e KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED=0 ... pytest -q /app/tests/test_message_endpoint.py` → 2 failed, 110 passed.
    - `docker compose exec truffles-api env -i PATH=/usr/local/bin:/usr/bin:/bin PYTHONPATH=/app pytest -q /app/tests/test_message_endpoint.py` → 112 passed.
    - `docker compose exec truffles-api env -i PATH=/usr/local/bin:/usr/bin:/bin PYTHONPATH=/app pytest -q /app/tests/test_demo_salon_eval.py::test_consult_pack_only_and_short_circuit` → passed.
    - `docker compose exec truffles-api env -i PATH=/usr/local/bin:/usr/bin:/bin PYTHONPATH=/app pytest -q /app/tests/test_webhook_response.py` → 6 passed.
    - `docker compose exec truffles-api env -i CI=1 PATH=/usr/local/bin:/usr/bin:/bin PYTHONPATH=/app pytest -q /app/tests -vv` → 463 passed.
  - Канон: добавлены пункты про signal/noise, intent_queue, media/ASR ordering, escalation notice (см. SPECS).
- NEXT:
  - При необходимости: контейнерный прогон перед финальной приёмкой.
  - Подготовить запись в `STATE.md` с evidence (Brain/Top Architect).
- Invariant:
  - Hard‑LAW/Policy/opt‑out/pending гейты выше consult/booking.
  - Факты бизнеса только из pack/tools; без выдумок.
  - Pending/manager_active — бот молчит (кроме статусов).
- Scope:
  - Канон: consult‑first, pack‑first, no‑dictionaries, quiet‑hours TTL, вечернее приветствие, media/ASR ordering.
  - Документация: onboarding‑инструкции для новых агентов в `docs/CONSULTANT_CODEMAP.md`.
  - Код: consult flow (order, fallback), media style reference pending, ASR inflight, escalation notice.
  - Код (поддержка канона/устойчивости): preflight branch phone guard, ChatFlow outbound env overrides,
    consult topic resolver fallback=none (без словарей), вечернее приветствие builder.
  - Тесты: consult precedence, short‑circuit rules, notices, media/order guards, knowledge_service expectations.
- Out of scope:
  - UI/Console/DB‑миграции, новые роли/онбординг, внешние интеграции.
- Touch-list (files):
  - `SPECS/CONSULTANT.md`
  - `SPECS/ESCALATION.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `docs/CONSULTANT_CODEMAP.md`
  - `docs/SESSION_INDEX.md`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/media.py`
  - `truffles-api/app/services/chatflow_service.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/services/knowledge_service.py`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_knowledge_service.py`
  - `truffles-api/tests/test_webhook_response.py`
- Plan:
  1) Обновить канон в `SPECS/*` (consult-first/pack-first, media/ASR ordering, quiet-hours TTL, escalation notice).
  2) Обновить consult‑flow (убрать explicit‑info short‑circuit при consult_intent, запретить legacy/LLM fallback, порядок ответов).
  3) Добавить media/ASR guardrails (style_reference_pending TTL, ASR inflight notice, escalation warning).
  4) Обновить onboarding‑инструкции для новых агентов в `docs/CONSULTANT_CODEMAP.md`.
  5) Обновить/добавить тесты под новые правила.
  6) Локальные проверки.
- DoD:
  - Канон обновлён и синхронизирован со спецификациями.
  - Consult‑ответ всегда первым при consult‑интенте; факты добавляются только при наличии в pack/tools.
  - Нет LLM‑советов/legacy‑словари для consult.
  - Фото/аудио обрабатываются с учётом очереди/TTL и эскалационных предупреждений.
  - `docs/CONSULTANT_CODEMAP.md` содержит чек‑лист для новых агентов и ссылки на канон.
  - Тесты проходят.
- Checks:
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py::test_consult_pack_only_and_short_circuit`
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_consult_precedence_over_booking_flow`
  - `pytest -q truffles-api/tests/test_webhook_response.py`
- Evidence:
  - Вывод pytest + обновлённые спецификации.
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_consult_precedence_over_booking_flow` (passed).
  - `EVAL_TIER=core pytest -q truffles-api/tests/test_demo_salon_eval.py::test_demo_salon_eval_cases` (passed).
  - Запись в `STATE.md` с фактами и evidence после проверок.
- Rollback:
- `git revert COMMIT_SHA` или откатить изменения в перечисленных файлах.
- No-go:
  - Не менять контракты DB/миграции.
  - Не добавлять новую orchestration‑логику в entrypoints/_legacy.py.
  - Не ослаблять Hard‑LAW/Policy/opt‑out/pending гейты.
- Риски/блокеры:
  - Падение существующих тестов consult‑flow (потребуются обновления ожиданий).
  - Нужны уточнения по TTL/вечернему приветствию — зафиксировать в каноне.
