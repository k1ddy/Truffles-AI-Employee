# TP-2026-04-01 — Consultant Core Booking-Manage Temporal Clue Grounding / Follow-up Continuity (a922)

- Название/цель: закрыть surfaced product blocker из fresh `Block H` replay, где live `check_booking` / confirm follow-up с уже данным weekday clue (`на четверг`) остается на generic booking-verification prompt и не сужает missing follow-up до identity/reference slot.
- Canon refs:
  - `STATE.md` — current next move after `Block H`
  - `docs/ACTIVE_CANON.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
  - `/tmp/booking_quality/a922-block-h-replay-20260401a/summary.json`
  - `/tmp/booking_quality/a922-block-h-replay-20260401a/responses.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401a/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-block-h-replay-20260401a/manual_audit.md`
  - `/tmp/booking_quality/a922-block-h-replay-20260401a/family_registry.json`

## Invariant
- `llm_policy_core` remains the sole semantic owner for `check_booking` / `verify_booking` intent, `calendar.get_booking`, `temporal_scope`, `expected_reply_type`, `next_question`, and `open_questions`.
- Boundary/runtime must not mint new business meaning or broaden the follow-up beyond the canonical pending-question contract.
- No scenario patching, no oracle weakening, no new keyword router branches in core.

## Scope
- Exact live runtime seam for booking-verification fact follow-up rendering when the owner already emitted `calendar.get_booking` + `expected_reply_type=name|time` and the incoming message carries a temporal clue.
- Shared visible-response mechanism only.

## Out of scope
- Scenario/oracle governance changes.
- Whole `Block H` doc sync.
- Booking-confirm taxonomy residue on `LLM-QUAL-a922-block-h-replay-20260401a-002-05-7add52`.
- Actual appointment lookup architecture for name/phone search.

## Touch-list
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-booking-manage-temporal-clue-grounding-followup-continuity-a922.md`

## One web search (mandatory before implementation)
- Query: `site:platform.openai.com/docs best practices prompt specific instructions GPT models official`
- Date/time: `2026-04-01 17:22 +06`
- Sources opened:
  - OpenAI API docs, `Reasoning models / use-case examples` — `https://platform.openai.com/docs/guides/reasoning/use-case-examples`
- Source quality:
  - High-signal primary source: official OpenAI documentation.
- Found reusable guidance:
  - Official guidance states GPT models benefit from precise instructions that explicitly provide the logic and data required for the output.
- Reuse / integrate / build decision:
  - `reuse -> integrate`: reuse the existing canonical follow-up contract (`expected_reply_type`, `next_question`, `open_questions`) and the already existing verification prompt family in runtime instead of inventing a new semantic branch.
  - `build`: add only a narrow response-composition helper where the current runtime still hardcodes a broader booking-verification prompt.
- Rejected variants:
  - Prompt-only fix in `llm_policy_core` without runtime change: rejected because fresh artifacts already show owner output is correct while final visible response is widened later.
  - Scenario/oracle patch: rejected because the failure is on live runtime response composition, not on generated coverage.

## Root cause (mandatory)
- Symptom:
  - `LLM-QUAL-a922-block-h-replay-20260401a-009-01-6c6aaa` and `LLM-QUAL-a922-block-h-replay-20260401a-009-02-ea4e3f` keep replying with `"Чтобы проверить запись, подскажите примерную дату и время или имя..."` even though the owner already grounded `temporal_scope=weekday` and asked only for `name`.
- Minimal reproduction:
  1. Start a fresh conversation.
  2. Send `Проверьте мою запись на четверг.`
  3. Send `Подтвердите, пожалуйста, мою запись на четверг.`
  4. Observe that live runtime repeats the same generic prompt instead of narrowing to the missing identity/reference slot.
- Evidence:
  - `responses.jsonl`:
    - `LLM-QUAL-a922-block-h-replay-20260401a-009-01-6c6aaa`
    - `LLM-QUAL-a922-block-h-replay-20260401a-009-02-ea4e3f`
  - `manual_audit.md`: dialog `9` turn `1=weak`, turn `2=fail`
  - `prompts/llm_policy_core.md:163-165` — owner contract says runtime may only voice the existing follow-up contract
  - `truffles-api/app/core/turn_executor.py:538-557` — live fact path still hardcodes a broader booking-verification prompt
  - `truffles-api/app/core/turn_executor.py:150-153` and `truffles-api/app/core/turn_executor.py:355-363` — runtime already has a narrower verification prompt family for collect-mode follow-ups, but the fact fallback bypass does not reuse it
