# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-POST-FIX-REPLAY-CLASSIFICATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh post-fix canary replay on the exact sanitized scenario that surfaced turn `9`, keep the lane evidence-only, and classify the fresh artifact before any new runtime or oracle work. This block is truthful only if it proves whether turn `9` is gone on the real dialog path and whether turn `12` survives independently after the landed fix.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r12/run_manifest.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`

## FACT pre-check (before replay)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
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
run_dir = Path('/tmp/booking_quality/a922-check-booking-proof-r12')
for name in ['summary.json', 'run_manifest.json', 'manual_audit.json']:
    path = run_dir / name
    print(f'--- {name} ---')
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        for key in ['run_id', 'status', 'mode', 'command', 'infra_valid', 'semantic_valid', 'stop_reason']:
            if key in data:
                print(f'{key}: {data[key]}')
PY`
  - `python3 - <<'PY'
import urllib.request
url = 'http://127.0.0.1:18186/admin/health'
with urllib.request.urlopen(url, timeout=10) as response:
    print(response.status)
    print(response.read(400).decode('utf-8', 'replace'))
PY`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`
- `FACT findings`:
  - the exact-time runtime fix is landed and the focused deterministic suite is green (`6 passed`)
  - mandatory packet / guard / architecture / session checks are green on the current worktree
  - `/tmp/booking_quality/a922-check-booking-proof-r12/run_manifest.json` shows the surfaced family already has one comparable dev replay command and exact `scenarios_file=/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json` is artifact-complete but not a valid closure artifact because `semantic_valid=false`
  - `http://127.0.0.1:18186/admin/health` responds `200`, so one fresh local replay is admissible
- `Detected drift (docs vs runtime)`:
  - repo truth already says guarded replay is the next move, but there is still no fresh post-fix artifact to prove the fix on the real canary path

## One web search (mandatory before implementation)
- **Query (exact):** `LangSmith compare experiments same dataset official docs`
- **Date/time (local):** `2026-03-22T08:18:24+05:00`
- **Sources opened (from this query):**
  - `https://docs.langchain.com/langsmith/home`
- **Source quality:** vendor documentation / primary source.
- **Reuse rule for this block:** this exact query is the single replay-evidence search; no second query is allowed.
- **Existing solutions found:** official evaluation guidance emphasizes measuring and tracking quality over time against stable evaluation inputs rather than changing the test surface mid-comparison.
- **Decision:** `reuse/integrate`
  - reuse the exact sanitized scenario file and comparable replay command shape from `r12`
  - integrate one fresh post-fix run plus mandatory manual audit
  - do not build a new scenario generator, new baseline, or new acceptance wrapper in this block
- **Rejected options:**
  - new scenario mutations before replay
  - acceptance baseline update from invalid `r12`
  - turn-12 oracle patch before fresh replay
  - any runtime or frozen-router edit in this block

## Root cause (mandatory)
- **Symptom:** the repo still lacks fresh post-fix canary evidence for the surfaced family; only deterministic tests and the pre-fix invalid replay artifact `a922-check-booking-proof-r12` exist.
- **Minimal reproduction:**
  1. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md` and confirm the fix is landed with focused deterministic evidence only.
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json` and confirm `infra_valid=true` but `semantic_valid=false`.
  3. inspect `/tmp/booking_quality/a922-check-booking-proof-r12/run_manifest.json` and confirm the comparable replay command + sanitized scenario file already exist.
  4. verify `http://127.0.0.1:18186/admin/health` is reachable, so one fresh local replay is admissible.
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/run_manifest.json`
  - `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- **Five Whys (or equivalent):**
  1. Why is the runtime fix not yet truthfully closed? Because only focused deterministic regressions passed; the real canary path has not been replayed after the fix.
  2. Why can we not use `r12` as closure evidence? Because `r12` is pre-fix and `semantic_valid=false`, so it cannot prove post-fix behavior.
  3. Why must the replay reuse the same scenario file? Because changing the dialog surface now would destroy comparability with the surfaced family.
  4. Why is this a proof/evidence block rather than a new runtime block? Because the runtime code already changed and the remaining gap is fresh observed evidence.
  5. Why should turn `12` stay untouched until after replay? Because it was downstream of the turn-9 stall on the old artifact and needs fresh classification.
- **Root cause statement:** the current closure gap is not missing code but missing comparable post-fix canary evidence, because the only surfaced artifact (`r12`) predates the fix and is semantically invalid for closure.
- **Fix mechanism:** run one fresh comparable dev replay against the same sanitized scenario file on the current runtime, complete manual audit, then classify turn `9` and turn `12` from the fresh artifact before any further runtime or oracle change.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/booking_quality/a922-check-booking-proof-r12/run_manifest.json` as the comparable replay command source
  - `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json` as the exact stable scenario file
  - `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - the already-green focused deterministic suite from the implementation block
- **External reuse:**
  - `https://docs.langchain.com/langsmith/home`
