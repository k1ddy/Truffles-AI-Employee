# TP-2026-03-27-consultant-core-workstream1-owner-adjacent-shadow-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-F5-owner-adjacent-shadow-cut`
- `PARENT_BLOCK_ID`: `WS1-F4-planner-synthetic-authority-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-planner-synthetic-authority-cut-a922.md`
- `UNLOCKS`: `WS1-F6-workstream1-closeout-check`

## Название/цель
Сделать owner-adjacent compatibility carriers на canaried `PolicyDecision` shadow-only: при наличии `SemanticDecisionV1` semantic смысл должен читаться только из canonical owner artifact, а не из `decision.semantic_frame`, `decision.pending_question_contract`, `decision.meta.semantic_contract`.

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
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
- `Baseline commands`:
  - `rg -n "decision\.semantic_frame|decision\.pending_question_contract|decision\.meta\.get\(\"semantic_contract\"\)" truffles-api/app/core`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_frame or semantic_contract or pending_question_contract"`
- `FACT findings`:
  - `build_from_semantic_decision(...)` still stores semantic meaning into `decision.semantic_frame`, `decision.pending_question_contract`, and `decision.meta["semantic_contract"]` even though canonical accessors already derive the same meaning from `SemanticDecisionV1`.
  - `dialog_state_service.py` and `turn_executor.py` still contain fallback reads of those carriers in owner-backed paths, so the compatibility fields are not shadow-only yet.
  - post-owner mutation guard exists, but before this block it still treated populated owner-adjacent carriers as the expected state instead of shadow debt.
- `Detected drift (docs vs code)`: `present`
  - Workstream 1 says `SemanticDecisionV1` must be the only hot-path meaning artifact, but canaried `PolicyDecision` still transports three compatibility meaning carriers.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_copy docs`
- **Date/time (local):** `2026-03-27 12:02 +05`
- **Why this query is precise:** This block may need to reshape Pydantic models while keeping typed defaults/updates stable on the compatibility-shadow path.
- **Sources opened (from this query):**
  - `Pydantic BaseModel API`: `https://docs.pydantic.dev/dev/api/base_model/`
- **Source quality:** Pydantic official docs (primary source).
- **Existing solutions found:** `BaseModel.model_copy(...)` is available for typed cloning/updates, but the block can stay simpler by constructing the desired shadow/default fields directly.
- **Decision:** `reject` for this block — no `model_copy(...)` helper is needed; direct constructor/default-field usage is enough for the authority cut.
- **Rejected options:**
  - Use `model_copy(update=...)` to preserve populated compatibility carriers and clone trimmed versions: rejected because the block should stop minting those carriers in the first place.
  - Keep populated carriers and rely on canonical accessors only: rejected because owner-adjacent truth carriers would remain live on the canaried path.

## Root cause (mandatory)
- **Symptom:** Canaried `PolicyDecision` still carries semantic meaning in multiple compatibility fields besides `semantic_decision`.
- **Minimal reproduction:**
  - `rg -n "semantic_frame|pending_question_contract|semantic_contract" truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py`
  - build a decision through `TurnPlanner.build_from_semantic_decision(...)` and inspect `decision.semantic_frame`, `decision.pending_question_contract`, and `decision.meta`
- **Evidence to capture:**
  - owner-backed `PolicyDecision` now ships shadow-only compatibility fields
  - downstream readers continue to use canonical accessors and runtime behavior remains stable
  - mutation guard now flags repopulation of owner-adjacent carriers as a violation
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still not at one meaning artifact? Because `PolicyDecision` still stores semantic meaning in compatibility fields alongside `semantic_decision`.
  2. Why is that a problem? Because those fields remain peer-readable truth carriers and keep semantic authority fragmented.
  3. Why does that matter if canonical accessors exist? Because live compatibility carriers can still be read or repopulated without crossing a guard boundary.
  4. Why not postpone this to state unification? Because Workstream 1 completion already requires legacy owner-adjacent paths to become shadow-only or deleted.
  5. Why is a bounded cut possible now? Because planner/runtime/executor already have canonical accessors and the previous blocks removed the major downstream rewrites.
