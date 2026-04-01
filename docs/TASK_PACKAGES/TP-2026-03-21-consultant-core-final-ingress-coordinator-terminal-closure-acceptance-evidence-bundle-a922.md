# TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-EVIDENCE-BUNDLE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-EVIDENCE-PREP-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `UNLOCKS`: `reenter_consultant_core_demo_salon_main_canary_after_promo_interrupt_contract_closure`

## Название/цель
Классифицировать surfaced family `a922-weekend-slot-constraint-dev-r79` в правильный слой и закрыть только proved reusable contract bug: active booking interrupt path должен распознавать `promotions` / `promotions_rules` как info interruption, отвечать по truth-first и сохранять pending `time` collect.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/summary.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/responses.jsonl`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: `truffles-api/app/routers/webhook/info.py`, `truffles-api/tests/test_master_info_flow.py`, `truffles-api/tests/test_reasoning_core.py`, canon/session docs listed below.
- `Baseline commands`:
  - `python3 - <<'PY'
import sys
sys.path.insert(0, 'truffles-api')
from app.routers.webhook import info as info_router
from app.services.info_signal_service import looks_like_promotions_policy_message
text = 'Есть ли у вас акции на маникюр?'
print(info_router._detect_info_class_intents(text, intent_decomp_set=set(), client_slug='demo_salon', service_query='Маникюр'))
print(looks_like_promotions_policy_message(text, client_slug='demo_salon'))
PY`
  - `python3 - <<'PY'
import json
path='/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/responses.jsonl'
msg_id='LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4'
for line in open(path, encoding='utf-8'):
    row=json.loads(line)
    if row['message_id']==msg_id:
        print({
            'turn_text': row['turn_text'],
            'outbox_text': row['outbox_text'],
            'decision_action': row['decision_meta']['action'],
            'decision_source': row['decision_meta']['source'],
            'info_tags': row['info_tags'],
            'info_sections': row['info_sections'],
            'strict_reasons': row['evaluation']['strict_reasons'],
        })
        break
PY`
- `FACT findings`:
  - the exact failing row is still `LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4`: user asks `Есть ли у вас акции на маникюр?`, runtime answers booking time guidance, and quality fails `expected_info_section_miss`, `info_section_miss`, `judge_fail`.
  - shared info-class intent resolver currently returns no intents for that text even though the promotions policy detector returns `True`; the missing signal is therefore inside the runtime info-intent contract, not in pack truth or readiness.
  - `promotions` / `promotions_rules` are already part of the semantic owner contract and `REASONING_CORE_TURN_PLANNER_INFO_INTENTS`; the failure is that the active booking interrupt resolver never receives them from `_detect_info_class_intents(...)`.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs form interruptions active loop FAQ slot filling`
- **Date/time (local):** `2026-03-21T22:31:00+05:00`
- **Why this query is precise:** the bug is an active-slot-collection interruption/resume contract. The search checks an official primary-source description of how interruption handling should preserve the active requested slot instead of silently consuming the interruption.
- **Sources opened (from this query):**
  - `Rasa documentation — Forms` — `https://rasa.com/docs/rasa/forms/` (redirects to legacy 3.x docs)
