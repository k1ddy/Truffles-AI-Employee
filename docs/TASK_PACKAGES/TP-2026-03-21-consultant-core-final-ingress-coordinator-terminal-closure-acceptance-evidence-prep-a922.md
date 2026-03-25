# TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-EVIDENCE-PREP-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BROADER-RESIDUAL-FAMILY-BUNDLE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-bundle-a922.md`
- `UNLOCKS`: `implement_consultant_core_final_ingress_coordinator_terminal_closure_acceptance_evidence_bundle`

## Название/цель
Переключить active program с runtime demolition на acceptance-evidence prep после доказанной main-path closure. Зафиксировать текущий blocker как proof/oracle-first family, синхронизировать canon и запретить новые runtime-патчи без явного доказательства reusable contract bug.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-bundle-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: `docs/ACTIVE_PROGRAM.md`, `docs/SOURCE_OF_TRUTH.yaml`, `STATE.md`, `STRUCTURE.md`, `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`, `docs/SESSION_INDEX.md`, `docs/_generated/AGENT_PACKET.*`
- `Baseline commands`:
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `python3 - <<'PY' ... /tmp/booking_quality/a922-weekend-slot-constraint-dev-r79 ... PY`
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/semantic_bridge_growth_guard.py`
  - `python3 scripts/continuity_writer_guard.py`
  - `python3 scripts/legacy_freeze_guard.py`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
  - `SESSION_AGENT=a922 scripts/session_check.sh`
- `FACT findings`:
  - main `/webhook` runtime closure is already proved locally: `reasoning_core` no longer calls `decision_router._handle_webhook_payload(...)` on the main path, and the surviving unresolved lane exits through explicit non-frozen handoff ownership.
  - recent quality inventory shows no canonical guarded acceptance baseline; the latest surfaced run is `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79` and it is still semantic-red.
  - the surfaced first-fail turn is `LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4`: user asks `Есть ли у вас акции на маникюр?`, while runtime answers `Понял, в субботу по услуге «Маникюр». Подскажите, пожалуйста, точное время.` and fails `expected_info_section_miss`, `info_section_miss`, `judge_fail`.
- `Detected drift (docs vs code)`: `ACTIVE_PROGRAM` / `SOURCE_OF_TRUTH` still point at the landed runtime bundle as the active block even though repo truth now says the next admissible move is acceptance-evidence preparation.

## One web search (mandatory before implementation)
- **Query (exact):** `pytest parametrize ids official docs`
- **Date/time (local):** `2026-03-21T21:12:14+05:00`
- **Why this query is precise:** the follow-up evidence block may need one small deterministic regression row family to keep acceptance-failure cases stable and attributable without inventing a new runner. The query is limited to official pytest guidance on stable parametrized ids.
- **Sources opened (from this query):**
  - `pytest documentation — How to parametrize fixtures and test functions` — `https://docs.pytest.org/en/stable/how-to/parametrize.html`
  - `pytest documentation — Parametrizing tests` — `https://docs.pytest.org/en/stable/example/parametrize.html`
- **Existing solutions found:** official pytest already provides stable `ids=` / `pytest.param(..., id=...)` for bounded regression families, so any follow-up deterministic coverage can stay inside existing suites.
- **Decision:** `reuse` — keep all acceptance-prep and later evidence work inside the existing guarded wrapper / diagnose / pytest owners; no new acceptance harness or ad-hoc replay wrapper is justified.
- **Rejected options:**
  - new acceptance wrapper: rejected because `scripts/llm_quality_guarded.sh` and `ops/diagnose.py` already own the lane
  - narrative-only blocker summary: rejected because the next block still needs machine-checkable commands and follow-up contract hooks
- **Open questions:** none for this doc-only prep block

