# TP-2026-01-31-llm-pack-ref-only

- Title/goal: Enforce LLM pack-ref-only contract for router + answer_interpreter (schema + validation + prompt cleanup).
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-018), `STATE.md` (PLAN: Unified Reasoning Core), `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard-LAW/policy/pending pre-LLM; decision_meta/trace on every early return; no orchestration in entrypoints/_legacy.py; stage order unchanged.
- Scope:
  - Add JSON schemas for dialogue controller and answer_interpreter outputs.
  - Add validators (Pydantic) and enforce schema in `route_dialogue_controller` and `interpret_expected_reply`.
  - Update LLM prompt to business-agnostic, pack-ref-only wording (no business lexicons).
  - Add unit tests for valid/invalid outputs.
- Out of scope: pack-index build/versioning, pack content changes, stage-order refactor, DB migrations, response composer changes.
- Touch-list:
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/schemas/intent.py`
  - `truffles-api/app/schemas/__init__.py`
  - `contracts/llm/dialogue_controller_output.v1.jsonschema`
  - `contracts/llm/answer_interpreter_output.v1.jsonschema`
  - `prompts/intent_classifier.md`
  - `truffles-api/tests/test_intent.py`
- Plan:
  1) Add JSON schema + Pydantic models for controller and answer_interpreter outputs.
  2) Validate LLM outputs; map invalid schema to `invalid_schema` error and safe fallback.
  3) Update prompt (file + fallback) to remove business-specific wording.
  4) Add targeted unit tests and run pytest.
- DoD:
  - Controller/answer_interpreter outputs are schema-validated.
  - Invalid schema triggers deterministic fallback (no LLM facts).
  - Prompt is business-agnostic and pack-ref-only.
  - Tests pass; evidence captured and recorded in STATE.md.
- Checks:
  - `pytest -q truffles-api/tests/test_intent.py`
- Evidence:
  - pytest output + file references; STATE.md updated with evidence by Brain/Top Architect before merge.
- Rollback: `git revert HEAD`.
- No-go:
  - Do not change `_legacy.py` or entrypoints.
  - Do not change stage order or decision graph.
  - Do not add business lexicons in code.
  - Do not touch packs/DB.
- Branch/worktree: `feat/2026-01-31-llm-pack-ref-only-a1`, `/home/zhan/worktrees/2026-01-31-llm-pack-ref-only-a1`, base `origin/main`, merge policy PR+CI, cleanup by Brain/Top Architect.
- Risks/blockers: controller output normalization vs schema strictness; keep validation aligned with existing cleaning to avoid false negatives.
