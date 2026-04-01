Title/Goal
- Create a repo-backed forensic memory system for consultant-core so future sessions can recover architecture truth from documents instead of relying on model memory or narrative retellings.

Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- User directive on `2026-03-26`: stop implementation drift, work through persistent forensic documents, accumulate file-by-file analysis plus final synthesis.

Root cause (mandatory)
- Symptom
  - The program keeps reopening the same architectural questions across sessions, while implementation drifts continue and strategic closure remains `open`.
- Minimal reproduction
  - Multiple prior sessions changed runtime/core files without producing a durable system-level inventory that explains what exists, why it exists, what is salvageable, and what still violates the semantic-first charter.
- Evidence
  - `STATE.md` still reports strategic closure `open`.
  - The active worktree snapshot at `8319d9e1` still contains a thin `consultant_core_v2` wrapper while orchestration remains in `truffles-api/app/core/consultant_runtime.py`.
- Five Whys
  1. Why does the same strategic problem reappear? Because context is carried mostly by session memory and scattered code changes.
  2. Why is session memory insufficient? Because this migration spans many hotspot files and many sessions.
  3. Why do hotspot files keep drifting? Because there is no durable forensic ledger of owners, truth-carriers, control paths, and deterministic rewrites.
  4. Why does that matter? Because every new session re-derives partial understanding and easily falls back into micro-fixes.
  5. Why has this not been corrected earlier? Because implementation work repeatedly outran system analysis.
- Root cause statement
  - The repo lacked an explicit external-memory forensic system that records architecture facts, violations, and cutover dependencies in a reusable, file-backed form.
- Fix mechanism
  - Create a dedicated documentation system for consultant-core forensics: file analyses, cross-cut ledgers, and a final synthesis document that future sessions must read before new architecture work.

One web search (mandatory before implementation)
- Query
  - `site:docs.arc42.org arc42 template architecture documentation`
- Date/time
  - `2026-03-26T22:40:00+05:00`
- Opened sources
  - `https://docs.arc42.org/` (official arc42 documentation)
- Source quality
  - Official architecture-documentation reference.
- What was found
  - A stable architecture-documentation system should separate per-component descriptions from cross-cutting views and final synthesis.
- Reuse / integrate / build decision
  - `integrate`
- Reason
  - We need a layered document system, not one narrative file.
- Rejected options
  - Single monolithic analysis file: rejected because it becomes unreadable and unusable as persistent working memory.

Invariant
- No new runtime behavior changes.
- No new semantic fixes disguised as analysis.
- All analysis claims must be tagged as `FACT`, `INFERENCE`, or `UNKNOWN`.

Scope
- Create the forensic document system under `docs/system_forensics/`.
- Produce the first deep hotspot analysis for `truffles-api/app/core/consultant_runtime.py`.
- Seed cross-cut ledgers and a final synthesis starter.
- Register the new docs in `STRUCTURE.md` and `STATE.md`.

Out of scope
- Refactoring runtime/core behavior.
- Closing any strategic architecture item.
- Finishing the entire repo analysis in one block.

Touch-list
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/TEMPLATE_FILE_ANALYSIS.md`
- `docs/system_forensics/files/*`
- `docs/system_forensics/ledgers/*`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/TASK_PACKAGES/TP-2026-03-26-consultant-core-system-forensics-foundation-a922.md`
- `STRUCTURE.md`
- `STATE.md`

Plan
1. Create the forensic document tree and working method.
2. Record the first deep file analysis for `consultant_runtime.py`.
3. Seed cross-cut ledgers from that first analysis.
4. Create the final synthesis starter document.
5. Register the document system in `STRUCTURE.md` and `STATE.md`.

DoD
- `docs/system_forensics/` exists with index, method, template, ledgers, final synthesis starter, and at least one completed file analysis.
- The first file analysis is evidence-backed and line-referenced.
- `STRUCTURE.md` and `STATE.md` mention the new document system truthfully.
- A basic docs integrity check and `git diff --check` pass.

Work mode (mandatory)
- forensic

Checks
- `python3 - <<'PY' ...` existence/integrity check for the new forensic docs
- `git diff --check`

Evidence
- New docs under `docs/system_forensics/`
- Updated `STRUCTURE.md`
- Updated `STATE.md`
- Check outputs recorded in the session response

Rollback
- Revert the docs-only commit that introduces `docs/system_forensics/` and index updates.

No-go
- No architecture claims without file refs.
- No closure claims.
- No implementation drift hidden inside docs work.

Risks/blockers
- The analysis can still miss hidden runtime paths if later scans discover additional callers or duplicate semantic surfaces.
- The first block only seeds the system; it does not answer the whole repo.

Residual architecture debt (mandatory)
- Current residuals accepted in this block
  - The first thirty-five hotspots are now analyzed: `consultant_runtime.py`, `dialog_state_service.py`, `intent_service.py`, `turn_executor.py`, `turn_planner.py`, `booking_prompt_owner.py`, `reasoning_core.py`, `decision.py`, `_legacy.py`, `context_manager.py`, `response.py`, `booking.py`, `info.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`, `app/webhook.py`, `app/main.py`, `app/routers/webhook/__init__.py`, `test_message_endpoint.py`, `test_webhook_dedup.py`, `test_webhook_response.py`, `test_webhook_booking.py`, `test_booking_chaos_dialogs.py`, `app/routers/outbox_service.py`, `app/routers/webhook/outbox.py`, `test_outbox_service_app.py`, `test_provider_gateway_integration.py`, `app/outbox_service_app.py`, `app/routers/admin.py`, `test_admin_legacy_auth.py`, `test_outbox_transport_degraded.py`, `app/workers/outbox.py`, and `app/routers/console.py`.
  - Cross-cut ledgers and final synthesis are much richer, but they still are not complete whole-repo closure artifacts.
- Why not in this block
  - Full repo analysis still must proceed hotspot by hotspot to stay evidence-backed.
- Risk if deferred
  - Remaining conclusions can still change after the direct repo-contract pins around the worker/console outbox caller surfaces are analyzed.
- Linked follow-up Task Package(s)
  - Current follow-up inside this TP: remaining live outbox package-seam caller analysis after the helper-test block.
- Expiry/trigger to stop deferral
  - If implementation resumes before the next hotspot analysis exists, this forensic block has failed its purpose.

Next-block contract (mandatory)
- Next block objective
  - Map the direct repo-contract pins around the live worker/console outbox caller surfaces, starting with `truffles-api/tests/test_outbox_worker_settings.py` and `truffles-api/tests/test_console_ops_jobs.py`, then update ledgers/final synthesis with that evidence.
- First deterministic check command
  - `rg -n "app\.workers import outbox|_get_outbox_worker_settings|assert_outbox_worker_startup_safe|_run_outbox_process_job|ConsoleOpsJobRunRequest\(|job_type=\"outbox_process\"" truffles-api/tests/test_outbox_worker_settings.py truffles-api/tests/test_console_ops_jobs.py truffles-api/app/workers/outbox.py truffles-api/app/routers/console.py`
- Blocked-by conditions
  - Dirty worktree that changes hotspot files without being committed first.
- Owner role for closure
  - Brain / Top Architect
