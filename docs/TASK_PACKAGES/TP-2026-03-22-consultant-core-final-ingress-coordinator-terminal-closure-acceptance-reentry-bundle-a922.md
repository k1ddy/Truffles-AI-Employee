# TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-REENTRY-BUNDLE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-CANARY-REPLAY-A922`
- `DEPENDS_ON`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `UNLOCKS`: `publish_consultant_core_final_ingress_coordinator_terminal_closure_acceptance_reentry_result_or_exact_gap`

## Название/цель
Выполнить truthful post-`r20` acceptance re-entry bundle: использовать свежий green demo-salon replay только как proof prerequisite, заново собрать canonical acceptance evidence (`lock -> replay -> canary -> full`), затем пройти multi-pack matrix и machine-readable open-world closure без новых runtime-патчей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/_generated/AGENT_PACKET.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: no runtime/core files are in scope; the block may touch docs/session/canon files only unless it stops with a truthful GAP.
- `Baseline commands`:
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `python3 - <<'PY'
import json, pathlib
summary = json.loads(pathlib.Path('/tmp/booking_quality/a922-check-booking-proof-r20/summary.json').read_text())
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'client_slug': summary.get('client_slug'),
})
PY`
  - `scripts/llm_quality_guarded.sh --help`
  - `python3 ops/diagnose.py llm-quality-matrix --help`
  - `python3 ops/diagnose.py llm-quality-open-world-closure --help`
- `FACT findings`:
  - fresh guarded replay `/tmp/booking_quality/a922-check-booking-proof-r20` is strict-audited green (`infra_valid=true`, `semantic_valid=true`, `turns_strict_failed=0`), so no honest demo-salon runtime or oracle blocker survives inside the bounded canary family.
  - the last-72h quality inventory now has one canonical replay (`a922-check-booking-proof-r20`), but still no canonical acceptance `lock`, `canary`, or `full` artifact and no `llm-quality-matrix` / `llm-quality-open-world-closure` artifact.
  - `r20` is a single-scenario replay on the locked sanitized canary surface; it is not itself final acceptance evidence for `P6` and cannot replace the required acceptance-lane chain or multi-pack closure artifact.
  - the stale `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md` is no longer truthful because its `r79` promo-interrupt runtime family was closed before `r20`.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI evaluation best practices official docs`
- **Date/time (local):** `2026-03-22T17:08:00+05:00`
- **Why this query is precise:** this block is an acceptance/evidence bundle, not a runtime bugfix. The query checks a primary-source reference for eval design discipline before expensive multi-step evidence runs.
- **Sources opened (from this query):**
  - `OpenAI API docs — Evaluation best practices` — `https://platform.openai.com/docs/guides/evaluation-best-practices`
- **Existing solutions found:** primary-source guidance says eval-driven development should combine scoped tests, task-specific datasets, automated scoring where possible, and calibrated human judgment rather than relying on one metric or one happy-path run.
- **Decision:** `reuse` — keep the existing repo owners (`scripts/llm_quality_guarded.sh`, `scripts/booking_dialog_scenarios.py`, `ops/diagnose.py llm-quality-matrix`, `ops/diagnose.py llm-quality-open-world-closure`) and execute the required evidence chain instead of inventing a new acceptance harness.
- **Rejected options:**
  - reusing `r20` as final closure proof: rejected because it is a dev-lane replay on one locked scenario, not the full acceptance contract.
  - reviving the stale `r79` promo-interrupt bundle: rejected because that runtime family is already closed and would reopen non-truthful work.
  - narrative-only closure summary: rejected because `P6` requires machine-readable closure evidence.
- **Open questions:** none before the first guarded acceptance lock.

## Root cause (mandatory)
- **Symptom:** demo-salon canary runtime/proof families are closed on fresh `r20`, but final consultant-core acceptance is still open.
- **Minimal reproduction:**
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `python3 - <<'PY'
import json, pathlib
summary = json.loads(pathlib.Path('/tmp/booking_quality/a922-check-booking-proof-r20/summary.json').read_text())
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'note': 'single-scenario replay; not acceptance lock/canary/full or multi-pack closure evidence',
})
PY`
- **Evidence to capture:** `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`, `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`, the fresh acceptance artifacts from this block if produced, or the exact blocking reason/family if the chain stops.
- **Five Whys (or equivalent):**
  1. Why is final program acceptance still open after `r20`? Because `r20` only proves the bounded demo-salon canary family; it is not the full acceptance contract.
  2. Why is `r20` insufficient? Because final closure still requires canonical acceptance-lane evidence and multi-pack/open-world proof.
  3. Why can the old 2026-03-21 acceptance bundle not be executed as-is? Because it assumes the still-open `r79` promo-interrupt runtime family, which is no longer true.
  4. Why is this not another runtime blocker? Because no honest runtime or proof blocker survives on the fresh canary; the remaining deficit is acceptance/open-world evidence.
  5. Why is the next move an evidence bundle instead of another doc-only block? Because the repo already has the owners and commands; the next truthful progress is to execute them or stop with an exact GAP.
