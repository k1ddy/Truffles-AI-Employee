# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Proof Decision A922

## Truthful Split
- Fresh replay `r24` closes the old runtime family:
  - dialog `2`, turn `9` (`На какое время лучше записаться?`) is now strict-green on `booking_prompt` / `collect`
  - covered downstream dialog `2` rows through turn `14` remain strict-green as well
- The new first blocker is not `reasoning_core.py` and not a semantic/runtime regression.

## New First Blocker
- Classification: `proof / preflight contamination gap`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/runtime_state.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
  - `ops/diagnose.py:3288`
  - `ops/diagnose.py:19256`
- Fresh blocker shape:
  - dialogs `1` and `2` complete without strict failures
  - dialog `3` never starts turn execution because replay preflight rotates across contaminated allowlist JIDs and then fail-closes
  - final artifact remains non-canonical: `infra_valid=false`, `semantic_valid=false`, `stop_reason=in_progress`
- Root cause statement:
  - `_llm_quality_select_fallback_jid(...)` currently returns `None` once the allowlist pool is exhausted while outbox is enabled, even though the replay already runs with `jid_mode=unique` and `allow_non_allowlist=true`
  - the proof path therefore cannot mint a fresh unique JID for dialog `3` and stops as contaminated preflight instead

## Decision
- Do not reopen runtime code first.
- Move to a bounded proof family in `ops/diagnose.py` plus JID-mode regressions.
