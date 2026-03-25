# TP-2026-03-15-consultant-core-sender-branch-ignore-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SENDER-BRANCH-IGNORE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MESSAGE-PREFLIGHT-COMPAT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-message-preflight-compat-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Вырезать следующий stateful boundary slice из legacy preflight в shared new core: ignore inbound, если sender сам является активным branch number. Этот ignore больше не должен жить только внутри `truffles-api/app/routers/webhook/http.py`; `reasoning_core` будет собирать typed no-op turn artifact и возвращать deterministic `Ignored sender (branch number)` до делегации в legacy router.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-empty-message-planner-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-media-normalization-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-message-preflight-compat-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_branch_routing_instance.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_branch_routing_instance.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,260p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,140p' truffles-api/app/routers/webhook/http.py`
  - `sed -n '380,430p' truffles-api/tests/test_branch_routing_instance.py`
  - `sed -n '1,340p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - active branch sender suppression currently lives in legacy `_run_preflight(...)` inside `truffles-api/app/routers/webhook/http.py`.
  - `reasoning_core` already owns bounded exception, empty-message, and media-normalization slices, but it still delegates branch-sender ignore semantics into the legacy preflight helper.
  - `_lookup_sender_branch(...)` is a stateful DB-backed check over active `Branch.phone`, which makes this slice richer than pure text validation while still bounded.
- `Detected drift (docs vs code)`: new core owns some ingress decisions already, but active branch sender ignore is still authored only by the legacy preflight helper instead of the shared runtime entrypoint.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org sqlalchemy func regexp_replace`
- **Date/time (local):** `2026-03-15 15:41 Asia/Almaty`
- **Why this query is precise:** this block moves the active-branch sender phone lookup from legacy preflight into `reasoning_core`, and the existing implementation relies on SQLAlchemy `func.regexp_replace(...)` for normalized phone matching.
- **Sources opened (from this query):**
  - `SQLAlchemy Core functions API` — `https://docs.sqlalchemy.org/20/core/functions.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** SQLAlchemy `func.regexp_replace(...)` is the canonical way to emit vendor SQL functions such as `regexp_replace(...)` inside query filters while preserving ORM composition.
- **Decision:** `reuse + integrate` — transplant the existing normalized phone-match query into `reasoning_core` and delete the legacy helper ownership from `http.py` for this one ignore lane.
- **Rejected options:**
  - leaving branch-sender ignore only in legacy preflight
  - reimplementing sender match with Python-side full table scans
  - widening this block into all branch-routing/instance-resolution semantics
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** the new core still cannot author one stateful ignore outcome itself; active branch sender suppression is still owned by the legacy preflight helper.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/http.py` and find `_lookup_sender_branch(...)` plus the early return `Ignored sender (branch number)`.
  2. Inspect `truffles-api/app/services/reasoning_core.py` and see that after normalization/empty-message checks it still delegates directly to `decision_router._handle_webhook_payload(...)`.
  3. Inspect `truffles-api/tests/test_branch_routing_instance.py` and see the ignore behavior is only proven against `_run_preflight(...)`, not against the shared new-core entrypoint.
- **Evidence to capture:**
  - typed ignore artifact in `reasoning_core`
  - no delegate call for active branch sender inbound
  - narrowed legacy preflight helper with updated deterministic test expectations
- **Five Whys (or equivalent):**
  1. Why is ingress cutover still partial? Because stateful sender-ignore logic still lives in the legacy helper.
  2. Why is this lane worth moving now? Because it is bounded, deterministic, and DB-backed, so it exercises more than trivial text validation without requiring legacy semantic router edits.
  3. Why not move all branch routing at once? Because instance resolution and tenant mismatch handling are a larger family; this block isolates one exact authority for deletion.
  4. Why is current ownership wrong? Because the shared runtime entrypoint should own bounded ingress outcomes, not delegate them back into the old preflight helper forever.
  5. Why does this reduce future drift? Because one more no-op/ignore outcome becomes impossible to grow only in the legacy path.
