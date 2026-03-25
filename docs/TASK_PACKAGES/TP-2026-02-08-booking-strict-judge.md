# TP-2026-02-08-booking-strict-judge

## Название/цель
Убрать ложные `OK` в LLM booking quality: ввести строгий fail-closed evaluator (`strict_pass_rate` + hard-fail причины), чтобы нерелевантные/неполные ответы, пропуски bot reply, ложные подтверждения записи и некорректное использование календарных инструментов не проходили как успех.

## Canon refs
- `STATE.md` (GAP: false-OK в llm-quality и недостоверная оценка диалогов).
- `AGENTS.md` (P0/P1/P2 fitness + stop-the-line).
- `SPECS/SYSTEM_REFERENCE.md` (LLM testing policy, trace/meta contracts, live-check evidence).
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
- `docs/SESSIONS/SESSION-2026-02-06-booking-quality-matrix-a14.md` (replay/frozen scenarios/missing_bot_reply контекст).

## Invariant
- FACT/COLLECT/HANDOFF и safety-гейты не меняются.
- `decision_meta`/`decision_trace` coverage не деградирует.
- Frozen сценарии не перезаписываются и не удаляются.
- Никаких ложных `OK`: критический семантический провал обязан давать `FAIL`.

## Scope
- Усилить `ops/diagnose.py llm-quality` строгими hard-fail правилами и отдельной метрикой `strict_pass_rate`.
- Явно различать `technical_pass` и `semantic_pass`; финальный `strict_ok` только при обоих.
- Добавить hard-fail для `missing_bot_reply` на frozen scenarios (`outbox/poll/timeout path`).
- Добавить hard-fail для ложного booking confirmation (подтверждение без достаточных сигналов/инструментального основания).
- Добавить проверки корректного calendar tool usage по trace/meta (когда сценарий требует booking/availability).
- Добавить/расширить unit тесты evaluator.
- Прогнать replay на `main`, `seed=1337`, только по готовому `--scenarios-file`.
- Обновить runbook для будущих агентов/людей: детальный SOP запуска, чтения артефактов, triage и next-step loop.

## Out of scope
- Изменение core runtime-пайплайна webhook/booking/policy.
- Перегенерация historical frozen сценариев и пересоздание baseline 3-дневного окна.
- Изменения БД схем/миграций.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_booking_quality_progress_gate.py`
- `truffles-api/tests/test_booking_quality_info_sections.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/SESSIONS/SESSION-2026-02-08-booking-strict-judge-a16.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Зафиксировать вход: выбрать frozen seed=1337 артефакт на main и baseline summary (read-only).
2) Проанализировать текущие false-OK в `responses.jsonl` + `summary.json` и формализовать strict hard-fail contract.
3) Реализовать evaluator изменения (`strict_ok`, hard-fail taxonomy, calendar/booking confirmation guards).
4) Добавить регрессии на hard-fail причины (включая `missing_bot_reply`).
5) Запустить таргетные pytest и replay `main seed=1337` через `--scenarios-file` без генерации.
6) Обновить runbook подробным SOP для будущих агентов и людей (быстрый старт + advanced triage + next actions).

## DoD
- В `summary.json` есть `strict_pass_rate` и список hard-fail причин.
- Диалоги с критическими semantic/technical ошибками больше не получают `OK`.
- Отдельно ловятся:
  - `missing_bot_reply_hard_fail`;
  - `false_booking_confirmation`;
  - `calendar_tool_contract_miss` (где применимо по ожиданию).
- Replay `main seed=1337` на frozen сценариях завершён; результаты воспроизводимы.
- Runbook обновлён детальной инструкцией с понятными next steps после каждого вида fail.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_info_sections.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/20260207-stress-main-seed-1337-gen/scenarios.json --baseline-summary /tmp/booking_quality/20260207-stress-main-seed-1337-gen/summary.json --count 10 --tool-hooks auto --reset-before-dialog --max-failures 20 --output-dir /tmp/booking_quality/20260208-strict-main-seed-1337-replay`

## Evidence
- `/tmp/booking_quality/20260208-strict-main-seed-1337-replay/summary.json`
- `/tmp/booking_quality/20260208-strict-main-seed-1337-replay/responses.jsonl`
- `/tmp/booking_quality/20260208-strict-main-seed-1337-replay/brief.md`
- pytest outputs for updated evaluator tests.
- session log + runbook update.

## Rollback
- `git revert SHA_FROM_THIS_BRANCH` в feature branch.
- Откат только кодовых/док-правок; historical artifacts не трогаем.

## No-go
- Не ослаблять safety-гейты ради метрик.
- Не подгонять evaluator под конкретные диалоги хардкодом по тексту.
- Не менять runtime-логику записи в календарь без отдельного TP.
- Не удалять и не перезаписывать готовые `/tmp/booking_quality/*` артефакты.

## Branch + Worktree
- Branch: `feat/2026-02-08-booking-strict-judge-a16`
- Worktree: `/home/zhan/worktrees/2026-02-08-booking-strict-judge-a16`
- Base ref: `origin/main`
- Merge policy: PR -> `main`
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch после merge

## Риски/блокеры
- Если replay зависает по внешней доставке/outbox polling, возможны false technical fails; mitigated через existing retry/backoff и explicit hard-fail taxonomy.
- Calendar tool contract должен опираться на существующие trace/meta поля; при недостатке сигналов часть кейсов будет `not_applicable`, а не ложный fail.
