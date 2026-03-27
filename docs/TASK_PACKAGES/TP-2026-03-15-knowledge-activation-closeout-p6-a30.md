# TP-2026-03-15-knowledge-activation-closeout-p6-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-CLOSEOUT-P6-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-CANARY-P5-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-ACTIVATION-CANARY-P5-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-DONE-A30`

## Название/цель
Закрыть программу knowledge release model не narrative-обещанием, а одним tenant-level closeout artifact: объединить P5 release/canary signals и branch-specific preview/live invariants в один machine-readable verdict, чтобы post-deploy go/no-go не зависел от ручного чтения health, metrics, SQL и owner preview отдельно.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-canary-p5-a30.md`
- `CA_ID`: `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `ops/knowledge_activation_closeout.py`
  - `truffles-api/tests/test_knowledge_activation_closeout.py`
  - `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `TECH.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `FACT findings`:
  - P5 proves deploy path correctness (`restart_release.sh` + release guard), but final operator decision still requires separate manual inspection of tenant branch state.
  - The program now has all runtime pieces (`active_version_id`, `knowledge_activation_jobs`, preview/live split), yet no single post-deploy artifact verifies them together for one real client/branch.
  - Without that combined artifact, final closeout can still regress into “health looks fine” while tenant preview/live semantics are wrong.

## One web search (mandatory before implementation)
- **Query (exact):** `Google SRE Workbook canarying releases synthetic monitoring`
- **Date/time (local):** `2026-03-15 18:56 +05`
- **Sources opened (from this query):** `https://sre.google/workbook/canarying-releases/`
- **Found options:** canary decisions should be based on explicit evaluation integrated into release automation, and rollout value comes from comparing live/control signals with minimal user impact.
- **Decision:** `reuse/integrate` — keep P5 release guard as the control-plane signal source and add one tenant-specific closeout artifact on top instead of inventing a separate closeout workflow.
- **Rejected options:** manual SQL checklist only; screenshot-only proof; a second custom release command unrelated to `restart_release.sh`.
- **Source quality:** high-signal primary source = Google SRE Workbook.

## Root cause (mandatory)
- **Symptom:** P5 makes deploy safer, but final release-model closure still depends on humans mentally merging two different truths: service health and tenant preview/live correctness.
- **Minimal reproduction:** after deploy, run the P5 guard and read health/metrics; then separately inspect branch knowledge state or owner preview. There is no single artifact that says whether one tenant actually satisfies the release-model contract.
- **Evidence:** `scripts/restart_release.sh`, `truffles-api/scripts/knowledge_activation_release_guard.py`, `truffles-api/app/services/console_consultant_verification.py`, `truffles-api/app/services/knowledge_registry_service.py`, `STATE.md`.
- **Five Whys (or equivalent):**
  1. Why is P5 not enough for final closure? Because it validates control-plane health, not tenant-specific product invariants.
  2. Why do tenant-specific invariants matter? Because the original defect mixed preview availability with live activation semantics for a branch.
  3. Why can operators still miss that? Because preview/live status currently lives in different surfaces and code paths.
  4. Why is manual comparison unsafe? Because go/no-go becomes subjective and inconsistent under pressure.
  5. Why is this architectural and not just ops polish? Because the whole program exists to prove the release model contract, not only process health.
- **Root cause statement:** the program lacks one machine-readable closeout artifact that evaluates tenant-level preview/live invariants together with the new activation transport health.
- **Fix mechanism:** add a closeout CLI that reuses the P5 release guard, snapshots one client/branch activation state from DB truth, derives preview/live invariants, and emits a single `go|no_go` verdict with reasons.

## Reuse-first plan (mandatory)
- **Internal reuse:** `truffles-api/scripts/knowledge_activation_release_guard.py`, existing Postgres/docker shell patterns in `ops/console_owner_admin_kpi_snapshot.py`, release runbook from P5, branch/job/version tables introduced in P1-P4.
- **External reuse:** Google SRE canary evaluation guidance.
- **Why not reinvent the wheel:** the control-plane guard already exists; the missing part is one tenant snapshot + contract evaluation layer.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `20`
- **Code dominance:** `ops/closeout automation`
- **Override token:** `none`
- **Why this profile fits:** bounded automation script + deterministic tests + runbook/canon sync, no runtime architecture changes.

