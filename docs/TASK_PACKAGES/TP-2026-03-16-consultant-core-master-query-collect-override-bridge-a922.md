# TP-2026-03-16-consultant-core-master-query-collect-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MASTER-QUERY-COLLECT-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PORTFOLIO-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-portfolio-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-COLLECT-SEAM-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть первый bounded collect semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit `master_query` turns без service grounding, чтобы frozen router получал уже готовый collect-contract (`intent=master_query`, `action=collect`, `tool_action=collect`, `next_question=service`) вместо первого policy-core LLM pass на этих turns, при этом grounded `master_query` fact path, named-master turns, pricing/duration mixes и соседние info seams остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-portfolio-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '420,460p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '430,530p' truffles-api/app/core/intent_routing.py`
  - `sed -n '901,990p' truffles-api/app/services/pack_runtime_service.py`
  - `sed -n '860,900p' truffles-api/tests/test_intent.py`
  - `rg -n "master_query|next_question|open_questions|tool_action=collect" truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - ingress already owns grounded `master_query` fact turns through a bounded snapshot branch, but explicit service-missing master questions still fall through to the first policy-core LLM pass inside frozen `decision.py`.
  - `resolve_master_intent(...)` already exposes the exact missing-service signal via `explicit=True` plus `needs_service_clarify=True`; the missing seam is only an ingress-owned collect snapshot.
  - `LlmPolicyCoreOutput` already validates `master_query` collect contracts when `tool_action in {collect,catalog.service_query}` and `next_question/open_questions` request `service`.
  - request-scoped policy overrides already carry `slots`, `next_question`, `open_questions`, `subject_kind`, `resolution_mode`, and are schema-validated before use.
- `Detected drift (docs vs code)`: current ingress cutover only owns grounded `master_query` facts; explicit master-selection questions without service are still semantic-owned by legacy policy-core LLM execution even though the resolver and schema already support a bounded collect contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html dataclasses field default_factory documentation`
- **Date/time (local):** `2026-03-16 14:14 +05`
- **Why this query is precise:** this block may extend the bounded snapshot dataclass with extra collect-contract fields, so the implementation should reuse the standard dataclass field/default pattern instead of inventing a custom container.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python documentation` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `dataclasses.field(default_factory=...)` is the standard way to add optional mutable collect-contract fields without sharing state across snapshots.
- **Decision:** `reuse + integrate` — reuse existing `PolicyCoreRouteSnapshot`, extend it minimally with collect-contract fields, and reuse existing request-scoped override validation.
- **Rejected options:**
  - adding a separate ad-hoc snapshot type just for one collect seam
  - editing frozen `decision.py` to special-case service-missing master questions
  - widening the block into named-master or availability semantics
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** explicit specialist/master questions without a concrete service still start with the first policy-core LLM pass inside frozen runtime.
- **Minimal reproduction:**
  1. Open `truffles-api/app/core/intent_routing.py` and confirm only grounded `master_query` fact turns are bridged.
  2. Open `truffles-api/app/services/pack_runtime_service.py` and confirm `resolve_master_intent(...)` already marks explicit service-missing turns with `needs_service_clarify=True`.
  3. Open `truffles-api/app/schemas/intent.py` and confirm `master_query` collect contracts with `next_question=service` are schema-valid.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded `master_query` collect override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - explicit service-missing master turns route to `intent="master_query"`, `action="collect"`, `tool_action="collect"`, `next_question="service"`, `open_questions=["service"]`
  - grounded `master_query` fact turns stay on the existing fact snapshot path
  - named-master turns and mixed pricing/duration turns remain outside this slice
  - override resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this seam still legacy-owned? Because ingress only bridges grounded master questions today.
  2. Why does that matter? Because explicit service-missing master questions are still core semantics decided by the first LLM pass inside frozen runtime.
  3. Why can ingress own this safely? Because `resolve_master_intent(...)` already exposes the needed explicit/missing-service signal and the schema already validates the bounded collect contract.
  4. Why not widen into availability or named-master handling? Because those paths carry extra follow-up and owner semantics that would turn this into a broader block.
  5. Why does this reduce drift? Because one more explicit semantic decision moves out of frozen runtime and into a typed ingress-owned contract.
- **Root cause statement:** explicit service-missing `master_query` turns remain in frozen `decision.py` because ingress lacks a bounded collect snapshot branch even though both the resolver and policy schema already support that contract.
- **Fix mechanism:**
  - add a routing-neutral detector for explicit service-missing master questions outside frozen runtime
  - extend `PolicyCoreRouteSnapshot` minimally for collect-contract fields
  - add a bounded `master_query` collect snapshot branch in `detect_policy_core_route_snapshot(...)`
  - verify delegate priming, override consumption, and exclusion behavior with deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `resolve_master_intent(...)`
  - existing request-scoped override schema validation in `intent_service`
  - existing grounded `master_query` branch and exclusions
- **External reuse:**
  - official Python `dataclasses.field(default_factory=...)` documentation
- **Why not reinvent the wheel:** the repo already has the resolver, schema, and override transport; this block only needs a narrow collect snapshot on top.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** one bounded collect seam with a small dataclass extension, one detector, one snapshot branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden service-missing `master_query` turns.
- No override bleed across requests or unrelated message text.
- No widening into named-master, specialist-availability, pricing/duration mixed turns, or booking state ownership.
- Existing grounded `master_query` fact bridge stays intact.

## Scope
- Add a routing-neutral bounded detector for explicit service-missing `master_query` turns.
- Extend `PolicyCoreRouteSnapshot` minimally so collect overrides can carry `next_question/open_questions`.
- Add a bounded `master_query` collect snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- named-master / specialist-availability semantics
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-collect-override-bridge-a922.md`
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
2. Add a routing-neutral detector for explicit service-missing `master_query` turns.
3. Extend `PolicyCoreRouteSnapshot` minimally for collect-contract fields and add the bounded collect branch.
4. Add deterministic tests for detection, exclusion, delegate priming, override consumption, and reset safety.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded `master_query` collect override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit service-missing master turns route to `intent="master_query"`, `action="collect"`, `tool_action="collect"`, `next_question="service"`, `open_questions=["service"]`
- grounded `master_query` fact turns remain on the existing fact path
- named-master turns and mixed pricing/duration turns remain outside this slice
- override state resets after delegate exit and does not apply to unrelated message text
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
- bounded collect snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires frozen-router edits, named-master handling, or availability follow-up ownership, stop and split
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
  - active block metadata must match the actual `master_query` collect override bridge being executed.

