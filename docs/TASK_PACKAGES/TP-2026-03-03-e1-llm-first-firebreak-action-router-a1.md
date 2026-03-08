# TP-2026-03-03-e1-llm-first-firebreak-action-router-a1

## Название/цель
Старт `Block E (LLM-first firebreak)` с безопасного runtime-среза: убрать deterministic semantic override из `_resolve_action` для OOD/escalation/rejection веток и принудительно вести эти turns в `ai_response` (semantic-owner path), сохранив boundary safety и обратимую активацию через env-флаг.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI guardrails deterministic validation after model decision structured outputs`
- **Date/time (local):** `2026-03-03 17:08 UTC`
- **Sources opened:**
  - `https://platform.openai.com/docs/guides/structured-outputs`
  - `https://martinfowler.com/articles/function-call-LLM.html`
- **Found ready solutions:**
  - Schema-first model outputs + deterministic validation at boundary.
  - Keep business semantics in model route, keep deterministic logic for validation/safety/protocol.
- **Decision (`reuse/integrate/build`):** `integrate` — использовать текущий policy-core + boundary-gates, добавить firebreak-переключатель в runtime routing вместо нового orchestration слоя.
- **Rejected options:**
  - Полный одномоментный вырез `_resolve_action` (слишком высокий риск регрессий).
  - Новая параллельная decision-pipeline.

## Root cause (mandatory)
- **Symptom:** core-path в `decision.py` всё ещё принимает semantic решения до/вне policy-core owner (`out_of_domain`, `escalate`, `rejection`).
- **Minimal reproduction:**
  - `rg -n "def _resolve_action|DecisionOutcome\\(\" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "GAP: LLM policy core не реализован в runtime" STATE.md`
- **Evidence:** `_resolve_action` возвращает semantic outcomes на основании deterministic signals; это расходится с LLM-first ownership charter.
- **Five Whys:**
  1. Исторический legacy-router оставался safety net для старых путей.
  2. Policy-core внедрялся инкрементально и не полностью поглотил routing.
  3. Часть semantic outcomes продолжила жить в deterministic ветке.
  4. Это создаёт post-hoc semantic override risk.
  5. Контракт `LLM semantic owner -> deterministic boundary` выполняется частично.
- **Root cause statement:** отсутствовал управляемый firebreak, который блокирует deterministic semantic overrides в core routing без большого-bang рефактора.
- **Fix mechanism:** добавить флаговый `llm_first_firebreak` в `_resolve_action` и перевод semantic override веток в `ai_response` path + trace/meta evidence.

## Invariant
- Не ослаблять LAW/safety/policy gates.
- Не менять default runtime поведение без явной активации флага.
- Не ломать `FACT/COLLECT/HANDOFF` контракт.

## Scope
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- ТЗ/план-обновление под findings A->F.

## Out of scope
- Полный демонтаж legacy routing.
- Новые продуктовые фичи.
- CI/nightly rollout для chaos-lane (идёт отдельным блоком).

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `STATE.md`

## Plan (1..N)
1. Добавить env-gated firebreak toggle для `_resolve_action`.
2. Вынести детектор semantic-override причин в отдельный helper.
3. При firebreak=on маршрутизировать semantic overrides в `ai_response`.
4. Добавить trace/meta observability (`llm_first_firebreak_*`).
5. Добавить deterministic tests: legacy behavior preserved when off; semantic override blocked when on.
6. Обновить ТЗ/plan с зависимостями A->F (status drift, acceptance chain, requirements matrix, CI realism, runtime SLO).

## DoD
- Firebreak-код есть и покрыт тестами.
- Legacy behavior сохраняется при `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=0`.
- При firebreak=on OOD/rejection override не выходят напрямую из `_resolve_action`.
- ТЗ-план синхронизирован с новыми findings и приоритетами.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_first_firebreak_out_of_domain_routes_to_ai_response or llm_first_firebreak_rejection_keeps_legacy_path_when_disabled"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "test_golden_cases or semantic_arbitration_off_keeps_master_without_location_rewrite"`
- `ruff check truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`

## Evidence
- `pytest` outputs (targeted + golden slice).
- `ruff` output.
- Diff with `llm_first_firebreak` meta/trace and helper contracts.

