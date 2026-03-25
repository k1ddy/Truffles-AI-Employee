# TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-FAMILY-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish the stop-the-line targeted frozen-waiver decision for the surviving acceptance-preflight `L2` booking handover-reuse seam. This block must prove that truthful progress is now blocked by exact frozen `booking.py` caller sites, record why the unwaived runtime attempt cannot be counted as admissible progress, and lock the narrowest allowed future waiver scope.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/brief.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/trace_bundle.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/brief.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/responses.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/trace_bundle.jsonl`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
obj = rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']
print(obj['turn_text'])
print(obj['decision_meta']['error'])
PY`
  - `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/booking.py`
  - `python3 - <<'PY'
import json
from pathlib import Path
run_dir = Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r18')
summary = json.loads((run_dir/'summary.json').read_text())
print(summary['infra_valid'])
print(summary['semantic_valid'])
print(summary['stop_reason'])
PY`
- `FACT findings`:
  - the surviving live runtime blocker after non-frozen A/B/C closure is still the frozen `booking.py` handover-reuse family: `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl` row `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a` records `turn_text="Хотелось бы перенести на следующий понедельник."` and `decision_meta.error="_reuse_active_handover() missing 1 required keyword-only argument: 'hooks'"`.
  - the truthful owner contract already exists at `truffles-api/app/services/handover_owner_service.py:1092`, while the remaining stale callers are still all frozen in `truffles-api/app/routers/webhook/booking.py:1702`, `truffles-api/app/routers/webhook/booking.py:2358`, `truffles-api/app/routers/webhook/booking.py:2914`, `truffles-api/app/routers/webhook/booking.py:3007`, and `truffles-api/app/routers/webhook/booking.py:3741`.
  - the attempted local runtime fix required executable additions inside frozen `truffles-api/app/routers/webhook/booking.py`, and `python3 scripts/legacy_freeze_guard.py` fail-closed with: `truffles-api/app/routers/webhook/booking.py: executable additions in frozen file without waiver -> from app.services.handover_owner_service import ActiveHandoverReuseRuntimeHooks; hooks=ActiveHandoverReuseRuntimeHooks(...)`.
  - the attempted fresh dev probe `/tmp/booking_quality/l2-acceptance-preflight-a922-r18` is non-canonical partial evidence only: `infra_valid=true`, `semantic_valid=false`, `stop_reason=signal_15`, `run_integrity_reasons=['run_completion_gap']`, `responses_rows=41`, `trace_rows=41`, and `dialogs_seen=[1, 2, 3]`.
  - the executed `r18` prefix shows only prefix relief, not closure proof: `error_rows=0`, `LLM-QUAL-l2-acceptance-preflight-a922-r18-002-02-27b1e5` resolved as `action=escalate`, `intent=reschedule`, `error=None`, and `LLM-QUAL-l2-acceptance-preflight-a922-r18-001-14-a3eadb` / `...-002-14-ec54c2` / `...-003-13-176966` resolved as `intent=human_request`, `error=None`.
  - the invalid frozen runtime attempt has now been reverted, `python3 scripts/legacy_freeze_guard.py` is back to `OK`, and the repo has returned to a truthful stopped state with no active frozen-file runtime patch.
- `Detected drift (docs vs code)`:
  - the family package correctly localized the blocker to frozen `booking.py`, but its implementation next-move implicitly assumed frozen editing would be canonically available; current repo truth disproved that assumption because `legacy_freeze_guard.py` blocked the exact required change.
  - leaving canon on the family package after the failed unwaived attempt would overstate admissible progress by implying `implement_acceptance_preflight_l2_frozen_booking_handover_reuse_family_closure_bundle` is still directly allowed.

## One web search (mandatory before implementation)
- **Query (exact):** `python keyword-only arguments official docs`
- **Date/time (local):** `2026-03-19T10:24:00+05:00`
- **Sources opened (from this query):**
  - `https://docs.python.org/3/reference/compound_stmts.html#function-definitions`
  - `https://docs.python.org/3/glossary.html#term-parameter`
- **Source quality:**
  - high-signal / primary source: official Python documentation
- **Reuse rule for this block:**
  - reused from the parent frozen-family package; no second query is allowed or needed for this stop-line decision block
- **Existing solutions found:**
  - keyword-only parameters must be passed explicitly by callers
  - widening the signature or hiding the mismatch behind a compatibility helper is the wrong fix shape