## Root cause (mandatory)
- **Symptom:** main-path runtime closure is done, but final consultant-core closure is still blocked because there is no canonical acceptance baseline to extend into the required multi-pack matrix/open-world proof lane.
- **Minimal reproduction:**
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `python3 - <<'PY'
import json, pathlib
base = pathlib.Path('/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79')
summary = json.loads((base / 'summary.json').read_text())
rows = [json.loads(line) for line in (base / 'responses.jsonl').read_text().splitlines()]
msg_id = 'LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4'
row = next(item for item in rows if item.get('message_id') == msg_id)
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'run_integrity_reasons': (summary.get('quality_status') or {}).get('run_integrity_reasons'),
    'stop_reason': summary.get('stop_reason'),
    'top_failures': [f.get('reason') for f in (summary.get('top_failures') or [])[:3]],
    'turn_text': row.get('turn_text'),
    'outbox_text': row.get('outbox_text'),
})
PY`
- **Evidence to capture:** `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/{summary.json,responses.jsonl}`, `docs/ACTIVE_PROGRAM.md`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- **Five Whys (or equivalent):**
  1. Why is the program still open after the terminal ingress cut? Because runtime closure alone is not the final acceptance claim.
  2. Why can the team not just keep deleting runtime seams? Because the main path is already closed, and new demolition work would be symptom-chasing unless a reusable contract bug is first proved.
  3. Why is there still no truthful final closure? Because the canary acceptance lane has no canonical fresh baseline to reuse or extend into matrix/open-world evidence.
  4. Why is the latest surfaced blocker not automatically a runtime bug? Because the current failure sits in the proof lane (`info_section_miss` / `judge_fail` on a dev run) and could be runtime, oracle, or pack/readiness only after bounded classification.
  5. Why does this prep block matter? Because without an explicit evidence-prep contract, the team will drift back into runtime micro-fixes or non-canonical reruns.
- **Root cause statement:** the remaining blocker is no longer live runtime authority; it is acceptance-evidence orchestration and failure-family classification after runtime closure, with the latest surfaced family still unresolved in the proof lane.
- **Fix mechanism:** publish one doc-only prep block that freezes runtime closure as done, classifies the current blocker as proof/oracle-first until disproved, binds the next move to one bounded acceptance-evidence bundle, and updates canon/agent packet accordingly.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
  - `scripts/quality_artifact_report.py`
  - `scripts/llm_quality_guarded.sh`
  - `ops/diagnose.py`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- **External reuse:** official pytest parametrization docs only, for stable row ids if a later bounded regression slice is required.
- **Why not reinvent the wheel:** acceptance ownership already exists in the guarded wrapper, matrix, closure validator, and existing docs/canon surfaces. This block only binds them to the new post-closure program state.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `30`
- **Code dominance:** `off`
- **Override token:** `none`
- **Why this profile fits:** runtime closure is already proved and the current task is governance/evidence preparation only. Any new code would be premature until the next evidence block classifies the surfaced family.

## Invariant
- do not reopen runtime demolition without proving a reusable core contract bug first
- do not weaken acceptance gates or reuse non-canonical dev runs as closure evidence
- do not claim beauty-only or runtime-only closure as final program acceptance
- frozen files stay untouched

## Scope
- publish one acceptance-evidence prep TP and one matching report artifact
- switch canon from the landed runtime bundle to the acceptance-prep block
- lock the next block to evidence-only canary re-entry and multi-pack closure preparation
- sync `STATE`, `ACTIVE_PROGRAM`, `SOURCE_OF_TRUTH`, session metadata, and generated agent packet

## Out of scope
- any runtime/core/proof implementation change
- any guarded `lock/replay/canary/full` execution in this block
- any new matrix or open-world closure run
- any frozen-file waiver or acceptance-gate relaxation

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
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
1. Freeze the latest acceptance facts from the runtime-closed worktree and latest dev-run artifacts.
2. Publish the doc-only acceptance-evidence prep TP/report with explicit blocker classification and next-block contract.
3. Switch `ACTIVE_PROGRAM`, `SOURCE_OF_TRUTH`, `STATE`, `STRUCTURE`, and session metadata to the new active block.
4. Regenerate the agent packet and rerun the required deterministic guards.

## DoD
- one new prep TP exists and is the active block in canon
- one matching report exists and records the latest acceptance-evidence facts without claiming closure
- `ACTIVE_PROGRAM`, `SOURCE_OF_TRUTH`, `STATE`, and session metadata all agree that runtime closure is done and the next move is acceptance evidence only
- generated agent packet and deterministic guards are green

