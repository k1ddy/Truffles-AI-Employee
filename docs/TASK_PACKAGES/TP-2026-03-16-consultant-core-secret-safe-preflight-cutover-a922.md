# TP-2026-03-16-consultant-core-secret-safe-preflight-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SECRET-SAFE-PREFLIGHT-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-REASONING-DEGRADE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-INGRESS-PREFLIGHT-AUTHORITY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать bounded ingress cutover без правок frozen runtime files: `reasoning_core` должен стать secret-safe authority для `enforce_secret=True` preflight-fail paths, сохраняя legacy incident/trace side-effects и убирая текущий bypass, при котором ранние `reasoning_core` exits могут обойти webhook secret enforcement.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reasoning-degrade-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/secrets.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/secrets.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "provided_secret|enforce_secret|_run_preflight|sender_is_branch|missing_remote_jid|missing_tenant_context|tenant_context|remote_is_branch_phone" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/http.py truffles-api/tests/test_reasoning_core.py`
  - `sed -n '9248,9338p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - `/webhook` enters `reasoning_core.handle_webhook_payload(..., enforce_secret=True)`, but `reasoning_core` does not validate webhook secrets before its own early exits.
  - current `reasoning_core` can ignore active branch sender before legacy `_run_preflight(...)`, which is a real secret-enforcement bypass on the wrapped `/webhook` path.
  - legacy `_run_preflight(...)` in `truffles-api/app/routers/webhook/http.py` already owns the correct client-level/branch-level secret checks plus `report_integration_incident(...)`, `alert_warning(...)`, preflight `decision_trace`, tenant-context validation, branch resolution, and early reject/drop responses.
  - `decision.py` is frozen, so the cutover must avoid editing its preflight call-site.
- `Detected drift (docs vs code)`: `reasoning_core` is supposed to be the new ingress seam, but secret-enforced preflight-fail behavior still effectively belongs to the legacy router and one existing `reasoning_core` early exit can bypass that gate.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org hmac compare_digest documentation`
- **Date/time (local):** `2026-03-16 07:51 Asia/Almaty`
- **Why this query is precise:** this block centralizes webhook secret comparison across the wrapped ingress path and must use the standard constant-time comparator instead of open-coded equality checks.
- **Sources opened (from this query):**
  - `hmac — Keyed-Hashing for Message Authentication` — `https://docs.python.org/3/library/hmac.html#hmac.compare_digest`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `hmac.compare_digest(...)` is the standard-library constant-time comparison primitive for verifying secrets.
