# TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MASTER-RESIDUAL-LEDGER-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTROLLED-DEMOLITION-MASTER-2026-03-15`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-active-name-time-followup-boundary-family-convergence-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PACKAGE-ORDERING-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать один stop-the-line master residual ledger после серии admissible micro-cuts. Блок должен перестать разбрасывать remaining work по локальным сообщениям и вместо этого собрать один repo-truth список всех оставшихся owner families, exact hotspots, execution order, stop conditions, and proof prerequisites.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/message.py`
- `truffles-api/app/routers/decision_core.py`
- `truffles-api/app/routers/provider_gateway.py`
- `truffles-api/app/webhook.py`
- `truffles-api/app/routers/webhook/dedup.py`
- `scripts/booking_dialog_scenarios.py`
- `ops/diagnose.py`

## FACT pre-check
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
- `Baseline commands`:
  - `sed -n '1,220p' docs/SOURCE_OF_TRUTH.yaml`
  - `sed -n '1,220p' docs/ACTIVE_PROGRAM.md`
  - `sed -n '1,260p' docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
  - `rg -n "_apply_policy_guard_override\(|_record_semantic_override_block\(" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "pending_resume|restore|snapshot|reset|handover_confirmation" truffles-api/app/routers/webhook/pending.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "_require_materialized_message_response|handle_decision\(|handle_provider_inbound\(|get_or_create_conversation\(" truffles-api/app/routers/message.py truffles-api/app/routers/decision_core.py truffles-api/app/routers/provider_gateway.py truffles-api/app/webhook.py`
  - `rg -n "rewrite|normalize|repair|expectation|semantic_override" ops/diagnose.py scripts/booking_dialog_scenarios.py`
- `FACT findings`:
  - progress is real but still partial at master-block level
  - remaining work is now large-package work, not another honest micro-slice sequence
  - the repo still lacks one current ordered backlog ledger that connects remaining hotspots to exact package order
- `Detected drift (docs vs code)`:
  - the previous audit explains overall status correctly, but current canon still points at residual family selection rather than one published ordered master ledger

## Root cause (mandatory)
- **Symptom:** every local success exposes another residual and the program still feels open-ended instead of converging toward a finite closure plan.
- **Minimal reproduction:**
  1. Read `docs/SOURCE_OF_TRUTH.yaml` and `docs/ACTIVE_PROGRAM.md`.
  2. Confirm the master status is still `partial/partial/partial/not started` for semantic, continuity, proof, and multi-pack.
  3. Grep `truffles-api/app/routers/webhook/decision.py` for `_apply_policy_guard_override(...)` and `_record_semantic_override_block(...)`.
  4. Observe that real deletions happened, but remaining live authority is still spread across several larger families.
- **Evidence to capture:**
  - one ordered residual-work ledger
  - one package-level execution order
  - exact hotspots by owner family
  - clear stop conditions for fake speed
- **Five Whys:**
  1. Why does progress feel non-final? Because local seams were deleted, but the remaining whole-program backlog was not published as one ordered ledger.
  2. Why was that confusing? Because each block updated truth and exposed the next residual without compressing the remaining work.
  3. Why did that happen? Because the working unit stayed too close to `admissible micro-cut` instead of `owner-family package`.
  4. Why is that costly now? Because the remaining work is no longer a set of easy bounded seams; it is a set of broader owner families and proof blocks.
  5. Why stop now? Because a package-order ledger is cheaper than continuing another local runtime cut with no compressed closure map.
- **Root cause statement:** the program lacks a current master residual ledger that translates real local seam deletions into one finite, ordered, family-level closure plan.
- **Fix mechanism:**
  - publish one report with exact remaining packages and hotspots
  - sync canon to point to the ledger
  - make the next block a package-level TP, not another residual micro-cut

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
  - existing guard checks and packet generator
  - current code hotspots in `decision.py`, `pending.py`, `state_service.py`, `session_memory.py`, `ops/diagnose.py`, `scripts/booking_dialog_scenarios.py`
- **External reuse:** none required for this read-only repo audit
- **Why not build something bigger:** this block is documentation of repo truth, not runtime implementation

## Invariant
- No runtime code edits.
- No frozen-file behavior edits.
- No new implementation claim without explicit old-authority deletion.
- The report must distinguish exact remaining work from still-open gaps.

## Scope
- publish one master residual ledger report
- map exact remaining workstreams and residual hotspots
- define ordered package backlog
- sync canon to point at the ledger and the next package-level move

## Out of scope
- runtime implementation changes
- proof execution
- multi-pack runs
- frozen-file waivers

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this stop-the-line audit TP.
2. Assemble the exact residual-work ledger from repo truth plus code hotspots.
3. Group residuals into package-level owner families with exact destinations or explicit GAPs.
4. Publish ordered package backlog and fast-path/no-go rules.
5. Sync canon and packet.
6. Run governance checks.

## DoD
- one master residual ledger report exists at `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- the report names exact remaining workstreams, exact hotspot clusters, ordered package backlog, and stop conditions
- canon points at this audit as the current block and no longer leaves the next move as vague residual selection
- governance checks are green

## Checks
- `rg -n "Verdict Summary|Why Confusion Is Growing|Master Residual Ledger|Ordered Package Backlog|Fastest Honest Path|Gap Register" docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
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
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- synced canon and packet
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** governance/doc checks only
- **Stop condition:** if the repo does not support a claimed exact package order, record `GAP` instead of guessing
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only audit; no runtime rollout
- **Go/no-go signals:** report published, canon synced, governance checks green
- **Rollback:** revert audit docs/canon sync and regenerate packet
- **Post-release monitoring window:** next block must be package-level, not a new micro-cut

## Rollback
1. Revert the audit TP, report, and canon sync.
2. Regenerate the packet.
3. Re-run governance checks.

## No-go
- no runtime edits hidden inside the audit
- no claim that the exact seam-by-seam global inventory is complete if evidence is missing
- no new micro-cut chosen before package ordering is published
- no claim of consultant correctness from this audit

## Risks / blockers
- some remaining families are exact at workstream level but not yet proved as complete seam-by-seam inventories
- canon sync changes the visible current block without changing runtime behavior
- the next package destination may still need one more bounded TP to avoid a new god-file

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - semantic owner remains partial
  - continuity owner remains partial
  - boundary owner remains partial
  - public entrypoint compatibility remains partial
  - debounce/buffer remains legacy-owned
  - proof path remains mixed
  - multi-pack proof remains not started
- **Why not in this block:**
  - this block only compresses and orders the remaining work; it does not execute runtime convergence
- **Risk if deferred:**
  - more local cuts will keep increasing visible complexity without a stable master plan
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-18-consultant-core-policy-core-guard-orchestration-package-a922` (to be authored)
  - `TP-2026-03-18-consultant-core-semantic-arbitration-residual-package-a922` (to be authored)
  - `TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922` (to be authored)
  - `TP-2026-03-18-consultant-core-proof-black-box-package-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core runtime implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** author the first package-level runtime TP for the `policy_core_guard_orchestration` residual family defined in the master ledger
- **First deterministic check command:** `rg -n "policy_core_guard_handoff_safe|policy_core_guard_pending_hold|policy_core_timeout_booking_completion|policy_core_degraded_reschedule_handoff|policy_core_degraded_collect_guard" truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** inability to converge that family without creating a new mixed hotspot or re-expanding `state_service.py`
- **Owner role for closure:** `Top Architect`
