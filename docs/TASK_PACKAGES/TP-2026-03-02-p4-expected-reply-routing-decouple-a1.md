# TP-2026-03-02-p4-expected-reply-routing-decouple-a1

## Status
- `SUPERSEDED_BY`: `docs/TASK_PACKAGES/TP-2026-03-02-p4-expected-reply-full-closure-a1.md`
- `REASON`: this file captured the first continuation slice only; full closure now uses a single end-to-end TP.

## Block identity
- `BLOCK_ID`: SIG-P4-EXPECTED-REPLY-DECOUPLE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-core-dehardcoding-sweep-a1
- `UNLOCKS`: P4 closure in parent TP and cleaner LLM-first routing boundary

## Название/цель
Закрыть остаток `P4 Expected-Reply Refactor`: убрать direct expected-reply routing branch control из webhook routers (`booking/info`) и оставить expected-reply как contract-state/update слой, не semantic router.

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
- `Baseline commands`:
  - `rg -n "expected_reply_type|expected_reply_matched|_apply_expected_reply" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/decision.py`
  - `rg -n "EXPECTED_REPLY_" truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - `expected_reply_type` участвует в routing conditions внутри `booking.py` (slot matching и short-circuit ветки).
  - `info.py` записывает и переиспользует expected-reply контекст при service_clarify/off_topic override.
  - `expected_reply_contract.py` уже существует как сервисный контрактный слой, но routers все еще содержат routing-coupling.
- `Detected drift (docs vs code)`: partial `P4` подтверждается code-fact, без противоречий.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa slot validation actions dialogue flow separation docs`
- **Date/time (local):** `2026-03-02 14:52, Asia/Almaty`
- **Why this query is precise:** нужен reference по разделению slot state handling и policy routing для dialog systems.
- **Sources opened (from this query):**
  - Rasa docs, Slot Validation Actions: `https://rasa.com/docs/reference/integrations/action-server/validation-action/`
  - Rasa docs, Domain/slots patterns: `https://rasa.com/docs/reference/primitives/domain/`
- **Existing solutions found:**
  - slot state как отдельный контрактный слой;
  - routing decision отделяется от slot-value validation/update.
- **Decision:** `integrate` и `build`
  - Использовать существующий expected-reply contract service и удалить router-level semantic branching, оставив boundary checks.
- **Rejected options:**
  - Сохранить router-level expected-reply branching как primary path (не соответствует LLM-first charter).
- **Open questions:**
  - Нужно уточнить минимально-безопасный этапный cutover (P4a/P4b) без регресса booking.

## Root cause (mandatory)
- **Symptom:** `P4` остается partial: expected-reply напрямую влияет на router ветвление.
- **Minimal reproduction:**
  - `rg -n "if expected_reply_type|expected_reply_blocked_by_info|_set_expected_reply_context" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py`
- **Evidence to capture:** code diff + targeted routing tests + decision_meta/trace invariants.
- **Five Whys (or equivalent):**
  1. Почему expected-reply влияет на routing? Исторически был как deterministic shortcut.
  2. Почему это проблема? Нарушает semantic-owner boundary.
  3. Почему не удален ранее? Нужна была firebreak-stability.
  4. Почему сейчас можно? Есть stronger policy-core envelope + contract tests.
  5. Почему делать отдельным блоком? Высокий риск regressions в booking/info flow.
- **Root cause statement:** expected-reply одновременно выполняет две роли (state contract и semantic router), что нарушает целевую архитектуру.
- **Fix mechanism:** split responsibilities: expected-reply -> state/update contract only; semantic routing -> policy-core + resolver contract.

## Reuse-first plan (mandatory)
- **Internal reuse:** `expected_reply_contract.py`, `decision.py` expected-reply application path, existing booking/info contract tests.
- **External reuse:** архитектурный pattern slot-state separation (Rasa docs).
- **Why not reinvent the wheel:** уже есть рабочий contract layer, нужен decouple/refactor без новой подсистемы.

## Invariant
- Не ломаем booking completion и info interrupt behavior.
- Не снижаем safety/LAW checks.
- Не вводим phrase/regex semantic hardcode.

## Scope
- Удалить/сократить router-level expected-reply semantic branching в `booking.py` и `info.py`.
- Оставить expected-reply как contract state update + deterministic boundary guard.
- Обновить контрактные тесты на meta/trace outcomes.

## Out of scope
- Полный redesign booking FSM.
- Изменение внешнего API webhook.
- L3 acceptance прогоны в этом блоке.

## Touch-list
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/expected_reply_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Выделить и зафиксировать router-coupled expected-reply ветки (map + tests).
2. Перенести expected-reply влияние в contract-state/result meta path.
3. Заменить routing assertions на contract meta/trace assertions.
4. Прогнать deterministic suite и обновить docs status.

## DoD
- В `booking.py/info.py` expected-reply не является primary semantic router branch.
- Routing outcomes принимаются по `decision_meta/decision_trace` и policy/resolver contracts.
- Targeted tests green без text-oracle regressions.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply or booking_info_interrupt or multi_truth"`
- `pytest -q truffles-api/tests/test_master_info_flow.py`
- `ruff check truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/tests/test_message_endpoint.py`

## Evidence
- Diff по router decoupling.
- Зеленые outputs из `Checks`.
- Обновление parent TP + `STATE.md` фактами.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** deterministic tests only
- **Stop condition:** любой behavior regression в booking/info tests
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased router decouple (`P4a` then `P4b`) behind existing deterministic guards.
- **Go/no-go signals:** zero regressions in target suites + preserved decision_meta invariants.
- **Rollback:** `git revert <commit>`
- **Post-release monitoring window:** next CI run + one replay deterministic lane.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P4` status changes only with deterministic evidence + trace/meta proof.

## Rollback
- Revert block commits and rerun target deterministic tests.

## No-go
- Нельзя переносить semantic branching в новые hardcoded if/else.
- Нельзя ослаблять existing safety/degrade guards.
- Нельзя закрывать `P4` без trace/meta evidence.

## Risks/Blockers
- Высокий регрессионный риск в booking prompts.
- Нужен строгий тестовый coverage на expected-reply transitions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: phase split `P4a/P4b` допустим для safe rollout.
- `Why not in this block`: большой blast radius, нужен этапный cutover.
- `Risk if deferred`: сохранится router coupling и сложность масштабирования policy-core.
- `Linked follow-up Task Package(s)`: `TP-2026-03-02-p4-expected-reply-routing-decouple-a1` (`P4b` section in same TP or next TP).
- `Expiry/trigger to stop deferral`: before next acceptance chain promotion.

## Next-block contract (mandatory)
- `Next block objective`: complete `P4b` cleanup of remaining expected-reply router hooks.
- `First deterministic check command`: `rg -n "if expected_reply_type|expected_reply_blocked_by_info" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py`
- `Blocked-by conditions`: failing booking/info deterministic tests.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `truffles-api/app/routers/webhook/booking.py` expected-reply branches map.
- `Do not touch`: safety/LAW/timeout-degrade gates in `decision.py`.
- `Open risks`: booking prompt regressions.
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply"`
