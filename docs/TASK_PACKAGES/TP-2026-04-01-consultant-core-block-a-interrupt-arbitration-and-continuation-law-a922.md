# TP-2026-04-01-consultant-core-block-a-interrupt-arbitration-and-continuation-law-a922

- Status: `in_progress`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `implementation`
- Block ID: `block-a-interrupt-arbitration-and-continuation-law`

## Название/цель
Закрыть только `Block A — Interrupt Arbitration And Continuation Law` в активном worktree `a922`: ввести один bounded canonical law для active follow-up interruptions, чтобы later specialist/master query больше не застревал внутри active media continuation, а generic info interrupt сохранял booking continuity явно и воспроизводимо.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-acceptance-blocker-booking-interrupt-media-parking-reopen-a922.md` (historical broad TP; not authoritative for this bounded block)
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/summary.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.md`

## Invariant
- Не лечить `LLM-QUAL-a922-l2-proof-seed7-20260401i-001-07-65fdf0` как single-turn patch; implementation unit = shared interrupt/continuation mechanism.
- Не чинить в этом блоке `parking/location/hours` fact scope и не расширять worktree в `Block B`.
- Не добавлять raw-text regex/phrase routing в core runtime.
- Не ослаблять owner-first contract: deterministic boundary может только валидировать, repair-ить или preserve-ить canonical continuity.
- Не обновлять `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries/reports до полного proof closeout этого блока.

## Scope
- Один bounded mechanism вокруг active follow-up interruption law для:
  - booking follow-up carryover
  - generic info interrupt carryover
  - media/style-reference continuation
  - specialist/master query under active continuation
- Exact live-path repair в owner validation / repair + canonical continuity projection only.
- Focused tests only for this mechanism.
- Exactly one minimal fresh replay only for interruption family after deterministic proof.

## Out of scope
- `Block B — Fact Scope Exactness`
- `Block C — Continuity Carrier Collapse`
- prompt rewrite / broad vocabulary redesign unless strictly required by the bounded mechanism
- legacy mesh drain / boundary purification / pack-runtime work
- broad governance-doc sync before proof closeout

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-a-interrupt-arbitration-and-continuation-law-a922.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## One web search (mandatory before implementation)
- Query: `hierarchical state machine interrupt preserve child state official documentation xstate`
- Date/time: `2026-04-01 05:08:42 +05 (Asia/Almaty)`
- Sources opened:
  - `https://stately.ai/docs/transitions`
  - `https://stately.ai/docs/history-states`
- Source quality:
  - official vendor documentation
- Found ready-made solutions:
  - no drop-in Truffles implementation; the reusable principle is explicit history/resume state: side interrupts should preserve a parent follow-up contract rather than reconstruct it ad hoc after the interrupt.
- Decision (`reuse/integrate/build`):
  - `integrate + build`
  - reuse the existing typed runtime spine and canonical pending-question contract;
  - integrate one explicit interrupt-resume law for active media/booking continuity;
  - build only the missing bounded validation/repair + projection seam.
- Rejected options:
  - broad FSM/library rewrite
  - hotfixing the surfaced turn only
  - mixing fact-plane `parking` repair into this block

## Exact Path Map (mandatory)
1. Input
- Fresh replay first-fail turn: `LLM-QUAL-a922-l2-proof-seed7-20260401i-001-07-65fdf0`
- User text: `Кто из специалистов делает маникюр?`
- Prior active state from trace: booking flow already shifted into media follow-up after `Могу прислать фото своих ногтей.` and runtime memory carried:
  - `active_goal=booking`
  - `memory.profile.pending_question_contract = {reason=user_offers_photos_for_style_reference, next_question=media, open_questions=[media], expected_reply_type=media}`
  - `memory.profile.semantic_contract.referents.service = manicure`
2. Owner output
- `llm_policy_core` emitted:
  - `intent=consult`
  - `action=collect`
  - `tool_action_hint=consult`
  - `pack_refs=[style_reference]`
  - `expected_reply_type=media`
  - `next_question=media`
  - `open_questions=[media]`
  - `reason=user_offers_photos_for_style_reference_continuation_and_photo_needed_for_style_alignment_with_specialist_query`
  - `pending_question_act=ask_about_requested_slot`
  - `pending_question_target=time`
  - `active_question_relation=ask_about_requested_slot`
