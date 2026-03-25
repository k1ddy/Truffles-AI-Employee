# TP-2026-03-25 Consultant Core Policy Core Acceptance Replay A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-POLICY-CORE-ACCEPTANCE-REPLAY-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `c2b065af`, `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`
- `UNLOCKS`: guarded acceptance evidence or the next truthful blocker family

## Название/цель
Зафиксировать локально доказанную live manual closure в canon и запустить один guarded acceptance replay на текущем runtime fingerprint. Блок не меняет runtime-код: он либо даёт acceptance artifact, либо честно открывает следующий blocker.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: runtime code already landed in `c2b065af`; this block touches only canon docs plus quality artifacts unless acceptance surfaces a new blocker.
- `Baseline commands`:
  - `git status --short --branch`
  - `curl -fsS http://localhost:8000/admin/health`
  - `python3 -m py_compile truffles-api/app/schemas/intent.py truffles-api/app/core/turn_executor.py truffles-api/app/services/intent_service.py truffles-api/app/services/llm/base.py truffles-api/app/services/llm/openai_provider.py truffles-api/app/services/demo_salon_knowledge.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_booking_appointments.py`
- `FACT findings`:
  - live runtime health is green on `localhost:8000` with `livecheck/allowlist/off`
  - Phase D manual dialogs already passed on the live runtime
  - locked replay baseline exists at `/tmp/booking_quality/a922-go2f-seed19/{summary.json,scenarios.json}`
- `Detected drift (docs vs code)`: `STATE.md`, `docs/ACTIVE_PROGRAM.md`, `docs/SOURCE_OF_TRUTH.yaml`, and the session doc were stale and still pointed to the pre-closure structural block

## One web search (mandatory before implementation)
- **Query (exact):** `not applicable`
- **Date/time (local):** 2026-03-25 15:15, Asia/Almaty
- **Why this query is precise:** This is a closure-only / acceptance-only block; no new implementation design is introduced.
- **Sources opened (from this query):**
  - pytest docs: How to invoke pytest — https://docs.pytest.org/en/stable/how-to/usage.html
- **Existing solutions found:** existing guarded workflow already lives in-repo
- **Decision:** reuse `scripts/llm_quality_guarded.sh` and the locked seed-19 replay artifacts
- **Rejected options:** ad-hoc direct `ops/diagnose.py llm-quality` replay for acceptance because it bypasses the guarded workflow
- **Open questions:** none

## Root cause (mandatory)
- **Symptom:** Phase D is locally proven, but canon docs and acceptance evidence do not yet reflect that closure; without a guarded acceptance run, closure remains product-local rather than canonized.
- **Minimal reproduction:** verify runtime health, run the mandatory local deterministic suites, then run one guarded acceptance replay against `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` and `/tmp/booking_quality/a922-go2f-seed19/summary.json`.
- **Evidence to capture:** updated canon docs, deterministic suite outputs, guarded replay `summary.json` / `brief.md` / `manual_audit.json`, and any surfaced failure family.
- **Five Whys (or equivalent):**
  1. Why is closure not final yet? Because acceptance evidence from the current fingerprint is missing.
  2. Why not rerun discovery? Because manual closure already proved the live product slice; the next admissible move is guarded acceptance only.
  3. Why use the locked seed-19 baseline? Because it is the comparable contract artifact already used for this family.
  4. Why run mandatory deterministic suites first? Because AGENTS requires local-first validation before expensive quality.
  5. Why stop after one replay if it fails? Because Phase E is a closure tool, not a replay-first discovery loop.
- **Root cause statement:** the remaining gap is evidence governance, not missing runtime implementation.
- **Fix mechanism:** update canon docs, run the required deterministic/local checks, execute one guarded acceptance replay, and publish the result truthfully.

## Reuse-first plan (mandatory)
- **Internal reuse:** `scripts/llm_quality_guarded.sh`, `ops/diagnose.py`, the locked seed-19 baseline under `/tmp/booking_quality/a922-go2f-seed19`, and the existing runtime on `localhost:8000`.
- **External reuse:** none; this is an in-repo validation path.
- **Why not reinvent the wheel:** the guarded workflow already enforces run integrity, fingerprinting, audit, and acceptance gates.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `closure_review`
- **Doc touch budget (files):** 6
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** the runtime code is already landed; this block is evidence + guarded validation only.

