# TP-2026-03-15-consultant-core-empty-message-planner-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-EMPTY-MESSAGE-PLANNER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-REASONING-DEGRADE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NONEXCEPTION-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Вырезать первый non-exception planner slice в `reasoning_core`: empty-message preflight. Пустой inbound без текста и без media больше не должен доходить до legacy router по разным entrypoint’ам. Этот slice будет собираться через new-core planner/boundary/executor и возвращать тот же внешний `WebhookResponse(message="Empty message")` без изменения legacy router semantics.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/routers/webhook/http.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,260p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '220,280p' truffles-api/app/routers/webhook/http.py`
  - `sed -n '1,260p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1,220p' truffles-api/app/core/turn_planner.py`
- `FACT findings`:
  - `reasoning_core` already owns one live new-core slice: runtime exception degrade.
  - Non-exception traffic still delegates wholesale to `decision_router._handle_webhook_payload`.
  - Empty-message rejection already exists in `webhook/http.py` preflight, but not in other reasoning-core entrypoints (`message`, `decision_core`, `provider_gateway` after translation). That means the same invalid inbound can still reach the legacy router depending on entrypoint.
- `Detected drift (docs vs code)`: new-core planner/boundary/executor exist, but deterministic non-exception preflight is still inconsistent across entrypoints.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic field_validator before strip string`
- **Date/time (local):** `2026-03-15 14:54 Asia/Almaty`
- **Why this query is precise:** this block needs one typed normalization seam for inbound preflight selection, specifically string trimming and normalization before planner-slice selection.
- **Sources opened (from this query):**
  - `Pydantic validators` — `https://docs.pydantic.dev/latest/concepts/validators/`
  - `Pydantic models` — `https://docs.pydantic.dev/latest/concepts/models/`
- **Existing solutions found:** use `field_validator(..., mode="before")` to normalize/trim raw string inputs before model coercion and keep the planner-slice decision on typed normalized fields instead of ad hoc string handling scattered across callers.
- **Decision:** `reuse + integrate` — reuse the current Pydantic-based core contract stack and add one typed inbound normalization model for the preflight planner slice.
- **Rejected options:**
  - duplicating raw `strip()` checks separately in every router
  - expanding this block into generic media normalization
  - touching `decision.py` to solve the issue there
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** empty-message rejection is inconsistent across entrypoints; some paths reject before runtime, others still delegate invalid empty inbound into the legacy router.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/http.py` preflight for `reason="empty_message"`.
  2. Inspect `truffles-api/app/services/reasoning_core.py` and confirm it delegates every non-exception inbound to `decision_router._handle_webhook_payload`.
  3. Observe there is no shared planner slice for empty inbound.
- **Evidence to capture:**
  - new typed inbound normalization/planner helper
  - deterministic tests proving empty text without media is rejected before delegation
  - deterministic tests proving media-without-text still delegates
- **Five Whys (or equivalent):**
  1. Why is non-exception cutover still weak? Because only the exception lane uses the new core.
  2. Why pick empty-message preflight? Because it is deterministic, bounded, and already canonized in one entrypoint.
  3. Why is current behavior risky? Because invalid inbound handling depends on which router called `reasoning_core`.
  4. Why not fix this in the legacy router? Because the goal is to remove semantic/preflight ownership from the legacy path, not add more there.
  5. Why does this reduce drift? Because one shared contract-driven preflight slice will make invalid empty inbound behavior consistent before legacy delegation.
- **Root cause statement:** empty-message rejection lives in one caller-specific preflight instead of one shared reasoning-core planner slice, so invalid inbound handling still depends on entrypoint and still bypasses the new core.
- **Fix mechanism:**
  - add typed inbound normalization for slice selection
  - build a new-core blocked `TurnResult` for empty non-media inbound
  - return the same external `WebhookResponse(success=False, message="Empty message")` without delegating to the legacy router

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py` as current behavior reference
- **External reuse:**
  - official Pydantic docs for `field_validator(..., mode="before")`
- **Why not reinvent the wheel:** the repo already uses Pydantic for typed contracts; this block should keep preflight normalization in the same contract style.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded runtime cutover slice with deterministic tests; docs just keep canon truthful.

## Invariant
- No semantic changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- External response for empty inbound remains `WebhookResponse(success=False, message="Empty message")`.
- Media-without-text inbound must still delegate to the legacy router.

## Scope
- Add a typed inbound normalization seam for planner slice selection.
- Handle empty non-media inbound directly in `reasoning_core` through the new core.
- Add deterministic tests for the new slice and delegation boundary.
- Sync source-of-truth/state/session docs.

## Out of scope
- Media normalization/caption extraction.
- Any happy-path semantic routing cutover in the legacy router.
- Continuity collapse beyond this bounded preflight slice.
- Multi-pack acceptance.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-empty-message-planner-slice-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish the bounded empty-message planner-slice TP.
2. Add typed inbound normalization/helper(s) for planner-slice selection.
3. Handle empty non-media inbound in `reasoning_core` through the new core and stop delegation there.
4. Add deterministic tests for reject-vs-delegate behavior.
5. Re-run packet/architecture/runtime checks and sync state/session docs.

## DoD
- Empty non-media inbound is blocked in `reasoning_core` before legacy delegation.
- The blocked slice is assembled through typed new-core contracts.
- Media-without-text inbound still delegates.
- Existing external response for empty inbound remains unchanged.
- Deterministic tests cover both reject and delegate boundaries.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- typed empty-message planner artifact
- deterministic reject/delegate test output
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires touching legacy router semantics or media logic, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded preflight cutover inside `reasoning_core` only
- **Go/no-go signals:** targeted tests + packet + arch guard + session check all green
- **Rollback:** revert empty-message slice changes only
- **Post-release monitoring window:** next block may target one richer non-exception planner slice only after this preflight slice is stable

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
- Revert this TP’s code/doc changes; retain the already-landed governance/runtime-contract/degrade-slice blocks.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No media handling rewrite in this block.
- No external API change for empty-message responses.
- No duplicate caller-specific `strip()` gates outside the shared slice.

## Risks/Blockers
- Typed normalization must not accidentally classify media-without-text as empty reject.
- The new blocked slice must stay clearly preflight-scoped and not bleed into other planner paths.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only empty-message preflight and exception degrade lanes will be cut over; all richer planner semantics still live in the legacy router.
- `Why not in this block`: this block is intentionally limited to one deterministic non-exception preflight slice.
- `Risk if deferred`: entrypoint drift would persist for invalid empty inbound, and the new core would still have no shared non-exception planner cutover.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any next caller-specific preflight logic is added.

## Next-block contract (mandatory)
- `Next block objective`: cut a richer non-exception planner slice from `reasoning_core` into the new core without touching legacy router semantics.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: empty-message slice not green; reject-vs-delegate boundary not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: legacy router semantic branches in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: media misclassification, widening preflight scope, hidden external behavior changes
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
