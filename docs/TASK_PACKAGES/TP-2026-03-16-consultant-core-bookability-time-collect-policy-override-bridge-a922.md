# TP-2026-03-16-consultant-core-bookability-time-collect-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOOKABILITY-TIME-COLLECT-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DURATION-SERVICE-CLARIFY-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-service-clarify-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-BOOKABILITY-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded collect semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit time-only booking followup turns, но только когда read-only active conversation snapshot уже несёт usable `service_referent` и `booking_active=True`. Frozen router должен получать уже готовый collect-contract (`intent=booking`, `action=collect`, `tool_action=calendar.list_slots`, `next_question=datetime`) вместо первого policy-core LLM pass на этих turns, при этом grounded duration/pricing/master/hours/location/promotions/contact seams, live availability ownership и frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-service-clarify-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

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
  - `sed -n '284,548p' truffles-api/app/core/intent_routing.py`
  - `sed -n '500,590p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '1668,1705p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '660,740p' truffles-api/tests/test_intent.py`
  - `sed -n '2535,2695p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - ingress already owns service-referent projection and service-missing collect bridges for `pricing`, `duration`, and `master_query`, but explicit time-only bookability followups with an active service referent still depended on the first policy-core LLM pass inside frozen `decision.py`.
  - the active conversation snapshot already exposes both `booking_active` and `service_referent`, so this slice can stay bounded and avoid widening into live availability ownership.
  - the request-scoped policy override seam already transports `slots`, `next_question`, `open_questions`, `subject_kind`, `resolution_mode`, and `temporal_scope`, so no new override transport is required.
  - downstream frozen runtime already accepts `calendar.list_slots` collect contracts with `temporal_scope`, so ingress can safely prime the exact contract without editing frozen files.
- `Detected drift (docs vs code)`: time-only booking followups under active booking context remained semantic-owned by the first policy-core LLM pass in frozen runtime even though the active booking gate, service referent projection, and request-scoped override seam already existed.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any function documentation`
- **Date/time (local):** `2026-03-16 15:59 +05`
- **Why this query is precise:** this block needs a short-circuit exclusion chain over neighboring info/booking seams and active snapshot gates; the implementation should stay a small composition layer instead of another branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `any(iterable)` remains the standard short-circuit composition primitive and matches the existing routing-neutral helper style already used in `info_signal_service.py`.
- **Decision:** `reuse + integrate` — reuse existing booking/date/time signal helpers, the read-only active conversation snapshot, and the request-scoped policy override seam; add only one bounded bookability detector plus one snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case time-only booking followups
  - widening this block into live availability or specialist-availability ownership
  - priming the override when no active booking/service referent exists
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit time-only booking followups such as `В какое время можно записаться?` still started with the first policy-core LLM pass inside frozen runtime even when the active conversation already carried `booking_active=True` and a usable service referent.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True` and `service_referent="Маникюр"`.
  2. Send `В какое время можно записаться?` through `reasoning_core`.
  3. Observe that, before this block, ingress had no bounded collect snapshot for missing temporal scope and delegated the first semantic decision to frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded bookability collect override before delegate execution when `booking_active=True` and a usable `service_referent` exists
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit time-only booking followups route to `intent="booking"`, `action="collect"`, `tool_action="calendar.list_slots"`, `next_question="datetime"`, `open_questions=["datetime"]`, `reason="missing_temporal_scope"`, `temporal_scope="none"`
  - turns with explicit time/date scope do not get this override
  - turns without active booking do not get this override
  - explicit service-in-text, pricing/duration/master/hours/location/promotions/contact neighbor seams stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why was this seam still legacy-owned? Because ingress only bridged service-missing collect and grounded fact seams, not active-booking time-only followups.
  2. Why does that matter? Because frozen `decision.py` still owned the first semantic decision for a common booking continuation turn.
  3. Why not bridge all availability now? Because broader live availability and specialist routing carry extra temporal and execution semantics that would widen this block too far.
  4. Why can ingress own this safely now? Because the read-only snapshot already exposes `booking_active` and `service_referent`, and downstream collect behavior already accepts the exact contract shape.
  5. Why does this reduce drift? Because another explicit collect decision moves out of frozen runtime and into a typed ingress-owned contract with explicit state gating.
- **Root cause statement:** active-booking time-only bookability followups remained in frozen `decision.py` because ingress lacked a bounded missing-temporal-scope detector, even though the active booking snapshot gate and request-scoped override seam already existed.
- **Fix mechanism:**
  - add a routing-neutral bounded detector for explicit time-only booking followups without temporal scope
  - add a bounded bookability collect snapshot branch in `detect_policy_core_route_snapshot(...)` gated by `booking_active` and active `service_referent`
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ReasoningCoreConversationSnapshot.booking_active`
  - existing `ReasoningCoreConversationSnapshot.service_referent`
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing booking/date/time helpers: `extract_time_token(...)`, `has_explicit_date_signal(...)`, `normalize_resolved_datetime_value(...)`, `has_pending_time_question_marker(...)`
  - existing routing-neutral helpers for neighboring seams: `looks_like_services_overview_message(...)`, `detect_location_policy_pack_refs(...)`, `looks_like_hours_policy_message(...)`, `looks_like_promotions_rules_policy_message(...)`, `looks_like_promotions_policy_message(...)`, `looks_like_contact_policy_message(...)`, `_has_price_signal(...)`, `_has_duration_signal(...)`, `resolve_master_intent(...)`, `get_pack_service_hint(...)`
  - existing `route_llm_policy_core(...)` schema validation and reset-safe override transport
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the snapshot gate, booking lexicon helpers, and collect-contract transport; this block only needs a narrow bookability detector plus one collect snapshot branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `23`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one detector, one collect branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden time-only active-booking followups.
- No override bleed across requests or unrelated message text.
- No override when `booking_active=False` or no usable active service referent exists.
- No widening into live availability, specialist routing, or broader scheduling execution ownership.