- Five Whys:
  1. Why did the user get a generic `date/time or name` prompt? Because the fact execution branch returned a fixed booking-verification message.
  2. Why did it ignore the owner's `next_question=name` contract? Because the branch does not read `pending_question_contract` or the existing verification prompt map.
  3. Why did the weekday clue not narrow the visible ask? Because the branch never inspects `message_text` for existing temporal grounding when rendering the fallback.
  4. Why is that inconsistent with the live semantic contract? Because prompt ownership says runtime may only voice the follow-up already decided by policy-core, but this branch broadens it post-owner.
  5. Why did the family surface now as first blocker? Because Blocks A-G removed earlier owner/boundary/fact-plane blockers, exposing this remaining response-composition bypass on booking-management follow-ups.
- Broken invariant:
  - For `calendar.get_booking` reference follow-ups, visible runtime text must stay within the canonical pending-question contract. If `next_question=name`, runtime must not re-ask for temporal data; when a temporal clue is already present, the visible prompt should preserve that clue and ask only for the missing identity/reference slot.
- Shared mechanism:
  - Booking-verification fact follow-up composition in runtime is split: collect-mode uses the verification prompt family, but fact-mode `calendar.get_booking` fallback bypasses that contract and emits a hardcoded broader prompt.
- Why the surfaced family belongs to that mechanism:
  - Both failing turns share the same owner output (`calendar.get_booking`, `expected_reply_type=name`, `temporal_scope=weekday`) and fail only at the final response-rendering seam.
- Open-world envelope expected to improve:
  - `check_booking` / `verify_booking` turns where the user already gave `weekday`, `day`, or `time` clues but still owes `name` or another reference slot.
- Layer classification:
  - Primary: `fact_composition_error`
  - Secondary residues kept out of scope for this block: `oracle_or_evaluator_error`
- Root cause statement:
  - The live `TurnExecutor` fact path for `calendar.get_booking` still hardcodes a generic booking-verification prompt and ignores the canonical pending-question contract plus already provided temporal grounding, so post-owner response composition widens the ask from `name` to `date/time or name`.
- Fix mechanism:
  - Replace the hardcoded `calendar.get_booking` fact fallback text with one canonical booking-verification follow-up composer that reuses the owner-emitted `expected_reply_type` / `next_question` contract and preserves any temporal clue already present in the inbound message.

## Plan
1. Implement a narrow booking-verification follow-up composer in the live runtime seam.
2. Add deterministic regression coverage for `weekday -> name-only` follow-up and confirm follow-up continuity.
3. Run focused deterministic tests only for this mechanism.
4. Run one minimal replay on the booking-manage temporal-clue family only.
5. Sync state/docs only if code + tests + minimal replay proof are green.

## DoD
- `calendar.get_booking` fact follow-up no longer broadens `next_question=name` into `date/time or name`.
- A weekday clue such as `на четверг` is preserved in the visible follow-up prompt.
- Confirm/check follow-up stays within the same narrowed identity/reference question.
- Deterministic tests and one minimal replay prove the block.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "check_booking or booking_verification"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "check_booking or booking_verification"`
- `git diff --check`
- minimal replay command to be recorded after implementation

## Evidence
- code diff in active worktree
- deterministic pytest outputs
- `/tmp/booking_quality/<block-run>/summary.json`
- `/tmp/booking_quality/<block-run>/responses.jsonl`
- `/tmp/booking_quality/<block-run>/trace_bundle.jsonl`
- `/tmp/booking_quality/<block-run>/manual_audit.md`
- `/tmp/booking_quality/<block-run>/manual_audit.json`
- `/tmp/booking_quality/<block-run>/family_registry.json`

## Rollback
- Revert touched runtime/test files in this block only.
- Stop local replay runtime if started.

## No-go
- No prompt-only closure claim.
- No docs sync before replay proof.
- No changes in `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, or `docs/_generated/*` before full closeout.
- No scenario-governance/oracle edits in this block.

## Риски/блокеры
- Runtime may still hide another booking-manage residue after the visible prompt is fixed.
- If the first minimal replay fail moves to a different family, stop and reopen RCA instead of widening the block.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - Actual booking verification lookup still relies on limited retrieval inputs and can surface broader booking-manage limitations later.
  - Secondary oracle residue on successful booking commit remains open.
- Why not in this block:
  - They are not the first visible blocker from fresh `Block H` evidence.
- Risk if deferred:
  - Another booking-manage family may surface immediately after this block is fixed.
- Linked follow-up Task Package(s):
  - `TP-2026-04-01-consultant-core-block-h-final-acceptance-a922.md`
  - next TP to be created only if fresh replay surfaces a new family
- Expiry/trigger to stop deferral:
  - If the next minimal replay still fails first on booking-manage reference retrieval semantics after visible prompt exactness is fixed.

## Next-block contract (mandatory)
- Next block objective:
  - Either close this block in docs after replay proof, or open the next surfaced booking-manage/runtime family without hotfixing inside acceptance.
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "check_booking or booking_verification"`
- Blocked-by conditions:
  - no fresh replay artifact, or first replay failure still belongs to the same visible-prompt mechanism
- Owner role for closure:
  - Brain / Top Architect after code + tests + minimal replay proof
