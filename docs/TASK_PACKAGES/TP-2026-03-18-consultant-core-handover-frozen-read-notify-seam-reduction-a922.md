# TP-2026-03-18-consultant-core-handover-frozen-read-notify-seam-reduction-a922

## Goal
Delete the remaining bounded frozen handover read/notify compatibility seam in `truffles-api/app/routers/webhook/decision.py` where the frozen file still hosts a live `get_active_handover` wrapper and still pulls `send_telegram_notification` through `escalation_service.py` instead of the owner surface.

## Canon refs
- `STATE.md` NOW: handover owner convergence, state-service helper collapse, frozen compat seam reduction, escalation supporting-helper closure
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Inline Function" "Remove Middle Man"`
- Date/time: `2026-03-18 09:32:37 +05`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/inlineFunction.html`
  - `https://refactoring.com/catalog/removeMiddleMan.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Inline Function`: remove a no-value forwarding wrapper when the call site can point to the real implementation directly
  - `Remove Middle Man`: bypass a compatibility relay once callers can safely depend on the true owner surface
- Decision: `integrate`
  - remove the frozen `get_active_handover(...)` forwarding body and use the imported owner symbol directly
  - remove the frozen relay through `escalation_service.send_telegram_notification` and bind the decision hook directly to the owner surface
- Rejected variants:
  - broad frozen rewrite of all `_reuse_active_handover` / `_create_pending_escalation_with_notification` call sites: rejected as too wide for this block
  - keeping the forwarding wrapper and only renaming imports: rejected because the old frozen seam would remain live

## Root cause (mandatory)
- Symptom:
  - `decision.py` still contains a live `get_active_handover(...)` forwarding wrapper
  - `decision.py` still imports `send_telegram_notification` from `escalation_service.py`, which is now only a compatibility layer
- Minimal reproduction:
  - `sed -n '8392,8468p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "get_active_handover\(|send_telegram_notification" truffles-api/app/routers/webhook/decision.py`
- Evidence:
  - `decision.py:8401` hosts `def get_active_handover(...) -> _handover_owner_get_active_handover(...)`
  - `decision.py:8424` and `decision.py:8448` pass `send_telegram_notification` from the legacy support module into handover hooks
  - `decision.py:19914` still reads active handover existence through the frozen wrapper symbol
- Five Whys:
  1. Why does frozen handover residue remain? Because earlier closure blocks prioritized moving live bodies out before trimming final relays.
  2. Why is this still relevant? Because the frozen file still participates in a read/notify path instead of pointing directly at the owner surface.
  3. Why is that a problem? Because it preserves unnecessary handover authority shape in the frozen hotspot.
  4. Why has it not already been removed? Because external/frozen compatibility had to be stabilized first.
  5. Why is it safe now? Because `_legacy` already bypasses `decision.py`, `escalation_service.py` is compatibility-only for the moved handover family, and the remaining relay is bounded to one wrapper plus one support import.
- Root cause statement:
  - The residual frozen seam exists because `decision.py` still keeps a forwarding read wrapper and still depends on a compatibility notification relay even after the owner surface became the real runtime authority.
- Fix mechanism:
  - inline the frozen read wrapper to the imported owner symbol
  - point the frozen notification hook directly at the owner notification symbol
  - keep the rest of the frozen self-use handover wrappers unchanged in this block

## Invariant
- No new handover authority may re-enter `state_service.py` or `escalation_service.py`.
- Frozen `booking.py` and `pending.py` remain untouched.
- No broad rewrite across many frozen call sites.
- No semantic hardcode or weakened guards.

## Scope
- `decision.py` handover read/notify bounded seam only
- related targeted tests/docs if import/patch behavior changes

