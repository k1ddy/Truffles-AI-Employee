# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-POST-FIX-CLASSIFICATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh post-fix canary replay on the same sanitized scenario that surfaced turn `13`, keep the block evidence-only, and classify the fresh artifact before any new runtime or oracle work. This block is truthful only if it proves whether explicit name progression is now repaired on the real dialog path and whether any downstream blocker survives independently after the landed non-frozen fix.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r14/run_manifest.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`

## FACT pre-check (before replay)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
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
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [12, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('evaluation'))
PY`
  - `python3 - <<'PY'
import json
from pathlib import Path
run_dir = Path('/tmp/booking_quality/a922-check-booking-proof-r14')
for name in ['summary.json', 'run_manifest.json', 'manual_audit.json']:
    path = run_dir / name
    print(f'--- {name} ---')
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        for key in ['run_id', 'status', 'mode', 'command', 'infra_valid', 'semantic_valid', 'stop_reason']:
            if key in data:
                print(f'{key}: {data[key]}')
PY`
  - `lsof -iTCP:18186 -sTCP:LISTEN -n -P`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`
- `FACT findings`:
  - the bounded turn-13 runtime fix is landed and the focused deterministic suite is green (`4 passed`)
  - `/tmp/booking_quality/a922-check-booking-proof-r14` is the current truthful pre-fix canary artifact: it closes turn `9`, closes turn `12`, and isolates turn `13` as the surviving runtime family
  - `/tmp/booking_quality/a922-check-booking-proof-r14/run_manifest.json` already preserves the comparable replay command shape and the exact `scenarios_file=/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - there is currently no listener on `127.0.0.1:18186`, so truthful replay requires a fresh local runtime start before evidence can be collected
- `Detected drift (docs vs runtime)`:
  - repo truth already says guarded replay is the next move, but there is still no fresh post-fix artifact proving the landed turn-13 fix on the real canary path

## One web search (mandatory before implementation)
- **Query (exact):** `LangSmith compare experiments same dataset official docs`
- **Date/time (local):** `2026-03-22T08:18:24+05:00`
- **Sources opened (from this query):**
  - `https://docs.langchain.com/langsmith/home`
- **Source quality:** vendor documentation / primary source.
- **Reuse rule for this block:** reuse the exact replay-evidence search already used for the comparable turn-9 replay lane; no second query is allowed.
- **Existing solutions found:** official evaluation guidance emphasizes comparing stable experiments against unchanged evaluation inputs instead of mutating the test surface mid-comparison.
- **Decision:** `reuse/integrate`
  - reuse the exact sanitized scenario file and comparable replay command shape from `r14`
  - integrate one fresh post-fix run plus mandatory strict audit
  - do not build a new scenario generator, new baseline, or new acceptance wrapper in this block
- **Rejected options:**
  - new scenario mutations before replay
  - acceptance baseline update from `r14`
  - oracle tightening before fresh replay
  - any new runtime or frozen-router edit in this block

## Root cause (mandatory)
- **Symptom:** the repo still lacks fresh post-fix canary evidence for the turn-13 family; only deterministic fix evidence and the pre-fix truthful artifact `a922-check-booking-proof-r14` exist.
- **Minimal reproduction:**
  1. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md` and confirm the fix is landed with focused deterministic evidence only
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` and confirm turn `13` is still the blocker on the pre-fix replay artifact
  3. inspect `/tmp/booking_quality/a922-check-booking-proof-r14/run_manifest.json` and confirm the exact comparable replay command + sanitized scenario file already exist
  4. verify there is no live listener on `127.0.0.1:18186`, so the next truthful step is a fresh runtime start and one comparable replay
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
  - `lsof -iTCP:18186 -sTCP:LISTEN -n -P`
- **Five Whys:**
  1. Why is turn `13` not truthfully closed yet? Because there is no fresh replay artifact after the landed runtime fix.
  2. Why is there no fresh replay artifact? Because the prior active block stopped at bounded implementation + deterministic regressions.
  3. Why can deterministic regressions not close the family alone? Because the program accepts core behavior only after the same canary path is replayed and audited.
  4. Why must the same canary path be replayed instead of generating a new scenario? Because comparison is only truthful on a stable scenario surface.
  5. Why is replay blocked right now? Because the local worktree runtime on `:18186` is not running and must be started fresh before collecting comparable evidence.
- **Root cause statement:** proof closure is pending because the post-fix canary replay has not yet been executed on a fresh local runtime using the same sanitized scenario surface.
- **Fix mechanism:** start the local worktree runtime fresh, rerun exactly one comparable replay on the locked scenario file, strict-audit the resulting artifacts, and classify only from that fresh evidence.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `r14` comparable replay command from `/tmp/booking_quality/a922-check-booking-proof-r14/run_manifest.json`
  - sanitized scenario file `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - focused deterministic turn-13 regression suite already published in the implementation block
  - existing audit command `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