## Checks
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `python3 - <<'PY'
import json, pathlib
base = pathlib.Path('/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79')
summary = json.loads((base / 'summary.json').read_text())
rows = [json.loads(line) for line in (base / 'responses.jsonl').read_text().splitlines()]
msg_id = 'LLM-QUAL-a922-weekend-slot-constraint-dev-r79-001-07-dee8f4'
row = next(item for item in rows if item.get('message_id') == msg_id)
print({
    'run_id': summary.get('run_id'),
    'infra_valid': summary.get('infra_valid'),
    'semantic_valid': summary.get('semantic_valid'),
    'run_integrity_reasons': (summary.get('quality_status') or {}).get('run_integrity_reasons'),
    'stop_reason': summary.get('stop_reason'),
    'top_failures': [f.get('reason') for f in (summary.get('top_failures') or [])[:3]],
    'turn_text': row.get('turn_text'),
    'outbox_text': row.get('outbox_text'),
})
PY`
- `rg -n "active_block_tp|current_block|current_nonnegotiable_next_move|multi_pack_acceptance_on_beauty_clinic_or_dental_generic_service" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md`
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
- new TP: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- new report: `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- latest blocker artifacts reused from `/tmp/booking_quality/a922-weekend-slot-constraint-dev-r79/{summary.json,responses.jsonl}`
- synced canon: `docs/ACTIVE_PROGRAM.md`, `docs/SOURCE_OF_TRUTH.yaml`, `STATE.md`, `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`, `docs/SESSION_INDEX.md`, `docs/_generated/AGENT_PACKET.md`, `docs/_generated/AGENT_PACKET.json`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** only cheap inventory/extraction and doc/guard checks are allowed in this prep block
- **Stop condition:** if the prep block requires runtime changes or expensive reruns to stay truthful, stop and split a new implementation TP instead
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** `n/a` — doc-only canon sync
- **Go/no-go signals:** `n/a`
- **Rollback:** revert the doc/canon sync files and rebuild the agent packet
- **Post-release monitoring window:** immediate doc-sync verification only

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - all of the above must be updated in the same block; otherwise the block ends `BLOCKED`

## Rollback
- revert the doc-only prep files, rerun packet/architecture guards, and restore the prior active block pointer.

## No-go
- do not run expensive acceptance suites in this prep block
- do not patch runtime because of the latest dev failure unless a new implementation TP first proves rightful ownership
- do not weaken `judge`, `semantic_valid`, `run_integrity`, matrix, or open-world gates
- do not touch frozen `decision.py`, `booking.py`, or `pending.py`

## Risks/Blockers
- the next evidence block may prove the surfaced family is a reusable runtime bug, which would require a new implementation TP rather than direct code in the evidence lane
- the next canary re-entry may surface a different blocker family once `r79` is displaced
- stale docs could mislead later agents back into runtime demolition if canon is not switched now

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: final canary/matrix/open-world evidence is still missing; live pilot/readiness work is still outside this program; older acceptance blocker reports remain historical context but no longer define the active block
- `Why not in this block`: this block is governance/evidence prep only; it intentionally does not implement or rerun the acceptance lane
- `Risk if deferred`: agents can resume runtime micro-fixes even though the main path is already closed, and final closure will keep drifting without one active evidence contract
- `Linked follow-up Task Package(s)`: `implement_consultant_core_final_ingress_coordinator_terminal_closure_acceptance_evidence_bundle` plus `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `Expiry/trigger to stop deferral`: stop deferral immediately if anyone proposes another runtime demolition slice before the acceptance lane is re-entered or before the surfaced family is classified under the five-class rule

## Next-block contract (mandatory)
- `Next block objective`: implement one bounded acceptance-evidence bundle that starts with truthful `demo_salon/main` canary re-entry and only escalates into matrix/open-world closure after the surfaced blocker family is classified
- `First deterministic check command`: `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
- `Blocked-by conditions`: no canonical canary baseline exists; latest surfaced family remains unclassified; any proposed fix requires runtime changes without a new implementation TP
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md`
- `Do not touch`: `truffles-api/app/services/reasoning_core.py`, frozen webhook routers, acceptance thresholds
- `Open risks`: `latest dev failure may still be runtime-owned`, `final multi-pack closure evidence does not exist yet`
- `First command to verify`: `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
