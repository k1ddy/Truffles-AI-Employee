# TP-2026-03-15-consultant-core-tenant-context-guard-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TENANT-CONTEXT-GUARD-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-REMOTE-BRANCH-PHONE-IGNORE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-remote-branch-phone-ignore-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-INGRESS-AUTHORITY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Продолжить bounded ingress cutover без касания frozen legacy semantic files: вынести tenant-context contract reject lane с eligible non-secret shared entrypoints в `reasoning_core`. Новый core должен детерминированно отвергать `tenant_context_contract_invalid` и client mismatch до legacy delegation, сохраняя тот же внешний контракт (`Invalid tenant_context` / `Tenant mismatch`) и не забирая mutation-heavy branch/instance resolution.

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
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/services/tenant_context_contract.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/services/tenant_context_contract.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '740,860p'`
  - `nl -ba truffles-api/app/routers/webhook/http.py | sed -n '150,240p'`
  - `sed -n '1,200p' truffles-api/app/services/tenant_context_contract.py`
- `FACT findings`:
  - tenant-context reject authority still lives only inside `truffles-api/app/routers/webhook/http.py::_run_preflight(...)`.
  - `tenant_context_contract_invalid`, `tenant_context_client_mismatch`, and `tenant_context_client_slug_mismatch` are read-only contract checks; they do not depend on debounce, outbox, conversation mutation, or frozen `decision.py` semantics.
  - `reasoning_core` already has the needed shared inputs for this lane: normalized payload, client slug, and reusable client-id resolution.
  - this cutover must stay on eligible non-secret paths so legacy secret preflight remains authoritative where required.
  - branch/instance mismatch and secret enforcement remain coupled to legacy preflight and are not safe to absorb in this block.
- `Detected drift (docs vs code)`: shared runtime ownership still excludes tenant-context contract rejects, so shared entrypoints depend on legacy `_run_preflight(...)` for a bounded non-semantic ingress contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev model_dump exclude_none mode json`
- **Date/time (local):** `2026-03-15 17:33 Asia/Almaty`
- **Why this query is precise:** this block reuses `WebhookTenantContext.model_dump(exclude_none=True, mode="json")` before `validate_tenant_context_contract(...)`; the only technical question is preserving the existing contract payload shape when moving ownership into `reasoning_core`.
- **Sources opened (from this query):**
  - `Pydantic BaseModel API / model_dump` — `https://docs.pydantic.dev/latest/api/base_model/`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** `model_dump(exclude_none=True, mode="json")` is the supported way to materialize a JSON-safe payload while omitting absent fields, which matches the current legacy preflight contract-validation pattern.
