# TP-2026-03-16-consultant-core-master-query-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MASTER-QUERY-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTACT-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-contact-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-FACT-SEAM-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded fact/info semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-grounded `master_query` turns, чтобы frozen router потреблял precomputed `master_query`/`catalog.service_query` contract вместо первого policy-core LLM pass на этих turns, при этом service-clarify master turns, named-master turns, booking specialist selection, and mixed pricing/duration/info turns остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-contact-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_master_info_flow.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_master_info_flow.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '901,1035p' truffles-api/app/services/pack_runtime_service.py`
  - `sed -n '540,575p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '320,430p' truffles-api/app/core/intent_routing.py`
  - `rg -n "master_query|master_signal_override_blocked|master" truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - downstream info execution already has a direct `intent == "master"` reply path backed by `resolve_master_intent(...)` and `build_master_reply_from_pack(...)`.
  - the policy schema already accepts bounded fact contracts for `intent="master_query"`, `action="fact"`, `tool_action="catalog.service_query"`, and `tool_args.service_query`.
  - explicit service-grounded master questions are already structurally separable through `resolve_master_intent(...)`, but ingress still lacks a bounded detector/snapshot branch for them.
  - existing runtime tests show there are broader `master_signal_override_blocked` cases, so this block must stay narrow: only service-grounded fact turns, no missing-service clarify path, no named-master path, no mixed price/duration/info path.
- `Detected drift (docs vs code)`: ingress already owns neighboring fact/info seams, but explicit service-grounded master questions still begin with the first policy-core LLM call inside frozen `decision.py` even though the service-grounded contract is already representable and the downstream reply path already exists.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any documentation`
- **Date/time (local):** `2026-03-16 13:39 +05`
- **Why this query is precise:** this block needs a tight exclusion gate over multiple bounded predicates while keeping the detector as a thin composition layer instead of another custom branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python built-in `any(iterable)` matches the existing short-circuit helper style used in routing-neutral signal helpers and is sufficient for a narrow exclusion gate around master-query detection.
- **Decision:** `reuse + integrate` — reuse `resolve_master_intent(...)` plus existing exclusion helpers and keep the new detector as a thin bounded composition layer.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit master-query routing directly
  - widening the block into missing-service clarify or named-master routing
  - encoding another master-specific phrase forest directly inside `intent_routing.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit service-grounded master questions still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/pack_runtime_service.py` and confirm `resolve_master_intent(...)` already separates explicit service-grounded master questions from clarify cases.
  2. Open `truffles-api/app/schemas/intent.py` and confirm `master_query` fact contracts with `tool_args.service_query` already validate.
  3. Open `truffles-api/app/core/intent_routing.py` and confirm there is no bounded master-query snapshot branch yet.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded `master_query` policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - explicit service-grounded master turns route to `intent="master_query"`, `action="fact"`, `tool_action="catalog.service_query"`, `pack_refs=["master"]`
  - missing-service master turns do not trigger this override
  - named-master turns do not trigger this override
  - mixed pricing/duration turns do not trigger this override
  - override state resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because service-grounded master questions still start with the first policy-core LLM pass inside frozen runtime.
  2. Why does that matter? Because the repo already has both a service-grounded master resolver and a schema-valid `master_query` fact contract.
  3. Why has ingress not taken this slice yet? Because there is no bounded detector/snapshot branch that reuses `resolve_master_intent(...)` while excluding adjacent master-related cases.
  4. Why can’t we just bridge all master turns? Because missing-service clarify, named-master, and mixed turns carry broader semantic risks and would widen the slice beyond safe bounded cutover.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit service-grounded fact contract while legacy runtime keeps only downstream orchestration.
- **Root cause statement:** service-grounded master semantics remain in frozen `decision.py` because ingress still lacks a bounded detector that reuses `resolve_master_intent(...)` for explicit fact turns while excluding clarify, named-master, and mixed info/pricing/duration paths.
- **Fix mechanism:**
  - add a routing-neutral bounded master-query detector outside frozen runtime
  - add a bounded `master_query` snapshot branch in `detect_policy_core_route_snapshot(...)`
  - verify override consumption, delegate priming, and exclusion behavior through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `resolve_master_intent(...)` and `MasterIntentResolution`
  - existing routing-neutral exclusion helpers for `services_overview`, `location`, `hours`, `pricing`, `duration`, `promotions`, `promotions_rules`, and `contact`
  - existing downstream master reply path in `_build_info_intent_reply(...)`
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the service-grounded master resolver, override transport, and downstream reply path; this block only needs a narrow ingress contract on top.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one routing-neutral detector, one snapshot branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden `master_query` turns.
- No override bleed across requests or unrelated message text.
- No widening into missing-service clarify, named-master turns, booking specialist selection, or mixed price/duration/info turns.
- Frozen delegate still owns downstream truth execution and side effects.

## Scope
- Add a routing-neutral bounded master-query detector outside frozen runtime.
- Add a bounded `master_query` policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_intent.py`, and reuse `truffles-api/tests/test_master_info_flow.py` if needed.
- Sync required canon/session artifacts.

## Out of scope
- missing-service master clarify
- named-master routing
- booking specialist selection or availability
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_master_info_flow.py`
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
2. Add a routing-neutral bounded master-query detector that reuses `resolve_master_intent(...)` and excludes clarify, named-master, and mixed turns.
3. Add the bounded `master_query` snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add deterministic tests for detection, media gating, clarify exclusion, named-master exclusion, mixed-query precedence, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded `master_query` policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit service-grounded master turns route to `intent="master_query"`, `action="fact"`, `tool_action="catalog.service_query"`, `pack_refs=["master"]`
- missing-service clarify, named-master, and mixed pricing/duration turns remain outside this slice
- override state resets after delegate exit and does not apply to unrelated message text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py -k master`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded master-query policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral master-query detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/master-info tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires frozen-router edits, missing-service clarify ownership, named-master routing, or booking specialist-selection semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + master-info tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual master-query policy override bridge being executed.

## Rollback
- Revert this TP's service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- direct edits in frozen `decision.py`, `booking.py`, or `pending.py`
- widening this block into missing-service clarify or named-master routing
- widening this block into booking specialist selection or availability routing
- adding new proof/eval or continuity work in the same block

## Risks / blockers
- explicit named-master or availability turns can look similar to generic master queries; the detector must stay narrow enough to avoid hijacking those turns.
- broader legacy `master_signal_override_blocked` behavior still exists; this block must not assume it is retired.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- richer master-related arbitration inside frozen `decision.py` still exists for clarify, named-master, and mixed turns.
- tenant-specific or multi-pack master-query variations are not part of this slice.

### Why not in this block
- this block is only for the explicit service-grounded `master_query` fact seam that already has schema-valid contracts and a downstream reply path.

### Risk if deferred
- frozen runtime remains first semantic owner for adjacent master-related turns until later cutover blocks land.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- next bounded fact seam TP after master-query bridge

### Expiry/trigger to stop deferral
- stop deferral once the next adjacent fact seam is selected or if master-query turns still show drift in deterministic replay evidence.

## Next-block contract (mandatory)
### Next block objective
- select the next bounded fact/info semantic seam after service-grounded `master_query` without returning to proof/continuity micro-slices.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k master_query_policy_override`

### Blocked-by conditions
- this block widens into missing-service clarify or named-master routing
- this block requires frozen-router edits
- deterministic master-query exclusions are not provable with focused tests

### Owner role for closure
- `Top Architect`
