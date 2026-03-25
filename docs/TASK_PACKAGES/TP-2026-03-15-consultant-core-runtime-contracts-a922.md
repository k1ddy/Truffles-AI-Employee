# TP-2026-03-15-consultant-core-runtime-contracts-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-RUNTIME-CONTRACTS-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-GOVERNANCE-LOCK-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-governance-lock-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEW-RUNTIME-SLICE-A922`

## Название/цель
Материализовать целевой consultant runtime contract в versioned JSON Schema и минимальном `app/core` scaffolding, не меняя активный runtime path. После этого следующий block сможет переводить один bounded slice на новый core уже не в narrative, а на typed contract basis.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `contracts/runtime/`
  - `truffles-api/app/core/`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STRUCTURE.md`
  - `STATE.md`
- `Baseline commands`:
  - `test -d contracts/runtime || echo missing:contracts/runtime`
  - `find truffles-api/app -maxdepth 2 -type d | rg '/core$' || true`
  - `sed -n '1,220p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,220p' contracts/policy/interaction_owner_matrix.v1.jsonschema`
  - `sed -n '1,220p' truffles-api/app/services/interaction_owner_matrix_service.py`
  - `sed -n '1,220p' truffles-api/app/schemas/turn_outcome.py`
- `FACT findings`:
  - governance docs now point to target runtime files under `contracts/runtime/` and `truffles-api/app/core/`, but those files do not exist yet.
  - current runtime still enters through `truffles-api/app/services/reasoning_core.py`, which is a thin wrapper over legacy router code; there is no parallel typed core package yet.
  - repo already has good schema-validation and typed-contract patterns (`contracts/policy/interaction_owner_matrix.v1.jsonschema`, `interaction_owner_matrix_service.py`, `TurnOutcome`), so this block should reuse those patterns instead of inventing a new contract style.
- `Detected drift (docs vs code)`: top-level source-of-truth already names runtime contracts and core modules as targets, but the repo still lacks the actual files.

## One web search (mandatory before implementation)
- **Query (exact):** `site:json-schema.org understanding json schema references defs additionalproperties required`
- **Date/time (local):** `2026-03-15 14:34 Asia/Almaty`
- **Why this query is precise:** this block is specifically about versioned JSON Schema design for reusable runtime contracts. The narrow question is how to structure strict object contracts with `$id`, `$defs`, enums, and closed-object validation without adding a new schema style.
- **Sources opened (from this query):**
  - `JSON Schema / object` — `https://json-schema.org/understanding-json-schema/reference/object`
  - `JSON Schema / Modular JSON Schema combination` — `https://json-schema.org/understanding-json-schema/structuring`
  - `JSON Schema / Enumerated values` — `https://json-schema.org/understanding-json-schema/reference/enum`
- **Existing solutions found:** use absolute `$id` identifiers, factor reusable shapes through `$defs`/`$ref`, use `enum`/`const` to freeze small taxonomies, and keep contract objects closed with `additionalProperties: false` where the schema is canonical.
- **Decision:** `reuse + integrate` — reuse the repo’s current Draft 2020-12 schema/test pattern and integrate the new runtime contracts into that existing discipline.
- **Rejected options:**
  - ad hoc unversioned JSON examples without schemas
  - putting the runtime contract only into Pydantic models without JSON Schema artifacts
  - cutting runtime over before contract artifacts exist
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** top-level governance now points to `PolicyDecision`, `DialogState`, `BoundaryOverride`, and `TurnResult`, but the repo still lacks the actual contract artifacts and core package they refer to.
- **Minimal reproduction:**
  1. `test -d contracts/runtime || echo missing`
  2. `find truffles-api/app -maxdepth 2 -type d | rg '/core$' || true`
  3. `sed -n '1,220p' truffles-api/app/services/reasoning_core.py`
  4. `sed -n '1,220p' docs/SOURCE_OF_TRUTH.yaml`
- **Evidence to capture:**
  - new contract schemas under `contracts/runtime/`
  - new scaffolding under `truffles-api/app/core/`
  - deterministic contract tests
  - updated source-of-truth/structure/state/session docs
- **Five Whys (or equivalent):**
  1. Why can the next runtime block still drift? Because the target runtime contract is named but not materialized.
  2. Why is that dangerous? Because the next implementation block could still improvise field names, ownership boundaries, and result shapes.
  3. Why not go straight to runtime cutover? Because without contracts, the cutover would again be documentary and branch-local.
  4. Why is this block bounded enough? Because it creates schemas and typed scaffolding without changing active behavior.
  5. Why does this reduce future agent drift? Because the next agent gets concrete files and types instead of only prose.