- **Root cause statement:** active branch sender suppression is still authored exclusively by legacy `_run_preflight(...)`, so the new core cannot yet express this stateful ignore outcome as a typed runtime contract and the legacy preflight helper remains larger than necessary.
- **Fix mechanism:**
  - add an active-branch sender lookup and typed ignore artifact in `reasoning_core`
  - return deterministic `Ignored sender (branch number)` before legacy delegation
  - delete the exact `_lookup_sender_branch` early-return ownership from `http.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/http.py` as current behavior reference
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_branch_routing_instance.py`
- **External reuse:**
  - official SQLAlchemy `func(...)` docs for the normalized phone-match query shape
- **Why not reinvent the wheel:** the repo already has the correct branch-phone lookup query and existing ignore wording; this block should relocate ownership, not invent new behavior.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded stateful ingress slice with deterministic tests and one explicit authority deletion from legacy preflight.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Existing user-visible ignore wording must remain exactly `Ignored sender (branch number)`.
- Empty-message/media-normalization/degrade slices must remain unchanged.

## Scope
- Move active branch sender ignore ownership into `reasoning_core`.
- Build a typed ignore artifact through the new core contracts.
- Narrow legacy `http.py` preflight by deleting the exact sender-branch early return.
- Add deterministic tests for the new shared ignore path and the narrowed legacy helper.
- Sync source-of-truth/state/session docs.

## Out of scope
- `remote_is_branch_phone` family in legacy preflight.
- branch instance resolution / tenant mismatch / secret enforcement.
- richer semantic planner slice beyond this bounded ignore lane.
- any changes in frozen legacy semantic router files.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-sender-branch-ignore-slice-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_branch_routing_instance.py`
- `ops/reset_knowledge.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this bounded sender-branch ignore TP with RCA and one web search.
2. Add active-branch sender detection and a typed ignore artifact in `reasoning_core`.
3. Delete the exact sender-branch early-return ownership from legacy `http.py`.
4. Add deterministic tests for the new reasoning-core ignore path and the narrowed preflight helper.
5. Re-run consultant-core checks and sync docs/session state.

## DoD
- Active branch sender inbound is ignored directly by `reasoning_core` before legacy delegation.
- `http.py` no longer owns the exact `_lookup_sender_branch` early return.
- User-visible ignore wording remains unchanged.
- Deterministic tests prove both the new shared path and the narrowed legacy helper behavior.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_branch_routing_instance.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/http.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- typed sender-ignore artifact in `reasoning_core`
- narrowed `http.py` preflight diff
- deterministic runtime + preflight tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this lane requires touching frozen semantic router files or widening into branch instance resolution family, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded ingress ignore cutover only
- **Go/no-go signals:** reasoning-core tests + branch-routing tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** next block may resume richer planner cutover after this exact legacy preflight authority is removed

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual sender-branch ignore block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization/message-compat blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No behavior changes to `remote_is_branch_phone` or branch instance routing in this block.
- No wording change for `Ignored sender (branch number)`.
- No caller-specific duplication of the sender-ignore lane.

## Risks/Blockers
- The moved ignore lane must still bypass legacy delegation deterministically.
- Narrowing `http.py` must not change unrelated branch-routing preflight behavior.
- `scripts/arch_guard.py` can be blocked by unrelated syntax errors in tracked changed files; if surfaced, only minimal parse-restoring blocker fixes are allowed.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only the exact active-branch sender ignore lane is moved; other branch-routing and tenant/instance preflight families still live in legacy `_run_preflight(...)`.
- `Why not in this block`: those families are larger and deserve separate bounded cutovers.
- `Risk if deferred`: legacy preflight still remains a large authority surface even after this deletion.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any new branch-routing behavior is added to `http.py`.

## Next-block contract (mandatory)
- `Next block objective`: cut one richer semantic planner slice from `reasoning_core` into the new core after this stateful ignore lane is removed from legacy preflight ownership.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py && pytest -q truffles-api/tests/test_branch_routing_instance.py`
- `Blocked-by conditions`: sender-ignore still owned only by legacy preflight; reasoning-core ignore path not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen semantic router files in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: widening into branch instance family, losing exact ignore wording, leaving dual ownership in `http.py`
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
