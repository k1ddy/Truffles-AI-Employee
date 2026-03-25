# TP-2026-03-15-consultant-core-governance-lock-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-GOVERNANCE-LOCK-A922`
- `PARENT_BLOCK_ID`: `none`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`
- `UNLOCKS`: `CONSULTANT-CORE-RUNTIME-CONTRACTS-A922`, `CONSULTANT-CORE-NEW-RUNTIME-SLICE-A922`

## Название/цель
Зафиксировать Week 1 governance lock для consultant core controlled demolition: выпустить top-level operational canon, generated agent packet, и fail-closed architecture guards, чтобы новые drift-ходы не могли пройти merge/acceptance даже если следующий агент не знает всю историю.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-p1.6o-demo-salon-architecture-closure-program-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `docs/`
  - `scripts/session_check.sh`
  - `scripts/zero_context_gate.sh`
  - `scripts/`
  - `truffles-api/tests/`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/services/state_service.py`
  - `ops/diagnose.py`
  - `scripts/booking_dialog_scenarios.py`
- `Baseline commands`:
  - `test -f docs/ACTIVE_CANON.md || echo missing:docs/ACTIVE_CANON.md`
  - `test -f docs/SOURCE_OF_TRUTH.yaml || echo missing:docs/SOURCE_OF_TRUTH.yaml`
  - `test -f docs/LEGACY_SUNSET.yaml || echo missing:docs/LEGACY_SUNSET.yaml`
  - `test -f docs/ACTIVE_PROGRAM.md || echo missing:docs/ACTIVE_PROGRAM.md`
  - `test -f scripts/arch_guard.py || echo missing:scripts/arch_guard.py`
  - `test -f scripts/build_agent_packet.py || echo missing:scripts/build_agent_packet.py`
  - `rg -n "interaction_state" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/state_service.py`
  - `rg -n "PolicyDecision|single semantic owner|owner matrix|InteractionState" docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`
- `FACT findings`:
  - top-level governance artifacts requested by the new demolition program do not exist yet: there is no `docs/ACTIVE_CANON.md`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/LEGACY_SUNSET.yaml`, `docs/ACTIVE_PROGRAM.md`, or generated `docs/_generated/AGENT_PACKET.*`.
  - repo already contains strong local architectural discoveries (`P1.6o79..P1.6o83`, `contracts/policy/interaction_owner_matrix.v1.jsonschema`, `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`, persisted `interaction_state` normalization), but they remain distributed across child docs/code rather than one operator-facing source-of-truth surface.
  - current process gates (`scripts/session_check.sh`, `scripts/zero_context_gate.sh`, `scripts/session_gate.sh`) enforce TP/session discipline, but there is no dedicated architecture gate that blocks new additions in sunset files, new continuity-writer drift, or proof-path semantic authority drift.
  - current continuity state already spans `context_manager`, `session_memory`, `pending.py`, and `state_service.py`; without a diff-based guard, the project can still accumulate more writers even though the direction is towards one canonical authority.
  - `STATE.md:92` still points to the old consultant remediation TP as the release-scope source of truth, so a fresh agent can start from the wrong surface and miss the redesign reset.
- `Detected drift (docs vs code)`:
  - architectural intent exists, but it is not surfaced as one generated packet or one top-level canon map.
  - legacy router files still lack a machine-enforced freeze fence.

## One web search (mandatory before implementation)
- **Query (exact):** `Python ast module documentation assignments function calls docs.python.org`
- **Date/time (local):** `2026-03-15 14:05 Asia/Almaty`
- **Why this query is precise:** Week 1 needs diff-based architectural guards. The narrow question is how to use Python's built-in AST tooling to inspect changed code for assignments/calls/imports without adding a new parsing dependency or inventing regex-only enforcement.
- **Sources opened (from this query):**
  - `Python 3 documentation / ast — Abstract Syntax Trees` — `https://docs.python.org/3/library/ast.html`
  - `Python 3 documentation / difflib` — `https://docs.python.org/3/library/difflib.html`
- **Existing solutions found:**
  - Python stdlib already provides enough structure to parse modules, walk assignments/calls/imports, and combine that with unified-diff hunks; no new third-party parser is required.
  - diff-aware enforcement can stay narrow: inspect only added lines and only in governed paths, rather than trying to prove global semantic purity in one step.
