# TP-2026-03-16-consultant-core-contact-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTACT-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROMOTIONS-RULES-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-rules-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-FACT-SEAM-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded fact/info semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit contact turns, чтобы frozen router потреблял precomputed `contact`/`info` contract вместо первого policy-core LLM pass на этих turns, при этом booking phone collection, integration/off-topic turns, and tenant-specific routing остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-rules-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_master_info_flow.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_master_info_flow.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1525,1588p' truffles-api/app/services/demo_salon_knowledge.py`
  - `sed -n '430,505p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '320,425p' truffles-api/app/core/intent_routing.py`
  - `rg -n "contact|instagram|whatsapp|telegram" truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - downstream info execution already has a direct truth path for `intent="contact"` in `_build_info_intent_reply(...)`.
  - ingress policy bridges already cover adjacent fact seams (`services_overview`, `location`, `hours`, `pricing`, `duration`, `promotions`, `promotions_rules`), but explicit contact turns still begin with the first policy-core LLM call inside frozen `decision.py`.
  - existing low-level contact detection in pack adapters is broader than this bounded cut and also fires on raw phone-number payloads and channel names, so a direct reuse without additional gating would risk colliding with booking phone collection or out-of-domain integration questions.
  - the request-scoped policy override seam already transports arbitrary `intent`, `pack_refs`, and `capability`, so the remaining gap is a bounded contact detector that excludes integration/off-topic and collection-shaped turns.
- `Detected drift (docs vs code)`: active ingress semantic cutover claims adjacent fact/info seams, but explicit contact questions still rely on frozen first-pass policy routing even though downstream truth execution is already direct and deterministic.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/re.html Python re word boundary documentation`
- **Date/time (local):** `2026-03-16 13:27 +05`
- **Why this query is precise:** this block adds a bounded regex-backed detector for explicit contact turns and needs exact word-boundary behavior without widening to integration or booking-number payloads.
- **Sources opened (from this query):**
  - `re — Regular expression operations — Python documentation` — `https://docs.python.org/3/library/re.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `re` boundary-aware search is sufficient for explicit contact-query anchors; no extra parsing library is needed for this bounded seam.
- **Decision:** `reuse + integrate` — reuse existing pack contact signal helpers and add a narrow routing-neutral contact-query gate on top.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit contact routing directly
  - reusing raw adapter `_has_contact_signal(...)` without additional gating
  - widening this block into booking phone collection or integration/off-topic routing
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit contact turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/info.py` and confirm that `_build_info_intent_reply(...)` already has a direct `intent == "contact"` truth branch.
  2. Open `truffles-api/app/core/intent_routing.py` and confirm there is no bounded contact snapshot branch yet.
  3. Open `truffles-api/app/services/demo_salon_knowledge.py` and confirm the low-level contact signal is broader than a safe ingress bridge because it also reacts to raw phone numbers and channel keywords.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded contact policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - explicit contact questions route to `intent="contact"`, `tool_action="info"`, `pack_refs=["contact"]`, without inventing a new capability token outside the existing policy schema
  - integration/off-topic channel questions do not trigger this override
  - raw phone-number collection payloads do not trigger this override
  - override state resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because contact questions still start with the first policy-core LLM pass inside frozen runtime.
  2. Why does that matter? Because downstream truth execution already knows how to answer contact questions deterministically, but semantic ownership still begins in legacy code.
  3. Why has ingress not taken this slice yet? Because there is no bounded routing-neutral detector for explicit contact queries.
  4. Why can’t we reuse the existing raw contact signal directly? Because it also reacts to channel mentions and raw phone-number payloads, which would widen the slice into booking collection or off-topic integration traffic.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** contact semantics remain in frozen `decision.py` because ingress still lacks a bounded contact-query detector that reuses existing signal helpers but excludes booking-number payloads and integration/off-topic channel turns.
- **Fix mechanism:**
  - add a routing-neutral explicit contact detector outside frozen runtime
  - add a bounded `contact` snapshot branch in `detect_policy_core_route_snapshot(...)`
  - verify override consumption, delegate priming, and exclusion behavior through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing pack adapter `_has_contact_signal(...)`
  - existing routing-neutral exclusion helpers for `services_overview`, `location`, `hours`, `pricing`, `duration`, `promotions`, and `promotions_rules`
  - existing downstream `intent="contact"` truth execution in `_build_info_intent_reply(...)`
- **External reuse:**
  - official Python `re` documentation
- **Why not reinvent the wheel:** the repo already has contact signal primitives, override transport, and downstream truth execution; this block only needs a narrow ingress contract on top.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one routing-neutral detector, one snapshot branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden contact turns.
- No override bleed across requests or unrelated message text.
- No widening into booking phone collection, integration/off-topic turns, or tenant-specific routing.
- Frozen delegate still owns downstream truth execution and side effects.

## Scope
- Add a routing-neutral explicit contact detector outside frozen runtime.
- Add a bounded contact policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_intent.py`, and, if needed, `truffles-api/tests/test_master_info_flow.py`.
- Sync required canon/session artifacts.

## Out of scope
- booking phone collection
- integration/off-topic routing
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-contact-policy-override-bridge-a922.md`
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
2. Add a routing-neutral explicit contact detector that excludes integration/off-topic and booking-number payloads.
3. Add the bounded contact snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add deterministic tests for detection, media gating, integration exclusion, raw-phone exclusion, override consumption, and delegate priming.
5. Sync canon/session artifacts, correct stale evidence strings, and rerun required checks.

## DoD
- `reasoning_core` primes a bounded contact policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- explicit contact questions route to `intent="contact"`, `action="fact"`, `tool_action="info"`
- integration/off-topic channel questions and raw phone-number collection payloads remain outside this slice
- override state resets after delegate exit and does not apply to unrelated message text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py -k contact`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded contact policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral contact detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/info tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires frozen-router edits, booking collection rewiring, or off-topic integration arbitration beyond bounded exclusions, stop and split
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
  - active block metadata must match the actual contact policy override bridge being executed.

## Rollback
- Revert this TP's service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- direct edits in frozen `decision.py`, `booking.py`, or `pending.py`
- widening this block into booking phone collection
- widening this block into integration/off-topic classification
- adding new proof/eval or continuity work in the same block
- using raw phone-number presence alone as a contact-routing trigger

## Risks / blockers
- channel-name queries can overlap with out-of-domain integration phrases; the detector must stay narrow enough to avoid hijacking off-topic traffic.
- the adapter-level contact signal is broader than this ingress slice; bounded exclusions are required to keep semantic ownership honest.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- richer contact-related arbitration inside frozen `decision.py` still exists for non-bounded turns.
- tenant-specific or multi-pack contact variations are not part of this slice.

### Why not in this block
- this block is only for the explicit contact fact seam that already has deterministic downstream truth execution.

### Risk if deferred
- frozen runtime remains first semantic owner for adjacent contact-like turns until later cutover blocks land.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- next bounded fact seam TP after contact bridge

### Expiry/trigger to stop deferral
- stop deferral once the next adjacent fact seam is selected or if contact turns still show drift in deterministic replay evidence.

## Next-block contract (mandatory)
### Next block objective
- select the next bounded fact/info semantic seam after contact without returning to proof/continuity micro-slices.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k contact_policy_override`

### Blocked-by conditions
- this block widens into booking phone collection
- this block requires frozen-router edits
- deterministic contact exclusions are not provable with focused tests

### Owner role for closure
- `Top Architect`
