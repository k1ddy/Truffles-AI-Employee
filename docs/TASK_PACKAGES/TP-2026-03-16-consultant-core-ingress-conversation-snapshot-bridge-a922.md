# TP-2026-03-16-consultant-core-ingress-conversation-snapshot-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-INGRESS-CONVERSATION-SNAPSHOT-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONFIRMATION-REFUSAL-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-confirmation-refusal-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Добавить в wrapped ingress read-only active conversation snapshot до delegate execution, чтобы `reasoning_core` опирался на реальный runtime state before planner bridges and stopped priming semantic overrides on turns where legacy routing already forbids bot reply.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-confirmation-refusal-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/conversation_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1070,1505p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,80p' truffles-api/app/services/conversation_service.py`
  - `sed -n '8338,8398p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1115,1365p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - wrapped ingress already primes multiple semantic/runtime overrides before delegate execution, but it does so without loading active conversation state first.
  - frozen `decision.py` still owns the first active-conversation lookup and routing matrix application, including `allow_bot_reply=False` for `manager_active`.
  - existing ingress bridges are cheap, but they still precompute semantic state even when a reused active conversation already forbids bot reply.
  - `reasoning_core` already has read-only helpers for secret-preflight trace conversation lookup, so a bounded snapshot bridge can reuse the same data access seam without touching frozen files.
- `Detected drift (docs vs code)`: target runtime says load dialog state before planner, but current wrapped ingress primes semantic overrides before any active-conversation snapshot exists.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org SQLAlchemy ORM query filter first multiple criteria documentation`
- **Date/time (local):** `2026-03-16 09:25 +05`
- **Why this query is precise:** this block adds a read-only active-conversation lookup in `reasoning_core` and must stay on the supported SQLAlchemy query path for multi-criteria filters before `.first()`.
- **Sources opened (from this query):**
  - `SQLAlchemy ORM Querying Guide — SELECT statements` — `https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** SQLAlchemy's supported pattern is to compose criteria on a select/query object before terminal fetch; this matches the existing repo style of `.query(...).filter(...).first()` for active conversation lookups.
- **Decision:** `reuse + integrate` — add a bounded read-only snapshot helper in `reasoning_core`, reuse existing active-conversation/handover lookup seam from non-frozen services/helpers, and use the snapshot only for gating ingress override priming.
- **Rejected options:**
  - touching frozen `decision.py` to export routing state directly
  - precomputing controller or multi-intent LLM work before active state is known
  - passing a synthetic conversation object through a new mutable side channel
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** wrapped ingress primes semantic override bridges before it knows whether the active conversation already forbids bot reply.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/reasoning_core.py` and observe that intent/domain/runtime override bridges are entered before any active conversation snapshot is loaded.
  2. Open `truffles-api/app/routers/webhook/decision.py` and observe that `ROUTING_MATRIX` forbids bot reply for `manager_active`.
  3. Note that the active conversation is still resolved only inside frozen runtime, after ingress bridges are already primed.
- **Evidence to capture:**
  - `reasoning_core` resolves a read-only active conversation snapshot before delegate execution
  - manager-active snapshots suppress ingress semantic override priming
  - bot-active snapshots preserve current override behavior and reset after delegate exit
- **Five Whys (or equivalent):**
  1. Why does ingress still over-prime semantic state? Because it has no active conversation snapshot before entering override contexts.
  2. Why is that a problem? Because semantic bridges run even on turns where the reused conversation already disables bot replies.
  3. Why not fix it in `decision.py`? Because the router core is frozen.
  4. Why can `reasoning_core` fix it safely? Because conversation lookup is read-only and can gate bridge entry without changing downstream execution.
  5. Why does this reduce drift? Because ingress moves one step closer to `load state before planner` and stops inventing semantic work on ineligible turns.
