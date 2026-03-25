# TP-2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-package-a922

## Goal
Delete or truthfully localize the surviving `L2` transport / observability blocker family so one fresh non-acceptance `demo_salon` summary can satisfy the remaining `go_to_full` evidence contract without reopening old architectural packages.

## Canon refs
- `STATE.md` NOW: consultant core `acceptance_preflight_blocker` implementation GAP
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-blocker-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`
- `truffles-api/app/services/chatflow_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either materializes one truthful non-acceptance `L2` summary or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `pytest custom markers skip tests official docs`
- **Date/time (local):** `2026-03-18T21:40:42+05:00`
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/how-to/mark.html`
  - `https://docs.pytest.org/en/stable/how-to/skipping.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - pytest already supports narrow node selection, explicit markers, and `skip` / `skipif` for environment-bound rows instead of ad-hoc wrapper logic
  - environment-dependent suites can remain truthful by reusing explicit pytest selection and conditional skipping semantics rather than inventing a separate test harness
- **Decision:** `reuse`
  - reuse existing owner suites and explicit pytest selection/skip semantics for transport-specific regressions instead of building new runner scaffolding around the `L2` blocker
- **Rejected options:**
  - broad suite reruns without owner scoping: rejected because the blocker is already localized to transport / observability surfaces
  - bespoke wrapper scripts for environment gating: rejected because pytest already provides the needed bounded selection semantics

## Root cause (mandatory)
- **Symptom:** hardcode preflight is green, fresh `L1` evidence exists, and worktree runtime parity is restored, but truthful `go_to_full` still cannot close because the only fresh non-acceptance `L2` run remains non-canonical.
- **Minimal reproduction:**
  - start a worktree-owned runtime on `http://127.0.0.1:18184`
  - run `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18184 --client-slug demo_salon --scenarios-file /tmp/booking_quality/l2-acceptance-preflight-a922-r3/scenarios.json --count 10 --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --min-wait 0.2 --max-wait 0.4 --manager-mode simulate --pending-mode ack --tool-hooks auto --jid-mode unique --reset-before-dialog --allowlist-jids "$OUTBOUND_ALLOWLIST_JIDS" --allow-non-allowlist`
  - audit with `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r3 --status done --strict-artifacts`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-blocker-a922.md` proves the old hardcode-core blocker seam is already deleted and `L1` evidence is already fresh, so the surviving blocker is now only `L2`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json` proves the current `L2` row is invalid: `infra_valid=false`, `semantic_valid=false`, `tool_evidence_reasons=["confirm_hook_missing"]`, `run_integrity_reasons=["run_completion_gap"]`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/manual_audit.md` proves the run is non-canonical: `run_incomplete`, `dialogs_seen=2/10`, `judge_alignment=conflicted`, `winner=contract`
  - worktree runtime logs from the same run prove repeated `Outbound guard: TEST_MODE enabled, SKIP message to jid=...` on the unique dev JIDs
  - `ops/diagnose.py` proves the runner requires `--allow-non-allowlist` or `--skip-outbox` when `--jid-mode unique` is used with outbox enabled
  - `truffles-api/app/services/chatflow_service.py` proves runtime `TEST_MODE` still skips outbound sends for JIDs outside `OUTBOUND_ALLOWLIST_JIDS`
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` proves `confirm_hook_missing` is a strict infra blocker under the current tool-evidence contract
- **Five Whys:**
  1. Why is `go_to_full` still blocked after hardcode/L1 closure? Because no truthful fresh `L2` summary exists.
  2. Why does the current `L2` summary remain invalid? Because the run ends with `confirm_hook_missing` and `run_completion_gap`.
  3. Why do those failures appear in the worktree-parity run? Because unique dev JIDs under `TEST_MODE` still hit outbound skip behavior, so transport / tool-hook observability diverges from what the runner expects.
  4. Why does the runner enter that state at all? Because the current dev lane needs `jid-mode unique` isolation, but `allow-non-allowlist` only relaxes runner-side admission; it does not change runtime outbound-guard behavior for non-allowlist JIDs.
  5. Why is this the next truthful package? Because the old hardcode preflight seam is already dead, fresh `L1` exists, and the remaining blocker before returning to acceptance preflight is now only the `L2` transport / observability family.
