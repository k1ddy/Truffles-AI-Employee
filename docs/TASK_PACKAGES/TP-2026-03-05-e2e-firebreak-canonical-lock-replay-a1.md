# TP-2026-03-05-e2e-firebreak-canonical-lock-replay-a1

## Название/цель
Выполнить канонический runtime acceptance `lock -> replay` для Block E (`E2e`) на firebreak-on runtime после E2d, чтобы получить однозначный semantic verdict на текущем fingerprint.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: `Block E / E2 runtime evidence`, `Block E / E2c canonical acceptance path`, `Block E / E2d process-unblock`)
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2c-canonical-replay-canary-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2d-acceptance-process-unblock-a1.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`
- `scripts/llm_quality_guarded.sh`

## One web search (mandatory before implementation)
- Query: `Google SRE Workbook canarying releases go no-go signals`
- Date/time (UTC): `2026-03-04T06:43Z`
- Sources opened:
  - `https://sre.google/workbook/canarying-releases/`
- Ready solutions found:
  - Canary/rollout gates must be explicit and attributable (`canary vs control`), otherwise decisions are noisy.
  - Deployment pipeline should stop on bad canary signals and keep rollback path cheap/predictable.
- Decision:
  - `integrate`: run canonical `lock -> replay` as attributable step sequence with strict stop conditions and explicit blocker reasons.
- Rejected alternatives:
  - Параллельные adhoc quality прогоны без chain contract и without comparable artifacts.

## Root cause (mandatory)
- Symptom:
  - До E2d runtime acceptance path зависал на process-gates и не доходил до стабильного `lock -> replay` semantic verdict.
- Minimal reproduction:
  1. Запустить acceptance lock после non-canonical process fail.
  2. Получить `lock_fingerprint_unchanged_after_non_canonical`.
  3. Попытаться через `allow_no_code_delta` и получить `acceptance_disallows_allow_no_code_delta`.
- Evidence:
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r17/summary.json`
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r18/summary.json`
  - `STATE.md` записи по E2c/E2d.
- Five Whys:
  1. Почему не был получен канонический replay? — lock step repeatedly non-canonical/process-invalid.
  2. Почему lock не восстанавливался? — fingerprint unchanged guard блокировал повтор.
  3. Почему нельзя было использовать старый override? — acceptance disallows `allow_no_code_delta`.
  4. Почему это приводило к зацикливанию? — не было узкого recovery-path для process-fail lock.
  5. Что изменилось? — E2d добавил controlled lock-only override.
- Root cause statement:
  - Acceptance chain был blocked process-level контрактом retry; E2d добавил детерминированный recovery-механизм, теперь нужен runtime execution для подтверждения.
- Fix mechanism:
  1. Поднять firebreak runtime на выделенном порту.
  2. Выполнить acceptance lock с `--allow-non-canonical-lock-retry` и strict gates.
  3. Выполнить manual audit lock.
  4. Выполнить acceptance replay от lock artifacts.
  5. Выполнить manual audit replay и зафиксировать canon status/evidence.

## Invariant
- Никакого ослабления acceptance gates (`run_economy`, `quality_constant`, `manual_audit`, `forensic_sla`).
- Никаких semantic hardcode/runtime policy changes в этом блоке.
- Сравниваем только канонические/сопоставимые артефакты.

## Scope
- Runtime execution `lock -> replay` на firebreak runtime.
- Артефакты `/tmp/booking_quality/<run-id>` + canon docs sync.

## Out of scope
- Новые semantic fixes в policy-core.
- Редизайн scenario generation pipeline.

