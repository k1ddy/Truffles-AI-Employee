# TP-2026-04-01-consultant-core-acceptance-blocker-booking-interrupt-media-parking-reopen-a922

## Название / цель
Закрыть первый truthful acceptance blocker family, surfaced by `a922-l2-proof-seed7-20260401i`: booking/info interrupt continuity drift, consult/media cue contract drift, and parking fact-scope overconstraint. Цель блока — вернуть acceptance lane к truthful replay readiness через один bounded runtime fix, а не через micro-patches.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-replay-and-full-human-semantic-audit-acceptance-a922.md`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/summary.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.md`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com interruption state machine preserve parent state side question branch by abstraction`
- Date/time: `2026-04-01 Asia/Almaty`
- Opened sources:
  - `https://martinfowler.com/eaaDev/EventCollaboration.html`
- Found ready-made solutions:
  - no direct Truffles-ready fix; the useful reusable principle is to keep one explicit collaboration/state contract instead of letting side channels reconstruct parent state.
- Decision: `build`
- Why: the surfaced bug is Truffles-specific contract drift across semantic owner, pending-question continuity, and fact-plane scope. External guidance is only a design reminder to keep one explicit contract path during side-question interruptions.
- Rejected variants:
  - broad FSM rewrite: too large and violates bounded recovery scope.
  - acceptance-only reruns: blocked until the shared mechanism is fixed.

## Root cause (mandatory)
### Symptom
- seed7 truthful dev replay `a922-l2-proof-seed7-20260401i` surfaced three linked product families:
  - booking/info interrupt continuity drift
  - consult/media cue drift
  - parking fact answer unresolved despite resolvable tool path

### Minimal reproduction
1. Booking flow with active `expected_reply_type=time`, then ask `Сколько стоит маникюр?`
2. Booking/consult flow with photo/reference cue: `Я могу прислать фото своих ногтей.` or `Вот фото референса`
3. Parking question: `Есть ли парковка рядом?`

### Evidence
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- pricing continuity evidence: final pending contract kept stale `pending_question_act/target` but dropped `expected_reply_type/next_question/open_questions`
- media evidence: contract stayed on `tool_decision=media` but stale booking axes remained and media cue was not consumable
- parking evidence: `fact_requested_refs=['location','parking']`, `fact_allowed_sets=[['location','hours','parking']]`, `tool_decision=fact_family_unresolved`

### Five Whys
1. Why did acceptance block surface again? Because owner/runtime contracts still drift on interrupt and parking fact paths under truthful replay.
2. Why did pricing interrupt lose continuity? Because owner contract validation preserves carryover only for `active_question_relation="generic_info_interrupt"`, while truthful owner output can still come back as `action="fact"` with stale relation axes.
3. Why did consult/media cue drift? Because strict consult/media contract validation only fires for the single reason `user_offers_photos_for_style_reference`, while truthful owner output already uses broader photo-reference reason variants.
4. Why did parking answer degrade to unresolved? Because fact manifest overconstrains requested `parking` into the emitted bundle `location+hours+parking`, so a valid parking-only tool answer becomes out-of-scope and is converted into `fact_family_unresolved`.
5. Why is this one shared mechanism? Because all three failures are the same class: owner-authored interrupt/fact contracts are too narrowly accepted, so truthful variants are rejected or overconstrained before reply realization.

### Broken invariant
- owner-authored interrupt/fact contract must survive truthful runtime variants without downstream loss or overconstraint

### Shared mechanism
- overly narrow contract normalization / validation for:
  - interrupt follow-up carryover on `action="fact"`
  - consult/media reason variants
  - first fact-family allowed emitted sets for `parking`

### Why the surfaced family belongs to that mechanism
- all failures occur before product wording quality: they appear in `decision_meta`, `pending_question_contract`, `fact_allowed_sets`, and `tool_decision` evidence on the live path.

### Open-world envelope expected to improve
- booking/info interrupts under active `time` collect
- consult/media photo/reference turns that use alternative but semantically equivalent reason codes
- parking-only fact asks that should not require sibling facts

