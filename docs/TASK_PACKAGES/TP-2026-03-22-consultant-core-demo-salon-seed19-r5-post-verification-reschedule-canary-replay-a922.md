# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R5 Post Verification Reschedule Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `UNLOCKS`: `classify_consultant_core_demo_salon_seed19_r6_after_post_verification_reschedule_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh exact replay on the original seed-`19` blocker scenarios after the bounded post-verification reschedule runtime repair. This block is truthful only if runtime parity is proven on `127.0.0.1:18186`, the replay reuses the locked scenarios/baseline, and strict audit classifies the next surviving family without narrative shortcuts.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`

## FACT pre-check (before replay)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`
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
  - `ss -ltnp | rg ':18186' || true`
  - `git rev-parse HEAD`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
summary=json.loads(Path('/tmp/booking_quality/a922-go2f-seed19-r5/summary.json').read_text())
print({
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'stop_reason': summary.get('stop_reason'),
})
PY`
- `FACT findings`:
  - the bounded runtime repair is landed locally and focused deterministic proof is green
  - no truthful replay for the repaired seed-`19` family exists yet
  - the replay must reuse `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` and baseline `/tmp/booking_quality/a922-go2f-seed19/summary.json`

## One web search (mandatory before implementation)
- `Reuse rule for this block`: replay-only block; no new query is opened. Reuse the implementation-family search already recorded in `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`.
- **Query (exact):** `Rasa forms interruptions requested slot preserve filled slots official docs`
- **Date/time (local):** `2026-03-22T21:15:53+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Reuse note:** no new query is opened in this replay block.
- **Rejected options:** new query; scenario mutation; baseline mutation; acceptance lock before replay.

## Root cause (mandatory)
- Symptom: pre-fix replay `r5` failed strict on dialog `1`, turn `13` because post-verification exact-time reschedule dropped grounded `service` and reopened `service_choice`.
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl` turn `13`
  2. confirm `booking_slots={'datetime': '18:30'}` and `expected_reply_type=service_choice`
  3. compare with the landed implementation block proving snapshot-grounded `service` is now rehydrated before missing-slot recomputation
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r5/{summary.json,responses.jsonl,manual_audit.json}`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- Five Whys:
  1. Why is replay needed? Because deterministic proof alone does not prove the real artifact lane is repaired.
  2. Why must replay be exact? Because only the locked seed-`19` scenarios make the before/after comparison truthful.
  3. Why must runtime parity be checked? Because stale in-memory code previously produced non-canonical replay evidence.
  4. Why is fail-fast still acceptable here? Because family boundary is already fixed; this is a closure block, not discovery.
  5. Why can acceptance remain paused? Because the seed-`19` runtime family must close before fresh multi-seed acceptance evidence resumes.
- Root cause statement: the repo still lacks fresh exact replay evidence for the repaired seed-`19` family, so truthful closure requires one parity-checked replay before any further acceptance decisions.
- Fix mechanism: start fresh local runtime, prove `/admin/version.git_commit == HEAD`, rerun the exact replay command shape as `a922-go2f-seed19-r6`, strict-audit the artifact, and sync canon to the result.

## Reuse-first plan (mandatory)
- Internal reuse:
  - reuse `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
  - reuse baseline `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - reuse the exact `r5` command shape from `/tmp/booking_quality/a922-go2f-seed19-r5/run_manifest.json`
- External reuse:
  - none beyond the implementation-family search already recorded
- Why not reinvent the wheel:
  - the locked scenarios, baseline, and prior replay command already exist; this block only re-executes them on fresh repaired runtime.

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: this block collects fresh exact replay evidence after a bounded runtime repair
- `Family handled in this block`: `seed19 r5 post-verification exact-time reschedule continuity`
- `Closure artifact expected from this mode`: one fresh exact replay artifact plus strict audit and canon sync

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: replay/closure only; no new runtime code expected in this block

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked scenarios or baseline
- do not claim acceptance closure from replay alone

