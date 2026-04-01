# TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-GUARD-FINALIZE-POST-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-GUARD-FINALIZE-OWNER-SURFACE-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the truthful post-cut audit after the generic tool-reply guard/finalize owner-surface deletion. This block must prove whether the next surviving authority is still an exact residual of the reduced tool-reply contour or whether the remaining `_maybe_apply_fact_guard(...)` body is already a broader mixed fact-guard family that requires a new architectural decision instead of another bounded implementation cut.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before audit closure)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "_finalize_tool_reply_owner_execution|_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19377,19426p;19980,20076p;21020,21040p;21294,21310p;21762,21778p'`
  - `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
  - `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- `FACT findings`:
  - the just-finished implementation block created one real deletion: frozen `decision.py:19406-19426` no longer directly enters `_maybe_apply_fact_guard(...)` plus `_finalize_turn_planner_owner_cutover(...)`; it now exits through `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)` at `:2705-2765`.
  - the surviving nested `_maybe_apply_fact_guard(...)` body still lives entirely in frozen `truffles-api/app/routers/webhook/decision.py:9630-9718`.
  - that nested body still owns clarify-attempt state mutation, trace/meta writes, escalation on clarify-limit, reply send/save, and final `WebhookResponse` shaping.
  - the nested body is not only used by the reduced tool-reply contour. It is still called directly at `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768`.
  - the same callable is still injected into broader non-tool-reply flows through `truffles-api/app/routers/webhook/info.py:786`, `:1168-1184`, `:1282-1290`, `:1411-1417`, `:1725-1731`, `:2136-2142`, and frozen `truffles-api/app/routers/webhook/booking.py:2442-2449`.
  - live fallback still remains at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`.
- `INFERENCE to verify in this block`:
  - the remaining `_maybe_apply_fact_guard(...)` body is already a broader mixed fact-guard family rather than the next exact residual of the reduced generic tool-reply contour.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Why this query is precise:** the post-cut audit needs the same migration rule as the parent implementation block: only atomic steps that retire the old live path count as progress.
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the parent generic owner-surface blocks; no second query is allowed or needed.
- **Existing solutions found:** after each atomic cut, run a post-cut audit; if the remaining path is broader than the original contour, stop and open a new explicit architectural decision instead of stretching the old implementation block.
- **Decision:** `reuse/integrate`
  - reuse the parent migration rule here to decide whether `_maybe_apply_fact_guard(...)` is still an exact residual or already a broader fact-guard family.
- **Rejected options:**
  - a second web query
  - pretending the reduced tool-reply contour and the nested fact-guard family are the same block
  - another bounded implementation attempt under the current TP without proving exact admissibility

## Root cause (mandatory)
- **Symptom:** after the direct generic tool-reply guard/finalize entry seam died, owners still remain partial and the next residual appears to be `_maybe_apply_fact_guard(...)` in frozen `decision.py`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19406-19426` and confirm the reduced tool-reply contour now exits through `reasoning_core._finalize_tool_reply_owner_execution(...)`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:9630-9718` and confirm the nested fact-guard body still mutates clarify state, emits trace/meta, escalates, sends/saves a reply, and returns a transport-shaped `WebhookResponse`.
  3. inspect the remaining direct fact-guard callsites in `decision.py:19985`, `:21024`, `:21300`, and `:21768`.
  4. inspect injected fact-guard use in `info.py:813`, `:1176`, `:1282`, `:1411`, `:1725`, `:2136`, and frozen `booking.py:2442`.
- **Evidence to capture:**
  - whether the nested fact-guard body belongs only to the reduced generic tool-reply contour or already spans multiple ingress families
  - whether moving that body now would require widening into `info.py`, `booking.py`, or other residual families
  - whether the current implementation TP can stay active truthfully
- **Five Whys (or equivalent):**
  1. Why are owners still partial after the guard/finalize owner-surface cut? Because the nested fact-guard body still lives in frozen `decision.py`.
  2. Why is that not automatically the next exact cut? Because the same body is still reused by direct legacy paths and injected into other flows beyond the reduced tool-reply contour.
  3. Why does that matter? Because deleting it now would widen scope beyond the current implementation block and reopen broader mixed ingress families.
  4. Why can the current non-frozen owner surface not finish this alone? Because `_finalize_tool_reply_owner_execution(...)` only replaced the entry seam; it still depends on the frozen callback for the nested fact-guard behavior.
  5. Why is a post-cut audit necessary? Because without it the program could mislabel a broader fact-guard migration as just one more exact tool-reply cut.
- **Root cause statement:** the current implementation block correctly deleted the direct generic tool-reply guard/finalize entry seam, but the remaining `_maybe_apply_fact_guard(...)` body is a broader mixed fact-guard family shared across multiple final-ingress contours; it is no longer truthfully the next exact residual of the reduced tool-reply contour.
- **Fix mechanism:**
  - stop the current exact implementation ladder here
  - publish this post-cut audit as a truthful stop-line verdict
  - lock the next move to a broader fact-guard family decision instead of another bounded implementation under the current TP

## Old authority seams under audit (mandatory)
- **FACT:** the direct generic tool-reply guard/finalize entry seam at `truffles-api/app/routers/webhook/decision.py:19406-19426` is already dead and is not the audit target anymore.
- **FACT:** the surviving nested fact-guard authority still lives at `truffles-api/app/routers/webhook/decision.py:9630-9718`.
- **FACT:** the surviving direct fact-guard callsites still live at `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768`.
- **FACT:** injected fact-guard use still lives in `truffles-api/app/routers/webhook/info.py:813`, `:1176`, `:1282`, `:1411`, `:1725`, `:2136`, and frozen `truffles-api/app/routers/webhook/booking.py:2442`.
- **FACT:** live fallback still reaches frozen ingress at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`.

