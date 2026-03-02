# TP-2026-03-02-p14-evidence-state-handoff-full-closure-a1

## Block identity
- `BLOCK_ID`: SIG-P14-EVIDENCE-STATE-HANDOFF-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-p13-canary-rollback-full-closure-a1
- `UNLOCKS`: `P14 Evidence + STATE Handoff` -> `done`

## Название/цель
Полностью закрыть `P14`: сделать `STATE.md` handoff и evidence completeness обязательным кодовым gate в quality chain, чтобы merge-blocking происходил автоматически при неполном пакете артефактов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `ops/diagnose.py`
  - `scripts/quality_chain_controller.sh`
  - `scripts/session_check.sh`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
  - `truffles-api/tests/test_booking_quality_chain_controller.py`
- `Baseline commands`:
  - `rg -n "summary.json|brief.md|responses.jsonl|trace_bundle.jsonl|run_manifest" ops/diagnose.py scripts/quality_chain_controller.sh`
  - `rg -n "STATE.md|session_check|manual_audit" scripts/session_check.sh docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `FACT findings`:
  - artifacts генерируются.
  - `STATE.md` handoff остается процессным требованием, а не жестким кодовым gate.
  - parent TP фиксирует `P14 partial`.
- `Detected drift (docs vs code)`: process/code mismatch в handoff enforcement.

## One web search (mandatory before implementation)
- **Query (exact):** `supply chain provenance attestations release artifacts integrity policy`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** нужен reference для обязательной связки release decision и complete evidence pack/provenance.
- **Sources opened (from this query):**
  - SLSA provenance overview: `https://slsa.dev/spec/v1.0/provenance`
  - NIST SSDF practices: `https://csrc.nist.gov/Projects/ssdf`
- **Existing solutions found:** fail-closed policy with mandatory attestations/artifact integrity before promotion.
- **Decision:** `integrate` fail-closed evidence completeness + STATE handoff gate.
- **Rejected options:** process-only reminder without enforced gate.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** можно получить "технически полный" run без machine-checked handoff completeness.
- **Minimal reproduction:**
  - `rg -n "P14 Evidence \+ STATE Handoff" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `scripts/session_check.sh` (в текущем виде не валидирует наличие state handoff ссылки на run artifacts)
- **Evidence to capture:** new gate results + failing/green test cases.
- **Five Whys (or equivalent):**
  1. Handoff проверялся руками.
  2. Ручная проверка не fail-closed.
  3. Без coded gate возможны пропуски evidence.
  4. Пропуски подрывают reproducibility и audit trail.
  5. Поэтому `P14` не закрывается полностью.
- **Root cause statement:** отсутствует кодовый merge-blocking gate на полноту evidence + STATE handoff.
- **Fix mechanism:** добавить deterministic gate, который требует полный artifact pack и ссылку/запись handoff в `STATE.md`.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing run manifest/index/manual_audit status builders, session check framework.
- **External reuse:** provenance attestation patterns (SLSA/SSDF).
- **Why not reinvent the wheel:** все артефакты уже есть; нужен enforcement layer.

## Invariant
- Не менять runtime semantics.
- Не ослаблять existing quality gates.
- Handoff policy должна быть fail-closed.

## Scope
- Добавить evidence completeness gate в `ops/diagnose.py`/chain controller.
- Добавить `STATE.md handoff` check в `session_check` для core/behavior blocks.
- Добавить deterministic tests на pass/fail cases.
- Обновить parent TP и `STATE.md`.

## Out of scope
- Редизайн всей docs системы.
- Внешние CI platform integrations beyond current repo tooling.

## Touch-list
- `ops/diagnose.py`
- `scripts/quality_chain_controller.sh`
- `scripts/session_check.sh`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_chain_controller.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить gate `evidence_handoff_complete` с fail reasons.
2. Привязать gate к chain promotion decision.
3. Добавить проверку `STATE.md` handoff в `session_check` для core behavior changes.
4. Добавить deterministic tests на red/green paths.
5. Обновить parent TP и `STATE.md` с фактическим закрытием.

## DoD
- Promotion block срабатывает при неполном artifact pack.
- Promotion block срабатывает без `STATE.md` handoff evidence.
- Deterministic tests зеленые.
- Parent TP: `P14` -> `done`.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff or artifact or evidence"`
- `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py -k "handoff or evidence"`
- `bash -n scripts/session_check.sh`
- `ruff check ops/diagnose.py scripts/quality_chain_controller.sh scripts/session_check.sh truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_chain_controller.py`
- `scripts/session_check.sh`

## Evidence
- Gate code diff and tests.
- Example red run (missing evidence) and green run (complete evidence).
- Parent TP + `STATE.md` updates.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic tests only
- **Stop condition:** false-positive gate blocks on compliant run
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic gate rollout in CI and local `session_check`.
- **Go/no-go signals:** zero false-pass for missing evidence, zero false-fail for compliant evidence.
- **Rollback:** revert gate commit and restore prior behavior.
- **Post-release monitoring window:** next 5 PRs with core behavior changes.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
  - `docs/SESSION_START_PROMPT.txt` (if check contract wording changes)
- `Drift closeout rule`:
  - `P14` закрывается только после включенного code gate и тестов.

## Rollback
- Revert commits and re-run deterministic checks.

## No-go
- Soft warning вместо hard gate.
- Manual-only confirmation для closure.
- Ослабление existing artifact requirements.

## Risks/Blockers
- Возможны ложные блокировки на legacy sessions; требуется compatibility branch in check logic.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: keep parent TP synced with `P14=done` and continue remaining blocked block (`P12`) by separate unblock decision.
- `First deterministic check command`: `scripts/session_check.sh`
- `Blocked-by conditions`: red evidence/handoff gate tests.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `ops/diagnose.py` evidence gate builders and `session_check.sh` handoff checks.
- `Do not touch`: runtime semantic logic in webhook routers.
- `Open risks`: legacy compatibility path in session checks.
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff or artifact"`.

## Execution status (2026-03-02)
- `Status`: `done`
- `Implementation facts`:
  - Added fail-closed evidence handoff status builder and manifest/summary sync:
    - `ops/diagnose.py`:
      - `LLM_QUALITY_EVIDENCE_HANDOFF_REQUIRED_ARTIFACTS`
      - `_llm_quality_collect_evidence_handoff_status`
      - `evidence_handoff_valid`/`evidence_handoff_reasons` in run manifest + summary quality status.
  - Enforced previous-step evidence handoff in chain controller before next canonical step:
    - `scripts/quality_chain_controller.sh`:
      - `_summary_evidence_handoff_status`
      - `ensure_previous_step_brief` blocks on `missing_evidence_handoff:*`.
  - Enforced merge-time handoff bundle in session gate for core behavior changes:
    - `scripts/session_check.sh`:
      - manual audit done + evidence bundle completeness checks,
      - explicit `STATE.md` handoff requirement when evidence gate is active.
  - Added deterministic coverage:
    - `truffles-api/tests/test_booking_quality_status_gate.py`
    - `truffles-api/tests/test_booking_quality_chain_controller.py`
- `Deterministic evidence`:
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff or artifact or evidence"` (`7 passed, 73 deselected`).
  - `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py -k "handoff or evidence"` (`4 passed, 15 deselected`).
  - `bash -n scripts/session_check.sh` (ok).
  - `bash -n scripts/quality_chain_controller.sh` (ok).
  - `ruff check ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_chain_controller.py` (ok).
