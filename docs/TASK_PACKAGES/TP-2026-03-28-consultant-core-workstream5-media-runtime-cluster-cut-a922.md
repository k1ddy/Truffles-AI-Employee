# TP-2026-03-28-consultant-core-workstream5-media-runtime-cluster-cut-a922

## Title / Goal
Remove the remaining live `media.py -> decision.py` helper seam by moving the media policy/default/message cluster into `media.py` itself and leaving only compatibility aliases in `decision.py`.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_media.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com extract small cohesive class from large class helper methods`
- Date/time: `2026-03-28T08:41:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/class-too-large.html`
- High-signal source quality:
  - Martin Fowler primary refactoring article on moving one cohesive helper slice at a time into a smaller direct owner while leaving the large class with compatibility aliases only.
- Found reusable idea:
  - redirect the live caller to the target owner first, then keep the old god-file surface as aliases until the rest of the strangler is complete.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already uses this same direct-owner strangler pattern across `runtime_primitives.py`, `booking_runtime.py`, `pending_runtime.py`, and the operational helper cut; `media.py` is the last large active consumer and should follow the same pattern.
- Rejected options:
  - keep `media.py` on `decision.py` until final Workstream 5 closeout: rejected because it is now the last large active helper seam.
  - create a second extra facade in front of `media.py`: rejected because `media.py` itself is the natural owner of its policy/default/message helpers.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/media.py` still reads all of its media policy/default/message helpers from `decision.py`, so the last large runtime helper family remains live on the god-file.

### Minimal Reproduction
1. Inspect direct `decision_router.*` reads in `truffles-api/app/routers/webhook/media.py`.
2. Confirm they all belong to the media helper family:
   - media type aliases
   - media size/rate/storage defaults
   - transcription defaults
   - ASR low-confidence thresholds
   - style-reference hint tokens/patterns
   - media user-facing messages
3. Confirm no remaining non-media caller needs `decision.py` to own those values.

### Evidence
- `rg -n "_decision_runtime|decision_router\." truffles-api/app/routers/webhook/media.py`
- `rg -n "MEDIA_TYPE_ALIASES|MEDIA_MAX_DEFAULT_MB|MEDIA_RATE_LIMIT_DEFAULTS|MEDIA_STORAGE_DEFAULT_DIR|MEDIA_STORAGE_MAX_BYTES|AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB|ASR_LOW_CONFIDENCE_MIN_CHARS|ASR_LOW_CONFIDENCE_MIN_WORDS|ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS|ASR_LOW_CONFIDENCE_NON_LETTER_RATIO|STYLE_REFERENCE_PATTERNS|STYLE_REFERENCE_HINT_TOKENS|MSG_MEDIA_UNSUPPORTED|MSG_MEDIA_TOO_LARGE|MSG_MEDIA_RATE_LIMIT" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/media.py`

### Five Whys
1. Why does `media.py` still import `decision.py`?
   - Because its default/message cluster was never re-homed after the other helper families were cut.
2. Why is that wrong now?
   - Because `decision.py` is still the live supplier for the last large operational helper family.
3. Why does that matter?
   - Because Workstream 5 cannot close honestly while `decision.py` still owns active helper behavior on the runtime path.
4. Why move it into `media.py` itself?
   - Because the whole cluster is media-specific and already consumed only by `media.py` plus compatibility aliases.
5. Why do it now?
   - Because after the booking and operational-helper cuts, this is the last large active seam.

### Root Cause Statement
The media helper family was left behind in `decision.py`: `media.py` still pulls its defaults, ASR thresholds, style-reference heuristics, and user-facing media responses from the legacy god-file instead of owning them directly.

### Fix Mechanism
Move the media helper cluster into `media.py`, switch all media reads to local/direct symbols, keep compatibility aliases in `decision.py`, and add deterministic guards so `media.py` cannot drift back to `decision_router.*`.

## Invariant
- Media intake, rate limiting, storage, ASR gating, and style-reference behavior stay unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live media-helper ownership.

## Scope
- Move the media helper cluster into `media.py`.
- Leave compatibility aliases in `decision.py` only.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Deleting `decision.py`.
- Reworking unrelated message endpoint failures outside the media path.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/media.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_webhook_media_policy.py`
- `truffles-api/tests/test_provider_gateway_integration.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Move the media helper cluster into `media.py`.
2. Switch all media reads to local/direct symbols and remove `_decision_runtime()`.
3. Leave compatibility aliases in `decision.py` only.
4. Add focused deterministic coverage and architecture guard updates.
5. Update repo truth.

## DoD
- `media.py` no longer reads the moved media helper cluster through `decision_router.*`.
- `media.py` no longer needs `_decision_runtime()`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_webhook_media_policy.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_media_policy.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_provider_gateway_integration.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "style_reference or media"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "media_runtime_cluster_uses_narrow_owner or operational_helper_runtime_cluster_uses_narrow_owners or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused media pytest output
- Focused architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility facade in front of `decision.py`.
- No semantic regex/phrase growth in governed core.
- No doc-only closure without authority reduction.

## Risks / Blockers
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `Canon Sync Gate` remains red because worktree `AGENTS.md` diverges from `/home/zhan/AGENTS.md`; this block cannot claim session gate closure.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `decision.py` itself will still survive as a compatibility orchestration shell after the media cut.

### Why not in this block
- This family is bounded to the last active `media.py -> decision.py` helper seam, not final `decision.py` deletion.

### Risk if deferred
- `decision.py` remains the last large live helper owner on the active runtime path.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `media.py` is still reading any moved helper from `decision.py`.

## Next-block Contract (mandatory)
### Next block objective
After this cut, run the Workstream 5 closeout proof pass against the remaining direct `decision.py` consumers and decide whether Workstream 5 is done.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "media_runtime_cluster_uses_narrow_owner or operational_helper_runtime_cluster_uses_narrow_owners"`

### Blocked-by conditions
- This block must first prove that `media.py` no longer reads the moved helper cluster from `decision.py` and that focused media tests stay green.

### Owner role for closure
- Brain / Top Architect
