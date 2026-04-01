# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-CANARY-RERUN-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement the bounded turn-13 runtime family without touching frozen routers. This block is admissible only if explicit name fill under active `expected_reply_type=name` is consumed through existing generic booking/state contracts, the fix stays inside live non-frozen runtime code, and the next move after landing is the same fresh canary replay instead of proof-lane churn.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r14/failure_families.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [12, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('hq1_classes'), row.get('evaluation'))
PY`
  - `python3 - <<'PY'
from app.routers.webhook import decision as decision_router
state = {'active': True, 'service': 'Маникюр', 'datetime': 'в субботу 11:00'}
print(decision_router._update_booking_from_messages(state, ['Меня зовут Амина.'], client_slug='demo_salon'))
print(decision_router._validate_expected_reply_value(expected_reply_type=decision_router.EXPECTED_REPLY_NAME, value='Меня зовут Амина.', client_slug='demo_salon'))
PY`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '12783,12895p;13531,14101p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '8689,8788p;14595,14772p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` turn `13` still loops `Как вас зовут?` after explicit name fill and records `booking_slot_stall`.
  - `decision_router._update_booking_from_messages(...)` already extracts `{'name': 'Амина'}` from `Меня зовут Амина.` on top of active booking context.
  - `decision_router._validate_expected_reply_value(... EXPECTED_REPLY_NAME ...)` already normalizes the same turn to `Амина`.
  - `truffles-api/app/services/reasoning_core.py:12783-12895` still contains an early semantic booking-prompt recovery branch that reopens `booking_prompt` whenever slots are incomplete, before the later booking-completion owner can consume the explicit name turn.
  - `truffles-api/app/services/reasoning_core.py:13531-14101` already defines the bounded completion path that should own explicit name progression once complete booking slots are available.
  - `truffles-api/tests/test_reasoning_core.py:8689-8788` already proves complete-name progression must execute booking completion instead of repeating the name prompt.
- `Detected drift (docs vs code)`:
  - canon is still on the turn-13 decision TP; once runtime code lands, active canon must promote this implementation block and move the next non-negotiable step to guarded replay.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs forms slot mappings from text requested slot explicit value`
- **Date/time (local):** `2026-03-22T09:00:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Reuse rule for this block:** reuse the exact search already recorded in the decision TP; no second query is allowed or needed.
- **Existing solutions found:** when a requested slot is filled from the user's text, the form should advance instead of re-asking the same slot.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing explicit-name validation and booking-state merger
  - integrate one bounded semantic-arbitration fix so the later booking-completion owner can consume the progressed name turn
- **Rejected options:**
  - second web query
  - proof/oracle tightening before runtime repair
  - phrase hardcode for `Меня зовут ...`
  - frozen-router edits

## Root cause (mandatory)
- **Symptom:** fresh canary turn `13` (`Меня зовут Амина.`) still returns `Отлично, время подходит. Как вас зовут?` under active `expected_reply_type=name` instead of progressing booking completion.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` turn `13`
  2. confirm `expected_reply_type=name`, `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`, and `evaluation.reasons=['booking_slot_stall']`
  3. inspect `truffles-api/app/services/reasoning_core.py:12783-12895`
  4. confirm semantic arbitration reopens `booking_prompt` as soon as slots are still incomplete on the policy payload
  5. inspect `truffles-api/app/services/reasoning_core.py:13531-14101`
  6. confirm the later booking-completion owner already knows how to consume a complete name turn and book/handoff contractually
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/failure_families.json`
  - `truffles-api/app/services/reasoning_core.py:12783-12895`
  - `truffles-api/app/services/reasoning_core.py:13531-14101`
  - `truffles-api/tests/test_reasoning_core.py:8689-8788`
  - direct helper probe of `_update_booking_from_messages(...)` and `_validate_expected_reply_value(...)`
- **Five Whys (or equivalent):**
  1. Why does turn `13` loop the same prompt? Because semantic arbitration returns a new `booking_prompt` before the explicit name turn is applied to canonical booking slots.
  2. Why does semantic arbitration do that? Because the early incomplete-slot recovery path only merges policy-validated slots and immediately re-prompts while `name` is still absent on the policy payload.
  3. Why does the explicit name not rescue that path? Because the recovery branch does not apply the existing explicit-name extraction/validation helpers before deciding to re-ask.
  4. Why is this a runtime bug instead of proof debt? Because deterministic repo contracts already require complete-name progression to booking completion or bounded handoff, not a repeated `name` prompt.
  5. Why is the fix bounded? Because the repo already owns explicit-name parsing and booking completion; the missing work is only wiring them together on the live non-frozen semantic path.
