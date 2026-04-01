# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R24-FALLBACK-JID-EXHAUSTION-PROOF-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R24-FALLBACK-JID-EXHAUSTION-PROOF-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r24_fallback_jid_exhaustion_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Land one bounded proof-only implementation family for fresh replay `r24`. This block must repair fallback-JID selection so outbox-enabled unique replay can mint a fresh dialog JID after allowlist exhaustion when `--allow-non-allowlist` is already explicit, without reopening runtime code, frozen routers, or acceptance gates.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-decision-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`

## FACT pre-check (before implementation)
- **Impacted code/docs/tests:**
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_jid_mode.py`
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- **Baseline commands:**
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r24 --status done --strict-artifacts`
  - `nl -ba ops/diagnose.py | sed -n '3288,3335p'`
  - `nl -ba ops/diagnose.py | sed -n '19256,19292p'`
  - `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`
- **FACT findings:**
  - `r24` already proves the old `reasoning_core.py` runtime family is closed on dialog `2`, turn `9` and downstream dialog `2` turns through `14`.
  - The replay still fail-closes before dialog `3` because `_llm_quality_select_fallback_jid(...)` returns `None` after allowlist exhaustion while outbox is enabled.
  - The replay already runs with `jid_mode=unique` and `allow_non_allowlist=true`, so the hard stop is now a proof-path helper mismatch, not a provider or runtime contract.

## One web search (mandatory before implementation)
- **Query (exact):** `WhatsApp Cloud API test phone number allowlist official documentation`
- **Date/time (local):** `2026-03-23 11:23 +05:00`
- **Sources opened (from this query):**
  - `https://stackoverflow.com/questions/74622031/whatsapp-business-api-cloud-how-do-i-register-a-customers-phonenumber-via-api`
  - `https://developers.facebook.com/docs/whatsapp/cloud-api/get-started#sent-test-message` (official Meta doc referenced by the answer; direct tooling fetch did not render, so the cited contract was read via the Stack Overflow answer that links it)
- **Source quality:** official vendor documentation / primary source via Meta doc reference, plus one attributed technical discussion that quotes the relevant limitation.
- **Existing solutions found:** WhatsApp-provided test numbers have a recipient list limit, while real registered sender numbers do not share that hard recipient cap. That means our replay harness should only hard-stop on allowlist exhaustion when non-allowlist fallback is actually forbidden, not when `--allow-non-allowlist` is already explicit.
- **Decision:** `build`
  - keep allowlist-first rotation
  - add deterministic fresh-JID generation after allowlist exhaustion when `allow_non_allowlist=true`
  - cover the helper with deterministic proof tests instead of reopening runtime code
- **Rejected options:** preserving the outbox-only hard stop after allowlist exhaustion; reopening `reasoning_core.py`; weakening replay contamination gates.

## Root cause (mandatory)
- **Symptom:** exact replay `r24` remains non-canonical and stops before dialog `3` even though the targeted `r23` runtime row is already strict-green.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json` and confirm the run is still incomplete/non-canonical
  2. inspect `ops/diagnose.py:3288-3335` and confirm `_llm_quality_select_fallback_jid(...)` returns `None` immediately after allowlist exhaustion when `skip_outbox=False`
  3. inspect `ops/diagnose.py:19256-19292` and confirm contaminated preflight breaks once fallback selection returns `None`
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
  - `ops/diagnose.py:3288-3335`
  - `ops/diagnose.py:19256-19292`
  - `truffles-api/tests/test_booking_quality_jid_mode.py`
- **Five Whys:**
  1. Why does replay stop before dialog `3`? Because contaminated preflight runs out of fallback JIDs.
  2. Why does it run out? Because the helper rotates through allowlist candidates and then returns `None`.
  3. Why does it return `None`? Because the helper hard-stops whenever outbox is enabled, even if non-allowlist fallback is explicitly allowed.
  4. Why is that wrong here? Because the replay already runs with `jid_mode=unique` and `allow_non_allowlist=true`, which means a fresh synthetic JID is contract-allowed for isolation.
  5. Why is this not runtime work? Because the old runtime family is already closed on fresh replay evidence; the stop happens inside proof-path preflight before dialog `3` begins.
- **Root cause statement:** `_llm_quality_select_fallback_jid(...)` still encodes an outdated outbox-first hard stop after allowlist exhaustion, so exact replay cannot mint a fresh unique dialog JID even when `allow_non_allowlist=true` explicitly permits it.
- **Fix mechanism:** make fallback selection allow a deterministic fresh non-allowlist JID after allowlist exhaustion whenever `allow_non_allowlist=true`, and prove that behavior with targeted JID-mode regressions.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_llm_quality_generate_unique_jid(...)`
  - existing contaminated-preflight fallback loop in `ops/diagnose.py`
  - existing deterministic JID helper tests in `truffles-api/tests/test_booking_quality_jid_mode.py`
