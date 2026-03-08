# TP-2026-02-21-consultant-contract-first-remediation-a1

- Название/цель: P1 re-open и доведение `Single Semantic Owner` до полного, fail-closed, tenant/branch-aware, capability-scoped, multilingual-safe business-agnostic состояния без semantic rewrite в runtime path.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- STATE refs: GAP по semantic ownership, fact-evidence linkage, booking commit contract, process-trust quality chain.
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Status Reset (binding, 2026-03-05)

- Все ранние секции/матрицы с `done/all done` в этом TP считаются историческим архивом и не являются acceptance-истиной.
- Активный статус:
  - `P1 Single Semantic Owner`: `re-open`.
  - Rollout (`canary/full`): `STOP-THE-LINE` до полного closure P1 + обязательного локального realism контура.
  - `P1.6` promotion discovery loop: `budget-blocked after latest evidence`; новые дорогие `dev/acceptance` quality run не являются default dev-loop до следующего acceptance window.
  - Current execution focus: `P1.6o16 pending-question interaction model gap (doc-first rescope before code)`; guarded rerun `p1.6o6-l2-dev-20260308-a1-r11` is audited but non-admissible (`infra_valid=false`, `semantic_valid=false`) and surfaced the next semantic family on `На какое время лучше записаться?`, which proved a broader documentation/process gap around active pending-question interaction semantics, so no new expensive `dev L2` action is allowed until `docs/TASK_PACKAGES/TP-2026-03-08-p1.6o16-booking-time-guidance-question-owner-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-p1.6o-demo-salon-architecture-closure-program-a1.md`, and `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` are synced on the doc-first contract and the bounded runtime child slice is explicit.
- Форензика состояния chain:
  - `/tmp/booking_quality/_chain/20260305-firebreak-e2e3-a1-r33.json` -> `blocked_reason=canary_rollback_executed`.
  - `/tmp/booking_quality/booking-canary-20260305-firebreak-e2e3-a1-r33/rollback.json` -> `status=executed`, `source=auto_canary_no_go`.

## Architecture Clarification (binding)

- `business-agnostic` в этом TP означает:
  - runtime-core не знает заранее конкретную нишу, филиал и набор услуг;
  - tenant/branch различия живут в `packs`, `policy`, `capabilities`, `runtime manifests`;
  - доступные tools определяются capability/protocol boundary для конкретного tenant/branch, а не core hardcode;
  - semantic-owner должен выдерживать разные языки и code-switching без отдельного keyword-router как основного механизма;
  - `demo_salon` используется как acceptance canary-pack, а не как модель мира для core.
- Следствие:
  - любой фикс, который улучшает поведение только под текущий pack/лексикон/язык и не переносит знание в data/config/capability layer, считается неполным.

## Process Gap Clarification (binding)

- `P1.6o1`..`P1.6o15` закрывали semantic ownership по осям `aboutness/state/referent/capability/oracle`, но не заморозили отдельную ось `interaction over active pending question`.
- Следствие: expensive guarded loop честно находил новые семьи, но оставался реактивным — surfaced family reopening worked as a truthfulness gate, not as a completeness gate.
- `P6A/P6B` расширяли surface coverage (`translit/typo/paraphrase/format/context-aware synthesis`), но сохраняли существующую scenario ontology (`tags/expect`); поэтому они не могли заранее поймать класс, которого не было в taxonomy/TP contract.
- До синхронизации docs/runbook/taxonomy любой узкий фикс вида `одна фраза -> один owner` считается process-incomplete даже если он локально green на deterministic contour.

## Atomic Sub-TP Matrix (binding)

