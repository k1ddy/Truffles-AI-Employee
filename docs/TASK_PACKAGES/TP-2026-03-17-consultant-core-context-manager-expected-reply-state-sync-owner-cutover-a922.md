# TP-2026-03-17-consultant-core-context-manager-expected-reply-state-sync-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTEXT-MANAGER-EXPECTED-REPLY-STATE-SYNC-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RICHER-CONTINUITY-COLLAPSE-AUDIT-POST-BOOKING-PROMPT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-RESTORE-BLOCKER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Схлопнуть следующий non-frozen continuity writer seam: вынести live expected-reply/question-contract state sync из `truffles-api/app/routers/webhook/context_manager.py` в `truffles-api/app/core/dialog_state_service.py`, чтобы `context_manager` стал thin wrapper вокруг persistence/trace/meta side effects. Блок должен удалить authority по canonical dialog-state sync, session-memory interaction-state sync, re-entry clear и question bookkeeping orchestration из router helper family без правок frozen `pending.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-richer-continuity-collapse-audit-after-booking-prompt-owner-family-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "_set_expected_reply_context|_sync_canonical_dialog_state|_sync_session_memory_interaction_state" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/core/dialog_state_service.py`
  - `sed -n '228,560p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '2330,2715p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '1,220p' truffles-api/app/routers/webhook/session_memory.py`
- `FACT findings`:
  - `context_manager._set_expected_reply_context(...)` still normalizes expected-reply fields, syncs canonical dialog state, syncs `session_memory.interaction_state`, clears re-entry, and updates question bookkeeping as one live continuity writer outside `DialogStateService`
  - `DialogStateService` already owns the typed primitives used by that flow (`project_expected_reply_projections`, `sync_canonical_question_contract_state`, `sync_session_memory_interaction_state`, `set_context_manager_payload`, `clear_context_re_entry_required`, `update_session_memory_on_question`), so the seam can be cut by reuse instead of another bridge
  - `context_manager._sync_canonical_dialog_state(...)` is also still imported through frozen `decision.py`, so the cut must preserve compatibility and make that helper a thin delegate instead of deleting the public router symbol
  - `docs/LEGACY_SUNSET.yaml` continuity guard currently allows added continuity writes only in router files; moving this writer into `DialogStateService` will require an explicit guard-authority update for `truffles-api/app/core/dialog_state_service.py`
- `Detected drift (docs vs code)`:
  - active canon still points to the audit block, but the next locked move is now an implementation block on `context_manager`/`DialogStateService`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python dataclasses module documentation`
- **Date/time (local):** `2026-03-17 20:18 +0500`
- **Why this query is precise:** this block needs a small typed transfer object between the new continuity owner and the router wrapper, and the standard-library contract matters more than inventing another ad-hoc tuple/dict protocol.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python 3 documentation` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python standard-library documentation.
- **Existing solutions found:** `@dataclass` is the standard-library way to define lightweight structured records with generated init/repr semantics, which fits an internal owner->wrapper handoff object better than another untyped tuple.
- **Decision:** `reuse/integrate` — use a stdlib dataclass for the internal expected-reply state-sync result instead of inventing a new runtime protocol or widening router-owned mutable state.
- **Rejected options:**
  - returning another position-dependent tuple from `DialogStateService`
  - introducing a new pydantic contract for a purely internal handoff object
  - keeping the multi-step state sync in `context_manager.py` and only renaming helpers
- **Open questions:** whether message metadata/trace persistence can stay entirely in the wrapper while the new dataclass owns all state-shaping outputs.

