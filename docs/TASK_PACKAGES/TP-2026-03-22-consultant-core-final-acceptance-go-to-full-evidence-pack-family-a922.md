# TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-ACCEPTANCE-GO-TO-FULL-EVIDENCE-PACK-FAMILY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-REENTRY-BUNDLE-A922`
- `DEPENDS_ON`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `UNLOCKS`: `retry_consultant_core_post_r20_acceptance_lock_with_truthful_pg_checklist`

## Название/цель
Материализовать truthful `go_to_full` evidence pack для post-`r20` acceptance lock: собрать свежий `L1` JUnit, подтвердить свежий green non-acceptance `L2`, добрать свежие green multi-seed summaries `7/19/42`, собрать canonical `pg_checklist`, затем один раз повторить guarded acceptance `lock`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/quality_chain_controller.sh`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r20/summary.json`
- `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: no runtime/core files are in scope; only docs/session/canon plus fresh evidence artifacts under `/tmp/booking_quality`.
- `Baseline commands`:
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `python3 - <<'PY'
import json, pathlib
summary = json.loads(pathlib.Path('/tmp/booking_quality/a922-check-booking-proof-r20/summary.json').read_text())
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'run_integrity_valid': summary.get('run_integrity_valid') or (summary.get('quality_status') or {}).get('run_integrity_valid'),
    'manual_audit_status': summary.get('manual_audit_status') or (summary.get('quality_status') or {}).get('manual_audit_status'),
    'quality_lane': summary.get('quality_lane') or summary.get('quality_lane_effective') or (summary.get('config') or {}).get('quality_lane') or (summary.get('quality_status') or {}).get('quality_lane_effective'),
})
PY`
  - `find /tmp/booking_quality -maxdepth 2 -type f -name 'pytest-junit.xml' -mmin -1440 -printf '%TY-%Tm-%TdT%TT %p\n' | sort`
  - `python3 - <<'PY'
from pathlib import Path
import json, time
now = time.time()
found = []
for path in Path('/tmp/booking_quality').rglob('summary.json'):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    cfg = data.get('config') or {}
    seed = cfg.get('seed', data.get('seed'))
    q = data.get('quality_status') or {}
    infra = q.get('infra_valid', data.get('infra_valid'))
    sem = q.get('semantic_valid', data.get('semantic_valid'))
    integ = q.get('run_integrity_valid', data.get('run_integrity_valid'))
    if seed in (7, 19, 42) and infra is True and sem is True and integ is True and now - path.stat().st_mtime < 24*3600:
        found.append((seed, str(path)))
print(found)
PY`
- `FACT findings`:
  - fresh dev-lane `L2` evidence already exists in `/tmp/booking_quality/a922-check-booking-proof-r20/summary.json`: `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`, `manual_audit_status=done`, `quality_lane=dev`.
  - a fresh `L1` JUnit already exists at `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`, but the post-`r20` block has not yet bound it to a new checklist mapping.
  - no fresh green summaries for required seeds `7`, `19`, and `42` were found in the current 24-hour window.
  - the previous acceptance lock did not fail on runtime or old latest-lock guard; it failed before execution because `/tmp/booking_quality/pg_checklist-a922-post-r20.json` did not exist.

## One web search (mandatory before implementation)
- **Query (exact):** `pytest junitxml official docs`
- **Date/time (local):** `2026-03-22T16:08:00+05:00`
- **Why this query is precise:** this block needs one truthful fresh `L1` JUnit artifact for the acceptance checklist and should rely on the official pytest mechanism, not ad-hoc report generation.
- **Sources opened (from this query):**
  - `pytest documentation` — `https://docs.pytest.org/en/stable/how-to/output.html`
