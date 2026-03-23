# TP-2026-03-16-consultant-verification-tenant-acceptance-p17-a30

- Title/Goal: Close the remaining consultant-verification acceptance gap with one deterministic tenant-level diagnostic tool: reuse the real overview/session/message service path, emit a machine-readable `go|no_go` artifact, and keep the focus strictly on `Проверка консультанта`, not generic livecheck families.
- Branch: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- Worktree path: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- Base ref: `main`
- Merge policy: merge commit only; no rebase
- Cleanup: Brain / Top Architect remove branch + worktree after merge

## Canon refs
- `STATE.md` NOW: the architectural release-model correction is merged and `workspace_enabled` diagnostics are in place, but the last in-scope closure step is still tenant-specific acceptance for `Проверка консультанта`.
- `docs/CONSOLE_GUIDE.md`
- `truffles-api/app/services/console_consultant_verification.py`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-verification-acceptance-diagnostics-p16-a30.md`
- CA_ID: none

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org argparse mutually exclusive group official docs`
- **Date/time (local):** `2026-03-16 19:05 Asia/Almaty`
- Sources opened (from this query):
  - Python docs, `argparse` reference: `https://docs.python.org/3/library/argparse.html`
- High-signal source: official Python docs
- Found solutions:
  - keep CLI mode strict with explicit flags instead of ad-hoc positional parsing
  - use argparse choices/defaults for deterministic operator contracts
- Decision: `reuse`
- Reason: this block adds one narrow operational CLI for tenant acceptance; standard-library `argparse` is sufficient and already matches existing repo patterns.
- Rejected options:
  - new wrapper dependency or custom flag parser
  - hiding the acceptance logic behind manual browser-only steps with no artifact

## Reuse-first plan (mandatory)
- Internal reuse:
  - `build_consultant_verification_overview`
  - `create_consultant_verification_session`
  - `append_consultant_verification_message`
  - `ConsoleConsultantVerificationSessionCreateRequest`
  - `ConsoleAuthContext`
- External reuse:
  - Python stdlib `argparse` guidance from the official docs above
- Why not reinvent the wheel:
  - the real consultant-verification service path already exists; this block only wraps it in a deterministic tenant acceptance diagnostic artifact.

## Root cause (mandatory)
- Symptom:
  - after the architectural fix and P16 contract cleanup, the remaining product question is still operationally awkward: for a concrete tenant/branch we do not yet have one deterministic artifact that says why `Проверка консультанта` is usable or blocked.
- Minimal reproduction:
  - today the team has to combine the overview payload, UI inspection, and an ad-hoc session/message attempt manually to answer “can this tenant actually use the tab?”
- Evidence:
  - `truffles-api/app/services/console_consultant_verification.py`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `docs/TASK_PACKAGES/TP-2026-03-16-consultant-verification-acceptance-diagnostics-p16-a30.md`
- Five Whys:
  1. Why is closure still incomplete after P16? Because we clarified the contract but did not yet give operators one deterministic tenant-level proof path.
  2. Why does that matter? Because the remaining failures are no longer architectural; they are tenant/config/branch/source/session readiness questions.
  3. Why is manual checking weak here? Because it mixes UI observation with ad-hoc API probing and makes RCA noisy.
  4. Why not just rely on the browser? Because we need a machine-readable artifact that can be attached to closure evidence and compared across tenants.
  5. Why should this reuse the real service path? Because a fake diagnostic path would drift from the actual owner experience and would not close the acceptance question honestly.
- Root cause statement:
  - the remaining gap is not product architecture anymore; it is missing tenant-level acceptance evidence for the real consultant-verification path.
- Fix mechanism:
  - add one tenant acceptance CLI that reuses the real overview/session/message service path, emits a structured `go|no_go` snapshot, and makes exact blocker families explicit without reintroducing ops jargon into the owner UI.

## Invariant
- Do not reintroduce `sync` / live activation as a preview gate.
- Do not merge workspace access and team tools back into one gate.
- Do not touch generic `livecheck-auto` / `CA03-CA06` families in this block.