3. Validator / interrupt arbitration
- `_validate_policy_core_runtime_contract(...)` did not reject or repair this turn because current law is too narrow:
  - consult/media validation fires only for exact reason `user_offers_photos_for_style_reference`
  - generic interrupt carryover preservation fires only when the output already says `active_question_relation=generic_info_interrupt`
- Result: no `policy_core_contract_repair` retry ran for this surfaced family.
4. Continuity preservation
- `ConsultantRuntime._project_runtime_pending_question_contract(...)` accepted the owner contract as canonical pending state.
- `DialogStateService.write_runtime_payload(...)` then persisted the media continuation with booking/time axes still attached.
5. Fallback / degrade
- None. No boundary deny/degrade fired; the bad owner output passed through the canonical path as if it were valid.
6. Final response
- `TurnExecutor` realized the turn as `tool_decision=media` and sent `Пришлите, пожалуйста, фото-пример желаемого результата.`
7. Trace/meta evidence
- `decision_meta.intent=consult`
- `decision_meta.tool_decision=media`
- `decision_meta.pending_question_contract.expected_reply_type=media`
- `decision_meta.pending_question_contract.pending_question_target=time`
- replay evaluation: `expected_reply_type_mismatch`, `expected_meta_mismatch`, `info_section_miss`, `judge_fail`
8. Layer classification
- Primary: `owner_error` — semantic owner kept media continuation on a later specialist/master side question.
- Secondary: `boundary_fallback_error` — contract validation/repair did not recognize the broader interrupt family and allowed bad owner output through.
- Not this block: `fact_composition_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`.

## Root cause (mandatory)
### Symptom
- Under active media follow-up inside booking continuity, a later specialist/master query remains trapped in `consult/media` instead of being arbitrated as a side interrupt with explicit booking resume.

### Minimal reproduction
1. Start booking collect with service known and time missing.
2. Shift into active media continuation (`LLM-QUAL-a922-l2-proof-seed7-20260401i-001-06-812f73`).
3. Ask a later specialist/master query: `Кто из специалистов делает маникюр?`.
4. Observe runtime still returns `tool_decision=media` instead of an interrupt answer with preserved booking continuity.

### Evidence
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- `truffles-api/app/services/intent_service.py:594`
- `truffles-api/app/services/intent_service.py:624`
- `truffles-api/app/core/consultant_runtime.py:530`
- `truffles-api/app/core/consultant_runtime.py:945`
- `truffles-api/app/core/dialog_state_service.py:3525`

### Five Whys
1. Why did the surfaced turn stay on media? Because the owner output kept `intent=consult`, `action=collect`, `expected_reply_type=media`.
2. Why did the owner output survive unchanged? Because boundary validation only recognizes one exact consult/media reason and one exact generic-info relation.
3. Why does that miss this family? Because truthful replay already uses broader reason variants and side-question variants (`...specialist_query`) while keeping the same active continuation envelope.
4. Why is continuity still wrong after the owner turn? Because runtime stores whichever pending-question contract the owner emitted; there is no explicit interrupt-resume law for active media follow-up.
5. Why is this one mechanism and not one scenario? Because the same missing law affects any active follow-up where a sub-continuation must coexist with a preserved parent resume contract.

### Broken invariant
- Active media/style-reference continuation may only survive while the user is still fulfilling that continuation. A later side question must be arbitrated as an interrupt and must preserve the parent booking follow-up explicitly.

### Shared mechanism
- Missing canonical interrupt-resume contract for active media follow-up, combined with reason-family validation that is too narrow to reject/reclassify broader truthful variants.

### Why the surfaced family belongs to that mechanism
- The failure is visible before wording quality: the wrong owner category, wrong `expected_reply_type`, and wrong `tool_decision` are already stamped in `decision_meta` / `decision_trace`.

### Open-world envelope expected to improve
- Active booking follow-up interrupted by:
  - generic info turns
  - specialist/master truth queries
  - continued photo/reference fulfillment turns that should remain on media

### Root cause statement
- The runtime has no single explicit law that distinguishes `continue media` from `interrupt + preserve booking resume` once media follow-up is active. Because validation/repair only accepts narrow exact variants, broader truthful owner outputs pass through unrepaired and the canonical state is rewritten as if the side question were still media fulfillment.

