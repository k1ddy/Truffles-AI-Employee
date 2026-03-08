# TP-2026-03-06-p6c2-p6-acceptance-closure-a1

- Название/цель: закрыть `P6` только после совместного proof для deterministic expansion, LLM stress synthesis, invariant gates и failure clustering.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`

## One web search (mandatory before implementation)

- Query: `site:docs.python.org argparse action append repeat option python docs`
- Time (UTC): `2026-03-06T16:10:00Z`
- Sources:
  - `Python docs: argparse`
- Ready solutions found:
  - repeated evidence inputs should use explicit repeatable CLI flags instead of positional guessing
  - closure tooling should accept multiple evidence artifacts deterministically so the same command can validate a full proof bundle
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse existing `ops/diagnose.py` status-gate/JSON-summary helpers
  - integrate a dedicated `P6` closure command with repeatable evidence-path flags
- Rejected options:
  - manual checklist-only closure without machine-readable evidence validation
  - one hardcoded artifact path instead of explicit multi-artifact inputs

## Root cause (mandatory)

- Symptom:
  - `P6` could be declared done too early if deterministic expansion or one canary pack is mistaken for full open-world proof.
- Root cause statement:
  - there is no dedicated closure block that checks all required layers together before acceptance.
- Fix mechanism:
  - create an explicit acceptance checklist and evidence gate for the whole `P6` program.

## Invariant

1. `P6` cannot close on one pack, one language, or one run family.
2. acceptance must use invariant evidence, not narrative optimism.

## Scope

- master TP/status docs
- runbook acceptance checklist
- closure evidence references
- heavy-stress policy note (acceptance chain stays `demo_salon` only)

## Out of scope

- new runtime features
- new generator/failure-clustering features

## Plan (1..N)

1. Collect readiness evidence from `P6A`, `P6B.2`, and `P6C.1`.
2. Define explicit go/no-go closure checklist.
3. Implement a machine-readable closure command that fail-closes on missing evidence.
4. Update master TP and runbook with final status only if all gates are green.

## DoD

1. `P6` status can be defended with concrete evidence across all required layers.
2. residual risks are listed explicitly if closure is blocked.

## Checks

- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "open_world or invariant_gate"`
- `git diff --check`

## Execution status

- `done` (closure gate implemented; program-level `P6` status remains `blocked` until a real proof bundle passes)

## Evidence

1. `ops/diagnose.py`
   - added `llm-quality-open-world-closure`
   - added deterministic profile coverage validation and matrix/child-summary closure checks
2. `truffles-api/tests/test_booking_quality_status_gate.py`
   - added deterministic `open_world` helper/CLI regression tests
3. `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
   - added canonical `P6` closure command and interpretation
4. Checks:
   - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py`
   - `ruff check ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`
   - `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`
   - `git diff --check`
5. Program status note:
   - `P6` itself is not marked closed in master TP because no real proof bundle has been run through the new closure command yet
6. Probe on historical bundle:
   - `python3 ops/diagnose.py llm-quality-open-world-closure --matrix-summary /tmp/booking_quality/booking-matrix-20260216-a88/matrix_summary.json --deterministic-scenarios /tmp/booking_quality/p6-closure-probe-20260306-a1/ru.json --deterministic-scenarios /tmp/booking_quality/p6-closure-probe-20260306-a1/kk.json --deterministic-scenarios /tmp/booking_quality/p6-closure-probe-20260306-a1/mixed.json --deterministic-scenarios /tmp/booking_quality/p6-closure-probe-20260306-a1/mixed_translit.json --output /tmp/booking_quality/p6-closure-probe-20260306-a1/p6_open_world_closure.json --pretty`
   - current block reasons confirm master status remains `blocked`: missing cross-domain contract, missing failure-family artifact, missing scenario-context/run-integrity/invariant evidence, only one client row

## Rollback

1. revert closure command/docs if acceptance ownership changes

## No-go

- no closure on budget arguments alone
- no closure on deterministic generator alone
- no closure without machine-readable artifact output from the closure command
- no heavy acceptance stress on non-`demo_salon` packs/branches

## Risks/Blockers

1. remaining budget or runtime windows may delay the first real proof bundle
2. existing matrix evidence may still fail because closure is stricter than previous narrative checks

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - the actual proof bundle is still missing
- Why not in this block:
  - this block implements the closure gate; it does not fabricate runtime evidence
- Risk if deferred:
  - future agents could still over-claim `P6` closure without running the gate
- Linked follow-up Task Package(s):
  - `none`; the next step is to run the closure command on a real bundle
- Expiry/trigger to stop deferral:
  - before any claim that `P6` is closed

## Next-block contract (mandatory)

- Next block objective:
  - run `llm-quality-open-world-closure` on a real multi-pack proof bundle (dev/forensic matrix), then return to the frozen promotion chain (`P1.6/P1.7`) only if it passes; any heavy acceptance stress remains `demo_salon` only
- First deterministic check command:
  - `python3 ops/diagnose.py llm-quality-open-world-closure --matrix-summary /tmp/booking_quality/<matrix-run>/matrix_summary.json --deterministic-scenarios /tmp/booking_quality/<seed-ru>/scenarios.json --deterministic-scenarios /tmp/booking_quality/<seed-kk>/scenarios.json --deterministic-scenarios /tmp/booking_quality/<seed-mixed>/scenarios.json --deterministic-scenarios /tmp/booking_quality/<seed-translit>/scenarios.json --pretty`
- Blocked-by conditions:
  - missing or non-green matrix summary
  - missing deterministic profile coverage bundle
  - any closure reason returned by the command
- Owner role for closure:
  - `Top Architect + Brain`