- **Decision:** `reuse/integrate`
  - keep the owner contract truthful, keep the required future runtime fix narrow, and move the question from implementation feasibility to frozen-waiver admissibility
- **Rejected options:**
  - a second web search: rejected by the block rule and unnecessary
  - a compatibility bridge/helper: rejected because it preserves the mixed authority seam instead of deleting it

## Root cause (mandatory)
- **Symptom:** the surviving frozen booking handover-reuse family can likely be fixed technically, but the only known truthful fix path currently requires editing a frozen file, so the last runtime attempt stopped at governance rather than producing admissible architecture progress.
- **Minimal reproduction:**
  1. Inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl` row `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a` and confirm the live blocker is the missing keyword-only `hooks` argument.
  2. Inspect `truffles-api/app/services/handover_owner_service.py` and `truffles-api/app/routers/webhook/booking.py` and confirm the owner contract already requires `hooks` while the five frozen callers still do not pass it.
  3. Review the guard-failure evidence from the reverted attempt: `legacy_freeze_guard.py` fail-closed on executable additions in frozen `booking.py`.
  4. Review `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/{summary.json,manual_audit.md,responses.jsonl}` and confirm the probe is partial/non-canonical, so it cannot be used as closure evidence.
- **Evidence to capture:**
  - exact `r17` failing row
  - exact five frozen callsites
  - exact `legacy_freeze_guard.py` failure text from the reverted attempt
  - exact `r18` partial-audit snapshot proving prefix relief only
- **Five Whys (or equivalent):**
  1. Why is the package still blocked? Because the surviving live blocker now sits only in frozen `booking.py`.
  2. Why can't the previous implementation be counted? Because it required executable additions in a frozen file without an approved waiver, and the freeze gate rejected it.
  3. Why doesn't the `r18` partial probe close the question? Because it stopped non-canonically with `signal_15` and `run_completion_gap`, so it proves only executed-prefix behavior, not full seam deletion.
  4. Why not keep the old family package as the active block? Because it still points to a direct implementation move that repo governance has now disproved as non-canonical without a waiver decision.
  5. Why is a targeted frozen-waiver decision now the honest next move? Because the owner contract is already known, the runtime scope is already narrowed to five exact frozen callsites, and the only remaining blocker is governance over that exact frozen edit surface.
- **Root cause statement:** the surviving acceptance-preflight `L2` blocker is no longer an architectural unknown; it is a governance-bound frozen caller family in `booking.py`. The previous runtime attempt showed likely technical feasibility, but because that path required executable edits in a frozen file without waiver, the block cannot be counted as admissible progress and canon must switch to an explicit targeted frozen-waiver decision.
- **Fix mechanism:**
  - publish the targeted frozen-waiver decision as the active canon block
  - lock the exact future frozen scope to the five `booking.py` callsites plus bounded supporting regressions
  - reject any broader frozen expansion, wrapper/helper growth, or rerun-only progress

## FACT vs INFERENCE verdict
- **FACT:** the old non-frozen A/B/C seams are already dead; the surviving blocker is frozen `booking.py` caller drift only.
- **FACT:** the attempted runtime patch likely improved the executed prefix but cannot be counted because it violated the freeze gate.
- **FACT:** after revert, no frozen runtime fix is currently live in the repo.
- **INFERENCE:** a narrow targeted frozen waiver is now the only honest path to further architecture progress on this family.
- **Decision:** switch canon from the frozen-family package TP to one targeted frozen-waiver decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/handover_owner_service.py`
  - the frozen-family package TP and its `r17` evidence
  - the reverted attempt's guard failure plus partial `r18` evidence
  - the existing targeted frozen-waiver decision pattern from `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
- **External reuse:**
  - official Python documentation for keyword-only parameters
- **Why not reinvent the wheel:**
  - no new owner design is needed; only the exact frozen governance decision is still missing

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `acceptance-preflight-frozen-booking-targeted-waiver-decision`
- **Why this profile fits:** this is a governance/decision block that reverts an invalid runtime attempt, updates canon, and locks the exact next move without touching runtime code.

## Invariant
- no runtime code edits in this block
- no claim that the frozen booking seam is already dead
- no claim that `r18` is closure evidence
- no transport / billing / observer / non-frozen A/B/C reopening
- no new wrapper/helper or signature widening counted as progress

## Scope
- prove that the package is now blocked by exact frozen `booking.py` authority
- record why the unwaived runtime attempt is invalid progress
- lock the narrowest future waiver scope
- switch canon/session/packet to the waiver-decision block

## Out of scope
- runtime implementation
- edits to frozen files in this block
- acceptance closure claims
- new `L2` reruns
- broader booking redesign or handover owner redesign

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Revert the invalid frozen runtime attempt so the repo returns to a truthful stopped state.
2. Publish this targeted frozen-waiver decision TP with the exact guard failure, `r17` blocker row, and partial `r18` evidence.
3. Switch canon so the active block is this waiver decision rather than the stale direct-implementation package.
4. Regenerate packet and rerun governance/session checks.

## Exact future waiver scope
- `truffles-api/app/routers/webhook/booking.py`
  - the `_reuse_active_handover(...)` caller at `:1702` for booking interrupt reschedule reuse
  - the `_reuse_active_handover(...)` caller at `:2358` for booking interrupt info-escalation reuse
  - the `_reuse_active_handover(...)` caller at `:2914` for same-day booking escalation reuse
  - the `_reuse_active_handover(...)` caller at `:3007` for active-booking human-request reuse
  - the `_reuse_active_handover(...)` caller at `:3741` for booking-commit reuse
- bounded supporting tests only:
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_booking_chaos_dialogs.py`
- **Not in waiver scope:**
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/response.py`
  - any transport / billing / observer / oracle code

## DoD
- the targeted frozen-waiver decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md`
- canon/packet/test all agree that this decision block is now active
- the exact future waiver scope is machine-readable in canon/session artifacts
- the next move is no longer the stale unwaived implementation bundle
- required checks are green

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
obj = rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']
print(obj['turn_text'])
print(obj['decision_meta']['error'])
PY`
- `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/booking.py`
- `python3 - <<'PY'
import json
from pathlib import Path
run_dir = Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r18')
summary = json.loads((run_dir/'summary.json').read_text())
print(summary['infra_valid'])
print(summary['semantic_valid'])
print(summary['stop_reason'])
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
- updated TP, canon, packet, session, state, and structure
- exact `r17` blocker row proving the frozen seam remains live without waiver
- exact `legacy_freeze_guard.py` failure text from the reverted attempt
- exact `r18` partial-audit snapshot proving only prefix relief
- green governance/session checks after reverting the invalid runtime patch

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max fresh non-acceptance `L2` runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the future waiver scope expands beyond the exact five `booking.py` callsites plus bounded regressions, stop and publish `GAP` instead of widening silently
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only stop-line decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree that the active block is now the waiver decision and the repo is back to a truthful stopped state
- **Rollback:** revert the decision TP and matching canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next runtime block must stay strictly inside the exact future waiver scope listed above

