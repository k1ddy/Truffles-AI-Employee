# TP-2026-03-02-p12-cross-domain-hardening-full-closure-a1

## Block identity
- `BLOCK_ID`: SIG-P12-CROSS-DOMAIN-HARDENING-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-p5b-distributed-retrieval-backend-a1
- `UNLOCKS`: `P12 Cross-domain Hardening` -> `done`

## Название/цель
Полностью закрыть `P12`: подтвердить масштабируемость contract-first поведения минимум на двух non-salon domains в deterministic и quality-контурах с fail-closed gate в acceptance chain.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
  - `ops/diagnose.py`
  - `scripts/llm_quality_guarded.sh`
  - domain packs in `truffles-api/app/knowledge/**`
- `Baseline commands`:
  - `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
  - `rg -n "cross-domain-contract|cross_domain_matrix_contract" ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`
  - `rg -n "demo_salon" truffles-api/app/knowledge truffles-api/tests`
- `FACT findings`:
  - deterministic non-salon contract suite существует.
  - quality tooling имеет cross-domain gate (`off|warn|block`).
  - live/acceptance evidence по двум non-salon domains не зафиксирован как done.
- `Detected drift (docs vs code)`: parent TP фиксирует `P12 partial`.

## One web search (mandatory before implementation)
- **Query (exact):** `OWASP SaaS tenant isolation testing strategy multi-tenant`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** нужен reference для tenant/domain isolation checks в multi-tenant системах.
- **Sources opened (from this query):**
  - OWASP Cloud Tenant Isolation project: `https://owasp.org/www-project-cloud-tenant-isolation/`
  - AWS SaaS tenant isolation whitepaper: `https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.html`
