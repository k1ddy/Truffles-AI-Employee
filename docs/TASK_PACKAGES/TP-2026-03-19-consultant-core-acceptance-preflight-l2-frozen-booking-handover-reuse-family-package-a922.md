# TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922

## Goal
Stop the next post-r17 churn loop and lock the surviving blocker to one bounded frozen booking handover-reuse family so the next implementation block can delete or truthfully localize that live seam instead of reopening non-frozen A/B/C work.

## Canon refs
- `STATE.md` NOW: consultant core `acceptance_preflight_l2_post_observer_runtime_failure_family` implementation GAP
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-post-observer-runtime-failure-family-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/brief.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/trace_bundle.jsonl`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the next implementation block either deletes the live frozen booking handover-reuse seam and materializes one truthful semantically valid fresh non-acceptance `L2` summary, or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `python keyword-only arguments official docs`
- **Date/time (local):** `2026-03-19T10:24:00+05:00`
- **Sources opened (from this query):**
  - `https://docs.python.org/3/reference/compound_stmts.html#function-definitions`
  - `https://docs.python.org/3/glossary.html#term-parameter`
- **Source quality:**
  - high-signal / primary source: official Python documentation
- **Found ready-made solutions:**
  - parameters declared after `*` are keyword-only
  - caller sites must supply keyword-only parameters explicitly by keyword
- **Decision:** `integrate`
  - keep the owner signature truthful and update the remaining frozen caller sites explicitly instead of widening the signature or adding a compatibility bridge
- **Rejected options:**
  - adding another wrapper/helper around `_reuse_active_handover(...)`: rejected because that preserves the mixed caller seam instead of deleting it
  - making `hooks` optional in the owner service: rejected because that would reintroduce silent mixed authority at the contract boundary

