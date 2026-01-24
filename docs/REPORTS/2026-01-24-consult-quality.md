# Отчёт: consult quality + chaos‑sim (2026‑01‑24)

**Scope:** TP `docs/TASK_PACKAGES/TP-2026-01-24-consult-quality-core-v1.md`.

**Branch/PR:**
- Branch: `consult/quality-fix-v1`
- PR: https://github.com/k1ddy/Truffles-AI-Employee/pull/333
- Commit: `894b76c5`

---

## 1) Что сделано (код/доки)

**Core поведение:**
- Pending‑gate выполняется **до** shield, чтобы pending‑ответы не перебивались shield‑drop.
  - Код: `truffles-api/app/routers/webhook/decision.py`
- Consult‑ответ **не сбрасывает booking‑goal**: если запись активна, consult отвечает и **добавляет booking‑prompt**.
  - Код: `truffles-api/app/routers/webhook/response.py`
- `current_goal` теперь учитывает `expected_reply_type` (booking‑lock) при резолве.
  - Код: `truffles-api/app/routers/webhook/context_manager.py`

**Тестовый кейс:**
- Добавлен EVAL‑кейс `E905` (consult + booking). 
  - Код: `truffles-api/app/knowledge/demo_salon/EVAL.yaml`

**Документация:**
- Новый Task Package: `docs/TASK_PACKAGES/TP-2026-01-24-consult-quality-core-v1.md`
- Обновления карт: `STRUCTURE.md`, `STATE.md`
- Новый код‑мап консультанта: `docs/CONSULTANT_CODEMAP.md`

---

## 2) Симуляция: статус и польза

**Что уже реализовано:**
- Chaos‑sim (10–15 ходов, RU/KZ/mixed + шум) → `ops/diagnose.py chaos-sim`.
- Оценка по `decision_meta`/`decision_trace` (не по тексту).
- RAG‑audit артефакты: `rag_debug.jsonl`, `rag_summary.json`.
- Детальный отчёт по фейлам: `summary.json`, `failures.jsonl`, `report.md`.

**Что даёт:**
- Быстрое выявление системных паттернов (multi‑intent, pending, goal‑drop).
- Массовая диагностика RAG по языку/шуму.
- Сравнение logic/llm режимов без ручной проверки чатов.

**Что ещё нужно улучшить:**
- Реальные Telegram/Console API (интеграционный слой).
- Конкурентные/дубликатные inbound и задержки сети.
- Media/ASR сценарии (voice‑ошибки, edits/удаления).

---

## 3) Тесты и артефакты (evidence)

**Logic run (20 кейсов):**
- Команда:
  - `PYTHONUNBUFFERED=1 python3 ops/diagnose.py chaos-sim --count 20 --seed 42 --mode logic --client-slug demo_salon --skip-outbox --min-wait 0 --max-wait 0.05 --poll-timeout 3 --poll-interval 0.2 --min-turns 10 --max-turns 12 --noise high --debug-all --console-mode skip --admin-token alerts-admin --rag-audit`
- Summary: `cases=20`, `turns=202`, `failures=154`
- Артефакты:
  - `ops/artifacts/chaos_sim/20260124-023007/summary.json`
  - `ops/artifacts/chaos_sim/20260124-023007/rag_debug.jsonl`
  - `ops/artifacts/chaos_sim/20260124-023007/rag_summary.json`

**LLM run (10 кейсов):**
- Команда:
  - `PYTHONUNBUFFERED=1 python3 ops/diagnose.py chaos-sim --count 10 --seed 42 --mode llm --client-slug demo_salon --skip-outbox --min-wait 0 --max-wait 0.05 --poll-timeout 3 --poll-interval 0.2 --min-turns 10 --max-turns 12 --noise high --debug-all --console-mode skip --admin-token alerts-admin --rag-audit`
- Summary: `cases=10`, `turns=101`, `failures=82`
- Артефакты:
  - `ops/artifacts/chaos_sim/20260124-024157/summary.json`
  - `ops/artifacts/chaos_sim/20260124-024157/rag_debug.jsonl`
  - `ops/artifacts/chaos_sim/20260124-024157/rag_summary.json`

---

## 4) Что выяснили по итогам прогонов

**Системные паттерны (не частные кейсы):**
- `pending_action_mismatch`/`state_mismatch`: ожидания генератора часто расходятся с реальным pending‑поведением.
- `expected_reply_type_mismatch`: booking‑interrupt/quiet‑hours и очередность prompts.
- `ood_false_positive`: часть in‑domain уходов маркируется как OOD при шуме.
- `consult_playbook_mismatch`: в редких случаях сервис‑семантика перехватывает consult.

**RAG‑audit:**
- Logic‑run: все turns → `overridden_by_gate` (ожидаемо при logic‑mode без LLM).
- LLM‑run: `rag_empty` + `branch_filter_empty` на части кейсов (требует подтверждения: фильтр branch/knowledge).

**Что изменили по результатам тестов:**
- Pending‑gate перенесён перед shield.
- Consult‑reply больше не перезаписывает booking‑goal, добавляется booking‑prompt.
- Добавлен EVAL‑кейс consult+booking (E905).

---

## 5) Что требует подтверждения (канон vs ожидания)

1) **Pending‑поведение** — в каноне pending всегда доминирует. Нужно решить, какие ответы допустимы (pending_status vs pending_wait vs shield_drop), и затем привести генератор ожиданий или логику.
2) **Expected reply при booking‑interrupt** — уточнить правила, когда `expected_reply_type` должен сохраняться (quiet hours, info‑interrupt, consult‑reply).
3) **RAG‑audit причины** — подтвердить, что `overridden_by_gate` в logic‑mode и `branch_filter_empty` в llm‑mode — это норма либо дефект конфигурации.

---

## 6) Когда и что делать по 3 пунктам

**Сразу после merge (до полного 1000‑прогона):**
1) Разобрать `pending_action_mismatch/state_mismatch`:
   - Сверить канон (`SPECS/CONSULTANT.md`) и текущий evaluator в `ops/diagnose.py`.
   - Решение: либо обновить expectations в генераторе, либо усилить pending‑gate.

**Следующим шагом (после 1):**
2) Уточнить `expected_reply_type` при booking‑interrupt и quiet hours:
   - Подтвердить правило в `SPECS/CONSULTANT.md` (goal‑lock при booking).
   - Внести корректировки в chaos‑evaluator, чтобы не ловить ложные фейлы.

**Параллельно (можно после 1):**
3) RAG‑audit причины `overridden_by_gate` / `branch_filter_empty`:
   - Проверить в `rag_debug.jsonl` фильтры и `rag_filter_reason`.
   - Решить: это нормальная деградация, или неправильная фильтрация branch/knowledge.

**После подтверждения 1‑3:**
- Разобрать `failures.jsonl` и предложить 1–2 **общих** фикса (не под кейсы).

---

## 7) Риски и блокеры

- **Risk:** ожидания симулятора расходятся с каноном → много false‑positive.
- **Risk:** logic‑mode не показывает реальную RAG‑эффективность → нужен LLM‑subset.
- **Blocker:** нет интеграционного слоя с реальными Telegram/Console API (это отдельный этап).

---

## 8) Как продолжать (для новых dev/агентов)

1) Прочитать `docs/CONSULTANT_CODEMAP.md` (код‑мап).
2) Прочитать `SPECS/CONSULTANT.md` (канон).
3) Проверить артефакты chaos‑sim в `ops/artifacts/chaos_sim/*`.
4) Решить пункт 1–3 из раздела 6, затем запускать 1000–1500 кейсов.

