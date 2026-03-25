# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R5 Post Verification Reschedule Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_runtime_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded runtime decision block from fresh replay `r5`. This block must prove whether the first surviving turn after confirm-hook repair is a new proof/oracle artifact or a real runtime continuity bug, and it must lock the next implementation family before any more acceptance evidence work resumes.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
summary=json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r5/summary.json').read_text())
print({
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'tool_evidence_valid': (summary.get('tool_evidence') or {}).get('valid'),
    'tool_evidence_counts': (summary.get('tool_evidence') or {}).get('counts'),
    'stop_reason': summary.get('stop_reason'),
})
PY`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if row.get('dialog_index') == 1 and row.get('turn_index') in {12, 13}:
        print(json.dumps({
            'turn': row.get('turn_index'),
            'text': row.get('turn_text'),
            'expected_reply_type': row.get('expected_reply_type'),
            'decision_action': (row.get('decision_meta') or {}).get('action'),
            'decision_source': (row.get('decision_meta') or {}).get('source'),
            'decision_expected_reply_type': (row.get('decision_meta') or {}).get('expected_reply_type'),
            'booking_slots': row.get('booking_slots'),
            'strict_reasons': (row.get('evaluation') or {}).get('strict_reasons'),
            'tool_hooks': [hook.get('action') for hook in (row.get('tool_hooks') or []) if isinstance(hook, dict)],
        }, ensure_ascii=False))
PY`
  - `python3 - <<'PY'
import ast
from pathlib import Path
module=ast.parse(Path('truffles-api/app/services/reasoning_core.py').read_text())
for name in ['_try_handle_turn_planner_safe_booking_prompt_owner_cutover', '_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover']:
    print(name)
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            print(' ', node.lineno)
PY`
- `FACT findings`:
  - `r5` restores infra truth: `infra_valid=true`, `tool_evidence.valid=true`, and confirm evidence is now observed on the `check_booking` alias replay row.
  - The first surviving strict failure is dialog `1`, turn `13`, not the old proof/tool-evidence family.
  - Turn `12` preserved `service='Маникюр'`, `datetime='15:00'`, and `expected_reply_type=name`, but turn `13` reopens generic booking collect and drops service continuity.
  - The live path intersects shadowed owner names already tracked by the architecture guard.
- `INFERENCE to verify in this block`:
  - the next honest move is a bounded runtime continuity implementation family, with explicit live-owner write scope because the relevant owner functions are duplicated in `reasoning_core.py`.

## One web search (mandatory before implementation)
- `Reuse rule for this block`: decision-only block; no new query is opened. Reuse the latest implementation-family search already recorded in `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`.
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm evaluator pass fail rubric deterministic contract alignment`
- **Date/time (local):** `2026-03-22T19:17:00+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Reuse note:** no new query was opened in this decision block; the existing implementation-family search is reused only as contract-evaluation context.

- **Rejected options:** treating turn `13` as proof-only while infra is green; resuming acceptance evidence work before runtime reclassification; opening a second web query for this decision-only block.

## Decision:
- `r5` restores confirm-hook proof parity on the exact replay surface.
- The first surviving blocker is runtime, not proof/oracle.
- The next block must be one bounded runtime implementation family on the live later owner defs.