| Block | Sub-TP | Status | Closure mode |
|---|---|---|---|
| `P1.1 Remove semantic rewrite runtime paths` | `docs/TASK_PACKAGES/TP-2026-03-05-p1.1-single-owner-rewrite-removal-a1.md` | `done` | code + mandatory deterministic checks |
| `P1.2a Remove phrase/token routing in policy info arbitration` | `docs/TASK_PACKAGES/TP-2026-03-05-p1.2a-core-phrase-routing-removal-a1.md` | `done` | code + contract tests |
| `P1.2b Remove remaining phrase routing in tool-response arbitration` | `docs/TASK_PACKAGES/TP-2026-03-05-p1.2b-tool-response-phrase-routing-removal-a1.md` | `done` | code + contract tests |
| `P1.3a Deterministic hard lock dead-rewrite removal` | `docs/TASK_PACKAGES/TP-2026-03-05-p1.3a-boundary-hardlock-dead-rewrite-removal-a1.md` | `done` | code + deterministic pack |
| `P1.3b Acceptance semantic override gate` | `docs/TASK_PACKAGES/TP-2026-03-05-p1.3b-acceptance-semantic-override-gate-a1.md` | `done` | quality-gate + evidence |
| `P1.4 LLM tool hint hardcode removal` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.4-llm-tool-hint-hardcode-removal-a1.md` | `done` | code + contract tests |
| `P1.5 Remove post-plan semantic rescue paths` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.5-post-plan-semantic-rescue-removal-a1.md` | `done` | code + contract tests |
| `P1.5b Single-owner contract suite realignment` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.5b-booking-interrupt-info-owner-protection-a1.md` | `done` | test contract realignment |
| `P1.5c Booking interrupt plan-conflict fail-closed` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.5c-booking-interrupt-plan-conflict-fail-closed-a1.md` | `done` | code + contract tests |
| `P1.6 Local realism + canonical acceptance lock` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6-local-realism-canonical-lock-a1.md` | `budget-blocked` | realism + fresh lock evidence |
| `P1.6o Demo-salon architecture closure program` | `docs/TASK_PACKAGES/TP-2026-03-07-p1.6o-demo-salon-architecture-closure-program-a1.md` | `in_progress` | program stays open until all known blocker families and any newly surfaced family are closed and the full proof bundle (`deterministic -> dev L2 -> lock -> replay -> audit`) is green |
| `P1.6a Policy-core structured-output compatibility` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6a-policy-core-structured-output-compat-a1.md` | `done` | code + runtime probe |
| `P1.6b Info followup hardcode removal` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6b-info-followup-hardcode-removal-a1.md` | `done` | code + targeted contract tests |
| `P1.6c Pre-lock readiness envelope` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6c-pre-lock-readiness-envelope-a1.md` | `done` | L1/L2 evidence + blocker extraction before guarded lock |
| `P1.6d Timeout-degrade fallback hardening` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6d-timeout-degrade-fallback-hardening-a1.md` | `done` | code + targeted timeout fallback tests + fresh dev L2 blocker rollover |
| `P1.6e Booking-active master_query pack enforcement` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6e-booking-master-query-pack-enforcement-a1.md` | `done` | code + contract realignment for master-query under booking |
| `P1.6f Master-availability query ownership` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6f-master-availability-query-ownership-a1.md` | `done` | prompt + resolver + contract + live probe |
| `P1.6g Reused-handover pending snapshot parity` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6g-reused-handover-context-capture-a1.md` | `done` | code + deterministic contract tests |
| `P1.6h Partial-datetime slot completeness parity` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6h-partial-datetime-slot-completeness-parity-a1.md` | `done` | prompt + policy memory/profile + deterministic booking completeness alignment |
| `P1.6i Booking collect slot-order invariant` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6i-booking-collect-slot-order-invariant-a1.md` | `done` | deterministic validator + fail-closed earliest-slot prompt + targeted regressions |
| `P1.6j Booking confirmation priority over policy-core degrade` | `docs/TASK_PACKAGES/TP-2026-03-06-p1.6j-booking-confirmation-priority-over-policy-core-degrade-a1.md` | `done` | policy-core guard + trace/meta + targeted confirmation regression |
| `P1.6k Demo-salon release-lane cleanup after budget stop` | `docs/TASK_PACKAGES/TP-2026-03-07-p1.6k-demo-salon-release-lane-cleanup-a1.md` | `done` | cleanup lane is green again on deterministic contour; `E508` closed; next action is one fresh guarded `demo_salon` dev L2 |
| `P1.6l LLM policy-core message-endpoint family closure` | `docs/TASK_PACKAGES/TP-2026-03-07-p1.6l-llm-policy-core-message-endpoint-family-a1.md` | `done` | real runtime gaps (`calendar.* fact_guard`, `person_service_signal`) closed; full `message_endpoint` green before fresh `demo_salon` dev L2 |
| `P1.6m Booking expected-reply alternate-slot capture under stale question state` | `docs/TASK_PACKAGES/TP-2026-03-07-p1.6m-booking-expected-reply-alternate-slot-capture-a1.md` | `done` | question-contract now preserves validated alternate booking slot answers under stale expected-reply state; next action returns to one fresh guarded `demo_salon` dev L2 |
| `P1.6n Weekend-availability service-referent arbitration` | `docs/TASK_PACKAGES/TP-2026-03-07-p1.6n-weekend-availability-service-referent-arbitration-a1.md` | `queued under P1.6o2/P1.6o3` | `r22` remains the first open family, but its closure now depends on the program-level semantic envelope + dialog-state + referent resolver slices |
| `P1.7 Acceptance replay + regression gate` | `TBD (create before start)` | `pending` | replay evidence |
| `P3.1 Booking commit contact minimum fail-closed` | `docs/TASK_PACKAGES/TP-2026-03-06-p3.1-book-slot-contact-minimum-fail-closed-a1.md` | `done` | no appointment create without resolved name+phone |
| `P3.1r Demo-salon booking contact evidence contract parity` | `docs/TASK_PACKAGES/TP-2026-03-07-p3.1r-demo-salon-booking-contact-evidence-contract-a1.md` | `done` | success meta/trace now records contact sources, quality guard accepts valid profile-name + remote-jid phone evidence, next action returns to one fresh guarded `demo_salon` dev L2 |
| `P3.2 Booking create transactional write boundary` | `docs/TASK_PACKAGES/TP-2026-03-06-p3.2-booking-create-transaction-boundary-a1.md` | `done` | appointment + outbox + reminders + profile sync share one write boundary |
| `P3.3 Booking mutation transactional parity` | `docs/TASK_PACKAGES/TP-2026-03-06-p3.3-booking-mutation-transaction-parity-a1.md` | `done` | reschedule/cancel mutation writes no longer commit independently |
| `P4.1 FACT evidence linkage fail-closed` | `docs/TASK_PACKAGES/TP-2026-03-06-p4.1-fact-evidence-linkage-fail-closed-a1.md` | `done` | no FACT without valid evidence linkage |
| `P5.1 Invariant quality gates blocking` | `docs/TASK_PACKAGES/TP-2026-03-06-p5.1-invariant-quality-gates-blocking-a1.md` | `done` | branch progression blocked on invariant regressions, not only case-list failures |
| `P6.1 Open-world scenario generator metamorphic coverage` | `docs/TASK_PACKAGES/TP-2026-03-06-p6.1-open-world-scenario-generator-metamorphic-coverage-a1.md` | `done` | deterministic generator produces multilingual/code-switch surface variants without new core hardcode |
| `P6.2 Open-world translit code-switch coverage` | `docs/TASK_PACKAGES/TP-2026-03-06-p6.2-open-world-translit-code-switch-coverage-a1.md` | `done` | deterministic generator produces Cyrillic/Latin mixed-script variants without changing tags/expect |
| `P6.3 Open-world typo surface coverage` | `docs/TASK_PACKAGES/TP-2026-03-06-p6.3-open-world-typo-surface-coverage-a1.md` | `done` | deterministic generator produces typo/noisy surface variants without changing tags/expect |
| `P6.4 Open-world paraphrase synonym coverage` | `docs/TASK_PACKAGES/TP-2026-03-06-p6.4-open-world-paraphrase-synonym-coverage-a1.md` | `done` | deterministic generator adds semantic-equivalent paraphrase families beyond language/script/noise axes |
| `P6.5 Open-world slot-format mutation coverage` | `docs/TASK_PACKAGES/TP-2026-03-06-p6.5-open-world-slot-format-mutation-coverage-a1.md` | `done` | deterministic generator adds time/phone/date format variants without changing slot expectations |
| `P6A Deterministic metamorphic expansion foundation` | `closed by P6.1-P6.5` | `done` | cheap replayable surface mutation layer exists, but it is only the foundation of open-world proof |
| `P6B.1 LLM stress synthesizer pack/branch context contract` | `docs/TASK_PACKAGES/TP-2026-03-06-p6b1-llm-open-world-stress-synthesizer-context-a1.md` | `done` | LLM scenario generation becomes pack-aware, branch-aware, capability-aware, and no longer salon-hardcoded |
| `P6B.2 Multi-pack / multi-capability LLM stress matrix` | `docs/TASK_PACKAGES/TP-2026-03-06-p6b2-multi-pack-multi-capability-stress-matrix-a1.md` | `done` | run the same LLM stress contract across multiple packs/capability envelopes |
| `P6C.1 Failure clustering and root-cause family reporting` | `docs/TASK_PACKAGES/TP-2026-03-06-p6c1-failure-clustering-root-cause-families-a1.md` | `done` | failures are grouped by invariant/root-cause family, not only by individual bad turns |
| `P6C.2 Acceptance closure for P6` | `docs/TASK_PACKAGES/TP-2026-03-06-p6c2-p6-acceptance-closure-a1.md` | `blocked` | closure command/evidence gate implemented; real proof bundle still required before `P6` can close |