- **Existing solutions found:** official Rasa form guidance treats side questions / unhappy paths during slot filling as explicit interruptions that are handled and then returned to the active loop, instead of being mistaken for slot fulfillment.
- **Decision:** `reuse` — keep Truffles on the existing `booking_interrupt` / `question_contract` contract and repair the shared info-intent classifier so promotions interruptions resume `expected_reply_type=time` after the fact reply.
- **Rejected options:**
  - promo-specific hardcode in `reasoning_core`: rejected because the bug is in the shared intent-contract layer, and phrase-specific branching in core violates the charter.
  - oracle-only waiver: rejected because runtime actually routes the turn as `booking_prompt`; this is not just a weak expectation.
  - pack/content change: rejected because promo truth already exists and the detector already knows the question is promotional.
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** during an active booking time collect, the user asks `Есть ли у вас акции на маникюр?`, but runtime continues the booking prompt instead of answering promotions info and resuming time collection.
- **Minimal reproduction:**
  - `python3 - <<'PY'
import sys
sys.path.insert(0, 'truffles-api')
from app.routers.webhook import info as info_router
from app.services.info_signal_service import looks_like_promotions_policy_message
text = 'Есть ли у вас акции на маникюр?'
print('detect_info_class_intents=', info_router._detect_info_class_intents(text, intent_decomp_set=set(), client_slug='demo_salon', service_query='Маникюр'))
print('promotions_policy=', looks_like_promotions_policy_message(text, client_slug='demo_salon'))
PY`
  - `python3 - <<'PY'
import json
path='/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/responses.jsonl'
msg_id='LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4'
for line in open(path, encoding='utf-8'):
    row=json.loads(line)
    if row['message_id']==msg_id:
        print({
            'turn_text': row['turn_text'],
            'outbox_text': row['outbox_text'],
            'decision_source': row['decision_meta']['source'],
            'decision_action': row['decision_meta']['action'],
            'strict_reasons': row['evaluation']['strict_reasons'],
        })
        break
PY`
- **Evidence to capture:** the two snippets above, `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/{summary.json,responses.jsonl}`, updated deterministic tests, and the post-fix targeted test output.
- **Five Whys (or equivalent):**
  1. Why does the bot answer with booking time guidance? Because the booking prompt owner does not see a recognized info interruption intent for the promo question.
  2. Why does it not see the intent? Because `_detect_info_class_intents(...)` returns an empty set for the promo question.
  3. Why is the set empty if the system already knows about promotions? Because promotions detection currently lives in policy/info-signal helpers, but the shared info-class intent resolver never compiles those signals into `intents` / `info_signals`.
  4. Why does that become a runtime bug instead of an oracle bug? Because runtime metadata on the failing row shows `action=booking_prompt` and `source=booking_prompt_owner`; the wrong path is actually executed.
  5. Why is the fix a shared-contract change rather than a local phrase patch? Because the reusable contract bug is the mismatch between policy-level promo detection and the shared info interrupt classifier that all booking-interrupt owners depend on.
- **Root cause statement:** the shared info-class intent resolver fails to compile existing promotions/promotions_rules policy signals into runtime intents, so active booking interrupt arbitration misclassifies promo questions as continued slot collection.
- **Fix mechanism:** extend `_detect_info_class_intents(...)` to surface `promotions` / `promotions_rules` from existing signal helpers, then cover the active booking interrupt path with deterministic regression tests proving truth reply + preserved `expected_reply_type=time`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - existing booking interrupt tests in `truffles-api/tests/test_reasoning_core.py`
  - existing info classifier tests in `truffles-api/tests/test_master_info_flow.py`
- **External reuse:** official Rasa form interruption guidance only.
- **Why not reinvent the wheel:** the runtime already has the correct owner contract (`booking_interrupt` + `question_contract`); only the shared classifier is under-reporting promo intents.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `30`
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded core contract repair with deterministic evidence, not a new runtime family expansion.

## Invariant
- preserve main-path architecture; no new phrase/regex branching in core
- preserve truth-first promo replies and pending `time` question continuity
- keep frozen webhook files untouched
- do not weaken acceptance/oracle gates to mask the failure

## Scope
- classify `r79` as a proved `core contract bug`
- repair the shared info-class intent resolver for `promotions` / `promotions_rules`
- add deterministic regressions for classifier output and active booking interrupt resume behavior
- sync canon/session docs to the new active implementation block

