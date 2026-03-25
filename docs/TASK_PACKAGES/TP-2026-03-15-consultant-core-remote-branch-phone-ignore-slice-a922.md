# TP-2026-03-15-consultant-core-remote-branch-phone-ignore-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-REMOTE-BRANCH-PHONE-IGNORE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DUPLICATE-MESSAGE-PREFLIGHT-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-duplicate-message-preflight-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-INGRESS-AUTHORITY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Продолжить bounded ingress cutover без касания frozen legacy semantic files: вынести `remote_is_branch_phone` ignore с eligible shared entrypoints в `reasoning_core`. Новый core будет детерминированно игнорировать inbound, если `remoteJid` совпадает с branch phone текущего клиента, и вернет тот же внешний `Ignored branch sender` до legacy delegation только на путях, где legacy secret preflight уже не должен владеть этим решением.

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
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '620,760p'`
  - `nl -ba truffles-api/app/routers/webhook/http.py | sed -n '220,280p'`
  - `sed -n '280,520p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - `remote_is_branch_phone` ignore still lives only in `truffles-api/app/routers/webhook/http.py`, inside legacy `_run_preflight(...)`.
  - unlike `_handle_debounce_gate(...)`, this exact ignore lane is read-only and does not require buffer mutation, conversation refresh, or write-side state, so it can be cut over safely without touching `decision.py`.
  - the previous suggested debounce/buffer block is not safe under current constraints: pre-running `_handle_debounce_gate(...)` before legacy delegation would duplicate buffer writes or require a new skip flag in frozen legacy runtime.
  - `reasoning_core` already has safe client-id resolution by `client_slug` and existing bounded ignore/degrade artifact patterns that can be reused.
- `Detected drift (docs vs code)`: shared ingress ownership is still false for same-client branch-phone ignore; provider/direct/message callers still depend on legacy `http.py` preflight for that decision.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org sqlalchemy query single column result all rows`
- **Date/time (local):** `2026-03-15 17:16 Asia/Almaty`
- **Why this query is precise:** this block reuses the existing `Branch.phone` single-column query shape from legacy preflight, and the only technical question is how safely that result shape should be consumed without widening the query semantics.
- **Sources opened (from this query):**
  - `SQLAlchemy Core Connections / Result handling` — `https://docs.sqlalchemy.org/20/core/connections.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** SQLAlchemy result rows for single-column selections should be handled deliberately rather than assuming one exact row object shape across call sites.
- **Decision:** `reuse + integrate` — keep the existing `Branch.phone` query semantics and preserve the current tuple/attribute normalization behavior while relocating ownership into `reasoning_core`.
- **Rejected options:**
  - attempting the debounce/buffer cutover in this block
  - changing branch-phone query semantics while moving ownership
  - widening the block into all webhook preflight authority
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** eligible shared entrypoints still depend on legacy `_run_preflight(...)` for `remote_is_branch_phone` ignore, so the shared runtime entrypoint does not own this bounded same-client branch-phone outcome.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/http.py:246` and find the `remote_is_branch_phone` early return.
  2. Inspect `truffles-api/app/services/reasoning_core.py:626` and confirm that after current bounded slices it still delegates this exact ignore family to legacy runtime.
  3. Compare with `_handle_debounce_gate(...)` in `truffles-api/app/routers/webhook/dedup.py` and note that debounce is mutation-heavy while this branch-phone ignore is read-only.
- **Evidence to capture:**
  - typed `remote_is_branch_phone` ignore artifact in `reasoning_core`
  - no delegate call when a same-client branch phone is detected on eligible paths
  - secret-enforced traffic still delegates into legacy preflight unchanged
- **Five Whys (or equivalent):**
  1. Why does this ignore still live in legacy preflight? Because no shared runtime slice has taken ownership of same-client branch-phone detection yet.
  2. Why move it now? Because it is stateful enough to matter, but still read-only and bounded.
  3. Why not do debounce instead? Because debounce mixes Redis writes, sleeps, conversation refresh, and state mutation, which cannot be pre-run safely without touching frozen legacy runtime.
  4. Why is current ownership wrong? Because shared reasoning entrypoints should not permanently depend on `http.py` for a bounded ignore decision.
  5. Why does this reduce future drift? Because one more ingress ignore outcome becomes available from the shared new-core seam instead of only the legacy preflight helper.
- **Root cause statement:** `remote_is_branch_phone` is still authored only in legacy `_run_preflight(...)`, even though it is a bounded read-only ingress decision that can be moved into `reasoning_core` safely on eligible paths.
- **Fix mechanism:**
  - add same-client branch-phone lookup plus typed ignore artifact in `reasoning_core`
  - run it only when `enforce_secret=False`, so legacy secret preflight is not bypassed
  - keep legacy `http.py` behavior intact for secret-enforced paths

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py` as behavior reference
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official SQLAlchemy docs for result/row handling
- **Why not reinvent the wheel:** the repo already contains the exact branch-phone comparison semantics and ignore wording; this block should relocate bounded ownership, not redesign it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded stateful ignore slice with deterministic tests and explicit refusal to widen into debounce or full preflight takeover.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Existing user-visible ignore wording must remain exactly `Ignored branch sender`.
- Secret-enforced traffic must still delegate to legacy preflight unchanged.
- Duplicate-message, sender-branch, empty-message, media-normalization, and degrade slices must remain unchanged.

