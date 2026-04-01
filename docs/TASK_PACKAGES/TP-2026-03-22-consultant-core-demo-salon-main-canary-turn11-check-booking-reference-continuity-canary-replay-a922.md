# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh post-fix canary replay on the same locked scenario surface after the bounded turn-11 runtime repair. This block is truthful only if it starts a fresh local runtime from the current worktree, produces one fresh comparable artifact, strict-audits it, and classifies the surviving path before any new runtime or oracle work.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
- `/tmp/booking_quality/_scenario_governance_registry.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `TECH.md`

## FACT pre-check (before replay)
- `Impacted docs/artifacts`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
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
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [10, 11]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('evaluation'))
PY`
  - `ss -ltnp | rg ':18186' || true`
  - `python3 - <<'PY'
import json
from pathlib import Path
path = Path('/tmp/booking_quality/a922-check-booking-proof-r16/run_manifest.json')
data = json.loads(path.read_text(encoding='utf-8'))
for key in ['run_id', 'status', 'mode', 'command', 'output_dir']:
    print(f'{key}: {data.get(key)}')
PY`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r16` is the current truthful pre-fix replay artifact for this family: `infra_valid=true`, `semantic_valid=false`, `stop_reason=max_failures_reached:1`, and the first surviving blocker is turn `11`.
  - no listener is currently present on `127.0.0.1:18186`, so truthful replay requires a fresh local runtime start before evidence can be collected.
  - `r16` already consumed the same locked scenario file `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`; comparison stays truthful only if the new run reuses that exact file.
  - the guarded wrapper would normally fail-closed on the prior replay mode because `r16` is indexed as `incomplete`, so this block must use one explicit guarded dev-lane continuation reason instead of silently bypassing the ledger/index contract.
- `Detected drift (docs vs runtime)`:
  - repo truth already says replay is the next move, but there is still no fresh post-fix artifact proving the landed turn-11 repair on the real canary path.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms requested_slot preserve requested slot repeated user reply site:rasa.com docs`
- **Date/time (local):** `2026-03-22T11:04:37+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Reuse rule for this block:** reuse the exact search already recorded in the turn-11 implementation family; this replay block does not open a new query.
- **Existing solutions found:** the active requested slot should remain tied to the earliest missing slot after the system merges grounded state.
- **Decision:** `reuse/integrate`
  - reuse the same locked scenario file and comparable replay shape from `r16`
  - integrate one fresh post-fix replay plus strict audit
  - do not build a new scenario or mutate the baseline surface in this block
- **Rejected options:**
  - new scenario mutations before replay
  - oracle tightening before fresh replay
  - runtime edits in this block
  - silent bypass of the replay ledger/index guard

## Root cause (mandatory)
- **Symptom:** the repo still lacks fresh post-fix canary evidence for the turn-11 family; only deterministic fix evidence and the pre-fix truthful artifact `a922-check-booking-proof-r16` exist.
- **Minimal reproduction:**
  1. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md` and confirm the fix is landed with deterministic evidence only
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl` and confirm turn `11` still fails on the pre-fix replay artifact
  3. inspect `/tmp/booking_quality/a922-check-booking-proof-r16/run_manifest.json` and confirm the exact comparable replay command and scenario file already exist
  4. verify there is no live listener on `127.0.0.1:18186`, so the next truthful step is a fresh runtime start and one comparable replay
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/run_manifest.json`
  - `ss -ltnp | rg ':18186'`
- **Five Whys:**
  1. Why is turn `11` not truthfully closed yet? Because there is no fresh replay artifact after the landed runtime fix.
  2. Why is there no fresh replay artifact? Because the prior active block stopped at bounded implementation + deterministic regressions.
  3. Why can deterministic regressions not close the family alone? Because the program accepts core behavior only after the same canary path is replayed and audited.
  4. Why must the same canary path be replayed instead of generating a new scenario? Because comparison is truthful only on a stable scenario surface.
  5. Why is a guarded continuation reason required? Because the replay ledger/index still marks the prior replay mode as `incomplete`, so a new comparable replay must acknowledge and document that indexed state rather than silently bypass it.
- **Root cause statement:** proof closure is pending because the post-fix canary replay has not yet been executed on a fresh local runtime using the same locked scenario surface, and the guard/index contract must be explicitly continued from the prior audited incomplete replay state.
- **Fix mechanism:** start the local worktree runtime fresh, run one guarded dev-lane replay with an explicit continuation reason, strict-audit the resulting artifact, and classify only from that fresh evidence.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `r16` replay command shape from `/tmp/booking_quality/a922-check-booking-proof-r16/run_manifest.json`
  - locked scenario file `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - focused deterministic check-booking owner suite already published in the implementation block
  - existing audit command `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
  - guarded wrapper `scripts/llm_quality_guarded.sh`
- **External reuse:**
  - the same official Rasa requested-slot guidance already recorded for the implementation family