- **Root cause statement:** the surviving blocker family is the mismatch between dev-lane unique-JID isolation and runtime `TEST_MODE` outbound behavior: the runner can admit non-allowlist unique JIDs, but the worktree runtime still skips outbound send / confirm observability for those JIDs, leaving `confirm_hook_missing` and `run_completion_gap` and preventing a truthful `L2` summary.
- **Fix mechanism:**
  - freeze the current `L2` blocker evidence from `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/*` and the owner surfaces in `ops/diagnose.py` plus `truffles-api/app/services/chatflow_service.py`
  - determine the rightful non-frozen owner that must align unique-JID dev runs with truthful transport / hook evidence, with an explicit stop if the only green path requires frozen `decision.py`
  - add the smallest focused regressions on JID-mode / allowlist / tool-evidence behavior
  - materialize one fresh non-acceptance `L2` summary with `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`

## Invariant
- do not reopen semantic / continuity / boundary partials unrelated to the `L2` blocker
- do not weaken `tool_evidence`, `run_integrity`, `semantic_valid`, `go_to_full`, or acceptance thresholds
- do not use `--skip-outbox` as the green path for truthful `L2` transport evidence
- do not touch frozen `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`; if the only truthful green path requires that, stop and publish `GAP`
- do not fake confirm hooks, transport evidence, or audit files
- do not rerun guarded acceptance `lock/replay/canary/full` in this package

## Scope
- publish one package-level implementation plan for the surfaced `acceptance_preflight_l2_transport_blocker` family
- lock the next implementation block to the surviving non-frozen owner surfaces around:
  - unique-JID dev run admission / JID selection
  - runtime `TEST_MODE` outbound guard behavior for those dev JIDs
  - strict tool-evidence / confirm-hook observability for non-acceptance `L2`
- allow one fresh non-acceptance `L2` run only after cheap deterministic checks and focused regressions

## Out of scope
- guarded acceptance `lock`, `replay`, `canary`, `full`
- `llm-quality-matrix` or `llm-quality-open-world-closure`
- reopening hardcode-core closure work
- broad runtime safety redesign
- frozen-file waivers
- gate weakening or stale-evidence reuse

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `ops/diagnose.py`
- `truffles-api/app/services/chatflow_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-blocker-a922.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/brief.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/manual_audit.md`
  - existing runner/transport owner surfaces in `ops/diagnose.py` and `truffles-api/app/services/chatflow_service.py`
  - existing focused suites in `truffles-api/tests/test_booking_quality_jid_mode.py`, `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`, and `truffles-api/tests/test_booking_quality_status_gate.py`
- **External reuse:**
  - official pytest marker/skip guidance from `docs.pytest.org`
- **Why this reuse mix is truthful:**
  - the blocker is already localized to transport / observability, so the correct path is to reuse the existing runner, transport, and owner test surfaces instead of inventing new abstractions

## Plan
1. Publish and register this `L2` transport-blocker package, then switch canon to it.
2. Freeze the current blocker evidence from `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/{summary.json,brief.md,manual_audit.md}` plus the worktree-runtime parity proof on `http://127.0.0.1:18184`.
3. Add or tighten the smallest regression rows that distinguish:
   - runner-side unique-JID / allow-non-allowlist admission
   - runtime `TEST_MODE` outbound guard behavior for unique dev JIDs
   - strict tool-evidence expectations for non-acceptance `L2`
4. Determine the rightful surviving owner surface:
   - if green `L2` can be restored through non-frozen runner / transport surfaces, fix only those
   - if the only green path requires frozen `decision.py`, stop and publish `GAP`
5. Materialize one fresh non-acceptance `L2` run on worktree runtime parity and audit it strictly.
6. Publish one bounded implementation report that either proves one truthful green `L2` summary or stops with exact narrower `reasons` / `failure_families`.

## DoD
- this TP locks one truthful implementation path for the surfaced `L2` transport / observability blocker family
- the next implementation block is bounded to non-frozen runner / transport owner surfaces only
- the TP names the exact blocker evidence, rightful owner surfaces, and one-run proof contract
- canon/session docs point at this package and the next move to implement it
- required architecture/session guards pass

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json').read_text())
print(summary['quality_status']['infra_valid'])
print(summary['quality_status']['semantic_valid'])
print(summary['quality_status']['tool_evidence_reasons'])
print(summary['quality_status']['run_integrity_reasons'])
PY`
- `python3 - <<'PY'
from pathlib import Path
text = Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r3/manual_audit.md').read_text()
for needle in ['run_incomplete', 'dialogs_seen: `2/10`', 'judge_alignment: `conflicted`']:
    print(needle, needle in text)
