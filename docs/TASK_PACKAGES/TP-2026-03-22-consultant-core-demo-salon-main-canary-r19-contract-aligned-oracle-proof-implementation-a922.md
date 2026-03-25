# TP-2026-03-22 — Consultant Core Demo Salon Main Canary R19 Contract-Aligned Oracle Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-PROOF-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-ORACLE-CONFLICT-PROOF-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-CANARY-REPLAY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Land one bounded oracle-proof implementation family for truthful replay `r19`. This block must align `ops/diagnose.py` auxiliary oracle layers with the contract-first truth already accepted by strict evaluation and manual audit, without touching runtime code, thresholds, or the locked canary scenario.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_judge_suppression.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r19 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [6, 9, 11, 12]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('evaluation'), row.get('judge'))
PY`
  - `nl -ba ops/diagnose.py | sed -n '4288,4468p'`
  - `nl -ba ops/diagnose.py | sed -n '9152,9235p'`
  - `nl -ba truffles-api/tests/test_booking_quality_judge_suppression.py | sed -n '106,220p'`
  - `nl -ba truffles-api/tests/test_booking_quality_status_gate.py | sed -n '2005,2098p'`
- `FACT findings`:
  - `r19` is already runtime-green (`infra_valid=true`, `turns_strict_failed=0`), so the implementation surface is proof-only.
  - semantic invalidity still comes from auxiliary oracle layers, not strict contract failure.
  - turns `9` and `12` are strict-green booking continuations but still count as semantic blockers via HQ1 `handoff_miss`.
  - turns `6`, `9`, `11`, and `12` remain judge `missed_question` despite contract-first green truth.

## One web search (mandatory before implementation)
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm judge pass fail clear detailed rubric`
- **Date/time (local):** `2026-03-22T13:34:21+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Reuse rule for this block:** no new query. Reuse the single exact search already recorded in the parent oracle family decision; this implementation stays inside the same proof family.
- **Existing solutions found:**
  - automated grading should stay aligned to production behavior and calibrated to human judgment
  - pass/fail rubrics must be clear and specific to the contract being measured
  - auxiliary oracle layers should not outrun the product contract they summarize
- **Decision:** `reuse/integrate`
  - reuse the repo's existing contract-first strict evaluator and manual-audit arbitration
  - integrate parity fixes into the auxiliary oracle helpers only
- **Rejected options:**
  - runtime changes
  - threshold weakening
  - scenario mutation before oracle parity is fixed

## Root cause (mandatory)
- **Symptom:** truthful replay `r19` remains semantically invalid even though strict contract evaluation is green.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json` and confirm `turns_strict_failed=0`, `semantic_valid=false`, `blocking_reasons={'handoff_miss': 2}`.
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl` turns `9` and `12` and confirm both are strict-green collect continuations that still land in HQ1 `handoff_miss`.
  3. inspect turns `6`, `9`, `11`, and `12` and confirm judge still reports `missed_question` while strict reasons stay empty.
  4. inspect `ops/diagnose.py:4288-4468` and `ops/diagnose.py:9152-9235` and confirm suppression / HQ1 helper logic lags behind the already-accepted contract fallbacks.
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
  - `ops/diagnose.py:4288-4468`
  - `ops/diagnose.py:9152-9235`
- **Five Whys (or equivalent):**
  1. Why is semantic validity still red? Because auxiliary oracle layers still emit false `handoff_miss` and `missed_question` on strict-green turns.
  2. Why do turns `9` and `12` still block? Because HQ1 does not mirror the active-booking collect fallback already accepted by the contract evaluator.
  3. Why do turns `6`, `9`, `11`, and `12` still get judge fail? Because judge suppression does not yet recognize the current contract-valid collect envelopes.
  4. Why is this not a runtime fix? Because the same artifact already has `winner=contract` and zero strict failures.
  5. Why is the implementation bounded? Because only `ops/diagnose.py` heuristics and their proof regressions lag behind.
- **Root cause statement:** auxiliary oracle helpers in `ops/diagnose.py` are out of parity with the current contract-first evaluator, so contract-valid turns still produce semantic-invalid residue.
- **Fix mechanism:** update judge suppression and HQ1 classification to mirror the accepted contract envelopes on `r19`, then lock the next move to a fresh replay on the same canary path.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - contract-first action fallback in `ops/diagnose.py`
  - manual-audit arbitration on `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
  - existing proof tests in `truffles-api/tests/test_booking_quality_judge_suppression.py` and `truffles-api/tests/test_booking_quality_status_gate.py`
- **External reuse:**
  - official OpenAI evaluation best-practices guidance only
- **Why not reinvent the wheel:**
  - the repo already knows the right answer; the missing work is auxiliary oracle parity.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes bounded proof-only code and deterministic proof.
- `Family handled in this block`: `r19 contract-aligned oracle parity`
- `Closure artifact expected from this mode`: local deterministic proof + canon sync + replay handoff

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `20`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - the block changes proof-only code in one file and two deterministic test files, then syncs canon.

## Invariant
- do not edit runtime behavior in `truffles-api/app/services/reasoning_core.py`
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked scenario file
- do not claim acceptance closure from deterministic proof alone

## Scope
- update `ops/diagnose.py` judge suppression for the surfaced contract-valid collect envelopes
- update `ops/diagnose.py` HQ1 classifier so it does not over-block contract-valid active booking continuation
- add deterministic regressions covering those exact surfaced families
- sync canon/session/packet to the implementation handoff

