# TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-REASONING-DEGRADE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RUNTIME-CONTRACTS-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Подключить один bounded new-core slice прямо в `reasoning_core`: exception/degrade lane. Этот блок не меняет happy-path consultant routing, но перестаёт собирать runtime-exception fallback ad hoc строками и разношёрстной metadata-логикой. Вместо этого fallback lane будет собираться через `PolicyDecision` + `BoundaryOverride` + `DialogState` + `TurnResult`, а совместимость наружу сохранится через тот же `WebhookResponse`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,260p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,240p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1,240p' truffles-api/app/core/turn_planner.py`
  - `sed -n '1,240p' truffles-api/app/core/turn_executor.py`
- `FACT findings`:
  - `reasoning_core` still delegates the entire active path to `decision_router._handle_webhook_payload`.
  - The only code it owns today is the top-level exception fallback lane.
  - That fallback lane still assembles outcome ad hoc: plain strings, direct transport calls, and sparse `decision_meta` error fields, without using the new runtime contracts.
- `Detected drift (docs vs code)`: the repo already has executable runtime contracts, but the only slice owned by `reasoning_core` still does not use them.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_dump mode json nested models`
- **Date/time (local):** `2026-03-15 14:37 Asia/Almaty`
- **Why this query is precise:** this block needs one compatibility bridge from typed Pydantic runtime contracts into JSON-safe metadata without inventing a second serialization style.
- **Sources opened (from this query):**
  - `Pydantic serialization` — `https://docs.pydantic.dev/latest/concepts/serialization/`
  - `Pydantic models` — `https://docs.pydantic.dev/latest/concepts/models/`
- **Existing solutions found:** use `model_validate(...)` to coerce nested contract payloads into typed models and `model_dump(mode="json")` to serialize nested models back into JSON-safe metadata.
- **Decision:** `reuse + integrate` — reuse the existing Pydantic contract stack already introduced in `app/core/` and serialize compatibility metadata with `model_dump(mode="json")`.
- **Rejected options:**
  - ad hoc `dict(...)` assembly for nested contract artifacts
  - adding a parallel dataclass serialization layer
  - widening this block into a happy-path planner cutover
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `reasoning_core` owns the runtime exception lane, but that lane still bypasses the new runtime contracts entirely.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/reasoning_core.py`.
  2. Inspect `handle_webhook_payload(... )` exception flow.
  3. Observe that fallback transport and `WebhookResponse` are assembled directly, while no `PolicyDecision`, `BoundaryOverride`, `DialogState`, or `TurnResult` exists.
- **Evidence to capture:**
  - new-core artifact builder in `reasoning_core`
  - deterministic tests proving exception lane now round-trips through typed contracts
  - unchanged user-visible fallback responses
- **Five Whys (or equivalent):**
  1. Why is the new core still not executing any live slice? Because `reasoning_core` delegates everything and only owns the exception lane.
  2. Why is that lane a good first slice? Because it is bounded, deterministic, and already outside legacy router semantics.
  3. Why is the current implementation weak? Because it records only ad hoc error fields and string fallbacks, not a typed runtime artifact.
  4. Why does that matter? Because future agents still have no executable example of `reasoning_core` using the new contracts in production code.
  5. Why does this fix reduce drift? Because one live runtime lane will now be assembled by the new core contract stack and emit explicit degrade reason codes.
- **Root cause statement:** runtime contracts exist, but `reasoning_core` still owns zero live contract-driven execution lanes; the exception fallback path remains ad hoc and therefore keeps the new core detached from real runtime behavior.
- **Fix mechanism:**
  - build the exception/degrade lane through `TurnPlanner`, `BoundaryValidator`, `DialogStateService`, `ResponseRealizer`, and `TurnExecutor`
  - serialize a compatibility `turn_outcome` projection from that artifact for existing consumers
  - keep `WebhookResponse` and transport behavior unchanged

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/response_realizer.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/schemas/turn_outcome.py`
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Pydantic docs for `model_validate(...)` and `model_dump(mode="json")`
- **Why not reinvent the wheel:** the block needs a compatibility projection, not a second contract system.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is a small but real runtime integration block; code changes dominate, docs just keep canon truthful.

## Invariant
- No changes to legacy router happy-path semantics in `decision.py`, `booking.py`, or `pending.py`.
- `WebhookResponse` contract and fallback user-facing texts stay unchanged.
- New core usage is limited to the bounded exception/degrade lane.

## Scope
- Wire `reasoning_core` exception lane through the new core contract stack.
- Emit compatibility metadata from that typed artifact.
- Add deterministic tests for the new slice.
- Sync source-of-truth/session/state docs.

## Out of scope
- Happy-path planner cutover.
- Any semantic routing change inside `decision.py`.
- Continuity writer collapse beyond this bounded degrade slice.
- Multi-pack acceptance.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish the bounded degrade-slice TP.
2. Add typed helper(s) needed to synthesize a controlled degrade `PolicyDecision`/`DialogState` artifact.
3. Wire `reasoning_core` exception handling through the new core stack.
4. Preserve current transport + `WebhookResponse` behavior while emitting compatibility metadata.
5. Add deterministic tests for the new slice.
6. Re-run packet/architecture/runtime checks and sync state/session docs.

## DoD
- `reasoning_core` exception lane produces a typed `TurnResult` artifact through `app/core`.
- Existing fallback response texts and `WebhookResponse` behavior remain unchanged.
- Compatibility metadata is emitted from the typed artifact.
- Deterministic tests prove the new slice and keep existing fallback behavior green.
- Top-level source-of-truth points to this block as the active slice.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- typed degrade artifact in `reasoning_core`
- deterministic test output for the new slice
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires touching legacy router semantics or widening `WebhookResponse`, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded additive cutover inside `reasoning_core` exception path only
- **Go/no-go signals:** targeted tests + `py_compile` + packet + arch guard + session check all green
- **Rollback:** revert `reasoning_core` new-core exception helper changes only
- **Post-release monitoring window:** next block may wire a non-exception planner slice only after this lane remains deterministic and stable

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual block being executed.

## Rollback
- Revert this TP’s code/doc changes; retain previously landed governance and runtime-contract blocks.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No new regex/phrase routing in core files.
- No API shape change to `WebhookResponse`.
- No silent fallback path without explicit degrade reason code.

## Risks/Blockers
- Synthetic degrade `PolicyDecision` must stay clearly marked as degrade-path, not normal semantic ownership.
- Compatibility metadata must not poison existing success-path semantics.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: happy-path consultant semantics still live in the legacy router; continuity still has multiple writers outside this slice.
- `Why not in this block`: this block is intentionally limited to the exception/degrade lane.
- `Risk if deferred`: if no next planner slice follows, the new core remains mostly a bounded fallback island.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any next consultant-core behavior change on the happy path.

## Next-block contract (mandatory)
- `Next block objective`: cut one non-exception planner slice from `reasoning_core` into the new core while leaving legacy router as compatibility shim.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: degrade slice not green; no stable compatibility metadata; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: legacy router semantic branches in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: synthetic degrade semantics leaking into happy path, metadata drift, widening block scope
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
