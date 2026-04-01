# TP-2026-03-18-consultant-core-handover-frozen-internal-self-use-classification-a922

## Goal
Truthfully classify whether the remaining frozen handover self-use wrappers in `truffles-api/app/routers/webhook/decision.py` still constitute live mixed authority or are now compatibility-only residue after the owner-family convergence blocks.

## Canon refs
- `STATE.md` NOW: handover owner convergence, state-service helper collapse, frozen compat seam reduction, escalation supporting-helper closure, frozen read/notify seam reduction
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-read-notify-seam-reduction-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after doc/guard checks are green; no runtime closure claim without a real seam deletion
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Remove Middle Man" "Inline Function"`
- Date/time: `2026-03-18 09:32:37 +05`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/removeMiddleMan.html`
  - `https://refactoring.com/catalog/inlineFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Remove Middle Man`: bypass a relay when callers can use the real owner directly
  - `Inline Function`: remove a forwarding wrapper only when it adds no useful boundary or contract
- Decision: `classify before build`
  - use the catalog as the gate: if the frozen wrappers are pure forwarders with no remaining local authority, classify them as compatibility residue and stop handover churn
  - only authorize a new runtime reduction if the wrappers still author behavior beyond forwarding/binding
- Rejected variants:
  - automatic further inline of all wrapper call sites: rejected because that would be a broader frozen rewrite without first proving a live seam still exists
  - declaring family closure without call-graph proof: rejected because the program requires proof, not narrative

## Root cause (mandatory)
- Symptom:
  - `decision.py` still contains `_reuse_active_handover(...)` and `_create_pending_escalation_with_notification(...)`
  - those wrappers are still called many times inside the frozen file
- Minimal reproduction:
  - `sed -n '8400,8460p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_reuse_active_handover\(|_create_pending_escalation_with_notification\(" truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1080,1210p' truffles-api/app/services/handover_owner_service.py`
- Evidence:
  - the frozen wrappers delegate directly to `_handover_owner_reuse_active_handover(...)` / `_handover_owner_create_pending_escalation_with_notification(...)`
  - the hooks they bind are `transition_state` from `state_service`, `_record_decision_trace` from `trace`, owner `send_telegram_notification`, owner `get_active_handover`, and owner `escalate_to_pending`
  - no remaining handover create/reuse/notify body lives in `decision.py`
- Five Whys:
  1. Why do wrappers remain? Because prior blocks removed live bodies first and left bounded frozen self-use shims in place.
  2. Why do they look suspicious? Because they still sit in the giant frozen hotspot and are still called many times.
  3. Why might they no longer be live authority? Because they now only bind existing owner/support hooks and immediately delegate to owner code.
  4. Why is this distinction important? Because the program only counts progress when an old live seam dies; deleting compatibility residue by broad rewrite is not mandatory if authority is already gone.
  5. Why must this be classified explicitly? Because otherwise the team can either over-claim closure or waste time on non-admissible frozen churn.
- Root cause statement:
  - The residual ambiguity exists because earlier family-closure blocks moved the live handover logic out, but left frozen self-use wrappers whose remaining role had not yet been proven as either live authority or compatibility-only residue.
- Fix mechanism:
  - inspect the hook assembly and call graph against the owner implementation
  - classify the wrappers truthfully
  - only authorize a new runtime cut if the wrappers still author behavior that is not already owned elsewhere

## Invariant
- No new handover logic lands in `state_service.py`, `escalation_service.py`, or frozen `decision.py`.
- Do not touch `booking.py` or `pending.py` in this classification block.
- Do not claim full handover-family closure without proof.

## Scope
- classification of `decision.py::_reuse_active_handover(...)` and `decision.py::_create_pending_escalation_with_notification(...)`
- doc/guard updates required to publish the classification result truthfully

## Out of scope
- new runtime rewrite inside `decision.py`
- proof bundle / multi-pack correctness
- boundary-owner implementation

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-internal-self-use-classification-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- generated packet artifacts only if required by packet build/check