## Scope
- One operational tenant-acceptance CLI for consultant verification.
- Deterministic tests for its `go|no_go` snapshot logic.
- Canon/session/docs updates for this closure block.

## Out of scope
- webhook semantic-runtime work in `decision.py` / `trace.py`
- generic CI/livecheck families
- new frontend features
- removal of legacy `feature_enabled` alias

## Touch-list
- `ops/consultant_verification_acceptance.py`
- `truffles-api/tests/test_consultant_verification_acceptance.py`
- `docs/CONSOLE_GUIDE.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Add a tenant-level consultant-verification acceptance CLI that reuses the real overview/session/message path via the running API container.
2. Emit a deterministic `go|no_go` JSON artifact with exact overview/session blocker families.
3. Cover the snapshot logic with narrow deterministic tests.
4. Sync canon/session docs and run the new CLI once on the canary tenant for evidence.

## DoD
- There is one command that tells us deterministically whether a target tenant can use `Проверка консультанта`.
- The artifact separates:
  - overview blockers
  - workspace/team-tools evidence
  - session/message probe result
- Team-tools rollout remains evidence-only and does not block tenant acceptance by itself.
- The block stays scoped to consultant verification and does not mutate generic livecheck/runtime families.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && pytest -q truffles-api/tests/test_consultant_verification_acceptance.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && ruff check ops/consultant_verification_acceptance.py truffles-api/tests/test_consultant_verification_acceptance.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && python3 -m py_compile ops/consultant_verification_acceptance.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- Hypothesis:
  - a dedicated tenant acceptance artifact will close the remaining consultant-verification ambiguity without touching product runtime semantics.
- Expected measurable effect:
  - we can diagnose `workspace_disabled` / `branch_required` / `preview_source_missing` / session-probe failure from one JSON artifact.
- Max full runs: `1 targeted pytest batch + 1 canary tenant acceptance run`
- Max targeted reruns per failure family: `1`
- Stop condition:
  - stop once the new CLI produces one valid canary artifact and deterministic tests are green.

## Evidence
- new acceptance CLI
- targeted unit tests
- one canary tenant JSON artifact
- updated canon/session docs

## Rollback
- Revert the narrow acceptance CLI commit; no schema or data rollback required.

## Release safety (mandatory for non-doc changes)
- Strategy:
  - read-mostly operational tooling; the only runtime mutation is an optional consultant-verification session/message probe that uses the existing safe-simulation path.
- Go/no-go signals:
  - CLI tests green
  - one canary tenant run returns a machine-readable artifact
- Rollback:
  - revert the CLI if it produces misleading acceptance results or mutates the wrong path
- Post-release monitoring window:
  - first two operator runs on real tenants after merge

## No-go
- No changes to generic webhook semantics
- No new UI gating logic in this block
- No fake acceptance path detached from the real consultant-verification services

## Risks/blockers
- Local P15 webhook/livecheck edits remain out-of-scope and must stay out of this block.
- The running `truffles-api` container must be available for the canary acceptance probe.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Acceptance still uses an operator CLI, not an always-on product UI evidence panel.
- `feature_enabled` still remains as a compatibility alias in the public response.

### Why not in this block
- This block closes tenant acceptance first; UI evidence history and alias cleanup are separate follow-ups.

### Risk if deferred
- Operators can still rely on ad-hoc manual checks if they ignore the new CLI.

### Linked follow-up Task Package(s)
- follow-up block to deprecate/remove `feature_enabled`
- possible later block to surface tenant acceptance evidence inside Ops UI

### Expiry/trigger to stop deferral
- if two more tenant investigations happen without using the artifact, acceptance evidence must move closer to the default ops path.

## Next-block contract (mandatory)
### Next block objective
- Run the tenant acceptance CLI on the actual target client/branch and close the original consultant-verification task with concrete runtime evidence.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && pytest -q truffles-api/tests/test_consultant_verification_acceptance.py`

### Blocked-by conditions
- missing or unhealthy `truffles-api` container on the rollout host

### Owner role for closure
- Brain / Top Architect
