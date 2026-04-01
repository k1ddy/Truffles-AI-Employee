# TP-2026-03-25 Consultant Core Continuity Writer Guard And Owner Reset A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CONTINUITY-WRITER-GUARD-AND-OWNER-RESET-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `UNLOCKS`: guarded Phase E acceptance replay

## Название/цель
Acceptance оказался честно заблокирован continuity guard’ом. Цель блока — убрать реальные внешние continuity-writers из active runtime path и сделать guard точным, чтобы он блокировал только реальные state writes, а не trace/meta/read plumbing.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: `scripts/continuity_writer_guard.py`, `docs/LEGACY_SUNSET.yaml`, `truffles-api/tests/architecture/test_single_continuity_writer.py`, `truffles-api/tests/architecture/test_arch_guard_packet.py`, and the real external continuity-writer files surfaced by the guard.
- `Baseline commands`:
  - `python3 scripts/continuity_writer_guard.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
  - `curl -fsS http://localhost:8000/admin/health`
- `FACT findings`:
  - `continuity_writer_guard.py` fails on the current branch with `204` hits because it treats any added line containing `expected_reply_*` / `pending_resume` plus `=` or `:` as a violation.
  - Many hits are false positives (`consultant_runtime`, `turn_planner`, `turn_executor`, `booking_prompt_owner`, `llm_quality_contracts`) because they only read, trace, or package continuity values.
  - There are also real external writers outside the allowlist: `truffles-api/app/services/handover_owner_service.py`, `truffles-api/app/services/policy_validation_boundary_service.py`, `truffles-api/app/services/timeout_owner_boundary_service.py`, `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`, and `truffles-api/app/services/reasoning_core.py`.
  - `truffles-api/tests/architecture/test_arch_guard_packet.py` is stale: it still hardcodes the pre-closure active block path and therefore fails after canon moves.
- `Detected drift (docs vs code)`: acceptance was manually green, but the architecture/process guard layer was not aligned with the current continuity-owner contract.

## One web search (mandatory before implementation)
- **Query (exact):** `Python ast Assign Subscript official docs`
- **Date/time (local):** 2026-03-25 15:23, Asia/Almaty
- **Why this query is precise:** the guard needs AST-level detection for real assignment targets (for example `Assign`, `Subscript`, dict writes) instead of line-token heuristics.
- **Sources opened (from this query):**
  - Python docs: `ast — Abstract syntax trees` — https://docs.python.org/3/library/ast.html
- **Existing solutions found:** Python stdlib `ast` exposes `Assign`, `Subscript`, `Attribute`, `Dict`, and source-span metadata, which is enough to classify actual state-write targets.
- **Decision:** build an AST-aware guard refinement on top of the existing script instead of adding more regex waivers.
- **Rejected options:**
  - grow `allowed_writer_paths` to silence false positives: rejected because it would normalize real multi-writer debt
  - add more string waivers: rejected because it keeps the same brittle false-positive mechanism
- **Open questions:** whether `reasoning_core.py` still needs any continuity write after the current shim collapse or can be reduced to read-only trace plumbing

## Root cause (mandatory)
- **Symptom:** acceptance preflight is blocked because `continuity_writer_guard.py` fails across the active branch, while `test_arch_guard_packet.py` still expects the old active block.
- **Minimal reproduction:** run `python3 scripts/continuity_writer_guard.py` and `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`.
- **Evidence to capture:** grouped guard violations by file, exact real external writer functions, architecture test output, and post-fix green guard/test outputs.
- **Five Whys (or equivalent):**
  1. Why is acceptance blocked? Because the mandatory guard stack is red.
  2. Why is the continuity guard red? Because it conflates any token reference with a continuity write.
  3. Why is that insufficient now? Because the architecture moved to one semantic owner / one continuity owner, while the guard still reasons at raw-line token level.
  4. Why is this more than a stale guard? Because a smaller set of real external writers still exists outside the allowed continuity-owner paths.
  5. Why must this be fixed before acceptance? Because acceptance evidence on a red continuity-owner guard would hide architecture debt instead of closing it.
- **Root cause statement:** the continuity-owner governance layer is split in two ways: the guard is overly broad and therefore noisy, and a bounded set of real continuity writes still lives outside the allowed owner paths.
- **Fix mechanism:** tighten the guard to detect real context/state writes only, then remove or reroute the real external continuity writes through the canonical writer surface.

