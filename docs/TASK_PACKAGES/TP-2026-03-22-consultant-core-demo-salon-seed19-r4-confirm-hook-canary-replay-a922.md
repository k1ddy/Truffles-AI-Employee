# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R4 Confirm Hook Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONTRACT-ALIGNED-CONFIRM-HOOK-PROOF-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `UNLOCKS`: `classify_consultant_core_demo_salon_seed19_r5_replay_truth`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh exact replay on the original seed-`19` blocker scenarios after the bounded proof-only confirm-hook parity fix. This block is truthful only if it starts a fresh local runtime from the current worktree, reuses the exact `r4` command shape with a new run id/output dir, strict-audits the artifact, and classifies the downstream path only after infra is restored.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
- `/tmp/booking_quality/_scenario_governance_registry.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `TECH.md`

## FACT pre-check (before replay)
- `Impacted docs/artifacts`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
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
- `Baseline commands`:
  - `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"`
  - `python3 scripts/quality_artifact_report.py --hours 48 --show-commands | sed -n '/a922-go2f-seed19-r4/,+6p'`
  - `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r4/summary.json').read_text())
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'stop_reason': summary.get('stop_reason'),
    'infra_reasons': (summary.get('quality_status') or {}).get('infra_reasons'),
})
PY`
  - `ss -ltnp | rg ':18186' || true`
- `FACT findings`:
  - the bounded proof-only repair is landed locally in `ops/diagnose.py`, and targeted deterministic proof is already green.
  - `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` remains the last exact replay artifact for this family; it is infra-invalid because `tool_evidence:confirm_hook_missing` stopped the run before downstream runtime reclassification.
  - no listener is currently active on `127.0.0.1:18186`, so truthful replay requires a fresh worktree runtime start before new evidence is collected.
  - the exact command shape for `r4` is already indexed; truthful comparison requires changing only `run_id`, `output_dir`, and runtime fingerprint.

## One web search (mandatory before implementation)
- `Reuse rule for this block`: replay/closure only; no new query is opened. Reuse the implementation-family search already recorded in `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`.
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm evaluator pass fail rubric deterministic contract alignment`
- **Date/time (local):** `2026-03-22T19:17:00+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Reuse note:** no new query was opened in this closure-only block; it reuses the already-recorded implementation-family search above.

## Root cause (mandatory)
- `Symptom`: the proof-only parity repair is landed, but there is still no fresh exact replay artifact proving whether infra is restored and whether any downstream runtime row survives.
- `Minimal reproduction`:
  1. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md` and confirm the parity fix is landed with deterministic proof only
  2. inspect `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` and confirm the last exact replay remains infra-invalid on `confirm_hook_missing`
  3. verify no listener exists on `127.0.0.1:18186`
- `Evidence`:
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/{summary.json,responses.jsonl,manual_audit.json}`
  - `python3 scripts/quality_artifact_report.py --hours 48 --show-commands`
  - `ss -ltnp | rg ':18186'`
- `Five Whys`:
  1. Why is the family not truthfully closed yet? Because there is no fresh exact replay artifact after the proof-only parity repair.
  2. Why is there no fresh exact replay artifact? Because the previous block stopped at implementation plus deterministic proof.
  3. Why can deterministic proof not close the family? Because the blocker surfaced on a specific exact replay prefix and must be re-evaluated on the same replay surface.
  4. Why must the same replay surface be reused? Because truthful reclassification depends on comparable scenarios, baseline, and fail-fast behavior.
  5. Why is a fresh runtime mandatory? Because stale in-memory runtime would invalidate the closure claim even if the proof helper is fixed.
- `Root cause statement`: closure is pending because the repaired proof helper has not yet been exercised on one fresh exact replay artifact generated from the same locked `r4` scenarios and baseline on a fresh local runtime.
- `Fix mechanism`: start a fresh worktree runtime, rerun the exact `r4` command shape as `r5`, strict-audit the artifact, and classify the first surviving blocker only from that fresh evidence.

