# TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922

## Goal
Delete or truthfully localize the surfaced acceptance-preflight blocker family so the final `demo_salon` guarded acceptance lane can start from a green preflight state instead of fail-closing on missing `go_to_full` evidence and current-worktree `hardcode_core_gate` violations.

## Canon refs
- `STATE.md` NOW: consultant core `demo_salon_noncanonical_lock_failure_family` implementation GAP
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/quality_chain_controller.sh`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `truffles-api/tests/test_booking_quality_info_sections.py`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either proves one green acceptance preflight path into a fresh guarded `demo_salon` lock or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `pytest --junitxml official docs`
- **Date/time (local):** `2026-03-18T20:42:06+05:00`
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/_modules/_pytest/junitxml.html`
  - `https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - `pytest --junitxml=/tmp/booking_quality/l1-acceptance-preflight-a922/pytest-junit.xml` is the canonical way to materialize a machine-readable JUnit report for downstream tooling
  - `tee-sys` capture remains compatible with plugins such as `junitxml`, so targeted L1 evidence can stay observable while still emitting the XML artifact
- **Decision:** `reuse`
  - reuse existing pytest owner suites with explicit `--junitxml` output for the L1 evidence pack instead of inventing a bespoke report generator or hand-written XML
- **Rejected options:**
  - hand-authoring fake JUnit XML or backfilling stale files: rejected because the chain controller validates actual report paths and freshness
  - bypassing `go_to_full` with partial checklist content: rejected because the guard is intentionally fail-closed and must stay machine-verifiable

## Root cause (mandatory)
- **Symptom:** the old fresh-lock admission seam is gone, but the next guarded `demo_salon` lock still cannot start truthfully because chain-controller prepare fail-closes on `go_to_full_l1_evidence_missing`, while static acceptance preflight is simultaneously red with `hardcode_core_gate:core_phrase_branching_detected`.
- **Minimal reproduction:**
  - `python3 ops/diagnose.py llm-quality-gates --run-economy-gate block --quality-constant-gate block --quality-lane acceptance --mode llm --count 10 --include-media --scenario-coverage booking,info,interrupt,handoff --judge-mode all --fail-on-thresholds --output /tmp/a922-unblock-gates.json && python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/a922-unblock-gates.json').read_text())
print(payload['quality_status'])
print((payload['gates'] or {}).get('hardcode_core_gate'))
PY && BASE_URL=http://127.0.0.1:8000 OPENAI_API_KEY="$OPENAI_API_KEY" scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-unblock --pg-checklist /tmp/booking_quality/pg_checklist-a922-unblock.json -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-a922.md` proves the old wrapper blocker seam is already deleted, so the surviving stop-the-line is now preflight-only
  - `/tmp/a922-unblock-gates.json` proves current-worktree acceptance preflight is invalid: `blocking_reasons=["hardcode_core_gate:core_phrase_branching_detected"]`
  - `/tmp/a922-unblock-gates.json` lists current worktree violations in frozen `truffles-api/app/routers/webhook/decision.py` plus live `truffles-api/app/services/info_signal_service.py`
  - `/tmp/booking_quality/pg_checklist-a922-unblock.json` proves the attempted checklist is structurally incomplete for `go_to_full`: it has `PG0..PG6`, `root_cause_statement`, and `defect_mapping`, but no `l1_evidence`, no `l2_evidence`, and no `evidence_freshness_hours`
  - `scripts/quality_chain_controller.sh` proves `l1_evidence` / `l2_evidence` are mandatory and fail-closed validated before the guarded `lock` can proceed
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` proves the same contract at the runbook level: current `L1` JUnit evidence, current `L2` non-acceptance summary, and freshness-bound checklist content are required before the acceptance envelope may start
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands` currently returns only the header row, so there is no fresh audited guarded baseline to reuse as truthful preflight evidence
  - existing JUnit artifacts under `/tmp/booking_quality/*/pytest-junit.xml` are stale and therefore cannot satisfy the default `24h` freshness gate
- **Five Whys:**
  1. Why does the fresh guarded `demo_salon` lock still not start? Because chain-controller prepare now checks `go_to_full` evidence instead of dying on the old wrapper seam.
  2. Why does chain-controller prepare fail? Because the current checklist lacks machine-readable `l1_evidence` and `l2_evidence`, so the guard fail-closes with `go_to_full_l1_evidence_missing` before the lock can begin.
  3. Why can we not just point the checklist at an older artifact? Because the runbook and controller both require current freshness, and `quality_artifact_report --hours 72` shows no recent audited baseline to reuse.
  4. Why is preflight still red even before expensive acceptance? Because current-worktree `hardcode_core_gate` detects phrase-branching violations in the live diff, including `info_signal_service.py` and one frozen `decision.py` line.
  5. Why is this the truthful next package? Because the program is no longer blocked by the old lock-admission seam; it is blocked by acceptance-preflight prerequisites, and those must be isolated before rerunning the final acceptance bundle.