- **Root cause statement:** the active blocker is now an open-world / acceptance-evidence gap: final consultant-core closure lacks the required post-`r20` canonical acceptance chain and machine-readable multi-pack closure artifact, while the older acceptance bundle docs are stale.
- **Fix mechanism:** publish one fresh acceptance re-entry implementation TP, execute the existing evidence owners in order, and either produce the required artifacts or stop with an exact failure family / gate reason without patching runtime.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `scripts/llm_quality_guarded.sh`
  - `scripts/booking_dialog_scenarios.py`
  - `scripts/quality_artifact_report.py`
  - `ops/diagnose.py llm-quality-matrix`
  - `ops/diagnose.py llm-quality-open-world-closure`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- **External reuse:** official OpenAI evaluation best practices only.
- **Why not reinvent the wheel:** the repo already owns the acceptance lane and closure validator; this block should execute or truthfully fail that chain, not add wrappers.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `30`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** the block is implementation in the evidence lane only; it may run expensive commands and update canon/reporting, but it must not introduce runtime/core patches.

## Invariant
- do not reopen runtime/core/proof ownership patches inside this block
- do not weaken acceptance gates, matrix gates, or open-world closure gates
- do not count `r20` replay alone as final closure
- keep actual target mapping fixed to `demo_salon/main`, `clinic_pack/main`, `generic/main`
- frozen files remain untouched

## Scope
- publish one fresh post-`r20` acceptance re-entry implementation TP
- run the required acceptance-evidence owners in order
- produce either fresh canonical acceptance/matrix/closure artifacts or an exact truthful GAP
- sync canon/session/reporting to the resulting truth

## Out of scope
- any runtime/core/proof code change
- any frozen-router edit
- any new acceptance harness or wrapper
- any gate weakening or manual artifact cleanup to force progress

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md`
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
1. Freeze post-`r20` acceptance facts and publish this fresh implementation TP.
2. Start a fresh local runtime on the active worktree and verify health/version.
3. Run canonical acceptance `lock` on `demo_salon`; if it stops non-canonically, stop the block and publish the exact failure family/gate reason.
4. Only if lock is valid, continue with `replay`, `canary`, and `full`.
5. Generate deterministic `ru`, `kk`, `mixed`, and `mixed_translit` scenario bundles.
6. Run one bounded `llm-quality-matrix` across `demo_salon/main`, `clinic_pack/main`, and `generic/main`.
7. Run `llm-quality-open-world-closure` and publish either `valid=true` closure evidence or an exact GAP.

## DoD
- one fresh post-`r20` acceptance re-entry TP/report exists
- this block either produces machine-readable final acceptance evidence or stops with an exact blocker family/gate reason
- canon/session docs point at the truthful active block and next move
- required packet/architecture/session guards pass

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-post-r20 --pg-checklist /tmp/booking_quality/pg_checklist-a922-post-r20.json -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-a922-post-r20 -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --scenarios-file /tmp/booking_quality/booking-lock-a922-post-r20/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-a922-post-r20/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
- `scripts/llm_quality_guarded.sh --mode canary --run-id booking-canary-a922-post-r20 -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-a922-post-r20/summary.json`
- `scripts/llm_quality_guarded.sh --mode full --run-id booking-full-a922-post-r20 -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-a922-post-r20/summary.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-ru-a922-post-r20 && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 42 --coverage booking,info,interrupt,handoff --language-profile ru --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-ru-a922-post-r20/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-kk-a922-post-r20 && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 1337 --coverage booking,info,interrupt,handoff --language-profile kk --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-kk-a922-post-r20/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-mixed-a922-post-r20 && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 2026 --coverage booking,info,interrupt,handoff --language-profile mixed --surface-noise-profile typo --semantic-variation-profile synonym --slot-format-profile variant --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-mixed-a922-post-r20/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-translit-a922-post-r20 && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 9001 --coverage booking,info,interrupt,handoff --language-profile mixed_translit --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-translit-a922-post-r20/scenarios.json`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality-matrix --client-slugs demo_salon,clinic_pack,generic --branch-slugs main,main,main --run-id-prefix multi-pack-post-r20-a922 --cross-domain-contract block --scenario-context-contract block -- --base-url http://127.0.0.1:18186 --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane dev --run-economy-gate block --fail-on-thresholds`
- `python3 ops/diagnose.py llm-quality-open-world-closure --matrix-summary /tmp/booking_quality/multi-pack-post-r20-a922/matrix_summary.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-ru-a922-post-r20/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-kk-a922-post-r20/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-mixed-a922-post-r20/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-translit-a922-post-r20/scenarios.json --output /tmp/booking_quality/multi-pack-closure-a922-post-r20.json --pretty`
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
- fresh acceptance artifacts if produced:
  - `/tmp/booking_quality/booking-lock-a922-post-r20/summary.json`
  - `/tmp/booking_quality/booking-replay-a922-post-r20/summary.json`
  - `/tmp/booking_quality/booking-canary-a922-post-r20/summary.json`
  - `/tmp/booking_quality/booking-full-a922-post-r20/summary.json`