## Root cause (mandatory)
- Symptom: fresh exact replay `r5` restores confirm-hook infra but still fails strict on dialog `1`, turn `13` when the user proposes a new exact time after `check_booking` reference collect.
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json` and confirm `infra_valid=true`, `tool_evidence.valid=true`, `stop_reason=max_failures_reached:1`
  2. inspect `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl` turn `12` and turn `13` in dialog `1`
  3. confirm turn `12` holds `service='Маникюр'`, `datetime='15:00'`, `expected_reply_type=name`, while turn `13` resets to `expected_reply_type=service_choice` and `booking_slots={'datetime': '18:30'}`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r5/{summary.json,responses.jsonl,manual_audit.json}`
  - `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
  - `truffles-api/app/services/reasoning_core.py:4933`
  - `truffles-api/app/services/reasoning_core.py:6005`
  - `truffles-api/app/services/reasoning_core.py:9774`
  - `truffles-api/app/services/reasoning_core.py:10846`
  - `truffles-api/tests/test_reasoning_core.py:10777`
- Five Whys:
  1. Why is `r5` still semantic-red? Because dialog `1`, turn `13` fails `expected_state_mismatch`.
  2. Why does turn `13` fail state contract? Because runtime reopens generic booking collect and expects `service_choice` instead of keeping `name` pending.
  3. Why is `service_choice` reopened? Because the post-verification reschedule path loses grounded service continuity when the user proposes a new exact time.
  4. Why is grounded service continuity lost? Because the live booking-prompt owner path only carries forward `datetime='18:30'` and does not preserve the already grounded service from the verification context.
  5. Why is the next fix risky? Because the relevant owner surfaces are shadowed duplicate top-level defs, so the live write scope must be explicit.
- Root cause statement: after confirm-hook infra is restored, the first surviving blocker is a runtime continuity bug: post-verification exact-time reschedule re-enters generic booking collect, drops grounded `service`, and rewrites `expected_reply_type` from `name` to `service_choice` instead of preserving the collected verification context.
- Fix mechanism: patch the live later owner surface(s) in `reasoning_core.py` so post-verification reschedule preserves grounded `service`, updates `datetime`, and keeps `expected_reply_type=name`, then lock the behavior with deterministic regression before another replay.

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing exact replay evidence in `/tmp/booking_quality/a922-go2f-seed19-r5`
  - existing check-booking continuity tests around `truffles-api/tests/test_reasoning_core.py:10777`
  - live owner cutover surfaces in `truffles-api/app/services/reasoning_core.py`
- External reuse:
  - none beyond the already-recorded search above
- Why not reinvent the wheel:
  - the repo already has the exact replay artifact, existing continuity tests, and the live owner surfaces that need a bounded correction.

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: this block is classification-only and must lock the right runtime family before any code.
- `Family handled in this block`: `seed19 r5 post-verification exact-time reschedule continuity`
- `Closure artifact expected from this mode`: one decision TP/report pair plus canon sync and one bounded runtime implementation handoff.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `24`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: the block is doc-only by intent, but the worktree still carries approved code deltas; keeping `implementation` mode avoids false governance failure while canon switches to the new runtime family.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not relabel the turn `13` failure as proof-only now that infra is green
- do not resume acceptance evidence-pack work in this block

## Scope
- classify `r5` by layer
- prove whether turn `13` is runtime vs proof/oracle
- record shadow-risk on the live owner surfaces
- lock one bounded runtime next move from the fresh replay evidence
- sync canon/session/packet to the new decision block

## Out of scope
- runtime implementation in this block
- new replay run or baseline update
- proof/oracle changes
- seed `42`
- acceptance evidence-pack work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
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
1. Re-audit `r5` and inspect turn `12` vs turn `13` continuity on the fresh replay artifact.
2. Publish this bounded runtime decision TP and matching report with RCA and exact evidence.
3. Switch canon/session artifacts from the replay block to this runtime-decision block.
4. Rebuild the packet and rerun the mandatory guard/session stack.
5. Hand off one bounded runtime implementation family before any more acceptance evidence work.

## DoD
- this TP and matching report exist and are the active block artifacts
- canon states that `r5` restored confirm-hook infra and that turn `13` is now the first surviving runtime blocker
- canon states that the next runtime block must use the live later owner defs because the relevant function names are shadowed
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the bounded runtime family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from pathlib import Path
summary=json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r5/summary.json').read_text())
print(summary['infra_valid'])
print((summary.get('tool_evidence') or {}).get('valid'))
print((summary.get('tool_evidence') or {}).get('counts'))
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if row.get('dialog_index') == 1 and row.get('turn_index') in {12, 13}:
        print({
            'turn': row.get('turn_index'),
            'expected_reply_type': row.get('expected_reply_type'),
            'decision_expected_reply_type': (row.get('decision_meta') or {}).get('expected_reply_type'),
            'booking_slots': row.get('booking_slots'),
            'strict_reasons': (row.get('evaluation') or {}).get('strict_reasons'),
        })
PY`
- `python3 - <<'PY'
import ast
from pathlib import Path
module=ast.parse(Path('truffles-api/app/services/reasoning_core.py').read_text())
for name in ['_try_handle_turn_planner_safe_booking_prompt_owner_cutover', '_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover']:
    print(name)
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            print(node.lineno)
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r5/{summary.json,responses.jsonl,manual_audit.json}`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- Fail-fast / scenario lock: reuse existing `r5` artifact only
- Stop condition: stop as soon as the layer decision is locked and synced in canon
- Escalation path: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: decision-only block; no runtime rollout.
- Go/no-go signals: canon must point at the runtime family and no proof-only or acceptance claim may move past `r5` while turn `13` remains open.
- Rollback: revert doc/canon updates only.
- Post-release monitoring window: none; no rollout in this block.

## Rollback
- revert doc/canon/session updates only; preserve `r5` artifacts and audit as evidence

## No-go
- do not patch runtime in this block
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not relabel `r5` as proof debt first
- do not rerun seed `19`, seed `42`, or acceptance lock work in this block

## Risks/Blockers
- the next runtime implementation family will touch shadowed owner names in `reasoning_core.py`
- a bounded runtime fix may surface another downstream family only after this turn closes
- advisory judge conflicts remain secondary noise on partial fail-fast artifacts

## Residual architecture debt (mandatory)
- Current residuals accepted in this block: duplicate top-level defs in `truffles-api/app/services/reasoning_core.py`, seed `42`, PG checklist assembly, and acceptance `lock` retry remain deferred.
- Why not in this block: this block exists only to classify the first surviving blocker after the proof family closed.
- Risk if deferred: without the bounded runtime fix, acceptance re-entry stays blocked on stale seed-`19` semantics.
- Linked follow-up Task Package(s): `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one forthcoming runtime implementation TP for the `r5` family.
- Expiry/trigger to stop deferral: stop deferral immediately after the bounded runtime family is implemented and replayed.

## Next-block contract (mandatory)
- Next block objective: implement one bounded runtime fix so post-verification exact-time reschedule preserves grounded service, updates datetime, and keeps `expected_reply_type=name` on the live owner path.
- First deterministic check command: `python3 - <<'PY'
import ast
from pathlib import Path
module=ast.parse(Path('truffles-api/app/services/reasoning_core.py').read_text())
for name in ['_try_handle_turn_planner_safe_booking_prompt_owner_cutover', '_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover']:
    print(name)
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            print(node.lineno)
PY`
- Blocked-by conditions: the implementation would require frozen-router edits; the live owner write scope cannot be isolated from the shadowed names; a fresh RCA disproves the runtime classification.
- Owner role for closure: `Brain | Top Architect`
