# TP-2026-03-27-consultant-core-workstream1-planner-synthetic-authority-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-F4-planner-synthetic-authority-cut`
- `PARENT_BLOCK_ID`: `WS1-F3-executor-semantic-output-constriction`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-executor-semantic-output-constriction-a922.md`
- `UNLOCKS`: `WS1-F5-owner-adjacent-legacy-shadow-cut`

## Название/цель
Убрать planner-side synthetic semantic minting из runtime core и формально зафиксировать, что canaried runtime принимает либо canonical `SemanticDecisionV1`, либо explicit boundary/degrade/preflight decisions.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/__init__.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/`
- `Baseline commands`:
  - `rg -n "build_from_policy_override\(|build_controlled_degrade\(|build_preflight_reject\(" truffles-api/app truffles-api/tests`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "policy_override or synthetic_policy_decision or preflight_reject or controlled_degrade"`
- `FACT findings`:
  - `build_from_policy_override(...)` still lives inside `truffles-api/app/core/turn_planner.py` and can mint semantic-looking `PolicyDecision` objects without canonical owner output, even though no production app caller currently uses it.
  - Live runtime callers of synthetic planner builders are limited to explicit boundary/degrade/preflight decisions: `TurnPlanner.plan(...)`, `ConsultantRuntime._plan_turn(...)`, and `TurnExecutor` boundary artifact helpers.
  - The semantic authority problem is now concentrated in runtime-core availability of a synthetic semantic builder, not in a currently live hot-path call site.
- `Detected drift (docs vs code)`: `present`
  - Workstream 1 completion requires exactly one `SemanticDecisionV1` per canaried turn and legacy owner-adjacent paths to be shadow-only or deleted, but `turn_planner.py` still contains a general-purpose synthetic semantic builder.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_validator after docs`
- **Date/time (local):** `2026-03-27 11:36 +05`
- **Why this query is precise:** This block may need a cross-field contract guard on `PolicyDecision` shape, so the primary-source question is whether Pydantic `model_validator(mode="after")` is the right enforcement mechanism.
- **Sources opened (from this query):**
  - `Pydantic docs / Dataclasses - Validation`: `https://docs.pydantic.dev/latest/concepts/dataclasses/`
- **Source quality:** Pydantic official docs (primary source).
- **Existing solutions found:** Pydantic `model_validator(mode="after")` can enforce cross-field invariants after object construction.
- **Decision:** `reject` for this block — a global model-level validator would over-constrain explicit boundary/test-support decisions; the narrower cut is to remove synthetic semantic minting from runtime core and add runtime-path enforcement for canonical owner vs explicit boundary-only synthetic outcomes.
- **Rejected options:**
  - Global `PolicyDecision` validator forbidding all non-owner decisions: rejected because explicit degrade/preflight/block decisions are legitimate typed exceptions.
  - Leave `build_from_policy_override(...)` in planner core and rely on convention: rejected because the authority-bearing helper remains available in the runtime core surface.

## Root cause (mandatory)
- **Symptom:** `turn_planner.py` still contains a general synthetic semantic builder that can mint semantic-looking `PolicyDecision` artifacts without canonical owner output.
- **Minimal reproduction:**
  - `rg -n "def build_from_policy_override|synthetic_policy_decision" truffles-api/app/core/turn_planner.py`
  - `rg -n "build_from_policy_override\(" truffles-api/app truffles-api/tests`
- **Evidence to capture:**
  - removal/quarantine of planner synthetic semantic builder from runtime core
  - deterministic tests proving canaried runtime rejects synthetic non-boundary decisions without `semantic_decision`
  - deterministic tests proving legacy test/support compatibility can still construct needed fixtures outside runtime core
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still open after Families 1-3? Because planner core still exposes a synthetic semantic decision builder.
  2. Why is that a problem if app code does not call it today? Because authority remains in runtime core and can be reintroduced onto the hot path without crossing a boundary.
  3. Why does that matter now? Because Workstream 1 is about deleting old semantic authority, not only redirecting current callers.
  4. Why not solve this later in planner/executor demotion? Because Workstream 1 completion explicitly requires one owner and shadow-only/deleted owner-adjacent paths first.
  5. Why not use a global `PolicyDecision` schema validator? Because explicit degrade/preflight/block decisions are allowed typed exceptions and should not be collapsed into the same rule.
