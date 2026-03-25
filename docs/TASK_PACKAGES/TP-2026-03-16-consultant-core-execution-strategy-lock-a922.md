# TP-2026-03-16-consultant-core-execution-strategy-lock-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-EXECUTION-STRATEGY-LOCK-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SEMANTIC-BRIDGE-GROWTH-GUARD-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-semantic-bridge-growth-guard-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Зафиксировать лучший corrective plan как обязательную machine-readable execution strategy, чтобы новый агент даже при тонком контексте стартовал с правильного порядка действий: no seam farming, no bridge-growth-as-progress, richer semantic owner cutover first, then single continuity writer, boundary owner, black-box proof, multi-pack acceptance, and only then retirement of legacy semantic authority. Эта стратегия должна быть зашита в `docs/SOURCE_OF_TRUTH.yaml`, surfaced in generated `AGENT_PACKET`, and repeated in `docs/SESSION_START_PROMPT.txt` so follow-up sessions read the same rules before any implementation.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-semantic-bridge-growth-guard-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/build_agent_packet.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `scripts/build_agent_packet.py`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `Baseline commands`:
  - `sed -n '1,160p' docs/SOURCE_OF_TRUTH.yaml`
  - `sed -n '1,120p' docs/ACTIVE_PROGRAM.md`
  - `sed -n '1,120p' docs/SESSION_START_PROMPT.txt`
  - `sed -n '1,220p' scripts/build_agent_packet.py`
- `FACT findings`:
  - the repo now has a hard guard against further hotspot bridge growth, but it still does not surface the approved corrective strategy as a first-class machine-readable instruction for future agents.
  - `AGENT_PACKET` currently explains current owners/blockers, but not the mandatory order of future work or the explicit rule that bridge growth does not count as progress.
  - `docs/SESSION_START_PROMPT.txt` still tells agents how to start a session, but not the locked corrective strategy they must prefer when context is thin.
- `Detected drift (docs vs code)`: the corrective plan exists in reasoning and conversation, but not yet as a durable startup contract in the generated packet and session-start canon.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org 3.12 json dumps sort_keys documentation`
- **Date/time (local):** `2026-03-16 22:40 +0500`
- **Why this query is precise:** this block updates the generated agent packet JSON and needs one deterministic serialization reference so packet snapshots remain stable for regression checks and future agents consume a canonical machine-readable artifact.
- **Sources opened (from this query):**
  - `json — JSON encoder and decoder — Python 3.12 documentation` — `https://docs.python.org/3.12/library/json.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `json.dumps(..., sort_keys=True)` is the standard deterministic JSON serialization mechanism for stable regression-friendly packet generation.
- **Decision:** `reuse + integrate` — keep packet generation in `scripts/build_agent_packet.py` and extend it with an explicit execution-strategy section, preserving deterministic JSON output.
- **Rejected options:**
  - introducing a second packet generator or ad-hoc narrative-only strategy doc
  - relying only on session logs for future-agent guidance
  - leaving strategy as tribal knowledge outside the generated packet
- **Open questions:** none for this bounded governance block.

## Root cause (mandatory)
- **Symptom:** even with the new growth guard, a future agent with thin context could still read the repo and not see the approved corrective sequence as an explicit startup contract.
- **Minimal reproduction:**
  1. Read the current generated `docs/_generated/AGENT_PACKET.md`.
  2. Observe that it lists owners, blockers, and allowed touch, but not the locked execution strategy or the rule that bridge growth is not valid progress.
  3. Start from `docs/SESSION_START_PROMPT.txt`; observe that it contains process guidance but not the corrective architectural sequence.
- **Evidence to capture:**
  - `docs/SOURCE_OF_TRUTH.yaml` contains an explicit execution-strategy section
  - generated packet surfaces this section in both JSON and markdown
  - architecture tests confirm the packet includes the strategy lock
  - session start prompt tells future agents to read and follow the execution strategy lock
- **Five Whys (or equivalent):**
  1. Why could future agents still drift after the new guard? Because they might know what not to do, but not the exact approved order of what to do next.
  2. Why is that dangerous? Because thin-context sessions tend to choose the easiest local path unless the next correct path is explicit.
  3. Why isn’t the current packet enough? Because it exposes state and blockers, but not the locked corrective strategy as a first-class section.
  4. Why isn’t session ritual enough? Because process guidance without strategy guidance still leaves room for local optimization around the wrong target.
  5. Why fix this now? Because the value of the new growth guard is highest when paired with a durable statement of the preferred path forward.