- **Root cause statement:** the live semantic-arbitration booking recovery path in `reasoning_core.py` reopens `booking_prompt` on incomplete policy slots before applying the repo's existing explicit-name capture to the active booking state, so the later booking-completion owner never sees a completed `name` slot on turn `13`.
- **Fix mechanism:** add one bounded non-frozen name-progression override in `reasoning_core.py`, reuse existing explicit-name extraction/validation helpers to merge `name` into active booking state before the recovery prompt decision, and let the existing booking-completion owner take over once the booking becomes complete.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `decision_router._update_booking_from_messages(...)`
  - `decision_router._validate_expected_reply_value(...)`
  - existing semantic booking recovery path in `reasoning_core.py`
  - existing booking-completion owner in `reasoning_core.py`
  - existing deterministic completion contract in `truffles-api/tests/test_reasoning_core.py:8689-8788`
- **External reuse:**
  - official Rasa forms/requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already owns name capture and completion semantics; this block only makes the live semantic path conform to them

## Invariant
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not reopen turn `9` or turn `12` as active blockers
- do not add phrase-hardcoded name handling in core
- do not claim acceptance closure from this block alone

## Scope
- implement bounded explicit-name progression on the live semantic booking path
- ensure the progressed name reaches the existing booking-completion owner
- add focused deterministic regression coverage for the real turn-13 family
- sync canon/session/packet to the implementation block and move the next step to guarded replay

## Out of scope
- guarded llm-quality replay itself
- `ops/diagnose.py` oracle tightening
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Publish this implementation TP and switch active canon/session references to it.
2. Repair semantic booking recovery so explicit name fill is merged before the recovery prompt can re-ask `name`.
3. Reuse the existing booking-completion owner once the repaired semantic path yields complete booking slots.
4. Add focused regression coverage for the surfaced turn-13 family.
5. Run focused regressions and mandatory governance checks.
6. Hand off the next move as guarded replay on the same fresh canary artifact.

## DoD
- active canon points to this implementation TP
- turn `13` explicit name progression is repaired in non-frozen runtime only
- the progressed customer name reaches booking completion or bounded handoff instead of repeated `name` prompt
- focused reasoning-core regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay on the same canary family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- focused pytest outputs from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; guarded replay stays in the next block
- **Stop condition:** if the fix requires frozen-router edits or breaks adjacent name-completion contracts, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new turn-13 regression passes, adjacent completion contracts stay green, architecture/session guards stay green
- **Rollback:** revert `reasoning_core.py`, `test_reasoning_core.py`, TP/report/canon sync, regenerate packet, rerun guards
- **Post-release monitoring window:** next block must be guarded replay on the same canary family before any proof-lane tightening

## Rollback
1. Revert the non-frozen runtime/test changes.
2. Revert this TP/report/canon sync.
3. Rebuild packet and rerun the mandatory checks.

## No-go
- no frozen-router edits
- no second web query
- no proof/oracle patch first
- no phrase hardcodes for name phrases
- no new acceptance claim without replay evidence

## Risks / blockers
- the explicit-name repair sits in semantic arbitration; a too-narrow fix could leave adjacent runtime paths inconsistent
- the completion owner still relies on tool/capability envelope; a tool-side regression would surface as a different failure family after this fix
- acceptance remains open until the same canary replay reruns on the repaired runtime

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - guarded replay for the repaired turn-13 family is still pending
  - judge/oracle conflicts on turns `6`, `9`, and `11` remain deferred proof debt
  - broader acceptance / open-world closure remains pending
- `Why not in this block:`
  - this block only lands the runtime family and focused deterministic proof
- `Risk if deferred:`
  - without replay, the repo still lacks truthful canary evidence that the surfaced turn-13 family is gone on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_turn13_name_progression_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any oracle tightening or acceptance-closure claim

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the guarded canary path for the repaired turn-13 family and reclassify any surviving failures only from fresh evidence
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`
- `Blocked-by conditions:`
  - focused deterministic regressions go red
  - governance/session checks go red
  - replay would proceed without fresh packet/canon truth
- `Owner role for closure:` `Top Architect`
