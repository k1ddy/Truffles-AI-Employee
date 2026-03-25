# TP-2026-03-22 — Consultant Core Debug Cadence Reset And Shadow-Def Guard A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEBUG-CADENCE-RESET-AND-SHADOW-DEF-GUARD-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `UNLOCKS`: `IMPLEMENT-CONSULTANT-CORE-DEMO-SALON-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-FAMILY-UNDER-FAMILY-FIRST-CADENCE`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Reset the consultant-core residual-debug cadence so the team stops doing turn-by-turn canon churn, and add a structural guard against new shadowed top-level core defs. This block must keep acceptance strict while making forensic discovery cheaper and more explicit.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `scripts/llm_quality_guarded.sh`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted docs/code/tests`:
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `scripts/llm_quality_guarded.sh`
  - `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import ast
from pathlib import Path
path = Path('truffles-api/app/services/reasoning_core.py')
mod = ast.parse(path.read_text())
by_name = {}
for node in mod.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        by_name.setdefault(node.name, []).append(node.lineno)
duplicates = {name: lines for name, lines in by_name.items() if len(lines) > 1}
print({'lines': sum(1 for _ in path.open()), 'top_level_defs': len([n for n in mod.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]), 'unique_names': len(by_name), 'duplicate_names': len(duplicates)})
for name, lines in sorted(duplicates.items()):
    print(name, lines)
PY`
  - `wc -l AGENTS.md docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `nl -ba AGENTS.md | sed -n '111,240p;316,344p'`
  - `nl -ba docs/SESSION_START_PROMPT.txt | sed -n '45,120p'`
  - `nl -ba scripts/llm_quality_guarded.sh | sed -n '298,345p'`
- `FACT findings`:
  - `truffles-api/app/services/reasoning_core.py` is `15345` lines long, contains `147` top-level function defs with only `110` unique names, and currently exposes `37` duplicate top-level names that can shadow earlier runtime authority.
  - The live duplicate set includes active owner-cutover surfaces such as `_try_handle_turn_planner_safe_booking_verification_owner_cutover`, `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover`, `_try_handle_turn_planner_safe_booking_prompt_owner_cutover`, and `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover`.
  - The current session/process ritual requires early full TP formalization and one-issue flow (`AGENTS.md:111`, `AGENTS.md:148`, `docs/SESSION_START_PROMPT.txt:45-57`), while the expensive replay tooling blocks repeated diagnostic attempts on pending/non-canonical artifacts (`scripts/llm_quality_guarded.sh:298-343`).
  - The runbook already distinguishes `dev/forensic` from `acceptance`, but the operative instructions still make residual debugging too serial and too administrative.
- `INFERENCE to verify in this block`:
  - the next leverage gain is not another micro runtime fix first; it is a cadence reset plus a structural guard that blocks new shadowed defs while preserving the current turn-11 runtime blocker as the next implementation family.

## One web search (mandatory before implementation)
- **Query (exact):** `Python ast module FunctionDef AsyncFunctionDef official documentation docs.python.org`
- **Date/time (local):** `2026-03-22T10:35:00+05:00`
- **Sources opened (from this query):**
  - `https://docs.python.org/pt-br/3.13/library/ast.html`
- **Source quality:** official Python documentation / primary source.
- **Existing solutions found:** Python exposes `ast.FunctionDef` and `ast.AsyncFunctionDef`, which is sufficient to build a deterministic top-level duplicate-def guard without importing runtime code.
- **Decision:** `reuse/integrate`
  - reuse Python AST for a zero-runtime-side-effect architecture test
  - integrate the existing `dev/forensic` quality lane instead of inventing another runner
  - build only the thin wrapper/documentation changes needed to make that lane practical
- **Rejected options:**
  - building a custom parser
  - weakening acceptance gates
  - continuing turn-by-turn TP churn without a family-level mode

