# TP-2026-03-16-consultant-core-confirmation-refusal-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONFIRMATION-REFUSAL-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROTECTIVE-LEXICAL-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-protective-lexical-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded lexical-response seam из frozen runtime в wrapped ingress: `reasoning_core` должен заранее вычислять confirmation decision и refusal flags and pass them through the existing request-scoped signal override, so frozen runtime consumes precomputed lexical confirmation/refusal state instead of owning the first pass itself.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-protective-lexical-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_ai_service.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/ai_service.py`
  - `truffles-api/tests/test_ai_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1958,2035p' truffles-api/app/services/ai_service.py`
  - `sed -n '1,110p' truffles-api/app/core/intent_routing.py`
  - `sed -n '11220,11395p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1115,1165p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still makes first-pass direct calls to `classify_confirmation(...)` and `detect_refusal_flags(...)` in live routing branches.
  - both classifiers already live in reusable `truffles-api/app/services/ai_service.py` and are pure deterministic lexical helpers.
  - wrapped ingress already primes request-local `use_intent_signal_override(...)`, so this seam can be moved without adding a new override channel.
  - unlike the multi-intent LLM seam, this block does not introduce extra LLM work or booking-budget drift; it is safe to precompute on every inbound.
- `Detected drift (docs vs code)`: ingress owns greeting/thanks/ack/low-signal/status/protective lexical flags, but confirmation/refusal lexical routing still begins inside frozen runtime.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python contextvars ContextVar reset token documentation`
- **Date/time (local):** `2026-03-16 09:09 +05`
- **Why this query is precise:** this block extends the existing request-scoped override payload and must keep async-local reset safety exact.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` / `reset(token)` is the correct async-task-local mechanism for per-request override expansion.
- **Decision:** `reuse + integrate` — widen the existing intent-signal override payload rather than introducing a new mutable side channel.
- **Rejected options:**
  - editing frozen `decision.py` to bypass confirmation/refusal logic directly
  - a second parallel confirmation/refusal override channel
  - jumping straight to multi-intent override, which would precompute extra LLM work on paths that still skip it inside legacy runtime
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** frozen runtime still owns the first confirmation/refusal lexical pass.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/ai_service.py` and observe that `classify_confirmation(...)` and `detect_refusal_flags(...)` are deterministic helpers.
  2. Open `truffles-api/app/routers/webhook/decision.py` and observe direct calls to those helpers in ASR confirmation, memory consent, and slot/refusal routing branches.
  3. Open `truffles-api/app/services/reasoning_core.py` and observe that the current signal override bridge does not carry confirmation or refusal payload.
- **Evidence to capture:**
  - wrapped ingress computes confirmation and refusal payload before delegate execution
  - `classify_confirmation(...)` and `detect_refusal_flags(...)` consume request-scoped override state for matching normalized text
  - override state resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is frozen runtime still semantically busy? Because confirmation/refusal lexical decisions still start there.
  2. Why does that matter? Because those decisions steer active confirmation flows and slot refusal routing before later runtime branches.
  3. Why not edit `decision.py`? Because it is frozen.
  4. Why can a bridge work? Because these helpers are deterministic and the request-local signal override channel already exists.
  5. Why does this reduce drift? Because another repeated lexical authority moves into wrapped ingress and frozen runtime only consumes precomputed state.
- **Root cause statement:** confirmation/refusal authority remains in frozen runtime because the current ingress signal override does not carry those lexical results into `ai_service` before delegate execution.
- **Fix mechanism:**
  - extend `app/core/intent_routing.py` to capture confirmation decision and refusal flags
  - extend `ai_service.py` override consumption for `classify_confirmation(...)` and `detect_refusal_flags(...)`
  - reuse the existing `reasoning_core` signal override bridge so delegate execution sees the richer payload

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `use_intent_signal_override(...)` request-local bridge
  - existing `classify_confirmation(...)` and `detect_refusal_flags(...)` helpers
  - existing `detect_intent_routing_primitives(...)` ingress bridge structure
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** this block only widens an existing override payload with already-existing lexical helpers.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `17`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded deterministic bridge with focused tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No override bleed across requests or unrelated text.
- No change to lexical heuristic definitions themselves in this block.
- No new LLM calls or booking-budget changes.

## Scope
- Extend `truffles-api/app/core/intent_routing.py` with confirmation decision and refusal flags.
- Extend `truffles-api/app/services/ai_service.py` so `classify_confirmation(...)` and `detect_refusal_flags(...)` consume the request-scoped signal override.
- Reuse the existing wrapped-ingress signal override bridge; no new override channel.
- Add deterministic tests in `truffles-api/tests/test_ai_service.py` and `truffles-api/tests/test_reasoning_core.py`.
- Sync required canon/session artifacts.

## Out of scope
- multi-intent override
- controller-route or action-resolution bridge work
- domain-router changes
- debounce/buffer migration
- booking/pending runtime migration
- proof/eval excision

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-confirmation-refusal-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/tests/test_ai_service.py`
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
2. Extend `app/core/intent_routing.py` to capture confirmation and refusal lexical payload.
3. Extend `ai_service.py` so `classify_confirmation(...)` and `detect_refusal_flags(...)` consume the request-scoped signal override for matching text.
4. Reuse the current wrapped-ingress signal override bridge so the delegate sees the richer payload without touching `reasoning_core.py`.
5. Add deterministic service/runtime tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- wrapped ingress scopes confirmation and refusal lexical state before delegate execution
- `classify_confirmation(...)` and `detect_refusal_flags(...)` consume request-scoped signal override state for matching normalized text
- override state resets after delegate exit and does not apply to unrelated text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_ai_service.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- richer lexical detector in `truffles-api/app/core/intent_routing.py`
- override consumption in `truffles-api/app/services/ai_service.py`
- delegate-facing coverage in `truffles-api/tests/test_reasoning_core.py`
- synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or expands into multi-intent/controller ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** widen the existing request-scoped signal override only
- **Go/no-go signals:** reasoning-core + ai-service tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep prior ingress bridges intact
- **Post-release monitoring window:** next block should be either multi-intent with proven bounded gating or controller-route, not more arbitrary micro-bridges

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual confirmation/refusal bridge being executed.

## Rollback
- Revert this TP's `intent_routing.py`, `ai_service.py`, test, and doc changes; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new lexical heuristics or phrase-hardcodes beyond reusing existing helper outputs.
- No new override channel for confirmation/refusal.

## Risks/Blockers
- if override matching is too broad, unrelated text may consume stale confirmation/refusal state.
- if confirmation/refusal precedence diverges from existing helpers, direct guard calls and old tests may disagree.
- if this block expands into multi-intent/controller ownership, it exceeds bounded scope and must be split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: multi-intent decomposition, controller-route ownership, class-router result ownership, action-resolution ownership, and booking/pending semantics still live in frozen `decision.py`; debounce/buffer remains legacy-owned.
- `Why not in this block`: this block only moves another deterministic lexical response seam and avoids precomputing new LLM work.
- `Risk if deferred`: frozen runtime keeps owning confirmation/refusal lexical routing seams after the current ingress bridges.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-multi-intent-override-a922`
- `Expiry/trigger to stop deferral`: before claiming ingress owns the full early lexical-response seam.

## Next-block contract (mandatory)
- `Next block objective`: move the next richer semantic seam, likely multi-intent decomposition with proven bounded gating or controller-route ownership, without touching frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: override state not text-scoped; confirmation/refusal precedence mismatch; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
