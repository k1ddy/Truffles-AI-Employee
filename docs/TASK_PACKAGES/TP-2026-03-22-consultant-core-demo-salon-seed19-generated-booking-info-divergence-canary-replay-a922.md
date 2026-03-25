# TP-2026-03-22 — Consultant Core Demo Salon Seed19 Generated Booking Info Divergence Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `UNLOCKS`: `classify_consultant_core_demo_salon_seed19_generated_booking_info_divergence_replay_truth`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh post-fix seed-`19` generated replay on the same dev-lane quality surface after the bounded runtime repair. This block is truthful only if it starts a fresh local runtime from the current worktree, reproduces the exact seed-`19` command shape with a new run id/output dir, strict-audits the new artifact, and classifies the surviving path before any more acceptance-evidence work.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19/manual_audit.json`
- `/tmp/booking_quality/_scenario_governance_registry.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `TECH.md`

## FACT pre-check (before replay)
- `Impacted docs/artifacts`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
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
  - `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/a922-go2f-seed19/summary.json').read_text())
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'run_integrity_valid': summary.get('run_integrity_valid') or (summary.get('quality_status') or {}).get('run_integrity_valid'),
    'threshold_breaches': (summary.get('quality_status') or {}).get('threshold_breaches'),
})
PY`
  - `python3 scripts/quality_artifact_report.py --hours 24 --show-commands | rg 'a922-go2f-seed19' -A1 -B1`
  - `ss -ltnp | rg ':18186' || true`
- `FACT findings`:
  - `/tmp/booking_quality/a922-go2f-seed19` is the current truthful pre-fix artifact for this family: `infra_valid=true`, `semantic_valid=false`, `run_integrity_valid=true`, `threshold_breaches=['irrelevant_fact_rate']`, `manual_audit_status=done`.
  - no listener is currently present on `127.0.0.1:18186`, so truthful closure requires a fresh worktree runtime before any new evidence is collected.
  - the exact direct dev-lane command shape for seed `19` is already indexed in `scripts/quality_artifact_report.py --hours 24 --show-commands`; comparison stays truthful only if the new run keeps the same seed / scenario-coverage / thresholds and changes only `run_id`, `output_dir`, and the fresh runtime fingerprint.

## One web search (mandatory before implementation)
- `Reuse rule for this block`: reuse the exact Rasa continuity search already recorded in `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`; this replay block does not open a new query.
- **Query (exact):** `Rasa forms interruptions requested slot official docs`
- **Date/time (local):** `2026-03-22T18:10:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** official vendor documentation / primary source.
- **Reuse note:** no new query was opened in this closure-only block; it reuses the already-recorded implementation-family search above.

## Root cause (mandatory)
- `Symptom`: the repo still lacks fresh post-fix seed-`19` evidence; only the pre-fix generated run and deterministic fix evidence exist.
- `Minimal reproduction`:
  1. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md` and confirm the fix is landed with deterministic proof only
  2. inspect `/tmp/booking_quality/a922-go2f-seed19/summary.json` and `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl` and confirm the pre-fix runtime artifact is still semantic-red
  3. verify no fresh listener exists on `127.0.0.1:18186`
- `Evidence`:
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
  - `/tmp/booking_quality/a922-go2f-seed19/{summary.json,responses.jsonl,manual_audit.json}`
  - `scripts/quality_artifact_report.py --hours 24 --show-commands`
  - `ss -ltnp | rg ':18186'`
- `Five Whys`:
  1. Why is seed `19` not truthfully closed yet? Because there is no fresh replay artifact after the landed runtime fix.
  2. Why is there no fresh replay artifact? Because the active block stopped at implementation plus deterministic regressions.
  3. Why can deterministic regressions not close the family? Because the acceptance lane depends on the same generated seed surface, not only unit tests.
  4. Why must the same generated seed surface be reused? Because the blocker was discovered on a specific seed/configuration and acceptance truth depends on comparable evidence.
  5. Why is a fresh runtime mandatory? Because previous replay disputes already showed stale in-memory runtime can invalidate closure claims.
- `Root cause statement`: proof closure is pending because the post-fix seed-`19` replay has not yet been executed on a fresh local runtime using the same indexed dev-lane command shape.
- `Fix mechanism`: start the local worktree runtime fresh, rerun the exact seed-`19` command shape with a new run id/output dir, strict-audit the artifact, and classify only from that fresh evidence.

## Reuse-first plan (mandatory)
- `Internal reuse`:
  - exact seed-`19` command shape from `python3 scripts/quality_artifact_report.py --hours 24 --show-commands`
  - the landed runtime fix in `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/routers/webhook/info.py`
  - strict audit command `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