- **Root cause statement:** Planner core still owns a general synthetic semantic minting capability (`build_from_policy_override(...)`), so canonical owner exclusivity is not yet structurally enforced even though current runtime callers mostly avoid that helper.
- **Fix mechanism:** remove synthetic semantic minting from runtime core, move test-only compatibility construction to test support, and add a canaried runtime guard that degrades if a synthetic non-boundary decision reaches the active runtime path without `semantic_decision`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse `TurnPlanner.build_from_semantic_decision(...)` as the only planner semantic constructor in runtime core.
  - Reuse existing `synthetic_policy_decision`, `degrade_path`, and `preflight_path` flags for runtime-path classification rather than inventing a second flag system.
  - Reuse existing `TurnPlanner` normalization helpers inside test-support compatibility builders.
- **External reuse:**
  - Pydantic validator docs were evaluated and intentionally not used for this narrower authority cut.
- **Why not reinvent the wheel:** The needed runtime signals and canonical constructor already exist; this block is about deleting the wrong constructor from runtime core.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** This is a planner-core authority removal plus deterministic guard/test move, not a broad subsystem rewrite.

## Invariant
- Canaried runtime must accept either canonical `SemanticDecisionV1` decisions or explicit boundary/degrade/preflight decisions only.
- No general semantic-looking decision may be minted inside runtime core without `semantic_decision`.
- Explicit degrade/handoff/preflight paths remain typed, reason-coded, and observable.
- Test/support compatibility fixtures may exist, but they must not sit in runtime core.

## Scope
- Remove `build_from_policy_override(...)` from `truffles-api/app/core/turn_planner.py`.
- Move needed compatibility fixture construction into test support.
- Add runtime guard that degrades if a non-boundary synthetic decision without `semantic_decision` reaches the canaried runtime path.
- Add focused regressions and a small architecture/runtime-core guard for the removed planner authority.
- Update repo truth/docs for the removed authority.

## Out of scope
- Deleting explicit `build_controlled_degrade(...)` / `build_preflight_reject(...)` boundary builders.
- Binding extraction.
- Full legacy mesh strangler.
- Turn journal / conversation projection cutover.

## Touch-list
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/__init__.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-planner-synthetic-authority-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Remove the synthetic semantic builder from planner core and add test-support replacement for deterministic fixtures.
2. Add a canaried runtime guard that rejects synthetic non-boundary decisions without `semantic_decision`.
3. Update deterministic tests and add a small architecture/runtime-core guard for the removed planner authority.
4. Run bounded checks, then update `STATE.md` / `STRUCTURE.md` truthfully.

## DoD
- `turn_planner.py` no longer contains a general synthetic semantic builder.
- Canaried runtime degrades explicitly if a synthetic non-boundary decision without `semantic_decision` reaches `_plan_turn(...)` or equivalent active runtime path.
- Test/support fixture construction still works outside runtime core.
- Deterministic tests prove the authority cut and explicit degrade behavior.

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/__init__.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "policy_override or synthetic_policy_decision or preflight_reject or controlled_degrade"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "policy_override or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- Code diff removing planner synthetic semantic builder from runtime core.
- Runtime/test evidence showing synthetic non-boundary decisions now degrade explicitly on canaried path.
- Truthful `STATE.md` entry naming exactly which planner authority was removed and what remains.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic-only in this family; no open-ended quality replay loop.
- **Stop condition:** if two code/test iterations fail without new authority-reduction evidence, stop and reopen RCA.
- **Escalation path:** `Brain / Top Architect` for any extra long realism or acceptance runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local canary only in this worktree; no production rollout in this block.
- **Go/no-go signals:** planner core no longer exposes general synthetic semantic minting; runtime degrades explicit synthetic non-boundary decisions; focused tests pass.
- **Rollback:** revert planner-core deletion, runtime guard, and corresponding test-support changes together.
- **Post-release monitoring window:** local deterministic regression pass for this block only.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `STRUCTURE.md`
  - this TP with implementation evidence
