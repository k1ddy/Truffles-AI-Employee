# TP-2026-03-30-consultant-core-consult-media-cue-continuity-a922

- Status: `in_progress`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Зафиксировать exact live-path RCA для surfaced family `consult/media cue continuity` из fresh replay `r36c`, доказать один механизм и один слой ответственности, и не допустить нового symptom patching по `dialog 7 / turn 1`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/REPORTS/2026-03-30-consultant-core-r36c-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36c/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit_workspace.md,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`

## Invariant
- Не лечить `dialog 7 / turn 1` как отдельный сценарий; implementation unit = только shared mechanism.
- Не добавлять phrase/regex branching по `фото`, `ногти`, `пример`, `референс` в runtime core.
- Не трогать runtime code в этом блоке до завершения exact path map и layer classification.
- Не смешивать этот блок с `booking-manage temporal clue grounding / follow-up continuity`.
- Не ослаблять `r36c` truth; никаких claims о practical/product closure.

## Scope
- Только механизм `consult/media cue continuity`.
- Exact path reconstruction для `dialog 7 / turn 1` из `r36c`.
- Доказать:
  - что owner уже видит media/style-reference cue,
  - где именно cue теряется,
  - почему итоговый reply превращается в generic service collect.

## Out of scope
- `booking-manage temporal clue grounding / follow-up continuity`
- `oracle contract / taxonomy alignment`
- любые code changes в `truffles-api/app/core/*`, `truffles-api/app/services/*`, `truffles-api/app/routers/webhook/*`
- any new replay until RCA is frozen and accepted

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-consult-media-cue-continuity-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r36c-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA only -> no code in this block`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `product::consult/media cue continuity::human_semantic_media_cue_miss,judge_fail,missed_question`
- Broken invariant:
  - when the user explicitly offers a photo/reference for consult, the visible path must preserve that media/style-reference cue; runtime may not collapse it into generic service-slot collection.
- Shared mechanism:
  - `consult/media cue continuity`
- Why this surfaced family belongs to that mechanism:
  - the owner trace already recognizes `style_reference` consultation intent, but the visible reply still asks only for service; the issue is cue continuity across owner -> collect execution, not one wording.
- Open-world envelope expected to improve:
  - any beauty consult turn where the user offers to send a photo/reference/example before naming a concrete service.

## One web search (mandatory before implementation)
- Query: `OpenAI official docs image inputs user message image upload responses API`
- Date/time: `2026-03-30 Asia/Almaty`
- Recording note:
  - the original exact minute was not persisted in repo artifacts before compaction
  - no extra query was issued after compaction to avoid violating the one-search rule
- Sources opened:
  - `https://platform.openai.com/docs/guides/vision`
- Source quality:
  - official vendor documentation
- Findings:
  - image/photo inputs are first-class message inputs and should remain structured user input rather than being flattened away as generic text-only intent residue
  - a system that accepts user-offered photos should keep the media/reference branch explicit in the interaction contract
- Decision:
  - `build`
  - reason: the repo already recognizes the photo/reference cue semantically; the missing piece is the internal owner-to-collect continuity contract, which must be reconstructed from live evidence before any implementation
- Rejected variants:
  - `patch the wording for "фото"` — scenario patching, not mechanism recovery
  - `route media cues back into frozen legacy style-reference helpers immediately` — bypasses the current governed runtime path

## Root cause (mandatory)
- Symptom:
  - `dialog 7 / turn 1`: `Я могу прислать фото своих ногтей.` -> bot: `На какую услугу хотите записаться?`
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r36c`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=7`, `turn_index=1`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36c/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36c/trace_bundle.jsonl`
  - `truffles-api/app/core/turn_planner.py:336`
  - `truffles-api/app/core/turn_planner.py:931`
  - `truffles-api/app/core/turn_executor.py:335`
- Five Whys:
  1. Why does the bot ask for service instead of acknowledging the offered photo/reference? Because the final collect execution chooses `next_slot=service` and emits the generic booking-style service prompt.
  2. Why does collect execution choose `service`? Because `_execute_collect(...)` falls back to `self._first_missing_booking_slot(...)` when the canonical pending-question contract has no `next_question`.
  3. Why is the canonical pending-question contract empty even though the trace says `user_offers_photos_for_style_reference`? Because the semantic owner output carries `pack_refs=["style_reference"]` and `capability=consultation`, but it does not materialize a first-class follow-up contract (`next_question`, `pending_question_target`, `open_questions`) for the media/reference path.
  4. Why is that a product failure? Because the explicit consult/media cue is recognized in semantic state but lost before the final response, so the visible path stops being media-aware.
  5. Why is this a mechanism-level family? Any consult/media offer with the same owner shape can collapse into the same generic service collect path.
- Root cause statement:
  - current evidence points to an owner-to-collect contract incompleteness: semantic owner recognizes `style_reference` consultation, but the follow-up contract remains structurally empty, so generic collect reconstruction falls through to booking-slot service collection and drops the explicit media cue.
- Fix mechanism:
  - not in this block; the follow-up implementation block must materialize a first-class consult/media follow-up contract and prove that generic booking-slot fallback no longer captures this envelope.

## Exact path map
1. `input`
   - `dialog 7 / turn 1`
   - user text: `Я могу прислать фото своих ногтей.`
2. `owner output`
   - `intent=consult`
   - `action=collect`
   - `tool_action_hint=consult`
   - `pack_refs=["style_reference"]`
   - `reason=user_offers_photos_for_style_reference`
   - `capability=consultation`
   - no explicit `next_question` / `open_questions`
3. `validator / guard`
   - no boundary deny/degrade path fires
   - trace stays on `semantic_runtime_path=consultant_core_v2`
4. `post-owner reconstruction`
   - `TurnPlanner.canonical_pending_question_contract(...)` rebuilds the pending-question contract from the semantic payload
   - because the owner payload does not provide follow-up fields, the resulting canonical pending-question contract is empty
5. `executor fallback`
   - `TurnExecutor._execute_collect(...)` computes `next_slot = canonical_pending_question.next_question or first_missing_booking_slot`
   - with an empty canonical pending question and no booking slots, the fallback becomes `service`
   - `_build_collect_prompt(...)` then emits the generic collect prompt for `service`
6. `final response / action`
   - visible reply: `На какую услугу хотите записаться?`
   - final action stays `collect` with `tool_decision=service`
7. `trace/meta evidence`
   - owner trace keeps `style_reference` and `consultation`
   - final `decision_meta` exposes `next_slot=service`, `tool_decision=service`
   - the media cue loss is therefore visible as a contract gap between semantic recognition and final collect behavior

## Layer classification
- `owner_error`
- rationale:
  - no boundary/degrade path rewrites the turn
  - the visible failure is enabled because owner output does not provide a first-class consult/media follow-up contract, even though the semantic frame correctly recognizes the cue

## Required RCA questions
1. Should the future fix extend `SemanticDecisionV1` follow-up fields for consult/media, or bind them through a separate consult-specific pending-question contract?
2. Is `style_reference_pending` the right continuity carrier for the governed path, or only a legacy compatibility carrier?
3. What exact contract should distinguish `photo/reference offer` from ordinary `collect service`?
4. How do we keep this fix pack-agnostic and avoid reintroducing legacy `style_reference` authority?

## Plan
1. Freeze `r36c` as the active practical truth in canon/docs.
2. Freeze this mechanism-first RCA in a dedicated TP.
3. Keep implementation blocked until Brain/Architect accept the exact path and layer classification.
4. Open one bounded implementation TP only after RCA closure.

## DoD
- Exact live path is written and tied to specific artifacts/code.
- One broken invariant and one shared mechanism are named explicitly.
- One layer classification is chosen and defended.
- No runtime code is changed in this block.
- Canon/docs point to `r36c` and to this RCA block as the next admissible move.

## Checks
- `python3 - <<'PY'\nimport json\nfrom pathlib import Path\nrows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-practical-proof-20260330-r36c/responses.jsonl').read_text().splitlines()]\nrow=next(item for item in rows if item['dialog_id']==7 and item['turn_index']==1)\nmeta=row['decision_meta']\nassert meta['semantic_frame']['capability_selection']['pack_refs'] == ['style_reference']\nassert meta['semantic_contract']['capability'] == 'consultation'\nassert meta['tool_decision'] == 'service'\nassert meta['next_slot'] == 'service'\nprint('consult_media_rca_seed_ok')\nPY`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-r36c-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36c/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit_workspace.md,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- updated canon/docs pointing to `r36c`

## Rollback
- Revert the doc-only truth sync and RCA TP as one block if the exact path or layer classification is disproven.

## No-go
- No runtime code changes.
- No dialog-level or wording-level patching.
- No backdoor move into `booking-manage temporal clue grounding / follow-up continuity` before this RCA closes.
- No claim that `r35f` remains the active practical truth.

## Риски/блокеры
- The visible failure sits on the owner/runtime contract seam; a careless future fix could re-open post-owner reconstruction or legacy style-reference authority.
- The repo still contains legacy style-reference helpers, but this block must not route around the governed hot path.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `booking-manage temporal clue grounding / follow-up continuity`
- `oracle contract / taxonomy alignment`
- broader architecture debt outside the touched canary envelope

### Why not in this block
- User/canon scope now demands one shared mechanism at a time after `r36c`.

### Risk if deferred
- Product closure remains blocked, and future work can drift back into scenario patching if the next mechanism is not frozen explicitly.

### Linked follow-up Task Package(s)
- next: bounded implementation TP for `consult/media cue continuity`
- queued after that: RCA TP for `booking-manage temporal clue grounding / follow-up continuity`

### Expiry/trigger to stop deferral
- Before any runtime code is changed for the media family.

## Next-block contract (mandatory)
### Next block objective
- Open one bounded implementation TP that materializes the consult/media follow-up contract on the governed path and proves the generic `service` fallback no longer captures this envelope.

### First deterministic check command
- `python3 - <<'PY'\nimport json\nfrom pathlib import Path\nrows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-practical-proof-20260330-r36c/responses.jsonl').read_text().splitlines()]\nrow=next(item for item in rows if item['dialog_id']==7 and item['turn_index']==1)\nprint(row['turn_text'])\nprint(row['inline_response_text'])\nprint(row['decision_meta']['semantic_frame']['reason'])\nprint(row['decision_meta']['tool_decision'])\nPY`

### Blocked-by conditions
- Brain/Architect have not yet accepted the exact path and chosen layer classification.

### Owner role for closure
- `Brain/Architect`