- **Root cause statement:** the surviving blocker family is now acceptance-preflight only: the repo has no current machine-readable `go_to_full` evidence pack for a truthful guarded `lock`, and the current worktree still fails `hardcode_core_gate`, so the acceptance lane cannot start even though the prior wrapper blocker seam has already been removed.
- **Fix mechanism:**
  - freeze and reproduce the current preflight failures from `llm-quality-gates`, the attempted PG checklist, and the guarded-lock prepare step
  - determine the rightful owner surfaces for the live `hardcode_core_gate` violations, with an explicit stop if the only path to green requires forbidden frozen-file edits
  - materialize one fresh L1 JUnit evidence pack and one fresh non-acceptance L2 summary using existing owner suites / commands only
  - assemble a truthful `go_to_full` checklist from that evidence, rerun cheap preflight gates, and only then attempt one guarded `demo_salon` `lock`

## Invariant
- do not reopen old architecture packages unrelated to acceptance preflight
- do not weaken `go_to_full`, `hardcode_core_gate`, `semantic_valid`, `run_integrity_valid`, thresholds, or failure-family gates
- do not patch runtime/core/proof ownership “along the way” unless that surface is the proven rightful owner of a surfaced preflight blocker
- do not edit frozen `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`; if the only green path requires that, stop and publish `GAP`
- do not reuse stale JUnit / summary artifacts to fake current evidence
- do not rerun the full multi-pack acceptance bundle in this package

## Scope
- publish one package-level implementation plan for the surfaced `acceptance_preflight_blocker` family
- lock the next implementation block to the two machine-readable blockers already exposed:
  - current-worktree `hardcode_core_gate`
  - missing/failing `go_to_full` evidence materialization for a fresh guarded `lock`
- require cheap deterministic gates and evidence materialization before any new guarded acceptance run
- allow one fresh guarded `demo_salon` `lock` only after preflight goes green or truthfully narrows to a new blocker family

## Out of scope
- `replay`, `canary`, `full`, `llm-quality-matrix`, or `llm-quality-open-world-closure`
- reopening runtime-target materialization or old authority-family packages
- beauty-only closure claims
- frozen-file waivers
- acceptance-gate weakening or stale-evidence reuse

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/quality_chain_controller.sh`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `truffles-api/tests/test_booking_quality_info_sections.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/a922-unblock-gates.json` for the exact current-worktree acceptance gate failure
  - `/tmp/booking_quality/pg_checklist-a922-unblock.json` for the failed preflight checklist shape
  - `scripts/quality_chain_controller.sh` as the canonical `go_to_full` gate owner
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` as the canonical acceptance runbook contract
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands` as the current evidence inventory surface
  - existing owner tests in `truffles-api/tests/test_booking_quality_status_gate.py`, `truffles-api/tests/test_booking_quality_guarded_wrapper.py`, `truffles-api/tests/test_booking_quality_info_sections.py`, and `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official `pytest` documentation for `--junitxml` and capture compatibility
- **Why this reuse mix is truthful:**
  - the blocker is about missing/invalid evidence and preflight gating, so the correct path is to reuse the existing chain controller, runbook, and test-owner surfaces rather than invent new readiness wrappers

## Plan
1. Publish and register this acceptance-preflight blocker package, then switch canon to it.
2. Freeze the surfaced blocker evidence from `/tmp/a922-unblock-gates.json`, `/tmp/booking_quality/pg_checklist-a922-unblock.json`, `scripts/quality_chain_controller.sh`, and the runbook.
3. Add or tighten the smallest regression rows that distinguish:
   - live `hardcode_core_gate` ownership for the current-worktree diff
   - `go_to_full` checklist materialization / freshness requirements
4. Determine the rightful surviving owner surfaces:
   - if `hardcode_core_gate` can go green via non-frozen surfaces, fix only those
   - if frozen `decision.py` is the only path, stop and publish `GAP`
5. Materialize one fresh L1 JUnit evidence pack from the exact target pytest suite(s) referenced in the checklist mapping.
6. Materialize one fresh `dev/forensic` L2 summary with `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`, and non-acceptance lane.
7. Assemble a truthful `go_to_full` checklist from that fresh evidence, rerun cheap preflight gates, and only then attempt one guarded `demo_salon` `lock`.
8. Publish one bounded implementation report that either proves green preflight plus fresh guarded lock start, or stops with exact narrower `reasons` / `failure_families`.

## DoD
- this TP locks one truthful implementation path for the surfaced acceptance-preflight blocker family
- the next implementation block is bounded to preflight blockers and does not reopen old architecture packages
- the TP names the exact blocker evidence, rightful owner surfaces, and the one-lock proof contract
- canon/session docs point at this package and the next move to implement it
- required architecture/session guards pass