- deterministic scenario bundle if produced:
  - `/tmp/booking_quality/multi-pack-seed-ru-a922-post-r20/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-kk-a922-post-r20/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-mixed-a922-post-r20/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-translit-a922-post-r20/scenarios.json`
- multi-pack closure artifacts if produced:
  - `/tmp/booking_quality/multi-pack-post-r20-a922/matrix_summary.json`
  - `/tmp/booking_quality/multi-pack-closure-a922-post-r20.json`
- if blocked: exact failing command, run dir, and blocking reason/failure family

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Max matrix runs:** `1`
- **Max deterministic seed bundles:** `1`
- **Cheap deterministic gates first:** inventory/help/health checks and PG-checklist readiness inspection must happen before any expensive acceptance or matrix run
- **Stop condition:** the block stops immediately on the first canonical acceptance-preflight gate reason, invalid artifact, or blocker family that would require runtime/core/proof edits
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** evidence-only execution against the current worktree runtime; no runtime/core rollout is allowed in this block
- **Go/no-go signals:** the first acceptance command must produce a canonical artifact or an exact gate reason; any need for runtime/core/proof edits is immediate `no-go`
- **Rollback:** revert doc/canon/report changes only and discard any closure claim that lacks machine-readable evidence
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
- revert the fresh TP/report/canon sync files only; do not keep any closure claim without machine-readable evidence.

## No-go
- do not patch runtime/core/proof owners inside this bundle
- do not use `--allow-pending-previous` or forensic overrides to bypass acceptance gates unless a new decision block explicitly authorizes it
- do not reuse `r20` as substitute for acceptance `lock/canary/full` evidence
- do not claim final closure without valid matrix and `llm-quality-open-world-closure` artifacts
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`

## Risks/Blockers
- fresh acceptance `lock` may still block on prior non-canonical lock state or a newly surfaced family
- multi-pack matrix may expose pack/readiness or scenario-context failures outside the demo-salon canary
- open-world closure may fail even after green matrix if deterministic profile coverage is incomplete

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred; advisory judge conflicts from `r20` remain outside final closure until matrix/open-world evidence is complete
- `Why not in this block`: this block is evidence-only and must not reopen runtime-core or proof-path ownership
- `Risk if deferred`: the program stays open on narrative truth only and the team can drift back into beauty-only claims or stale acceptance docs
- `Linked follow-up Task Package(s)`: one fresh blocker family TP if the acceptance bundle stops before closure
- `Expiry/trigger to stop deferral`: stop deferral immediately if the first guarded acceptance command blocks or if any matrix/closure artifact returns invalid

## Next-block contract (mandatory)
- `Next block objective`: if this bundle stops before machine-readable closure, publish one exact blocker-family or gate-decision TP from the first failing acceptance/matrix/closure step
- `First deterministic check command`: `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `Blocked-by conditions`: acceptance lock cannot start canonically; any acceptance/matrix/closure artifact is invalid or missing; truthful completion would require runtime/core/proof code changes
- `Owner role for closure`: `Brain | Top Architect`
