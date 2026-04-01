# TP-2026-03-15-consultant-core-duplicate-message-preflight-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DUPLICATE-MESSAGE-PREFLIGHT-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SENDER-BRANCH-IGNORE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-sender-branch-ignore-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-PLANNER-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Вырезать следующий shared idempotency slice из legacy runtime: `Duplicate message_id` early return должен собираться в `reasoning_core`, а не только внутри `truffles-api/app/routers/webhook/decision.py`. Новый core будет делать read-only probe существующего дубликата и возвращать тот же deterministic `Duplicate message_id` до legacy delegation, не трогая write-side dedup insertion в legacy path и не обходя legacy secret/skip-persist semantics.

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
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/dedup.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_webhook_dedup.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/dedup.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '300,620p'`
  - `sed -n '164,390p' truffles-api/app/routers/webhook/dedup.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9651,9680p'`
  - `sed -n '1,340p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1,220p' truffles-api/tests/test_webhook_dedup.py`
- `FACT findings`:
  - duplicate-message early return is still owned only by legacy `_handle_dedup_gate(...)` under `truffles-api/app/routers/webhook/dedup.py`, and that helper is called from `truffles-api/app/routers/webhook/decision.py`.
  - `reasoning_core` already owns several ingress slices, but still delegates duplicate-message ownership into legacy runtime after normalization/preflight.
  - the current dedup helper is write-path aware: for non-duplicates it inserts into `message_dedup`, so naively calling it from `reasoning_core` before legacy delegation would create false duplicates on the same request.
  - `reasoning_core` currently does not resolve `client_id`, so any bounded dedup cutover needs a minimal safe client-id lookup before the read-only probe.
- `Detected drift (docs vs code)`: shared ingress ownership claim is still false for duplicate-message idempotency; duplicate skip semantics remain authored in legacy decision runtime.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org sqlalchemy exists select table query 2.0`
- **Date/time (local):** `2026-03-15 16:21 Asia/Almaty`
- **Why this query is precise:** this block needs a read-only existence probe for a preexisting duplicate record before legacy delegation, and the least risky implementation is an existence-style lookup rather than a new write path.
- **Sources opened (from this query):**
  - `SELECT and Related Constructs — SQLAlchemy 2.0 Documentation` — `https://docs.sqlalchemy.org/20/core/selectable.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** SQLAlchemy's `exists()` / existence-query pattern is the canonical way to express a read-only presence check before taking a skip path.
- **Decision:** `reuse + integrate` — add a read-only duplicate probe in `reasoning_core` that checks preexisting dedup evidence, while leaving write-side `message_dedup` insertion in the existing legacy helper for non-duplicate traffic.
- **Rejected options:**
  - reusing `_handle_dedup_gate(...)` directly in `reasoning_core` because it mutates dedup state for non-duplicates
  - adding a skip flag to frozen `truffles-api/app/routers/webhook/decision.py`
  - widening this block into full dedup/debounce ownership transfer
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** `reasoning_core` still cannot author `Duplicate message_id` as a typed contract; duplicate skip ownership remains inside the legacy dedup gate called by `decision.py`.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/reasoning_core.py` and confirm it normalizes input, applies bounded preflight slices, then delegates into `decision_router._handle_webhook_payload(...)`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:9651` and see that duplicate-message ownership still begins in legacy runtime.
  3. Inspect `truffles-api/app/routers/webhook/dedup.py` and see `_handle_dedup_gate(...)` both checks duplicates and writes new dedup state for non-duplicates.
- **Evidence to capture:**
  - typed duplicate-ignore artifact in `reasoning_core`
  - no legacy delegate call when a preexisting duplicate is detected
  - non-duplicate traffic still reaches legacy dedup/write path unchanged
- **Five Whys (or equivalent):**
  1. Why is duplicate ownership still legacy-only? Because the only duplicate skip decision currently sits behind `_handle_dedup_gate(...)` in legacy runtime.
  2. Why not just call that helper earlier? Because it inserts into `message_dedup` for non-duplicates, which would make the same request look duplicate when legacy runtime continues.
  3. Why is that bad? Because it would silently alter normal traffic and break idempotency semantics.
  4. Why is read-only probing the right bounded cut? Because it lets the new core own the duplicate skip outcome without touching write-side dedup behavior for non-duplicates.
  5. Why does this reduce future drift? Because one more shared ingress outcome becomes impossible to author only in `decision.py`.
- **Root cause statement:** duplicate-message skip is trapped inside a legacy helper that mixes read and write dedup responsibilities, so `reasoning_core` cannot own the skip outcome without a separate read-only probe.
- **Fix mechanism:**
  - resolve `client_id` in `reasoning_core` when possible
  - add a read-only preexisting duplicate probe for `message_dedup` / saved inbound messages
  - run that probe only when `enforce_secret=False` and `skip_persist=False`, so the bounded cutover cannot bypass legacy security or skip-persist behavior
  - build a typed duplicate-ignore artifact and return the existing `Duplicate message_id` response before legacy delegation
  - leave legacy write-side dedup path intact for non-duplicates

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/dedup.py` as existing behavior and fast-bypass reference
  - `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official SQLAlchemy existence-query docs
