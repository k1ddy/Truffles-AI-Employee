# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R4 Confirm Hook Proof Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-PROOF-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r4_contract_aligned_confirm_hook_proof_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded proof-decision block for exact replay `r4`. This block must prove whether `confirm_hook_missing` belongs to runtime, transport/readiness, or proof/tooling, and it must lock the next move before any more runtime or acceptance-evidence work resumes.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`

## FACT pre-check (before decision sync)
- **Impacted docs/tests:**
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- **Baseline commands:**
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r4 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r4/summary.json').read_text())
print(summary['quality_status']['infra_reasons'])
print(summary['tool_evidence']['counts'])
PY`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if (row.get('tool_signals') or {}).get('confirm'):
        print({
            'dialog': row.get('dialog_index'),
            'turn': row.get('turn_index'),
            'tags': row.get('turn_tags'),
            'calendar_intent': (row.get('tool_signals') or {}).get('calendar', {}).get('intent'),
            'hook_actions': [hook.get('action') for hook in (row.get('tool_hooks') or []) if isinstance(hook, dict)],
        })
PY`
  - `nl -ba ops/diagnose.py | sed -n '5412,5430p'`
  - `nl -ba ops/diagnose.py | sed -n '11676,11731p'`
  - `nl -ba truffles-api/tests/test_booking_quality_tool_evidence_gate.py | sed -n '134,176p'`
- **FACT findings:**
  - `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` is infra-invalid because `quality_status.infra_reasons=['tool_evidence:confirm_hook_missing']`; this is the first admissible blocker on the exact replay artifact.
  - The same summary shows `confirm_tool_events=2`, `confirm_hook_events=0`, and `confirm_opportunity_total=4`, so the proof lane required confirm evidence but observed no confirm hook sends.
  - The only confirm-required rows on `r4` are dialog `1` turn `12` and dialog `2` turn `7`; both have `turn_tags=['confirm']`, `tool_signals.calendar.intent='check_booking'`, and `tool_hooks=['calendar']` with no confirm hook error or confirm send attempt recorded.
  - `_llm_quality_build_tool_evidence_status(...)` counts `check_booking` as a confirm candidate, but `_llm_quality_should_send_confirm_hook(...)` only sends a synthetic confirm hook on `confirm`-tagged turns when the normalized calendar intent is `calendar.get_booking`.
  - The pre-fix blocker artifact `/tmp/booking_quality/a922-go2f-seed19/summary.json` was infra-valid and had `confirm_hook_events=2`, but those hooks were reached later on untagged `check_booking` rows; `r4` fail-fast stopped before those later rows.
- **INFERENCE to verify in this block:**
  - the next truthful move is a bounded proof/tool-evidence implementation family in `ops/diagnose.py`, not a runtime patch and not a transport/readiness fix.

## One web search (mandatory before implementation)
- **Reuse rule for this block:** decision-only block; no new query was opened. Reuse the latest proof-lane search already recorded in `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`.
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm judge pass fail clear detailed rubric`
- **Date/time (local):** `2026-03-22T13:34:21+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Existing solutions found:** keep evaluators aligned to the production contract, calibrate automated scoring against human arbitration, and prefer explicit task-specific pass/fail logic over looser judge interpretation when the contract is already defined.
- **Decision:** `reuse/integrate`
- **Reuse note:** no new query was opened in this decision block; the existing proof-lane search is reused only as contract-evaluation context.
- **Rejected options:** opening a new runtime family before infra is restored; treating the replay as transport failure without evidence of a failed confirm-hook send; weakening strict tool-evidence gates for fail-fast replay.

## Root cause (mandatory)
- **Symptom:** exact replay `r4` is infra-invalid before the old runtime blocker can be reclassified because strict tool evidence reports `confirm_hook_missing`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` and confirm `infra_valid=false`, `tool_evidence.valid=false`, and `tool_evidence.reasons=['confirm_hook_missing']`
  2. inspect `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl` and confirm the only confirm-required rows have `turn_tags=['confirm']`, `tool_signals.calendar.intent='check_booking'`, and only `calendar` hooks recorded
  3. inspect `ops/diagnose.py:5412-5430` and `ops/diagnose.py:11676-11731` and confirm the hook-sending predicate and the strict evidence counter are not aligned on `check_booking`
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`
  - `ops/diagnose.py:5412-5430`
  - `ops/diagnose.py:11676-11731`
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- **Five Whys:**
  1. Why is `r4` infra-invalid? Because strict tool evidence says `confirm_hook_missing`.
  2. Why is `confirm_hook_missing` raised? Because `confirm_opportunity_total > 0` while `confirm_hook_events == 0`.
  3. Why do confirm opportunities exist on `r4`? Because strict evidence counts `check_booking` intents as confirm candidates.
  4. Why were no confirm hooks observed? Because the only observed confirm rows are `confirm`-tagged turns whose calendar intent stays `check_booking`, and `_llm_quality_should_send_confirm_hook(...)` suppresses the synthetic confirm hook for those rows.
  5. Why did the old blocker artifact not show this? Because the full pre-fix run reached later untagged `check_booking` rows that did emit confirm hooks, while fail-fast `r4` stopped before those later rows.
