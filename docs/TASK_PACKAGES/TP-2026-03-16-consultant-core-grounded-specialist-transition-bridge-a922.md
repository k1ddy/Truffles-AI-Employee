# TP-2026-03-16-consultant-core-grounded-specialist-transition-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-GROUNDED-SPECIALIST-TRANSITION-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SPECIALIST-DATE-RANGE-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-specialist-date-range-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-SPECIALIST-AVAILABILITY-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий richer bounded specialist-availability seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit grounded specialist turns вида `А какие мастера доступны?`, но только когда read-only active conversation snapshot уже несёт `booking_active=True`, usable `service_referent`, usable active booking datetime value, и `reply_slot=time`. Frozen router должен получать уже готовый collect-contract (`next_question=name`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=specific_time`, `resolution_mode=referent_followup`, `pending_question_target=specialist`, `active_question_relation=specialist_availability_followup`) вместо первого policy-core LLM pass на этих turns, при этом specialist date-range followups, active-name booking-time followups, and frozen router files остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-specialist-date-range-followup-bridge-a922.md`
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
  - `sed -n '24914,25110p' truffles-api/tests/test_message_endpoint.py`
  - `sed -n '780,900p' truffles-api/app/core/intent_routing.py`
  - `sed -n '860,980p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '880,940p' truffles-api/app/services/reasoning_core.py`
  - `python3 - <<'PY' ... resolve_master_intent("А какие мастера доступны?") ... PY`
- `FACT findings`:
  - frozen `decision.py` already preserves the downstream contract for grounded specialist transition to `next_question=name`, `subject_kind=specialist`, `capability=live_availability`, `temporal_scope=specific_time`, `pending_question_target=specialist`, and `active_question_relation=specialist_availability_followup`.
  - ingress currently has no read-only snapshot field for the raw active booking datetime value; it only projects `booking_time_token`, which is insufficient for grounded specialist transition because the downstream preserved contract needs the original booking datetime value such as `завтра`.
  - `test_llm_policy_core_grounded_specialist_availability_transitions_to_name_collect` already proves the downstream contract for `А какие мастера доступны?` under active booking/service/datetime context.
  - the current specialist date-range bridge already proved that explicit specialist cues can be safely combined with active booking/service snapshot anchors and request-scoped overrides without frozen-router edits.
