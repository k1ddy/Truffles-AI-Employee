# TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-GREETING-FAMILY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-GREETING-OWNER-FAMILY-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-greeting-owner-family-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NORMAL-PATH-BOOKING-PROMPT-OWNER-FAMILY-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Зафиксировать richer owner-replacement target после safe greeting family cutover и не дать программе скатиться обратно в micro-slice bridge growth. Этот блок должен доказательно выбрать следующий admissible deletion seam, явно заблокировать соблазнительные, но смешанные seam’ы, и обновить canon так, чтобы следующий агент шел уже в один конкретный implementation block.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-greeting-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "ingress_domain_router_out_of_domain|style_reference_text|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py`
  - `sed -n '240,365p' truffles-api/app/core/intent_routing.py`
  - `sed -n '430,575p' truffles-api/app/core/intent_routing.py`
  - `sed -n '22430,22910p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1780,1945p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - `out_of_domain` is still normalized as a controller snapshot family (`reason="ingress_domain_router_out_of_domain"`), but its runtime execution remains mixed with low-signal/fallback/firebreak semantics, lateness policy exceptions, and knowledge-backlog writes inside frozen `decision.py`.
  - `style_reference` is already normalized as a policy snapshot (`reason="style_reference_text"`), but the live authority still spans pending-media state, Telegram/media forwarding, and escalation lifecycle inside frozen `decision.py`.
  - `booking_prompt` is still the main normal-path continuity/semantic authority seam: policy snapshots and specialist/active-name followup routing still normalize against `resume_reason="booking_prompt"`, while frozen `decision.py` still authors booking prompt reply text, expected-reply transitions, trace/meta, and booking-state writes.
  - new core already has the substrate needed for a broader `booking_prompt` cutover: typed planner decisions, typed owner artifacts, collect-owner dialog-state construction, and booking payload preservation all exist outside frozen legacy.
- `Detected drift (docs vs code)`:
  - execution strategy forbids counting another micro-bridge as progress, but current canon still names the greeting cutover as the active block even though the next real decision is now a richer seam ranking and lock.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Branch by Abstraction"`
- **Date/time (local):** `2026-03-17 13:29 +0500`
- **Why this query is precise:** the audit needs one high-signal external reference for choosing the next cut by deletion value through an existing abstraction seam, instead of prolonging dual authority with another narrow bridge.
- **Sources opened (from this query):**
  - `Branch by Abstraction` — `https://martinfowler.com/bliki/BranchByAbstraction.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** use an existing abstraction seam to swap ownership incrementally, but only when the old implementation can be retired instead of running indefinitely in parallel.
- **Decision:** `reuse/integrate` — prefer the next seam where current new-core abstractions already exist (`TurnPlanner` + `DialogStateService` + `TurnExecutor`) and where the old `decision.py` authority can become unreachable in one family-sized cut.
- **Rejected options:**
  - another narrow specialist/booking followup micro-slice
  - text-only `style_reference` cutover without media/pending/escalation ownership
  - `out_of_domain` cutover before its firebreak/low-signal/backlog semantics are disentangled
- **Open questions:** whether the first `booking_prompt` block should stop at safe normal-path prompt families or also take `intent_queue -> booking` in the same cut; this remains the first implementation TP decision.

## Root cause (mandatory)
- **Symptom:** after the greeting cutover, the repo still has multiple tempting legacy seams, but no locked richer target seam; this creates real risk of resuming bridge-growth by inertia instead of deleting a meaningful old authority family.
- **Minimal reproduction:**
  1. Run `rg -n "ingress_domain_router_out_of_domain|style_reference_text|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py`.
  2. Inspect `truffles-api/app/core/intent_routing.py` and observe that multiple followup families still key off `resume_reason="booking_prompt"`.
  3. Inspect `truffles-api/app/routers/webhook/decision.py` and observe that legacy still computes booking prompts, expected-reply transitions, and related trace/meta writes.
  4. Inspect `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/dialog_state_service.py`, and `truffles-api/app/core/turn_executor.py` and confirm the new-core substrate for a broader booking prompt cut already exists.
- **Evidence to capture:**
  - `booking_prompt` remains a live normal-path authority in frozen `decision.py`
  - `style_reference` remains blocked by media/pending/escalation semantics
  - `out_of_domain` remains blocked by firebreak/low-signal/backlog semantics
  - canon is updated so the next move is one concrete implementation target, not another audit loop
- **Five Whys (or equivalent):**
  1. Why is the next move risky? Because the bounded deterministic families already harvested are mostly exhausted.
  2. Why can’t we just take the next obvious remaining route snapshot? Because `style_reference` and `out_of_domain` still mix semantic ownership with broader stateful/boundary behavior.
  3. Why is `booking_prompt` different? Because it still concentrates legacy semantic + continuity authority while new-core typed seams already exist to absorb it.
  4. Why does that matter architecturally? Because it deletes a larger old authority family instead of growing one more ingress bridge.
  5. Why must this be locked in canon now? Because otherwise the next agent can still make an inadmissible micro-slice move while believing it is making progress.
