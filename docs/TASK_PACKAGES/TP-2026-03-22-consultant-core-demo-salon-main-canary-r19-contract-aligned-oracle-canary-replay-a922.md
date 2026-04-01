# TP-2026-03-22 — Consultant Core Demo Salon Main Canary R19 Contract-Aligned Oracle Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-PROOF-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `UNLOCKS`: `IMPLEMENT-CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-EVIDENCE-BUNDLE`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run one fresh guarded replay on the same locked demo-salon canary surface after the bounded `ops/diagnose.py` oracle-parity fix. This block is truthful only if it starts a fresh local runtime, produces one fresh comparable artifact, completes strict audit, and proves whether the remaining `r19` proof family is closed without reopening runtime or scenario work.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
- `/tmp/booking_quality/_scenario_governance_registry.json`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `TECH.md`

## FACT pre-check (before replay)
- `Impacted docs/artifacts`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r19 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [6, 9, 11, 12]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('evaluation'), row.get('judge'))
PY`
  - `ss -ltnp | rg ':18186' || true`
- `FACT findings`:
  - `r19` is runtime-green (`infra_valid=true`, `turns_strict_failed=0`) and the remaining blocker is proof-only.
  - bounded proof-only implementation is already landed locally in `ops/diagnose.py`; the repo still lacks fresh replay evidence on the same canary surface.
  - the next replay must reuse the exact locked scenario file `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`.
  - no listener is active on `127.0.0.1:18186`, so truthful replay requires a fresh local runtime start.

## One web search (mandatory before implementation)
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm judge pass fail clear detailed rubric`
- **Date/time (local):** `2026-03-22T13:34:21+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Reuse rule for this block:** no new query. Reuse the single exact search already recorded in the parent proof family; replay/closure work inside the same family does not open another query.
- **Existing solutions found:** auxiliary graders must stay aligned to the production contract and calibrated to human arbitration.
- **Decision:** `reuse/integrate`
  - reuse the parent-family research, the same locked scenario, and the same guarded replay surface
- **Rejected options:**
  - second web query
  - runtime edits before fresh replay
  - scenario mutation before closure replay

## Root cause (mandatory)
- **Symptom:** the bounded oracle-proof fix exists locally, but the repo still lacks fresh replay evidence proving the same locked canary surface is now semantically green.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json` and confirm `infra_valid=true`, `semantic_valid=false`, `turns_strict_failed=0`
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json` and confirm `winner=contract`, `conflict_count=4`
  3. inspect `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md` and confirm proof-only parity fixes are landed with deterministic evidence only
  4. verify `127.0.0.1:18186` needs a fresh runtime start before replay
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- **Five Whys:**
  1. Why is the family not closed yet? Because only deterministic proof exists for the oracle-parity fix.
  2. Why is deterministic proof insufficient? Because canary closure is accepted only after the same locked scenario is replayed and audited.
  3. Why reuse the same scenario? Because comparison is truthful only on the stable canary surface.
  4. Why start a fresh runtime? Because replay evidence is invalid if it runs against stale in-memory code or no listener at all.
  5. Why not open new runtime/proof work first? Because the next admissible question is closure, not another implementation hypothesis.
- **Root cause statement:** closure is pending because the proof-only fix has not yet been replayed on the locked demo-salon canary surface under a fresh local runtime and strict audit.
- **Fix mechanism:** start the local runtime fresh, run one guarded replay with the same scenario surface, complete strict audit, then sync canon from the new artifact only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - parent proof implementation TP/report
  - existing guarded replay command shape from `/tmp/booking_quality/a922-check-booking-proof-r19/run_manifest.json`
  - locked scenario file `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - strict audit command `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
- **External reuse:**
  - the same OpenAI evaluation best-practices guidance already recorded in the parent family
- **Why not reinvent the wheel:** this block is evidence-only; runtime semantics and scenario surface are already fixed.

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: this block does not change runtime semantics; it verifies the bounded proof family on the real canary path and classifies only from fresh evidence
- `Family handled in this block`: `r19 contract-aligned oracle replay closure`
- `Closure artifact expected from this mode`: one fresh replay artifact + strict audit + canon sync

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: the block is closure-only by intent, but the worktree already contains the approved proof diff; keeping `implementation` avoids false governance failures on the existing code delta.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked scenario file
- do not claim final acceptance closure from this dev-lane replay alone

## Scope
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- run one guarded comparable replay as `/tmp/booking_quality/a922-check-booking-proof-r20`
- strict-audit the new artifact
- sync canon/session truth from fresh replay evidence only

## Out of scope
- new runtime implementation
- new `ops/diagnose.py` changes
- scenario mutation
- edits to frozen routers
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
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
1. Start a fresh local runtime from the current worktree with canon env sourced.
2. Run one guarded comparable replay as `a922-check-booking-proof-r20` on the locked scenario surface.
3. Complete strict audit on the new artifact.
4. Publish the replay report and sync canon/session truth from `r20`.
5. Hand off the next move as final acceptance evidence work, not another demo-salon micro-fix.

## DoD
- fresh run `/tmp/booking_quality/a922-check-booking-proof-r20` exists with `summary.json`, `responses.jsonl`, `brief.md`, and strict-audit artifacts
- the replay uses the exact locked scenario file from `r19`
- `r20` truthfully answers whether the proof family is closed on the real canary path
- mandatory packet / guard / architecture / session checks pass after canon sync
- next non-negotiable move comes from fresh `r20` evidence rather than stale `r19` assumptions

## Checks
- `python3 - <<'PY'
import urllib.request
for path in ('/admin/health', '/admin/version'):
    with urllib.request.urlopen('http://127.0.0.1:18186' + path, timeout=10) as response:
        print(path, response.status)