## Scope
- start fresh local runtime on `127.0.0.1:18186`
- prove `/admin/version.git_commit == HEAD`
- run one exact replay as `/tmp/booking_quality/a922-go2f-seed19-r6`
- strict-audit the artifact and classify the next surviving family
- sync canon/session/packet to the replay result

## Out of scope
- new runtime edits
- new web search
- acceptance `lock` / `go_to_full`
- seed `42`
- oracle/proof changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`
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
1. Verify no stale listener is active on `127.0.0.1:18186`.
2. Start a fresh local runtime from the current worktree and prove `/admin/version.git_commit == HEAD`.
3. Reuse the exact `r5` replay command shape with only `run_id` / `output_dir` changed to `a922-go2f-seed19-r6`.
4. Strict-audit the fresh artifact.
5. Sync canon/session/packet to the replay result and hand off the next honest move.

## DoD
- fresh run `/tmp/booking_quality/a922-go2f-seed19-r6` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- runtime parity on `http://127.0.0.1:18186/admin/version` matches current `HEAD` before replay
- replay reuses the locked seed-`19` scenarios and baseline
- canon states whether turn `13` is closed or a new surviving family remains
- mandatory packet / guard / architecture / session checks pass after sync

## Checks
- `ss -ltnp | rg ':18186' || true`
- `python3 - <<'PY'
import json
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:18186/admin/version', timeout=10) as response:
    data=json.load(response)
print(data)
PY`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r6 --run-id a922-go2f-seed19-r6 --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r6 --status done --strict-artifacts`
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
- `/tmp/booking_quality/a922-go2f-seed19-r6/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r6/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r6/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r6/manual_audit.json`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-canary-replay-a922.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `1`
- **Fail-fast / scenario lock:** exact locked seed-`19` scenarios only, `--max-failures 1`
- **Stop condition:** stop after one fresh audited replay and sync canon to the result
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** replay-only validation on fresh local runtime; no runtime rollout in this block
- **Go/no-go signals:** runtime parity matches `HEAD`, replay artifact is infra-valid, strict audit completes, guard/session stack stays green
- **Rollback:** stop the local listener, discard non-canonical replay artifacts, revert doc/canon sync if needed
- **Post-release monitoring window:** any new runtime family must be classified before acceptance work resumes

## Rollback
1. Stop the local listener on `127.0.0.1:18186`.
2. Mark any incomplete replay as non-canonical if needed.
3. Revert this replay TP/report/canon sync if the run is invalid.

## No-go
- no runtime edits in this block
- no scenario mutation
- no baseline mutation
- no second web query
- no acceptance lock before replay truth is established

## Risks / blockers
- stale local runtime would invalidate replay evidence
- if `r6` closes turn `13`, a new downstream family may become first-fail
- acceptance remains paused until this exact replay is classified

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - duplicate defs remain in `truffles-api/app/services/reasoning_core.py`
  - acceptance evidence-pack work remains paused behind seed-`19` replay truth
- `Why not in this block:`
  - replay/closure only; no structural cleanup or acceptance expansion here
- `Risk if deferred:`
  - without fresh replay, the repo still lacks truthful evidence that the repaired runtime family is gone on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `classify_consultant_core_demo_salon_seed19_r6_after_post_verification_reschedule_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any new acceptance attempt or new seed-`42` work

## Next-block contract (mandatory)
- `Next block objective:`
  - classify fresh replay `r6` and lock the next surviving family, if any, before any new runtime or acceptance move
- `First deterministic check command:`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r6 --status done --strict-artifacts`
- `Blocked-by conditions:`
  - fresh replay is infra-invalid or non-canonical
  - runtime parity on `:18186` does not match `HEAD`
  - mandatory guard/session stack fails after sync
- `Owner role for closure:`
  - `Brain / Top Architect`
