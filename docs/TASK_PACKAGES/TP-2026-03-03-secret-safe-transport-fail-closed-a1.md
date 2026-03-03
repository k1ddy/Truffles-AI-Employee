# TP-2026-03-03-secret-safe-transport-fail-closed-a1

## Block identity
- `BLOCK_ID`: `TP-SECRET-SAFE-TRANSPORT-FAIL-CLOSED-A1`
- `PARENT_BLOCK_ID`: `TP-2026-02-21-consultant-contract-first-remediation-a1`
- `UNLOCKS`: `Secret-safe transport gate` (`partial` -> `done`)

## Название/цель
Довести secret-safe transport до fail-closed контракта: автоматическое обнаружение секретов в argv/командах/артефактах и блокировка quality-run с явным reason-code (`secret_exposure_detected`).

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `ops/diagnose.py`
- `scripts/llm_quality_guarded.sh`

## One web search (mandatory before implementation)
- **Query (exact):** `OWASP sensitive data exposure command line arguments secrets process list`
- **Date/time (local):** `2026-03-03 11:10 Asia/Almaty`
- **Sources opened (from this query):**
  - `https://owasp.org/www-project-top-ten/`
  - `https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html`
- **Decision:** интегрировать секрет-detector в существующий runtime gate pipeline и переводить риск в fail-closed blocker.
- **Rejected options:** оставлять только redact/sanitize без блокирующего статуса.

## Root cause (mandatory)
- **Symptom:** есть redaction/sanitize, но нет явного fail-closed gate class для секрет-экспозиции.
- **Minimal reproduction:**
  - `rg -n "_sanitize_command_for_logging|redacted|webhook-secret" ops/diagnose.py`
  - `rg -n "secret_exposure_detected" ops/diagnose.py truffles-api/tests`
- **Evidence:** в коде присутствует санитизация, но отсутствует отдельный blocking reason-code и end-to-end test на его срабатывание.
- **Five Whys (or equivalent):**
  1. Сначала закрывали утечки через redact в логах.
  2. Не добавили отдельную классификацию инцидента как blocker.
  3. Без blocker-класса процесс не fail-closed.
  4. Риск может быть замечен постфактум, не до acceptance.
  5. Требование ТЗ о secret-safe gate остается partial.
- **Root cause statement:** отсутствует machine-enforced reason-code и gate path для детекта секрета в transport/argv контуре.
- **Fix mechanism:** добавить detector + `secret_exposure_detected` reason + blocking_counts integration + deterministic tests.

## Reuse-first plan (mandatory)
- **Internal reuse:** command sanitizer, preflight and blocking-reasons framework в `ops/diagnose.py`.
- **External reuse:** OWASP Secrets Management guidance.
- **Why reuse first:** существующий gate framework готов; нужен дополнительный detector и wire-up, а не новый subsystem.

## Business flow impact
- Снижает риск инцидентов утечки секретов в CI/quality артефактах, что напрямую влияет на надежность и доверие бизнеса.

## Operator UX impact
- Понятная и однозначная причина блокировки (`secret_exposure_detected`) вместо неявных предупреждений в логах.

## Duplicate-surface audit
- Не вводить отдельный external scanner.
- Использовать текущие preflight/status gate механизмы.

## Invariant
- Не ослаблять существующие security/preflight gates.
- Не ломать совместимость текущих run commands.
- Не менять бизнес-логику диалогов.

## Scope
- Добавить fail-closed detector для секретов в argv/command artifacts.
- Добавить reason-code `secret_exposure_detected` в blocking reasons taxonomy.
- Сделать gate mandatory в acceptance lane.
- Покрыть deterministic tests и обновить parent TP статус.

## Out of scope
- Полная DLP-платформа.
- Секрет-сканирование всего репозитория вне runtime-gate контекста.

## Touch-list
- `ops/diagnose.py`
- `scripts/llm_quality_guarded.sh`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить detector и reason-code `secret_exposure_detected` в status taxonomy.
2. Встроить detector в preflight/runtime summary как fail-closed.
3. Добавить deterministic tests на detector positive/negative.
4. Обновить parent TP и `STATE.md` по факту.

## DoD
- Есть явный reason-code `secret_exposure_detected` в quality status.
- При детекте секрета acceptance run блокируется fail-closed.
- Deterministic tests green.
- Parent TP и `STATE.md` обновлены фактическим evidence.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "secret or webhook_secret_preflight"`
- `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `rg -n "secret_exposure_detected|sanitize|redact" ops/diagnose.py`

## Evidence
- deterministic test outputs
- sample summary with blocking reason `secret_exposure_detected`
- parent TP status update with evidence paths

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (deterministic/security gate block)
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** любой failed security-gate test
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive fail-closed security gate over existing runner.
- **Go/no-go signals:** security gate tests green, no regression in guarded wrapper.
- **Rollback:** revert detector/reason-code commits.
- **Post-release monitoring window:** next 48h verify no false-positive spike in security gate blocks.

## Rollback
- Revert changes in `ops/diagnose.py`, wrapper and tests.
- Return to redact-only behavior (temporary rollback only by explicit decision).

## No-go
- Ограничиться только маскированием без blocking reason.
- Подавлять секрет-детект в acceptance lane.

## Risks/Blockers
- Риск false-positive при грубых regex/heuristics.
- Нужен аккуратный allowlist для технически безопасных параметров.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Next-block contract (mandatory)
- `Next block objective`: закрыть `P12` после наличия двух runtime non-salon onboardings.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `Blocked-by conditions`: no two real runtime non-salon domains.
- `Owner role for closure`: Brain + Top Architect.