## Invariant
- Do not modify runtime code in this block unless acceptance surfaces a new blocker and a new TP is opened.
- Do not run more than one expensive guarded acceptance replay in this block.
- Do not weaken any quality, oracle, or acceptance gates.

## Scope
- publish the live manual closure evidence in canon docs
- refresh active canon/session pointers to the acceptance block
- run the mandatory local deterministic suites
- run one guarded acceptance replay on the current runtime fingerprint
- publish the truthful result

## Out of scope
- new runtime implementation
- acceptance lock regeneration
- acceptance full run if replay already fails
- any legacy substrate cleanup

## Touch-list
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `/tmp/booking_quality/booking-replay-20260325-a922-phase-e/*`

## Plan (1..N)
1. Update canon docs so the live manual closure is recorded as FACT.
2. Re-verify runtime health and run the required local deterministic suites.
3. Execute one guarded acceptance replay against the locked seed-19 baseline.
4. Audit and publish the acceptance result or the next blocker family.

## DoD
- manual closure evidence is recorded in canon docs
- active block pointers reference this acceptance block
- mandatory local deterministic suites have current outputs
- exactly one guarded acceptance replay artifact exists for this block
- result is documented truthfully with no hidden retries

## Checks
- `git status --short --branch`
- `curl -fsS http://localhost:8000/admin/health`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-20260325-a922-phase-e --allow-no-owner-delta -- --base-url http://127.0.0.1:8000 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-replay-20260325-a922-phase-e --status done --strict-artifacts`

## Evidence
- updated canon docs
- deterministic suite outputs from this block
- `/tmp/booking_quality/booking-replay-20260325-a922-phase-e/{summary.json,brief.md,manual_audit.json,responses.jsonl}`
- follow-up report or blocker note in `STATE.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 1 guarded acceptance replay
- **Fail-fast / scenario lock:** locked seed-19 scenarios, `--max-failures 20`, stop after the first acceptance replay result
- **Stop condition:** if any mandatory deterministic suite fails or the guarded replay is non-green, stop and publish the blocker instead of looping
- **Escalation path:** Brain / Top Architect decide any extra acceptance run

## Release safety (mandatory for non-doc changes)
- **Strategy:** local acceptance-only validation on the current worktree runtime; no rollout changes
- **Go/no-go signals:** mandatory deterministic suites pass, replay artifact is valid, and acceptance gates do not surface a new blocker
- **Rollback:** no runtime rollback in this block; if acceptance fails, publish the blocker and keep code unchanged
- **Post-release monitoring window:** not applicable

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `Drift closeout rule`:
  - update the same block immediately after the replay result; no deferred doc sync

## Rollback
Revert the doc-only updates if they are incorrect. Acceptance artifacts live under `/tmp/booking_quality` and can be discarded if the run is invalid.

## No-go
- no runtime code edits in this block
- no second acceptance replay in this block
- no direct unguarded acceptance command
- no weakening of oracle, audit, or threshold gates

## Risks/Blockers
- mandatory local suites may still surface a product/runtime blocker before acceptance
- guarded replay may fail on a new fingerprint-specific contract family
- local runtime may drift if containers restart unexpectedly mid-run

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: generic pack minimum-data-contract debt remains for branch `e6862577-449e-4c54-9deb-7d9aee782076`; broader open-world closure is still out of scope.
- `Why not in this block`: this block is acceptance review for the demo-salon closure path only.
- `Risk if deferred`: generic-pack gaps can still block broader proof claims even if demo-salon acceptance goes green.
- `Linked follow-up Task Package(s)`: to be opened only if acceptance surfaces a blocker or when the program moves beyond demo-salon closure.
- `Expiry/trigger to stop deferral`: if acceptance passes, the next block must either address generic-pack minimum data or open-world proof expansion.

## Next-block contract (mandatory)
- `Next block objective`: either publish Phase E acceptance closure or open one new bounded blocker TP from the replay result.
- `First deterministic check command`: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-replay-20260325-a922-phase-e --status done --strict-artifacts`
- `Blocked-by conditions`: failed mandatory local suites, unhealthy runtime, or invalid replay artifact
- `Owner role for closure`: Brain / Top Architect

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `curl -fsS http://localhost:8000/admin/health`
- `Do not touch`: `truffles-api/app/core/*` and `truffles-api/app/services/*` unless the acceptance replay surfaces a new blocker and a new TP is opened
- `Open risks`: mandatory local suites or the guarded replay can still surface a blocker
- `First command to verify`: `git status --short --branch`