- `External reuse`:
  - none beyond the implementation-family search already recorded
- `Why not reinvent the wheel`:
  - this block is evidence-only; the repo already has the fixed runtime path, the seed configuration, and the audit tooling.

## Work mode (mandatory)
- `closure`

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: this is replay/closure by intent, but the worktree already carries the approved runtime diff; keeping `implementation` mode avoids false governance failures on the existing code delta while canon is synced to fresh replay truth.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not reopen the evidence-pack family before fresh seed-`19` truth is known

## Scope
- publish the bounded replay TP/report lane
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- revalidate the focused deterministic suites and runtime parity preflight
- execute one fresh direct dev-lane seed `19` run on the same command shape as the blocker artifact
- strict-audit the new run and classify the fresh output
- sync canon/session/packet to the replay outcome

## Out of scope
- new runtime implementation
- new oracle/judge work
- seed `42`
- checklist assembly or acceptance `lock` retry before replay truth is known

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
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
1. Publish this replay TP and prepare the matching report.
2. Start a fresh local runtime from the current worktree with env sourced from canon env files.
3. Revalidate the focused deterministic suites and runtime parity preflight.
4. Run one fresh seed-`19` direct dev-lane quality artifact as `/tmp/booking_quality/a922-go2f-seed19-r2`.
5. Complete strict artifact audit on the fresh run.
6. Read the fresh surviving path, write the replay report, and sync canon/session truth from the new artifact.

## DoD
- fresh run `/tmp/booking_quality/a922-go2f-seed19-r2` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- the replay reuses the indexed seed-`19` command shape from the blocker artifact with only the fresh run identity changed
- the report truthfully classifies whether the seed-`19` runtime family is repaired on the real generated surface and whether any downstream blocker survives independently
- mandatory packet / guard / architecture / session checks pass after canon sync
- next non-negotiable move is updated from fresh evidence rather than stale `/tmp/booking_quality/a922-go2f-seed19`

## Checks
- `pytest -q truffles-api/tests/test_master_info_flow.py -k "hours or promotions"`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"`
- `python3 - <<'PY'
import json, subprocess, urllib.request
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
with urllib.request.urlopen('http://127.0.0.1:18186/admin/version', timeout=10) as response:
    runtime = json.load(response).get('git_commit')
print({'head': head, 'runtime': runtime, 'match': head == runtime})
PY`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --seed 19 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r2 --run-id a922-go2f-seed19-r2 --history-max 20 --fail-on-thresholds --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r2 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r2/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r2/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r2/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r2/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- `Max direct seed runs`: `1`
- `Fail-fast / scenario lock`: exact seed `19` only; same count / thresholds / scenario coverage as the blocker artifact
- `Stop condition`: stop immediately if preflight is invalid, runtime parity fails, or a second expensive rerun would be needed to explain the same artifact
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- `Strategy`: evidence-only local replay on the fixed runtime; no runtime mutation in this block
- `Go/no-go signals`: focused deterministic suites stay green, runtime parity matches `HEAD`, replay artifacts are audit-complete, and governance checks stay green after sync
- `Rollback`: revert TP/report/canon/session updates, rebuild the packet, rerun the mandatory guards; leave the produced run dir only as forensic evidence
- `Post-release monitoring window`: next block must classify the fresh replay artifact before any seed `42`, checklist, or acceptance lock work resumes

## Rollback
- revert doc/canon/report changes for this replay block; keep the produced run dir only as evidence

## No-go
- do not change runtime/core code in this block
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not run seed `42`
- do not resume acceptance `go_to_full` checklist work before fresh seed `19` truth is classified

## Risks/Blockers
- the fresh replay may still be semantic-red and surface a narrower downstream blocker
- runtime parity may fail if the local server is not started from this worktree
- seed `19` may carry advisory judge noise even if the runtime family closes

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: duplicate top-level defs in `truffles-api/app/services/reasoning_core.py`, seed `42`, PG checklist assembly, and acceptance `lock` retry remain deferred
- `Why not in this block`: this block is closure-only for the first surfaced generated seed family
- `Risk if deferred`: acceptance re-entry stays blocked on stale seed-`19` truth
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one new bounded family TP if replay stays semantic-red
- `Expiry/trigger to stop deferral`: stop deferral immediately after the fresh seed-`19` replay is classified

## Next-block contract (mandatory)
- `Next block objective`: classify the fresh seed-`19` replay truth and either reopen a narrower runtime family or return to the evidence-pack family if seed `19` goes green
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"`
- `Blocked-by conditions`: fresh runtime parity cannot be established; seed run is infra-invalid; replay surfaces a blocker that splits into a new family before canon sync
- `Owner role for closure`: `Brain | Top Architect`
