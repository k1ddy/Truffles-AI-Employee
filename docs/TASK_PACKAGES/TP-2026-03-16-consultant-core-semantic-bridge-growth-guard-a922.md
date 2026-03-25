# TP-2026-03-16-consultant-core-semantic-bridge-growth-guard-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SEMANTIC-BRIDGE-GROWTH-GUARD-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SERVICE-CHOICE-SPECIALIST-EXACT-TIME-FOLLOWUP-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-exact-time-followup-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Остановить системный drift в сторону новой keyword/phrase-driven архитектуры: ввести machine-enforced guard, который запрещает незаметный рост новых semantic bridge families в generic ingress hotspot files и заставляет любой новый semantic seam проходить через явный waiver, а не через бесконечное наращивание `detect_*`/`looks_like_*`/`reason=*` micro-bridges. Этот блок не добавляет новый business seam; он убирает сам стимул повторять плохой паттерн реализации.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-exact-time-followup-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `scripts/arch_guard.py`
- `scripts/legacy_freeze_guard.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/arch_guard.py`
  - `scripts/semantic_bridge_growth_guard.py`
  - `docs/SEMANTIC_BRIDGE_GUARD.yaml`
  - `truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `python3 - <<'PY' ... ast-collect tracked detector names from info_signal_service.py ... PY`
  - `python3 - <<'PY' ... ast-collect PolicyCoreRouteSnapshot reason literals from intent_routing.py ... PY`
  - `sed -n '1,120p' docs/SOURCE_OF_TRUTH.yaml`
- `FACT findings`:
  - the canon already forbids semantic hardcode and keyword routing in core, but there is no machine-enforced guard that blocks new bounded phrase-bridge families in generic ingress hotspots.
  - current active cutover status already lists a long chain of bounded overrides in `docs/ACTIVE_PROGRAM.md`; this is architectural evidence that micro-bridge growth can keep looking like progress unless explicitly constrained.
  - the hottest growth surfaces are `truffles-api/app/services/info_signal_service.py` and `truffles-api/app/core/intent_routing.py`, because they currently accumulate detector families and `PolicyCoreRouteSnapshot(reason=...)` branches.
- `Detected drift (docs vs code)`: canon forbids the pattern, but current enforcement only guards frozen legacy files, continuity writers, and proof-only semantic authority; there is no equivalent guard for new generic-core semantic bridge growth.

## One web search (mandatory before implementation)
- **Query (exact):** `Python 3 ast module documentation`
- **Date/time (local):** `2026-03-16 22:26 +0500`
- **Why this query is precise:** this block needs one deterministic way to inspect Python source structure without brittle line matching, so the guard can track function definitions and `PolicyCoreRouteSnapshot(reason=...)` literals structurally.
- **Sources opened (from this query):**
  - `ast — Abstract Syntax Trees — Python 3.12.10 documentation` — `https://docs.python.org/3.12/library/ast.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ast.parse(...)` and AST traversal are the standard built-in way to inspect function definitions and call keywords in Python source without regex-on-diff fragility.
- **Decision:** `reuse + integrate` — use Python AST parsing for a snapshot-based architecture guard instead of building another line-oriented diff heuristic.
- **Rejected options:**
  - using raw regex over source text as the primary guard mechanism
  - using diff-based executable-addition logic like `legacy_freeze_guard.py`, because this branch already contains accumulated bridge additions and a diff-only guard would fail before it can become the new baseline
  - deferring the fix until after more ingress bridge blocks
- **Open questions:** none for this bounded corrective block.

## Root cause (mandatory)
- **Symptom:** the migration kept making local progress by adding more bounded ingress semantic bridges, even though canon forbids phrase/keyword-driven semantic ownership in generic core.
- **Minimal reproduction:**
  1. Read `AGENTS.md` semantic-hardcode and no-shortcut rules.
  2. Read `docs/ACTIVE_PROGRAM.md` current blocker line that enumerates a long chain of bounded ingress overrides.
  3. Observe that the current guard suite does not fail on new bridge-family growth in `info_signal_service.py` or `intent_routing.py`.
- **Evidence to capture:**
  - a new architecture guard fails when a new tracked detector family is added to `info_signal_service.py` without an explicit waiver
  - the same guard fails when a new `PolicyCoreRouteSnapshot(reason=...)` bridge reason is added to `intent_routing.py` without an explicit waiver
  - `arch_guard.py` runs the new guard in the default architecture suite
  - current known hotspot inventory is snapshotted in machine-readable config
- **Five Whys (or equivalent):**
  1. Why could bad seams keep growing? Because there was no guard for semantic bridge growth in generic ingress hotspots.
  2. Why did the work naturally flow there? Because frozen legacy files were protected, while sidecar ingress seams remained writable and green under current checks.
  3. Why is that dangerous? Because it recreates split semantic ownership in a new place instead of deleting the old owner.
  4. Why didn’t existing canon stop it? Because the canon stated the rule, but machine enforcement covered only legacy freeze, continuity writers, and proof-path authority.
  5. Why fix this before the next cutover block? Because without the guard, the next easiest implementation path will keep repeating the same anti-pattern.