- Execution law for this TP:
  - One block at a time.
  - A block can be marked `done` only with its own sub-TP + evidence.
  - Exception: if an expensive realism/promotion block is explicitly marked `budget-blocked` with audited evidence, implementation may continue on the next systemic block while rollout/promotion stays frozen.
  - `lock/replay/canary/full` is an acceptance promotion chain, not the primary debugging loop; during `P1.6` we first close readiness via `P1.6c` (`L1/L2 evidence`, audit debt, `PG checklist`) and only then start guarded `lock`.
  - If a realism/acceptance loop hits `budget-stop` while diff review shows patch-fitting drift, the mandatory next block is release-lane cleanup; no new expensive run starts before that cleanup block is complete and deterministic checks are green.

## P6 Clarification (binding)

- `P6` is not equal to the deterministic mutation blocks already closed.
- Correct full-scope `P6` is split into:
  - `P6A Deterministic metamorphic expansion foundation`:
    - `P6.1`..`P6.5`
    - purpose: cheap replayable multilingual/script/noise/paraphrase/slot-format expansion
  - `P6B LLM open-world stress synthesis`:
    - purpose: generate unexpected, business-agnostic, pack/branch/tool-aware scenarios that a production consultant must survive
  - `P6C Forensic clustering + acceptance closure`:
    - purpose: turn failures into root-cause families and decide whether `P6` is truly closed
