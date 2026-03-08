# TP-2026-03-04-e3-consultant-data-continuity-deep-audit-a1

## Block identity
- `BLOCK_ID`: `E3`
- `PARENT_BLOCK_ID`: `E2`
- `DEPENDS_ON`: `TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1.md`
- `UNLOCKS`: `E3.2 single-writer booking/profile transition`

## Название/цель
Провести deep audit по сбору/использованию клиентских данных консультантом и закрыть системный разрыв contact-continuity (`appointments` vs `users`) без ослабления LLM-first и quality-gates.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: Block E semantic blockers + degraded fallback)
- `docs/TASK_PACKAGES/TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/console.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/tests/test_booking_appointments.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT source, COUNT(*) AS total, COUNT(*) FILTER (WHERE customer_name IS NOT NULL AND btrim(customer_name) <> '') AS with_name, COUNT(*) FILTER (WHERE customer_phone IS NOT NULL AND btrim(customer_phone) <> '') AS with_phone FROM appointments GROUP BY source ORDER BY total DESC;"`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH bot_users AS (SELECT DISTINCT c.user_id FROM appointments a JOIN conversations c ON c.id=a.conversation_id WHERE a.source='bot' AND c.user_id IS NOT NULL) SELECT (SELECT COUNT(*) FROM bot_users) AS bot_users_total, (SELECT COUNT(*) FROM users u JOIN bot_users bu ON bu.user_id=u.id WHERE u.phone IS NOT NULL AND btrim(u.phone) <> '') AS bot_users_with_phone, (SELECT COUNT(*) FROM users u JOIN bot_users bu ON bu.user_id=u.id WHERE u.name IS NOT NULL AND btrim(u.name) <> '') AS bot_users_with_name;"`
  - `jq '.blocking_reasons,.metrics.rates.degraded_fallback_rate,.metrics.rates.hard_fail_rate' /tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/summary.json`
- `FACT findings`:
  - `booking-lock-20260305-firebreak-e2-a1-r22` full-completion, non-canonical: blockers `calendar_tool_contract_miss`, `stale_booking_carryover`, `judge_fail`; breaches on `hard_fail_rate`, `degraded_fallback_rate`.
  - Runtime data path writes contacts mostly into `appointments`, but `users` profile remains mostly empty for bot-created flows.
  - `calendar.book_slot` tool-path does not guarantee phone fallback from `remote_jid` nor profile materialization into `users`.
- `Detected drift (docs vs code)`: `present`
  - Product contract says `collect contacts`, while booking slot-order in code is `service/datetime/name` and profile persistence is fragmented.

## One web search (mandatory before implementation)
- **Query (exact):** `SQLAlchemy Session flush commit transaction boundaries official docs`
- **Date/time (local):** `2026-03-04 13:31, Asia/Almaty`
- **Why this query is precise:** Нужно подтвердить корректную стратегию для atomically-consistent записи данных профиля и booking в рамках одной транзакционной сессии без неявных race/side effects.
- **Sources opened (from this query):**
  - SQLAlchemy 2.0 Documentation: Session Basics — `https://docs.sqlalchemy.org/en/20/orm/session_basics.html`
  - SQLAlchemy 2.0 Documentation: State Management — `https://docs.sqlalchemy.org/en/20/orm/session_state_management.html`
- **Existing solutions found:** flush-before-commit discipline, single session unit-of-work, explicit commit boundaries for multi-entity consistency.
- **Decision:** `integrate` — применить единый write-boundary для booking contact continuity (tool call + profile sync metadata in same request lifecycle).
- **Rejected options:** prompt-only mitigation (не закрывает data continuity).
- **Open questions:** нужен ли отдельный `EXPECTED_REPLY_PHONE` как новый контрактный слой (вне текущего блока).

## Root cause (mandatory)
- **Symptom:**
  - Acceptance lock non-canonical due booking/tool continuity defects.
  - Contact data сохраняется непоследовательно: в `appointments` есть, в `users` часто отсутствует.
- **Minimal reproduction:**
  1. Запустить/проверить lock `booking-lock-20260305-firebreak-e2-a1-r22`.
  2. Выполнить SQL-агрегаты по `appointments` и `users` для bot-source.
  3. Проверить `calendar.book_slot` path (`execute_tool_action`) и передачу `user_phone`.
- **Evidence to capture:**
  - `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/{summary.json,responses.jsonl,trace_bundle.jsonl}`
  - SQL snapshots from `chatbot` DB (`appointments/users/conversations`)
- **Five Whys (or equivalent):**
  1. Почему semantic blockers остаются? — Нет единого terminal contract в edge booking/tool branches.
  2. Почему контакты теряются в платформе? — `users` профиль не синхронизируется с booking contact snapshots.
  3. Почему это не ловится раньше? — Гейты покрывают semantic/trace, но не enforce cross-table identity continuity.
  4. Почему архитектура это допускает? — Multi-writer orchestration (decision + tool + booking + console read-model).
  5. Почему риск растет с масштабом? — Каждый новый домен добавляет вариативность, а единый owner перехода отсутствует.