- **Root cause statement:** the system allowed a repeat of the old architecture pattern because there was no machine-enforced constraint preventing new semantic detector families and snapshot reasons from accumulating in generic ingress hotspot files, so bounded micro-bridges could keep masquerading as architectural progress.
- **Fix mechanism:**
  - add a snapshot-based AST guard for hotspot files
  - treat current tracked detector/reason inventory as the temporary baseline
  - fail architecture checks on any future unwaived growth in that inventory
  - wire the guard into `arch_guard.py` and architecture tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `scripts/legacy_freeze_guard.py` for CLI/config/test shape
  - `scripts/arch_guard.py` as the central architecture gate entrypoint
  - existing architecture test loading pattern in `truffles-api/tests/architecture/*`
- **External reuse:**
  - Python `ast` module from the standard library
- **Why not reinvent the wheel:** AST traversal already gives a deterministic structural view of Python code; this block only needs a thin policy layer over that primitive.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this block is a systemic architecture guard with one new script, one config, focused tests, and required canon/session sync.

## Invariant
- No new business/runtime seam is added in this block.
- No frozen legacy router file is edited.
- Current known hotspot inventory becomes the explicit baseline; future growth requires waiver, not silence.
- The guard must be structural, not line-fragile.

## Scope
- Add a machine-readable hotspot snapshot config.
- Add a new AST-based semantic bridge growth guard.
- Add focused architecture tests.
- Wire the new guard into `arch_guard.py`.
- Sync canon/session artifacts.

## Out of scope
- deleting existing bridge families in this block
- richer planner cutover itself
- continuity refactor
- proof-path refactor
- multi-pack acceptance work
- editing frozen router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-semantic-bridge-growth-guard-a922.md`
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Snapshot current hotspot inventory in a machine-readable config.
3. Implement an AST-based guard that checks hotspot inventory equality unless an explicit waiver is active.
4. Add focused architecture tests and wire the guard into `arch_guard.py`.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `scripts/semantic_bridge_growth_guard.py` fails on new tracked detector names in `info_signal_service.py` without waiver
- `scripts/semantic_bridge_growth_guard.py` fails on new `PolicyCoreRouteSnapshot(reason=...)` literals in `intent_routing.py` without waiver
- `scripts/arch_guard.py` runs the new guard by default
- focused architecture tests are green
- canon/session metadata truthfully marks this corrective block

## Checks
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- machine-readable hotspot inventory in `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- failing tests for unwaived bridge growth
- successful architecture suite and arch guard with the new guard wired in

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** architecture checks only
- **Stop condition:** if the guard needs to inspect runtime semantics beyond hotspot inventory, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** architecture-governance-only; no runtime behavior change
- **Go/no-go signals:** new guard tests + full architecture suite + arch guard + packet + session check green
- **Rollback:** revert the guard/config/test/doc changes only
- **Post-release monitoring window:** the next block must use this guard as the constraint before any richer semantic cutover continues

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match this corrective guard block, not the last specialist seam.

## Rollback
1. Revert `docs/SEMANTIC_BRIDGE_GUARD.yaml`, `scripts/semantic_bridge_growth_guard.py`, `scripts/arch_guard.py`, and the touched architecture tests/docs.
2. Regenerate agent packet.
3. Re-run architecture checks to confirm the repo returns to the previous guard set only.

## No-go
- no new semantic bridge family in `info_signal_service.py`
- no new `PolicyCoreRouteSnapshot(reason=...)` branch added in this block
- no frozen-router edits
- no pretending that this governance block itself is semantic cutover progress

## Risks / blockers
- the hotspot inventory is intentionally a snapshot of a bad-but-current state; if the list is inaccurate, the guard can fail until synchronized.
- this block constrains future implementation paths; that is intentional and should not be relaxed silently.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - existing bounded bridge families remain in place; this block only freezes their further growth
  - broader semantic ownership still remains in frozen `decision.py`
  - continuity is still not a single writer
- **Why not in this block:**
  - deleting existing bridges and replacing the broader owner requires a separate runtime cutover block, not a governance-only guard block
- **Risk if deferred:**
  - without the guard, the next easiest implementation path will keep growing the same anti-pattern
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-richer-semantic-owner-cutover-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next semantic cutover block can delete or bypass a broader owner seam instead of adding another hotspot family

## Next-block contract (mandatory)
- **Next block objective:** take one richer semantic owner slice out of the legacy runtime using `turn_planner`/new-core ownership, with this guard active so no new hotspot family can be added as a shortcut
- **First deterministic check command:** `python3 scripts/semantic_bridge_growth_guard.py`
- **Blocked-by conditions:** need for new hotspot allowlist growth, frozen-router semantic growth, or inability to express the cutover through new-core contracts
- **Owner role for closure:** `Top Architect`