## Out of scope
- new replay run in this block
- runtime implementation
- scenario mutation
- edits to frozen routers
- multi-pack acceptance or open-world closure

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
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
1. Land bounded parity updates in `ops/diagnose.py` for judge suppression and HQ1 handoff classification.
2. Add targeted regressions in the existing oracle proof test files.
3. Re-run focused deterministic checks plus a helper probe against the existing `r19` artifact.
4. Sync canon/session/packet to the new implementation block.
5. Hand off the next move as one fresh replay on the same locked canary surface.

## DoD
- `ops/diagnose.py` changes stay bounded to the oracle helpers for this family
- targeted proof tests are green
- helper probe on the existing `r19` rows shows turns `6`, `9`, `11`, and `12` now suppress `missed_question`, and turns `9` / `12` no longer classify as `handoff_miss`
- mandatory guard/session stack is green after canon sync
- next non-negotiable move is a fresh replay, not another local proof patch

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"`
- `python3 - <<'PY'
import ast, json, re
from pathlib import Path
script = Path('ops/diagnose.py')
source = script.read_text(encoding='utf-8')
tree = ast.parse(source)
assigns = {
    'LLM_QUALITY_HQ1_CLASSES',
    'LLM_QUALITY_HQ1_RESCHEDULE_MARKERS',
    'LLM_QUALITY_HQ1_MASTER_MARKERS',
    'LLM_QUALITY_HQ1_SERVICE_OVERVIEW_MARKERS',
    'LLM_QUALITY_HQ1_HALLUCINATION_MARKERS',
}
funcs = {
    '_llm_quality_normalize_expect_token',
    '_llm_quality_normalize_tool_token',
    '_llm_quality_effective_intent',
    '_llm_quality_check_booking_tool_answered',
    '_llm_quality_has_expected_followup_prompt',
    '_llm_quality_should_suppress_missed_question_judge_fail',
    '_llm_quality_hq1_normalize_text',
    '_llm_quality_hq1_contains_any',
    '_llm_quality_hq1_has_hallucination_signal',
    '_llm_quality_collect_hq1_classes',
}
body=[]
for node in tree.body:
    if isinstance(node, ast.Assign):
        names={t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & assigns:
            body.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in funcs:
        body.append(node)
ns={'re': re}
exec(compile(ast.Module(body=body, type_ignores=[]), str(script), 'exec'), ns, ns)
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [6, 9, 11, 12]:
    row=next(r for r in rows if r.get('turn_index') == idx)
    suppress=ns['_llm_quality_should_suppress_missed_question_judge_fail'](
        judge_result=row.get('judge'),
        strict_reasons=(row.get('evaluation') or {}).get('strict_reasons') or [],
        meta=row.get('decision_meta') or {},
        meta_action=((row.get('decision_meta') or {}).get('action')),
        expected_reply_type_value=row.get('expected_reply_type'),
        booking_active=row.get('conversation_state') in {'bot_active', 'pending', 'manager_active'},
        turn_tags=row.get('turn_tags') or [],
        outbox_text=row.get('outbox_text') or '',
    )
    hq1=ns['_llm_quality_collect_hq1_classes'](row)
    print(idx, {'suppress': suppress, 'hq1': hq1})
PY`
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
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: no replay in this block
- `Stop condition`: if the parity fix would require runtime changes, scenario mutation, or threshold weakening
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: proof-only local change; no runtime rollout mutation
- Go/no-go signals: targeted proof tests and guard stack stay green
- Rollback: revert proof-only code/docs/tests, rebuild packet, rerun guards
- Post-release monitoring window: the next block must rerun the same locked canary before any acceptance claim changes

## Rollback
1. Revert `ops/diagnose.py` and the two targeted proof test files.
2. Revert this TP/report and canon/session updates.
3. Rebuild the packet and rerun the mandatory guard stack.

## No-go
- do not change runtime semantics
- do not mutate the scenario file
- do not weaken thresholds or semantic gates
- do not touch frozen routers
- do not count this block as final acceptance closure

## Risks / blockers
- over-broad suppression could hide a future real semantic miss, so every new allowance must stay anchored to contract-valid strict-green envelopes only
- fresh replay is still required; local deterministic proof alone cannot close the program
- duplicate defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - fresh replay still pending after local oracle parity fix
  - duplicate defs in `truffles-api/app/services/reasoning_core.py` remain deferred
  - final acceptance / open-world closure remain pending
- `Why not in this block:`
  - this block is implementation-only for the bounded oracle family
- `Risk if deferred:`
  - without fresh replay, the repo still lacks truthful proof that semantic invalidity clears on the same canary surface
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_r19_contract_aligned_oracle_canary_replay`
- `Expiry/trigger to stop deferral:`
  - if the next replay surfaces a real strict runtime regression, stop and publish a new bounded decision before more oracle tuning

## Next-block contract (mandatory)
- `Next block objective:`
  - run one fresh replay on the same locked canary surface and prove whether `semantic_valid` clears after the oracle parity fix
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"`
- `Blocked-by conditions:`
  - if targeted proof tests are not green
  - if local runtime on the replay port is stale or missing
  - if a new replay would require scenario mutation first
- `Owner role for closure:`
  - `Hands`, with `Brain / Top Architect` accepting the replay evidence
