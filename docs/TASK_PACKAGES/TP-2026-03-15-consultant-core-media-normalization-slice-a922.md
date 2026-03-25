# TP-2026-03-15-consultant-core-media-normalization-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MEDIA-NORMALIZATION-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-EMPTY-MESSAGE-PLANNER-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-empty-message-planner-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Вырезать следующий non-exception planner slice в `reasoning_core`: shared media-only inbound normalization before legacy delegation. Media-only inbound больше не должен зависеть от caller-specific preflight в `webhook/http.py`; `reasoning_core` будет один раз нормализовать caption/media placeholder через typed planner input и затем делегировать в legacy runtime уже с нормализованным текстом.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-runtime-contracts-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-empty-message-planner-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/media.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,260p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '220,280p' truffles-api/app/routers/webhook/http.py`
  - `sed -n '207,260p' truffles-api/app/routers/webhook/media.py`
  - `sed -n '1,320p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - `reasoning_core` now owns the exception degrade lane and empty-message preflight lane.
  - Media-only normalization still lives in `webhook/http.py`: caption promotion and fallback placeholder like `[audio]` happen there, not in the shared runtime entrypoint.
  - Other callers (`decision_core`, `provider_gateway`, `message`) can still enter `reasoning_core` without that shared normalization.
- `Detected drift (docs vs code)`: new-core planner slices exist, but media-only normalization is still caller-specific instead of shared in `reasoning_core`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev/latest/concepts/models model_copy update nested models`
- **Date/time (local):** `2026-03-15 15:02 Asia/Almaty`
- **Why this query is precise:** this block needs one safe way to normalize nested `WebhookRequest` / `WebhookBody` data before delegation without mutating caller objects ad hoc.
- **Sources opened (from this query):**
  - `Pydantic models / model_copy` — `https://docs.pydantic.dev/latest/concepts/models/`
  - `Pydantic serialization / model_dump` — `https://docs.pydantic.dev/latest/concepts/serialization/`
- **Existing solutions found:** use typed models for normalization, `model_validate(...)` for coercion, and `model_copy(update={...})` to create updated nested models without mutating the original object in place.
- **Decision:** `reuse + integrate` — reuse `TurnPlanner` typed inbound normalization and update nested `WebhookRequest`/`WebhookBody` via Pydantic copying rather than custom dict surgery.
- **Rejected options:**
  - caller-specific `strip()`/placeholder logic in each router
  - raw dict mutation on `payload.body`
  - widening this block into media storage/ASR behavior
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** media-only inbound normalization is still inconsistent across reasoning-core callers because it lives in `webhook/http.py` preflight instead of the shared entrypoint.
- **Minimal reproduction:**
  1. Inspect `webhook/http.py` and find caption promotion / `[media]` placeholder logic.
  2. Inspect `reasoning_core.handle_webhook_payload(...)` and see it delegates non-preflight inbound directly.
  3. Inspect `decision_core` / `provider_gateway` and see they call `reasoning_core` without `webhook/http.py` preflight.
- **Evidence to capture:**
  - one shared payload-normalization helper in `reasoning_core`
  - deterministic tests for caption promotion and placeholder delegation
  - unchanged empty-message reject behavior
- **Five Whys (or equivalent):**
  1. Why is non-exception cutover still partial? Because normalization for media-only inbound still depends on caller-specific preflight.
  2. Why is this slice bounded enough? Because it only normalizes inbound text before legacy delegation.
  3. Why not change the legacy router? Because the goal is to shift planner ownership into `reasoning_core`, not add more caller drift or legacy branches.
  4. Why is shared normalization valuable? Because all reasoning-core callers can then feed the same normalized payload into the legacy runtime.
  5. Why does this reduce future drift? Because future planner slices can assume one normalized inbound shape instead of caller-specific variants.
- **Root cause statement:** media-only inbound normalization is still owned by one HTTP caller preflight instead of the shared reasoning-core planner boundary, so identical media-only input can arrive at the legacy runtime in different shapes depending on entrypoint.
- **Fix mechanism:**
  - add a typed normalization helper in `reasoning_core` using `TurnPlanner` + media extraction
  - promote media caption into message text when present
  - otherwise synthesize a `[media_type]` placeholder before legacy delegation

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/routers/webhook/media.py`
  - `truffles-api/app/routers/webhook/http.py` as the current behavior reference
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Pydantic docs for `model_copy(update={...})` and typed model validation
- **Why not reinvent the wheel:** the repo already has typed inbound normalization and media extraction; this block should connect them, not fork a second normalization style.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded runtime cutover slice with deterministic tests; docs only keep canon truthful.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Empty non-media inbound must still reject exactly as before.
- Media-only inbound must still delegate to the legacy runtime, just with shared normalization.

## Scope
- Add shared media-only normalization before legacy delegation in `reasoning_core`.
- Reuse media caption extraction and placeholder normalization.
- Add deterministic tests for caption promotion and placeholder delegation.
- Sync source-of-truth/state/session docs.

## Out of scope
- Media storage/forwarding/ASR behavior.
- Any semantic routing change in the legacy router.
- Message API compatibility refactor for preflight responses.
- Multi-pack acceptance.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-media-normalization-slice-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish the bounded media-normalization planner-slice TP.
2. Add a shared normalization helper in `reasoning_core` using typed inbound input plus media extraction.
3. Delegate normalized media-only inbound into the legacy runtime.
4. Add deterministic tests for caption promotion and placeholder delegation.
5. Re-run packet/architecture/runtime checks and sync state/session docs.

## DoD
- Media-only inbound is normalized in `reasoning_core` before legacy delegation.
- Caption promotion and `[media_type]` placeholder behavior are covered by deterministic tests.
- Empty non-media reject remains unchanged.
- No legacy router semantics changed.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- shared media normalization helper in `reasoning_core`
- deterministic caption/placeholder delegation tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires touching media storage/ASR or legacy semantic routing, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded normalization cutover before legacy delegation only
- **Go/no-go signals:** targeted tests + packet + arch guard + session check all green
- **Rollback:** revert media-normalization slice changes only
- **Post-release monitoring window:** next block may target a richer planner slice after shared inbound normalization remains stable

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
- Revert this TP’s code/doc changes; retain the already-landed governance/runtime-contract/degrade/preflight blocks.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No duplicate media normalization branches in caller routers.
- No media storage/ASR logic changes in this block.
- No external API contract changes.

## Risks/Blockers
- Shared normalization must not misclassify empty non-media inbound as media.
- Placeholder normalization must remain truthful to the existing HTTP preflight behavior.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only exception, empty-message, and media-normalization planner slices will be cut over; richer semantic planning still lives in the legacy router.
- `Why not in this block`: this block is intentionally limited to one shared normalization seam before delegation.
- `Risk if deferred`: caller-specific media-only drift would remain and make later planner slices harder to reason about.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any new caller-specific media preflight logic is added.

## Next-block contract (mandatory)
- `Next block objective`: cut one richer semantic planner slice from `reasoning_core` into the new core on top of shared inbound normalization.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: media-normalization slice not green; caption/placeholder delegation not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: legacy router semantic branches in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: media misclassification, duplicated normalization, widening scope into storage/ASR
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