- `Drift closeout rule`:
  - if runtime core still contains any non-boundary synthetic semantic builder after this block, record that exact surface as residual debt.

## Rollback
- Revert planner-core synthetic builder removal, runtime guard, and the deterministic test-support migration together.

## No-go
- No new semantic builder hidden under a renamed planner helper.
- No weakening of explicit degrade/preflight semantics.
- No moving synthetic semantic authority from planner core into executor/runtime core.
- No binding extraction in this block.

## Risks/Blockers
- A large number of deterministic tests currently rely on planner-side synthetic fixture construction.
- Some test fixtures may depend on exact legacy `semantic_contract` / `pending_question_contract` shape and will need faithful support helpers.
- Over-tightening the runtime guard could accidentally block explicit boundary/degrade paths.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: explicit degrade/preflight synthetic decisions still exist on the hot path as typed boundary outcomes; legacy owner-adjacent compatibility mesh remains; full shadow-only/delete closure is not complete.
- `Why not in this block`: this family is limited to removing planner-core general synthetic semantic minting and enforcing the canaried runtime distinction.
- `Risk if deferred`: planner core would continue shipping a general semantic minting capability even after owner/state/executor cuts.
- `Linked follow-up Task Package(s)`: `WS1-F5-owner-adjacent-legacy-shadow-cut` (to be authored after this block lands).
- `Expiry/trigger to stop deferral`: if any other planner/runtime core helper can mint semantic-looking decisions without `semantic_decision` after this block, the next block must target it before Workstream 2 starts.

## Next-block contract (mandatory)
- `Next block objective`: convert remaining owner-adjacent legacy compatibility surfaces to shadow-only/delete status now that planner core no longer exposes general synthetic semantic minting.
- `First deterministic check command`: `rg -n "semantic_decision_required|synthetic_policy_decision|semantic_contract" truffles-api/app/core truffles-api/app/routers/webhook`
- `Blocked-by conditions`: planner core still contains a general synthetic semantic builder, or canaried runtime still proceeds with a non-boundary synthetic decision lacking `semantic_decision`.
- `Owner role for closure`: `Brain / Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `no`
- `Start from`: `truffles-api/app/core/turn_planner.py`
- `Do not touch`: `explicit boundary/degrade/preflight semantics beyond the runtime guard classification needed in this block`
- `Open risks`: `test fixture migration volume`, `boundary path false positives`, `legacy compatibility payload shape`
- `First command to verify`: `rg -n "build_from_policy_override|synthetic_policy_decision" truffles-api/app/core/turn_planner.py truffles-api/tests`


## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `turn_planner.py` no longer ships a general synthetic semantic builder; runtime-core semantic construction now goes through `build_from_semantic_decision(...)` or explicit boundary/degrade/preflight paths only.
  - `consultant_runtime.py` now degrades if a non-boundary decision without `semantic_decision` reaches the canaried runtime path.
  - test/support compatibility fixture construction moved out of runtime core into `truffles-api/tests/__init__.py`.
- `Files touched`:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/__init__.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/__init__.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "policy_override or synthetic_policy_decision or preflight_reject or controlled_degrade"` -> `2 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "policy_override or semantic_contract or pending_question_contract"` -> `5 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `65 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py` -> `80 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `24 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - added runtime regression proving synthetic non-boundary decisions without `semantic_decision` now degrade explicitly on the canaried runtime path.
  - added architecture guard proving `turn_planner.py` no longer contains `build_from_policy_override`.
  - updated deterministic fixtures to use test-support compatibility builders instead of runtime-core planner minting.
- `Realistic/local behavior checks`:
  - not run in this bounded family; no `llm-quality` acceptance run was part of this block.
- `Authority removed`:
  - planner core no longer contains a general-purpose semantic-looking decision minting helper outside canonical owner construction.
- `Residual debt left for next block`:
  - explicit degrade/preflight synthetic decisions still exist as typed boundary outcomes on the hot path.
  - owner-adjacent legacy compatibility surfaces are still not shadow-only/delete and remain the next Workstream 1 target.