## Reuse-first plan (mandatory)
1. Reuse the current owner-service hook contracts and local call graph as the evidence base.
2. Compare the frozen wrapper hook assembly to the owner-service internal hook assembly.
3. If the frozen wrappers only forward/bind existing owner/support hooks, classify them as compatibility-only residue.
4. If any wrapper still authors live state/trace/side-effect behavior not already owned elsewhere, stop and author a bounded frozen implementation TP.

## Plan
1. Capture wrapper body evidence from `decision.py` and owner body evidence from `handover_owner_service.py`.
2. Author and register this classification TP.
3. Run doc/guard checks.
4. Publish truthful classification in `STATE.md`, including whether any old seam actually died in this block.

## DoD
- TP records a clear classification verdict with code evidence
- `STATE.md` records whether the residual frozen self-use seam is still live mixed authority or compatibility-only residue
- if no old seam died in this block, that is stated explicitly
- doc/guard checks pass

## Checks
- `rg -n "def _reuse_active_handover|def _create_pending_escalation_with_notification|_reuse_active_handover\(|_create_pending_escalation_with_notification\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/handover_owner_service.py`
- `rg -n "transition_state|_record_decision_trace|send_telegram_notification|get_active_handover|escalate_to_pending" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/handover_owner_service.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/trace.py`
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
- This is a doc/classification block only.
- Runtime change is explicitly out of scope unless the classification proves a live seam remains and a separate bounded implementation TP is authored.
- Go/no-go signal: do not claim runtime deletion from this block unless a real runtime seam is changed.
- Rollback: revert the doc updates only.

## Evidence
- TP + `STRUCTURE.md`
- `STATE.md` classification entry
- `rg`/`sed` proof showing wrapper bodies and owner bodies
- green doc/guard checks

## Rollback
- Revert the TP/STATE/STRUCTURE updates and rerun the doc/guard checks.

## No-go
- Do not count this block as runtime progress if no seam is deleted.
- Do not broaden into a frozen rewrite in the same block.
- Do not touch `booking.py`.
- Do not claim handover family fully closed without explicit proof.

## Risks / blockers
- The wrappers may be thin enough that deleting them would only be cosmetic churn.
- The wrappers may still be mistaken for live authority because they sit in a frozen hotspot with many call sites.
- If the evidence is ambiguous, status must be `GAP`, not “probably fine”.

## Token / run budget (mandatory for expensive suites)
- Cheap evidence first: `rg` + `sed`
- Doc/guard checks second
- No expensive runtime suites in this classification block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still contains `_reuse_active_handover(...)` and `_create_pending_escalation_with_notification(...)`
- boundary-owner hotspot remains elsewhere in `decision.py`

### Why not in this block
- this block is only the classification gate
- deleting the wrappers without proof of remaining authority would be fake progress

### Risk if deferred
- the team may continue unnecessary frozen handover churn or over-claim family closure

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-family-classification-a922` if handover residue is classified compatibility-only
- or a new bounded frozen handover implementation TP only if this block proves a live mixed seam still remains

### Expiry/trigger to stop deferral
- stop deferral if new behavior is added to the frozen wrappers or if another block tries to count progress without killing a real seam

## Next-block contract (mandatory)
### Next block objective
- if handover residue is compatibility-only, shift the stop-the-line program to the first real `boundary_owner` family hotspot outside fake handover churn

### First deterministic check command
- `rg -n "_derive_pending_booking_resume_boundary_payload|_resolve_resume_boundary_activation|apply_timeout_owner_boundary_resolution|BoundaryOverride|boundary_state|boundary_reason" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/app/core/boundary_validator.py`

### Blocked-by conditions
- classification evidence is ambiguous
- a real live handover seam is found and needs a separate bounded runtime TP first

### Owner role for closure
- Brain / Top Architect