## Root cause (mandatory)
- **Symptom:** the one admissible fresh rerun after non-frozen A/B/C closure, `/tmp/booking_quality/l2-acceptance-preflight-a922-r17`, is still `semantic_valid=false`.
- **Minimal reproduction:**
  - keep the worktree runtime on `http://127.0.0.1:18184`
  - inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/{summary.json,brief.md,manual_audit.md,responses.jsonl,trace_bundle.jsonl}`
  - inspect the owner signature and surviving callers with:
    - `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py`
- **Evidence:**
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/summary.json` records `infra_valid=true`, `semantic_valid=false`, `stop_reason=max_failures_reached:1`, and `blocking_reasons={'run_completion_gap': 119}` because the run fail-fast stopped on the first surfaced semantic fail
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/manual_audit.md` records `artifact_integrity.valid=true`, `responses_rows=18`, `trace_rows=18`, `dialogs_seen=[1, 2]`, `judge_alignment=conflicted`, and `winner=contract`
  - representative row `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a` proves the surviving live blocker is a runtime exception, not an observer mismatch: `turn_text="Хотелось бы перенести на следующий понедельник."`, `decision_meta.error="_reuse_active_handover() missing 1 required keyword-only argument: 'hooks'"`
  - `truffles-api/app/services/handover_owner_service.py:1092-1101` defines `_reuse_active_handover(..., *, hooks: ActiveHandoverReuseRuntimeHooks)`
  - non-frozen callers are already aligned, for example `truffles-api/app/routers/webhook/info.py:1763-1775`
  - the remaining stale callers are all frozen in `truffles-api/app/routers/webhook/booking.py:1702`, `truffles-api/app/routers/webhook/booking.py:2358`, `truffles-api/app/routers/webhook/booking.py:2914`, `truffles-api/app/routers/webhook/booking.py:3007`, and `truffles-api/app/routers/webhook/booking.py:3741`
  - the next failing row `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-06-db71cd` only surfaces downstream expectation residue (`expected_meta_mismatch` / `expected_trace_miss` at `llm_policy_plan_delta`) after the runtime exception has already broken the booking contour
- **Five Whys:**
  1. Why is `r17` still semantic-red after A/B/C? Because a live runtime exception still survives on a booking contour.
  2. Why does that runtime exception survive? Because frozen `booking.py` still calls `_reuse_active_handover(...)` without the now-required keyword-only `hooks=` contract.
  3. Why did the previous block not remove it? Because the previous block was explicitly limited to non-frozen A/B/C surfaces and stopped truthfully once the blocker narrowed to frozen `booking.py`.
  4. Why is the remaining blocker now a legitimate next package? Because the owner service contract is already truthful and all surviving callers are localized to five frozen booking contours.
  5. Why would another rerun or observer work be false progress? Because `r17` already proves the active blocker is runtime contract drift on frozen booking callers, not transport, billing, or oracle semantics.
- **Root cause statement:** the surviving blocker after non-frozen A/B/C closure is a frozen caller-family drift: `booking.py` still invokes `_reuse_active_handover(...)` as if `hooks` were not required, even though the owner contract already moved and non-frozen callers were updated.
- **Fix mechanism:**
  - update the five frozen `booking.py` caller sites to pass `ActiveHandoverReuseRuntimeHooks(...)` explicitly
  - add focused regressions that prove each booking contour reuses the truthful owner contract without a new wrapper/helper
  - run exactly one fresh non-acceptance `L2` rerun and strict audit after the fix

## Invariant
- do not reopen transport, billing, observer, or non-frozen A/B/C work as the main story
- do not weaken judge/oracle gates, semantic thresholds, `go_to_full`, or acceptance thresholds
- do not widen `_reuse_active_handover(...)` with optional compatibility behavior
- do not add a new wrapper/helper to hide the frozen caller drift
- do not claim semantic / continuity / boundary full closure from this block alone
- do not run guarded acceptance `lock/replay/full` or multi-pack closure in this package

## Scope
- publish one bounded package for the surviving frozen booking handover-reuse family from `r17`
- lock the next implementation block to the five frozen `booking.py` caller sites only
- require that the next implementation block either deletes the live frozen caller seam or stops with a truthful narrower `GAP`
- allow one fresh non-acceptance `L2` rerun only after the frozen caller fix plus focused regressions

## Out of scope
- non-frozen A/B/C reopening
- observer/oracle refinement as the primary path
- billing/provider or transport remediation
- broader booking flow redesign
- handover owner signature redesign
- new compatibility wrappers/helpers
- acceptance closure claims

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- next implementation block only:
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_booking_chaos_dialogs.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing owner contract in `truffles-api/app/services/handover_owner_service.py`
  - already-aligned non-frozen callers in `info.py`, `policy.py`, `guards.py`, and `response.py`
  - fresh blocker evidence from `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/*`
  - existing handover frozen-history docs, especially `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- **External reuse:**
  - official Python documentation for keyword-only parameters
- **Why this reuse mix is truthful:**
  - the owner implementation already exists and already works on non-frozen paths, so the truthful move is to converge the remaining stale booking callers onto that same contract instead of inventing another abstraction layer

## Plan
1. Publish and register this frozen booking handover-reuse package, then switch canon to it.
2. Freeze the representative `r17` row and the five surviving `booking.py` caller sites.
3. Next implementation block: wire `ActiveHandoverReuseRuntimeHooks(...)` into those five frozen caller sites only.
4. Add focused regressions for `reschedule_request`, booking interrupt escalation, same-day escalation, human-request during active booking, and booking commit reuse.
5. Run focused deterministic subsets, then exactly one fresh non-acceptance `L2` rerun and strict audit.
6. Publish one bounded implementation report that either proves a truthful semantically valid fresh `L2` summary or stops with a narrower residual family.

## DoD
- canon points to this package as the active block
- the next move is fixed to `implement_acceptance_preflight_l2_frozen_booking_handover_reuse_family_closure_bundle`
- the package makes clear that the active blocker story is frozen `booking.py` caller drift, not non-frozen A/B/C, transport, billing, or observer work
- required doc/architecture/session guards pass

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/summary.json').read_text())
print(summary['infra_valid'])
print(summary['semantic_valid'])
print(summary['stop_reason'])
print(summary['blocking_reasons'])
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
obj = rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']
print(obj['turn_text'])
print(obj['decision_meta']['error'])
print(obj['decision_meta']['action'])
print(obj['decision_meta']['intent'])
PY`
- `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py`
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
- updated package and canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `STATE.md`, `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- representative fresh blocker evidence reused from `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/{summary.json,brief.md,manual_audit.md,responses.jsonl,trace_bundle.jsonl}`
- one bounded implementation report for the next block
- one fresh non-acceptance `L2` summary only if the next implementation block reaches semantic green

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- **Max full runs:** `0`
- **Max guarded acceptance runs:** `0`
- **Cheap deterministic gates first:** exact `r17` probes, frozen caller grep, focused regressions, runtime parity verification
- **Reuse policy:** reuse `r17` evidence; do not regenerate acceptance artifacts in this package
- **Stop condition:** if green requires another compatibility wrapper/helper, widening the owner signature, or reopening non-frozen families as the main story, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded dev-lane frozen-family reconciliation only; focused regressions before one rerun
- **Go/no-go signals:**
  - all five frozen booking callers pass the truthful `hooks=` contract
  - no new compatibility seam or widened owner signature is introduced
  - one fresh non-acceptance `L2` rerun reaches `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`
- **Rollback:**
  - revert the next implementation block changes
  - keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/*` untouched as blocker evidence
- **Rollback verification:**
  - rerun the focused frozen-family regressions
  - rerun `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r17 --status done --strict-artifacts`
- **Post-release monitoring window:** only until the bounded frozen-family implementation report is published; if the fresh rerun stays semantic-red, reopen as `GAP`

## Rollback
- Revert the docs/canon files touched by this block and rerun the required guards; keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/*` untouched as blocker evidence.

## No-go
- wrapper/helper growth counted as progress
- owner-signature widening to make `hooks` optional
- rerun-only progress without deleting the frozen caller seam
- reopening transport, billing, observer, or non-frozen A/B/C as the primary story
- silent acceptance or oracle weakening

## Risks / blockers
- the frozen caller family may reveal a second frozen booking seam after the runtime exception is cleared; that is admissible only if the first live caller seam is explicitly deleted first
- if the truthful green path requires touching frozen files outside `booking.py`, stop and publish `GAP` instead of broadening silently
- if the next rerun remains semantic-red but no frozen caller seam dies, the block is not progress

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- program-level `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial in `docs/SOURCE_OF_TRUTH.yaml`
- frozen `decision.py` still survives as broader semantic and boundary ingress
- final multi-pack acceptance closure is still not reached

### Why not in this block
- this package is limited to the surviving frozen booking handover-reuse family from `r17`
- reopening broader partial architecture tracks here would turn the next move back into an unbounded demolition wave

### Risk if deferred
- if this frozen family is not isolated now, the program will keep churning dev reruns without clearing the first live booking runtime exception

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- next implementation block from this package
- return path to `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next block tries to solve the family via compatibility bridge growth, owner-signature widening, or a rerun-only story

## Next-block contract (mandatory)
### Next block objective
- implement one bounded frozen booking handover-reuse closure bundle that deletes or truthfully localizes the remaining live `_reuse_active_handover(..., hooks)` caller seam in `booking.py`, then run one strict non-acceptance `L2` rerun

### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
checks = {
    'error': rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']['decision_meta']['error'],
    'turn_text': rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']['turn_text'],
}
print(checks)
PY`

### Blocked-by conditions
- any path that resolves the issue by adding a wrapper/helper or widening `_reuse_active_handover(...)`
- any path that requires reopening non-frozen A/B/C as the main story
- any path that needs frozen edits outside `booking.py` to claim this family closed
- any rerun-only path without new frozen-family regression coverage

### Owner role for closure
- `Top Architect / Brain / Hands`