- **Root cause statement:** `r4` is blocked by a proof/tool-evidence parity gap in `ops/diagnose.py`, not by runtime semantics or transport delivery: strict evidence counts `check_booking` as a confirm opportunity, but the synthetic confirm-hook sender does not mirror that rule on `confirm`-tagged `check_booking` rows, so fail-fast exact replay can go infra-red before the runtime blocker is even reclassified.
- **Fix mechanism:** keep runtime untouched; align `ops/diagnose.py` confirm-hook eligibility and/or strict evidence counting with the same `check_booking` confirm contract, add deterministic regressions around `confirm`-tagged `check_booking` rows and fail-fast replay prefixes, then rerun the exact replay.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing strict tool-evidence helpers in `ops/diagnose.py`
  - existing tool-evidence tests in `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
  - exact blocker artifacts `/tmp/booking_quality/a922-go2f-seed19` and `/tmp/booking_quality/a922-go2f-seed19-r4`
- **External reuse:**
  - none beyond the already-recorded proof-lane search above
- **Why not reinvent the wheel:**
  - the repo already has the relevant hook sender, evidence counter, and deterministic test surface; this block only chooses the right layer for the next fix.

## Work mode (mandatory)
- **Mode:** `forensic`
- **Why this mode:** this block is classification-only and must prove the first surviving blocker layer before any new code.
- **Family handled in this block:** `seed19 r4 confirm-hook proof parity family`
- **Closure artifact expected from this mode:** one decision TP/report pair plus canon sync and one exact implementation handoff.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** the block is doc-only by intent, but the worktree still carries approved runtime diffs; keeping `implementation` mode avoids false governance failure on the existing code delta while canon switches to the proof lane.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not reinterpret the downstream explicit-handoff mismatch as admissible until infra is restored
- do not reopen checklist assembly or acceptance lock work in this block

## Scope
- classify `r4` by layer
- prove whether `confirm_hook_missing` belongs to runtime, transport/readiness, or proof/tooling
- lock one bounded next move from the exact replay evidence
- sync canon/session/packet to the new decision block

## Out of scope
- `ops/diagnose.py` code changes in this block
- new replay run or baseline update
- runtime implementation
- scenario mutation
- acceptance evidence-pack work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
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
1. Re-audit `r4` and inspect the confirm-hook rows plus the matching helper logic in `ops/diagnose.py`.
2. Publish this bounded proof decision TP and matching report with RCA and exact evidence.
3. Switch canon/session artifacts from the replay block to this proof-decision block.
4. Rebuild the packet and rerun the mandatory guard/session stack.
5. Hand off one exact proof implementation family before any more runtime or acceptance work.

## DoD
- this TP and matching report exist and are the active block artifacts
- canon states that `r4` is blocked by a proof/tool-evidence parity gap, not a runtime regression
- canon states that the downstream semantic mismatch on dialog `2` turn `9` remains inadmissible until infra is restored
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the confirm-hook proof implementation family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r4 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r4/summary.json').read_text())
print(summary['quality_status']['infra_reasons'])
print(summary['tool_evidence']['counts'])
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if (row.get('tool_signals') or {}).get('confirm'):
        print({
            'dialog': row.get('dialog_index'),
            'turn': row.get('turn_index'),
            'tags': row.get('turn_tags'),
            'calendar_intent': (row.get('tool_signals') or {}).get('calendar', {}).get('intent'),
            'hook_actions': [hook.get('action') for hook in (row.get('tool_hooks') or []) if isinstance(hook, dict)],
        })
PY`
- `nl -ba ops/diagnose.py | sed -n '5412,5430p'`
- `nl -ba ops/diagnose.py | sed -n '11676,11731p'`
- `nl -ba truffles-api/tests/test_booking_quality_tool_evidence_gate.py | sed -n '134,176p'`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Max lock runs:** `0`
- **Max new audits:** `0`
- **Fail-fast / scenario lock:** reuse existing `r4` artifact only
- **Stop condition:** stop as soon as the layer decision is locked and synced in canon
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** decision-only block; no runtime rollout.
- **Go/no-go signals:** canon must point at the proof/tool-evidence family and no runtime or acceptance claim may move past `r4` while infra is invalid.
- **Rollback:** revert doc/canon updates only.
- **Post-release monitoring window:** none; no rollout in this block.

## Rollback
- revert doc/canon/session updates only; preserve `r4` artifacts and audit as evidence

## No-go
- do not patch runtime in this block
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not relabel `r4` as a runtime blocker first
- do not rerun seed `19`, seed `42`, or acceptance lock work in this block

## Risks/Blockers
- the proof lane may still need a second split between hook-eligibility and evidence-counting logic during implementation
- downstream runtime mismatch on dialog `2` turn `9` may survive after infra is repaired
- duplicate owner surfaces in `reasoning_core.py` remain unrelated but deferred debt

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** acceptance evidence-pack materialization, seed `42`, downstream `r4` semantic mismatch, and duplicate-def debt remain deferred.
- **Why not in this block:** this block is decision-only and exists to prevent a new runtime patch from being opened on infra-invalid evidence.
- **Risk if deferred:** without a clean layer decision, the team could reopen runtime churn or acceptance work on a non-canonical blocker.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one forthcoming proof implementation TP for the `r4` confirm-hook family.
- **Expiry/trigger to stop deferral:** stop deferral immediately after the confirm-hook proof family is either implemented or disproved.

## Next-block contract (mandatory)
- **Next block objective:** implement the bounded proof/tool-evidence family behind `r4` so confirm-tagged `check_booking` turns satisfy the same strict confirm contract already counted by the evidence gate.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook"`
- **Blocked-by conditions:** the current evidence is disproved as transport failure or runtime code starts sending confirm hooks before proof changes are made.
- **Owner role for closure:** `Brain | Top Architect`
