# TP-2026-03-18-consultant-core-debounce-buffer-owner-convergence-package-a922

## Goal
Delete or bypass the split debounce / buffer / duplicate-message authority across frozen `truffles-api/app/routers/webhook/decision.py`, legacy-coupled `truffles-api/app/routers/webhook/dedup.py`, and the shadow preexisting-duplicate probe in `truffles-api/app/services/reasoning_core.py` by converging ingress dedup/buffer ownership into one narrow existing non-frozen owner surface, while removing that owner’s dependency on the legacy semantic ingress path.

## Canon refs
- `STATE.md` NOW: consultant core `public_entrypoint_materialization_contract` runtime family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the targeted dedup/debounce runtime lane plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Move Function" "Separate Query from Modifier"`
- **Date/time (local):** `2026-03-18 16:44:47 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/separateQueryFromModifier.html`
- **Source quality:**
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- **Found ready-made solutions:**
  - `Move Function`: move behavior to the module that already owns the dominant data/invariant instead of leaving caller/callee ownership split
  - `Separate Query from Modifier`: separate pure duplicate probing from mutation-heavy buffering / trace / state side effects so callers stop mixing lookup and mutation contracts
- **Decision:** `reuse + integrate`
  - reuse the existing `truffles-api/app/routers/webhook/dedup.py` module as the single ingress dedup/buffer owner surface instead of creating a new service layer
  - reuse existing non-frozen downstream owners for post-debounce state/semantic outcomes (`truffles-api/app/routers/webhook/guards.py`, `truffles-api/app/routers/webhook/context_manager.py`, `truffles-api/app/services/intent_service.py`, `truffles-api/app/routers/webhook/trace.py`) instead of keeping those branches in `dedup.py`
  - converge `truffles-api/app/services/reasoning_core.py` duplicate preflight onto the same dedup owner contract instead of maintaining a shadow backend lookup
- **Rejected options:**
  - grow `truffles-api/app/services/reasoning_core.py` into the full debounce/buffer mutation owner: rejected because it would create a new mixed ingress hotspot
  - leave duplicate lookup split between `reasoning_core.py` and `dedup.py`: rejected because the old authority family would remain live
  - move this family into `truffles-api/app/services/state_service.py`: rejected because this is ingress idempotency/buffering, not continuity ownership
  - create a new `*_dedup_service.py` layer before proving the existing `dedup.py` surface cannot own the package: rejected because that is wrapper-first, not reuse-first

