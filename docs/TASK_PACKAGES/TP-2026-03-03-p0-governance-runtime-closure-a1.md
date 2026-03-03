# TP-2026-03-03-p0-governance-runtime-closure-a1

## Block identity
- `BLOCK_ID`: `TP-P0-GOVERNANCE-RUNTIME-CLOSURE-A1`
- `PARENT_BLOCK_ID`: `TP-2026-02-21-consultant-contract-first-remediation-a1`
- `UNLOCKS`: `P0 Governance Lock` (`partial` -> `done`)

## Название/цель
Закрыть `P0 Governance Lock` как `done` через fail-closed runtime evidence governance: единый статус-контур, однозначные причины блокировки и каноничное handoff-доказательство для merge/acceptance.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `.github/workflows/ci.yml`

## One web search (mandatory before implementation)
- **Query (exact):** `GitHub Actions required status checks branch protection fail closed workflow design`
- **Date/time (local):** `2026-03-03 11:00 Asia/Almaty`
- **Sources opened (from this query):**
  - `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches`
  - `https://docs.github.com/en/actions/using-workflows/about-workflows`
- **Decision:** reuse existing branch-protection and required-checks pattern; integrate status normalization into existing gate scripts/workflows.
- **Rejected options:** отдельный параллельный governance pipeline без связи с текущим chain-controller.

## Root cause (mandatory)
- **Symptom:** `P0` помечен `partial`, потому что есть кодовые гейты, но нет формально закрытого runtime-evidence контура для governance closure.
- **Minimal reproduction:**
  - `rg -n "P0 Governance Lock" docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `rg -n "llm-quality-gates|manual_audit_not_done|evidence_handoff" .github/workflows/ci.yml scripts/session_check.sh ops/diagnose.py`
- **Evidence:** статические/локальные проверки есть; статус-матрица и закрытие по runtime evidence не сведены в один closure-контракт.
- **Five Whys (or equivalent):**
  1. Гейты развивались по частям (CI, session_check, diagnose).
  2. Единый closure-критерий `P0 done` не зафиксирован как machine-checkable пакет.
  3. Из-за этого статус остается `partial` даже при наличии кода.
  4. Команда и агенты читают разные источники статуса.
  5. Возникает процессный дрейф и повторные обсуждения вместо детерминированного closure.
- **Root cause statement:** нет единого fail-closed runtime closure-контракта для governance-блока.
- **Fix mechanism:** добавить единый governance closure digest + machine-check условий `done` + обновление parent TP/STATE по факту.

## Reuse-first plan (mandatory)
- **Internal reuse:** `ops/diagnose.py` quality statuses, `scripts/session_check.sh`, `.github/workflows/ci.yml` required checks.
- **External reuse:** GitHub protected branches/required checks best practices (официальные docs).
- **Why reuse first:** все ключевые механизмы уже есть; нужен нормализующий слой и closure-контракт, а не новая система.

## Business flow impact
- Governance становится прозрачным для Brain/Top Architect: ясно, когда блок действительно закрыт и можно двигаться к следующему бизнес-блоку.

## Operator UX impact
- Один понятный статус по `P0` без ручной сверки нескольких файлов и разнотолков в handoff.

## Duplicate-surface audit
- Не создавать новый governance runner.
- Использовать существующие `ops/diagnose.py` + `session_check.sh` + CI required checks.

## Invariant
- Не ослаблять текущие fail-closed quality gates.
- Не вводить bypass-пути для acceptance lane.
- Не менять бизнес-контракт `FACT/COLLECT/HANDOFF`.

## Scope
- Нормализовать `P0` closure-критерий в machine-checkable форму.
- Добавить явный `governance_closure_status` в quality summary/evidence digest.
- Зафиксировать rule: без closure evidence `P0` не может быть `done`.
- Обновить parent TP статус по факту выполнения.

## Out of scope
- Изменения в semantic policy-core логике.
- Любые новые runtime-продуктовые фичи.

## Touch-list
- `ops/diagnose.py`
- `scripts/session_check.sh`
- `.github/workflows/ci.yml`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Описать и закодировать единый `governance_closure_status` (valid/reasons/evidence paths).
2. Добавить fail-closed проверку closure в `session_check.sh` и CI gate.
3. Добавить deterministic tests на positive/negative closure cases.
4. Обновить parent TP: `P0` -> `done` только после green evidence.

## DoD
- `P0` переводится в `done` только при machine-checkable closure status.
- Session/CI блокируют merge при невалидном governance closure.
- Есть deterministic тесты и green results.
- Parent TP и `STATE.md` обновлены фактами и artifact paths.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "governance or closure or handoff"`
- `bash -n scripts/session_check.sh`
- `python3 ops/diagnose.py llm-quality-gates --help`
- `rg -n "governance_closure_status|p0_governance" ops/diagnose.py scripts/session_check.sh`

## Evidence
- test outputs (deterministic)
- updated gate output snippet with `governance_closure_status`
- parent TP diff + `STATE.md` entry with exact evidence paths

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (doc+deterministic/process block)
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** любой fail в gate/test
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive process hardening with fail-closed defaults.
- **Go/no-go signals:** session_check and CI governance gate both green.
- **Rollback:** revert governance closure commits.
- **Post-release monitoring window:** next 48h all related PRs must show stable governance closure signals.

## Rollback
- Revert changes in `ops/diagnose.py`, `scripts/session_check.sh`, `.github/workflows/ci.yml`.
- Restore parent TP status to `partial` if closure conditions break.

## No-go
- Отмечать `P0 done` без runtime closure evidence.
- Добавлять новый governance pipeline вместо reuse существующих gate layers.

## Risks/Blockers
- Возможен конфликт legacy сессий при строгом closure enforcement.
- Потребуется точная backward-compatible формулировка статусов.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: закрыть Stage D taxonomy sync после стабилизации P0 closure.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "scenario_governance"`
- `Blocked-by conditions`: governance closure status not green.
- `Owner role for closure`: Brain + Top Architect.
