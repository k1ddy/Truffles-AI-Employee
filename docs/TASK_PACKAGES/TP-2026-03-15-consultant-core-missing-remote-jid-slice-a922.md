# TP-2026-03-15-consultant-core-missing-remote-jid-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MISSING-REMOTE-JID-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TENANT-CONTEXT-GUARD-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-tenant-context-guard-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-INGRESS-AUTHORITY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Продолжить bounded ingress cutover без касания frozen legacy semantic files: вынести `missing_remote_jid` reject lane с eligible shared entrypoints в `reasoning_core`. Новый core должен детерминированно отвергать inbound без `metadata.remoteJid`, сохраняя тот же внешний контракт `Missing metadata.remoteJid` и не обходя secret-enforced legacy preflight.

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
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-sender-branch-ignore-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-duplicate-message-preflight-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-remote-branch-phone-ignore-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-tenant-context-guard-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '880,980p'`
  - `nl -ba truffles-api/app/routers/webhook/http.py | sed -n '150,190p'`
  - `sed -n '1,260p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - `missing_remote_jid` reject still lives only in `truffles-api/app/routers/webhook/http.py::_run_preflight(...)`.
  - this lane is read-only and does not require branch resolution, debounce mutation, conversation state, or frozen `decision.py` edits.
  - `reasoning_core` already receives normalized payload + optional metadata and can reject this lane before any richer planner logic.
  - to preserve secret-ordering invariants, this slice must stay on eligible non-secret paths only; `enforce_secret=True` traffic must still delegate to legacy preflight.
- `Detected drift (docs vs code)`: shared runtime ownership still excludes `missing_remote_jid`, so one more ingress reject remains authored only in legacy preflight.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev latest api base_model model_copy model_dump optional nested fields`
- **Date/time (local):** `2026-03-15 18:13 Asia/Almaty`
- **Why this query is precise:** this block relies on the current nested `WebhookRequest` / `WebhookMetadata` model shape and must preserve safe optional-field handling while keeping the normalized payload contract unchanged.
- **Sources opened (from this query):**
  - `Pydantic BaseModel API` — `https://docs.pydantic.dev/latest/api/base_model/`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** Pydantic’s model APIs keep nested optional fields explicit and JSON-safe via standard model access and `model_dump(...)`; no custom coercion layer is needed for this bounded reject slice.
- **Decision:** `reuse + integrate` — keep the existing payload model and bounded preflight pattern, and relocate only `missing_remote_jid` ownership into `reasoning_core`.
- **Rejected options:**
  - widening the block into client-missing or branch/instance resolution
  - changing payload normalization semantics
  - running this reject before secret enforcement on `enforce_secret=True` traffic
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** eligible shared entrypoints still depend on legacy `_run_preflight(...)` for `missing_remote_jid`, even though this is a read-only ingress reject.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/http.py:154` and find the `missing_remote_jid` early return.
  2. Inspect `truffles-api/app/services/reasoning_core.py` and confirm that payloads without `metadata.remoteJid` still fall through to legacy delegation on non-secret paths.
  3. Verify that no conversation, debounce, branch-instance, or write-side state is required for this exact reject family.
- **Evidence to capture:**
  - typed `missing_remote_jid` reject artifact in `reasoning_core`
  - no delegate call when `metadata.remoteJid` is absent on eligible non-secret paths
  - `enforce_secret=True` traffic still delegates unchanged
- **Five Whys (or equivalent):**
  1. Why does `missing_remote_jid` still live in legacy preflight? Because no shared runtime slice has taken ownership of this bounded reject yet.
  2. Why move it now? Because it is deterministic, read-only, and low-risk.
  3. Why keep it off secret-enforced paths? Because legacy preflight still owns secret ordering and that must not be bypassed.
  4. Why is current ownership wrong? Because shared entrypoints should not permanently depend on `http.py` for a simple ingress contract reject.
  5. Why does this reduce future drift? Because one more ingress authority becomes typed and centralized in `reasoning_core`.
- **Root cause statement:** `missing_remote_jid` is still authored only in legacy `_run_preflight(...)`, even though it is a bounded read-only ingress reject that can move safely into `reasoning_core` on eligible non-secret paths.
- **Fix mechanism:**
  - add a typed `missing_remote_jid` reject artifact in `reasoning_core`
  - return the exact external `Missing metadata.remoteJid` response before legacy delegation on eligible non-secret paths
  - keep `enforce_secret=True` traffic delegated to legacy preflight unchanged

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py` as behavior reference
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Pydantic docs for BaseModel field/model behavior
- **Why not reinvent the wheel:** the repo already has the exact reject wording and payload model; this block should relocate bounded ownership, not redesign ingress parsing.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded deterministic ingress reject slice with explicit guard against secret-ordering drift.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Existing external message must remain exactly `Missing metadata.remoteJid`.
- `enforce_secret=True` traffic must still delegate into legacy preflight unchanged.
- Already-landed bounded slices must remain behaviorally unchanged.

