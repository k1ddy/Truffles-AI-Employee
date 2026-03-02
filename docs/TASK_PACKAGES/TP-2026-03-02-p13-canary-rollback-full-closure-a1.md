# TP-2026-03-02-p13-canary-rollback-full-closure-a1

## Block identity
- `BLOCK_ID`: SIG-P13-CANARY-ROLLBACK-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: none
- `UNLOCKS`: `P13 Canary + Rollback` -> `done`

## Название/цель
Полностью закрыть `P13`: внедрить исполняемый canary/rollback механизм для quality/runtime изменений с проверяемыми go/no-go сигналами и автоматизированным возвратом в baseline.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/quality_chain_controller.sh`
  - `scripts/llm_quality_guarded.sh`
  - `ops/diagnose.py`
  - `truffles-api/tests/test_booking_quality_chain_controller.py`
  - `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `Baseline commands`:
  - `rg -n "canary|rollback|go_no_go|promotion" scripts/quality_chain_controller.sh scripts/llm_quality_guarded.sh ops/diagnose.py`
  - `rg -n "P13 Canary \+ Rollback" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `FACT findings`:
  - chain controller и guarded wrapper существуют, но отдельный canary/rollback flow не автоматизирован.
  - parent TP фиксирует `P13 missing`.
- `Detected drift (docs vs code)`: отсутствует runtime canary automation.

## One web search (mandatory before implementation)
- **Query (exact):** `Google SRE canary analysis rollback strategy service release`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** нужен reference для формальных go/no-go и rollback при canary rollout.
- **Sources opened (from this query):**
  - Google SRE workbook canarying releases: `https://sre.google/workbook/canarying-releases/`
  - Argo Rollouts canary docs: `https://argo-rollouts.readthedocs.io/en/stable/features/canary/`
- **Existing solutions found:** staged promotion with metric gates and immediate rollback on threshold breach.
- **Decision:** `integrate` canary stage в chain controller + explicit rollback command path.
- **Rejected options:** manual ad-hoc rollout decisions without coded gating.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** нет кодового механизма canary+rollback для acceptance-to-release transitions.
- **Minimal reproduction:**
  - `rg -n "canary|rollback" scripts/quality_chain_controller.sh scripts/llm_quality_guarded.sh ops/diagnose.py`
- **Evidence to capture:** new scripts/commands + deterministic tests validating block/promote/rollback behavior.
- **Five Whys (or equivalent):**
  1. Ранние этапы фокусировались на lock/replay/full достоверности.
  2. Promotion оставался process/manual.
  3. Manual path не дает fail-closed rollback guarantee.
  4. Без canary gate сложно безопасно включать новые retrieval/policy changes.
  5. Поэтому `P13` остается missing.
- **Root cause statement:** отсутствует coded release safety pipeline with enforced canary and rollback.
- **Fix mechanism:** добавить canary stage + go/no-go evaluators + rollback executor в quality toolchain.

## Reuse-first plan (mandatory)
- **Internal reuse:** существующие chain controller state machine, run manifests, acceptance status builders.
- **External reuse:** SRE canary analysis pattern, staged promotion best practices.
- **Why not reinvent the wheel:** текущий chain controller уже имеет основу state transitions.

## Invariant
- Нельзя обходить existing acceptance gates.
- Rollback должен быть deterministic и быстрый.
- Любая деградация -> automatic block/rollback path.

## Scope
- Добавить canary stage в quality chain.
- Добавить go/no-go evaluation based on semantic/delivery/reliability gates.
- Добавить rollback command path и audit artifacts.
- Добавить deterministic tests для canary/rollback state transitions.

## Out of scope
- Kubernetes cluster-specific rollout manifests.
- Изменение доменной бизнес-логики.

## Touch-list
- `scripts/quality_chain_controller.sh`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_chain_controller.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить `canary` режим/состояние в chain controller.
2. Ввести go/no-go evaluator и thresholds из acceptance artifacts.
3. Добавить explicit rollback executor и rollback artifact logging.
4. Обновить guarded wrapper для поддержки canary/rollback.
5. Добавить deterministic tests на promote/block/rollback transitions.
6. Обновить runbook, parent TP и `STATE.md`.

## DoD
- Canary stage запускается и валидируется кодом.
- При fail thresholds chain выполняет rollback path.
- Deterministic tests для canary/rollback зеленые.
- Parent TP: `P13` -> `done`.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py`
- `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `ruff check scripts/quality_chain_controller.sh scripts/llm_quality_guarded.sh ops/diagnose.py truffles-api/tests/test_booking_quality_chain_controller.py truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `bash -n scripts/quality_chain_controller.sh`
- `bash -n scripts/llm_quality_guarded.sh`

## Evidence
- Script diffs with canary/rollback commands.
- Test outputs.
- Example canary->rollback chain artifacts.
- Parent TP + `STATE.md` updates.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic chain tests first; one controlled canary simulation
- **Stop condition:** rollback transition failure
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** canary mandatory before promotion.
- **Go/no-go signals:** no semantic blockers, no delivery hard-fail, no reliability breach.
- **Rollback:** auto rollback command + manual fallback command documented.
- **Post-release monitoring window:** first 24h after canary promotion.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P13` закрывается только при наличии coded canary + rollback + tests.

## Rollback
- Revert changes to chain/controller scripts and tests if canary state machine unstable.

## No-go
- Manual-only canary decisions без coded evaluator.
- Продвижение без rollback path.
- Подмена rollback soft warning вместо hard gate.

## Risks/Blockers
- Threshold tuning может требовать 1-2 controlled iterations.
- Ошибка state transition может блокировать chain.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: close `P14` evidence/state handoff enforcement.
- `First deterministic check command`: `rg -n "manual_audit|state_handoff|run_manifest" ops/diagnose.py scripts/quality_chain_controller.sh`
- `Blocked-by conditions`: red canary/rollback tests.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: chain controller state machine transitions.
- `Do not touch`: core webhook semantics.
- `Open risks`: rollback transition regressions.
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py`.
