# TP-2026-03-16-consultant-core-duration-service-clarify-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DURATION-SERVICE-CLARIFY-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PRICING-SERVICE-CLARIFY-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-service-clarify-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SERVICE-DEPENDENT-INFO-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded collect semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-missing `duration` turns, но только когда в active conversation snapshot нет usable service referent. Frozen router должен получать уже готовый collect-contract (`intent=duration`, `action=collect`, `tool_action=info`, `next_question=service`) вместо первого policy-core LLM pass на этих turns, при этом grounded duration facts, referent-followups, pricing/master/hours mixes и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-service-clarify-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_llm_policy_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '468,548p' truffles-api/app/core/intent_routing.py`
  - `sed -n '427,520p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '590,665p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '240,255p' truffles-api/tests/test_llm_policy_core.py`
  - `sed -n '2287,2405p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - ingress already owns grounded duration facts via the bounded `duration_info` snapshot, but generic service-missing duration turns still fall through to the first policy-core LLM pass inside frozen `decision.py`.
  - current product behavior already accepts service clarify for duration-dependent info via `duration_or_price_clarify` / `missing_service_query`, and deterministic tests already codify that `duration` is a service-dependent info intent.
  - the new snapshot gate from the pricing collect block already exposes a usable active `service_referent`, so this seam can stay bounded and avoid regressing referent-followups.
  - the request-scoped policy override seam already transports `next_question`, `open_questions`, `subject_kind`, and `resolution_mode`, so no new override transport is required.
- `Detected drift (docs vs code)`: explicit generic duration questions are still semantic-owned by the first policy-core LLM pass in frozen runtime even though the downstream collect behavior and the ingress snapshot gate already exist.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any function documentation`
- **Date/time (local):** `2026-03-16 14:35 +05`
- **Why this query is precise:** this block needs a tight exclusion chain over neighboring seams and snapshot conditions; the implementation should stay as a short-circuit composition layer rather than another custom branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `any(iterable)` is the standard short-circuit composition primitive and matches the existing routing-neutral helper style used in `info_signal_service.py`.
- **Decision:** `reuse + integrate` — reuse existing signal helpers, active-service snapshot gating, and request-scoped policy override transport; add only one bounded duration detector plus one snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case duration service clarify
  - adding a broad referent resolver in this block
  - forcing duration collect overrides even when an active service referent already exists
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit service-missing duration turns still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Open `truffles-api/app/core/intent_routing.py` and confirm only grounded duration facts are bridged today.
  2. Open `truffles-api/tests/test_llm_policy_core.py` and confirm `duration` is already treated as a service-dependent info intent.
  3. Open `truffles-api/app/services/reasoning_core.py` and confirm the read-only conversation snapshot already exposes a usable service referent gate from the pricing block.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded duration collect override before delegate execution when no active service referent exists
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit generic duration turns route to `intent="duration"`, `action="collect"`, `tool_action="info"`, `next_question="service"`, `open_questions=["service"]`, `reason="need_service"`
  - grounded duration facts remain on the existing fact snapshot path
  - active service-referent conversations do not get this override
  - pricing/master/hours mixed turns remain outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress only bridges grounded duration facts today.
  2. Why does that matter? Because generic duration questions still depend on the first LLM pass inside frozen runtime.
  3. Why not blindly bridge them? Because active conversation state may already carry a usable service referent, and forcing a collect override there would regress referent-followup behavior.
  4. Why can ingress own this safely now? Because the read-only conversation snapshot already projects a usable service referent and the downstream collect behavior already exists.
  5. Why does this reduce drift? Because another explicit collect decision moves out of frozen runtime and into a typed ingress-owned contract with an explicit snapshot gate.
