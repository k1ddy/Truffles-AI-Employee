# TP-2026-03-16-consultant-core-pricing-service-clarify-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PRICING-SERVICE-CLARIFY-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MASTER-QUERY-COLLECT-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-collect-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SERVICE-CLARIFY-SEAM-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded collect semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-missing `pricing` turns, но только когда в active conversation snapshot нет usable service referent. Frozen router должен получать уже готовый collect-contract (`intent=pricing`, `action=collect`, `tool_action=info`, `next_question=service`) вместо первого policy-core LLM pass на этих turns, при этом grounded pricing facts, referent-followups, duration/master mixes и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-collect-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '852,950p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '460,555p' truffles-api/app/core/intent_routing.py`
  - `sed -n '477,520p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '9710,9805p' truffles-api/tests/test_message_endpoint.py`
  - `rg -n "pricing_query|need_service|next_question\": \"service\"|open_questions\": \[\"service\"\]" truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - ingress already owns grounded pricing facts via the bounded `pricing_query` snapshot, but generic service-missing pricing turns still fall through to the first policy-core LLM pass inside frozen `decision.py`.
  - current product behavior already accepts a bounded collect contract for generic pricing questions: `intent="pricing"`, `action="collect"`, `tool_action="info"`, `next_question="service"`, `open_questions=["service"]`, `reason="need_service"`.
  - a blind ingress override would be unsafe because active conversation context can already carry a usable service referent; those turns should stay on the downstream referent-aware path instead of being forced into service clarify.
  - `reasoning_core` already resolves a read-only active conversation snapshot before semantic bridge entry, but that snapshot currently does not surface a usable service referent for gating this seam.
- `Detected drift (docs vs code)`: explicit generic pricing questions are still semantic-owned by the first policy-core LLM pass in frozen runtime even though the downstream collect contract already exists and the ingress layer already has the right preflight/snapshot infrastructure to gate a bounded override.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python all function documentation`
- **Date/time (local):** `2026-03-16 14:19 +05`
- **Why this query is precise:** this block needs a tight exclusion/gating chain over neighboring seams and snapshot conditions; the implementation should stay as a short-circuit composition layer rather than another custom branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#all`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `all(iterable)` is the standard short-circuit composition primitive and matches the existing routing-neutral helper style used in `info_signal_service.py`.
- **Decision:** `reuse + integrate` — reuse existing signal helpers, snapshot bridge, and override transport; add only one bounded pricing detector plus one snapshot gate for active service referents.
- **Rejected options:**
  - editing frozen `decision.py` to special-case pricing service clarify
  - adding a broad deictic/referent resolver in this block
  - forcing pricing collect overrides even when an active service referent already exists
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit service-missing pricing turns still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Open `truffles-api/app/core/intent_routing.py` and confirm only grounded pricing facts are bridged today.
  2. Open `truffles-api/tests/test_message_endpoint.py` and confirm current behavior already accepts a bounded collect contract for `Сколько стоит?` style turns.
  3. Open `truffles-api/app/services/reasoning_core.py` and confirm the active conversation snapshot does not yet expose a usable service referent for gating this seam.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded pricing collect override before delegate execution when no active service referent exists
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit generic pricing turns route to `intent="pricing"`, `action="collect"`, `tool_action="info"`, `next_question="service"`, `open_questions=["service"]`, `reason="need_service"`
  - grounded pricing facts remain on the existing fact snapshot path
  - active service-referent conversations do not get this override
  - duration/master mixed turns remain outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress only bridges grounded pricing facts today.
  2. Why does that matter? Because generic pricing questions still depend on the first LLM pass inside frozen runtime.
  3. Why not blindly bridge them? Because active conversation state may already carry a usable service referent, and forcing a collect override there would regress referent-followup behavior.
  4. Why can ingress own this safely now? Because `reasoning_core` already resolves a read-only conversation snapshot and the downstream collect contract is already known and tested.
  5. Why does this reduce drift? Because another explicit collect decision moves out of frozen runtime and into a typed ingress-owned contract with an explicit snapshot gate.