### Root cause statement
- The current runtime accepts only a narrow subset of truthful owner interrupt/media/fact variants. When the owner emits semantically correct but contract-adjacent payloads, carryover preservation and media validation do not fire, and the parking fact-plane denies a resolvable parking-only answer by requiring an unnecessary sibling bundle.

### Fix mechanism
- broaden owner contract preservation for fact-side interrupts with active pending carryover
- broaden consult/media strict validation from one exact reason to the governed style-reference/photo-reference family
- narrow `parking` allowed emitted set to the parking-only slice

## Invariant
- no semantic hardcode on user text in core
- no downstream semantic rewrite outside the owner path
- no fact-scope widening outside explicit fact-plane rules
- no ACTIVE_/STATE/packet/report sync until the full block closes

## Scope
- owner contract validation/repair for fact interrupts with active carryover
- consult/media reason-family validation and repair
- parking fact-plan emitted-set correction
- focused deterministic tests
- one truthful dev replay rerun on local proof runtime if targeted suites are green

## Out of scope
- broad acceptance closure docs
- unrelated scenario patches
- baseline refresh
- product/practical green claim

## Touch-list
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- optional focused acceptance helper tests if strictly needed
- block artifacts only after full closeout:
  - report
  - active canon/program/state/packet

## Plan
1. Add bounded helper(s) in owner validation for carryover-preserving fact interrupts and style-reference reason family.
2. Narrow first fact-family policy so requested `parking` allows a parking-only emitted set.
3. Add deterministic tests for:
   - pricing interrupt with active carryover but stale relation
   - consult/media alternate reason variants
   - parking requested scope resolving without forced sibling facts
4. Run focused local-first deterministic suites.
5. If green, rerun one truthful guarded dev replay against the local proof runtime and stop at first fail.
6. Only then close the block with one doc/state sync.

## DoD
- pricing/info interrupt preserves `expected_reply_type`, `next_question`, `open_questions`, and pending axes on owner path
- consult/media reason variants are forced into the governed media follow-up contract
- requested `parking` no longer requires `hours` in `allowed_emitted_sets`
- truthful dev replay moves past the covered blocker family or surfaces a new first-fail family

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "generic_info_interrupt or consult_media"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "parking or consult_media or generic_info_interrupt"`
- guarded truthful dev replay command from acceptance lane, using local proof runtime `http://127.0.0.1:18188`
- `git diff --check`

## Evidence
- focused pytest output
- `/tmp/booking_quality/<new-run-id>/summary.json`
- `/tmp/booking_quality/<new-run-id>/responses.jsonl`
- `/tmp/booking_quality/<new-run-id>/trace_bundle.jsonl`
- `/tmp/booking_quality/<new-run-id>/manual_audit.md`
- exact rerun command

## Rollback
- revert touched files in this block only
- discard the new dev replay as non-canonical if deterministic checks or truthful replay regress

## No-go
- no scenario-specific prompt hacks
- no weakening of acceptance oracle
- no ACTIVE_/STATE/packet/report update before full block closure
- no second replay if the first truthful rerun still surfaces the covered family

## Риски / блокеры
- truthful replay may surface an adjacent continuity family after this one clears
- existing deterministic tests may encode outdated parking bundle assumptions and will need honest correction

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- acceptance lane remains open even if this block goes green
- any adjacent first-fail family after this block is deferred

### Why not in this block
- this block only covers the first truthful blocker family from `a922-l2-proof-seed7-20260401i`

### Risk if deferred
- acceptance remains blocked by newly surfaced adjacent runtime debt

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-replay-and-full-human-semantic-audit-acceptance-a922.md`
- new TP to be opened only if the truthful rerun surfaces a different first-fail family

### Expiry / trigger to stop deferral
- if truthful dev replay still fails on the same family after this bounded fix, stop and reopen RCA instead of patching further

## Next-block contract (mandatory)
### Next block objective
- resume acceptance lane if the truthful rerun moves past this family; otherwise open the newly surfaced runtime block from evidence

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "generic_info_interrupt or consult_media"`

### Blocked-by conditions
- focused deterministic checks must be green
- truthful local proof runtime on `:18188` must stay `TEST_MODE=1`, `EVAL_MODE=local`

### Owner role for closure
- Brain / Top Architect