- **Root cause statement:** generic duration service-clarify semantics remain in frozen `decision.py` because ingress lacks a bounded service-missing duration detector, even though the active-service gate and request-scoped override seam already exist.
- **Fix mechanism:**
  - add a routing-neutral bounded duration service-clarify detector outside frozen runtime
  - add a bounded duration collect snapshot branch in `detect_policy_core_route_snapshot(...)` gated by the snapshot service-referent signal
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.service_referent`
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing grounded duration detector and snapshot branch
  - existing routing-neutral helpers `_has_duration_signal(...)`, `_has_price_signal(...)`, `looks_like_services_overview_message(...)`, `looks_like_hours_policy_message(...)`, `detect_location_policy_pack_refs(...)`, `looks_like_promotions_policy_message(...)`, `looks_like_promotions_rules_policy_message(...)`, `looks_like_contact_policy_message(...)`, and `resolve_master_intent(...)`
  - existing `route_llm_policy_core(...)` schema validation
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the collect contract, active-service gate, signal helpers, and override transport; this block only needs a narrow duration detector plus one collect snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one collect branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden generic duration turns.
- No override bleed across requests or unrelated message text.
- No duration collect override when an active usable service referent already exists.
- Grounded duration facts and neighboring pricing/master/hours seams remain unchanged.

## Scope
- Add a routing-neutral bounded duration service-clarify detector outside frozen runtime.
- Add a bounded duration collect snapshot branch in `detect_policy_core_route_snapshot(...)` gated by the snapshot service-referent signal.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- pricing collect changes
- availability/bookability semantics
- named-master or specialist-availability ownership
- frozen-router edits
- proof-path work
- continuity work beyond the existing read-only service-referent projection

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-service-clarify-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
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
2. Add a routing-neutral detector for explicit service-missing duration turns.
3. Add the bounded duration collect snapshot branch and snapshot gate.
4. Add deterministic tests for detection, referent gating, mixed-query exclusion, delegate priming, override consumption, and reset safety.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded duration collect override before delegate execution when no active service referent exists
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit generic duration turns route to `intent="duration"`, `action="collect"`, `tool_action="info"`, `next_question="service"`, `open_questions=["service"]`, `reason="need_service"`
- grounded duration facts remain on the existing fact path
- active service-referent conversations do not get this override
- pricing/master/hours mixed turns remain outside this slice
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
- bounded duration service-clarify detector in `truffles-api/app/services/info_signal_service.py`
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
  - active block metadata must match the actual duration service-clarify override bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous grounded-duration-only behavior.

## No-go
- no edits in `truffles-api/app/routers/webhook/decision.py`
- no edits in `truffles-api/app/routers/webhook/booking.py`
- no edits in `truffles-api/app/routers/webhook/pending.py`
- no override when a usable active service referent exists
- no widening into availability, named-master handling, or mixed price/duration bundles
- no proof/continuity side quests in this block

## Риски/блокеры
- a too-broad duration detector could hijack hours/work-schedule turns that must stay outside this slice.
- a duration detector that ignores price overlap could widen into mixed duration+price arbitration.
- legacy followup carriers may still surface weak service hints; this block must stay conservative and prefer `None` over false positives.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- pricing+duration mixed arbitration remains frozen-runtime-owned.
- availability/bookability and specialist-availability semantics remain outside ingress ownership.
- broader referent-followup info handling still depends on frozen runtime.

### Why not in this block
- those paths carry additional temporal, followup, and multi-intent owner semantics and would widen this bounded duration slice into a much larger migration.

### Risk if deferred
- generic duration questions remain only partially ingress-owned until adjacent mixed-info and availability seams are migrated.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-availability-policy-override-evaluation-a922.md` (planned)

### Expiry/trigger to stop deferral
- stop deferral once the next service-dependent info seam requires shared price+duration arbitration or live availability routing.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether a bounded availability/bookability seam can be migrated next without widening into live scheduling or frozen booking ownership.
- **First deterministic check command:** `rg -n "bookability|live_availability|calendar.list_slots|available" truffles-api/app/services/intent_service.py truffles-api/app/routers/webhook/info.py truffles-api/app/core/intent_routing.py`
- **Blocked-by conditions:** duration service-clarify block must land green first; next seam must prove a routing-neutral bounded detector outside frozen runtime.
- **Owner role for closure:** `Top Architect`