- **Existing solutions found:** fail-closed isolation checks + representative multi-tenant test matrix.
- **Decision:** `integrate` cross-domain contract matrix + acceptance gate by explicit min non-salon domains.
- **Rejected options:** validation только на `demo_salon`.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** `P12` остается partial, потому что нет полного quality evidence для двух non-salon domains.
- **Minimal reproduction:**
  - `rg -n "P12 Cross-domain Hardening" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `scripts/quality_artifact_report.py --hours 72 --show-commands`
- **Evidence to capture:** deterministic + acceptance artifacts по двум non-salon domains.
- **Five Whys (or equivalent):**
  1. Исторически acceptance цепочка строилась вокруг `demo_salon`.
  2. Domain-agnostic intent подтвержден частично, но runtime evidence неполный.
  3. Без non-salon acceptance нет доказанной масштабируемости.
  4. Без explicit domain matrix gate возможны скрытые regressions.
  5. Поэтому `P12` нельзя закрыть без полного cross-domain evidence.
- **Root cause statement:** acceptance evidence не покрывает минимум два non-salon domains end-to-end.
- **Fix mechanism:** добавить и enforce двухдоменную cross-domain matrix в deterministic + guarded acceptance.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing cross-domain tests, quality gate args, guarded chain controller.
- **External reuse:** tenant isolation validation patterns from OWASP/AWS guidance.
- **Why not reinvent the wheel:** нужные gate primitives уже реализованы.

## Invariant
- `demo_salon` остается канарейкой, но не единственным domain.
- Contract gates остаются fail-closed.
- Никаких domain hardcode в runtime/core.

## Scope
- Зафиксировать два non-salon domains для качества:
  - если есть реальные slugs: использовать их.
  - если нет: добавить два canonical reference packs в repo (`demo_dental`, `demo_auto`) с production-like datasets.
- Расширить deterministic suite и acceptance matrix на оба domains.
- Сделать cross-domain gate обязательным для acceptance (`block`).
- Обновить docs/state с evidence.

## Out of scope
- Продакшн rollout новых коммерческих клиентов.
- UI features.

## Touch-list
- `truffles-api/app/knowledge/<non-salon-pack-1>/**` (new or existing)
- `truffles-api/app/knowledge/<non-salon-pack-2>/**` (new or existing)
- `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `ops/diagnose.py`
- `scripts/llm_quality_guarded.sh`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Определить и зафиксировать 2 non-salon domains (real slugs или canonical reference packs).
2. Довести deterministic contract suite для обоих domains.
3. Включить fail-closed cross-domain matrix gate в acceptance entrypoint.
4. Выполнить guarded acceptance artifacts для обоих domains.
5. Обновить parent TP и `STATE.md` с фактическими артефактами.

## DoD
- Есть минимум 2 non-salon domains в deterministic и acceptance evidence.
- Cross-domain gate в acceptance работает в `block` режиме.
- Parent TP: `P12` -> `done`.

## Checks
- `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "cross_domain"`
- `scripts/llm_quality_guarded.sh --mode lock --run-id p12-cross-domain-lock -- --client-slug <non-salon-1> --cross-domain-contract block`
- `scripts/llm_quality_guarded.sh --mode replay --run-id p12-cross-domain-replay -- --client-slug <non-salon-2> --cross-domain-contract block`

## Evidence
- deterministic test outputs.
- acceptance artifacts (`summary.json`, `brief.md`, `run_manifest.json`) for both non-salon domains.
- parent TP + `STATE.md` updates with exact run paths.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` (one per non-salon domain)
- **Fail-fast / scenario lock:** lock/replay only, canonical params fixed
- **Stop condition:** first non-canonical/invalid run
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic-first, then guarded acceptance with cross-domain block gate.
- **Go/no-go signals:** valid infra/semantic/integrity for both non-salon domains.
- **Rollback:** revert domain pack/test changes.
- **Post-release monitoring window:** next 48h quality runs include both non-salon domains.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` (if matrix command changes)
- `Drift closeout rule`:
  - `P12` не закрывается без artifacts по двум non-salon domains.

## Rollback
- Revert commit(ы) и выключить cross-domain block gate только через explicit TP decision.

## No-go
- Объявлять `P12 done` по одному домену.
- Использовать только `demo_salon` как доказательство масштабируемости.
- Ослаблять gate до `warn` для acceptance closure.

## Risks/Blockers
- Отсутствие готовых non-salon slugs/данных.
- Увеличение времени acceptance matrix.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: keep `P12` blocked until two real runtime non-salon domains are explicitly onboarded for guarded acceptance.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `Blocked-by conditions`: missing runtime onboarding dataset/slug pair for two non-salon domains.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: decision on runtime onboarding scope for two non-salon domains, then guarded acceptance plan.
- `Do not touch`: policy-core behavior logic.
- `Open risks`: missing runtime non-salon onboarding keeps `P12` open/blocked.
- `First command to verify`: `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`.

## Execution status (2026-03-02)
- `Status`: `blocked` (business deferral: no runtime onboarding of two non-salon domains in current cycle)
- `Implementation facts`:
  - Added canonical non-salon reference packs:
    - `truffles-api/app/knowledge/clinic_pack/SALON_TRUTH.yaml`
    - `truffles-api/app/knowledge/dental_pack/SALON_TRUTH.yaml`
  - Added pack docs:
    - `truffles-api/app/knowledge/clinic_pack/README.md`
    - `truffles-api/app/knowledge/dental_pack/README.md`
  - Updated cross-domain deterministic suite to use real pack slugs/data from repository (removed inline runtime-truth injection):
    - `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `Deterministic evidence`:
  - `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py` (included in packet run; green).
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "cross_domain_matrix_contract"` (`3 passed, 74 deselected`).
  - `ruff check truffles-api/tests/test_cross_domain_signal_contract_suite.py` (green inside packet lint run).
- `Block reason`:
  - Current execution cycle does not onboard two real runtime non-salon domains; therefore required guarded acceptance artifacts cannot be produced.
- `Unblock conditions`:
  - Onboard two real runtime non-salon domains (slug + runtime data readiness).
  - Run guarded acceptance artifacts for both domains with valid `infra_valid/semantic_valid/run_integrity_valid/manual_audit`.
  - Update parent TP + `STATE.md` with concrete artifact paths.