- **Root cause statement:** В core отсутствует контрактный single-writer для связки `tool outcome -> contact materialization -> profile read-model`, из-за чего данные клиента деградируют между слоями even when booking action succeeds.
- **Fix mechanism:** Ввести boundary guard на contact continuity в booking tool-path (phone fallback from `remote_jid`, deterministic metadata) и синхронизацию профиля пользователя в decision-path на успешный `calendar.book_slot`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Existing booking normalizers (`booking_signal_service.normalize_phone_digits`).
  - Existing expected-reply/decision meta contracts.
  - Existing booking/tool tests (`test_booking_appointments.py`, `test_message_endpoint.py`).
- **External reuse:** SQLAlchemy session unit-of-work patterns from official docs.
- **Why not reinvent the wheel:** Нужен точечный deterministic boundary fix в существующем flow, не новый orchestration framework.

## Invariant
- LLM-first semantic ownership сохраняется.
- Deterministic logic только на boundary/data integrity.
- Никаких phrase-hardcode и ослабления acceptance gates.

## Scope
- Deep audit findings formalization for contact continuity risk.
- Code fix:
  - `calendar.book_slot`: fallback phone derivation from `remote_jid`.
  - Decision booking success: profile sync (`user.name/user.phone`) + observability meta.
- Deterministic tests for new contract.

## Out of scope
- Полный рефактор `decision.py` в модульный single-writer (это E3.2).
- Новый expected-reply type `phone` и глобальная migration сценариев.
- Canary/full rollout.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-e3-consultant-data-continuity-deep-audit-a1.md`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_message_endpoint.py`
- `STATE.md`

## Plan (1..N)
1. Зафиксировать deep-audit фактами (quality + SQL + code-path).
2. Внедрить contact continuity guard (`user_phone` fallback + tool metadata).
3. Внедрить profile materialization на успешном booking в decision path.
4. Добавить deterministic regression tests.
5. Прогнать таргетные тесты и зафиксировать evidence.
6. Обновить `STATE.md` с вердиктом E3.

## DoD
- Для booking tool-path телефон не теряется при наличии `remote_jid` (deterministic fallback).
- После успешного `calendar.book_slot` профиль `user` в request lifecycle синхронизируется по `name/phone` при отсутствии значений.
- Новые тесты добавлены и проходят.
- `STATE.md` обновлён фактами и residual debt.

## Checks
- `pytest -q truffles-api/tests/test_booking_appointments.py -k "book_slot_uses_remote_jid_phone_fallback"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_collect_with_full_slots_normalizes_to_book_slot"`

## Evidence
- Test output from commands in `Checks`.
- SQL snapshots (pre/post) for bot contact continuity.
- Updated `STATE.md` entry with explicit evidence paths.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (no expensive llm-quality run in this block).
- **Fail-fast / scenario lock:** deterministic test subset only.
- **Stop condition:** any regression in booking/tool core tests.
- **Escalation path:** Brain/Top Architect decides if acceptance lock rerun is needed immediately after E3.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local deterministic guard fix only; no direct rollout.
- **Go/no-go signals:** targeted tests pass; no regression in touched contract.
- **Rollback:** revert E3 commit.
- **Post-release monitoring window:** next acceptance lock (`E2/E3 chained`) before canary.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
- `Drift closeout rule`:
  - If full single-writer not in scope, record as explicit residual debt with follow-up TP.

## Rollback
- `git revert <commit_sha_of_E3>` and keep E2 blocked.

## No-go
- Не добавлять prompt-only workaround вместо data continuity fix.
- Не менять thresholds/gates для прохождения.
- Не вводить tenant-specific hardcode.

## Risks/Blockers
- Возможны скрытые paths вне `calendar.book_slot` (legacy/manual).
- Если появится требование strict phone-before-booking, понадобится новый `EXPECTED_REPLY_PHONE` контракт (вне E3).

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: large multi-writer orchestration in `decision.py`; no full single-writer transition engine yet.
- `Why not in this block`: нужно закрыть risk быстро и минимально-инвазивно.
- `Risk if deferred`: повторные continuity drift в новых доменах/каналах.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-e3.2-single-writer-booking-profile-transition-a1.md`.
- `Expiry/trigger to stop deferral`: любой следующий acceptance fail с `calendar_tool_contract_miss` или profile continuity breach.

## Next-block contract (mandatory)
- `Next block objective`: выделить единый owner transition для `booking/tool/profile` и добавить cross-table gate.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "calendar_tool_contract_miss or stale_booking_carryover"`
- `Blocked-by conditions`: E3 deterministic tests must pass.
- `Owner role for closure`: Hands (impl/tests), Brain+Top Architect (acceptance + merge).

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/tool_registry_service.py` and `truffles-api/app/routers/webhook/decision.py`
- `Do not touch`: acceptance thresholds/gates and unrelated tenant logic.
- `Open risks`: missing explicit phone expected-reply contract.
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_appointments.py -k "book_slot_uses_remote_jid_phone_fallback"`
