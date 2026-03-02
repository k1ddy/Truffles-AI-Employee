# TP-2026-03-02-multi-seed-drift-gate-a1

- Название/цель: Enforce multi-seed drift evidence for acceptance chain. Goal: acceptance lock requires validated dev-lane evidence across required seeds (7/19/42 by default) to reduce stochastic drift risk and comply with P10.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md` (`P10 Canonical Quality Chain`).
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Root cause (mandatory)

- Symptom: Acceptance chain can be promoted with single-seed evidence; multi-seed drift is only advisory and not enforced.
- Minimal reproduction: Provide PG checklist with passing `PG0..PG6` + valid `l1_evidence` + `l2_evidence` from a single seed. Chain controller accepts it, enabling acceptance lock without multi-seed validation.
- Evidence:
  - `scripts/quality_chain_controller.sh` validates `PG0..PG6`, `l1_evidence`, `l2_evidence` only; no seed coverage check.
  - `ops/diagnose.py` writes `config.seed`, but no gate consumes it.
- Five Whys:
  1. Why can acceptance proceed with one seed? Because PG checklist validation does not require multi-seed evidence.
  2. Why doesn’t PG checklist require it? Multi-seed coverage was specified in TP P10 but not encoded in tooling.
  3. Why wasn’t it encoded? Initial focus was on chain ordering and gate fail-closed, not stochastic drift control.
  4. Why is drift control needed? LLM outputs vary by seed; single seed hides regressions.
  5. Why is this a blocker now? Acceptance is a release gate, and TP requires multi-seed evidence for contract metrics.
- Root cause statement: The acceptance go-to-full gate lacks deterministic enforcement of multi-seed evidence, so stochastic drift can pass undetected.
- Fix mechanism: Extend PG checklist validation to require `multi_seed_evidence` with required seeds and validated L2 summaries; add unit test coverage.

## One web search (mandatory before implementation)

- Query (exact): `python random seed reproducibility documentation`
- Date/time: `2026-03-02T02:34:37Z`
- Opened sources:
  - `https://docs.python.org/3/library/random.html#random.seed` (primary)
- Ready solutions found:
  - Deterministic reproducibility requires explicit seeding; seed must be recorded and validated to compare runs.
- Decision: `reuse/integrate`
  - Use existing `summary.config.seed` emitted by `ops/diagnose.py` and enforce multi-seed coverage in chain controller.
- Rejected options:
  - Adding a new runner or external drift service (overkill; existing chain controller + summaries suffice).

## Invariant

- Acceptance chain remains `lock -> replay -> full` with fail-closed gates.
- No relaxation of acceptance thresholds or quality lanes.
- Dev lane remains required; acceptance lane only after go-to-full passes.

## Scope

- Add multi-seed evidence validation to PG checklist (acceptance lock only).
- Require default seed set `{7,19,42}` unless explicitly overridden in checklist.
- Validate each seed summary is dev-lane, canonical (`infra_valid`, `semantic_valid`, `run_integrity_valid`), and fresh.
- Add deterministic unit tests for new validation logic.

## Out of scope

- Changes to LLM runtime or scenario generation logic.
- Adding new acceptance runner modes.
- Running expensive L3 chains.

## Touch-list

- `scripts/quality_chain_controller.sh`
- `truffles-api/tests/test_booking_quality_chain_controller.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/SESSIONS/SESSION-2026-02-19-llm-first-firebreak-a1.md`
- `docs/SESSION_INDEX.md`

## Plan

1. Extend PG checklist schema to include `multi_seed_evidence`.
2. Implement validation: required seeds, summary presence, seed match, canonical + dev-lane, freshness.
3. Add unit tests for pass and fail cases.
4. Update parent TP execution status after implementation.

## DoD

- Acceptance lock fails when multi-seed evidence is missing or incomplete.
- Validation passes with required seeds and canonical dev-lane summaries.
- Unit tests cover at least one success and one failure path.

## Checks

- `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py`

## Evidence

- Test output for the above.
- Updated parent TP execution status for `P10`.
 - `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py` (`15 passed`).

## Rollback

- Revert commit(s) that add multi-seed validation and tests.

## No-go

- Do not add new runtime logic or change acceptance thresholds.
- Do not allow acceptance to bypass PG checklist.

## Release safety

- Rollout: merge to main after tests pass.
- Go/no-go: tests green; no changes to runtime behavior.
- Rollback: revert commit if gate blocks critical workflows.

## Риски/блокеры

- Existing acceptance workflows without multi-seed evidence will be blocked until checklist is updated.