## Scope
- Add same-client branch-phone ignore ownership to `reasoning_core` on eligible paths.
- Build a typed ignore artifact through the new core contracts.
- Add deterministic tests for the new shared ignore path and the secret-enforcement guard.
- Sync source-of-truth/state/session docs.

## Out of scope
- debounce/buffer ownership transfer
- deleting the legacy `http.py` branch-phone check for secret-enforced paths
- branch instance resolution / tenant mismatch / other preflight families
- any changes in frozen legacy semantic router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-remote-branch-phone-ignore-slice-a922.md`
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
1. Publish this bounded same-client branch-phone TP with RCA and one web search.
2. Add branch-phone lookup and typed ignore artifact in `reasoning_core`.
3. Guard the new slice so secret-enforced traffic still delegates into legacy preflight.
4. Add deterministic reasoning-core tests for ignore and delegate paths.
5. Re-run consultant-core checks and sync docs/session state.

## DoD
- `reasoning_core` returns `Ignored branch sender` before legacy delegation when a same-client branch phone is detected on eligible paths.
- Secret-enforced traffic still delegates to legacy preflight unchanged.
- No frozen legacy semantic router file changes are needed.
- Deterministic tests prove the new shared ignore path and the secret-enforcement guard.

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
- typed same-client branch-phone ignore artifact in `reasoning_core`
- deterministic ignore/no-delegate and secret-enforcement tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this lane requires mutating debounce/buffer state or touching frozen semantic router files, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded same-client branch-phone ignore cutover only
- **Go/no-go signals:** reasoning-core tests + runtime-contract tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** revisit debounce only in a separate TP with an explicit safe bridge or legacy cut line

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual same-client branch-phone block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization/message-compat/sender-ignore/duplicate blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No debounce/buffer mutation in `reasoning_core`.
- No wording change for `Ignored branch sender`.
- No bypass of secret-enforced legacy preflight.

## Risks/Blockers
- same-client branch-phone lookup still depends on `client_slug -> client_id` resolution in `reasoning_core`.
- legacy `http.py` will still own the same ignore lane for secret-enforced paths, so dual ownership remains temporarily by design.
- no current deterministic test existed for `Ignored branch sender`; this block must add one.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only the same-client branch-phone ignore outcome moves on eligible paths; debounce/buffer and the rest of legacy preflight remain in place.
- `Why not in this block`: debounce is mutation-heavy and not safely pre-runnable under current frozen-file constraints.
- `Risk if deferred`: legacy preflight still remains a large authority surface after this deletion.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-ingress-authority-a922`
- `Expiry/trigger to stop deferral`: before any new branch-phone ignore behavior is added to legacy preflight.

## Next-block contract (mandatory)
- `Next block objective`: cut the next safe ingress authority after same-client branch-phone ignore, without widening into mutation-heavy debounce unless the bridge is explicitly designed.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: same-client branch-phone ignore still owned only by legacy preflight; reasoning-core ignore path not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen semantic router files in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: widening into debounce, bypassing secret-enforced preflight, changing current branch-phone matching semantics
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