## Reuse-first plan (mandatory)
- **Internal reuse:** `DialogStateService`, existing pending-resume helpers in `state_service.py`, existing architecture tests, existing guard script skeleton.
- **External reuse:** Python stdlib `ast`; no new dependency.
- **Why not reinvent the wheel:** the stdlib already provides the exact parse tree we need for assignment-target inspection.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2000
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** this block changes architecture/process guard code plus a bounded set of real runtime writers.

## Invariant
- Do not weaken the single continuity-writer goal by broadening allowlists to active runtime writers.
- Do not reopen legacy semantic substrate.
- Do not run acceptance until the continuity guard and architecture packet guard are green again.

## Scope
- refine `continuity_writer_guard.py` to detect real writes, not read/trace/meta lines
- remove or reroute the bounded real external continuity writes through canonical owner paths
- sync architecture tests and canon pointers to the true active block

## Out of scope
- new booking/info/handoff product logic
- open-world proof expansion
- guarded acceptance replay itself

## Touch-list
- `scripts/continuity_writer_guard.py`
- `scripts/proof_path_guard.py`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_proof_blackbox_guards.py`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-continuity-writer-guard-and-owner-reset-a922.md`

## Plan (1..N)
1. Make the guard AST-aware enough to separate real continuity writes from read/trace/meta plumbing.
2. Confirm the remaining real violations after the guard refinement.
3. Remove or reroute the bounded real external continuity writes through canonical writer surfaces.
4. Sync architecture tests and canon docs to the true active block.
5. Re-run the mandatory guard stack; only then reopen acceptance.

## DoD
- `python3 scripts/continuity_writer_guard.py` is green
- bounded real external continuity-writer files are either cleaned up or routed through allowed writer surfaces
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` is green
- canon docs point to this block truthfully
- next honest move is Phase E acceptance replay, not another guard-repair loop

## Checks
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- updated guard/test outputs
- grouped before/after continuity-writer violations
- doc/report/state sync for the blocker and fix

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0 expensive quality runs in this block
- **Fail-fast / scenario lock:** deterministic guard/test loop only
- **Stop condition:** if guard refinement still leaves a broad uncontrolled violation set after bounded writer reroutes, stop and publish the remaining real writers instead of widening scope
- **Escalation path:** Brain / Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** local deterministic architecture-governance fix only; no rollout change
- **Go/no-go signals:** continuity guard green, architecture tests green, session check green
- **Rollback:** revert the guard/runtime files if the refined guard becomes weaker or writer reroute changes behavior
- **Post-release monitoring window:** immediate deterministic recheck only

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `Drift closeout rule`:
  - acceptance remains blocked until these docs and the guard/test evidence agree

## Rollback
Revert the guard/runtime/doc changes from this block; acceptance TP remains the follow-up once the continuity block is green.

## No-go
- do not silence the guard by blanket allowlisting active runtime files
- do not run acceptance in this block
- do not introduce new regex/phrase branching in runtime code

## Risks/Blockers
- `handover_owner_service.py` may still carry real pending-resume writes that require a slightly wider continuity owner extraction than expected
- `reasoning_core.py` may still own a bounded pending-resume reason write despite the shim collapse

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: demo-salon acceptance replay remains open; generic-pack minimum-data-contract debt remains open.
- `Why not in this block`: both are downstream of the continuity-owner guard gate.
- `Risk if deferred`: acceptance can look green locally while architecture governance stays red.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-policy-core-acceptance-replay-a922.md`
- `Expiry/trigger to stop deferral`: immediately after the guard stack goes green.

## Next-block contract (mandatory)
- `Next block objective`: reopen and run the guarded Phase E acceptance replay on the green continuity-owner guard stack.
- `First deterministic check command`: `python3 scripts/continuity_writer_guard.py`
- `Blocked-by conditions`: any remaining real external continuity writer or stale canon/session guard mismatch
- `Owner role for closure`: Brain / Top Architect

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `python3 scripts/continuity_writer_guard.py`
- `Do not touch`: semantic-owner runtime files outside the bounded writer set
- `Open risks`: real external writers may remain in `handover_owner_service.py` / `reasoning_core.py` even after guard refinement
- `First command to verify`: `git status --short --branch`