- **Why not reinvent the wheel:** the repo already has canonical duplicate wording, dedup reason name, and write-side dedup ownership; this block only splits out the read-only duplicate skip decision.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded idempotency slice with deterministic tests and no changes to frozen semantic router files.

## Invariant
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- Existing user-visible duplicate wording must remain exactly `Duplicate message_id`.
- Non-duplicate traffic must still reach legacy dedup write path unchanged.
- Secret-enforced and `skip_persist` traffic must not bypass legacy validation/write-path behavior.
- Empty-message/media-normalization/sender-branch-ignore/degrade slices must remain unchanged.

## Scope
- Add read-only preexisting duplicate detection to `reasoning_core`.
- Build a typed duplicate-ignore artifact through the new core contracts.
- Return deterministic `Duplicate message_id` before legacy delegation when the duplicate already exists and the request is not on a secret-enforced or `skip_persist` path.
- Add deterministic tests for the new shared duplicate path and the read-only probe behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- write-side dedup insertion refactor
- debounce/buffer ownership transfer
- any changes in frozen legacy semantic router files
- changing dedup wording, TTL, or backend policy

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-duplicate-message-preflight-slice-a922.md`
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
1. Publish this bounded duplicate-message TP with RCA and one web search.
2. Add a read-only preexisting duplicate probe plus typed duplicate-ignore artifact in `reasoning_core`.
3. Keep non-duplicate traffic delegating into legacy runtime unchanged.
4. Add deterministic tests for the new duplicate path and bypass semantics.
5. Re-run consultant-core checks and sync docs/session state.

## DoD
- `reasoning_core` returns `Duplicate message_id` before legacy delegation when a preexisting duplicate is detected on eligible paths.
- Non-duplicate traffic still delegates to legacy runtime.
- Secret-enforced and `skip_persist` traffic still delegates to legacy runtime unchanged.
- No frozen legacy semantic router file changes are needed.
- Deterministic tests prove the new shared duplicate path and fast-bypass/non-duplicate safeguards.

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
- typed duplicate artifact in `reasoning_core`
- deterministic duplicate/no-delegate test
- deterministic bypass/non-duplicate test
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this slice requires mutating dedup state in `reasoning_core` or touching frozen semantic router files, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded duplicate-message early-return cutover only
- **Go/no-go signals:** reasoning-core tests + runtime-contract tests + packet + arch guard + session check all green
- **Rollback:** revert this TP’s code/doc changes only
- **Post-release monitoring window:** next block may resume richer planner cutover or debounce slice after this exact dedup skip authority is removed from legacy ownership

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual duplicate-message block being executed.

## Rollback
- Revert this TP’s code/doc changes; keep the already-landed governance/runtime-contract/degrade/empty-message/media-normalization/message-compat/sender-ignore blocks intact.

## No-go
- No changes in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`.
- No write-side dedup in `reasoning_core`.
- No behavior changes to debounce/buffer or dedup fast-test bypass policy.
- No wording change for `Duplicate message_id`.

## Risks/Blockers
- `reasoning_core` currently lacks `client_id`, so the read-only probe must resolve it safely without changing missing-client behavior.
- A read-only `message_dedup` query must tolerate environments where the table read fails and degrade to a messages-table fallback.
- Over-eager duplicate probing in fast-test bypass mode would change test/runtime semantics; bypass must remain intact.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only the duplicate-message skip outcome moves; write-side dedup insertion and debounce/buffer logic still live in legacy dedup helpers.
- `Why not in this block`: mixing read/write dedup transfer and debounce transfer would widen scope and raise rollback risk.
- `Risk if deferred`: idempotency authority is still split, even after duplicate skip ownership is reduced.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-next-planner-slice-a922`
- `Expiry/trigger to stop deferral`: before any new dedup/debounce behavior is added to legacy runtime.

## Next-block contract (mandatory)
- `Next block objective`: cut the next richer shared ingress slice after duplicate skip ownership is removed from legacy runtime.
- `First deterministic check command`: `python3 scripts/arch_guard.py && pytest -q truffles-api/tests/test_reasoning_core.py`
- `Blocked-by conditions`: duplicate-message skip still owned only by legacy dedup gate; reasoning-core duplicate path not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen semantic router files in `decision.py`, `booking.py`, `pending.py`
- `Open risks`: accidental write-side dedup in new core, losing fast-test bypass semantics, adding client lookup side effects
- `First command to verify`: `pytest -q truffles-api/tests/test_reasoning_core.py`