- **Root cause statement:** consultant controlled demolition has governance now, but it still lacks the concrete runtime contract artifacts and typed core skeleton needed to constrain the next migration step.
- **Fix mechanism:**
  - create versioned runtime schemas for `PolicyDecision`, `DialogState`, `BoundaryOverride`, and `TurnResult`
  - create minimal `app/core` typed scaffolding aligned with those schemas
  - add deterministic schema/model tests before any runtime cutover

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `contracts/policy/interaction_owner_matrix.v1.jsonschema`
  - `truffles-api/app/services/interaction_owner_matrix_service.py`
  - `truffles-api/app/schemas/turn_outcome.py`
  - provider/schema tests that already validate Draft 2020-12 contracts
- **External reuse:**
  - official JSON Schema docs for `$id`, `$defs`, `enum`, and closed object design
- **Why not reinvent the wheel:** the repo already has a contract-validation stack; this block should extend it, not fork it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** the block must ship real contracts and code scaffolding, but still stay non-behavioral.

## Invariant
- No active consultant runtime cutover in this block.
- No semantic behavior changes in the legacy router path.
- New contracts must be truthful about current vs target status.

## Scope
- Add `contracts/runtime/*.jsonschema`.
- Add minimal `truffles-api/app/core/` scaffolding aligned with those contracts.
- Add deterministic schema/model tests.
- Sync top-level source-of-truth docs to those new files.

## Out of scope
- Wiring `reasoning_core` to the new core.
- New runtime slice migration.
- Multi-pack acceptance.
- Proof-lane reruns.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `contracts/runtime/dialog_state.v1.jsonschema`
- `contracts/runtime/boundary_override.v1.jsonschema`
- `contracts/runtime/turn_result.v1.jsonschema`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`

## Plan (1..N)
1. Publish the bounded runtime-contract TP.
2. Create the four versioned runtime schemas.
3. Create minimal typed core scaffolding matching those contracts.
4. Add deterministic schema/model tests.
5. Re-run governance and contract checks.
6. Sync state/session/structure docs.

## DoD
- `contracts/runtime/*.jsonschema` exist and validate example payloads.
- `truffles-api/app/core/` exists with importable typed scaffolding.
- Deterministic contract tests are green.
- `docs/SOURCE_OF_TRUTH.yaml` target paths now point to real files.
- No active runtime behavior changed.

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/arch_guard.py`
- `python3 -m py_compile truffles-api/app/core/__init__.py truffles-api/app/core/turn_planner.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/response_realizer.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- new schema files
- new `app/core` files
- green deterministic contract test output
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the contract shapes cannot stay small, typed, and non-behavioral, stop and split before touching runtime entrypoints
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive non-behavioral contract/scaffolding block only
- **Go/no-go signals:** contract tests, `py_compile`, `arch_guard`, `git diff --check`, `session_check` all green
- **Rollback:** revert runtime-contract schema/scaffolding files only
- **Post-release monitoring window:** next block may wire only one bounded runtime slice after rerunning `arch_guard` + contract tests

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `Drift closeout rule`:
  - if a target path is named in source-of-truth, it must exist by the end of this block.

## Rollback
- Revert new contract/scaffolding files and related doc sync.

## No-go
- No hidden cutover in `reasoning_core.py`.
- No changes to legacy router semantics.
- No placeholder contracts that do not cover the fields already frozen by canon.

## Risks/Blockers
- Contract shapes can sprawl if they try to encode the whole runtime at once.
- Scaffolding must stay clearly non-authoritative until the next cutover block.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: runtime still executes through legacy router; new core is scaffolding only.
- `Why not in this block`: cutover belongs to the next bounded migration block.
- `Risk if deferred`: without immediate next slice migration, new contracts remain unused structure.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-new-runtime-slice-a922`
- `Expiry/trigger to stop deferral`: before any new consultant-core behavior change.

## Next-block contract (mandatory)
- `Next block objective`: wire one bounded consultant slice from `reasoning_core` into the new core path behind the new runtime contracts.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Blocked-by conditions`: runtime contracts missing; core scaffolding missing; deterministic contract tests not green.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: legacy router semantics in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: contract overscope, accidental behavior changes, making scaffolding look like cutover
- `First command to verify`: `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
