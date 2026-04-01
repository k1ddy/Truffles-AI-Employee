# TP-2026-03-16-consultant-core-promotions-rules-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROMOTIONS-RULES-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROMOTIONS-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTACT-POLICY-OVERRIDE-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded fact/info semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit promotions-rules turns, чтобы frozen router потреблял precomputed `promotions_rules`/`info` contract вместо первого policy-core LLM pass на этих turns, при этом generic promotions, service-grounded promo questions, and broader mixed info bundles остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_master_info_flow.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_master_info_flow.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '220,260p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '380,430p' truffles-api/app/core/intent_routing.py`
  - `sed -n '560,590p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '3606,3620p' truffles-api/app/services/demo_salon_knowledge.py`
- `FACT findings`:
  - generic promotions cutover is active, but stacking-rule questions are explicitly excluded and still start with the first policy-core LLM call inside frozen `decision.py`.
  - downstream info execution already has truth handling for `promotions_rules`, but `_build_info_intent_reply(...)` only exposes the generic `promotions` branch directly.
  - routing-neutral stacking-rule primitives already exist outside frozen files via `promotions_stacking_phrases` and `promotions_stacking_terms`.
  - the request-scoped policy override seam already transports arbitrary `intent`, `pack_refs`, and `capability`, so the remaining gap is a bounded promotions-rules detector plus a direct info-path branch.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for generic promotions turns, but explicit promotions-rules semantics still begin with a frozen policy-core LLM call and then rely on downstream fallback behavior instead of a direct contract path.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any documentation`
- **Date/time (local):** `2026-03-16 13:05 +05`
- **Why this query is precise:** this block adds a bounded routing-neutral detector that should fire when any stacking-rule phrase matches while keeping the implementation on top of Python built-ins rather than another custom matching loop.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python built-in `any(iterable)` cleanly expresses phrase-match short-circuit semantics and matches the existing `signal_any_match(...)` helper strategy already used in `info_signal_service.py`.
- **Decision:** `reuse + integrate` — extend the existing routing-neutral signal helpers and keep the promotions-rules detector as a thin composition layer.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit stacking-rule routing directly
  - widening this block into generic promotions or service-grounded promo questions
  - keeping promotions-rules only as a downstream fallback path in `info.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit promotions-rules turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/core/intent_routing.py` and confirm that generic promotions are bridged, but stacking-rule turns are excluded.
  2. Open `truffles-api/app/services/demo_salon_knowledge.py` and confirm that stacking-rule questions resolve to `promotions_rules` through a distinct truth path.
  3. Open `truffles-api/app/routers/webhook/info.py` and confirm that direct `promotions_rules` intent is not handled as its own branch.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded promotions-rules policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - `_build_info_intent_reply(...)` handles `intent="promotions_rules"` directly
  - override state resets after delegate exit and does not leak to unrelated message text
  - generic promotions, price/duration mixed turns, and service-grounded promo questions remain outside this bounded slice
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because stacking-rule turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because downstream truth execution already knows how to answer promotions rules, but it still depends on frozen semantic ownership before it can run.
  3. Why has ingress not taken this slice yet? Because there is no dedicated promotions-rules detector or direct info-branch contract for it.
  4. Why is a bounded cut now safe? Because stacking-rule lexicon keys already exist and are explicitly separable from generic promotions and price/duration questions.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** promotions-rules semantics remain in frozen `decision.py` because ingress still lacks a bounded routing-neutral detector for stacking-rule turns and downstream info execution lacks a direct `promotions_rules` branch for a request-scoped override contract.
- **Fix mechanism:**
  - add a bounded promotions-rules detector outside frozen runtime
  - add a bounded `promotions_rules` snapshot branch in `detect_policy_core_route_snapshot(...)`
  - add direct `promotions_rules` handling to `_build_info_intent_reply(...)`
  - verify delegate priming and info execution through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `signal_any_match(...)` and `signal_all_match(...)`
  - existing `promotions_stacking_phrases` and `promotions_stacking_terms` lexicon keys
  - existing downstream truth formatting for `promotions_rules`
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the override transport, lexicon helpers, and truth formatting; this block should only connect them through a direct bounded contract.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one new detector, one new snapshot branch, one direct info-path branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden promotions-rules turns.
- No override bleed across requests or unrelated message text.
- No widening into generic promotions, service-grounded promo questions, or mixed price/duration bundles.
- Frozen delegate still owns downstream truth execution and side effects.

## Scope
- Add a routing-neutral explicit promotions-rules detector outside frozen runtime.
- Add a bounded promotions-rules policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add direct `promotions_rules` support to `_build_info_intent_reply(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_intent.py`, and `truffles-api/tests/test_master_info_flow.py`.
- Sync required canon/session artifacts.

## Out of scope
- generic promotions cutover changes
- service-grounded promotions cutover
- price/duration mixed bundles
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-rules-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/routers/webhook/info.py`
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
2. Add a routing-neutral promotions-rules detector outside frozen runtime.
3. Add the bounded promotions-rules snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add direct `promotions_rules` support to `_build_info_intent_reply(...)`.
5. Add deterministic tests for detection, media gating, mixed-query exclusion, direct info reply, override consumption, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded promotions-rules policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- `_build_info_intent_reply(...)` handles `intent="promotions_rules"` directly
- override state resets after delegate exit and does not apply to unrelated message text
- generic promotions, service-grounded promotions, and mixed price/duration turns remain outside this bounded slice
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py -k promotions`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded promotions-rules policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral promotions-rules detector in `truffles-api/app/services/info_signal_service.py`
- direct info-path support in `truffles-api/app/routers/webhook/info.py`
- focused runtime/info tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires generic promotions rewiring, service-grounded promotions, mixed-info arbitration, or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + master-info tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual promotions-rules policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream truth execution.
- No widening into generic promotions, service-grounded promotions, or mixed price/duration arbitration in this block.

## Risks/Blockers
- A promotions-rules detector could wrongly steal generic promotions turns if stacking markers are too broad.
- A direct `promotions_rules` info branch could drift from the existing truth fallback behavior if meta/resolved intent are not preserved contractually.
- A detector that ignores price/duration overlap could widen into mixed info arbitration.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `decision.py` still owns generic mixed info bundles, service-grounded promotions, contact, broader booking arbitration, and all non-bounded policy-core semantics.
- **Why not in this block:** this slice is limited to explicit promotions-rules turns so it can move one semantic seam without touching frozen routers.
- **Risk if deferred:** promotions remains only partially ingress-owned until the rules path is migrated.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-contact-policy-override-evaluation-a922.md` (planned)
- **Expiry/trigger to stop deferral:** stop deferral once the next bounded fact/info seam no longer fits without mixed-bundle arbitration.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether contact can be migrated as the next bounded fact/info override without widening into booking phone collection or tenant-specific routing.
- **First deterministic check command:** `sed -n '1550,1815p' truffles-api/app/services/demo_salon_knowledge.py`
- **Blocked-by conditions:** promotions-rules block must land green first; contact cutover must prove a routing-neutral detector outside frozen runtime.
- **Owner role for closure:** `Top Architect`
