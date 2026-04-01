# TP-2026-03-21 — Consultant Core Demo Salon Main Canary Preflight Proof Gap A922

## Название / цель
Зафиксировать truthful preflight evidence после promo-interrupt closure: доказать, что `r9` turn 10 (`check_booking_prompt`) был stale oracle/proof artifact, а не runtime blocker, и перевести программу на следующий честный вопрос — классификацию advisory gap на turns 9 и 12 до любого нового runtime-кода.

## Canon refs
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`

## Repo anchors
- Main runtime path already migrated; final acceptance is still open in proof lane.
- `check_booking_prompt` is already the expected bounded owner path for collect-reference booking verification in `truffles-api/tests/test_reasoning_core.py:9518`, `truffles-api/tests/test_reasoning_core.py:9649`, `truffles-api/tests/test_reasoning_core.py:9655`, `truffles-api/tests/test_message_endpoint.py:29096`, and `truffles-api/tests/test_message_endpoint.py:29256`.
- Scenario sanitizer already normalizes stale booking-management follow-ups in `truffles-api/app/services/llm_quality_contracts.py` and `scripts/booking_dialog_scenarios.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs forms unhappy paths active loop interruptions`
- **Date/time (local):** `2026-03-21T22:24:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/` (official docs; redirects to legacy OSS docs)
- **Existing solutions found:**
  - official guidance treats interruptions during an active requested-slot loop as explicit unhappy paths that either return to the active loop or deactivate it; they are not supposed to be silently scored as a generic reply while the requested slot remains active.
- **Decision:** `reuse`
  - keep Truffles on the existing `question_contract` / scenario-sanitizer contract, treat stale `turn10` action mismatch as proof drift, and only classify turns `9` / `12` after refreshed artifacts are frozen.
- **Rejected options:**
  - patch runtime before classification: rejected; would violate the “classify before code” rule.
  - keep replaying the stale `a922-weekend-slot-constraint-dialog.json`: rejected; it already encodes obsolete expectations.
  - weaken judge/threshold gates: rejected; proof gaps must stay observable.

## Root cause (mandatory)
- Symptom:
  - `a922-promo-l2-preflight-r9` stopped on turn `10` with `expected_action_mismatch` because scenario turn `Проверьте, пожалуйста, мою запись на маникюр в выходные.` still expected `action=reply`, while runtime correctly executed `check_booking_prompt`.
- Minimal reproduction:
  - `python3 - <<'PY'
import json, random, sys
from pathlib import Path
sys.path.insert(0, 'truffles-api')
from app.services.llm_quality_contracts import sanitize_booking_scenario_llm_turns
payload = json.loads(Path('/tmp/booking_quality/a922-weekend-slot-constraint-dialog.json').read_text())
turns = payload['dialogs'][0]['turns']
sanitized = sanitize_booking_scenario_llm_turns(
    turns,
    {'service': 'Маникюр', 'day': 'в выходные', 'time_exact': '11:00', 'time_range': 'днем'},
    random.Random(0),
    service_candidates=('Маникюр',),
)
print(json.dumps(sanitized[9], ensure_ascii=False, indent=2))
PY`
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --scenarios-file /tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json --count 1 --min-turns 8 --max-turns 8 --include-media --scenario-coverage booking,info,interrupt --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --min-wait 0.0 --max-wait 0.15 --manager-mode simulate --pending-mode ack --tool-hooks auto --jid-mode unique --reset-before-dialog --allowlist-jids 99999000190@s.whatsapp.net --allow-non-allowlist --judge-mode all --run-economy-gate off --quality-lane auto --manual-audit-gate block --max-failures 1 --run-id a922-check-booking-proof-r12`
- Evidence to capture:
  - `/tmp/booking_quality/a922-promo-l2-preflight-r9/{summary.json,responses.jsonl,manual_audit.json}`
  - `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/{summary.json,brief.md,responses.jsonl,manual_audit.json}`
- Five Whys:
  1. Why did `r9` stop on turn 10? Because the scenario file still required `action=reply` for a booking-verification follow-up.
  2. Why was that expectation stale? Because the replay reused an older `scenarios-file` artifact and loader replayed it as-is.
  3. Why is this not a runtime bug? Because current runtime tests and `r12` both show `check_booking_prompt` is the correct bounded owner path for this turn.
  4. Why did the refreshed run stay semantic-red? Because turns `9` and `12` still produce advisory judge/HQ1 disagreement and `booking_slot_progress_rate=0.0`, even though strict contract checks pass.
  5. Why stop here instead of patching? Because turns `9` and `12` are the next classification boundary: either oracle/proof needs strengthening, or a new runtime family exists. That must be proved before code.