### Fix mechanism
- Materialize one explicit interrupt-resume law for active media follow-up:
  - derive/preserve the parent booking resume contract explicitly,
  - broaden media-family validation from one exact reason to the governed photo/style-reference reason family,
  - require reclassification when the owner output signals later specialist/master interruption inside that family,
  - preserve explicit booking continuity on generic info interrupts.

## Plan
1. Add explicit interrupt-resume projection for active media follow-up in the typed runtime state path.
2. Broaden owner validation/repair in `intent_service.py` from exact-value checks to governed reason-family / resume-contract checks.
3. Add/update focused tests for:
   - media follow-up variant acceptance,
   - specialist/master query reclassification under active media,
   - explicit booking continuity preservation on active interrupt law.
4. Run only focused deterministic tests for Block A.
5. Run exactly one minimal fresh replay on the interruption family.
6. If and only if replay moves past this family, then close the block and sync the deferred governance docs.

## DoD
- Specialist/master query no longer returns `tool_decision=media` when active media continuation exists.
- Generic info interrupt preserves booking continuity explicitly on the owner/runtime path.
- Media continuation still survives for actual photo/reference fulfillment variants.
- No unrelated `parking/fact_plane` changes land in this block.
- Focused deterministic tests pass.
- One minimal fresh replay provides truthful evidence for this block only.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "generic_info_interrupt or consult_media or specialist_query"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "consult_media or generic_info_interrupt or specialist"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_collect_interrupt_arbitration"`
- focused minimal replay command (to be frozen after deterministic green; one run only)
- `git diff --check`

## Evidence
- focused pytest output for the Block A tests
- exact changed files in the worktree
- one fresh interruption-only replay bundle under `/tmp/booking_quality/<run-id>/`
- replay command + surfaced first-fail classification
- `STATE.md` / active-governance sync deferred until the block is actually proven

## Rollback
- Revert only the Block A file set above.
- Discard the fresh replay bundle as non-canonical if deterministic proof or the bounded replay fails on the same family.

## No-go
- No `parking`, `location`, or fact-plane edits in this block.
- No scenario-only prompt wording hack.
- No broad doc churn.
- No second replay if the first fresh replay still surfaces the same family.
- No closure claim from tests/docs alone.

## Риски/блокеры
- The first replay after the fix may surface an adjacent interruption family instead of total green.
- Existing tests may encode an older consult/media contract that must be honestly narrowed or replaced.
- The worktree is already dirty; edits must stay strictly inside the touch-list and must not disturb unrelated live changes.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `Block B — Fact Scope Exactness`
- broader continuity-writer collapse (`Block C`)
- boundary purification / pack-runtime / legacy mesh / operational dedupe follow-ups (`Block D+`)

### Why not in this block
- The user explicitly required one hard block at a time and the fresh first-fail family is Block A only.

### Risk if deferred
- Even after Block A closes, the next replay can still surface fact scope or continuity carrier debt as the next blocker.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-b-fact-scope-exactness-a922.md` (to be authored only if Block A proof closes and Block B becomes first-fail)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c-continuity-carrier-collapse-a922.md` (future)

### Expiry/trigger to stop deferral
- If the fresh replay after Block A still first-fails on the same interruption family, stop-the-line and reopen RCA instead of widening the block.

## Next-block contract (mandatory)
### Next block objective
- If Block A is proven, move to `Block B — Fact Scope Exactness` and make fact-plane the sole governor for `location / hours / parking`.

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "parking or fact"`

### Blocked-by conditions
- Block A deterministic checks red
- Block A replay still first-fails on the same interruption family
- any attempt to mix `fact_plane.py` or broad governance sync into the current block before proof

### Owner role for closure
- Brain / Top Architect after code + focused tests + exactly one minimal replay proof

## Branch / Worktree / Merge policy / Cleanup
- Branch: current active worktree branch (do not retarget in this block)
- Worktree path: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: current worktree HEAD vs `/home/zhan/truffles-main` only as canon/diff target
- Merge policy: no merge/commit implied by this TP; closure only after Block A proof
- Cleanup: no runtime/doc cleanup beyond this touch-list before closeout