## Root cause (mandatory)
- **Symptom:** the continuity audit already proved `context_manager._set_expected_reply_context(...)` is the richest non-frozen writer seam, but the live orchestration still sits in router code and keeps multiple continuity writes outside the target owner.
- **Minimal reproduction:**
  1. Run `rg -n "_set_expected_reply_context|_sync_canonical_dialog_state|_sync_session_memory_interaction_state" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/core/dialog_state_service.py`.
  2. Inspect `truffles-api/app/routers/webhook/context_manager.py` and observe that `_set_expected_reply_context(...)` still performs expected-reply normalization, canonical question-contract sync, session-memory interaction-state sync, re-entry clearing, and session-memory question bookkeeping inline.
  3. Inspect `truffles-api/app/core/dialog_state_service.py` and confirm the typed normalization/setter primitives for the same payloads already exist there.
  4. Confirm frozen `decision.py` still imports `_sync_canonical_dialog_state(...)`, so compatibility requires a delegate rather than a removed symbol.
- **Evidence to capture:**
  - the router helper becomes thin and no longer authors the continuity state-shaping flow inline
  - `DialogStateService` becomes the added continuity owner path for this family
  - frozen `decision.py` stays untouched while inheriting the new owner via the router delegate
  - continuity guard is updated to treat `DialogStateService` as an allowed writer for the guarded tokens
- **Five Whys (or equivalent):**
  1. Why is the continuity seam still live? Because `_set_expected_reply_context(...)` still authors several payload mutations in router code.
  2. Why wasn’t it already deleted when session-memory bridges moved? Because that earlier work only extracted primitives; the orchestration remained local.
  3. Why can this seam be cut now? Because the audit narrowed the target to a non-frozen helper family with existing typed service primitives.
  4. Why can’t we just delete the router helper? Because frozen `decision.py` still calls `_sync_canonical_dialog_state(...)` through the legacy surface.
  5. Why must the cut move into `DialogStateService` instead of another wrapper? Because progress is deletion of writer authority, not another bridge that leaves the router as the semantic continuity source.