- **Root cause statement:** generic pricing service-clarify semantics remain in frozen `decision.py` because ingress lacks both a bounded service-missing pricing detector and a read-only active-service-referent gate to keep referent-followups on the downstream path.
- **Fix mechanism:**
  - extend the read-only conversation snapshot with a usable service referent projection
  - add a routing-neutral bounded pricing service-clarify detector outside frozen runtime
  - add a bounded pricing collect snapshot branch in `detect_policy_core_route_snapshot(...)` that is disabled when a service referent is present
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot`
  - existing `DialogStateService` service-carryover projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing grounded pricing detector and snapshot branch
  - existing `route_llm_policy_core(...)` schema validation
- **External reuse:**
  - official Python `all(...)` documentation
- **Why not reinvent the wheel:** the repo already has the collect contract, snapshot loading, signal helpers, and override transport; this block only needs a narrow detector plus a snapshot gate.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one snapshot enrichment, one detector, one collect branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden generic pricing turns.
- No override bleed across requests or unrelated message text.
- No pricing collect override when an active usable service referent already exists.
- Grounded pricing facts and neighboring duration/master seams remain unchanged.

## Scope
- Extend the read-only conversation snapshot with a usable service referent projection.
- Add a routing-neutral bounded pricing service-clarify detector outside frozen runtime.
- Add a bounded pricing collect snapshot branch in `detect_policy_core_route_snapshot(...)` gated by the snapshot service-referent signal.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- duration collect bridge
- availability/bookability semantics
- named-master or specialist-availability ownership
- frozen-router edits
- proof-path work
- continuity work beyond read-only snapshot projection

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-service-clarify-policy-override-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
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
2. Extend the read-only conversation snapshot with a usable service-referent projection.
3. Add a routing-neutral detector for explicit service-missing pricing turns.
4. Add the bounded pricing collect snapshot branch and snapshot gate.
5. Add deterministic tests for detection, referent gating, mixed-query exclusion, delegate priming, override consumption, and reset safety.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded pricing collect override before delegate execution when no active service referent exists
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit generic pricing turns route to `intent="pricing"`, `action="collect"`, `tool_action="info"`, `next_question="service"`, `open_questions=["service"]`, `reason="need_service"`
- grounded pricing facts remain on the existing fact path
- active service-referent conversations do not get this override
- duration/master mixed turns remain outside this slice
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- read-only service-referent snapshot in `truffles-api/app/services/reasoning_core.py`
- bounded pricing service-clarify detector in `truffles-api/app/services/info_signal_service.py`
- bounded collect snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or cannot avoid active-referent regressions, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + runtime-contracts + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's signal/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to doc-heavy micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual pricing service-clarify override bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous grounded-pricing-only behavior.

## No-go
- no edits in `truffles-api/app/routers/webhook/decision.py`
- no override when a usable active service referent exists
- no widening into duration collect, availability, or named-master handling
- no proof/continuity side quests in this block

## Риски/блокеры
- the read-only service-referent projection may miss some legacy referent carriers; if so, the block must stay conservatively narrow.
- a too-broad pricing detector could hijack duration/master/mixed turns; exclusion tests are mandatory.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duration collect and broader referent-aware info followups remain frozen-runtime-owned.
- availability/bookability semantics remain outside ingress ownership.

### Why not in this block
- those paths carry additional temporal/referent/follow-up owner semantics and would widen this bounded pricing slice into a much larger migration.

### Risk if deferred
- some generic info collect turns still begin in frozen runtime, so semantic ownership remains split across service-clarify capability families.

### Linked follow-up Task Package(s)
- `TBD: consultant-core-duration-or-availability-collect-bridge-a922`

### Expiry/trigger to stop deferral
- stop deferring once ingress starts bridging the remaining service-clarify info/availability families.

## Next-block contract (mandatory)
### Next block objective
- evaluate the next bounded service-clarify or availability seam after pricing, but only if it can stay outside frozen router files and keep referent safety explicit.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k pricing`

### Blocked-by conditions
- the snapshot gate cannot distinguish active service-referent conversations safely enough
- the collect snapshot needs frozen-router edits to work
- schema validation rejects the override contract

### Owner role for closure
- `Top Architect`
