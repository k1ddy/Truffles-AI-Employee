# TP-2026-03-03-stage-d-scenario-taxonomy-sync-a1

## Block identity
- `BLOCK_ID`: `TP-STAGE-D-SCENARIO-TAXONOMY-SYNC-A1`
- `PARENT_BLOCK_ID`: `TP-2026-02-21-consultant-contract-first-remediation-a1`
- `UNLOCKS`: `Stage D Scenario Governance` (`partial` -> `done`)

## Название/цель
Синхронизировать бизнес-таксономию сценариев (`production-like`, `expert-hard`, `chaos/noise`) с runtime enforcement в quality-gates, чтобы Stage D закрывался по фактам и без расхождений терминов между ТЗ, кодом и runbook.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`

## One web search (mandatory before implementation)
- **Query (exact):** `NIST stress testing evaluation scenarios taxonomy production like hard cases`
- **Date/time (local):** `2026-03-03 11:05 Asia/Almaty`
- **Sources opened (from this query):**
  - `https://www.nist.gov/itl/ai-risk-management-framework`
  - `https://owasp.org/www-project-cloud-tenant-isolation/`
- **Decision:** интегрировать бизнес taxonomy в существующий scenario governance registry как versioned mapping, без нового параллельного механизма.
- **Rejected options:** хранить taxonomy только в документации без machine enforcement.

## Root cause (mandatory)
- **Symptom:** в ТЗ Stage D требует `production-like/expert-hard/chaos-noise`, а runtime gate валидирует другой набор токенов (`booking/info/interrupt/handoff`).
- **Minimal reproduction:**
  - `rg -n "production-like|expert hard cases|chaos/noise" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `rg -n "LLM_QUALITY_SCENARIO_REALISM_REQUIRED_BUCKETS" ops/diagnose.py`
- **Evidence:** терминология и runtime check-лист расходятся.
- **Five Whys (or equivalent):**
  1. Изначально quality coverage делалась на intent-токенах.
  2. Позже в ТЗ добавили бизнес buckets Stage D.
  3. Явный mapping не был добавлен в код.
  4. Из-за этого формально Stage D нельзя считать закрытым.
  5. Появляется риск неверной интерпретации acceptance-ready статуса.
- **Root cause statement:** отсутствует versioned taxonomy mapping между бизнес buckets и runtime coverage enforcement.
- **Fix mechanism:** добавить taxonomy mapping в scenario governance status/registry и покрыть deterministic tests + runbook sync.

## Reuse-first plan (mandatory)
- **Internal reuse:** `_llm_quality_build_scenario_contract_status`, `_llm_quality_build_scenario_realism_sla`, scenario governance registry.
- **External reuse:** NIST/OWASP guidance для risk-based scenario categorization.
- **Why reuse first:** текущий governance pipeline уже реализован; нужно расширить его контракт, а не добавлять новый контур.

## Business flow impact
- Бизнес получает понятный ответ, что acceptance сценарии действительно покрывают реальные клиентские условия, сложные кейсы и шум.

## Operator UX impact
- Оператор видит в summary/registry не только технические coverage tokens, но и бизнес-бакеты, понятные без чтения кода.

## Duplicate-surface audit
- Не создавать отдельный taxonomy storage.
- Расширить текущий scenario registry и quality summary.

## Invariant
- Не ослаблять `infra_valid/semantic_valid/run_integrity_valid`.
- Не отключать существующие coverage tokens; добавить mapping поверх.
- Не ломать `lock -> replay -> canary -> full` цепочку.

## Scope
- Добавить `taxonomy_mapping_version` и `business_bucket_presence` в scenario governance.
- Сделать fail-closed check для acceptance, если отсутствуют обязательные business buckets.
- Обновить runbook с одним каноничным описанием taxonomy.
- Обновить parent TP статус Stage D по факту.

## Out of scope
- Новые продуктовые домены.
- Изменение бизнес-порогов качества вне taxonomy синка.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Ввести versioned mapping: runtime tokens -> business buckets.
2. Добавить fail-closed validation бизнес buckets в scenario governance gate для acceptance.
3. Добавить/обновить deterministic tests для positive/negative cases.
4. Синхронизировать runbook и parent TP статус Stage D.

## DoD
- В acceptance governance есть machine-check `business_bucket_presence` по требуемым buckets.
- Stage D закрывается по deterministic evidence, без терминологических расхождений.
- Runbook и parent TP синхронизированы с кодом.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "scenario_governance or realism"`
- `python3 ops/diagnose.py llm-quality --help | rg -n "scenario-governance"`
- `rg -n "taxonomy|business_bucket|realism_sla" ops/diagnose.py docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Evidence
- deterministic test outputs
- summary/registry snippets with new taxonomy fields
- parent TP + runbook diffs

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (deterministic/process block)
- **Fail-fast / scenario lock:** deterministic checks only
- **Stop condition:** первый failing taxonomy gate test
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive compatibility (old tokens preserved, new business mapping enforced).
- **Go/no-go signals:** all scenario governance deterministic tests green.
- **Rollback:** revert taxonomy-mapping commits.
- **Post-release monitoring window:** next 48h acceptance summaries checked for `business_bucket_presence` fields.

## Rollback
- Revert changes in `ops/diagnose.py`, tests, runbook.
- Restore previous scenario governance behavior.

## No-go
- Закрывать Stage D только на doc-level формулировках.
- Убирать существующие runtime coverage checks.

## Risks/Blockers
- Неправильный mapping может давать false-negative в acceptance.
- Нужна точная backward-compatibility для уже сохраненного registry.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: закрыть secret-safe transport fail-closed gate.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "secret"`
- `Blocked-by conditions`: taxonomy sync not merged.
- `Owner role for closure`: Brain + Top Architect.