- **Decision:** `reuse + integrate` — reuse stdlib AST/diff tooling and integrate it into Truffles-specific architecture guards driven by YAML source-of-truth files.
- **Rejected options:**
  - add another parser/framework dependency for guard scripts;
  - rely on regex-only grep as the primary enforcement mechanism for architectural drift;
  - delay governance until the new runtime core exists.
- **Open questions:**
  - none for Week 1; target is preventive diff-based governance, not full semantic static analysis.

## Root cause (mandatory)
- **Symptom:** consultant architecture knowledge exists, but each new agent still has to rediscover it from scattered TPs/docs/code, and nothing fail-closed prevents new legacy semantic growth or new proof/continuity authorities from reappearing.
- **Minimal reproduction:**
  1. `test -f docs/ACTIVE_CANON.md || echo missing`
  2. `test -f docs/SOURCE_OF_TRUTH.yaml || echo missing`
  3. `test -f scripts/arch_guard.py || echo missing`
  4. `rg -n "P1\.6o79|P1\.6o80|P1\.6o81|P1\.6o82|P1\.6o83" docs/TASK_PACKAGES`
  5. `rg -n "interaction_state" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/state_service.py`
  6. `rg -n "ops/diagnose.py|booking_dialog_scenarios.py" scripts truffles-api/tests truffles-api/app`
- **Evidence to capture:**
  - missing-file baseline for top-level canon/guard/packet files
  - existing interaction-owner / interaction-state artifacts and file refs
  - new guard outputs and architecture tests after implementation
  - generated `docs/_generated/AGENT_PACKET.md` and `.json`
- **Five Whys (or equivalent):**
  1. Why does the same architectural drift keep threatening the project? Because the important rules live mostly in narrative docs and scattered implementation details.
  2. Why is that fragile? Because each new agent has limited context and can start from a different local source of truth.
  3. Why can wrong moves still land? Because current session/quality gates do not specifically block legacy semantic expansion, continuity-writer growth, or proof-path authority drift.
  4. Why is that happening even after `P1.6o79..P1.6o83`? Because those blocks mined the right architecture, but the mined truth was not lifted into one top-level operational canon plus preventive merge gates.
  5. Why must this happen before more runtime work? Because otherwise new runtime slices will still be implemented under documentary governance and the same drift pattern will return.
- **Root cause statement:** the repo has architecture knowledge but not architecture governance: there is no single generated context packet, no top-level executable source-of-truth map, and no fail-closed architecture gate that prevents new drift in legacy semantics, continuity writes, or proof-path authority.
- **Fix mechanism:**
  - publish a top-level controlled-demolition canon and legacy-sunset map;
  - generate one minimal agent packet from those files;
  - add diff-based architecture guards for legacy freeze, continuity-writer drift, and proof-path drift;
  - wire a single `arch_guard.py` entrypoint and deterministic tests so this governance is machine-checked.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `P1.6o79..P1.6o83` as mined architecture evidence and current cutover status
  - `contracts/policy/interaction_owner_matrix.v1.jsonschema`
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
  - `scripts/session_check.sh`, `scripts/zero_context_gate.sh`, `scripts/session_gate.sh`
  - current `interaction_state` normalization in `context_manager.py` and `session_memory.py`
- **External reuse:**
  - Python stdlib `ast` and `difflib` for guard implementation
- **Why not reinvent the wheel:** the repo already discovered the runtime architecture and already has process gates; Week 1 only needs a thin governance layer that surfaces current truth and blocks new drift.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `12`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** the block is mostly governance/docs, but it must ship executable guards and tests or it does not actually reduce future drift.