- **Why not reinvent the wheel:**
  - this block is evidence-only; the repo already has the fixed runtime path, the stable scenario surface, and the guarded replay tooling.

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: this block does not change runtime semantics; it verifies the bounded family on the real canary path and classifies only from fresh evidence
- `Family handled in this block`: `turn-11 check-booking reference continuity post-fix closure replay`
- `Closure artifact expected from this mode`: one fresh replay artifact + strict audit + canon sync from fresh evidence

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - the block is replay/closure by intent, but the worktree already carries the approved turn-11 runtime diff; keeping `implementation` mode avoids false governance failures on the existing code delta while canon is synced to fresh replay truth.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not generate a new scenario or mutate the locked scenario file
- do not claim final acceptance closure from dev-lane replay alone

## Scope
- publish the bounded replay TP/report lane
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- revalidate the focused deterministic suite and runtime health preflight
- execute one guarded comparable replay as `/tmp/booking_quality/a922-check-booking-proof-r17`
- strict-audit the new run and classify the surfaced turns from fresh evidence only
- sync canon/session/packet to the replay outcome

## Out of scope
- new runtime implementation
- `ops/diagnose.py` oracle changes
- duplicate-def cleanup
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- acceptance baseline refresh or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Publish this replay TP and prepare the matching report.
2. Start a fresh local runtime from the current worktree with env sourced from canon env files.
3. Revalidate the focused deterministic suite and runtime health preflight.
4. Run one guarded comparable replay as `a922-check-booking-proof-r17` on the locked scenario file with an explicit continuation reason for the prior audited incomplete replay state.
5. Complete strict artifact audit on the fresh run.
6. Read fresh surviving turns, write the replay report, and sync canon/session truth from the new artifact.

## DoD
- fresh run `/tmp/booking_quality/a922-check-booking-proof-r17` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- the replay uses the exact locked scenario file from `r16`
- the report truthfully classifies whether turn `11` is repaired on the real canary path and whether any downstream blocker survives independently
- mandatory packet / guard / architecture / session checks pass after canon sync
- next non-negotiable move is updated from fresh evidence rather than stale `r16` assumptions

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "check_booking_prompt_owner"`
- `python3 - <<'PY'
import urllib.request
url = 'http://127.0.0.1:18186/admin/health'
with urllib.request.urlopen(url, timeout=10) as response:
    print(response.status)
PY`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-check-booking-proof-r17 --owner-file truffles-api/app/services/reasoning_core.py --quick-check 'cd /home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922 && pytest -q truffles-api/tests/test_reasoning_core.py -k "check_booking_prompt_owner"' --forensic-override-reason 'post-fix guarded continuation after audited incomplete replay r16 surfaced turn11 before runtime repair' -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 1 --scenarios-file /tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json --mode llm --min-turns 8 --max-turns 8 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --allowlist-jids 99999000195@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-check-booking-proof-r17 --run-id a922-check-booking-proof-r17 --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r17 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r17/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r17/brief.md`
- `/tmp/booking_quality/a922-check-booking-proof-r17/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r17/manual_audit.md`
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
- the truthful replay finished `semantic_valid=false` even though `turns_strict_failed=0`, so the next block must separate surviving runtime threshold debt from advisory judge/hq1 conflicts without mixing layers again
- local dev lane still depends on env discovery from `/home/zhan/truffles-main/truffles-api/.env` + `/home/zhan/infrastructure/.env`
- the surviving turn-8 family sits close to the already landed exact-time progression logic; implementation must avoid regressing the repaired turn `11` and already-green turn `13`

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - turn `8` booking-interrupt exact-time progression runtime family is still open
  - judge/hq1 conflicts on turns `6`, `9`, and `11` remain deferred proof debt only
  - duplicate defs remain recorded structural debt in `truffles-api/app/services/reasoning_core.py`
  - final acceptance / open-world closure remains pending
- `Why not in this block:`
  - this block is the truthful replay/evidence bridge after the landed turn-11 runtime fix; it classifies from fresh evidence but does not reopen runtime or oracle code itself
- `Risk if deferred:`
  - without a fresh replay classification, the team would either reopen already-closed turn-11 work or patch oracle debt before the newly surfaced turn-8 runtime family
- `Linked follow-up Task Package(s):`
  - `implement_consultant_core_demo_salon_turn8_booking_interrupt_exact_time_progression_runtime_family`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any new oracle/judge tuning or additional replay

## Next-block contract (mandatory)
- `Next block objective:`
  - implement the bounded turn-8 booking-interrupt exact-time progression runtime family while preserving the repaired turn `11` and the re-entered turn `13`
- `First deterministic check command:`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl').open(encoding='utf-8') if line.strip()]
row = next(r for r in rows if r.get('turn_index') == 8)
print(row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('booking_progressed'), row.get('evaluation'))
PY`
- `Blocked-by conditions:`
  - fresh code inspection disproves the turn-8 runtime classification
  - implementation would require frozen-router edits
  - governance/session checks go red after sync
- `Owner role for closure:` `Top Architect`