## Touch-list (файлы/таблицы)
- `docs/TASK_PACKAGES/TP-2026-03-05-e2e-firebreak-canonical-lock-replay-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `STATE.md`

## Plan (1..N)
1. Проверить preconditions (`index/latest_by_mode`, chain-state, runtime availability).
2. Запустить firebreak runtime (`127.0.0.1:18184`) с безопасными env overrides.
3. Выполнить acceptance lock (`r22`) с E2d override и strict contract.
4. Выполнить `llm-quality-audit --status done --strict-artifacts` для lock.
5. Выполнить acceptance replay (`r22`) от lock scenarios/baseline.
6. Выполнить `llm-quality-audit` для replay.
7. Обновить `STATE.md` + program TP с итоговым status/evidence.

## Execution result (2026-03-04)
- Step 1-4 выполнены:
  - Firebreak runtime поднят на `http://127.0.0.1:18184` (`LLM_POLICY_CORE_ENABLED=1`, `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=1`, `OTEL_ENABLED=0`, infra URL overrides).
  - Acceptance lock `booking-lock-20260305-firebreak-e2-a1-r22` завершён полностью (`142/142`, duration `3497.87s`) с `infra_valid=true`, `run_integrity.valid=true`, `semantic_valid=false`.
  - Semantic blocking reasons: `calendar_tool_contract_miss=2`, `stale_booking_carryover=1`, `judge_fail=1`.
  - Threshold breaches: `hard_fail_rate=0.0141 (>0.0)`, `degraded_fallback_rate=0.1783 (>0.05)`.
  - Runtime artifact signal: `policy_core_mode=degraded_fallback` on `23` turns with unresolved degrade reason-code (`policy_core_guard=unknown`).
  - Strict audit выполнен: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22 --status done --strict-artifacts` (`artifact_integrity.valid=true`, `manual_audit=done`).
- Step 5 blocked fail-closed:
  - Acceptance replay command returned `chain_step_order_violation:replay:lock` because chain step `lock` is marked `failed` (`/tmp/booking_quality/_chain/20260305-firebreak-e2-a1-r22.json`).
- Итог блока `E2e`: `BLOCKED` по semantic quality contract (не по process/preflight).

## DoD
- Есть runtime artifacts для lock и replay с `summary.json`, `brief.md`, `manual_audit.md/json`, `run_manifest.json`.
- Canon status по E2 обновлен однозначно (`in_progress`/`blocked`/`done`) с reason-codes.
- Никаких отключенных gate/threshold.

### DoD status
- `PARTIAL`: lock artifacts + strict audit — `done`; replay artifacts — `blocked` chain contract (`lock failed`).

## Checks
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-20260305-firebreak-e2-a1-r22 ... --allow-non-canonical-lock-retry`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22 --status done --strict-artifacts`
- `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-20260305-firebreak-e2-a1-r22 ... --reset-before-dialog --fail-on-regression`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-replay-20260305-firebreak-e2-a1-r22 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/*`
- `/tmp/booking_quality/booking-replay-20260305-firebreak-e2-a1-r22/*`
- Updated canon docs (`STATE.md`, program TP)
- `/tmp/booking_quality/_chain/20260305-firebreak-e2-a1-r22.json`

## Release safety (mandatory)
- Rollout strategy: acceptance-only (no production rollout change).
- Go/no-go signals:
  - `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true` for lock/replay.
  - No process-gate violations.
- Rollback:
  - Stop local runtime process and keep previous canon status; no prod path changes.

## Rollback
- Runtime: terminate local `uvicorn` process on `:18184`.
- Docs: revert TP/STATE updates if evidence mapping is incorrect.

## No-go
- Нельзя запускать replay без lock scenarios/baseline.
- Нельзя запускать acceptance с `allow_no_code_delta`.
- Нельзя обновлять baseline по non-canonical run.

## Риски/блокеры
- Индекс `_index/latest_by_mode/lock` currently points to incomplete run and requires explicit guarded override.
- Scenario-generation stage may stall before runtime dialogs.
- Semantic blockers (`r13` classes) may still keep lock/replay non-canonical.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - Semantic split ownership remains in booking-calendar contract path (`tool outcome -> expected_reply/state`).
- Why not in this block:
  - Objective of E2e was runtime verdict after E2d, not semantic refactor.
- Risk if deferred:
  - Continued non-canonical lock, no replay/canary progression, repeated customer-facing booking drift.
- Linked follow-up Task Package(s):
  - `TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1`.
- Expiry/trigger to stop deferral:
  - Any next acceptance lock still reporting `calendar_tool_contract_miss` or `stale_booking_carryover`.

## Next-block contract (mandatory)
- Next block objective:
  - Execute targeted semantic remediation (`E2f`) for `calendar_tool_contract_miss` + `stale_booking_carryover` + degraded fallback budget breach, then rerun acceptance lock.
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_calendar_book_slot_ok_terminal_clear_blocks_followup_expected_reply or policy_collect_interrupt_arbitration_rewrites_master_query_to_info"`
- Blocked-by conditions:
  - Missing deterministic contract tests for `calendar_tool_contract_miss` and stale carryover classes.
  - Missing firebreak runtime/profile alignment for rerun evidence (`:18184` with firebreak flags enabled).
- Owner role for closure:
  - Hands (execution + artifacts), Brain/Top Architect (acceptance sign-off).