- **Existing solutions found:** official pytest supports machine-readable JUnit output via `--junitxml=<path>`; this is the canonical artifact shape expected by downstream tooling.
- **Decision:** `reuse` — produce or refresh `L1` evidence with standard pytest JUnit output only; do not invent a custom XML generator.
- **Rejected options:**
  - hand-written or stale JUnit reuse without freshness validation: rejected because `quality_chain_controller.sh` fail-closes stale/missing evidence
  - bypassing multi-seed evidence: rejected because `go_to_full` now requires it by controller contract
- **Open questions:** none before the first evidence materialization step.

## Root cause (mandatory)
- **Symptom:** post-`r20` acceptance re-entry still cannot start because guarded acceptance `lock` fail-closes before execution.
- **Minimal reproduction:**
  - `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-post-r20 --pg-checklist /tmp/booking_quality/pg_checklist-a922-post-r20.json -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- **Evidence to capture:** `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`, fresh JUnit if re-materialized, fresh seed summaries if produced, fresh checklist JSON, and the retried acceptance lock result.
- **Five Whys (or equivalent):**
  1. Why did the fresh acceptance `lock` not start? Because chain-controller prepare failed.
  2. Why did chain-controller prepare fail? Because the required `pg_checklist` file was missing/unreadable.
  3. Why was the checklist missing? Because the post-`r20` state had not yet materialized a new `go_to_full` evidence pack.
  4. Why is the evidence pack incomplete? Because only fresh `L2` is already present; fresh bound `L1` and fresh green multi-seed summaries are still missing from the post-`r20` contract.
  5. Why is this the rightful next block? Because no honest runtime or oracle blocker survives on `r20`; the narrow blocker is now acceptance-preflight evidence assembly.
- **Root cause statement:** final acceptance is currently blocked by missing `go_to_full` evidence-pack materialization, not by runtime semantics: the post-`r20` state lacks a canonical checklist binding fresh `L1`, fresh green multi-seed summaries, and the already-green non-acceptance `L2`.
- **Fix mechanism:** produce/refresh the missing evidence artifacts, assemble the checklist JSON, then retry exactly one guarded acceptance `lock` and truthfully stop on the next blocker if any.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/booking_quality/a922-check-booking-proof-r20/summary.json`
  - `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`
  - `scripts/quality_chain_controller.sh`
  - `scripts/llm_quality_guarded.sh`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - existing green architecture/session guard stack
- **External reuse:** official pytest JUnit docs only.
- **Why not reinvent the wheel:** the repo already defines the checklist schema and acceptance chain; the missing work is evidence materialization, not tooling creation.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `30`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** this is an evidence-materialization block with expensive runs but no runtime code edits.

## Invariant
- do not reopen runtime/core/proof edits
- do not weaken acceptance or multi-seed gates
- do not fake checklist content or reuse stale evidence outside freshness window
- frozen files remain untouched

## Scope
- materialize or refresh the missing `go_to_full` evidence artifacts
- assemble one truthful post-`r20` checklist JSON
- retry exactly one guarded acceptance `lock`
- publish either the new acceptance artifact or the next exact blocker truth

## Out of scope
- `replay`, `canary`, `full` beyond the first retried `lock` if the lock fails
- any runtime/core/proof code change
- matrix/open-world closure before the acceptance `lock` starts canonically

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
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
1. Freeze the current blocker truth and publish this bounded evidence-pack TP.
2. Refresh `L1` JUnit evidence if needed with one targeted pytest JUnit run.
3. Start a fresh local runtime on `127.0.0.1:18186`.
4. Materialize fresh green dev-lane seed summaries for `7`, `19`, and `42`.
5. Assemble `/tmp/booking_quality/pg_checklist-a922-post-r20.json` from fresh `L1`, fresh seed evidence, and fresh `L2` `r20`.
6. Retry one guarded acceptance `lock`.
7. Publish the result and sync canon to the next truthful move.

## DoD
- one truthful post-`r20` evidence-pack TP/report exists
- `/tmp/booking_quality/pg_checklist-a922-post-r20.json` exists and passes schema/contract expectations
- either a new acceptance `lock` artifact exists or the next blocker is localized exactly
- canon/session docs and generated packet agree on the active block and next move