- Heavy stress policy:
  - acceptance `lock/replay/canary/full` runs stay on `demo_salon` only
  - multi-pack proof for `P6` is collected via `dev/forensic` matrix evidence, not acceptance lane stresses
- Therefore:
  - `P6.1`..`P6.5` are necessary but not sufficient
  - `P6` is not closed until `P6B` and `P6C` are completed
  - no claim of business-agnostic / multi-branch / multilingual robustness may rely only on deterministic scenario expansion

## One Web Search (mandatory before implementation)

- Query: `NIST SP 800-207 policy decision point policy enforcement point`.
- Time (UTC): `2026-03-05T12:44:50Z`.
- Open sources:
  - NIST SP 800-207 (Zero Trust Architecture): `https://csrc.nist.gov/pubs/sp/800/207/final`
  - NIST glossary: Policy Decision Point: `https://csrc.nist.gov/glossary/term/policy_decision_point`
  - NIST glossary: Policy Enforcement Point: `https://csrc.nist.gov/glossary/term/policy_enforcement_point`
- Ready solutions found:
  - Контрактное разделение Decision Point и Enforcement Point: enforcement валидирует/блокирует, но не подменяет решение decision owner.
- Decision (`reuse/integrate/build`):
  - `integrate`: применить PDP/PEP separation к текущему policy-core.
  - `reuse`: существующий trace/meta контракт и hard-lock фрейм уже есть, но incomplete.
  - `build`: точечное удаление latent rewrite paths и перенос phrase logic из core в pack/resolver.
- Rejected variants:
  - Второй deterministic semantic router (rejected: нарушает single owner).
  - Расширение keyword hardcode в core как "быстрый фикс" (rejected: нарушает business-agnostic charter).

