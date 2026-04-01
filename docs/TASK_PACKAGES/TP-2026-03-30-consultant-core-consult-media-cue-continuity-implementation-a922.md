# TP-2026-03-30-consultant-core-consult-media-cue-continuity-implementation-a922

- Status: `materially_complete_in_repo`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Материализовать bounded governed fix для механизма `consult/media cue continuity`: сделать consult/media follow-up contract representable на owner boundary, сохранить его через planner -> executor -> canonical continuity state, и убрать generic booking `service` fallback для этого envelope без возврата к legacy style-reference authority.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-consult-media-cue-continuity-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r36c-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36c/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit_workspace.md,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`

## Invariant
- Не лечить `dialog 7 / turn 1` как wording-only patch; implementation unit = один shared mechanism.
- Не добавлять phrase/regex routing по raw user text в runtime core.
- Не возвращать media cue в frozen legacy `response.py` / `context_manager.py` / `webhook.py`.
- Не re-author semantic meaning post-hoc в planner/executor; фикс должен проходить через owner contract + bounded deterministic execution.
- Не открывать вместе с этим блоком `booking-manage temporal clue grounding / follow-up continuity`.

## Scope
- Только governed envelope `consult/media cue continuity`.
- Materialize owner follow-up contract so consult/media cue is representable and survives:
  - policy-core prompt / vocabulary / response schema
  - policy-core runtime contract validation / repair
  - planner canonical pending-question contract
  - executor collect prompt realization
  - canonical continuity projections for the touched consult/media path
- Add deterministic tests for planner/runtime/state continuity.

## Out of scope
- Fresh replay / human semantic audit closure.
- New legacy deletion.
- `booking-manage temporal clue grounding / follow-up continuity`.
- Broad consult redesign or media-analysis product work.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-consult-media-cue-continuity-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/policy_prompt_snapshot_service.py`
- `truffles-api/app/services/policy_vocabulary_snapshot_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/turn_outcome.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_turn_outcome_contract.py`
- `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

## One web search (mandatory before implementation)
- Query: `OpenAI official docs image inputs user message image upload responses API`
- Date/time: `2026-03-30 Asia/Almaty`
- Sources opened:
  - `https://platform.openai.com/docs/guides/vision`
- Source quality:
  - official vendor documentation
- Findings:
  - image/photo input should stay explicit in the interaction contract, not collapse into generic text-only residue;
  - systems that accept user-offered photos should keep the media branch first-class in the owner/output contract.
- Decision (`reuse/integrate/build`):
  - `integrate + build`
  - reuse the existing governed owner/runtime path;
  - integrate a first-class consult/media follow-up contract into that path;
  - build only the missing representability + continuity seam.
- Rejected options:
  - wording-only patch for `фото`
  - routing the flow back into frozen legacy style-reference helpers
  - broad media-subsystem rewrite before the bounded contract fix

## Root cause (mandatory)
- Symptom:
  - `dialog 7 / turn 1`: `Я могу прислать фото своих ногтей.` -> bot: `На какую услугу хотите записаться?`
- Minimal reproduction:
  - `r36c`, `dialog_id=7`, `turn_index=1`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36c/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36c/trace_bundle.jsonl`
  - `truffles-api/app/services/policy_vocabulary_snapshot_service.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/dialog_state_service.py`
- Five Whys:
  1. Why does the visible path ask for service? Because collect execution falls back to booking `service`.
  2. Why does collect execution fall back? Because the owner follow-up contract is structurally empty at runtime.
  3. Why is it structurally empty? Because consult/media follow-up is not representable across the current vocabulary / expected-reply / next-question envelope.
  4. Why does that break continuity? Because executor/state layers still assume collect == booking unless a different contract survives intact.
  5. Why is this mechanism-wide? Because any consult turn with the same owner shape can collapse into the same generic booking collect.
- Broken invariant:
  - owner-recognized consult/media cue must survive into final collect behavior and canonical continuity; it may not silently reopen booking `service`.
- Shared mechanism:
  - representable consult/media follow-up contract across owner boundary, execution, and canonical continuity.
- Why this surfaced family belongs to that mechanism:
  - the failure is not one phrase; it is the missing contract surface that lets consult/media survive beyond semantic recognition.
- Open-world envelope expected to improve:
  - consult turns where the user offers a photo/reference/example before naming a concrete service.
- Root cause statement:
  - the governed path currently cannot represent and preserve a consult/media follow-up contract, so planner/executor/state default back to booking collect semantics.
- Fix mechanism:
  - add a first-class `media` follow-up contract on the owner path, validate/repair it at the owner boundary, realize it in executor, and preserve it in canonical continuity instead of forcing booking-state/service fallback.

## Plan
1. Switch canon from RCA-only block to this bounded implementation block.
2. Extend policy-core prompt/vocabulary so consult/media follow-up is representable (`expected_reply_type=media`, `next_question=media`).
3. Add owner-boundary validation/repair for the consult/media contract.
4. Realize `media` collect deterministically in executor and stop writing false booking continuity for this path.
5. Preserve the `media` follow-up in canonical continuity projections.
6. Add focused deterministic tests.
7. Sync packet/state/structure and report the remaining proof step.

## DoD
- Owner contract can represent consult/media follow-up without raw-text branching in core.
- Deterministic runtime no longer reopens generic booking `service` for the governed consult/media envelope.
- Canonical continuity preserves the media follow-up instead of forcing booking/current_goal contamination.
- No frozen legacy authority files gain new semantic logic.
- Focused deterministic tests pass.
- Repo docs/packet/state are synchronized to the active implementation block.

## Checks
- `pytest -q truffles-api/tests/test_intent.py -k "style_reference or policy_core_prompt"`
- `pytest -q truffles-api/tests/test_turn_outcome_contract.py`
- `pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py -k "style_reference or media"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "style_reference or media"`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`

## Evidence
- deterministic test results for the bounded contract
- updated active TP + canon/packet sync
- exact changed files in repo

## Rollback
- Revert this implementation TP and the bounded runtime/prompt/test changes as one block.

## No-go
- No user-text regex/phrase routing in runtime core.
- No direct call into frozen legacy style-reference flow.
- No claim of product closure without fresh replay + full human semantic audit.
- No widening into `booking-manage temporal clue grounding / follow-up continuity`.

## Риски/блокеры
- The repo still has broader consult/media debt outside this first bounded contract.
- Fresh replay may still surface a second-order failure on the next media turn.
- Prompt/schema changes can spill into other collect paths if the contract validation is too weak.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- fresh replay + full human semantic audit on the new head are still pending
- `booking-manage temporal clue grounding / follow-up continuity`
- broader actual-media handling beyond this bounded contract may still surface in replay

### Why not in this block
- This block is limited to the first bounded mechanism repair proven by `r36c` RCA.

### Risk if deferred
- Product closure remains blocked even if deterministic tests pass.

### Linked follow-up Task Package(s)
- fresh replay / audit proof step on the new head
- next RCA block for `booking-manage temporal clue grounding / follow-up continuity`

### Expiry/trigger to stop deferral
- Before any claim that the consult/media family is closed product-side.

## Next-block contract (mandatory)
### Next block objective
- Run fresh replay + full human semantic audit and decide whether `consult/media cue continuity` is actually improved on the practical path.

### First deterministic check command
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "style_reference or media"`

### Blocked-by conditions
- implementation checks red
- packet/canon drift
- any new symptom-only patch request outside this mechanism

### Owner role for closure
- Brain / Top Architect after deterministic proof + fresh replay + human audit