PY`
- `rg -n "confirm_hook_missing|allow-non-allowlist|skip-outbox|jid-mode unique|Outbound guard: TEST_MODE enabled, SKIP" ops/diagnose.py truffles-api/app/services/chatflow_service.py truffles-api/tests/test_booking_quality_jid_mode.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py truffles-api/tests/test_booking_quality_status_gate.py`
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
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- blocker evidence reused from:
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-blocker-a922.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/brief.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/manual_audit.md`
- one bounded implementation report for the next block
- one fresh non-acceptance `L2` summary if the implementation block reaches green transport evidence
- `STATE.md` entry naming either the deleted transport blocker seam or the exact narrower `GAP`

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- **Max full runs:** `0`
- **Max guarded acceptance runs:** `0`
- **Cheap deterministic gates first:** summary/manual-audit proof, owner-surface grep, focused regressions, runtime parity verification before any new `L2` run
- **Reuse policy:** reuse the current blocker artifacts; do not regenerate acceptance evidence in this package
- **Stop condition:** if green `L2` requires frozen-file edits, `--skip-outbox`, fake hooks, or gate weakening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded dev-lane unblock only; cheap gates and focused regressions before one fresh `L2` run
- **Go/no-go signals:**
  - one non-frozen owner surface is proven for the unique-JID / `TEST_MODE` mismatch
  - focused regressions are green
  - one fresh non-acceptance `L2` summary has `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`
  - no new blocker family appears that would force another architectural detour inside this block
- **Rollback:**
  - revert this block's code/doc changes
  - keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/*` untouched as blocker evidence
  - do not resume acceptance preflight until the rollbacked state is revalidated
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** only until the bounded `L2` blocker report is published; if the fresh `L2` run remains non-canonical, reopen as `GAP`

## Rollback
- Revert the docs/canon/code files touched by this block and rerun the required guards; do not remove or rewrite blocker evidence.

## No-go
- Do not rerun guarded acceptance `lock/replay/canary/full` in this package.
- Do not claim `go_to_full` closure from this package alone.
- Do not use `--skip-outbox` as the truthful green path.
- Do not fake confirm hooks, transport events, or audit artifacts.
- Do not touch frozen `decision.py`, `booking.py`, or `pending.py` in this package.

## Risks / blockers
- the only truthful green path may still terminate at frozen `decision.py` simulation behavior, forcing a `GAP`
- the runner-side and runtime-side allowlist assumptions may diverge in more than one place, revealing a smaller follow-up blocker family
- the fresh `L2` run may expose a new semantic family after transport evidence is restored

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- acceptance preflight overall remains incomplete until `go_to_full` is rebuilt from fresh `L1 + L2`
- final multi-pack acceptance re-entry remains open
- broader semantic / continuity / boundary residuals remain outside this package

### Why not in this block
- this block only isolates the surviving non-acceptance `L2` transport / observability blocker family
- guarded acceptance reruns still belong to the acceptance-preflight and multi-pack re-entry lanes

### Risk if deferred
- the program remains blocked before any truthful return to acceptance preflight
- teams can drift into non-canonical dev reruns instead of closing the real blocker
- `go_to_full` stays structurally incomplete even though hardcode preflight and `L1` are already green

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`

### Expiry/trigger to stop deferral
- stop deferral once one truthful fresh non-acceptance `L2` summary exists or a narrower truthful `GAP` proves the remaining blocker family

## Next-block contract (mandatory)
### Next block objective
- implement one bounded `acceptance_preflight_l2_transport_blocker` closure bundle so one truthful non-acceptance `L2` summary exists for `go_to_full`

### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json').read_text())
print(summary['quality_status']['tool_evidence_reasons'])
print(summary['quality_status']['run_integrity_reasons'])
PY && rg -n "confirm_hook_missing|allow-non-allowlist|skip-outbox|Outbound guard: TEST_MODE enabled, SKIP" ops/diagnose.py truffles-api/app/services/chatflow_service.py`

### Blocked-by conditions
- the only green path requires frozen `decision.py` edits
- the only green path requires `--skip-outbox` or any other transport-evidence weakening
- the fresh `L2` run still cannot achieve `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`

### Owner role for closure
- `Top Architect`