- `Detected drift (docs vs code)`: the next contract-compatible specialist seam is the grounded specialist transition, and ingress still lacks the read-only snapshot parity needed to precompute its collect contract before delegate execution.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org 3.12 dataclasses field default documentation`
- **Date/time (local):** `2026-03-16 18:01 +0500`
- **Why this query is precise:** this block extends a frozen read-only snapshot dataclass by one optional projection field; the implementation must stay default-safe and immutable without introducing mutable state carriers.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python 3.12 documentation` — `https://docs.python.org/3.12/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python dataclasses support adding defaulted fields on frozen dataclasses cleanly; this matches the need for one optional read-only snapshot projection without changing mutability semantics.
- **Decision:** `reuse + integrate` — reuse the existing conversation snapshot builder, request-scoped policy override seam, master-intent resolution, and downstream preserved specialist-followup contract; add only one read-only snapshot projection and one bounded grounded-specialist detector/branch.
- **Rejected options:**
  - editing frozen `decision.py` to special-case grounded specialist transition
  - widening this block into weekend/date-range specialist ownership
  - widening this block into generic specialist recommendation or master-query execution ownership
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit grounded specialist availability followups under active booking/service/datetime context still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Load an active conversation snapshot with `booking_active=True`, `service_referent="Маникюр"`, `booking.datetime="завтра"`, and `reply_slot="time"`.
  2. Send `А какие мастера доступны?` through `reasoning_core`.
  3. Observe that ingress currently lacks a raw booking-datetime snapshot projection and a bounded grounded-specialist branch, so the first semantic decision still falls into frozen `decision.py`.
- **Evidence to capture:**
  - `reasoning_core` projects the active booking datetime value into a read-only snapshot field without adding writers
  - ingress primes a bounded grounded-specialist override before delegate execution when the snapshot gating matches
  - `route_llm_policy_core(...)` consumes that override without provider init
  - explicit grounded specialist turns route to `goal="booking"`, `next_question="name"`, `open_questions=["name"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, `resolution_mode="referent_followup"`, `pending_question_target="specialist"`, and `active_question_relation="specialist_availability_followup"`
  - turns without active booking datetime value do not get this override
  - specialist date-range followups stay outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress does not yet project the active booking datetime value needed to form the preserved specialist-followup contract.
  2. Why is `booking_time_token` insufficient? Because the downstream grounded specialist contract uses the full active booking datetime value like `завтра`, not only an exact time token.
  3. Why is grounded specialist transition the next safe seam? Because frozen downstream already preserves the exact `specialist_availability_followup` owner shape for this case and repo tests already prove it.
  4. Why can ingress own it safely now? Because the active service referent, reply slot, and booking-active state are already projected read-only, and only one more read-only datetime projection is missing.
  5. Why does this reduce drift? Because another richer booking collect contract moves out of frozen runtime and into a typed ingress-owned override without changing execution ownership or adding continuity writers.
- **Root cause statement:** grounded specialist availability transition remained in frozen `decision.py` because ingress lacked the read-only active booking datetime projection and the narrow detector needed to combine the existing explicit specialist cue with active booking/service snapshot anchors into one bounded collect override before delegate execution.
- **Fix mechanism:**
  - add one read-only active booking datetime projection to `ReasoningCoreConversationSnapshot`
  - add a narrow detector for explicit grounded specialist availability followups with neighbor-seam exclusions
  - emit a bounded policy snapshot branch keyed by active service referent + active booking datetime + `reply_slot=time`
  - verify priming, exclusion, and reset safety through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing active conversation snapshot builder and `service_referent` projection
  - existing request-scoped `PolicyCoreRouteSnapshot` / policy override seam
  - existing `resolve_master_intent(...)` signal resolution
  - existing routing-neutral exclusions for services-overview, location, hours, promotions, contact, duration, pricing, and reschedule/cancel neighbors
  - existing frozen downstream specialist-followup contract evidenced in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python dataclasses documentation
- **Why not reinvent the wheel:** the repo already has the override transport, specialist-followup downstream contract, and most snapshot anchors; this block only needs one extra read-only snapshot field and one bounded grounded-specialist detector/branch.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one read-only snapshot extension, one detector, one snapshot branch, focused tests, and required canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden grounded specialist turns.
- No override bleed across requests or unrelated message text.
- No override when active booking datetime value is absent.
- No widening into specialist date-range/weekend ownership or generic specialist recommendation.

## Scope
- Add one read-only active booking datetime projection to `ReasoningCoreConversationSnapshot`.
- Add a narrow detector for explicit grounded specialist availability followups.
- Add a bounded policy snapshot branch that reuses active booking/service snapshot anchors.
- Add deterministic tests.
- Sync required canon/session artifacts.

## Out of scope
- specialist weekend/date-range seams beyond the already-closed slice
- active-name booking-time followups
- generic specialist recommendation routing
- live slot execution ownership
- frozen-router edits
- proof-path work
- continuity work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-grounded-specialist-transition-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
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
1. Publish this TP with RCA and the required single web search.
2. Add one read-only active booking datetime projection and a bounded grounded-specialist detector/snapshot branch.
3. Add deterministic tests for detection, snapshot gating, neighbor exclusions, delegate priming, override consumption, and reset safety.
4. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` projects a read-only active booking datetime value into the conversation snapshot without adding writers
- `reasoning_core` primes a bounded grounded-specialist override before delegate execution when the snapshot gating matches
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit grounded specialist turns route to `next_question="name"`, `open_questions=["name"]`, `subject_kind="specialist"`, `capability="live_availability"`, `temporal_scope="specific_time"`, and `resolution_mode="referent_followup"`
- turns without active booking datetime value do not get this override
- specialist date-range followups stay outside this slice
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
- read-only booking datetime projection in `truffles-api/app/services/reasoning_core.py`
- bounded grounded-specialist detector in `truffles-api/app/services/info_signal_service.py`
- bounded followup snapshot in `truffles-api/app/core/intent_routing.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice needs frozen-router edits or widens into weekend/date-range specialist ownership or adds continuity writers, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + runtime-contracts + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's snapshot/signal/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to doc-heavy micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual grounded specialist transition bridge being executed.

## Rollback
1. Revert `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/services/info_signal_service.py`, `truffles-api/app/core/intent_routing.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous bridges only.

## No-go
- no edits to `truffles-api/app/routers/webhook/decision.py`
- no live slot execution or alternate-slot generation in ingress
- no widening this detector into weekend/date-range specialist turns or generic master recommendation in the same block
- no return to proof/continuity micro-slices inside this block

## Риски/блокеры
- grounded specialist wording can overlap with generic master-query or booking-info seams if the detector is widened carelessly
- downstream preservation still depends on the frozen specialist-followup owner predicate, so the snapshot contract must stay exact

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - specialist weekend turns remain frozen-runtime owned
  - broader booking outcome semantics still remain in frozen `decision.py`
  - continuity is still not a single writer
- **Why not in this block:**
  - each of those surfaces would widen this bounded bridge into a mixed semantic/execution or continuity refactor
- **Risk if deferred:**
  - neighboring specialist availability families remain in frozen runtime a bit longer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-next-specialist-availability-seam-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next specialist seam can reuse the same snapshot anchors without new writers

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded specialist-availability seam after grounded specialist transition, prioritizing weekend specialist followups only if they can remain read-only and contract-compatible with the existing specialist owner predicate
- **First deterministic check command:** `pytest -q truffles-api/tests/test_intent.py -k specialist`
- **Blocked-by conditions:**
  - if the next seam needs frozen-router edits
  - if the next seam requires new continuity writers
  - if the next seam cannot preserve contract compatibility with the existing specialist followup owner predicate
- **Owner role for closure:** `Top Architect`