- **Decision:** `reuse + integrate` — add a shared webhook-secret comparator in `truffles-api/app/routers/webhook/secrets.py` and reuse it from the secret-enforced preflight bridge.
- **Rejected options:**
  - leaving secret enforcement only inside legacy preflight while `reasoning_core` keeps early exits ahead of it
  - broad ingress refactor that edits frozen `decision.py`
  - rebuilding preflight side-effects from scratch instead of reusing legacy `_run_preflight(...)`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** on `/webhook` requests with `enforce_secret=True`, `reasoning_core` can still take early exits before legacy webhook secret validation; at minimum `sender_is_branch` currently sits ahead of the secret gate.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/reasoning_core.py` and observe `_lookup_active_sender_branch(...)` + early return before any secret validation.
  2. Open `truffles-api/app/routers/webhook/http.py:_run_preflight(...)` and observe that client-level secret validation must happen before payload validation.
  3. Open `truffles-api/app/routers/webhook/http.py:handle_webhook(...)` and observe that `/webhook` calls `reasoning_core.handle_webhook_payload(..., enforce_secret=True)`.
- **Evidence to capture:**
  - `reasoning_core` runs a secret-enforced legacy preflight bridge before any of its own early exits on the wrapped `/webhook` path
  - preflight failures return directly from `reasoning_core` with legacy side-effects preserved
  - successful secret-enforced preflight delegates with `enforce_secret=False` to avoid double secret validation
  - tests prove sender-branch ignore no longer bypasses secret enforcement
- **Five Whys (or equivalent):**
  1. Why is ingress still unsafe? Because the wrapped `/webhook` path enters `reasoning_core` before legacy secret validation.
  2. Why is that a bug? Because `reasoning_core` already has early exits that can return before the hard preflight secret gate.
  3. Why can't we just fix it in `decision.py`? Because `decision.py` is frozen for new semantic/runtime growth.
  4. Why is reusing `_run_preflight(...)` the bounded fix? Because it already contains the required secret checks, incident reporting, alerting, trace recording, tenant validation, and early reject/drop behavior.
  5. Why does this reduce drift? Because secret-enforced preflight-fail authority moves to the new ingress seam without re-implementing or weakening the hard gate.
- **Root cause statement:** the wrapped `/webhook` path still relies on legacy preflight for hard secret enforcement, but `reasoning_core` has early returns ahead of that gate, so the new ingress seam is not yet safe or authoritative for secret-enforced preflight failures.
- **Fix mechanism:**
  - add a secret-enforced preflight bridge in `reasoning_core` that reuses legacy `_run_preflight(...)` with equivalent trace-resolution callbacks
  - delegate to `decision_router._handle_webhook_payload(...)` with `enforce_secret=False` only after that bridge has already enforced secrets successfully
  - centralize secret comparison through a shared comparator in `truffles-api/app/routers/webhook/secrets.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/webhook/http.py:_run_preflight(...)`
  - `truffles-api/app/routers/webhook/secrets.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/routers/webhook/decision.py:_find_message_by_message_id(...)`
  - existing `reasoning_core` preflight/degrade scaffolding and tests
- **External reuse:**
  - official Python `hmac.compare_digest(...)` documentation
- **Why not reinvent the wheel:** the repo already has a mature legacy preflight with the required side-effects; this block should reuse it from `reasoning_core`, not fork it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded ingress bridge cutover with explicit tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No weakening of client-level or branch-level webhook secret enforcement.
- No loss of integration incidents, secret-missing alerts, or early preflight trace writes.

## Scope
- Add a secret-enforced legacy preflight bridge in `truffles-api/app/services/reasoning_core.py`.
- Reuse `truffles-api/app/routers/webhook/http.py:_run_preflight(...)` plus equivalent trace callbacks from the new ingress seam.
- Centralize webhook secret comparison in `truffles-api/app/routers/webhook/secrets.py` and reuse it where touched in `http.py`.
- Update `truffles-api/tests/test_reasoning_core.py` for the new secret-safe behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- removing the second non-secret preflight pass inside frozen `decision.py`
- dedup/debounce cutover
- richer semantic planner cutover
- frozen runtime file edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-secret-safe-preflight-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/secrets.py`
- `truffles-api/tests/test_reasoning_core.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and one web search.
2. Add a shared webhook-secret comparator in `truffles-api/app/routers/webhook/secrets.py` and reuse it in touched secret checks.
3. Add a secret-enforced preflight bridge in `truffles-api/app/services/reasoning_core.py` that reuses legacy `_run_preflight(...)` with equivalent trace callbacks.
4. Make successful secret-enforced preflight delegate with `enforce_secret=False` to avoid double secret validation.
5. Update `truffles-api/tests/test_reasoning_core.py` for the new ingress behavior and rerun required checks.
6. Sync canon/session artifacts.

## DoD
- `/webhook` requests with `enforce_secret=True` can no longer bypass secret enforcement through `reasoning_core` early exits
- preflight failures now return directly from `reasoning_core` while preserving legacy incident/alert/trace side-effects
- successful secret-enforced preflight delegates without a second secret check
- deterministic reasoning/runtime/architecture/session checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- secret-enforced preflight bridge in `truffles-api/app/services/reasoning_core.py`
- shared webhook-secret comparator in `truffles-api/app/routers/webhook/secrets.py`
- updated `truffles-api/tests/test_reasoning_core.py`
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires editing frozen `decision.py` or rebuilding dedup/debounce side-effects, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** wrapped `/webhook` ingress preflight bridge only
- **Go/no-go signals:** reasoning-core suite + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's reasoning-core/http/secrets/test/doc changes only
- **Post-release monitoring window:** next block should either remove duplicate preflight pass with a non-frozen seam or continue richer semantic cutover; do not grow more legacy-owned ingress logic

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual secret-safe preflight cutover being executed.

## Rollback
- Revert this TP's reasoning-core/http/secrets/test/doc changes; keep previously landed governance, continuity, and proof-path blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No weakening of webhook secret validation.
- No dedup/debounce cutover in this block.

## Risks/Blockers
- duplicating too much legacy preflight logic in `reasoning_core` would turn this into a broad ingress rewrite.
- losing preflight trace callbacks would make the cutover architecturally dishonest even if user-visible responses stayed the same.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: frozen `decision.py` still runs a second non-secret preflight pass after successful bridge handoff; dedup/debounce still remain legacy-owned.
- `Why not in this block`: removing the duplicate pass needs a non-frozen seam; dedup/debounce preserve mutation-heavy side-effects and exceed this bounded cut.
- `Risk if deferred`: some ingress work remains duplicated and legacy-owned after successful secret-enforced preflight.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-ingress-preflight-authority-followup-a922`
- `Expiry/trigger to stop deferral`: before claiming complete ingress cutover or before moving dedup/debounce without explicit side-effect preservation.

## Next-block contract (mandatory)
- `Next block objective`: remove the duplicate post-bridge preflight pass through a non-frozen seam or take the next richer semantic cutover in `reasoning_core`.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: secret-enforced preflight still bypassable through `reasoning_core`; source-of-truth not synced; bridge helper absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- The only intended runtime change is a secret-safe preflight bridge for `enforce_secret=True` ingress.
- Reuse legacy `_run_preflight(...)`; do not fork dedup/debounce or edit frozen files.
- Keep the bridge honest about residual duplicate preflight after successful handoff.