## Work mode (mandatory)
- `implementation`

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py -k 'allows_fresh_lock_after_audited_non_canonical_latest_run' --junitxml /tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`
- `bash -lc 'set -a && source /home/zhan/truffles-main/truffles-api/.env && set +a && python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --seed 7 --mode llm --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text ок --tool-confirm-text да --tool-cancel-text отмена --tool-calendar-text проверь запись --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed7 --run-id a922-go2f-seed7 --history-max 20 --fail-on-thresholds --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000'`
- same direct dev-lane command for seeds `19` and `42` with output dirs `/tmp/booking_quality/a922-go2f-seed19` and `/tmp/booking_quality/a922-go2f-seed42`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed7 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed42 --status done --strict-artifacts`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-post-r20 --pg-checklist /tmp/booking_quality/pg_checklist-a922-post-r20.json -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
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
- fresh TP/report and synced canon/session artifacts listed above
- `L1` JUnit:
  - `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`
- fresh green seed summaries if produced:
  - `/tmp/booking_quality/a922-go2f-seed7/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed42/summary.json`
- assembled checklist:
  - `/tmp/booking_quality/pg_checklist-a922-post-r20.json`
- retried acceptance lock if produced:
  - `/tmp/booking_quality/booking-lock-a922-post-r20/summary.json`
- if blocked: exact failing command, artifact path, and blocker reason/family

## Token / run budget (mandatory for expensive suites)
- **Max guarded lock runs:** `1`
- **Max direct seed runs:** `3`
- **Max JUnit refresh runs:** `1`
- **Cheap deterministic gates first:** inspect current evidence inventory before any fresh runs
- **Stop condition:** stop immediately if any seed run or the retried lock surfaces a blocker that would require runtime/core/proof edits or gate weakening
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** evidence-only execution against the current worktree runtime; no runtime/core rollout in this block
- **Go/no-go signals:** all checklist evidence is current and valid, and the retried acceptance `lock` either starts canonically or yields a narrower truthful gate reason
- **Rollback:** revert doc/canon/report changes only; do not keep any checklist or closure claim that lacks fresh evidence
- **Post-release monitoring window:** immediate artifact and guard verification only

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - block stays `BLOCKED` until canon, session log, and generated packet all point at the same active TP/report truth

## Rollback
- revert doc/canon/report changes and discard any non-truthful checklist; keep blocker artifacts intact.

## No-go
- do not bypass acceptance gates with `--allow-pending-previous` or forensic overrides
- do not fake checklist evidence or re-label stale artifacts as fresh
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not start matrix/open-world closure before the acceptance `lock` starts canonically

## Risks/Blockers
- one or more fresh seed runs may still be semantic-red or run-integrity-red
- the retried acceptance `lock` may surface a new acceptance-preflight blocker after the checklist exists
- current runtime environment may fail health or judge/secret readiness before seed evidence finishes

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: final acceptance, matrix, and open-world closure remain open until a canonical lock exists; duplicate top-level defs remain deferred
- `Why not in this block`: this block is only the checklist/evidence-pack family and one retried acceptance `lock`
- `Risk if deferred`: the program stays blocked on missing acceptance-preflight evidence and can drift back into narrative-only closure claims
- `Linked follow-up Task Package(s)`: one new blocker-family TP if the retried lock stops on a new narrower gate
- `Expiry/trigger to stop deferral`: stop deferral immediately after the retried lock result is known

## Next-block contract (mandatory)
- `Next block objective`: either continue with `replay/canary/full` if the retried lock is canonical, or publish one new exact blocker-family TP from the retried lock result
- `First deterministic check command`: `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `Blocked-by conditions`: seed evidence cannot be materialized canonically; checklist remains invalid; retried lock stops on a new blocker requiring runtime/core/proof edits
- `Owner role for closure`: `Brain | Top Architect`