## Release safety (mandatory)
- **Rollout strategy:** feature-flag only (`LLM_POLICY_CORE_LLM_FIRST_FIREBREAK`).
- **Go/no-go signals:** no regression in golden slice + no increase in `unknown_state`/`policy_core_guard` error spikes.
- **Rollback:** disable env flag; revert single patch.
- **Verification:** inspect decision_meta fields `llm_first_firebreak_enabled/applied/reasons` on sampled turns.

## Rollback
- Set `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=0`.
- Revert changes in `decision.py` and tests if needed.

## No-go
- Включать firebreak по умолчанию без runtime canary evidence.
- Подменять firebreakом policy/LAW decisions.
- Объявлять Block E закрытым после одного router-среза.

## Риски/блокеры
- При включении флага возможен сдвиг распределения между `out_of_domain` и `ai_response` путями.
- Нужны runtime acceptance traces до default-enable.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `_resolve_action` всё ещё содержит semantic ветвления (частично нейтрализованы только под firebreak=on).
  - `expected_reply/pending/minimum_data` ещё имеют deterministic precedence в отдельных путях.
- **Why not in this block:**
  - Требуется staged rollout, иначе высокий регрессионный риск.
- **Risk if deferred:**
  - Частичное нарушение semantic-ownership контракта сохраняется.
- **Linked follow-up Task Package(s):**
  - `E2`: `default-on canary` + runtime replay evidence.
  - `E3`: extraction of remaining semantic branches from `_resolve_action`.
  - `A/B/C/D/F`: status canon sync, acceptance chain, requirements matrix, CI realism lane, runtime reliability.
- **Expiry/trigger to stop deferral:**
  - Если canary firebreak stable 48h и replay no-regression green, deferred статус блокируется и `E2` обязателен к запуску.

## Next-block contract (mandatory)
- **Next block objective:** `E2` — включить firebreak в canary и собрать guarded acceptance evidence на lock/replay.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_first_firebreak or semantic_arbitration_off_keeps_master_without_location_rewrite"`
- **Blocked-by conditions:** нет актуального canonical lock/replay/canary пакета на текущем fingerprint с `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK=1`.
- **Owner role for closure:** Brain + Top Architect.

## Execution update (2026-03-03)
- `Status`: `done (E1 slice only)`
- `Implemented`:
  - Added env toggle: `LLM_POLICY_CORE_LLM_FIRST_FIREBREAK`.
  - Added helper `_llm_first_firebreak_semantic_reasons(...)`.
  - `_resolve_action(..., llm_first_firebreak=True)` routes semantic override candidates to `ai_response`.
  - Added decision metadata/trace: `llm_first_firebreak_enabled`, `llm_first_firebreak_applied`, `llm_first_firebreak_reasons`.
  - Added deterministic tests for on/off behavior.
- `Checks`:
  - `2 passed, 270 deselected` (new firebreak tests).
  - `31 passed, 241 deselected` (golden+semantic arbitration slice).
  - `ruff check ...` -> `All checks passed`.
- `E2 forensic continuation (same date, non-canonical evidence)`:
  - Acceptance preflight for firebreak runtime is green (`booking-lock-20260303-firebreak-e2-a1-r5`), but run was interrupted and ended `run_incomplete` (`stop_reason=in_progress`), so no canonical lock evidence in this session.
  - Guarded replay attempts confirmed fail-closed chain behavior (`manual_audit_pending`, `repeat_fingerprint`, `acceptance_count_lt_10`) and required explicit forensic cleanup before reruns.
  - Runtime probe matrix with firebreak env enabled (`/tmp/booking_quality/firebreak_probe_matrix/results.tsv`) showed missing `decision_meta.llm_first_firebreak_*` fields in persisted metadata for OOD/rejection/handoff probes; this is now tracked as an E2 observability gap to close before default-on decisions.
- `E2 observability remediation continuation (same date, local code-fact)`:
  - Added fail-closed meta seeding before routing early-returns (`enqueue_only`/`skip_persist`) in `decision.py` via `_seed_llm_first_firebreak_observability(...)`, so enabled firebreak always stamps inbound `decision_meta`.
  - Promoted `llm_first_firebreak` to critical trace retention stage in `trace.py` to prevent observability loss under trace truncation pressure.
  - Added deterministic regression `test_llm_first_firebreak_enqueue_only_seeds_observability_meta`.
  - Local checks: `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_first_firebreak"` (`3 passed, 270 deselected`), `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_arbitration_off_keeps_master_without_location_rewrite"` (`1 passed, 272 deselected`), `ruff check truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/trace.py truffles-api/tests/test_message_endpoint.py` (`All checks passed`).
