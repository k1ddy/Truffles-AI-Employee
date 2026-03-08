# TP-2026-03-04-e2a-interrupt-arbitration-owner-a1

## Block identity
- `BLOCK_ID`: `E2a`
- `PARENT_BLOCK_ID`: `TP-2026-02-19-llm-first-firebreak-program`
- `DEPENDS_ON`: `TP-2026-03-03-e1-llm-first-firebreak-action-router-a1`
- `UNLOCKS`: `E2b` (lexicon/resolver expansion), `E2c` (canonical replay/canary on same fingerprint)

## Название/цель
Закрыть первый системный дефект E2: отсутствие единого owner для booking/info interrupt в policy-core и дрейф expected-reply после terminal tool outcomes. Блок должен убрать booking-prompt takeover на info/master turns и запретить повторную постановку expected-reply после `clear_expected_reply`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (`IN_PROGRESS Block E / E2 runtime evidence`)
- `STRATEGY/REQUIREMENTS.md` (`Booking/info interrupt contract`, `Expected-reply single owner contract`)
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md` (E2 RCA + next-block contract)

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_master_query_normalizes_to_master_info_under_booking or llm_policy_core_get_booking_ok_does_not_force_handoff"`
- `FACT findings`:
  - `collect` path in policy-core can bypass info interrupt ownership and directly emit booking prompts for info-like turns (`decision.py`, `policy_tool_action == "collect"` branch).
  - Tool-contract `clear_expected_reply=True` can be followed by re-derivation of booking follow-up in the same turn (`decision.py`, calendar/tool follow-up derivation block).
  - Runtime evidence from `booking-lock-20260304-firebreak-e2-a1-r13` confirms failures on `master/price` interrupts and `booking_slot_stall` after `calendar.book_slot=ok`.
- `Detected drift (docs vs code)`: `none` (docs already describe these RCA items, code not yet closed).

## One web search (mandatory before implementation)
- **Query (exact):** `AWS Step Functions terminal state no Next Choice state guard order`
- **Date/time (local):** `2026-03-04 10:18, Asia/Almaty`
- **Why this query is precise:** Нужен первичный reference по deterministic orchestration: terminal state must stop further transitions; guard arbitration must be explicit and ordered.
- **Sources opened (from this query):**
  - AWS Docs: *State machine structure in Step Functions workflows* — https://docs.aws.amazon.com/step-functions/latest/dg/statemachine-structure.html
  - AWS Docs: *Choice workflow state in Step Functions* — https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html
- **Existing solutions found:** Внешние state-machine/orchestrator паттерны подтверждают: terminal-state semantics и явная guard arbitration.
- **Decision:** `build` (reuse internal contracts). Мы интегрируем pattern в существующий policy-core, не добавляя внешнюю orchestrator библиотеку.
- **Rejected options:**
  - Внедрение стороннего state-machine runtime: избыточно для точечного E2a и риск migration-drift в core path.
  - Regex-first локальный hotfix в collect branch: нарушает semantic-first charter и не решает ownership drift системно.
- **Open questions:** `none`.

## Root cause (mandatory)
- **Symptom:**
  - Info/master turns в активной booking-сессии местами завершаются `booking_prompt`/`service_clarify` без `info_sections`.
  - После `calendar.book_slot=ok` сохраняется `expected_reply_type=time` (`booking_slot_stall`).
- **Minimal reproduction:**
  - `booking-lock-20260304-firebreak-e2-a1-r13` bad turns:
    - `LLM-QUAL-booking-lock-20260304-firebreak-e2-a1-r13-004-13-52edaf`
    - `LLM-QUAL-booking-lock-20260304-firebreak-e2-a1-r13-009-11-51f75d`
    - `LLM-QUAL-booking-lock-20260304-firebreak-e2-a1-r13-010-10-892d78`
- **Evidence to capture:** `summary.json`, targeted `responses.jsonl` extracts, deterministic unit tests in `test_message_endpoint.py`.
- **Five Whys (or equivalent):**
  1. Why info turns become booking prompts? `collect` branch executes before unified interrupt ownership and keeps booking progression as default.
  2. Why collect branch wins? Policy plan (`tool_action=collect`) is treated as terminal local directive for missing booking slot.
  3. Why info intent is not preserved? Info signals are split across detector/policy payload/router branches; no single arbitration owner before collect.
  4. Why booking slot stalls after successful commit? `clear_expected_reply` is applied, but follow-up derivation can set a new expected-reply in same turn.
  5. Why allowed architecturally? expected-reply contract lacks terminal-clear guard in downstream follow-up path.
- **Root cause statement:** Runtime has split semantic ownership at booking/info interrupt boundary and missing terminal-clear invariant for expected-reply in tool follow-up.
- **Fix mechanism:**
  - Add single pre-branch `collect->info` interrupt arbitration contract for booking-active turns.
  - Enforce terminal-clear guard that blocks any follow-up expected-reply derivation in same turn when tool contract clears it.