## Out of scope
- any pack truth/content change
- any branch/tool readiness change
- any frozen-router edit
- full guarded canary/matrix/open-world reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_master_info_flow.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the RCA evidence showing promotions policy detection exists while `_detect_info_class_intents(...)` still returns empty.
2. Publish the implementation TP/report and switch canon from prep to the bounded acceptance-evidence bundle.
3. Patch the shared info-class resolver to emit `promotions` / `promotions_rules` without adding new semantic hardcode in core.
4. Add targeted deterministic tests for classifier output and active booking promo interrupt resume behavior.
5. Rerun targeted tests plus required packet/guard checks.

## DoD
- active block is this implementation TP, not the prep block
- `_detect_info_class_intents(...)` returns `promotions` / `promotions_rules` for promo policy questions
- active booking prompt owner answers promo interruption via truth reply and preserves `expected_reply_type=time`
- targeted deterministic suites and required guards pass
- report artifact records the classification as `core contract bug` with exact evidence

## Checks
- `pytest -q truffles-api/tests/test_master_info_flow.py -k 'promotions'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_prompt_owner.*promotions or promotions_policy_override'`
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py`
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
- updated shared classifier: `truffles-api/app/routers/webhook/info.py`
- deterministic regressions: `truffles-api/tests/test_master_info_flow.py`, `truffles-api/tests/test_reasoning_core.py`
- active block/report/doc sync files listed above
- RCA artifacts from `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic regression only in this block
- **Stop condition:** if the bug cannot be proved by deterministic classifier/runtime tests and requires broader runtime surgery, stop and re-split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** keep change local to shared info-class intent resolver + tests; no rollout or env mutation in this block
- **Go/no-go signals:** targeted tests and guard stack must stay green; any frozen-file touch or broader runtime regression is `no-go`
- **Rollback:** revert resolver/test/doc changes and rebuild packet
- **Post-release monitoring window:** next block must reenter guarded canary on `demo_salon/main`

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - block stays `BLOCKED` until canon, session log, and generated packet all point at this implementation TP/report

## Rollback
- revert the resolver/test/doc changes, rerun packet/guard checks, and restore the prep TP as the active block.

## No-go
- do not patch `truffles-api/app/services/reasoning_core.py` with promo phrase hardcodes just to pass this family
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not classify this as pack/readiness without contrary evidence
- do not run non-canonical acceptance reruns as substitute for deterministic proof in this block

## Risks/Blockers
- broadening `_detect_info_class_intents(...)` could affect non-booking info routing if the signal contract is too loose; targeted classifier tests must prove no obvious drift
- the next guarded canary may surface a second failure family after promo interrupt closure
- full local realism / guarded canary evidence is intentionally deferred to the next block

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: guarded `demo_salon/main` canary, multi-pack matrix, and open-world closure remain undone after this bounded fix
- `Why not in this block`: this block is only the proved contract-bug repair and deterministic evidence bundle required before truthful canary re-entry
- `Risk if deferred`: without the next canary rerun, closure still relies on deterministic evidence only and final acceptance remains open
- `Linked follow-up Task Package(s)`: `reenter_consultant_core_demo_salon_main_canary_after_promo_interrupt_contract_closure`
- `Expiry/trigger to stop deferral`: stop deferral as soon as deterministic regressions are green; next move must be guarded canary re-entry, not another doc-only block

## Next-block contract (mandatory)
- `Next block objective`: reenter guarded `demo_salon/main` canary using the repaired promo interrupt contract and reclassify any remaining first-fail family from canonical evidence
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_prompt_owner.*promotions'`
- `Blocked-by conditions`: this block not merged into canon; targeted deterministic checks not green; local runtime environment unavailable for guarded canary
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md`
- `Do not touch`: frozen webhook routers, acceptance thresholds, unrelated runtime families
- `Open risks`: `canary may still surface another family after promo fix`, `full guarded realism not yet rerun`
- `First command to verify`: `python3 - <<'PY'
import sys
sys.path.insert(0, 'truffles-api')
from app.routers.webhook import info as info_router
print(info_router._detect_info_class_intents('Есть ли у вас акции на маникюр?', intent_decomp_set=set(), client_slug='demo_salon', service_query='Маникюр'))
PY`