## Root Cause (mandatory)

- Symptom:
  - Семантика все еще частично распределена между LLM-owner и детерминированными ветками/legacy-эвристиками.
  - Есть риски ложного FACT и sidecar-смешения booking/info.
  - Booking commit не fail-closed по контактному минимуму и не атомарен end-to-end.
  - LLM tool-execution path до сих пор использует message-text heuristics для `info_sections_hint` и guard-сигналов.
  - Acceptance пока доказывает single-owner в основном на одном canary pack и еще не доказывает multi-business / multilingual / code-switch robustness.

- Minimal reproduction:
  1. `wc -l truffles-api/app/routers/webhook/decision.py` -> `17996` (god-file orchestration).
  2. `rg -n "_legacy|legacy\." truffles-api/app/routers/webhook/decision.py | wc -l` -> `230`.
  3. `rg -n "_register_policy_override|policy_action\s*=|policy_tool_action\s*=" truffles-api/app/routers/webhook/decision.py`.
  4. `rg -n "FACT_GUARD_ENABLED" truffles-api/app/routers/webhook/decision.py` -> `False`.
  5. `sed -n '4040,4155p' truffles-api/app/routers/webhook/decision.py` (required fields for `calendar.book_slot`).

- Evidence:
  - `truffles-api/app/routers/webhook/decision.py`
    - latent semantic rewrite branches still present (guarded by hard-lock, but physically in runtime core).
    - explicit phrase markers in core (`адрес`, `где`, `парков`, `до скольки`, `мест`).
    - `FACT_GUARD_ENABLED = False`.
    - LLM tool path использует `_detect_info_class_intents(message_text, ...)` для hint/guard.
  - `truffles-api/app/services/tool_registry_service.py`
    - booking create + sync + reminder исполняются отдельными commit-точками.
  - `truffles-api/app/services/appointment_service.py`
    - appointment creation commit независим от outbox/reminder/profile transition.
  - `truffles-api/app/routers/webhook/response.py`
    - append-sidecar/followup ветки могут смешивать FACT и booking prompts в одном body.
  - `truffles-api/app/knowledge/demo_salon/EVAL.yaml`
    - `must_include/must_include_any`: `895` вхождений (phrase-oracle давление).

- Five Whys:
  1. Почему semantic drift продолжает всплывать: core совмещает owner-решение и post-processing семантики.
  2. Почему это осталось: hard-lock блокирует часть мутаций, но rewrite-код и phrase ветки не удалены архитектурно.
  3. Почему это опасно: любой обход/регрессия снова включает второй semantic owner.
  4. Почему качество нестабильно: acceptance частично ориентирован на phrase-oracle и demo-lexicon, а не на open-world invariants.
  5. Почему бизнес-agnostic не достигается: core содержит нишевые/языковые маркеры и demo-coupled fallback patterns, а multilingual/code-switch robustness пока не доказана отдельным open-world acceptance.

- Root cause statement:
  - Корневая проблема не в одном дефекте, а в смешении semantic ownership и deterministic эвристик внутри монолитного orchestrator слоя, плюс неполный контракт fail-closed на FACT и booking commit.

- Fix mechanism:
  - Удалить semantic rewrite как runtime capability (не только блокировать), оставить deterministic только boundary validation.
  - Перенести phrase/lexicon routing из core в pack/resolver contracts.
  - Убрать message-text info hinting из LLM tool path, закрепить LLM-owned `pack_refs`.
  - Закрыть fail-closed контракты по FACT evidence linkage и booking commit atomicity как обязательные boundary gates.

## Invariant

1. Один semantic owner: `action/intent/slots/fact_refs` определяются только policy-core LLM.
2. Deterministic слой не меняет semantic decision, только `validate/block/degrade` с reason_code.
3. Core остается business-agnostic: без tenant/niche phrase branching.
4. Core остается tenant/branch-aware только через runtime capabilities/packs/manifests, а не через tenant-specific logic branches.
5. Multilingual/code-switch turns не должны требовать language-router в core.
6. FACT без валидного evidence linkage запрещен.
7. Booking commit без контактного минимума запрещен.

## Scope