## Rollback
1. Revert `truffles-api/app/core/intent_routing.py`, `truffles-api/app/services/info_signal_service.py`, and touched tests.
2. Regenerate agent packet.
3. Re-run deterministic checks and confirm ingress falls back to the previous grounded-master-only behavior.

## No-go
- no edits in `truffles-api/app/routers/webhook/decision.py`
- no widening into named-master or specialist availability
- no proof/continuity side quests in this block
- no unvalidated override payloads bypassing schema checks

## Риски/блокеры
- `resolve_master_intent(...)` may classify broader person-question shapes than the bounded block wants; if exclusions are insufficient, stop and split.
- collect-contract fields in the snapshot dataclass must remain immutable/reset-safe.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- grounded specialist-availability and named-master semantics remain frozen-runtime-owned.
- downstream master reply normalization still lives in legacy paths after the ingress collect/fact bridge.

### Why not in this block
- those paths carry follow-up owner, availability capability, and downstream orchestration semantics that are materially larger than this bounded collect seam.

### Risk if deferred
- some master-selection turns still begin in frozen runtime, so semantic ownership is not yet singular for the full master capability family.

### Linked follow-up Task Package(s)
- `TBD: consultant-core-next-collect-or-availability-seam-a922`

### Expiry/trigger to stop deferral
- stop deferring once ingress `master_query` bridges no longer split into grounded fact vs service-missing collect only.

## Next-block contract (mandatory)
### Next block objective
- evaluate the next bounded collect/availability seam after explicit service-missing `master_query`, but only if it can stay outside frozen router files.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k master_query`

### Blocked-by conditions
- this block introduces false positives on named-master or pricing/duration turns
- the collect snapshot needs frozen-router edits to work
- schema validation rejects the override contract

### Owner role for closure
- `Top Architect`