## FACT vs INFERENCE verdict
- **FACT:** the current guard/finalize implementation block achieved one admissible seam deletion.
- **FACT:** the remaining `_maybe_apply_fact_guard(...)` authority is broader than the reduced tool-reply contour.
- **INFERENCE:** continuing under the current exact implementation TP would widen scope and misclassify a broader fact-guard family as just another bounded residual.
- **Decision:** switch canon to this post-cut audit block and lock the next move to a broader fact-guard family decision.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)`
  - `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - existing architecture packet/guard checks
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the repo already has the reduced owner entry surface and existing guard-related owner fragments; this block only classifies the remaining live authority and prevents another misleading bounded implementation attempt.

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `9`
- **Code dominance:** `doc-heavy`
- **Why this profile fits:** this block is a stop-line audit with canon sync only; it does not introduce another runtime edit.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is `done`
- no claim that the broader fact-guard family is already solved
- no new wrapper/helper counted as progress
- no widening into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756` in this block

## Scope
- audit the remaining `_maybe_apply_fact_guard(...)` residual after the guard/finalize owner-surface cut
- decide whether the remaining residual is still exact-scope or already broader family scope
- sync canon/session artifacts to this post-cut audit block

## Out of scope
- moving `_maybe_apply_fact_guard(...)` body itself
- new runtime implementation in `decision.py`, `info.py`, `booking.py`, or `reasoning_core.py`
- acceptance or `L2` reruns
- unrelated residual families outside the fact-guard / final-ingress hotspot

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Scan the remaining fact-guard callsites after the guard/finalize owner-surface cut.
2. Prove whether the remaining `_maybe_apply_fact_guard(...)` body is still an exact residual of the reduced tool-reply contour.
3. If it is broader, switch canon to this post-cut audit block and lock the next move to a broader decision block.

## DoD
- the audit states explicitly that no old seam died in this doc-only block
- the audit names the remaining fact-guard family with file/line evidence
- canon moves to the post-cut audit block with one machine-readable next move
- the next move is no longer framed as another exact guard/finalize implementation cut

## Checks
- `rg -n "_finalize_tool_reply_owner_execution|_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19377,19426p;19980,20076p;21020,21040p;21294,21310p;21762,21778p'`
- `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
- `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- explicit post-cut seam map for the remaining fact-guard family
- synced canon/session artifacts for this audit block
- green governance/session checks after the canon move
- explicit statement that seam-deletion count in this block is zero

## Rollback
1. Revert this audit TP and the canon/session updates.
2. Regenerate the agent packet.
3. Re-run the governance checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only post-cut audit; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree that this audit block is active and that the next move is a broader fact-guard decision.
- **Rollback:** revert the audit TP and canon sync, regenerate the packet, rerun the governance checks.
- **Post-release monitoring window:** the next block must either author the broader fact-guard family decision or stop as `GAP`; it must not resume exact-scope guard/finalize implementation under the old TP.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** governance/session checks only.
- **Stop condition:** if the audit still cannot distinguish exact residual from broader family, stop and escalate instead of making runtime edits.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits in this block
- no claim that `_maybe_apply_fact_guard(...)` is the next exact cut under the old TP without broader-decision approval
- no second web search
- no helper/wrapper growth counted as progress

## Risks / blockers
- the broader fact-guard family crosses both non-frozen and frozen ingress files, so a future implementation may require a new explicit rooted family scope
- frozen `booking.py` reuse of `maybe_apply_fact_guard` means a broader migration cannot be silently hidden under the current exact tool-reply TP
- if the next decision widens into unrelated boundary or continuity families, that must be called out as a separate `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - `truffles-api/app/routers/webhook/decision.py:19985`
  - `truffles-api/app/routers/webhook/decision.py:21024`
  - `truffles-api/app/routers/webhook/decision.py:21300`
  - `truffles-api/app/routers/webhook/decision.py:21768`
  - `truffles-api/app/routers/webhook/info.py:813`
  - `truffles-api/app/routers/webhook/info.py:1176`
  - `truffles-api/app/routers/webhook/info.py:1282`
  - `truffles-api/app/routers/webhook/info.py:1411`
  - `truffles-api/app/routers/webhook/info.py:1725`
  - `truffles-api/app/routers/webhook/info.py:2136`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `truffles-api/app/services/reasoning_core.py:8075-8087`
- **Why not in this block:**
  - this block is audit-only and the remaining live authority is broader than the just-finished exact tool-reply cut.
- **Risk if deferred:**
  - the program could resume seam farming under the wrong exact-scope contract and recreate a mixed hotspot story.
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922`
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922`
- **Expiry/trigger to stop deferral:**
  - before any new final-ingress implementation claim touching `_maybe_apply_fact_guard(...)`

## Next-block contract (mandatory)
- **Next block objective:** author `TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md` to lock the truthful rooted family and admissible destinations for the broader `_maybe_apply_fact_guard(...)` migration.
- **First deterministic check command:** `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19980,20076p;21020,21040p;21294,21310p;21762,21778p' && nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p' && nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
- **Blocked-by conditions:**
  - need to move `_maybe_apply_fact_guard(...)` body without first publishing the broader fact-guard decision
  - need for a new helper/wrapper as a way around the broader scope decision
  - need to reopen unrelated continuity or timeout families
  - need for a second web query
- **Owner role for closure:** `Top Architect`