- **Root cause statement:** the repo already has the typed continuity primitives, but the last rich expected-reply/question-contract orchestration still lives in `context_manager.py`, so the router remains the live writer authority even though the intended owner already exists.
- **Fix mechanism:**
  - add a typed service-level helper that performs expected-reply state sync and returns a structured result
  - move canonical dialog-state shaping into `DialogStateService`
  - reduce router helpers to compatibility delegates plus persistence/trace/meta side effects
  - update contract tests and continuity guard so the new owner path is explicit and protected

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_expected_reply_projections(...)`
  - `DialogStateService.set_expected_reply_context_fields(...)`
  - `DialogStateService.sync_canonical_question_contract_state(...)`
  - `DialogStateService.sync_session_memory_interaction_state(...)`
  - `DialogStateService.set_context_manager_payload(...)`
  - `DialogStateService.clear_context_re_entry_required(...)`
  - `DialogStateService.update_session_memory_on_question(...)`
- **External reuse:**
  - Python stdlib `dataclasses`
- **Why not reinvent the wheel:** the block is valid only if the existing typed continuity owner absorbs the orchestration; creating another router-local contract would preserve the old authority shape.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** this block changes continuity ownership, test coverage, guards, and canon in one bounded cut.

## Invariant
- No edits to frozen `truffles-api/app/routers/webhook/decision.py`, `booking.py`, or `pending.py`.
- No new generic ingress/phrase bridge families.
- Trace/message metadata behavior must remain compatible for existing callers of `_set_expected_reply_context(...)`.
- Deterministic boundary semantics must not replace LLM semantic ownership.

## Scope
- Move `_sync_canonical_dialog_state(...)` state-shaping authority into `DialogStateService` behind a compatibility delegate.
- Move `_set_expected_reply_context(...)` continuity state orchestration into `DialogStateService` behind a typed result object.
- Update continuity guard/canon to recognize `DialogStateService` as the allowed writer for this family.
- Add focused service/runtime regression tests.

## Out of scope
- edits to frozen `pending.py`
- pending-resume snapshot/restore cutover
- broader context-manager carryover families unrelated to expected-reply/question-contract sync
- local-first realism contour closure for the whole program
- boundary or proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this implementation TP with RCA and one exact web search.
2. Add the new typed `DialogStateService` helper(s) for canonical expected-reply state sync and router handoff.
3. Reduce `context_manager._sync_canonical_dialog_state(...)` and `_set_expected_reply_context(...)` to thin delegates plus persistence/trace/meta side effects.
4. Add focused `DialogStateService` tests and run targeted runtime regressions that exercise pending/resume and question-contract paths.
5. Update guard/canon/session artifacts and regenerate `AGENT_PACKET`.
6. Run deterministic checks and session gate.

## DoD
- `DialogStateService` owns the expected-reply/question-contract state-shaping flow for this bounded family
- `context_manager._sync_canonical_dialog_state(...)` is a compatibility delegate, not the live authority
- `context_manager._set_expected_reply_context(...)` only persists context and records traces/message metadata around the service result
- frozen `decision.py` remains untouched and still works through the delegate surface
- new focused tests prove canonical state sync, session-memory sync, and re-entry clear behavior via the service owner
- continuity guard, packet, and canon are green

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'transport_degraded_pending_reentry_restores_booking_resume or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary'`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- new TP and updated canon/session artifacts
- code diff showing router delegate thinning and new service owner helper
- focused test evidence from `test_dialog_state_service.py` and targeted `test_message_endpoint.py`
- green guard + packet + session check results

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic targeted regressions only for this block
- **Stop condition:** if the cut requires frozen-file edits or if the router cannot be reduced below persistence/trace/meta side effects, stop and escalate instead of adding another bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local worktree cutover only; no rollout outside deterministic verification in this block
- **Go/no-go signals:** focused tests, architecture checks, packet regeneration, and continuity guard green
- **Rollback:** revert the service/helper changes and restore previous canon/guard config
- **Post-release monitoring window:** next block must choose a fresh continuity seam rather than reopening this helper family

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Drift closeout rule`:
  - active canon may point to this block only if the service owns the bounded state sync, the router wrapper is thin, and frozen `pending.py` remains explicitly residual debt rather than silently absorbed.

## Rollback
1. Revert `DialogStateService`, `context_manager`, test, and canon changes from this block.
2. Restore `docs/LEGACY_SUNSET.yaml` continuity guard to the previous allowed-writer set.
3. Regenerate the packet and rerun the deterministic checks.

## No-go
- no frozen-file edits
- no router-local replacement object that keeps state authority outside `DialogStateService`
- no weakening of continuity guard or architecture checks without explicit canon change in the same block
- no claim that this closes pending-resume restore

## Risks / blockers
- `_set_expected_reply_context(...)` still has persistence and trace side effects, so the cut must avoid changing observable trace/meta ordering in existing flows
- continuity guard will fail if `DialogStateService` becomes the writer without an explicit allowed-writer update
- frozen `pending.py` remains the next tempting seam and could be confused with being solved by this block even though it is not

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `pending.py` still owns direct pending-resume snapshot/restore authority
  - `context_manager.py` will still keep persistence/trace/message-metadata wrapper side effects for the expected-reply family
  - broader continuity writer families outside expected-reply/question-contract remain fragmented
- **Why not in this block:**
  - this block is bounded to one continuity writer deletion without touching frozen files or unrelated carryover families
- **Risk if deferred:**
  - future work may overclaim continuity convergence or reopen router authority through convenience edits
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-context-manager-expected-reply-state-sync-owner-cutover-a922.md`
- **Expiry/trigger to stop deferral:**
  - before claiming single continuity writer convergence or before taking `pending.py` as the next block without an explicit freeze decision

## Next-block contract (mandatory)
- **Next block objective:** `pending_resume_restore_blocker_audit_after_context_manager_expected_reply_state_sync_owner_cutover`
- **First deterministic check command:** `rg -n "_build_pending_resume_snapshot|_restore_pending_resume|restore_pending_resume_payload|pending_resume" truffles-api/app/routers/webhook/pending.py truffles-api/app/services/state_service.py truffles-api/app/core/dialog_state_service.py`
- **Blocked-by conditions:** frozen `pending.py` remains non-editable or the remaining continuity value lies in another non-frozen seam discovered by post-cutover audit
- **Owner role for closure:** `Top Architect`
