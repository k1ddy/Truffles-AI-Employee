# TP-2026-03-02-s2-s3-signal-compiler-and-gate-v2-a1

## Block identity
- `BLOCK_ID`: SIG-S2-S3-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-s0-s1-signal-manifest-and-hardcode-gate-a1
- `UNLOCKS`: TP-S4 cross-domain-contract-suite

## Название/цель
Закрыть `S2` и `S3`: добавить signal runtime compiler/loader контракт (cache + validation + versioning) и расширить hardcode gate v2 до runtime/core/signal scope с fail-closed блокировкой.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s0-s1-signal-manifest-and-hardcode-gate-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/signal_manifest_service.py`
  - `ops/diagnose.py`
  - `truffles-api/tests/test_signal_manifest_service.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
- `Baseline commands`:
  - `rg -n "load_signal_manifest|lru_cache" truffles-api/app/services/signal_manifest_service.py`
  - `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES|_llm_quality_is_hardcode_core_file" ops/diagnose.py`
- `FACT findings`:
  - signal loader был schema-validated, но без явного runtime compiled-version/meta/fingerprint контракта.
  - hardcode gate v1 покрывал список файлов, но не имел расширенного runtime/core/signal scope policy.

## One web search (mandatory before implementation)
- **Query (exact):** python lru_cache invalidate by key file mtime best practice
- **Date/time (local):** 2026-03-02 09:42, Asia/Almaty
- **Why this query is precise:** нужен детерминированный паттерн кеширования компиляции manifest по file signature для runtime loader.
- **Sources opened (from this query):**
  - Python `functools.lru_cache` docs: https://docs.python.org/3/library/functools.html
  - JSON Schema object reference: https://json-schema.org/understanding-json-schema/reference/object
  - JSON Schema type reference: https://json-schema.org/understanding-json-schema/reference/type
- **Existing solutions found:** компиляция через cache keyed by deterministic file signature + schema validation before compile.
- **Decision:** integrate — compile bundle cached by manifest signature + runtime version meta (`schema_version:fingerprint`), fail on schema/regex compile errors.
- **Rejected options:** cache only by process lifetime without file signature/version metadata.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** signal manifest runtime не имел строгого compiled-version/fingerprint контракта; hardcode gate покрывал только ограниченный список путей.
- **Minimal reproduction:**
  - `rg -n "_llm_quality_is_hardcode_core_file|LLM_QUALITY_HARDCODE_CORE_PREFIXES" ops/diagnose.py`
  - `rg -n "load_signal_manifest|get_signal_regex_pattern" truffles-api/app/services/signal_manifest_service.py`
- **Evidence to capture:** diff, deterministic tests, lint, py_compile.
- **Five Whys (or equivalent):**
  1. Почему S2 считался открытым? — не было versioned compiled bundle контракта.
  2. Почему S3 считался частичным? — scope gate был file-list based без runtime/signal policy scope.
  3. Почему это риск? — drift может пройти между слоями и не быть замечен до expensive acceptance.
  4. Почему это мешает масштабированию? — без compiled-version сложно reproducible forensic по signal behavior.
  5. Почему это нужно сейчас? — это прямой блокер перед S4 cross-domain доказательством.
- **Root cause statement:** отсутствовал явный runtime compiler/versioning contract для signal manifests и fail-closed scope policy в hardcode gate v2.
- **Fix mechanism:** реализовать compiled manifest bundle с signature cache/version meta и расширить gate scope function до runtime/core/signal policy.

## Reuse-first plan (mandatory)
- **Internal reuse:** `jsonschema`/validator patterns из existing services, текущий hardcode-gate в `ops/diagnose.py`.
- **External reuse:** official Python `lru_cache` + JSON Schema references.
- **Why not reinvent the wheel:** расширение существующего loader/gate без нового фреймворка.

## Invariant
- booking/info behavior не должен деградировать.
- gate должен оставаться deterministic и fail-closed на violations в целевом scope.
- никаких новых domain literals в webhook core/runtime.

## Scope
- S2: compiled signal manifest bundle (cache by signature, schema validation, compiled version/fingerprint metadata).
- S3: hardcode gate v2 scope for runtime/core/signal with tests.

## Out of scope
- S4 cross-domain quality suite.
- L3 acceptance run.

## Touch-list
- `truffles-api/app/services/signal_manifest_service.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_signal_manifest_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`

## Plan (1..N)
1. Refactor signal manifest service to compiled bundle API (version/cache/fingerprint).
2. Extend hardcode scope detection in gate v2 (webhook runtime + signal/runtime services).
3. Add deterministic tests for compiled bundle meta/cache and scope policy.
4. Run deterministic verification and record evidence.

## DoD
- `signal_manifest_service` exposes compiled runtime metadata and signature-cache behavior.
- hardcode gate scope includes runtime/core/signal policy paths.
- deterministic tests for S2/S3 are green.

## Checks
- `pytest -q truffles-api/tests/test_signal_manifest_service.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "hardcode_core_gate or line_has_phrase_branching or hardcode_core_scope"`
- `python3 -m py_compile truffles-api/app/services/signal_manifest_service.py ops/diagnose.py`
- `ruff check truffles-api/app/services/signal_manifest_service.py ops/diagnose.py truffles-api/tests/test_signal_manifest_service.py truffles-api/tests/test_booking_quality_status_gate.py`

## Evidence
- Code diff for S2/S3.
- Test/lint/compile outputs from checks.
- Parent TP status update.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** any regression in booking/info deterministic suites
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** local deterministic gate first, then branch CI.
- **Go/no-go signals:** all checks in `Checks` are green.
- **Rollback:** revert commit.
- **Post-release monitoring window:** next S4 prep cycle.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-19-llm-first-firebreak-a1.md`
- `Drift closeout rule`:
  - close in the same block, no deferred TP status drift.

## Rollback
- `git revert <commit>`

## No-go
- Не ослаблять gate scope из-за false positive вместо точечной технической whitelist.
- Не отключать schema validation в signal loader.

## Risks/Blockers
- Scope expansion gate может дать шум в нестабильных diffs; mitigation: strict contextual detector + technical whitelist.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: S4 non-salon cross-domain contract suite still pending.
- `Why not in this block`: это отдельный объём (pack fixtures + quality lanes).
- `Risk if deferred`: масштабируемость останется не доказана quality-evidence.
- `Linked follow-up Task Package(s)`: `TP-S4`.
- `Expiry/trigger to stop deferral`: before acceptance chain promotion for final P7 closure.

## Next-block contract (mandatory)
- `Next block objective`: S4 cross-domain deterministic + quality suite for two non-salon packs.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_cross_domain_capability_isolation.py`
- `Blocked-by conditions`: none after S2/S3 green checks.
- `Owner role for closure`: Brain + Top Architect.
