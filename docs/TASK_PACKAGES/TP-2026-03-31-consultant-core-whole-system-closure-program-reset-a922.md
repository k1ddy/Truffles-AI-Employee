# TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922

## Название / цель
Сбросить активную governing execution base с canary-closeout/replay-next на whole-system architecture closure, чтобы все следующие агенты работали от одного полного accelerated plan и не обновляли canon/state после каждого микродействия.

## Canon refs
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com branch by abstraction parallel change legacy system`
- Date/time (local): `2026-03-31 00:00 +0500`
- Sources opened:
  - `https://martinfowler.com/ieeeSoftware/beforeClarity.pdf`
- Source quality:
  - primary source / Michael Feathers via Martin Fowler archive
- Ready solutions found:
  - safe dependency-breaking and sequencing must precede broad cleanup in legacy systems;
  - you gain speed by clarifying seams and testability first, not by random local changes.
- Decision (`reuse/integrate/build`): `integrate`
  - integrate those sequencing lessons into the whole-system governing program.
- Rejected options:
  - leave replay as the next move;
  - keep canary closeout as the active operating base;
  - keep updating `STATE.md` and canon after partial micro-fixes inside unfinished blocks.

## Invariant
- No runtime behavior changes.
- No replay or human audit.
- No active move may start from a surfaced symptom family.
- No micro-fix-based `STATE.md` or canon updates before a full block completes.
- Canon/state/report sync happens only after one full block completes.

## Scope
- switch active governing docs to the whole-system closure program
- lock in block-closeout reporting discipline
- align packet/guards/tests to the new active block

## Out of scope
- `Authority Freeze` implementation itself
- fact contract implementation
- runtime code changes

## Touch-list
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/whole_system_program_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_whole_system_program_guard.py`

## Plan
1. Publish the whole-system governing DEC.
2. Publish the whole-system master program TP.
3. Switch active lock/canon/program/source-of-truth to the new active block.
4. Re-point the next move from replay to `Authority Freeze -> Fact Contract Schema`.
5. Add a block-specific whole-system program guard.
6. Sync packet/tests/state/structure once, at the close of this full block.

## DoD
- `ACTIVE_*`, `SOURCE_OF_TRUTH`, `RECOVERY_EXECUTION_LOCK`, and packet all point to the whole-system program reset block.
- `current_non_negotiable_next_move` is no longer replay.
- block-closeout reporting discipline is explicit and machine-readable.
- guard/tests fail if the active docs drift back to canary replay-first behavior.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/whole_system_program_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_whole_system_program_guard.py`
- `git diff --check`

## Evidence
- new DEC
- new master TP
- active block TP
- report for this reset block
- synced packet and guard outputs

## Rollback
- restore previous active block lock and packet if the reset is rejected

## No-go
- no replay
- no runtime patching
- no partial state/canon/report updates during unfinished downstream blocks

## Risks / blockers
- later implementation still depends on unknown callers and carrier inventories
- this block only resets execution law; it does not itself reduce runtime authority debt

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- semantic owner extraction still open
- continuity collapse still open
- fact plane still open system-wide
- legacy mesh still open system-wide
- operational entrypoint dedupe still open

### Why not in this block
This block only changes the governing execution base.

### Risk if deferred
Future agents will keep making local progress against the wrong operating base.

### Linked follow-up Task Package(s)
- future: `Authority Freeze`
- future: `Fact Contract Schema`

### Expiry / trigger to stop deferral
- stop deferral immediately after this reset block is accepted

## Next-block contract (mandatory)
### Next block objective
Complete `Authority Freeze` as the first whole-system implementation block and publish field-level writer/caller inventories.

### First deterministic check command
`python3 - <<'PY'
import json
from pathlib import Path
for rel in [
    'docs/system_forensics/authority_registry.json',
    'docs/system_forensics/compatibility_carrier_inventory.json',
    'docs/system_forensics/dead_surface_registry.json',
]:
    assert Path(rel).exists(), rel
print('authority_freeze_inputs_present')
PY`

### Blocked-by conditions
- active docs still reference replay as the next move
- block-closeout reporting discipline not locked

### Owner role for closure
Brain / Top Architect
