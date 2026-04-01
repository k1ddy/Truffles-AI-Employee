# TP-2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922

## Название / цель
Снять ложные closure-claims после live-code перепроверки и вернуть активную программу к первому реально незакрытому инварианту: `single semantic owner` и `post-owner semantic reconstruction`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com architectural fitness function software architecture`
- Date/time (local): `2026-03-31 23:45 +0500`
- Sources opened:
  - `https://www.martinfowler.com/ieeeSoftware/mda-thomas.pdf`
- Source quality:
  - high-signal architecture source hosted by Martin Fowler archive
- Ready solutions found:
  - architecture claims must be backed by executable fitness checks, not narrative alignment only
  - closure should be asserted only after the code-level mechanism is actually constrained
- Decision (`reuse/integrate/build`): `integrate + build`
  - reuse the existing registry/guard pattern
  - integrate live-code evidence into the governing layer
  - build one truth-correction guard that blocks further false closure claims
- Rejected options:
  - keeping final-closure status while known live competing paths remain
  - replay before semantic-owner truth is re-opened

## Invariant
- Do not claim closure for any mechanism that is not proven on live code.
- Do not run replay or human audit in this block.
- Do not change runtime behavior in this block.
- Do not leave active docs/tests saying that only replay remains.

## Scope
- retract unsupported closure claims from active docs/registries/packet
- reopen `single semantic owner` and `post-owner semantic reconstruction`
- downgrade machine-readable status from final closure to truth-correction base
- add a guard/test that blocks self-referential closure claims while known live code evidence remains
- publish the follow-up TP for the real runtime reopen block

## Out of scope
- runtime code changes to fix semantic-owner violations
- replay
- human semantic audit
- new symptom-family fixes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md`
- `docs/CLOSURE_CLAIM_TRUTH_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/closure_claim_truth_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_closure_claim_truth_guard.py`

## Root cause (mandatory)
### Symptom
Active docs, registries, and tests said whole-system architecture closure was complete and that only replay remained, but live code still contains non-owner semantic writing and post-owner reconstruction.

### Minimal reproduction
1. Read active closure claims in `docs/ACTIVE_CANON.md`, `docs/ACTIVE_PROGRAM.md`, `docs/system_forensics/authority_registry.json`.
2. Inspect live code in `truffles-api/app/core/turn_planner.py`, `truffles-api/app/core/consultant_runtime.py`, `truffles-api/app/core/dialog_state_service.py`, and `truffles-api/app/core/turn_executor.py`.
3. Observe synthetic control `PolicyDecision` creation and downstream semantic-contract reconstruction.
4. Observe that active tests mostly confirm registry narrative, not the conflicting live code paths.

### Evidence
- `truffles-api/app/core/turn_planner.py:690`
- `truffles-api/app/core/turn_planner.py:724`
- `truffles-api/app/core/consultant_runtime.py:528`
- `truffles-api/app/core/consultant_runtime.py:551`
- `truffles-api/app/core/dialog_state_service.py:960`
- `truffles-api/app/core/dialog_state_service.py:1013`
- `truffles-api/app/core/turn_executor.py:1147`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `docs/system_forensics/authority_registry.json`

### Five Whys
1. Why did closure get claimed too early?
  - Because green registry/guard sync was treated as proof of mechanism closure.
2. Why is that invalid?
  - Because the live code still contains semantic control and reconstruction paths outside the owner.
3. Why did the tests miss that?
  - Because they mostly validated machine-readable declarations, not conflicting runtime code facts.
4. Why is that dangerous?
  - Because it creates false completion and sends the program to replay while the base invariant is still broken.
5. Why must truth correction happen before new runtime work?
  - Because other agents need one honest active operating base before touching code again.

### Broken invariant
No block may claim closure while the declared mechanism still has live competing writers or downstream reconstruction paths in code.

### Shared mechanism
Closure-claim truth correction for semantic owner and post-owner reconstruction.

### Why the surfaced family belongs to that mechanism
The failure is not one runtime behavior bug; it is a false architecture-closure claim that directly misstates the active system topology.

### Open-world envelope expected to improve after the fix
- future agents see the real open invariant first
- replay stays blocked until the invariant is actually repaired
- docs/tests no longer overstate closure against live code

### Root cause statement
The governing layer allowed self-referential proof: registries and tests confirmed the declared closure story even though live code still contained competing semantic writers and post-owner reconstruction.

### Fix mechanism
Downgrade active governance from final closure to truth-correction, encode live-code evidence of the open invariant, and make semantic-owner reopen the only admissible next runtime block.

## Plan
1. Publish this truth-correction TP/report and a follow-up TP for semantic-owner reopen.
2. Roll back active docs/registries from whole-system closure to truth-correction status.
3. Replace “replay next” with “semantic-owner reopen next”.
4. Add a truth guard that fails if active docs claim closure while known live semantic-control/reconstruction markers still exist.
5. Sync packet/state/structure once after all truth-correction checks pass.

## DoD
- Active block is `Consultant Core Closure-Claim Truth Correction And Semantic-Owner Reopen`.
- Active docs no longer claim that repo-side architecture closure is complete or that replay is the only next move.
- `authority_registry.json` no longer claims semantic-owner closure and points semantic-owner work next to `semantic_owner_and_post_owner_reconstruction_reopen`.
- Governance statuses are downgraded from whole-system closure base to truth-correction base.
- New guard/test proves the active docs stay honest while live code still contains the reopened evidence markers.
- Packet/state/canon/program are synced once at block closeout.

## Work mode
- governance correction

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/closure_claim_truth_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_closure_claim_truth_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md`
- `docs/CLOSURE_CLAIM_TRUTH_GUARD.yaml`
- `scripts/closure_claim_truth_guard.py`
- updated active docs/registries/packet
- `truffles-api/tests/architecture/test_closure_claim_truth_guard.py`

## Rollback
- restore the prior active whole-system-governance-closure base if this truth correction is rejected

## No-go
- do not touch runtime semantic code in this block
- do not run replay
- do not keep any active statement that only replay remains
- do not treat registry/test sync as mechanism proof

## Risks / blockers
- broader continuity, boundary, pack/runtime, legacy, and operational claims still need reproof after semantic-owner reopen
- old historical closure artifacts remain in the repo and must stay historical, not active

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- live non-owner semantic control paths remain
- live post-owner semantic reconstruction remains
- broader continuity / boundary / pack-runtime / legacy / operational closure still requires reproof

### Why not in this block
This block corrects truth and governance only; it does not change runtime code.

### Risk if deferred
Any new agent can continue from a false `done` base and make the repo less trustworthy.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md`

### Expiry / trigger to stop deferral
- stop deferral before any replay, product-quality claim, or new block closeout is attempted

## Next-block contract (mandatory)
### Next block objective
Remove live non-owner semantic control decisions and downstream semantic-contract reconstruction on the hot path.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
text = Path('truffles-api/app/core/turn_planner.py').read_text(encoding='utf-8')
assert 'build_controlled_degrade' in text
print('semantic_owner_reopen_required')
PY`

### Blocked-by conditions
- truth-correction block not accepted
- active docs still claim replay is the only next move
- authority registry still marks semantic owner as closed

### Owner role for closure
Brain / Top Architect