- **Root cause statement:** Owner-backed `PolicyDecision` still embeds compatibility semantic carriers as first-class payloads, so `SemanticDecisionV1` is not yet the only hot-path meaning artifact even though canonical accessors exist.
- **Fix mechanism:** stop populating owner-adjacent compatibility carriers on `build_from_semantic_decision(...)`, make downstream core readers use canonical accessors for owner-backed decisions, and treat repopulation of those carriers as a post-owner mutation violation.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse `TurnPlanner.canonical_semantic_frame(...)`, `TurnPlanner.canonical_pending_question_contract(...)`, and `TurnPlanner.canonical_semantic_contract(...)`.
  - Reuse existing owner-detection helpers in `DialogStateService`.
  - Reuse the existing post-owner mutation guard rather than introducing a second guard path.
- **External reuse:**
  - Pydantic `BaseModel` API was evaluated and intentionally not needed beyond direct defaults/constructors.
- **Why not reinvent the wheel:** Canonical derivation logic already exists; the block only needs to stop shipping parallel carriers and clean remaining runtime reads.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** This is a bounded authority cut across planner/runtime/executor readers, not a broader state/journal migration.

## Invariant
- If `semantic_decision` exists, meaning is read from it only.
- Compatibility carriers may remain structurally present in typed models, but they must be shadow-only on canaried owner-backed decisions.
- Explicit degrade/preflight/block decisions remain typed exceptions.
- No hidden semantic fallback may be reintroduced in runtime core.

## Scope
- Stop populating owner-backed `decision.semantic_frame`, `decision.pending_question_contract`, and `decision.meta["semantic_contract"]`.
- Update runtime/state/executor readers to use canonical owner accessors on that path.
- Update mutation guard and deterministic tests for shadow-only carriers.
- Update repo truth/docs.

## Out of scope
- Binding extraction.
- `TurnJournalV1` / `ConversationProjectionV1` cutover.
- Deleting explicit boundary/degrade/preflight synthetic decisions.
- Full legacy mesh strangler.

## Touch-list
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-owner-adjacent-shadow-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Make `build_from_semantic_decision(...)` emit shadow-only compatibility carriers.
2. Update core readers to use canonical owner accessors on the canaried path.
3. Tighten the mutation guard and deterministic tests around repopulated owner-adjacent carriers.
4. Run bounded checks, then update `STATE.md` / `STRUCTURE.md` truthfully.

## DoD
- Owner-backed `PolicyDecision` no longer carries populated `semantic_frame`, `pending_question_contract`, or `meta.semantic_contract`.
- Core runtime/state/executor behavior still reads canonical owner meaning correctly.
- Post-owner mutation guard flags repopulated compatibility carriers.
- Deterministic tests prove the cut.

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_frame or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- Code diff showing owner-backed decisions now ship shadow-only compatibility carriers.
- Deterministic regressions showing runtime/state/executor still work through canonical owner accessors.
- Truthful `STATE.md` entry naming exactly which owner-adjacent carriers were demoted.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic-only in this family; no open-ended quality replay loop.
- **Stop condition:** if two code/test iterations fail without new authority-reduction evidence, stop and reopen RCA.
- **Escalation path:** `Brain / Top Architect` for any extra long realism or acceptance runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local canary only in this worktree; no production rollout in this block.
- **Go/no-go signals:** owner-backed compatibility carriers are shadow-only; runtime/state/executor still read canonical meaning; focused tests pass.
- **Rollback:** revert planner output shadowing, reader changes, and mutation/test updates together.
- **Post-release monitoring window:** local deterministic regression pass for this block only.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `STRUCTURE.md`
  - this TP with implementation evidence
