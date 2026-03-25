# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R4 Contract-Aligned Confirm Hook Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONTRACT-ALIGNED-CONFIRM-HOOK-PROOF-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-PROOF-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r4_confirm_hook_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Land one bounded proof-only implementation family for exact replay `r4`. This block must align synthetic confirm-hook eligibility with the strict confirm-evidence contract already counted by `ops/diagnose.py`, without touching runtime code, frozen routers, thresholds, or the locked replay scenarios.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`

## FACT pre-check (before implementation)
- **Impacted code/docs/tests:**
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
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
  - `nl -ba truffles-api/tests/test_booking_quality_tool_evidence_gate.py | sed -n '134,320p'`
- **FACT findings:**
  - `r4` is already classified as proof/tool-evidence red, not runtime red.
  - Strict evidence counts `check_booking` as a confirm opportunity.
  - The synthetic confirm-hook sender currently suppresses `confirm`-tagged `check_booking` rows, so no confirm hook is attempted on the exact replay prefix.
  - The old full blocker artifact stayed infra-valid only because it later reached untagged `check_booking` rows that emitted confirm hooks.

## One web search (mandatory before implementation)
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm evaluator pass fail rubric deterministic contract alignment`
- **Date/time (local):** `2026-03-22T19:17:00+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Existing solutions found:** evaluators should stay aligned to the production contract, use explicit pass/fail criteria, and avoid auxiliary heuristics that contradict the accepted measurement contract.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing strict confirm-evidence contract
  - integrate the fix only into the synthetic confirm-hook proof helper and its deterministic tests
- **Rejected options:** runtime changes; threshold weakening; reclassifying the downstream runtime row before infra is restored.

## Root cause (mandatory)
- **Symptom:** exact replay `r4` fails infra with `confirm_hook_missing` before the old runtime blocker can be reclassified.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` and confirm `quality_status.infra_reasons=['tool_evidence:confirm_hook_missing']`
  2. inspect `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl` and confirm the observed confirm-required rows are `confirm`-tagged `check_booking` turns with only `calendar` hooks recorded
  3. inspect `ops/diagnose.py:5412-5430` and `ops/diagnose.py:11676-11731` and confirm sender/counter parity drift on `check_booking`
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
  1. Why is `r4` infra-invalid? Because strict tool evidence reports `confirm_hook_missing`.
  2. Why is `confirm_hook_missing` reported? Because `confirm_opportunity_total > 0` while `confirm_hook_events == 0`.
  3. Why are confirm opportunities present? Because strict evidence counts `check_booking` and `check_record` as confirm candidates.
  4. Why were no confirm hooks observed on `r4`? Because the only observed prefix rows are `confirm`-tagged `check_booking` turns, and the current helper suppresses synthetic confirm hooks on them.
  5. Why did the older full artifact stay green on infra? Because it later reached untagged alias turns that emitted confirm hooks and masked the parity gap.
- **Root cause statement:** `_llm_quality_should_send_confirm_hook(...)` is narrower than the strict confirm-evidence contract already enforced by `_llm_quality_build_tool_evidence_status(...)`, so fail-fast exact replay prefixes can go infra-red on `confirm`-tagged `check_booking` turns even though the same alias is already counted as a confirm-required path.
- **Fix mechanism:** expand synthetic confirm-hook eligibility so `confirm`-tagged `check_booking` / `check_record` alias turns satisfy the same strict confirm contract already counted by the evidence gate, and lock that behavior with deterministic proof tests before replay.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing strict tool-evidence helpers in `ops/diagnose.py`
  - existing deterministic proof surface in `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
  - exact replay artifacts `/tmp/booking_quality/a922-go2f-seed19` and `/tmp/booking_quality/a922-go2f-seed19-r4`
- **External reuse:**
  - official OpenAI evaluation best-practices guidance only
- **Why not reinvent the wheel:**
  - the repo already has the correct strict confirm contract and the hook infrastructure; this block only restores parity between them.

## Work mode (mandatory)
- **Mode:** `implementation`
- **Why this mode:** this block changes bounded proof-only code and deterministic proof.
- **Family handled in this block:** `seed19 r4 contract-aligned confirm-hook parity`
- **Closure artifact expected from this mode:** local deterministic proof + canon sync + exact replay handoff

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** the block changes one proof-only code file and one deterministic test file, then syncs canon to the implementation handoff.

## Invariant
- do not edit runtime behavior in `truffles-api/app/services/reasoning_core.py`
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked replay scenarios
- do not claim runtime closure from deterministic proof alone

## Scope
- update `ops/diagnose.py` synthetic confirm-hook helper for the surfaced alias parity gap
- add deterministic regressions in `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- sync canon/session/packet to the implementation result

## Out of scope
- new replay run in this block
- runtime implementation
- scenario mutation
- acceptance evidence-pack work
- edits to frozen routers

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
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
1. Land the bounded confirm-hook parity update in `ops/diagnose.py`.
2. Add targeted deterministic regressions in `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`.
3. Re-run focused proof checks.
4. Sync canon/session/packet to the implementation result.
5. Hand off the next move as one exact replay on the same locked seed-`19` scenarios.

## DoD
- `ops/diagnose.py` changes stay bounded to the confirm-hook proof helper for this family
- targeted proof tests are green
- the new deterministic coverage proves `confirm`-tagged `check_booking` and `check_record` alias turns now send confirm hooks under the strict contract
- mandatory guard/session stack is green after canon sync
- next non-negotiable move is a fresh exact replay, not another local proof patch

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"`
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
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Max lock runs:** `0`
- **Max new audits:** `0`
- **Fail-fast / scenario lock:** reuse existing `r4` artifact only; no replay in this block
- **Stop condition:** stop as soon as deterministic proof is green and canon is synced to the replay handoff
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** proof-only local change; no runtime rollout.
- **Go/no-go signals:** deterministic proof is green, guard/session stack is green, and canon points the next move at exact replay rather than runtime work.
- **Rollback:** revert `ops/diagnose.py`, proof tests, and doc/canon updates.
- **Post-release monitoring window:** next block must be the exact replay; no acceptance work resumes first.

## Rollback
- revert `ops/diagnose.py`, proof tests, and doc/canon/session updates only; preserve `r4` artifacts as evidence

## No-go
- do not patch runtime in this block
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not weaken tool-evidence gates for fail-fast replay
- do not run seed `19`, seed `42`, or acceptance lock work in this block

## Risks/Blockers
- downstream runtime mismatch on dialog `2` turn `9` may survive after infra is repaired
- the exact replay may expose a narrower proof or runtime family immediately after the confirm-hook parity fix
- duplicate owner surfaces in `reasoning_core.py` remain unrelated but deferred debt

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** downstream `r4` semantic mismatch, acceptance evidence-pack materialization, seed `42`, and duplicate-def debt remain deferred.
- **Why not in this block:** this block exists only to restore proof parity so the next replay becomes admissible.
- **Risk if deferred:** without this fix, the team keeps chasing infra-invalid evidence and cannot truthfully reopen runtime or acceptance lanes.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one forthcoming exact replay TP for the repaired `r4` family.
- **Expiry/trigger to stop deferral:** stop deferral immediately after the fresh exact replay is classified.

## Next-block contract (mandatory)
- **Next block objective:** rerun the exact seed-`19` blocker scenarios on fresh local runtime and reclassify the downstream path only after infra is restored.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"`
- **Blocked-by conditions:** deterministic proof stays red or the fix requires runtime/sandbox changes outside `ops/diagnose.py`.
- **Owner role for closure:** `Brain | Top Architect`