- **External reuse:**
  - the same LangSmith official guidance already recorded for stable-eval replay discipline
- **Why not reinvent the wheel:**
  - this block is evidence-only; the repo already has the fixed runtime path, the stable scenario surface, and the comparable command shape

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not generate a new scenario or mutate the locked scenario file
- do not claim final acceptance closure from dev-lane replay alone

## Scope
- publish the bounded replay TP/report lane
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- rerun the focused deterministic suite required before the expensive replay
- execute one comparable replay as `/tmp/booking_quality/a922-check-booking-proof-r16`
- strict-audit the new run and classify the surfaced turns from fresh evidence only
- sync canon/session/packet to the replay outcome

## Out of scope
- new runtime implementation
- `ops/diagnose.py` oracle changes
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- acceptance baseline refresh or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
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
2. Start a fresh local runtime from the current worktree with the repo env sourced.
3. Revalidate the focused deterministic suite and local replay preflight.
4. Run one fresh comparable replay as `a922-check-booking-proof-r16` against `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`.
5. Complete strict artifact audit on the fresh run.
6. Read fresh turns `13` and any downstream survivors, write the replay report, and sync canon/session truth.

## DoD
- fresh run `/tmp/booking_quality/a922-check-booking-proof-r16` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- the replay uses the exact sanitized scenario file from `r14`
- the report truthfully classifies whether turn `13` is repaired on the real canary path and whether any downstream blocker survives independently
- mandatory packet / guard / architecture / session checks pass after canon sync
- next non-negotiable move is updated from fresh evidence rather than stale `r14` assumptions

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`
- `python3 - <<'PY'
import urllib.request
url = 'http://127.0.0.1:18186/admin/health'
with urllib.request.urlopen(url, timeout=10) as response:
    print(response.status)
PY`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 1 --scenarios-file /tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json --mode llm --min-turns 8 --max-turns 8 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --allowlist-jids 99999000193@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-check-booking-proof-r16 --run-id a922-check-booking-proof-r16 --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r16 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/brief.md`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.md`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** one replay only, fixed `scenarios_file`, `count=1`, `max-failures=1`
- **Stop condition:** if preflight is invalid, the run is infra-invalid, or a second expensive replay would be needed to explain the same artifact
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** evidence-only local replay on the fixed runtime; no runtime mutation in this block
- **Go/no-go signals:** focused deterministic suite stays green, local health responds, replay artifacts are audit-complete, and governance checks stay green after sync
- **Rollback:** revert TP/report/canon/session updates, rebuild the packet, rerun the mandatory guards; leave the produced run dir only as forensic evidence
- **Post-release monitoring window:** the next block must classify the fresh replay artifact before any new runtime or oracle change

## Rollback
1. Revert this replay TP/report and matching canon/session updates.
2. Restore the runtime implementation block as active.
3. Rebuild the packet and rerun the mandatory guards.

## No-go
- no runtime or oracle edits in this block
- no new scenario generation or mutation
- no acceptance baseline update from the fresh replay
- no second expensive replay without a new hypothesis
- no stale-runtime debate once fresh replay exists

## Risks / blockers
- the replay may still finish `semantic_valid=false`, which would keep the block as a truthful classification/evidence block instead of a closure block
- local dev lane still depends on judge key discovery from env + console env
- a new downstream blocker may survive even if turn `13` is repaired, which would require a new bounded decision block rather than an oracle shortcut

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - final acceptance / open-world closure remains pending
  - judge conflicts on turns `6`, `9`, and `11` remain deferred proof debt unless the fresh replay changes that truth
  - this block still produces dev-lane evidence, not release acceptance evidence
- `Why not in this block:`
  - this block is only the truthful replay/evidence bridge after the landed turn-13 runtime fix
- `Risk if deferred:`
  - without a fresh replay artifact, the team cannot truthfully close the turn-13 family or classify any surviving downstream blocker
- `Linked follow-up Task Package(s):`
  - `classify_consultant_core_demo_salon_post_fix_turn13_canary_replay_before_any_new_runtime_or_oracle_change`
- `Expiry/trigger to stop deferral:`
  - stop deferral immediately after the fresh replay artifact exists

## Next-block contract (mandatory)
- `Next block objective:`
  - classify the fresh turn-13 replay artifact and open only the bounded next family, if any survives
- `First deterministic check command:`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [12, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('evaluation'))
PY`
- `Blocked-by conditions:`
  - focused deterministic regressions go red
  - local runtime preflight fails on `:18186`
  - replay artifacts are incomplete or invalid
- `Owner role for closure:` `Top Architect`