- **Root cause statement:** the repo lacked a machine-readable and startup-visible encoding of the approved corrective execution strategy, so future agents could still optimize locally without seeing the mandatory architectural sequence and progress-credit rule.
- **Fix mechanism:**
  - add an explicit execution-strategy section to `docs/SOURCE_OF_TRUTH.yaml`
  - surface it in generated `AGENT_PACKET`
  - repeat it in `docs/SESSION_START_PROMPT.txt`
  - validate it through architecture tests and packet generation checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `docs/SOURCE_OF_TRUTH.yaml` as the machine-readable canon root
  - existing `scripts/build_agent_packet.py` as the generated packet path
  - existing `docs/SESSION_START_PROMPT.txt` as session bootstrap contract
- **External reuse:**
  - Python `json.dumps(..., sort_keys=True)` from the standard library
- **Why not reinvent the wheel:** the repo already has one canonical strategy carrier (`SOURCE_OF_TRUTH`) and one generated agent bootstrap artifact (`AGENT_PACKET`); this block only needs to encode the missing strategy layer there.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `mixed`
- **Override token:** `none`
- **Why this profile fits:** governance-heavy block with one generator update, one startup-prompt update, focused architecture tests, and required canon/session sync.

## Invariant
- No runtime behavior change.
- No frozen legacy router edit.
- The corrective strategy becomes part of startup truth, not only session discussion.
- Generated packet remains deterministic.

## Scope
- Add explicit execution-strategy section to `docs/SOURCE_OF_TRUTH.yaml`.
- Surface that strategy in `scripts/build_agent_packet.py` outputs.
- Add/extend architecture tests for the new packet content.
- Update `docs/SESSION_START_PROMPT.txt` to point future agents to the strategy lock.
- Sync canon/session artifacts.

## Out of scope
- richer semantic owner cutover itself
- continuity cutover itself
- proof-path rewrite
- multi-pack acceptance implementation
- editing frozen router files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSION_START_PROMPT.txt`
- `scripts/build_agent_packet.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Encode the corrective execution strategy in `docs/SOURCE_OF_TRUTH.yaml`.
3. Surface the strategy in generated packet JSON/markdown and add packet test coverage.
4. Update session start prompt to direct future agents to the strategy lock.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `docs/SOURCE_OF_TRUTH.yaml` contains a machine-readable execution strategy lock
- generated `AGENT_PACKET` includes an explicit execution strategy section
- `docs/SESSION_START_PROMPT.txt` points future agents to that strategy lock before implementation
- architecture tests and packet checks are green

## Checks
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- machine-readable execution strategy in `docs/SOURCE_OF_TRUTH.yaml`
- generated packet JSON/markdown containing the strategy lock
- session-start prompt updated to point at the strategy
- green architecture/session gates

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** architecture checks only
- **Stop condition:** if implementing the strategy lock requires runtime behavior edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** governance-only, packet-generation-only
- **Go/no-go signals:** packet test + architecture suite + packet check + arch guard + session check green
- **Rollback:** revert strategy-lock doc/generator/prompt/test changes only
- **Post-release monitoring window:** next block must be a richer semantic owner cutover under the strategy lock

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the execution-strategy lock block and its packet output.

## Rollback
1. Revert the new execution-strategy section, packet generator changes, startup-prompt changes, and test updates.
2. Regenerate agent packet.
3. Re-run architecture/session gates to confirm the previous packet shape is restored.

## No-go
- no new semantic bridge family
- no runtime semantic routing change
- no frozen-router edit
- no replacing machine-readable strategy with narrative-only prose

## Risks / blockers
- if the strategy text is too vague, future agents will still optimize locally; this block must stay concrete and ordered.
- if packet generation is not updated together with source-of-truth, drift appears immediately.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - the strategy is locked, but the richer semantic owner cutover is still not implemented yet
  - continuity is still not a single writer
  - proof-path is still not fully black-box
- **Why not in this block:**
  - this block is only about making the approved path durable and startup-visible, not executing the next runtime cutover itself
- **Risk if deferred:**
  - future agents may avoid the forbidden shortcut but still choose the wrong next block because the preferred path is not explicit enough
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-richer-semantic-owner-cutover-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral when the next active block is a real owner-replacement cutover in `turn_planner`

## Next-block contract (mandatory)
- **Next block objective:** take one richer semantic owner slice out of legacy runtime via `truffles-api/app/core/turn_planner.py`, with explicit progress credit only if an old authority seam becomes deleted or unreachable
- **First deterministic check command:** `python3 scripts/build_agent_packet.py --check`
- **Blocked-by conditions:** inability to express the cutover through `PolicyDecision`, need for a new hotspot bridge family, or lack of deletion/unreachability target for the chosen seam
- **Owner role for closure:** `Top Architect`