- **External reuse:**
  - Meta WhatsApp Cloud API test-recipient limitation guidance
- **Why not reinvent the wheel:**
  - the helper already knows how to mint deterministic unique JIDs; this block only extends when that existing mechanism is admissible.

## Work mode (mandatory)
- **Mode:** `implementation`
- **Why this mode:** this block changes one bounded proof-path helper and its deterministic tests.
- **Family handled in this block:** `seed19 r24 fallback-JID exhaustion proof family`
- **Closure artifact expected from this mode:** focused proof tests, canon sync to the implementation handoff, and one exact replay handoff.

## Invariant
- do not reopen `truffles-api/app/services/reasoning_core.py`
- do not edit frozen webhook routers
- do not weaken replay contamination gates or acceptance thresholds
- keep allowlist-first behavior when untried allowlist JIDs still exist

## Scope
- repair fallback-JID selection in `ops/diagnose.py`
- add deterministic regressions in `truffles-api/tests/test_booking_quality_jid_mode.py`
- sync canon/session/packet to the implementation result

## Out of scope
- runtime code changes
- acceptance lock/full runs
- scenario mutation
- frozen router edits

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Repair `_llm_quality_select_fallback_jid(...)` so allowlist-first rotation can fall back to a deterministic fresh JID when `allow_non_allowlist=true`.
2. Add targeted JID-mode regressions for outbox-enabled fallback and repeated fresh-JID generation.
3. Run focused proof checks.
4. Sync canon/session/packet to the implementation result.
5. Hand off the next move as one fresh exact replay on the locked seed-`19` scenarios.

## DoD
- fallback-JID helper no longer hard-stops after allowlist exhaustion when non-allowlist fallback is explicitly allowed
- focused JID-mode tests are green
- canon points at the implementation block and the next move is the exact replay, not more proof patching
- mandatory guard/session stack is green after sync

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py`
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`
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
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_jid_mode.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`
- updated canon/session/packet artifacts

## Rollback
Revert the helper and test changes, then restore the previous proof-decision canon if focused proof fails.

## No-go
- no runtime changes first
- no frozen router edits
- no gate weakening
- no new replay until focused proof is green

## Risks/blockers
- if fresh generated JIDs can also collide with tried values, the helper must mint another deterministic candidate instead of returning the same one again.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- downstream dialog `3+` runtime families remain unknown until exact replay becomes canonical
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt

### Why not in this block
This is a bounded proof-only helper repair.

### Risk if deferred
Replay will keep fail-closing preflight and we will keep misclassifying downstream runtime work as unavailable.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-canary-replay-a922.md`

### Expiry/trigger to stop deferral
Immediate; exact replay must follow once focused proof is green.

## Next-block contract (mandatory)
### Next block objective
Run one fresh exact replay on the locked seed-`19` scenarios and strict-audit whether dialog `3` now starts after fallback-JID repair.

### First deterministic check command
`python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py`

### Blocked-by conditions
Focused JID-mode proof still red; stale local runtime; missing `r24` audit.

### Owner role for closure
Brain / Top Architect