1. `P1 Single Semantic Owner hard closure`:
  - удалить/деактивировать latent rewrite paths в runtime (не оставлять switchable fallback).
  - вынести phrase-based semantic hints из core runtime path.
  - оставить только whitelist boundary overrides (`LAW/safety/schema/capability/idempotency/state`) с trace/meta reason.
2. Обновить deterministic gates и тесты под новый контракт P1.
3. Зафиксировать process-trust preconditions для следующего блока (P2/P3), но без их полной реализации в этом TP.
4. Зафиксировать, что доказательство multi-business/multilingual robustness принимается позже отдельным open-world block, а не объявляется закрытым по одному canary-pack.

## Out Of Scope

1. Полная реализация `P2 FACT body neutrality`.
2. Полная реализация `P3 Booking Commit Protocol`.
3. Полная реализация `P4 FACT evidence linkage`.
4. Полный open-world generator (P6).

## Touch-list (allowed)

- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/services/expected_reply_contract.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `ops/diagnose.py`
- `scripts/quality_chain_controller.sh`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## Plan (1..N)

1. `P1.1` Remove semantic rewrite runtime paths
- Убрать runtime-ветки, где `policy_action/policy_tool_action/policy_intent` меняются post-hoc.
- Сохранить только `semantic_override_blocked` с reason_code + trace/meta.

2. `P1.2` Remove core phrase routing
- Удалить нишевые/языковые marker lists из `decision.py` semantic router path.
- Перенести необходимые сигналы в pack/resolver/config слой.

3. `P1.3` Enforce deterministic boundary contract
- Ввести fail-closed guard: любое semantic delta после owner -> блок/clarify/handoff.
- Зафиксировать `semantic_override_rate=0` как blocking invariant в acceptance lane.

4. `P1.4` LLM tool hint hardcode removal
- Удалить message-text fallback для LLM tool hints и обновить contract tests на LLM-owned `pack_refs`.
- Запретить core lexical hinting в LLM tool path (contract test).

5. `P1.5` Remove post-plan semantic rescue paths
- Убрать deterministic восстановление `pack_refs` и `service_query` из `message_text` после LLM plan.
- Перевести missing semantic refs в fail-closed path (`clarify`/block reason), а не в text-driven rescue.

6. `P1.6` Local realism and canonical acceptance lock
- Прогнать обязательный локальный контур для core behavior.
- Сформировать новый single-owner baseline lock, пригодный для дальнейшего replay.

7. `P1.7` Acceptance replay gate
- Прогнать replay строго по lock-сценариям и fail-on-regression.
- Сформировать evidence packet для Brain/Top Architect.

8. `Post-P1 proof obligation` (binding note, not implemented in this TP)
- После closure `P1.7` следующий program-level proof обязан явно покрыть:
  - несколько business packs;
  - branch-specific capability differences;
  - multilingual/code-switch phrasing;
  - tool availability differences per branch/business.
- Это принимается в `P6 Open-world tests`, а не считается закрытым только по `demo_salon`.

## DoD

1. Нет runtime rewrite пути, который меняет owner semantic decision после LLM.
2. `semantic_override_rate` в acceptance lane = `0` (кроме whitelist degrade reason-codes, отдельно учтенных).
3. В `decision.py` нет business-specific phrase routing веток для semantic arbitration.
4. Все обязательные локальные тесты зеленые.
5. Есть полный evidence packet (trace/meta/artifacts) и обновление `STATE.md` (Brain/Top Architect).

## Checks

- Static contract checks:
  - `rg -n "_register_policy_override" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "policy_action\s*=|policy_tool_action\s*=" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "адрес|где|парков|до скольки|во сколько|мест" truffles-api/app/routers/webhook/decision.py`

- Mandatory deterministic tests:
  - `pytest -q truffles-api/tests/test_message_endpoint.py`
  - `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py`