## Root cause (mandatory)
- **Symptom:** debounce/buffer remains legacy-owned and mutation-heavy, and duplicate-message handling is still split between the frozen ingress path and a second preexisting-duplicate probe in `reasoning_core.py`.
- **Minimal reproduction:**
  - `rg -n "_handle_dedup_gate|_handle_debounce_gate|is_duplicate_message_id|should_process_debounced_message|_lookup_preexisting_duplicate_message|legacy\._(coerce_batch_messages|evaluate_booking_signal|record_decision_trace|get_conversation_context|get_booking_context|get_reengage_confirmation|is_reengage_confirmation_active)|legacy\.is_opt_out_message" truffles-api/app/routers/webhook/dedup.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Evidence:**
  - frozen `truffles-api/app/routers/webhook/decision.py:9305` still routes duplicate-message handling through `_handle_dedup_gate(...)`
  - frozen `truffles-api/app/routers/webhook/decision.py:11456` still routes debounce/buffer handling through `_handle_debounce_gate(...)`
  - `truffles-api/app/routers/webhook/dedup.py:398` still mixes Redis/DB debounce mechanics with legacy semantic/state helpers such as `_coerce_batch_messages`, `_evaluate_booking_signal`, `_record_decision_trace`, conversation-context reads, reengage checks, and `is_opt_out_message`
  - `truffles-api/app/services/reasoning_core.py:5905` still keeps a second duplicate backend lookup path (`message_dedup` / `messages` fallback) before delegating to the router path
  - `truffles-api/app/routers/webhook/guards.py:363` already owns a separate non-frozen mute/reengage family, proving that post-debounce muted-state outcomes already have an owner lane outside `dedup.py`
  - `truffles-api/app/routers/webhook/decision.py:11484` and `truffles-api/app/routers/webhook/decision.py:11551` recompute `batch_messages` and `booking_signal` after the debounce gate, so keeping semantic booking/mute arbitration inside `dedup.py` duplicates later runtime ownership
- **Five Whys:**
  1. Why is debounce/buffer still marked legacy-owned? Because `dedup.py` extracted mechanics but kept semantic/state decisions that still depend on legacy ingress helpers.
  2. Why did that happen? Because the helper had to stay executable from frozen `decision.py` without widening the cutover, so mechanical debounce and post-debounce policy reactions were left in one place.
  3. Why is ownership still split even after extraction? Because `reasoning_core.py` later added a separate preexisting-duplicate probe before delegation instead of reusing one dedup owner contract.
  4. Why is that split a problem now? Because the same inbound family can still change behavior through two different duplicate backends plus a mutation-heavy helper that depends on legacy semantic code.
  5. Why is `truffles-api/app/routers/webhook/dedup.py` the truthful destination? Because the package is ingress idempotency/buffering, it already owns the Redis/DB primitives and frozen callsites, and the residual semantic branches can be pushed back to existing downstream owners instead of growing `reasoning_core.py` or `state_service.py`.
- **Root cause statement:** debounce/buffer authority remains mixed because `dedup.py` still combines pure dedup/buffer mechanics with legacy semantic/state reactions, while `reasoning_core.py` shadows duplicate probing with a separate backend lookup path before the frozen delegate.
- **Fix mechanism:**
  - make `truffles-api/app/routers/webhook/dedup.py` the sole ingress dedup/buffer owner surface
  - split pure duplicate probing from mutation-heavy buffering / trace / skip-return assembly inside that owner
  - remove `dedup.py` dependence on legacy semantic ingress helpers by reusing existing downstream non-frozen owners for post-debounce state reactions
  - converge `reasoning_core.py` duplicate preflight to the same dedup owner contract so the old shadow lookup path dies

## Invariant
- `truffles-api/app/services/reasoning_core.py` must not grow into a general debounce/buffer mutation owner or a new ingress switchboard.
- `truffles-api/app/services/state_service.py` must not grow.
- Frozen `truffles-api/app/routers/webhook/decision.py` must remain transport/call-site only for this family; the block is invalid if new authority stays mixed across frozen `decision.py`, `dedup.py`, and `reasoning_core.py`.
- No new helper forest, no one-helper-per-branch pattern, and no new legacy compatibility layer counts as progress.
- If `dedup.py` cannot drop the legacy semantic ingress helpers without a wider frozen waiver or a new mixed hotspot, stop and publish `GAP`.

## Scope
- Publish one package-level implementation plan for the residual `debounce_buffer_owner_convergence` family
- Converge duplicate probing, debounce gating, buffer drain/assembly, and early duplicate/debounce skip artifacts into one non-frozen ingress owner surface
- Remove legacy semantic/state decisions from that owner surface where they duplicate later owner lanes
- Collapse the shadow duplicate-probe split between `dedup.py` and `reasoning_core.py`
- Update only directly impacted tests/docs/contracts for this family

## Out of scope
- `proof_black_box_completion`
- `multi_pack_acceptance`
- new public-entrypoint work
- broader `/webhook` semantic retirement behind frozen `truffles-api/app/routers/webhook/decision.py`
- frozen `truffles-api/app/routers/webhook/decision.py`
- frozen `truffles-api/app/routers/webhook/booking.py`
- frozen `truffles-api/app/routers/webhook/pending.py`
- any staged rollout or prod claim beyond local/runtime validation

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-debounce-buffer-owner-convergence-package-a922.md`
- `STATE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STRUCTURE.md`
- `truffles-api/app/routers/webhook/dedup.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_webhook_dedup.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py` only if directly impacted by the dedup/debounce owner cutover
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/webhook/dedup.py` existing Redis/DB dedup and buffer primitives
  - `truffles-api/app/routers/webhook/guards.py` existing non-frozen mute/reengage owner lane for post-debounce state reactions
  - `truffles-api/app/routers/webhook/context_manager.py` existing reengage confirmation/context helpers
  - `truffles-api/app/services/intent_service.py:is_opt_out_message(...)`
  - `truffles-api/app/routers/webhook/trace.py:_record_decision_trace(...)`
  - `truffles-api/tests/test_webhook_dedup.py`, `truffles-api/tests/test_reasoning_core.py`, and `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - Martin Fowler `Move Function` and `Separate Query from Modifier` guidance from the single mandatory query above