- Root cause statement:
  - the active blocker is now proof-layer drift, not the old promo interrupt runtime bug: stale scenario artifact `a922-weekend-slot-constraint-dialog.json` encoded obsolete turn-10 expectations, and once refreshed, the remaining red moved to advisory judge/progress alignment on turns `9` and `12`.
- Fix mechanism:
  - freeze refreshed scenario/run evidence, switch canon to this proof-gap audit block, and force the next block to classify turns `9` / `12` before any runtime or oracle changes.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py`
  - `ops/diagnose.py llm-quality`
  - `ops/diagnose.py llm-quality-audit`
  - existing `check_booking_prompt` contract tests listed above
- External reuse:
  - official Rasa forms / unhappy-path guidance only
- Why not reinvent the wheel:
  - the repo already has the right requested-slot interruption model; the immediate need is truthful evidence and classification, not a new runtime branch.

## Execution profile (mandatory for non-doc blocks)
- TP mode: `implementation`
- Doc touch budget (files): `30`
- Code dominance: `off`
- Override token: `none`
- Why this profile fits:
  - the work is proof/evidence-heavy and this worktree is already dirty from prior runtime blocks, so `doc_only` would fail-closed in session governance even though no new runtime code is planned.

## Invariant
- do not touch frozen webhook routers
- do not add runtime hotfixes for turns `9` / `12` before classification
- do not weaken judge / threshold / acceptance gates
- keep the promo interrupt closure recorded as done; this block only reclassifies the next proof blocker

## Scope
- freeze the `r9` vs `r12` evidence chain
- publish a new active TP/report for the proof-gap audit
- sync canon/session/packet to the refreshed blocker classification
- keep next move explicit: classify turns `9` / `12` before runtime changes

## Out of scope
- runtime code changes in `truffles-api/app/services/reasoning_core.py` or elsewhere
- scenario-loader behavior changes
- canonical acceptance lock/replay/full runs
- multi-pack matrix or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the stale-turn-10 proof with `r9` + sanitized scenario evidence.
2. Freeze the refreshed `r12` proof showing strict pass across all 14 turns and residual advisory red.
3. Publish the new TP/report and switch canon from the old promo-bug block to this proof-gap audit.
4. Rebuild the agent packet and rerun doc/architecture guards.

## DoD
- `docs/SOURCE_OF_TRUTH.yaml` points `active_block_tp` at this TP
- `docs/ACTIVE_PROGRAM.md`, `STATE.md`, and session docs state that turn `10` is no longer the blocker
- refreshed run `a922-check-booking-proof-r12` is recorded as `infra_valid=true`, `turns_strict_failed=0`, `failure_family_count=0`
- remaining red is explicitly captured as advisory `judge_oracle_alignment_gap` / `booking_slot_progress_rate`, not misreported as the old promo runtime bug
- packet/guard stack passes after sync

## Classification addendum (2026-03-22)
- Turn `9` verdict: `runtime contract bug`
  - explicit exact-time fill (`11 утра`) under active `expected_reply_type=time` is still regressing to a stale `Подскажите, пожалуйста, точное время` re-ask
  - repo/runtime contracts already require either slot progression to `name` or bounded handoff for exact-time reschedule-without-reference turns
- Turn `12` verdict: `oracle/proof gap`
  - current strict oracle still permits `booking_prompt` as fallback for expected `handoff` while `booking_active=true`
  - current `r12` trace/meta do not yet prove that this turn independently violated the runtime reschedule-handoff contract
- Sequencing consequence:
  - do not tighten turn-12 oracle first
  - fix or reproduce the turn-9 runtime family first, rerun, then decide whether turn `12` survives as an independent oracle/runtime issue

## Checks
- `python3 - <<'PY'
import json, random, sys
from pathlib import Path
sys.path.insert(0, 'truffles-api')
from app.services.llm_quality_contracts import sanitize_booking_scenario_llm_turns
payload = json.loads(Path('/tmp/booking_quality/a922-weekend-slot-constraint-dialog.json').read_text())
turns = payload['dialogs'][0]['turns']
sanitized = sanitize_booking_scenario_llm_turns(
    turns,
    {'service': 'Маникюр', 'day': 'в выходные', 'time_exact': '11:00', 'time_range': 'днем'},
    random.Random(0),
    service_candidates=('Маникюр',),
)
print(json.dumps(sanitized[9], ensure_ascii=False, indent=2))
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
for run in ['a922-promo-l2-preflight-r9', 'a922-check-booking-proof-r12']:
    summary = json.loads(Path('/tmp/booking_quality', run, 'summary.json').read_text())
    print(run, summary.get('infra_valid'), summary.get('semantic_valid'), summary.get('stop_reason'))