## Root cause (mandatory)
- **Symptom:** residual consultant-core work has become expensive, serial, and low-leverage; after each truthful replay the team opens another narrow blocker without first reducing process friction or addressing obvious structural hazards in the owner hotspot.
- **Minimal reproduction:**
  1. compare the current active canary decision block and session ritual in `docs/ACTIVE_PROGRAM.md`, `AGENTS.md`, and `docs/SESSION_START_PROMPT.txt`
  2. inspect `scripts/llm_quality_guarded.sh` and observe that repeated/pending forensic attempts are blocked unless the operator manually overrides multiple gates
  3. AST-parse `truffles-api/app/services/reasoning_core.py` and confirm that shadowed top-level duplicate defs exist in live owner-cutover paths
- **Evidence:**
  - `AGENTS.md:111-165`
  - `AGENTS.md:183-218`
  - `AGENTS.md:316-344`
  - `docs/SESSION_START_PROMPT.txt:45-57`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:16-29`
  - `scripts/llm_quality_guarded.sh:298-343`
  - `truffles-api/app/services/reasoning_core.py`
- **Five Whys:**
  1. Why does work feel endless? Because each replay is used as both discovery and closure, so only the first surviving blocker gets surfaced.
  2. Why does that become expensive? Because every surfaced blocker gets a new bounded doc/canon cycle before family boundaries are stabilized.
  3. Why is debugging itself unreliable? Because `reasoning_core.py` contains shadowed top-level defs, so humans and agents can read or patch dead code.
  4. Why was this not already prevented? Because there is no architecture guard for duplicate top-level core defs, and the existing `dev/forensic` lane is under-documented and ergonomically weak.
  5. Why does this block need to be meta-level? Because fixing turn `11` without resetting cadence and blocking new shadowed defs would preserve the same low-leverage operating mode.
- **Root cause statement:** the system currently over-serializes residual debugging at the process layer and under-protects the runtime hotspot at the structure layer; the combination makes each surviving blocker expensive to classify and risky to patch.
- **Fix mechanism:** codify family-first `forensic -> implementation -> closure` work modes in governance docs, make forensic continuation explicit in `scripts/llm_quality_guarded.sh` without weakening acceptance mode, and add an architecture test that records the current duplicate-def debt in `reasoning_core.py` and blocks any unreviewed growth.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `dev/forensic` lane in `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - existing `--manual-audit-gate` and `--forensic-sla-gate` support in `ops/diagnose.py`
  - existing architecture test suite under `truffles-api/tests/architecture`
- **External reuse:**
  - official Python `ast` documentation
- **Why not reinvent the wheel:**
  - the repo already has the runner, gates, and architecture-test location; the missing work is explicit cadence policy plus a thin ergonomic wrapper and a guard for current structural debt

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes governance docs, quality tooling, and architecture guards; it is not a turn-level runtime repair and it is not a closure replay
- `Family handled in this block`: `consultant-core residual debug cadence + shadowed core def guard`
- `Closure artifact expected from this mode`: green architecture/tooling checks plus synced canon, not a new canary replay

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `20`
- `Code dominance`: `light_runtime_tooling`
- `Override token`: `none`
- `Why this profile fits`:
  - the block is mostly governance/tooling/test work, but it intentionally changes executable guard/tooling surfaces and therefore is not `doc_only`

## Invariant
- do not weaken acceptance requirements or baseline integrity
- do not touch frozen webhook routers
- do not patch runtime semantics for turn `11` in this block
- do not add phrase-hardcoded logic to runtime-core
- keep `turn 11` as the next runtime family after this cadence reset

## Scope
- update governance docs to make work family-first instead of turn-first for residual debugging
- document and expose explicit `forensic` continuation in the guarded quality wrapper
- add an architecture test that locks the current duplicate-def debt and blocks unreviewed growth
- switch active canon/session artifacts to this meta-block

