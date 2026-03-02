# TP-2026-03-02-s0-s1-signal-manifest-and-hardcode-gate-a1

## Block identity
- `BLOCK_ID`: SIG-S0-S1-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: SIG-PROGRAM-S0-S4
- `UNLOCKS`: S2 signal runtime compiler

## Название/цель
Закрыть `S0` и `S1` по P7-continuation: расширить static no-hardcode gate на signal-layer и вынести domain regex/keywords из signal services в schema-validated declarative manifest.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-process-integrity-signal-program-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `ops/diagnose.py`
  - `truffles-api/app/services/booking_signal_service.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
- `Baseline commands`:
  - `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES" ops/diagnose.py`
  - `rg -n "_RELATIVE_DAY_TOKEN_PATTERNS|_DAYPART_TOKEN_PATTERNS|_DATETIME_DURATION_CONTEXT_MARKERS|_DATETIME_DAYPART_STEMS" truffles-api/app/services/booking_signal_service.py`
- `FACT findings`:
  - hardcode gate не покрывает `*_signal_service.py`.
  - domain regex/markers остаются в `booking_signal_service.py`.

## One web search (mandatory before implementation)
- **Query (exact):** python regex configuration from yaml with schema validation best practices
- **Date/time (local):** 2026-03-02 09:34, Asia/Almaty
- **Why this query is precise:** нужен безопасный паттерн для externalized regex manifests без потери deterministic валидации.
- **Sources opened (from this query):**
  - Python `re` documentation (primary): https://docs.python.org/3/library/re.html
  - JSON Schema type reference (primary): https://json-schema.org/understanding-json-schema/reference/type
  - JSON Schema object reference (primary): https://json-schema.org/understanding-json-schema/reference/object
- **Existing solutions found:** хранить regex как data + schema validation + controlled compile path.
- **Decision:** integrate — вводим `SIGNAL_MANIFEST.yaml` + JSON schema + runtime loader API.
- **Rejected options:** оставлять regex в Python constants в `*_signal_service.py`.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** firebreak снял hardcode из core, но domain literals остались в signal-layer без data-contract.
- **Minimal reproduction:**
  - `rg -n "_RELATIVE_DAY_TOKEN_PATTERNS|_DAYPART_TOKEN_PATTERNS|_DATETIME_DURATION_CONTEXT_MARKERS|_DATETIME_DAYPART_STEMS" truffles-api/app/services/booking_signal_service.py`
  - `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES" ops/diagnose.py`
- **Evidence to capture:** diff + gate tests + signal behavior tests.
- **Five Whys (or equivalent):**
  1. Почему gate не остановил residual hardcode? — scope gate ограничен core files.
  2. Почему hardcode остался после P7? — перенос сделали в signal services как firebreak.
  3. Почему это риск? — domain drift переносится между файлами, а не в data layer.
  4. Почему сложно масштабировать? — новый домен требует code edits вместо manifest edits.
  5. Почему чинить сейчас? — это блокер для S2/S4 и cross-domain contract scaling.
- **Root cause statement:** нет сквозного no-hardcode enforcement для signal-layer и нет declarative signal-manifest контракта.
- **Fix mechanism:** S0 расширяет gate на signal files; S1 выносит domain patterns в schema-validated manifest и подключает signal services к нему.

## Reuse-first plan (mandatory)
- **Internal reuse:** `jsonschema` validation approach из `pack_compiler_service.py`, lexicon loading patterns из `pack_runtime_*`.
- **External reuse:** Python `re` docs + JSON Schema reference.
- **Why not reinvent the wheel:** используем standard JSON Schema и существующий runtime facade.

## Invariant
- Не ухудшить booking/info deterministic behavior.
- Не добавить runtime phrase branching обратно в webhook core.
- Любой residual hardcode должен быть либо в manifest data, либо в explicit technical whitelist.

## Scope
- S0 hardcode gate scope + technical allowlist.
- S1 signal manifest + schema + migration of booking/info signal literals.

## Out of scope
- S2 compiler/versioning pipeline.
- S3/S4 implementation.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/app/services/booking_signal_service.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/signal_manifest_service.py`
- `truffles-api/app/knowledge/generic/SIGNAL_MANIFEST.yaml`
- `contracts/packs/signal_manifest.v1.jsonschema`
- `truffles-api/tests/test_booking_quality_status_gate.py`

## Plan (1..N)
1. Extend hardcode gate scope to `*_signal_service.py` with technical-format whitelist.
2. Add signal manifest schema + YAML artifact for booking/info signal patterns.
3. Add signal manifest runtime loader helpers.
4. Migrate booking/info signal services to manifest-backed patterns.
5. Run deterministic checks and update evidence docs.

## DoD
- hardcode gate includes signal files.
- booking/info signal services no longer contain domain regex/keyword literals from old constants.
- manifest schema validates and runtime uses manifest-backed values.
- target deterministic tests are green.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "hardcode_core_gate or line_has_phrase_branching"`
- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "info_intents or booking_info_intents or expected_reply"`

## Evidence
- Git diff for `S0/S1`.
- Test outputs listed in Checks.
- Session + STATE updates with FACT entries.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0 (no expensive L3 in this block).
- **Fail-fast / scenario lock:** deterministic tests only.
- **Stop condition:** any regression in booking/info contract tests.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** branch-scoped deterministic validation before PR.
- **Go/no-go signals:** all listed deterministic tests green.
- **Rollback:** `git revert` of this block commit.
- **Post-release monitoring window:** next deterministic replay cycle under S2 prep.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-19-llm-first-firebreak-a1.md`
- `Drift closeout rule`:
  - no open doc drift for S0/S1 scope.

## Rollback
- Revert block commit in this branch.

## No-go
- Не переносить domain literals из core в другой runtime python-файл как workaround.
- Не ослаблять gate для прохода тестов.

## Risks/Blockers
- Manifest parse/validation errors can break signal path if not covered by tests.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: нет compiler/versioning API (S2), нет cross-domain suite (S4).
- `Why not in this block`: это scope следующих блоков `S2/S4`.
- `Risk if deferred`: manifest rollout без compiler contract может давать drift/dup logic.
- `Linked follow-up Task Package(s)`: `TP-S2`, `TP-S3`, `TP-S4`.
- `Expiry/trigger to stop deferral`: before closing S2.

## Next-block contract (mandatory)
- `Next block objective`: S2 runtime compiler/loader with versioning and cache contract.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py`
- `Blocked-by conditions`: S0/S1 checks not green.
- `Owner role for closure`: Brain + Top Architect.