- Mandatory local realism:
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id booking-lock-p1-20260306-a1`

- Acceptance chain (after P1 green only):
  - `scripts/llm_quality_guarded.sh --mode replay ... --reset-before-dialog --fail-on-regression`

## Evidence

1. Code diff (P1 scope only).
2. Test logs for all mandatory checks.
3. LLM-quality run dir with:
  - `summary.json`
  - `brief.md`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `manual_audit.md`
  - `manual_audit.json`
  - `run_manifest.json`
4. Top failures with exact replay command.
5. `STATE.md` entry by Brain/Top Architect (before merge for behavior/core changes).

## Release Safety

- Strategy: rollout freeze (`stop-the-line`) until P1 DoD passes.
- Go/no-go signals:
  - `semantic_override_rate=0`
  - mandatory suite green
  - local realism valid (`infra_valid=true`, `semantic_valid=true`, `judge.enabled=true`)
- Rollback:
  - revert the specific P1 commit(s) via non-interactive `git revert`.
  - rerun mandatory deterministic suite.

## Rollback

1. Run non-interactive `git revert` for the specific P1 commit SHA that introduced the regression.
2. `pytest -q truffles-api/tests/test_message_endpoint.py`.
3. `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`.
4. If regression persists: stop rollout and restore last known good branch snapshot (merge-only policy).

## No-go

1. Запрещено добавлять новые keyword/regex routing ветки в core semantic path.
2. Запрещено оставлять latent semantic rewrite behind feature flag.
3. Запрещено "чинить" качество через `must_include` без контрактных метрик trace/meta.
4. Запрещено продвигать canary/full при `semantic_override_rate>0` или неполном evidence handoff.
5. Запрещено ослаблять acceptance thresholds ради бюджета/скорости.

## Risks/Blockers

1. `decision.py` монолит (17996 строк) повышает риск hidden regressions.
2. Историческое смешение `legacy` и policy-core усложняет изоляцию semantic owner.
3. Process-trust gap: часть старых `summary.json` не синхронизирует evidence_handoff поля консистентно.
4. P1 closure может выявить новые падения в старых phrase-driven тестах (ожидаемо, не blocker).

## Residual Architecture Debt (mandatory)

- Current residuals accepted in this block:
  - `P1.5b` single-owner contract suite realignment.
  - `P1.6` local realism + canonical acceptance lock closure.
  - `P1.7` acceptance replay + regression gate.
  - Program-level blocks after P1 (`P3`, `P4`, `P6`).

- Why not in this block:
  - После пользовательского указания принят atomic режим `1 block -> 1 sub-TP -> 1 closure`.

- Risk if deferred:
  - P1 remains incomplete even при закрытом P1.1; rollout still blocked.

- Linked follow-up Task Package(s):
  - Этот TP как master + `docs/TASK_PACKAGES/TP-2026-03-07-p1.6o-demo-salon-architecture-closure-program-a1.md` as the active closure contract.
  - Child execution slices under `P1.6o`, then `P1.7`.

- Expiry/trigger to stop deferral:
  - До любого `canary/full` блоки `P1.5b..P1.7` должны быть closed.

## Next-block Contract (mandatory)

- Next block objective:
  - complete the doc-first rescope of `P1.6o16` so the canon explicitly models interaction semantics over the active pending question (`fill_requested_slot`, `ask_about_requested_slot`, `slot_constraint`, `slot_compare`, `mixed_fill_plus_question`), then start only the bounded runtime slice for the first surfaced family before any fresh guarded `demo_salon` `dev L2`.

- First deterministic check command:
  - `rg -n "Pending-question interaction contract|fill_requested_slot|ask_about_requested_slot|slot_constraint|slot_compare|mixed_fill_plus_question" STRATEGY/REQUIREMENTS.md docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md docs/TASK_PACKAGES/TP-2026-03-07-p1.6o-demo-salon-architecture-closure-program-a1.md docs/TASK_PACKAGES/TP-2026-03-08-p1.6o16-booking-time-guidance-question-owner-a1.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md && git diff --check`

- Blocked-by conditions:
  - `P1.6o16` remains framed as a one-phrase `time guidance` fix instead of a broader pending-question interaction gap.
  - runbook / TP / requirements taxonomy are not synchronized on the new interaction-act vocabulary.
  - The bounded post-doc runtime child slice is not explicit.
  - Runtime `http://127.0.0.1:18184` is not restarted from the post-doc code state before the next guarded window.

- Owner role for closure:
  - `Top Architect + Brain`
