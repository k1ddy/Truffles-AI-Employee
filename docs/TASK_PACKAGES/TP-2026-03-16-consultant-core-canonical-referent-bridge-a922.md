# TP-2026-03-16-consultant-core-canonical-referent-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CANONICAL-REFERENT-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-NORMALIZATION-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-normalization-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после session-memory normalization bridge: canonical dialog-state referent shaping must stop living in `truffles-api/app/routers/webhook/context_manager.py`. `DialogStateService` should become the owner of normalized canonical referent set/project/prune behavior for `current_referents`, while `context_manager.py` stays as a thin orchestration layer around manager mutation and legacy compatibility helpers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-normalization-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '100,230p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "current_referents|set_canonical_referent|project_canonical_referent|prune_canonical_referent" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_service_carryover_reads_from_canonical_dialog_state'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already normalizes canonical dialog state, including `current_referents`, but `context_manager.py` still owns referent payload shaping and TTL/age projection in `_set_canonical_referent(...)`, `_project_canonical_referent(...)`, and `_prune_canonical_referent(...)`.
  - These helpers feed live service/master carryover compatibility paths, so the canonical referent seam is still a live continuity writer outside `DialogStateService`.
  - The seam is bounded because it only touches `current_referents` state payloads and existing carryover readers already have focused compatibility tests.
- `Detected drift (docs vs code)`: single continuity writer completion is still blocked by canonical referent shaping living in `context_manager.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python dict pop official documentation`
- **Date/time (local):** `2026-03-16 21:34 +0500`
- **Why this query is precise:** the block moves canonical referent set/prune logic into `DialogStateService` and must preserve dict removal/update semantics when deleting expired or empty referents.
- **Sources opened (from this query):**
  - `Built-in Types — Mapping Types — dict` — `https://docs.python.org/3/library/stdtypes.html#mapping-types-dict`
- **Source quality:** official Python documentation.
- **Existing solutions found:** standard `dict.pop()`/copy semantics are the correct baseline for bounded referent set/prune updates without custom mutation helpers.
- **Decision:** `reuse + integrate` — preserve the existing dict-based referent update semantics while relocating ownership into `DialogStateService`.
- **Rejected options:**
  - leaving referent shaping in `context_manager.py`
  - widening this block into broader canonical dialog-state sync orchestration
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** canonical referent payload shaping is still owned by `context_manager.py`, so `DialogStateService` is not yet the single shaping authority for this live continuity seam.
- **Minimal reproduction:**
  1. Call `_set_service_carryover(...)` or `_sync_canonical_dialog_state(...)`.
  2. Observe that `context_manager.py` builds `current_referents.service` payloads locally via `_set_canonical_referent(...)`.
  3. Call `_get_service_carryover(...)` or `_prune_service_carryover(...)` and observe that age/ttl projection and expiry pruning are also still computed locally.
- **Evidence to capture:**
  - `DialogStateService` directly owns canonical referent set/project/prune behavior.
  - `context_manager.py` becomes a thin wrapper for manager-level state injection only.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented here? Because canonical dialog-state normalization moved, but referent set/project/prune logic stayed local.
  2. Why is that a problem? Because a live continuity payload still has two shaping authorities.
  3. Why can this block stay bounded? Because canonical referents are a single state subtree with existing compatibility tests.
  4. Why not widen into all canonical sync logic? Because broader sync orchestration mixes bounded payload ownership with planner/state orchestration.
  5. Why fix this now? Because this is another real writer deletion on the non-negotiable continuity path.
- **Root cause statement:** `context_manager.py` still decides how canonical `current_referents` entries are written, projected, and pruned, so `DialogStateService` is not yet the sole shaping authority for that live continuity seam.
- **Fix mechanism:**
  - add bounded canonical referent set/project/prune helpers to `DialogStateService`
  - replace local referent shaping in `context_manager.py` with thin delegation
  - prove parity with focused service tests and targeted compatibility checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing canonical state normalization in `DialogStateService`
  - existing message-endpoint carryover compatibility tests
  - existing context-manager manager-state wrappers
- **External reuse:**
  - official Python dict semantics from the standard library docs
- **Why not reinvent the wheel:** this is continuity-owner consolidation, not a new referent model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded canonical-referent writer collapse with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- External canonical referent projection behavior stays unchanged for existing service carryover flows.
- TTL/age/remaining projection semantics stay unchanged.

## Scope
- Add bounded canonical referent set/project/prune helpers to `DialogStateService`.
- Make `context_manager.py` delegate canonical referent shaping to the service.
- Add regression tests for the new service ownership and reuse existing compatibility tests.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- broader canonical dialog-state sync orchestration
- new semantic owner cutovers
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-canonical-referent-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add bounded canonical referent helpers to `DialogStateService`.
3. Replace local referent shaping in `context_manager.py` with thin delegation.
4. Add focused service tests and rerun targeted message-endpoint compatibility checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns canonical referent set/project/prune behavior for this seam.
- `context_manager.py` stays orchestration-only for manager mutation around canonical referents.
- tests prove parity for set, project, and prune behavior.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_service_carryover_reads_from_canonical_dialog_state or test_service_carryover_applies_for_pricing'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- unit tests showing service-owned canonical referent set/project/prune
- targeted message-endpoint checks showing service carryover compatibility is unchanged
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires broader canonical sync widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helpers, context-manager delegation, tests, and doc sync
- **Post-release monitoring window:** next block should continue writer collapse or return to owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the canonical referent bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, context-manager delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader canonical sync/state-restore orchestration
- no counting this block as done unless `context_manager.py` loses local canonical referent shaping authority

## Risks / blockers
- if the helper changes referent ttl/age semantics, service carryover compatibility can drift.
- if the helper changes canonical owner/projection metadata, downstream traces and meta can drift.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this canonical referent seam
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded referent-ownership slice; widening further would mix payload shaping with broader canonical sync orchestration
- **Risk if deferred:**
  - canonical referent drift remains possible because `context_manager.py` stays a live writer for `current_referents`
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-next-seam-a922` (planned)
- **Expiry/trigger to stop deferral:**
  - stop deferral if another block needs new `current_referents` shaping logic in `context_manager.py`

## Next-block contract (mandatory)
- **Next block objective:** either delete the next bounded continuity writer seam after canonical referents or return to richer owner-replacement work only if it deletes an old semantic authority without new bridge growth.
- **First deterministic check command:** `python3 scripts/continuity_writer_guard.py`
- **Blocked-by conditions:** broader canonical sync widening, frozen-router edits, or any need to grow generic semantic bridge families
- **Owner role for closure:** `Top Architect`
