# TP-2026-03-02-p4-expected-reply-full-closure-a1

## Block identity
- `BLOCK_ID`: SIG-P4-EXPECTED-REPLY-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: none
- `UNLOCKS`: `P4 Expected-Reply Refactor` -> `done`

## Название/цель
Полностью закрыть `P4`: expected-reply остается только boundary contract/state, а semantic routing и action selection происходят через policy-core + resolver contract, без router-branching по `expected_reply_type`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/expected_reply_contract.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_expected_reply_contract.py`
- `Baseline commands`:
  - `rg -n "expected_reply_type|expected_reply_matched|expected_reply_blocked_by_info" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py`
  - `rg -n "_apply_expected_reply_contract|should_skip_booking_interrupt_for_expected_reply" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/expected_reply_contract.py`
- `FACT findings`:
  - `expected_reply_contract.py` существует и используется, но router coupling по expected-reply в `booking.py`/`info.py` еще присутствует.
  - В `P4a` уже вынесен один booking gate в `should_skip_booking_interrupt_for_expected_reply`, но это не закрывает весь `P4`.
- `Detected drift (docs vs code)`: parent TP фиксирует `P4 partial`, drift отсутствует.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa validation action separate from dialogue policy slot validation docs`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** требуется reference pattern разделения state/slot validation и dialogue policy routing.
- **Sources opened (from this query):**
  - Rasa Validation Action: `https://rasa.com/docs/reference/integrations/action-server/validation-action/`
  - Rasa Domain/slots: `https://rasa.com/docs/reference/primitives/domain/`
- **Existing solutions found:** validation/state logic должна быть boundary layer, policy-routing отдельно.
- **Decision:** `integrate` текущий `expected_reply_contract.py` как boundary-only слой и убрать router semantic branching.
- **Rejected options:** оставить router branching как основной путь.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** expected-reply участвует в router-level semantic routing, поэтому `P4` остается partial.
- **Minimal reproduction:**
  - `rg -n "if .*expected_reply_type|expected_reply_blocked_by_info|expected_reply_matched" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py`
- **Evidence to capture:** diff удаления router coupling + deterministic tests + decision meta continuity.
- **Five Whys (or equivalent):**
  1. Router shortcuts добавлялись для быстрых стабилизаций.
  2. Shortcut смешал semantic ownership и boundary-state.
  3. Смешение нарушило LLM-first charter.
  4. При добавлении новых доменов появляется routing drift.
  5. Без полного decouple `P4` не может быть `done`.
- **Root cause statement:** expected-reply имеет двойную роль (state + routing), что нарушает boundary model.
- **Fix mechanism:** оставить expected-reply только как boundary contract/state, убрать semantic branching из routers.

## Reuse-first plan (mandatory)
- **Internal reuse:** `expected_reply_contract.py`, `_apply_expected_reply_contract` в `decision.py`, текущие expected-reply tests.
- **External reuse:** pattern slot-validation vs policy-routing (Rasa docs).
- **Why not reinvent the wheel:** primitives уже есть, нужен targeted decouple без redesign всего orchestration.

## Invariant
- Не деградировать `FACT/COLLECT/HANDOFF` outcome contract.
- Не ослаблять LAW/safety/timeouts/semantic-firewall.
- Не менять внешний webhook API.

## Scope
- Удалить router semantic branching по expected-reply в `booking.py` и `info.py`.
- Довести expected-reply до boundary-only contract usage.
- Обновить тесты на contract/meta/trace oracle.

## Out of scope
- Полный redesign booking/info FSM.
- L3 acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/expected_reply_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_expected_reply_contract.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Полный inventory router branches по expected-reply.
2. Перенос remaining rules в `expected_reply_contract.py` как boundary decisions.
3. Удаление direct branching из `booking.py`.
4. Удаление direct branching из `info.py`.
5. Test migration на contract/meta assertions в затронутых сценариях.
6. Прогон deterministic checks.
7. Обновление parent TP и `STATE.md` с фактами.

## DoD
- В `booking.py`/`info.py` нет semantic branching по expected-reply.
- Expected-reply используется только как state/contract boundary.
- Target checks зеленые.
- Parent TP: `P4` переведен в `done` с evidence.

## Checks
- `rg -n "if .*expected_reply_type|expected_reply_blocked_by_info|expected_reply_matched" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py`
- `pytest -q truffles-api/tests/test_expected_reply_contract.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply or booking_info_interrupt or info_interrupt"`
- `pytest -q truffles-api/tests/test_master_info_flow.py`
- `ruff check truffles-api/app/services/expected_reply_contract.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/tests/test_expected_reply_contract.py truffles-api/tests/test_message_endpoint.py`

## Evidence
- Diff удаления router coupling.
- Логи `Checks`.
- Обновление parent TP + `STATE.md` с ссылкой на проверки.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic tests only
- **Stop condition:** любой regression в booking/info routing
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic-first + PR CI.
- **Go/no-go signals:** zero router coupling + green target tests.
- **Rollback:** `git revert <commit>`.
- **Post-release monitoring window:** следующий CI unit + targeted replay in L1 lane.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P4` можно отметить `done` только после удаления branching и зеленых checks.

## Rollback
- Revert commit(ы) и повторить `Checks`.

## No-go
- Новый semantic hardcode в routers.
- Ослабление safety/LAW gates.
- Объявление `P4 done` при оставшемся router coupling.

## Risks/Blockers
- Скрытые call-sites expected-reply в router code.
- Нужна аккуратная регрессия по interrupt/off-topic.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Execution Status Update (2026-03-02)
- `STATUS`: done.
- `Implementation`:
  - router-level expected-reply equality/membership branching removed from `truffles-api/app/routers/webhook/booking.py` and `truffles-api/app/routers/webhook/info.py`;
  - routing/guard decisions moved to `truffles-api/app/services/expected_reply_contract.py` helpers (`expected_reply_slot_key`, `should_prefer_info_class_for_booking_interrupt`, `should_override_truth_gate_off_topic_contract`, `truth_gate_expected_reply_prompt_contract`, `should_repeat_booking_prompt`, `should_mark_booking_time_service_candidate`, `should_keep_booking_prompt_for_info_clarify_time_followup`, `should_use_expected_service_off_topic_prompt`);
  - deterministic helper coverage extended in `truffles-api/tests/test_expected_reply_contract.py`.
- `Validation`:
  - `ruff check truffles-api/app/services/expected_reply_contract.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/tests/test_expected_reply_contract.py` -> pass;
  - `pytest -q truffles-api/tests/test_expected_reply_contract.py` -> `20 passed`;
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply or booking_info_interrupt"` -> `22 passed, 248 deselected`;
  - `pytest -q truffles-api/tests/test_master_info_flow.py` -> `29 passed`;
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "truth_gate or off_topic"` -> `6 passed, 264 deselected`.

## Next-block contract (mandatory)
- `Next block objective`: full-closure `P9` without text-oracle leftovers.
- `First deterministic check command`: `rg -n "assert .* in response\.bot_response|assert any\(token in response_text" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`
- `Blocked-by conditions`: `P4` checks red.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `booking.py` + `info.py` remaining expected-reply branches.
- `Do not touch`: timeout/safety/firewall logic in `decision.py`.
- `Open risks`: booking/info interrupt regressions.
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply"`.
