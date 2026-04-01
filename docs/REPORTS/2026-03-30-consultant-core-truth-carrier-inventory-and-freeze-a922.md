# 2026-03-30 — Consultant Core Truth-Carrier Inventory And Freeze

## Summary

This block turned the continuity carrier inventory into a machine-readable truth-carrier freeze law.

The repo now has:
- explicit phase advance from block 2 to block 3 recorded in the recovery lock / waiver layer while practical truth stays `r35f` and runtime stays paused
- explicit writer precedence per continuity carrier
- explicit reader precedence per continuity carrier family
- one frozen no-new-competing-writer guard contract
- booking continuity carriers promoted into the continuity inventory
- previously grouped auxiliary carrier families split into explicit carrier rows

No runtime behavior changed in this block.

## What Changed

### 1. Compatibility inventory became a freeze law
`docs/system_forensics/compatibility_carrier_inventory.json` moved from inventory-only to freeze-law status:
- `schema_version: v3`
- `status: machine_readable_truth_carrier_freeze`
- top-level `freeze_guard`
- top-level `reader_precedence_law`
- per-carrier writer precedence
- per-carrier reader precedence
- per-carrier allowed future write paths
- per-carrier guarded context tokens
- per-carrier expiry trigger

### 2. Missing continuity carriers were added
The carrier map now explicitly includes the previously missing booking continuity surfaces:
- `consultant_runtime.booking_payload`
- `context.booking`

### 3. Grouped low-confidence carriers were sharpened
The old grouped auxiliary family is now split into explicit carriers:
- `handover_confirmation`
- `reengage_confirmation`
- `asr_confirm_pending`
- `asr_inflight`
- `style_reference_pending`
- `memory_profile`
- `memory_pending`

The queue/service-hint/re-entry family was also sharpened with explicit freeze law fields:
- `intent_queue_and_service_hints`

### 4. The continuity guard is now wired to the active machine-readable base
- `docs/LEGACY_SUNSET.yaml` now contains the active `continuity_guard`
- `scripts/continuity_writer_guard.py` now resolves its guard contract from `docs/SOURCE_OF_TRUTH.yaml` and the freeze law
- `scripts/build_agent_packet.py` now validates sync between the freeze-law guard contract and `docs/LEGACY_SUNSET.yaml`
- `scripts/arch_guard.py` now enforces the same contract through the standard architecture gate

### 5. Canon switched to the new active block
The active operating base now points to:
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md`

That switch is reflected in:
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Freeze-Law Coverage

The continuity freeze law now covers these carrier families explicitly:
- canonical runtime state
- canonical runtime booking payload
- runtime projection and journal
- runtime trace observer shadow
- context-manager canonical shadow
- top-level booking compatibility state
- expected-reply compatibility fields
- current-goal compatibility field
- service/consult/class carryover surfaces
- session memory
- pending resume
- intent queue / service hints / re-entry gate
- handover / reengage confirmations
- ASR confirmation / inflight state
- style-reference pending state
- memory profile / memory pending

## Low-Confidence Entries

No carrier rows remain `medium` or `low` in the freeze-law inventory.

Residual risk is no longer “missing carrier rows”.
Residual risk is that many of those carriers are still live at runtime and must be drained in later phases.

## Checks

Executed for this block:
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k continuity_writer`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `git diff --check`

## Residual Debt

Still open after this block by design:
- competing continuity carriers still exist at runtime
- legacy webhook-era modules still read and write those carriers
- canonical state is still forced to coexist with compatibility carriers
- planner/executor/runtime shell semantic reconstruction is still open
- boundary/degrade constriction is still open
- first-class fact plane is still missing

## Block Status

Implementation truth:
- this block is materially complete in repo artifacts, guards, tests, packet, and canon sync
- this block has been phase-advanced to block 4 by explicit user instruction recorded in `docs/RECOVERY_PHASE_WAIVER.yaml`
- the next phase advance beyond block 4 still requires explicit owner/architect acceptance

This report therefore treats the block as:
- `materially_complete_in_repo`
- `phase_advanced_to_block_4_under_explicit_user_waiver`
- `program_phase_advance_beyond_block_4_pending_owner_acceptance`

## Next Admissible Block

After acceptance of this block, the exact next admissible block is:
- adapter-only legacy mesh and caller proof

That block must start from the now-frozen continuity law and prove exact live callers of the legacy mesh, not guess from stale docs.