- **Root cause statement:** the program has already harvested most safe micro-deletions, but canon had not yet frozen the next richer seam choice; without an explicit audit lock, the remaining mixed seams invite another round of bridge growth instead of deleting the still-central `booking_prompt` authority family.
- **Fix mechanism:**
  - rank the remaining post-greeting seams by deletion value vs mixed-semantics risk
  - lock `booking_prompt` as the next implementation target
  - explicitly mark `style_reference` and `out_of_domain` inadmissible for the next block
  - regenerate canon/agent packet so the next move is machine-readable

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/reasoning_core.py`
  - existing read-only legacy compatibility helper `_next_booking_prompt(...)` in `truffles-api/app/routers/webhook/decision.py`
- **External reuse:**
  - Martin Fowler `Branch by Abstraction`
- **Why not reinvent the wheel:** the audit is valuable only if it points the next block at a seam that can reuse the already-built new-core abstractions and retire real legacy authority, not if it invents another bespoke bridge family.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `32`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this block is architecture governance and next-step lock-in only; runtime behavior does not change here.

## Invariant
- No frozen-router edits.
- No new bridge family is introduced or counted as progress.
- The audit must lock exactly one next implementation target.
- `style_reference` and `out_of_domain` must not be accidentally promoted into “maybe next” ambiguity if the evidence still shows mixed ownership.

## Scope
- Audit the remaining richer seams named in the current next-block contract.
- Rank admissibility and deletion value.
- Publish the next implementation target and explicit blocked seams.
- Update canon/session artifacts and regenerate the agent packet.

## Out of scope
- runtime code changes
- new tests outside packet/architecture doc checks
- `style_reference` implementation
- `out_of_domain` implementation
- `booking_prompt` implementation itself

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan (1..N)
1. Publish this audit TP with RCA and one exact web search.
2. Re-run the current next-block contract seam scan and inspect the remaining legacy authority holders.
3. Rank `booking_prompt`, `style_reference`, and `out_of_domain` by deletion value vs mixed-semantics risk.
4. Lock one next implementation target and explicitly mark blocked seams.
5. Update `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, and session/canon artifacts.
6. Regenerate the agent packet and run governance checks.

## DoD
- one evidence-backed next implementation target is chosen
- `booking_prompt` is explicitly locked as the next admissible owner-replacement cut
- `style_reference` and `out_of_domain` are explicitly marked blocked for the immediate next block
- machine-readable canon points to this audit block and to the next implementation move
- governance checks are green

## Checks
- `rg -n "ingress_domain_router_out_of_domain|style_reference_text|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- the seam-scan command output
- the new audit TP
- updated `docs/SOURCE_OF_TRUTH.yaml`
- regenerated `docs/_generated/AGENT_PACKET.*`
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** no runtime quality suites; doc and architecture checks only
- **Stop condition:** if the audit cannot identify a seam that removes or bypasses a real old authority family, stop and escalate instead of inventing another bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only governance lock; no runtime rollout
- **Go/no-go signals:** packet regeneration and governance checks green
- **Rollback:** revert doc/canon updates and regenerate the packet
- **Post-release monitoring window:** next block must start from the locked `booking_prompt` objective, not from a newly improvised seam

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Drift closeout rule`:
  - canon may point to `booking_prompt` as the next move only if the audit evidence still shows `style_reference` and `out_of_domain` are mixed seams and `booking_prompt` remains the richest deletable authority family.

## Rollback
1. Revert the new audit TP and canon/session updates.
2. Regenerate the packet from the previous source of truth.
3. Re-run the governance checks.

## No-go
- no runtime implementation hidden inside the audit
- no “maybe next” ambiguity for `style_reference` or `out_of_domain`
- no claim that the audit itself counts as semantic convergence

## Risks / blockers
- `booking_prompt` may still prove too broad for a single safe block and require a tightly-scoped safe normal-path subset
- some `booking_prompt` authority is intertwined with `intent_queue` and specialist followup variants, so the next implementation TP must define the exact family boundary before code starts
- `style_reference` and `out_of_domain` remain tempting shortcuts for agents who only look at snapshot detectors instead of live runtime ownership

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `booking_prompt` still lives in frozen `decision.py`
  - `style_reference` remains legacy-owned
  - `out_of_domain` remains legacy-owned
- **Why not in this block:**
  - this block only locks the next deletion target; it does not implement the cutover
- **Risk if deferred:**
  - the program can backslide into another micro-slice or mixed-seam cut and lose the demolition discipline
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-owner-replacement-audit-after-safe-greeting-owner-family-cutover-a922.md`
- **Expiry/trigger to stop deferral:**
  - before any new consultant-core runtime implementation block starts in this worktree

## Next-block contract (mandatory)
- **Next block objective:** `turn_planner_normal_path_booking_prompt_owner_family_cutover_after_richer_owner_replacement_audit`
- **First deterministic check command:** `rg -n "booking_prompt|_next_booking_prompt|intent_queue_choice == \\\"booking\\\"" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** inability to define a safe `booking_prompt` family boundary without frozen-file edits or new bridge growth
- **Owner role for closure:** `Top Architect`