- `Drift closeout rule`:
  - if owner-backed runtime core still reads populated compatibility carriers after this block, record the exact remaining reader as residual debt.

## Rollback
- Revert owner-backed compatibility shadowing, the reader updates, and the guard/test changes together.

## No-go
- No new semantic fallback hidden in `meta` keys.
- No moving owner-adjacent semantic authority into binding/executor helpers.
- No claim that Workstream 1 is fully done in this block.
- No binding/state-journal expansion in this block.

## Risks/Blockers
- Some deterministic tests currently assert compatibility carrier contents directly.
- A few runtime helpers still read carrier fields directly and must be updated together.
- The mutation guard must not start flagging legitimate explicit boundary/degrade decisions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: explicit boundary/degrade/preflight synthetic decisions still exist; legacy compatibility mesh outside runtime core still remains; Workstream 1 closeout proof is still pending.
- `Why not in this block`: this family is limited to making owner-backed compatibility carriers shadow-only.
- `Risk if deferred`: `SemanticDecisionV1` would remain only one of several hot-path meaning carriers.
- `Linked follow-up Task Package(s)`: `WS1-F6-workstream1-closeout-check` (to be authored after this block lands).
- `Expiry/trigger to stop deferral`: if owner-backed decisions still transport populated semantic compatibility carriers after this block, Workstream 2 must not start.

## Next-block contract (mandatory)
- `Next block objective`: perform Workstream 1 closeout check and target any remaining owner-adjacent legacy runtime readers or shadow-only violations before Workstream 2 begins.
- `First deterministic check command`: `rg -n "semantic_decision|semantic_frame|pending_question_contract|semantic_contract" truffles-api/app/core truffles-api/app/routers/webhook`
- `Blocked-by conditions`: owner-backed decisions still emit populated compatibility carriers, or canonical runtime behavior breaks after the cut.
- `Owner role for closure`: `Brain / Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `no`
- `Start from`: `truffles-api/app/core/turn_planner.py`
- `Do not touch`: `boundary/degrade/preflight exception paths beyond what is needed to preserve their typed behavior`
- `Open risks`: `direct carrier assertions in tests`, `runtime helper fallbacks`, `mutation-guard false positives`
- `First command to verify`: `rg -n "decision\.semantic_frame|decision\.pending_question_contract|decision\.meta\.get\(\"semantic_contract\"\)" truffles-api/app/core`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - owner-backed `PolicyDecision` instances now keep `semantic_frame`, `pending_question_contract`, and `meta.semantic_contract` as shadow-only compatibility fields instead of populated meaning carriers.
  - runtime/state/executor readers now derive semantic contract and pending-question semantics from canonical owner accessors on the canaried path.
  - post-owner mutation guard now treats repopulated owner-adjacent compatibility carriers as a semantic mutation violation.
- `Files touched`:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_frame or semantic_contract or pending_question_contract"` -> `8 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract"` -> `7 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `67 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py` -> `80 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `24 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - added regression proving owner-backed planner output now keeps owner-adjacent compatibility carriers shadow-only while canonical accessors still project semantic meaning.
  - added regression proving post-owner mutation guard fires when those shadow carriers are repopulated.
  - updated runtime/state tests to assert canonical owner reads instead of direct populated compatibility carriers on the canaried path.
- `Realistic/local behavior checks`:
  - not run in this bounded family; no `llm-quality` acceptance run was part of this block.
- `Authority removed`:
  - canaried `PolicyDecision` is no longer a multi-carrier semantic payload; `SemanticDecisionV1` is now the single hot-path meaning source on that decision path.
- `Residual debt left for next block`:
  - explicit boundary/degrade/preflight synthetic decisions still exist as typed exceptions.
  - remaining Workstream 1 closeout debt is to scan for any owner-adjacent legacy runtime readers or shadow-only violations outside the touched core path before Workstream 2 starts.
