# TP-2026-03-27-consultant-core-workstream1-media-outbox-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-media-outbox-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-secondary-helper-mesh-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-secondary-helper-mesh-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-remaining-legacy-helper-proof`

## Название/цель
Снять remaining `_legacy.py` authority из media/outbox helper family: перевести `media.py` и `outbox.py` на direct/local owners и narrow delayed `decision.py` access вместо ambient legacy adapter.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/media.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py`
  - `rg -n "MEDIA_|ASR_|STYLE_REFERENCE_|MSG_MEDIA_|_find_message_by_message_id|_find_message_by_conversation_created_at|_ensure_rag_meta_defaults" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py`
- `FACT findings`:
  - `media.py` still imports `_legacy.py` for media/asr/style constants, media response messages, env helper, and logger access.
  - `outbox.py` still imports `_legacy.py` for saved-message lookup, RAG meta defaults, media decision serialization/deserialization, media evaluation, and one trace write.
  - both files are active runtime helpers, so `_legacy.py` remains live on media and outbox paths even after the earlier helper-mesh cleanup.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/reference import statement python reference`
- **Date/time (local):** `2026-03-27 23:40 +05`
- **Why this query is precise:** this block replaces ambient legacy adapter imports with explicit direct imports and narrow delayed access where import cycles remain.
- **Sources opened (from this query):**
  - `Python Language Reference / The import system`: `https://docs.python.org/3.15/reference/import.html`
- **Source quality:** official Python documentation (primary source).
- **Existing solutions found:** Python import semantics support explicit imports and narrow delayed module binding without a wildcard compatibility adapter.
- **Decision:** `build` — remove `_legacy.py` from `media.py` and `outbox.py`, using local ownership plus narrow delayed `decision.py` access only where cycle-sensitive legacy residue still exists.
- **Rejected options:**
  - keep `_legacy.py` for media/outbox convenience: rejected because it preserves the ambient legacy bus on active helper paths.
  - move all remaining media/outbox helper code back into `decision.py`: rejected because it regrows legacy god-file authority.

## Root cause (mandatory)
- **Symptom:** `_legacy.py` still remains active on media/outbox paths after the primary and secondary helper cuts.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py`
- **Evidence to capture:**
  - `media.py` and `outbox.py` no longer import `_legacy.py`
  - focused regressions for media/outbox/expected-reply stay green
  - architecture proof freezes the no-`_legacy` state for this helper family
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still open after the secondary helper cut? Because active helper paths still import `_legacy.py` in media/outbox.
  2. Why does that matter? Because these helpers stay on the default runtime path and keep the compatibility adapter live.
  3. Why are they still coupled? Because constants, saved-message lookups, and meta-default helpers were never rebound directly after extraction.
  4. Why not postpone? Because criterion 4 requires owner-adjacent legacy paths to be shadow-only or deleted before closeout.
  5. Why use narrow delayed decision access instead of more wrappers? Because the goal is to kill the adapter bus without growing new compatibility layers.
- **Root cause statement:** `media.py` and `outbox.py` still depend on `_legacy.py` as an ambient adapter for constants and helper calls, so live runtime helper authority is still routed through the legacy mesh.
- **Fix mechanism:** replace `_legacy.py` calls with local ownership, direct helper imports, and narrow delayed `decision.py` access only where the remaining legacy residue is cycle-sensitive.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse existing helper functions already extracted in `media.py`, `trace.py`, and `http.py`
  - reuse direct `decision.py` residue only through narrow delayed access where cycle-sensitive constants/helpers remain
- **External reuse:**
  - no external package is needed
- **Why not reinvent the wheel:** this block only rebinds existing owners and removes the adapter bus.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `3`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- media intake / rate-limit / storage / ASR behavior must remain deterministic.
- outbox enqueue/replay behavior must remain deterministic.
- no new semantic owner path may be introduced.

## Scope
- remove `_legacy.py` imports from `media.py` and `outbox.py`
- bind media/outbox helpers to local/direct owners and narrow delayed decision access where necessary
- add architecture proof freezing this helper family boundary
- update focused deterministic tests and repo truth

## Out of scope
- deleting `decision.py`
- deleting `_legacy.py`
- service-side `_legacy.py` callers in `tool_registry_service.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/media.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-media-outbox-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Rebind `media.py` away from `_legacy.py` using local constants/logger and narrow delayed `decision.py` access only where necessary.
2. Rebind `outbox.py` away from `_legacy.py` using direct/local helpers and narrow delayed `decision.py` access only where necessary.
3. Add architecture freeze guards for `media.py` and `outbox.py`.
4. Run focused deterministic checks once for the whole block.
5. Update repo truth once for the whole block.

## DoD
- `media.py` and `outbox.py` contain no `_legacy.py` import.
- focused regressions pass.
- architecture guard freezes the helper family boundary.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "media or style_reference or enqueue_only or outbox_payload_guard or expected_reply_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- `media.py` and `outbox.py` no longer import `_legacy.py`
- passing focused regressions
- architecture freeze guard for this helper family

## Rollback
- restore `_legacy.py` imports in `media.py` / `outbox.py` and revert tests/docs together.

## No-go
- no new wildcard or adapter exports
- no regrowth of `decision.py` helper authority beyond narrow residue use
- no claim that Workstream 1 is done before remaining `decision.py` / `__init__.py` / service-side residue is reassessed

## Risks/Blockers
- direct top-level imports from `decision.py` can create cycles, so some residue may need delayed accessors.
- `tool_registry_service.py` still remains outside this block and may keep compatibility residue alive.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `decision.py`, `__init__.py`, and service-side `_legacy.py` callers remain after this helper family cut.
- `Why not in this block`: they are a separate residue family beyond the media/outbox helpers.
- `Risk if deferred`: Workstream 1 closeout remains blocked until those consumers are either demoted or proven shadow-only.
- `Linked follow-up Task Package(s)`: `WS1-closeout-final-legacy-residue-proof`
- `Expiry/trigger to stop deferral`: if any new default-path helper starts importing `_legacy.py`, the residue family expands and this deferral stops being valid.

## Next-block contract (mandatory)
- `Next block objective`: reassess the remaining `_legacy.py` consumers (`decision.py`, `__init__.py`, `tool_registry_service.py`) and determine the honest final closeout path for Workstream 1.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook truffles-api/app/services | sed -n '1,200p'`
- `Blocked-by conditions`: media/outbox cut reveals active default-path residue that still requires `_legacy.py` outside the accepted list.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - removed `_legacy.py` from active `media.py` and `outbox.py`
  - media/outbox now use local/direct owners plus narrow delayed `decision.py` residue access only where needed
  - architecture proof now freezes this helper family against `_legacy.py` reintroduction
- `Files touched`:
  - `truffles-api/app/routers/webhook/media.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/tests/test_provider_gateway_integration.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py truffles-api/tests/test_webhook_media_policy.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_media_policy.py` -> `3 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_provider_gateway_integration.py` -> `12 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "style_reference_detects_send_photo_phrases or expected_reply_contract_bypasses_human_request or expected_reply_contract_prefers_session_memory_pending_question_contract"` -> `3 passed, 189 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `10 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/outbox.py` -> no matches
  - architecture guard now freezes `media.py` and `outbox.py` against `_legacy.py` reintroduction
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - `_legacy.py` is no longer the active media/outbox helper authority bus
- `Residual debt left for next block`:
  - remaining Workstream 1 `_legacy.py` residue is now narrowed to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/__init__.py`, and service-side compatibility callers in `truffles-api/app/services/tool_registry_service.py`