## Reuse-first plan (mandatory)
- **Internal reuse:** `_derive_policy_info_refs`, `resolve_master_intent`, existing `info` branch, `resolve_tool_expected_reply_contract`.
- **External reuse:** N/A (only reference pattern from AWS docs).
- **Why not reinvent the wheel:** Реиспользуем текущие routing/contract helpers, добавляем только ownership guard и terminal invariant.

## Invariant
- Не деградировать booking continuity, handoff safety, and policy-core tool contract validation.
- Не добавлять semantic hardcode в core runtime path.

## Scope
- `E2a-1`: Implement interrupt arbitration owner (`collect -> info` in booking-active turns, when explicit info/master signals exist).
- `E2a-2`: Implement terminal-clear expected-reply guard for tool outcomes (`clear_expected_reply=True`).
- Добавить deterministic tests для обоих механизмов.

## Out of scope
- Расширение lexicon/regex для `по цене` и иных morphological variants (`E2b`).
- Runtime replay/canary acceptance closure (`E2c`).

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2a-interrupt-arbitration-owner-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить helper arbitration contract в `decision.py` (input: policy collect + booking-active + policy/message info signals; output: effective tool_action/info refs).
2. Подключить helper до ветвления `policy_tool_action`, логировать decision_trace/meta reason-code для observability.
3. Добавить terminal-clear flag в tool result path и запретить downstream follow-up derivation при clear-contract.
4. Добавить/обновить deterministic tests в `test_message_endpoint.py`.
5. Прогнать targeted pytest + ruff и зафиксировать evidence в `STATE.md`.

## DoD
- `collect` с `policy_intent=master_query` в booking-active turn маршрутизируется в info interrupt path (`info_sections` включает `master`, без booking prompt takeover).
- При `calendar.book_slot=ok` и `clear_expected_reply=True` не выставляется новый `expected_reply_type` в том же turn.
- Новые/обновленные тесты green, lint green.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_collect_master_query_rewrites_to_info_interrupt or calendar_book_slot_ok_terminal_clear_blocks_followup_expected_reply or llm_policy_core_get_booking_ok_does_not_force_handoff"`
- `ruff check truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`

## Evidence
- `git diff` for touched files.
- Pytest output (targeted tests).
- Forensic mapping in `STATE.md` entry for E2a.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (в этом блоке только deterministic unit checks).
- **Fail-fast / scenario lock:** targeted test selection via `-k`.
- **Stop condition:** если 2 подряд итерации без нового failing assertion -> stop and reopen RCA.
- **Escalation path:** Brain/Top Architect approval for moving to E2b/E2c runtime loops.

## Release safety (mandatory for non-doc changes)
- **Strategy:** feature-preserving internal guard (no new runtime flag), rollout через обычный PR lane.
- **Go/no-go signals:** deterministic tests + no regression on existing contract tests.
- **Rollback:** revert commit with E2a changes.
- **Post-release monitoring window:** next canonical replay (`E2c`) must confirm no `booking_slot_stall` regression.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
- `Drift closeout rule`:
  - если runtime replay не выполнен в этом блоке, фиксируем explicit residual debt + next block contract.

## Rollback
- `git revert <E2a-commit>` on feature branch or rollback patch removing arbitration rewrite + terminal-clear guard.

## No-go
- Не ослаблять acceptance thresholds/quality gates.
- Не добавлять phrase-hardcode branching в core как primary semantic owner.
- Не менять runtime baseline артефакты вручную.

## Risks/Blockers
- `collect->info` rewrite может изменить UX на пограничных turns без info-signal.
- Возможны скрытые зависимости от старого поведения в смежных tests.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: price morphology misses (`по цене`) и broader multilingual master-query lexicon robustness.
- `Why not in this block`: это отдельный resolver/lexicon hardening scope (`E2b`), не part of ownership invariant.
- `Risk if deferred`: часть price/master turns останется в collect path при policy timeout/low-signal.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-e2b-lexicon-resolver-hardening-a1` (to be created), `TP-2026-03-04-e2c-canonical-replay-canary-a1` (to be created).
- `Expiry/trigger to stop deferral`: before E2 close claim and before updating canonical lock baseline.

## Next-block contract (mandatory)
- `Next block objective`: закрыть E2b (lexicon/resolver coverage) и снять remaining `info_section_miss` for price morphology.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_info_interrupt or policy_core_master_query"`
- `Blocked-by conditions`: E2a tests green and no expected-reply terminal-clear regression.
- `Owner role for closure`: `Hands` (implementation), acceptance by `Brain/Top Architect`.

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/routers/webhook/decision.py` (`policy_tool_action` arbitration + tool follow-up block)
- `Do not touch`: policy-core external API contract, quality gate thresholds.
- `Open risks`: collect/info borderline turns, degraded timeout path.
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_collect_master_query_rewrites_to_info_interrupt"`