- **Why not reinvent the wheel:**
  - this block should reuse the repo's existing replay lane and exact surfaced scenario, not invent a new proof harness

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `30`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - this block is evidence-only in intent, but the worktree already contains approved runtime changes; keeping `implementation` mode avoids false fail-closed governance on the existing code diff

## Invariant
- do not edit runtime code or frozen webhook routers in this block
- do not tighten turn `12` oracle before reading the fresh replay artifact
- do not mutate the scenario file or broaden scenario coverage
- do not claim acceptance or open-world closure from this block
- do not start a second expensive replay without new evidence

## Scope
- publish the replay TP/report and switch canon/session to it
- execute one fresh comparable dev replay on the exact sanitized scenario file
- run mandatory manual audit on the fresh artifact
- inspect turns `9` and `12` on the fresh artifact and hand off the next classification move

## Out of scope
- runtime code changes
- oracle/judge changes in `ops/diagnose.py`
- acceptance lock/replay/full chain
- baseline updates
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
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
1. Publish this replay TP and switch canon/session to it.
2. Revalidate the exact focused deterministic suite and local replay preflight.
3. Run one fresh comparable replay as `a922-check-booking-proof-r13` against `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`.
4. Complete strict artifact audit on the fresh run.
5. Read fresh turns `9` and `12`, write the replay report, and hand off the next classification move.

## DoD
- active canon points to this replay TP
- fresh run `/tmp/booking_quality/a922-check-booking-proof-r13` exists with `summary.json`, `responses.jsonl`, `brief.md`, and manual audit artifacts
- the replay uses the exact sanitized scenario file from `r12`
- the report classifies whether turn `9` is repaired on the real canary path and whether turn `12` survives independently
- mandatory packet / guard / architecture / session checks pass after canon sync

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`
- `python3 - <<'PY'
import urllib.request
url = 'http://127.0.0.1:18186/admin/health'
with urllib.request.urlopen(url, timeout=10) as response:
    print(response.status)
PY`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 1 --scenarios-file /tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json --mode llm --min-turns 8 --max-turns 8 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --allowlist-jids 99999000191@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-check-booking-proof-r13 --run-id a922-check-booking-proof-r13 --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r13 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r13/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r13/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r13/brief.md`
- `/tmp/booking_quality/a922-check-booking-proof-r13/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r13/manual_audit.md`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** one replay only, fixed `scenarios_file`, `count=1`, `max-failures=1`
- **Stop condition:** if preflight is invalid, the run is infra-invalid, or a second expensive replay would be needed to explain the same artifact
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** evidence-only local replay on the fixed runtime; no rollout or runtime mutation in this block
- **Go/no-go signals:** focused deterministic suite stays green, local health responds, replay artifacts are audit-complete, and governance checks stay green after sync
- **Rollback:** revert TP/report/canon/session updates, rebuild the packet, rerun the mandatory guards; leave the produced run dir only as forensic evidence
- **Post-release monitoring window:** the next block must classify the fresh replay artifact before any new runtime or oracle change

## Rollback
1. Revert this replay TP/report and matching canon/session updates.
2. Restore the runtime implementation block as active.
3. Rebuild the packet and rerun governance/session checks.

## No-go
- no runtime or oracle edits in this block
- no new scenario generation or mutation
- no acceptance baseline update from the fresh replay
- no second expensive replay without a new hypothesis
- no turn-12 classification from old `r12` once fresh replay exists

## Risks / blockers
- the replay may still finish `semantic_valid=false`, which would keep the block as a truthful classification/evidence block instead of a closure block
- local dev lane still depends on external judge key discovery from env files / console env
- downstream turn `12` may remain ambiguous even after turn `9` is fixed and require a separate oracle/runtime classification block

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - post-fix turn `12` classification is still pending until the fresh replay is read
  - final acceptance / open-world closure remains pending
  - replay evidence here is still dev-lane, not release acceptance
- `Why not in this block:`
  - this block is only the truthful replay/evidence bridge after the landed runtime fix
- `Risk if deferred:`
  - without a fresh replay artifact, the team can neither close the turn-9 family nor truthfully decide whether turn `12` is still a runtime issue
- `Linked follow-up Task Package(s):`
  - `audit_consultant_core_demo_salon_post_fix_canary_replay_before_any_new_runtime_or_oracle_change`
- `Expiry/trigger to stop deferral:`
  - stop deferral immediately after the fresh replay is audited; no new runtime or oracle block is allowed first

## Next-block contract (mandatory)
- `Next block objective:`
  - classify the fresh replay artifact before any new runtime or oracle change, deciding whether turn `9` is closed and whether turn `12` remains a runtime bug or oracle debt
- `First deterministic check command:`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r13 --status done --strict-artifacts`
- `Blocked-by conditions:`
  - replay artifacts missing or unaudited
  - local replay preflight invalid
  - governance checks red after canon sync
- `Owner role for closure:` `Top Architect`