## Reuse-first plan (mandatory)
- `Internal reuse`:
  - exact `r4` command shape from `python3 scripts/quality_artifact_report.py --hours 48 --show-commands`
  - strict audit command `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
  - locked scenarios `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
  - baseline `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `External reuse`:
  - none beyond the implementation-family search already recorded
- `Why not reinvent the wheel`:
  - this block is evidence-only; the repo already has the fixed proof helper, locked scenarios, baseline, and audit tooling.

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: this block produces fresh replay evidence only; no new runtime or proof implementation is allowed.
- `Family handled in this block`: `seed19 r4 confirm-hook replay truth`
- `Closure artifact expected from this mode`: one fresh exact replay artifact plus strict audit and canon sync.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: this is replay/closure by intent, but the worktree already carries approved code deltas; keeping `implementation` mode avoids false governance failure while canon syncs to fresh replay truth.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked replay scenarios or baseline
- do not reopen acceptance evidence-pack work before fresh replay truth is classified

## Scope
- publish this bounded replay TP/report lane
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- rerun the exact `r4` command shape as one fresh replay artifact `/tmp/booking_quality/a922-go2f-seed19-r5`
- strict-audit the new run
- classify the fresh surviving path
- sync canon/session/packet to the replay outcome

## Out of scope
- new runtime implementation
- new proof/oracle implementation
- seed `42`
- PG checklist assembly or acceptance `lock` retry

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
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
1. Publish this replay TP and matching report shell.
2. Re-run the targeted confirm-hook proof test and verify no listener is active on `127.0.0.1:18186`.
3. Start a fresh local runtime from the current worktree and prove `/admin/version.git_commit == HEAD`.
4. Execute one fresh exact replay as `/tmp/booking_quality/a922-go2f-seed19-r5` using the same `r4` scenarios and baseline.
5. Complete strict audit on the fresh artifact.
6. Read the surviving path, write the replay report, and sync canon/session truth from the new artifact.

## DoD
- fresh run `/tmp/booking_quality/a922-go2f-seed19-r5` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- runtime parity on `http://127.0.0.1:18186/admin/version` matches current `HEAD` before replay
- the replay reuses the `r4` command shape with only `run_id` / `output_dir` changed
- the report truthfully classifies whether infra is restored and whether any downstream blocker survives independently
- mandatory packet / guard / architecture / session checks pass after canon sync
- next non-negotiable move comes from fresh evidence, not stale `r4`

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"`
- `python3 - <<'PY'
import json, subprocess, urllib.request
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, cwd='/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922').strip()
with urllib.request.urlopen('http://127.0.0.1:18186/admin/version', timeout=10) as response:
    runtime = json.load(response).get('git_commit')
print({'head': head, 'runtime': runtime, 'match': head == runtime})
PY`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r5 --run-id a922-go2f-seed19-r5 --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r5/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- `Max direct replay runs`: `1`
- `Fail-fast / scenario lock`: exact `r4` scenarios only; same baseline and thresholds as the blocker artifact
- `Stop condition`: stop immediately if runtime parity fails, preflight is invalid, or a second expensive rerun would be needed to explain the same artifact
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- `Strategy`: evidence-only local replay on the repaired proof helper; no runtime mutation in this block
- `Go/no-go signals`: confirm-hook deterministic proof stays green, runtime parity matches `HEAD`, replay artifact is audit-complete, and governance checks stay green after sync
- `Rollback`: revert TP/report/canon/session updates, rebuild the packet, rerun mandatory guards; keep the produced run dir only as forensic evidence
- `Post-release monitoring window`: next block must classify the fresh replay artifact before any acceptance evidence work resumes

## Rollback
- revert doc/canon/report changes for this replay block; keep the produced run dir only as evidence

## No-go
- do not change runtime/core code in this block
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`
- do not run seed `42`
- do not resume acceptance `go_to_full` checklist work before fresh replay truth is classified

## Risks/Blockers
- the fresh replay may stay semantic-red and surface a narrower downstream blocker
- runtime parity may fail if the local server is not started from this worktree
- advisory judge noise may still appear even if infra is restored

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: duplicate top-level defs in `truffles-api/app/services/reasoning_core.py`, seed `42`, PG checklist assembly, and acceptance `lock` retry remain deferred
- `Why not in this block`: this block is closure-only for the repaired `r4` proof family
- `Risk if deferred`: acceptance re-entry stays blocked on stale seed-`19` truth
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one new bounded family TP if replay stays semantic-red
- `Expiry/trigger to stop deferral`: stop deferral immediately after the fresh replay artifact is classified

## Next-block contract (mandatory)
- `Next block objective`: classify the fresh `r5` replay truth and either reopen a narrower runtime/proof family or return to the acceptance evidence-pack family if seed `19` goes green
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"`
- `Blocked-by conditions`: runtime parity cannot be established; replay is infra-invalid for a new reason; replay surfaces a new bounded family before canon sync
- `Owner role for closure`: `Brain | Top Architect`
