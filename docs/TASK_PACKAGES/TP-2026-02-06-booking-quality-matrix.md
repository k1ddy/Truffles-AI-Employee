# TP-2026-02-06-booking-quality-matrix

## Название/цель
Стабилизировать booking‑поведение на реальных перебивках и ошибочных ответах по слотам (service/date/time/name/phone): обновить генератор сценариев, провести LLM‑quality матрицу (seed 42/1337/2026, count=10), и подтвердить реальную запись в БД на реальных мастеров (demo_salon/branch_b).

## Canon refs
- `STATE.md` (GAP: booking dialogs missing replies/unknown_state; booking flow stalls).
- `STRATEGY/REQUIREMENTS.md`.
- `SPECS/CONSULTANT.md`.
- `SPECS/SYSTEM_REFERENCE.md`.
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
- `AGENTS.md` (P0/P1/P2 fitness + session rules).

## Invariant
- FACT/COLLECT/HANDOFF сохраняется (не меняем policy/LAW приоритеты).
- decision_meta/decision_trace обязателен на каждом inbound.
- booking_interrupt сохраняется при перебивках; expected_reply_type не сбрасывается от шума.
- `_legacy.py` = adapter‑only; entrypoints без оркестрации.
- outbox idempotency и trace retention не ломаем.

## Scope
- Проверить/создать реальных мастеров и услуги в demo_salon/branch_b (specialists/services/specialist_services), выставить рабочие часы для слотов.
- Обновить `scripts/booking_dialog_scenarios.py`: реальные услуги из demo_salon pack + явные «не по слоту» ответы (service/date/time/name/phone) + постоянные перебивки/шум.
- Обновить `ops/diagnose.py`: поддержать `allow_booking_stall` в ожиданиях, чтобы валидно проверять «не по слоту» ответы без ложных фейлов.
- Обновить `scripts/booking_confirm_verify.sh`/`ops/diagnose.py livecheck-auto`: выбор branch_slug для корректного instance_id.
- Добавить поддержку выбора мастера в booking‑tool: `specialist_name` в LLM‑plan prompt + маппинг name → specialist_id в tool registry (fallback: если по услуге ровно один мастер, использовать его).
- Провести 3 LLM‑quality прогона (seed 42/1337/2026, count=10, include_media, coverage booking/info/interrupt/handoff, tool‑hooks auto), после каждого зафиксировать top‑3 failures и конкретное следующее действие.
- Подтвердить реальную запись через runbook (`scripts/booking_confirm_verify.sh --apply --cancel-appointments`) и снять SQL evidence.

## Out of scope
- long‑eval и любые ночные/долгие прогоны.
- Изменения core‑пайплайна, policy/LAW, pack‑контента, миграции.
- Любые non‑demo_salon клиенты.

## Touch-list
- `scripts/booking_dialog_scenarios.py`
- `ops/diagnose.py`
- `scripts/booking_confirm_verify.sh`
- `prompts/llm_plan.md`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/decision.py`
- `docs/TASK_PACKAGES/TP-2026-02-06-booking-quality-matrix.md`
- `docs/SESSIONS/SESSION-*.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- Таблицы: `clients`, `branches`, `specialists`, `services`, `specialist_services`, `appointments`, `appointment_sync_states`, `calendar_blocks`, `calendar_connections`, `google_calendar_tokens`, `calendar_sync_cursors`, `outbox_messages`, `messages`, `conversations`.

## Plan
1) Preflight: найти client_id/branch_id demo_salon/branch_b; проверить наличие specialists/services/working_hours.
2) Если мастеров/услуг нет — создать 2–3 специалистов и услуги, связать через specialist_services; задать рабочие часы (branch или specialist).
3) Обновить генератор сценариев: сервисы из demo_salon pack + явные «не по слоту» ответы (service/date/time/name/phone), сохранить expect‑правила.
4) Обновить LLM‑quality evaluator: `allow_booking_stall` в ожиданиях.
5) Добавить поддержку выбора мастера: расширить prompt LLM‑plan (specialist_name) + маппинг name → specialist_id в tool registry.
6) Запустить LLM‑quality матрицу (3 прогона) и зафиксировать top‑3 failures + конкретные next steps; правки делать только если причина ясна.
7) Запустить `scripts/booking_confirm_verify.sh --apply --cancel-appointments` и собрать SQL evidence (appointments/outbox/trace/meta), убедиться что specialist_id не NULL.
8) Обновить `STATE.md` с evidence и краткой сводкой.

## DoD
- В demo_salon/branch_b есть активные мастера + услуги; слоты выдаются (working_hours задан).
- Сценарии содержат неправильные ответы по слотам (service/date/time/name/phone) и перебивки; smoke‑run генератора проходит; evaluator не считает это ложным stall.
- 3 LLM‑quality прогона завершены; по каждому есть top‑3 failures и шаги фикса (или обоснованный стоп).
- Booking confirm подтверждён реальной записью в БД и outbox (SQL evidence + trace/meta), appointment.specialist_id не NULL.
- `STATE.md` обновлён с ссылками на evidence.

## Checks
- SQL preflight (specialists/services/working_hours).
- `python3 scripts/booking_dialog_scenarios.py --count 1 --min-turns 10 --max-turns 16 --coverage booking,info,interrupt --include-media --output /tmp/booking_dialog_scenarios_smoke_20260206.json`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --seed 42`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/booking-lock-42/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-42/summary.json --count 10 --tool-hooks auto --reset-before-dialog --max-failures 20`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --seed 1337`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --seed 2026`
- `scripts/booking_confirm_verify.sh --client-slug demo_salon --branch-slug branch_b --apply --cancel-appointments`
- SQL: `SELECT id, specialist_id, start_at, status FROM appointments WHERE branch_id = '2e9f5a9d-50a2-4b07-8e54-da2cac2ac751' ORDER BY created_at DESC LIMIT 5;`

## Evidence
- `/tmp/booking_quality/20260206-064148/summary.json`, `responses.jsonl`, `scenarios.json`, `trace_bundle.jsonl` (пример LLM‑quality прогона; для матрицы будут 3 прогона).
- `/tmp/booking_quality/booking-lock-42/brief.md` (top failures + replay command for next agent).
- `/tmp/sql_*` дампы для specialists/services/working_hours.
- `/tmp/livecheck_ca05_booking*`, `/tmp/livecheck_ca12_booking_full*` и SQL evidence из `booking_confirm_verify`.
- запись в `STATE.md`.

## Rollback
- Данные: отключить тестовых специалистов/услуги (`is_active=false`), вернуть `branches.working_hours` в `{}` при необходимости.
- Код: revert commit.

## No-go
- Любые изменения policy/LAW или core‑пайплайна.
- pytest внутри prod контейнера; docker‑cp/‑v hacks.
- long‑eval или прогоны без плана следующего действия.

## Branch + Worktree
- Branch: `feat/2026-02-06-booking-quality-matrix-a14`
- Worktree: `/home/zhan/worktrees/2026-02-06-booking-quality-matrix-a14`
- Base ref: `origin/main`
- Merge policy: PR -> `main`
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch

## Риски/блокеры
- Нет allowlist JID или `TEST_MODE=1` → LLM‑quality/livecheck невозможны.
- Нет provider токенов → booking confirm может уйти в provider‑not‑ready.
- При отсутствии working_hours/masters слоты пустые.