## Out of scope
- broad handover call-site rewrite inside `decision.py`
- proof bundle / multi-pack correctness
- boundary-owner family work
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-read-notify-seam-reduction-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py` only if required

## Reuse-first plan (mandatory)
1. Reuse the existing owner imports already available in `decision.py`.
2. Replace the frozen `get_active_handover(...)` function body with a direct symbol binding to the owner import.
3. Replace the frozen notification dependency on `escalation_service.py` with the owner notification symbol.
4. Leave the broader frozen self-use wrappers untouched unless this bounded seam cannot be removed otherwise.
5. Validate with targeted handover message-endpoint checks and required guards.

## Plan
1. Author and register this TP.
2. Reduce `decision.py` read/notify seam to direct owner bindings.
3. Update targeted tests only if runtime patch points change.
4. Run targeted runtime checks and required guards.
5. Record evidence in `STATE.md` only if the old frozen read/notify seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer hosts a forwarding `get_active_handover(...)` function body
- `decision.py` no longer imports `send_telegram_notification` from `escalation_service.py` for the moved handover family
- targeted tests and required guards are green
- `STATE.md` records the deleted/unreachable frozen seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_escalation_reuses_active_handover or legacy_handover_adapter or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve or booking_verification_creates_handover_when_none_active or booking_verification_request_does_not_escalate_active_booking_without_reference'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Release safety (mandatory for non-doc changes)
- Rollout strategy: local-only bounded frozen-waiver validation in this worktree before any merge; no prod rollout claim in this block
- Go/no-go signals:
  - no forwarding `get_active_handover(...)` body remains in `decision.py`
  - `decision.py` notification hook no longer depends on `escalation_service.py`
  - targeted handover tests and required guards pass
- Rollback:
  - revert the `decision.py` read/notify edits and any impacted tests/docs
- Rollback verification:
  - rerun the targeted message-endpoint checks plus required guard set

## Evidence
- TP + `STRUCTURE.md`
- diff proving `decision.py` wrapper removal / direct owner notification binding
- targeted green tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert this block's `decision.py` and test/doc changes, then rerun the targeted handover checks.

## No-go
- Do not widen the frozen edit into a broad handover rewrite.
- Do not touch `booking.py`.
- Do not move owner logic back into `escalation_service.py`.
- Do not claim family closure beyond what this bounded seam actually deletes.

## Risks / blockers
- Some tests may patch `decision.py` handover symbols and need redirection if symbol shapes change.
- If deleting the wrapper forces a wider frozen rewrite, stop and publish `GAP` instead.

## Token / run budget (mandatory for expensive suites)
- Cheap gate first: `py_compile` + targeted message-endpoint selection
- Medium suites next: `test_reasoning_core.py`, `test_consultant_core_runtime_contracts.py`
- Required guard set last
- Stop condition: if two consecutive iterations fail without a new structural deletion, stop and return to RCA

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `_reuse_active_handover(...)` and `_create_pending_escalation_with_notification(...)` wrappers still remain in `decision.py`
- frozen self-use handover call sites inside `decision.py` still exist

### Why not in this block
- removing those wrappers safely would require a broader frozen rewrite than this bounded seam reduction allows

### Risk if deferred
- the frozen hotspot still retains some handover orchestration shape, even after the bounded read/notify seam is removed

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-handover-frozen-internal-self-use-classification-a922` if the remaining seam still needs truthful classification after this block

### Expiry/trigger to stop deferral
- stop deferral if new handover behavior lands in the remaining frozen wrappers or if another block tries to count progress without deleting a real frozen seam

## Next-block contract (mandatory)
### Next block objective
- classify whether the remaining frozen `_reuse_active_handover(...)` / `_create_pending_escalation_with_notification(...)` self-use seam is still live mixed authority or has become acceptable compatibility-only residue

### First deterministic check command
- `rg -n "def _reuse_active_handover|def _create_pending_escalation_with_notification|_reuse_active_handover\(|_create_pending_escalation_with_notification\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/handover_owner_service.py`

### Blocked-by conditions
- this block fails to delete the frozen read/notify seam
- tests require a broader frozen rewrite than scoped here
- required guards fail

### Owner role for closure
- Brain / Top Architect