## Rollback
1. Revert this decision TP and the matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime edits hidden inside this decision block
- no claim that `r18` proves closure
- no direct return to the stale unwaived implementation move
- no blanket frozen waiver broader than the exact scope above
- no wrapper/helper counted as seam deletion

## Risks / blockers
- the future waived implementation may surface a second frozen booking residual after the runtime exception is cleared; that must stop and publish a narrower `GAP` instead of broadening scope silently
- if the future fix needs another frozen file besides `booking.py`, this decision no longer covers it
- acceptance remains blocked until one future waived implementation plus a fresh canonical rerun prove semantic green

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - the frozen booking handover-reuse seam remains live
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial overall
  - final multi-pack acceptance closure remains open
- **Why not in this block:**
  - this block is only the waiver decision and stop-line sync; it does not execute frozen runtime code
- **Risk if deferred:**
  - the team may either restart fake rerun churn or count another unwaived frozen patch as progress
- **Linked follow-up Task Package(s):**
  - future exact-scope implementation block unlocked by this decision
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - before any next frozen booking runtime implementation starts
  - immediately if anyone proposes broader frozen scope or rerun-only progress

## Next-block contract (mandatory)
- **Next block objective:** implement the exact targeted frozen waiver for the five `booking.py` handover-reuse callers and rerun one fresh non-acceptance `L2` only after the bounded regressions pass
- **First deterministic check command:** `rg -n "_reuse_active_handover\(" truffles-api/app/routers/webhook/booking.py`
- **Blocked-by conditions:** if the fix requires frozen files beyond `booking.py`, a new wrapper/helper, owner-signature widening, or another fresh `L2` before the bounded regressions pass, stop and publish `GAP`
- **Owner role for closure:** `Top Architect`