## Invariant
- Do not mutate knowledge versions, activation jobs, or branch pointers just to collect closeout evidence.
- Do not add a second deploy path outside `restart_release.sh` + P5 guard.
- P0-P5 runtime semantics must remain unchanged.

## Scope
- Add one tenant-level closeout CLI/artifact on top of P5 guard.
- Evaluate preview/live release-model invariants from branch/version/job DB truth.
- Document the final post-deploy closeout command in the runbook.

## Out of scope
- Real production rollout execution in this block.
- New UI surfaces.
- Synthetic publish/retry mutations for evidence generation.

## Touch-list
- `ops/knowledge_activation_closeout.py`
- `truffles-api/tests/test_knowledge_activation_closeout.py`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`

## Plan
1. Add a tenant-level closeout CLI that reuses P5 release guard signals and snapshots branch/version/job truth from Postgres.
2. Encode release-model invariants (`preview still available`, `live pointer not switched early`, `candidate/active consistency`) into one `go|no_go` artifact.
3. Cover the decision logic with deterministic tests.
4. Extend the release runbook and sync canon/session docs.

## DoD
- One command writes a JSON closeout artifact for `client_slug + branch_slug`.
- Artifact combines P5 guard output with tenant preview/live invariants and explicit reasons.
- Deterministic tests cover both `go` and `no_go` failure families.
- Runbook shows exact post-deploy closeout command and how to read it.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_knowledge_activation_closeout.py tests/test_knowledge_activation_release_guard.py tests/test_restart_release_scripts.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && python3 -m py_compile ops/knowledge_activation_closeout.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** one combined closeout artifact will remove the remaining subjective/manual step from the knowledge activation release decision.
- **Expected measurable effect:** operators can collect one JSON file with both control-plane and tenant contract status instead of stitching health + SQL + owner preview by hand.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one green deterministic test pass, one green py_compile, and one green session gate.

## Evidence
- Diff for new closeout CLI and tests.
- JSON artifact schema/fields documented in runbook.
- Deterministic test output.
- Session/state update pointing to final closeout command.

## Rollback
- Revert the closeout CLI/runbook/canon changes; P5 release guard remains the latest valid automation layer.

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive post-deploy evidence only; no runtime mutation.
- **Go/no-go signals:** P5 guard `decision=go` plus tenant-level invariants `preview_available`, `can_verify_now`, and `active/published/job` consistency.
- **Post-release monitoring window:** same as P5; closeout artifact is captured immediately after deploy and again after the first activation settles.
- **Rollback:** if closeout artifact is `no_go`, stop rollout progression and use the existing P5 rollback path.

## No-go
- Do not invent another deploy path.
- Do not write a script that auto-publishes or auto-rolls back tenant knowledge just to create evidence.
- Do not mark the program closed on P5 health alone.

## Risks/Blockers
- Closeout artifact depends on the target environment exposing both P5 guard endpoints and Postgres/docker access.
- Tenant config may disable consultant verification rollout; that must be reported as a real blocker, not silently ignored.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Actual production closeout execution remains an operational step after this automation lands.

### Why not in this block
- This block builds the closeout artifact and proof contract; running it against production is a separate rollout action, not a code change.

### Risk if deferred
- The program can still be locally green while the final production closeout artifact has not yet been captured.

### Linked follow-up Task Package(s)
- `none if closeout artifact is captured on rollout`; otherwise open a rollout-evidence follow-up from the first blocking reason.

### Expiry/trigger to stop deferral
- Do not call the program done until one real closeout artifact exists for the rollout target.

## Next-block contract (mandatory)
### Next block objective
- Capture one real closeout artifact on the rollout target and make the explicit `go|no_go` decision.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && python3 ops/knowledge_activation_closeout.py --help`

### Blocked-by conditions
- P6 closeout CLI and runbook must land first.

### Owner role for closure
- `Top Architect | Brain`