## Invariant
- No new semantic logic is added to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py` in this block.
- No runtime product behavior is changed for user conversations.
- Existing fail-closed quality/session gates remain intact.
- `FACT/COLLECT/HANDOFF` stays the product outcome contract.

## Scope
- Create top-level controlled-demolition governance docs (`DEC`, `ACTIVE_CANON`, `SOURCE_OF_TRUTH`, `LEGACY_SUNSET`, `ACTIVE_PROGRAM`).
- Add generated `AGENT_PACKET` builder and output files.
- Add diff-based architecture guard scripts plus one `arch_guard.py` entrypoint.
- Add deterministic architecture tests.
- Sync `STRUCTURE.md`, `STATE.md`, and session artifacts to the new governance surface.

## Out of scope
- New runtime core package or cutover.
- Multi-pack acceptance implementation.
- Removal of existing legacy semantic debt already present in runtime.
- LLM-quality reruns.
- Runtime behavior or DB schema changes.

## Touch-list
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/legacy_freeze_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/proof_path_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Create the session/worktree and freeze the exact Week 1 block in session metadata.
2. Publish the controlled-demolition DEC, master TP, and top-level governance canon files.
3. Implement generated agent packet builder and initial packet outputs.
4. Implement diff-based guard scripts for legacy-freeze, continuity-writer drift, proof-path drift, then wrap them in `scripts/arch_guard.py`.
5. Add deterministic tests for the new guard behavior and packet build/check flow.
6. Sync `STRUCTURE.md`, `STATE.md`, session log/index, and run deterministic verification.

## DoD
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md` exists and matches the Week 1 governance scope.
- `docs/ACTIVE_CANON.md`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/LEGACY_SUNSET.yaml`, and `docs/ACTIVE_PROGRAM.md` exist and are truthful about current cutover status.
- `python3 scripts/build_agent_packet.py --check` passes and generated packet files exist.
- `python3 scripts/arch_guard.py` passes on the Week 1 branch.
- `pytest -q truffles-api/tests/architecture` passes.
- `STRUCTURE.md`, `STATE.md`, session log, and session index are updated with FACT-only evidence.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `scripts/session_check.sh`

## Evidence
- Generated `docs/_generated/AGENT_PACKET.md`
- Generated `docs/_generated/AGENT_PACKET.json`
- `scripts/arch_guard.py` pass output
- `pytest -q truffles-api/tests/architecture` output
- Updated `STATE.md`
- Updated session log and session index

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only; no guarded LLM-quality lane is admissible in this block
- **Stop condition:** if Week 1 cannot be expressed as truthful top-level canon plus deterministic guards, stop and reopen RCA instead of widening runtime scope
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive governance rollout only; new guards run locally in this block and are designed for later CI wiring without changing runtime behavior.
- **Go/no-go signals:** `build_agent_packet --check`, `arch_guard.py`, `pytest -q truffles-api/tests/architecture`, `git diff --check`, and `scripts/session_check.sh` are all green.
- **Rollback:** revert Week 1 governance/docs/guard/test files only.
- **Post-release monitoring window:** next consultant-core block must start by running `python3 scripts/arch_guard.py` and `python3 scripts/build_agent_packet.py --check` before any runtime change.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `Drift closeout rule`:
  - publish top-level canon and structure/state/session sync in this same block; if any follow-up is deferred, name the exact TP ID in residual debt.

## Rollback
- Revert the Week 1 governance commit(s) affecting docs/guards/tests.
- Keep pre-existing consultant runtime/code unchanged.

## No-go
- No new semantic helper growth in frozen legacy router files.
- No new continuity writes outside the governed canonical path.
- No new proof/eval authority that rewrites runtime semantics.
- No runtime core cutover hidden inside this governance block.

## Risks/Blockers
- Existing consultant governance is already spread across many child TPs; the new top-level canon must summarize it without contradicting current code reality.
- Diff-based guards must prevent new drift without pretending they already cleaned old debt.
- `STATE.md` currently highlights other local console work, so this block must explicitly record why consultant governance is the new top-level program surface.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: legacy semantic authority still exists in runtime; continuity still has multiple live containers; proof/eval still contains existing historical semantics; no new runtime core package is cut over.
- `Why not in this block`: Week 1 is governance-first and must not mix structural runtime migration with preventive fences.
- `Risk if deferred`: without an immediate follow-up runtime-contract block, the repo will be better governed but still operationally dependent on legacy core.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-runtime-contracts-a922`, `TP-2026-03-15-consultant-core-new-runtime-slice-a922`
- `Expiry/trigger to stop deferral`: before any new consultant runtime slice, proof-lane restart, or platform-level robustness claim.

## Next-block contract (mandatory)
- `Next block objective`: materialize runtime contracts and route one bounded slice through the new controlled path under the Week 1 governance fences.
- `First deterministic check command`: `python3 scripts/arch_guard.py && python3 scripts/build_agent_packet.py --check`
- `Blocked-by conditions`: Week 1 governance files missing; packet generation failing; architecture guards not green.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, `truffles-api/app/routers/webhook/pending.py` for new semantics in this block
- `Open risks`: existing legacy debt remains; SOURCE_OF_TRUTH must stay truthful about current vs target cutover; guard false positives must be kept bounded and test-covered
- `First command to verify`: `python3 scripts/arch_guard.py`
