# TP-2026-03-02-contract-test-migration-semantic-service-a1

- Название/цель: Закрыть часть `P9 Contract Test Migration` для demo_salon семантических тестов: убрать текстовые оракулы в `semantic_service_match` и `semantic_question_type` тестах и заменить на контрактные meta‑проверки (`intent`, `action`, `canonical_name`, `suggestions`, `fact_intents`, `duration_item`). Цель: contract‑first без зависимости от текста ответа.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- STATE refs (NOW): `P9 Contract Test Migration` остаётся partial; в `truffles-api/tests/test_message_endpoint.py` есть текстовые asserts в demo_salon семантических тестах (service match + question type).
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Root cause (mandatory)

- Symptom: demo_salon semantic tests проверяют содержимое текста ответа (`result.response`/`decision.response`) вместо контрактных meta‑полей.
- Minimal reproduction: `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_service_matcher or semantic_question_type"` — asserts используют `response.casefold()`.
- Evidence: `truffles-api/tests/test_message_endpoint.py` содержит проверки по тексту в `test_semantic_service_matcher_*` и `test_semantic_question_type_routes_duration_and_price`.
- Five whys:
  - Почему тесты используют текстовые asserts? — Изначально проверяли человеческий текст как proxy качества.
  - Почему это стало проблемой? — Контракт требует опираться на `decision_meta`/структурные поля.
  - Почему не мигрировали раньше? — Фокус был на runtime‑ремедиации и process‑гейтах.
  - Почему текстовые asserts вредят? — Они хрупкие при легитимной перефразировке/локализации.
  - Почему сейчас? — P9 остаётся partial; закрываем семантический блок тестов.
- Root cause statement: semantic demo_salon tests используют текст ответа как primary oracle, что противоречит contract‑first acceptance.
- Fix mechanism: заменить текстовые asserts на meta‑проверки (intent/action/canonical_name/suggestions/fact_intents/duration_item).

## One web search (mandatory before implementation)

- Query: `pytest assert statement introspection documentation`
- Date/time: `2026-03-02T07:55:29+05:00`
- Opened sources:
  - `https://docs.pytest.org/en/4.6.x/assert.html` (primary)
- Ready solutions found:
  - Использование стандартного `assert` с читаемыми проверками на контрактные поля.
- Decision: `reuse/integrate`
  - Использовать привычные `assert` на meta‑поля вместо текстовых проверок.
- Rejected options:
  - None (single-source primary was sufficient).

## Reuse-first (mandatory)

- Reuse: `DemoSalonDecision.meta` и `SemanticServiceMatch` поля (`canonical_name`, `suggestions`).
- Integrate: текущие `fact_intents`, `duration_item` из `_build_fact_meta`.
- Configure: нет.
- Build: не требуется.

## Release safety (mandatory)

- Rollout strategy: N/A (test-only change).
- Go/No-go: зелёный pytest в Touch-list.
- Rollback: revert commit.

## Invariant

- Не менять runtime семантику и поведение `demo_salon_knowledge`.
- Не добавлять новые текстовые оракулы как primary acceptance.
- Не менять contract `FACT/COLLECT/HANDOFF`.

## Scope

- Миграция demo_salon semantic тестов в `truffles-api/tests/test_message_endpoint.py` на контрактные meta‑проверки.
- Удаление прямых проверок текста ответа в `test_semantic_service_matcher_*` и `test_semantic_question_type_routes_duration_and_price`.

## Out of scope

- Любые runtime изменения в `demo_salon_knowledge`.
- Миграция других текстовых asserts вне указанного блока.

## Touch-list

- `truffles-api/tests/test_message_endpoint.py`

## Plan

1. Найти текстовые asserts в `test_semantic_service_matcher_*` и `test_semantic_question_type_routes_duration_and_price`.
2. Заменить их на проверки `intent/action/canonical_name/suggestions/fact_intents/duration_item`.
3. Прогнать pytest по scoped набору.
4. Обновить parent TP execution status.

## DoD

- В указанных тестах нет проверок по тексту ответа.
- Тесты проверяют контрактные поля meta и структурные атрибуты.
- `pytest` из `Checks` зелёный.

## Checks

- `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_service_matcher or semantic_question_type"`

## Evidence

- `pytest -q truffles-api/tests/test_message_endpoint.py -k "semantic_service_matcher or semantic_question_type"` (`7 passed, 263 deselected in 7.68s`).
- Diff с удалением текстовых asserts.

## Rollback

- `git revert <commit>`.

## No-go

- Нельзя ослаблять контрактные проверки.
- Нельзя менять runtime логику `demo_salon_knowledge`.

## Риски/блокеры

- Если meta‑поля окажутся недостаточными, потребуется отдельный TP на расширение meta.

## Fitness Functions impacted

- P0 (Semantic Ownership): сохраняется за счёт contract‑first тестов.
- P2 (Evidence Integrity): checks генерируют детерминированное evidence.

### Execution Status Update (2026-03-02)

- Done: demo_salon semantic tests переведены на meta‑проверки; checks зелёные.