- **Decision:** `reuse + integrate` — keep the existing tenant-context payload shaping and validation helper unchanged, and relocate only the bounded reject ownership into `reasoning_core`.
- **Rejected options:**
  - rewriting `validate_tenant_context_contract(...)`
  - widening the block into branch/instance mismatch handling
  - skipping contract validation and only checking client mismatch
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** eligible non-secret shared runtime entrypoints still depend on legacy `_run_preflight(...)` for tenant-context contract rejects, even though this lane is a read-only ingress contract check.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/http.py:168` through `truffles-api/app/routers/webhook/http.py:224` and locate `tenant_context_contract_invalid`, `tenant_context_client_mismatch`, and `tenant_context_client_slug_mismatch` early returns.
  2. Inspect `truffles-api/app/services/reasoning_core.py:745` through `truffles-api/app/services/reasoning_core.py:860` and confirm these reject families still fall through to legacy delegation.
  3. Verify `truffles-api/app/services/tenant_context_contract.py` already exposes the exact contract validator needed by a bounded reasoning-core preflight slice.
- **Evidence to capture:**
  - typed tenant-context reject artifact in `reasoning_core`
  - no delegate call when tenant-context contract is invalid or mismatched
  - legacy delegate still handles branch/instance/secret families unchanged
- **Five Whys (or equivalent):**
  1. Why does tenant-context reject still live in legacy preflight? Because no shared runtime slice has claimed this bounded contract lane yet.
  2. Why move it now? Because it is deterministic, read-only, and shared across entrypoints.
  3. Why not move branch/instance mismatch with it? Because those checks still depend on legacy resolution flow and integration incident side-effects.
  4. Why is current ownership wrong? Because a shared runtime seam should own shared ingress contract rejects instead of delegating them forever to `http.py`.
  5. Why does this reduce future drift? Because one more ingress contract authority becomes typed and centralized in `reasoning_core`.
- **Root cause statement:** tenant-context contract rejects are still authored only in legacy `_run_preflight(...)`, despite being bounded read-only ingress checks that can move into `reasoning_core` without touching frozen semantic router files.
- **Fix mechanism:**
  - add tenant-context validation/mismatch detection plus typed reject artifact(s) in `reasoning_core`
  - run the new guard only on eligible non-secret paths
  - preserve exact external messages for invalid contract and mismatch cases
  - leave branch/instance mismatch and secret enforcement in legacy preflight untouched

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py` as behavior reference
  - `truffles-api/app/services/tenant_context_contract.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Pydantic docs for `model_dump(...)`
- **Why not reinvent the wheel:** the repo already has the contract validator and the exact legacy reject semantics; this block should relocate bounded ownership, not redesign tenant-context validation.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded shared contract slice with deterministic tests and explicit refusal to widen into branch/instance resolution or frozen-router edits.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Existing external messages must remain exactly `Invalid tenant_context` and `Tenant mismatch`.
- Secret enforcement and branch/instance mismatch must remain in legacy preflight.
- Existing degrade, empty-message, media-normalization, sender-ignore, same-client-branch-phone, and duplicate-message slices must remain unchanged.

## Scope
- Add tenant-context contract reject ownership to `reasoning_core` for invalid contract and client mismatch lanes on eligible non-secret paths.
- Build typed reject artifact(s) through the new core contracts.
- Add deterministic tests for the new shared reject paths.
- Sync source-of-truth/state/session docs.

## Out of scope
- branch/instance mismatch handling
- secret enforcement changes
- deleting legacy `http.py` tenant-context checks for still-legacy paths
- any changes in frozen legacy semantic router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-tenant-context-guard-slice-a922.md`
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
1. Publish this tenant-context guard TP with RCA and one web search.
2. Add tenant-context reject detection and typed artifact builder(s) in `reasoning_core`.
3. Keep branch/instance/secret ownership in legacy preflight unchanged.
4. Add deterministic reasoning-core tests for invalid contract and mismatch paths.
5. Re-run consultant-core checks and sync docs/session state.

## DoD
- `reasoning_core` returns `Invalid tenant_context` before legacy delegation when the tenant-context contract is invalid on eligible non-secret paths.
- `reasoning_core` returns `Tenant mismatch` before legacy delegation when tenant-context client identity mismatches the resolved client on eligible non-secret paths.
- Frozen legacy semantic router files remain untouched.
- Deterministic tests prove the new reject paths and that unrelated legacy families still delegate.

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
- typed tenant-context reject artifact(s) in `reasoning_core`
- deterministic invalid-contract/mismatch no-delegate tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this lane requires branch/instance resolution writes, integration incident side-effects, or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded tenant-context guard cutover only
- **Go/no-go signals:** reasoning-core tests + runtime-contract tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** keep branch/instance mismatch in legacy ownership until an explicit safe bridge exists

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual tenant-context guard block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization/message-compat/sender-ignore/duplicate/remote-branch-phone blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No branch/instance resolution move in this block.
- No external wording changes for `Invalid tenant_context` or `Tenant mismatch`.
- No bypass of secret-enforced legacy preflight semantics.

## Risks/Blockers
- tenant-context validation depends on successful `client_slug -> client_id` resolution for mismatch checks.
- legacy `http.py` will still own branch/instance mismatch and secret-related families after this block.
- no current deterministic reasoning-core tests exist for tenant-context reject ownership.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only invalid tenant-context contract and client mismatch move on shared paths; branch/instance mismatch, secret enforcement, and mutation-heavy debounce remain in legacy ownership.
- `Why not in this block`: those remaining families still depend on side-effects or deeper legacy resolution flow.
- `Risk if deferred`: ingress contract ownership remains split until each remaining family is removed deliberately.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-ingress-authority-a922`
- `Expiry/trigger to stop deferral`: before any new tenant-context guard logic is added to legacy preflight.

## Next-block contract (mandatory)
- `Next block objective`: cut the next safe shared ingress authority after tenant-context rejects without widening into branch/instance resolution or mutation-heavy debounce.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: tenant-context reject paths still owned only by legacy preflight; reasoning-core guard not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen semantic router files in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: widening into branch/instance resolution, bypassing secret-enforced preflight, changing tenant-context contract payload shape
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