## Out of scope
- fixing `turn 11` runtime continuity
- deleting the existing duplicate defs from `reasoning_core.py`
- new acceptance replay
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`

## Touch-list
- `AGENTS.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/llm_quality_guarded.sh`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this meta-block TP/report and switch active canon from turn-level runtime decision to cadence-reset guard work.
2. Update governance docs (`AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`) to codify family-first `forensic -> implementation -> closure` work.
3. Extend `scripts/llm_quality_guarded.sh` with one explicit forensic override path that keeps acceptance strict but lowers discovery friction in dev lane.
4. Add an architecture test that records current duplicate top-level core defs in `reasoning_core.py` and blocks new growth.
5. Rebuild packet, rerun architecture/session checks, sync session/state artifacts, and copy repo `AGENTS.md` back to `/home/zhan/AGENTS.md` for canon sync.

## DoD
- governance docs explicitly distinguish `forensic`, `implementation`, and `closure` work for residual debugging
- `scripts/llm_quality_guarded.sh` exposes a documented forensic override path without weakening acceptance mode
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py` exists and passes, locking the current duplicate-def debt by explicit allowlist/counts
- active canon/session artifacts point to this meta-block
- `current_nonnegotiable_next_move` now sends the team back to the turn-11 runtime family under the new family-first cadence
- `/home/zhan/AGENTS.md` matches repo `AGENTS.md` again

## Checks
- `python3 - <<'PY'
import ast
from pathlib import Path
path = Path('truffles-api/app/services/reasoning_core.py')
mod = ast.parse(path.read_text())
by_name = {}
for node in mod.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        by_name.setdefault(node.name, []).append(node.lineno)
duplicates = {name: lines for name, lines in by_name.items() if len(lines) > 1}
print('duplicate_names', len(duplicates))
print('sample', list(sorted(duplicates.items()))[:5])
PY`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- updated `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, `scripts/llm_quality_guarded.sh`
- updated canon/session/packet artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: none; this block must not launch a new quality run
- `Stop condition`: if the guard/tooling change would weaken acceptance semantics, stop and publish that contradiction instead of merging it
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: tooling/test/governance only; no runtime rollout
- Go/no-go signals: architecture suite green, packet green, session check green, no frozen router edits
- Rollback: revert wrapper/test/doc changes and restore prior canon block
- Post-release monitoring window: next runtime family must use the new cadence and keep acceptance lane unchanged

## Rollback
1. Revert this TP/report and canon/session sync.
2. Restore the prior turn-11 runtime decision as the active block.
3. Revert the wrapper/test/doc changes and rerun packet + architecture checks.

## No-go
- do not weaken `acceptance` lane gates
- do not reclassify turn `11` in this block
- do not delete duplicate defs in `reasoning_core.py` without a separate runtime block
- do not introduce new direct `ops/diagnose.py llm-quality` acceptance entrypoints
- do not touch frozen routers

## Risks / blockers
- documenting a new cadence without a thin executable improvement would not change operator behavior; that is why the wrapper and architecture guard are in scope
- the duplicate-def test must not fail on current known debt, only on unreviewed growth or drift in the explicitly tracked set
- the next runtime family may still need a dedicated shadowed-def cleanup follow-up if it touches affected owner surfaces

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - turn `11` check-booking reference continuity remains the next runtime blocker
  - `reasoning_core.py` still contains the current known duplicate top-level defs; this block only locks the debt and prevents silent growth
  - session tooling still does not auto-generate work-mode metadata; this block documents the mode but does not enforce it through `session_start.sh`
- `Why not in this block:`
  - removing duplicate defs and fixing turn `11` are separate runtime-family changes and would mix process reset with live semantic repair
- `Risk if deferred:`
  - without this reset, the team falls back to turn-by-turn canon churn and risks patching shadowed code again
- `Linked follow-up Task Package(s):`
  - `implement_consultant_core_demo_salon_turn11_check_booking_reference_continuity_runtime_family_under_family_first_cadence`
  - `author_consultant_core_reasoning_core_shadowed_def_cleanup_family`
- `Expiry/trigger to stop deferral:`
  - stop deferral immediately if the next runtime family needs to touch any currently duplicated owner function name in `reasoning_core.py`

## Next-block contract (mandatory)
- `Next block objective:`
  - implement the turn-11 check-booking reference continuity family under the new family-first cadence, using forensic discovery only as needed and keeping closure replay separate
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`
- `Blocked-by conditions:`
  - any proposed fix that touches a currently duplicated owner function name without a shadowed-def cleanup decision
  - any attempt to use acceptance replay as discovery instead of closure
- `Owner role for closure:`
  - `Hands` implementation, `Brain/Top Architect` canon acceptance