- **Root cause statement:** current wrapped ingress lacks a read-only active-conversation snapshot step before planner bridges, so semantic override priming happens without the state that decides whether bot reply is even allowed.
- **Fix mechanism:**
  - add a bounded active-conversation snapshot helper in `reasoning_core`
  - derive `allow_bot_reply` from the existing routing matrix rather than duplicating semantics
  - gate current semantic override contexts on the snapshot while keeping delegate behavior unchanged

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `decision_router.find_active_conversation_by_channel_ref(...)` read-only lookup seam
  - existing `ReasoningCore` secret-preflight trace lookup pattern
  - existing request-local override context managers in `reasoning_core`
  - existing `decision_router.ROUTING_MATRIX` as the source of truth for `allow_bot_reply`
- **External reuse:**
  - official SQLAlchemy querying guide
- **Why not reinvent the wheel:** the block adds state loading and gating around existing bridges; it does not introduce a new routing model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `18`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** one bounded code-first seam in `reasoning_core` with focused tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No change to downstream delegate behavior once entered.
- No new LLM calls.
- No new write path; snapshot lookup stays read-only.

## Scope
- Add a read-only active conversation snapshot helper in `truffles-api/app/services/reasoning_core.py`.
- Use the snapshot to gate current ingress semantic override bridges before delegate execution.
- Add deterministic coverage in `truffles-api/tests/test_reasoning_core.py`.
- Sync required canon/session artifacts.

## Out of scope
- controller-route ownership
- multi-intent ownership
- debounce/buffer migration
- booking/pending semantic migration
- proof/eval excision
- continuity-writer changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ingress-conversation-snapshot-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
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
2. Add a read-only active-conversation snapshot helper in `reasoning_core` that can resolve by explicit `conversation_id` or by active remote-jid/client lookup.
3. Derive `allow_bot_reply` from the existing routing matrix and gate current semantic override bridges on that snapshot.
4. Add deterministic runtime tests for manager-active suppression and bot-active preservation.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- wrapped ingress resolves an active conversation snapshot before semantic override bridge entry
- manager-active snapshot suppresses current semantic override priming
- bot-active snapshot preserves current delegate-facing override behavior
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- active-conversation snapshot helper in `truffles-api/app/services/reasoning_core.py`
- delegate-facing gating coverage in `truffles-api/tests/test_reasoning_core.py`
- synced source-of-truth/session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or expands into controller/multi-intent ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** read-only snapshot + bounded gating of already-existing ingress bridges
- **Go/no-go signals:** reasoning-core tests + runtime-contract tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's reasoning-core/test/doc changes only; keep earlier ingress bridges intact
- **Post-release monitoring window:** next block should consume the snapshot for a richer semantic seam, not add more ungated bridges

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual ingress conversation snapshot bridge being executed.

## Rollback
- Revert this TP's `reasoning_core.py`, test, and doc changes; keep prior ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new write path for conversation state.
- No new synthetic routing matrix or duplicate semantic constants if existing runtime sources can be reused.

## Risks/Blockers
- if snapshot lookup diverges from legacy active-conversation lookup, ingress gating may disagree with delegate state.
- if gating is too broad, existing bot-active or pending turns may lose current override priming.
- if this block expands into controller or multi-intent ownership, it exceeds bounded scope and must be split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: controller-route ownership, multi-intent ownership, action-resolution ownership, debounce/buffer, and the main planner/happy-path semantics still live behind frozen `decision.py`; continuity and proof-path larger debt remain.
- `Why not in this block`: this block only installs the state-loading seam needed before richer semantic bridges; it intentionally avoids new LLM work or frozen-router edits.
- `Risk if deferred`: ingress keeps priming semantic work without the conversation state that decides whether bot reply is even allowed.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming wrapped ingress owns richer controller/action routing or before adding any new semantic bridge that depends on active conversation state.

## Next-block contract (mandatory)
- `Next block objective`: consume the ingress conversation snapshot for the next richer semantic seam, likely controller-route or another planner bridge, without touching frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: snapshot does not match legacy active conversation reuse; manager-active gating leaks overrides; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