- **Why this reuse mix is truthful:**
  - the existing non-frozen dedup module already owns the persistent ingress mechanics
  - the existing non-frozen guards/context/intent owners already cover the semantic/state decisions that should not live inside the dedup owner
  - reuse deletes the split instead of adding another layer that still leaves old ownership alive

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. Split the residual family into pure ingress mechanics vs post-debounce semantic/state reactions.
3. Keep `truffles-api/app/routers/webhook/dedup.py` as the sole owner for duplicate probe/backends, debounce timing, buffer drain/assembly, and early duplicate/debounce skip artifacts.
4. Remove `dedup.py` dependence on legacy semantic ingress helpers by reusing existing non-frozen owners for post-debounce state reactions or by letting later runtime owners handle those decisions after the buffer result is returned.
5. Converge `truffles-api/app/services/reasoning_core.py` duplicate preflight to the same dedup owner contract and delete the shadow duplicate lookup path.
6. Tighten targeted dedup/reasoning-core tests and only touch broader webhook tests if the owner contract changes their patch points.
7. Run the targeted dedup/debounce lane plus required guards.
8. Record evidence in `STATE.md` only if the old split debounce/buffer authority is actually deleted or unreachable.

## DoD
- one non-frozen owner surface (`truffles-api/app/routers/webhook/dedup.py`) owns the ingress dedup/buffer family
- `truffles-api/app/services/reasoning_core.py` no longer keeps a shadow duplicate backend lookup path for this family
- `truffles-api/app/routers/webhook/dedup.py` no longer depends on legacy semantic ingress helpers such as `_evaluate_booking_signal`, `_coerce_batch_messages`, `_record_decision_trace`, conversation-context reads, reengage checks, or `legacy.is_opt_out_message`
- frozen `truffles-api/app/routers/webhook/decision.py` retains at most call-site delegation for the dedup/debounce family
- targeted dedup/debounce tests pass
- required architecture/session guards pass
- `STATE.md` records the deleted/unreachable old debounce/buffer authority seam with evidence