## Scope
- Add a routing-neutral bounded detector for explicit time-only booking followups without temporal scope.
- Add a bounded bookability collect snapshot branch in `detect_policy_core_route_snapshot(...)` gated by active booking plus active service referent.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- live availability slot execution ownership
- specialist-availability ownership
- broader booking planner migration
- frozen-router edits
- proof-path work
- continuity work beyond the existing read-only active booking/service referent projection

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-bookability-time-collect-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
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
1. Publish this TP with RCA and the required single web search.
2. Add a routing-neutral detector for explicit time-only booking followups without temporal scope.
3. Add the bounded bookability collect snapshot branch and active-state gate.
4. Add deterministic tests for detection, booking-state gating, temporal-scope exclusion, service-in-text exclusion, delegate priming, override consumption, and reset safety.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded bookability collect override before delegate execution when active booking plus active service referent exist
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit time-only booking followups route to `intent="booking"`, `action="collect"`, `tool_action="calendar.list_slots"`, `next_question="datetime"`, `open_questions=["datetime"]`, `reason="missing_temporal_scope"`, `temporal_scope="none"`
- explicit time/date scope turns remain outside this slice
- no active-booking/service-referent state means no override
- neighboring pricing/duration/master/hours/location/promotions/contact seams remain unchanged
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
- bounded bookability time-only detector in `truffles-api/app/services/info_signal_service.py`
- bounded collect snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into live availability/specialist ownership, stop and split
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
  - active block metadata must match the actual bookability time-collect override bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/reasoning_core.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous duration/pricing/master-only collect behavior.

## No-go
- no edits in `truffles-api/app/routers/webhook/decision.py`
- no edits in `truffles-api/app/routers/webhook/booking.py`
- no edits in `truffles-api/app/routers/webhook/pending.py`
- no override when active booking or active service referent is missing
- no widening into live availability, specialist routing, or mixed duration/price bundles
- no proof/continuity side quests in this block

## Риски/блокеры
- a too-broad detector could hijack hours or live availability turns that need richer temporal semantics.
- a detector that ignores explicit service-in-text or temporal-scope signals could regress existing grounded booking and scheduling flows.
- stale legacy booking carriers may still expose weak service hints; this slice must stay conservative and prefer `None` over false positives.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader live availability and specialist-availability ownership remain frozen-runtime-owned.
- booking followups with explicit temporal scope still rely on frozen runtime for richer temporal interpretation.
- debounce/buffer and broader planner outcome seams remain outside ingress ownership.

### Why not in this block
- those paths combine live scheduling execution, richer temporal arbitration, and broader booking planner semantics that would widen this bounded time-only followup slice into a much larger migration.

### Risk if deferred
- active-booking followups are only partially ingress-owned until adjacent availability and richer booking planner seams are migrated.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-availability-bookability-policy-override-evaluation-a922.md` (planned)

### Expiry/trigger to stop deferral
- stop deferral once the next bounded bookability/availability seam can be expressed without taking live scheduling execution ownership.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether a bounded bookability/availability seam beyond time-only followups can migrate next without widening into live scheduling execution or frozen booking ownership.
- **First deterministic check command:** `rg -n "calendar.list_slots|temporal_scope|live_availability|available|bookability" truffles-api/app/services/info_signal_service.py truffles-api/app/core/intent_routing.py truffles-api/app/services/intent_service.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py`
- **Blocked-by conditions:** bookability time-collect bridge must land green first; the next seam must prove a routing-neutral bounded detector outside frozen runtime and avoid taking live slot execution ownership.
- **Owner role for closure:** `Top Architect`