PY`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-check-booking-proof-r20 --owner-file ops/diagnose.py --quick-check 'cd /home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922 && pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"' --forensic-override-reason 'post-r19 contract-aligned oracle proof continuation after audited semantic-invalid r19 showed HQ1 and judge parity drift only' -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 1 --scenarios-file /tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json --mode llm --min-turns 8 --max-turns 8 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --allowlist-jids 99999000196@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-check-booking-proof-r20 --run-id a922-check-booking-proof-r20 --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r20 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r20/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r20/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r20/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** one replay only, fixed `scenarios_file`, `count=1`, `max-failures=1`
- **Stop condition:** if preflight is invalid or a second expensive replay would be needed to explain the same artifact
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** evidence-only local replay on the fixed proof path; no runtime mutation in this block
- **Go/no-go signals:** health/version preflight responds `200`, replay summary is strict-green, strict audit produces a valid artifact, and canon guards remain green after sync
- **Rollback:** revert TP/report/canon/session updates, rebuild the packet, rerun mandatory guards; keep the run dir only as forensic evidence
- **Post-release monitoring window:** the next block must convert the green demo-salon canary into canonical acceptance evidence or classify the remaining acceptance gap

## Rollback
1. Revert this replay TP/report and matching canon/session updates.
2. Restore the proof implementation block as active.
3. Rebuild the packet and rerun the mandatory guards.

## No-go
- no runtime or oracle edits in this block
- no new scenario generation or mutation
- no second expensive replay without a new hypothesis
- no stale runtime reuse once fresh evidence is required

## Risks / blockers
- even with `semantic_valid=true`, manual audit can still keep judge conflicts advisory-only; that must not be misreported as zero oracle debt
- final program acceptance still needs canonical acceptance evidence beyond this dev-lane replay
- duplicate defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - final acceptance evidence / multi-pack closure remains open after demo-salon canary closure
  - duplicate top-level defs remain deferred in `truffles-api/app/services/reasoning_core.py`
- `Why not in this block:`
  - this block is canary replay closure only
- `Risk if deferred:`
  - without the next acceptance bundle, runtime closure is green locally but final program closure remains only partially evidenced
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `Expiry/trigger to stop deferral`: stop deferral if a new runtime/proof family is proposed before the acceptance-evidence bundle is reopened

## Next-block contract (mandatory)
- `Next block objective`: resume the post-runtime acceptance evidence lane now that the demo-salon main canary is fresh and semantically green
- `First deterministic check command`: `python3 scripts/quality_artifact_report.py --hours 24 --show-commands`
- `Blocked-by conditions`: none beyond canon sync for this replay artifact
- `Owner role for closure`: `Brain / Top Architect`
- `Exact next move`: `implement_consultant_core_final_ingress_coordinator_terminal_closure_acceptance_evidence_bundle`