## Checks
- `rg -n "_handle_dedup_gate|_handle_debounce_gate|is_duplicate_message_id|should_process_debounced_message|_lookup_preexisting_duplicate_message|legacy\._(coerce_batch_messages|evaluate_booking_signal|record_decision_trace|get_conversation_context|get_booking_context|get_reengage_confirmation|is_reengage_confirmation_active)|legacy\.is_opt_out_message" truffles-api/app/routers/webhook/dedup.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `python3 -m py_compile truffles-api/app/routers/webhook/dedup.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/trace.py truffles-api/app/services/intent_service.py truffles-api/tests/test_webhook_dedup.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_state_service.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_webhook_dedup.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'duplicate_message_id or duplicate_probe or http_preflight_bridge_cache_short_circuits_duplicate_non_secret_preflight or secret_preflight_bridge_primes_duplicate_http_preflight'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'only_latest_message_is_processed'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` if `reasoning_core` ownership/contracts change materially
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
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the old split dedup/debounce family reduced to one surviving owner surface plus caller-only frozen delegation
- green targeted dedup/debounce runtime lane plus required guards
- `STATE.md` entry naming the deleted/unreachable old debounce/buffer seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** hotspot grep plus `python3 -m py_compile`
- **Targeted lane next:** `test_webhook_dedup.py`, duplicate-probe tests in `test_reasoning_core.py`, and the debounce concurrency test in `test_state_service.py`
- **Contract lane after targeted pass:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` only if the `reasoning_core` contract changed materially
- **Stop condition:** if implementation requires `reasoning_core.py` to absorb buffered-message mutation or muted/reengage policy ownership, or if `dedup.py` cannot shed the legacy semantic helpers without a wider frozen change, stop and return to RCA instead of growing helpers
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only ingress/runtime compatibility validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - `dedup.py` is the sole dedup/buffer owner surface
  - `reasoning_core.py` no longer shadows duplicate backend lookup
  - targeted dedup/debounce tests pass
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's changes to the touched dedup/reasoning-core files plus synced docs
  - rerun the targeted dedup/debounce test lane and required guards
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_webhook_dedup.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'duplicate_message_id or duplicate_probe'`
  - `pytest -q truffles-api/tests/test_state_service.py -k 'only_latest_message_is_processed'`
- **Post-release monitoring window:** first post-merge consultant-core block only; do not advance to proof or multi-pack work if the duplicate/debounce split reappears

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted dedup/debounce/runtime checks.

## No-go
- Do not grow `truffles-api/app/services/reasoning_core.py` into a mutation-heavy debounce/buffer owner.
- Do not move this family into `truffles-api/app/services/state_service.py`.
- Do not keep duplicate probing split between `reasoning_core.py` and `dedup.py`.
- Do not leave `dedup.py` dependent on legacy semantic ingress helpers and count that as convergence.
- Do not claim consultant correctness, full `/webhook` retirement, or full runtime closure from this block.

## Risks / blockers
- `truffles-api/app/routers/webhook/dedup.py` currently mixes pure mechanics and semantic branches; if the semantic branches prove contractually required before later guards run, the block may need a truthful `GAP` instead of forced convergence.
- `truffles-api/app/services/reasoning_core.py` already short-circuits duplicate inbound before delegate; if that contract cannot reuse a dedup owner hook without widening runtime ownership, the block must stop.
- many existing webhook tests still patch `_legacy.should_process_debounced_message`; the runtime block may need test-surface cleanup without counting test-patch churn itself as progress.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `proof_black_box_completion` and `multi_pack_acceptance` remain open after this package
- broader legacy `/webhook` runtime still remains behind frozen `truffles-api/app/routers/webhook/decision.py`
- some broader mute/reengage/guard ownership still lives in `truffles-api/app/routers/webhook/guards.py` and is not retired by this package

### Why not in this block
- this package only deletes the split dedup/debounce owner family
- collapsing proof observers, broader `/webhook` retirement, or later multi-pack acceptance into the same block would hide whether the dedup family actually converged

### Risk if deferred
- duplicate/idempotency behavior remains split between two runtime paths
- debounce buffering keeps depending on legacy semantic helpers and can continue to reintroduce ingress coupling
- test surfaces keep patching old `_legacy` dedup hooks instead of one owner contract

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922` (ordered later)
- `TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922` (ordered later)

### Expiry/trigger to stop deferral
- stop deferral if any new duplicate/debounce ingress rule lands outside `truffles-api/app/routers/webhook/dedup.py` before this package is implemented

## Next-block contract (mandatory)
### Next block objective
- implement the `debounce_buffer_owner_convergence` runtime family convergence defined by this TP and delete or bypass the split dedup/debounce authority family

### First deterministic check command
- `rg -n "_handle_dedup_gate|_handle_debounce_gate|is_duplicate_message_id|should_process_debounced_message|_lookup_preexisting_duplicate_message|legacy\._(coerce_batch_messages|evaluate_booking_signal|record_decision_trace|get_conversation_context|get_booking_context|get_reengage_confirmation|is_reengage_confirmation_active)|legacy\.is_opt_out_message" truffles-api/app/routers/webhook/dedup.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`

### Blocked-by conditions
- inability to keep `truffles-api/app/routers/webhook/dedup.py` as the sole owner surface without growing `reasoning_core.py`
- any implementation that leaves shadow duplicate probing live in `truffles-api/app/services/reasoning_core.py`
- any implementation that still requires the legacy semantic ingress helpers inside `dedup.py`
- any implementation that requires frozen `decision.py`, `booking.py`, or `pending.py` to absorb this family instead of remaining caller-only

### Owner role for closure
- Brain / Top Architect