## Checks
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `python3 - <<'PY'
import json
from pathlib import Path
checklist = json.loads(Path('/tmp/booking_quality/pg_checklist-a922-unblock.json').read_text())
print(sorted((checklist.get('go_to_full') or {}).keys()))
PY`
- `python3 ops/diagnose.py llm-quality-gates --run-economy-gate block --quality-constant-gate block --quality-lane acceptance --mode llm --count 10 --include-media --scenario-coverage booking,info,interrupt,handoff --judge-mode all --fail-on-thresholds --output /tmp/a922-unblock-gates.json`
- `rg -n "go_to_full_l1_evidence_missing|go_to_full_l2_evidence_missing|go_to_full_gate_missing|go_to_full_gate_failed|go_to_full_l1_target_not_passed|core_phrase_branching_detected" scripts/quality_chain_controller.sh docs/runbooks/BOOKING_CONFIRM_VERIFY.md ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`
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
- preflight blocker evidence reused from:
  - `/tmp/a922-unblock-gates.json`
  - `/tmp/booking_quality/pg_checklist-a922-unblock.json`
  - `scripts/quality_chain_controller.sh`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- one bounded implementation report for the next block
- one fresh L1 JUnit artifact and one fresh non-acceptance L2 summary if the implementation block reaches green preflight
- `STATE.md` entry naming either the deleted preflight blocker seam or the exact narrower `GAP`

## Token / run budget (mandatory for expensive suites)
- **Max guarded lock runs:** `1`
- **Max full runs:** `0`
- **Max replay/canary runs:** `0`
- **Max matrix / closure runs:** `0`
- **Cheap deterministic gates first:** artifact inventory, checklist-shape proof, hardcode-core gate proof, and targeted regressions before any guarded `lock`
- **Reuse policy:** reuse the surfaced blocker artifacts; do not regenerate multi-pack evidence in this package
- **Stop condition:** if green preflight requires frozen-file edits, stale evidence reuse, or gate weakening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded preflight unblock only; cheap gates and fresh evidence materialization before any guarded acceptance start
- **Go/no-go signals:**
  - `hardcode_core_gate` is green without forbidden frozen-file edits
  - one current L1 JUnit artifact and one current non-acceptance L2 summary exist and pass controller validation
  - one guarded `demo_salon` `lock` starts without preflight fail-close
  - no new failure family appears that would force another architecture detour inside this block
- **Rollback:**
  - revert this block's code/doc changes
  - keep `/tmp/a922-unblock-gates.json` and `/tmp/booking_quality/pg_checklist-a922-unblock.json` untouched as blocker evidence
  - do not resume the final acceptance re-entry bundle until the rollbacked state is revalidated
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** only until the bounded preflight report is published; if guarded `lock` still fail-closes before execution, reopen as `GAP`

## Rollback
- Revert the docs/canon/code files touched by this block and rerun the required guards; do not remove or rewrite blocker evidence.

## No-go
- Do not rerun the full multi-pack acceptance bundle in this package.
- Do not fake `go_to_full` readiness with partial, stale, or hand-authored evidence.
- Do not weaken `hardcode_core_gate` or mark it non-blocking.
- Do not touch frozen `decision.py`, `booking.py`, or `pending.py` in this package.
- Do not claim final consultant closure or multi-pack acceptance closure from this block alone.

## Risks / blockers
- the current `hardcode_core_gate` may prove that one remaining frozen `decision.py` diff line is still a live blocker, forcing a truthful `GAP`
- the rightful L1/L2 evidence pack may reveal another current blocker family before the guarded `lock` can start
- evidence freshness windows may invalidate otherwise-green historical artifacts, requiring deliberate materialization rather than reuse

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- final multi-pack acceptance re-entry remains open
- broader semantic/continuity/boundary legacy residuals still exist outside the acceptance-preflight family
- the final machine-readable closure artifact still does not exist

### Why not in this block
- this block only isolates and unblocks the acceptance-preflight prerequisites
- the full `lock/replay/canary/full` chain and multi-pack closure still belong to the already-authored acceptance re-entry TP

### Risk if deferred
- the program remains blocked before any truthful final acceptance rerun can even begin
- teams can drift into stale-evidence reuse or checklist bypasses instead of proving current readiness
- the existing acceptance re-entry TP remains unexecutable despite the prior wrapper blocker seam already being removed

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`

### Expiry/trigger to stop deferral
- stop deferral once a fresh guarded `demo_salon` `lock` starts from green preflight or a narrower truthful `GAP` proves the remaining blocker family

## Next-block contract (mandatory)
### Next block objective
- implement one bounded `acceptance_preflight_blocker` closure bundle so green preflight can admit one fresh guarded `demo_salon` `lock`

### First deterministic check command
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands && python3 - <<'PY'
import json
from pathlib import Path
checklist = json.loads(Path('/tmp/booking_quality/pg_checklist-a922-unblock.json').read_text())
print(sorted((checklist.get('go_to_full') or {}).keys()))
payload = json.loads(Path('/tmp/a922-unblock-gates.json').read_text())
print((payload.get('quality_status') or {}).get('blocking_reasons'))
print(((payload.get('gates') or {}).get('hardcode_core_gate') or {}).get('violations'))
PY`

### Blocked-by conditions
- `hardcode_core_gate` can only be cleared via frozen-file edits
- no current L1 JUnit evidence or no current valid L2 summary can be materialized without stale-evidence reuse or gate weakening
- a fresh guarded `demo_salon` `lock` still fail-closes on a different preflight blocker family after these prerequisites go green

### Owner role for closure
- `Top Architect / Brain / Hands`