## Scope
- Add `missing_remote_jid` reject ownership to `reasoning_core` on eligible non-secret paths.
- Build a typed reject artifact through the new core contracts.
- Add deterministic tests for the new reject path and the secret-enforcement guard.
- Sync source-of-truth/state/session docs.

## Out of scope
- client-missing ownership transfer
- missing-tenant-context ownership transfer
- branch/instance resolution changes
- secret enforcement changes
- any changes in frozen legacy semantic router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-missing-remote-jid-slice-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this bounded `missing_remote_jid` TP with RCA and one web search.
2. Add the typed reject artifact and eligible non-secret guard in `reasoning_core`.
3. Add deterministic reasoning-core tests for reject and secret-enforcement delegate paths.
4. Re-run consultant-core checks and sync docs/session state.

## DoD
- `reasoning_core` returns `Missing metadata.remoteJid` before legacy delegation when `metadata.remoteJid` is absent on eligible non-secret paths.
- `enforce_secret=True` traffic still delegates into legacy preflight unchanged.
- Frozen legacy semantic router files remain untouched.
- Deterministic tests prove the new reject path and the secret-ordering guard.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- typed `missing_remote_jid` reject artifact in `reasoning_core`
- deterministic reject/no-delegate and secret-ordering tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this lane requires secret-ordering changes, branch resolution, or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded `missing_remote_jid` cutover only
- **Go/no-go signals:** reasoning-core tests + runtime-contract tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** keep client-missing and other preflight families split into separate bounded blocks

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual `missing_remote_jid` block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization/message-compat/sender-ignore/duplicate/remote-branch-phone/tenant-context blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No secret-ordering bypass on `enforce_secret=True` traffic.
- No wording change for `Missing metadata.remoteJid`.
- No widening into client-missing or branch/instance logic.

## Risks/Blockers
- direct `handle_webhook_direct` already does secret validation before calling `reasoning_core`, so behavior must remain aligned across both public entrypoints.
- other preflight rejects still remain in legacy ownership after this block.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only `missing_remote_jid` moves on eligible non-secret paths; client-missing, missing-tenant-context, branch/instance mismatch, secret enforcement, and debounce remain in legacy ownership.
- `Why not in this block`: those remaining families either need separate authority decisions or depend on deeper legacy sequencing.
- `Risk if deferred`: ingress ownership remains split until each remaining reject family is cut over deliberately.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-ingress-authority-a922`
- `Expiry/trigger to stop deferral`: before any new `missing_remote_jid` behavior is added to legacy preflight.

## Next-block contract (mandatory)
- `Next block objective`: cut the next safe shared ingress authority after `missing_remote_jid` without widening into secret ordering or mutation-heavy debounce.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: `missing_remote_jid` still owned only by legacy preflight; reasoning-core reject path not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen semantic router files in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: bypassing secret ordering, widening into client-missing or branch logic, changing current external reject wording
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