PY`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r12 --status done --strict-artifacts`
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
- `/tmp/booking_quality/a922-promo-l2-preflight-r9/summary.json`
- `/tmp/booking_quality/a922-promo-l2-preflight-r9/responses.jsonl`
- `/tmp/booking_quality/a922-promo-l2-preflight-r9/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/brief.md`
- `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- Fail-fast / scenario lock: one refreshed dev preflight already captured as `r12`
- Stop condition: if refreshed evidence still looked like a strict runtime blocker, split a new classification TP before any code
- Escalation path: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: no runtime or rollout change in this block
- Go/no-go signals: packet/docs/guards stay green; no frozen-file touch
- Rollback: revert canon/session/test/doc changes and rebuild packet
- Post-release monitoring window: next block must classify turns `9` / `12` before any guarded acceptance promotion

## Doc sync plan (after implementation)
- Docs/specs to update in same block:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- Drift closeout rule:
  - this block stays open until canon and generated packet all point at the same proof-gap audit TP/report.

## Rollback
- revert the new TP/report/canon sync, rerun packet build/check, and restore the prior promo-bug TP as active.

## No-go
- do not reopen the old promo interrupt runtime bug without contrary evidence
- do not edit runtime code because of judge-only advisory red
- do not keep replaying stale scenario artifacts as if they were canonical truth
- do not weaken `booking_slot_progress_rate` or HQ1/judge gates to claim progress
- do not claim turn `12` is a proved runtime bug from the current `r12` artifact alone

## Risks / blockers
- turn `9` exact-time progression family now needs a bounded runtime RCA/fix block
- turn `12` may collapse after the turn-9 fix rerun because current evidence is downstream of stale time-collect state
- `llm-quality` replaying stale scenario files remains an operational footgun until the next block decides whether loader behavior or runbook guidance should change
- guarded acceptance remains blocked until the turn-9 runtime family is handled and turn `12` is rerun truthfully

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - turn `9` runtime exact-time progression family remains unfixed
  - turn `12` oracle/proof weakness remains untightened until post-fix rerun
  - guarded `demo_salon/main` acceptance lock/replay/full is still pending
  - multi-pack matrix and open-world closure remain pending
- Why not in this block:
  - this block closes the truthful classification boundary only; it does not open a new runtime implementation family
- Risk if deferred:
  - without a bounded turn-9 runtime block, the team could keep arguing about turn `12` on top of already-corrupted booking state
- Linked follow-up Task Package(s):
  - `author_consultant_core_demo_salon_turn9_exact_time_progression_runtime_tp`
- Expiry/trigger to stop deferral:
  - stop deferral immediately before any new runtime patch, oracle tightening, or guarded acceptance baseline update

## Next-block contract (mandatory)
- Next block objective:
  - author the bounded runtime TP for the turn-9 exact-time progression family, using turn `12` only as downstream oracle debt until a post-fix rerun proves otherwise
- First deterministic check command:
  - `python3 - <<'PY'
import json
from pathlib import Path
for idx in [8, 9, 12]:
    for line in Path('/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        if row.get('turn_index') == idx:
            print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('hq1_classes'))
            break
PY`
- Blocked-by conditions:
  - this canon sync not merged
  - `r12` manual audit not marked `done`
  - packet/guard stack not rebuilt after sync
- Owner role for closure:
  - `Brain | Top Architect`

## Handoff (for zero-context next agent)
- Ready for next agent: `yes`
- Start from: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- Do not touch: frozen routers, runtime core, acceptance thresholds
- Open risks: `turn 9 exact-time progression bug is still live`, `turn 12 may be oracle-only once turn 9 is fixed`, `stale scenario replay is an operational hazard`
- First command to verify:
  - `python3 - <<'PY'
import json
from pathlib import Path
for idx in [8, 9, 12]:
    for line in Path('/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        if row.get('turn_index') == idx:
            print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'))
            break
PY`
