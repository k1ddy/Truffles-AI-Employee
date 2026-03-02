# TP-2026-03-02-contract-test-migration-master-a1

- Название/цель: Закрыть оставшийся кусок `P9 Contract Test Migration` для master-интентов: убрать текстовые оракулы в master-info тестах и заменить на контрактные мета‑проверки. Цель: contract‑first (decision_meta/intent/action/info_sections/fact_intents) без зависимости от текста ответа.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- STATE refs (NOW): в `STATE.md` зафиксирован open item по contract‑first и запрету текстовых оракулов; оставшиеся текстовые asserts — в `truffles-api/tests/test_message_endpoint.py` и `truffles-api/tests/test_knowledge_service.py`. Этот TP закрывает master long‑hair тесты.
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Root cause (mandatory)

- Symptom: master‑info тесты завязаны на текст ответа и ломают contract‑first oracle.
- Minimal reproduction: `pytest -q truffles-api/tests/test_info_master_long_hair.py` показывает asserts по `reply.casefold()`.
- Evidence (pre-fix): `truffles-api/tests/test_info_master_long_hair.py` содержал проверки по тексту (“длинные волосы”, “балаяж”).
- Five whys:
  - Почему тесты используют текстовые asserts? — Ранее текст был единственным доступным индикатором качества.
  - Почему это стало проблемой? — Контракт требует принимать качество по `decision_meta/decision_trace`.
  - Почему не мигрировали раньше? — Фокус был на runtime‑ремедиации и process‑гейтах.
  - Почему текстовые asserts вредят? — Они хрупкие при легитимной перефразировке/локализации.
  - Почему сейчас? — P9 остаётся partial; закрытие требует убрать последние текстовые оракулы.
- Root cause statement: остаточные тесты используют текст ответа как primary oracle, что противоречит contract‑first acceptance.
- Fix mechanism: заменить текстовые asserts на контрактные мета‑проверки (intent/action/info_sections/fact_intents/master_reply_mode/master_profiles).

## One web search (mandatory before implementation)

- Query: `python str.casefold documentation`
- Date/time: `2026-03-02T01:48:02Z`
- Opened sources:
  - `https://docs.python.org/3/library/stdtypes.html#str.casefold` (primary)
- Ready solutions found:
  - `str.casefold()` предназначен для caseless matching; использовать для нормализации лексиконов.
- Decision: `reuse/integrate`
  - при необходимости в новых тестовых проверках или нормализации использовать `casefold()` вместо `lower()`.
- Rejected options:
  - None (single-source primary was sufficient).

## Reuse-first (mandatory)

- Reuse: существующие `decision_meta` и `_build_fact_meta` из `pack_runtime_service.py`.
- Integrate: текущие master‑контракты `master_reply_mode`, `master_profiles`, `fact_intents`, `info_sections`.
- Configure: нет.
- Build: только если meta полей окажется недостаточно (ожидается не потребуется).

## Release safety (mandatory)

- Rollout strategy: N/A (test-only change, no runtime behavior changes).
- Go/No-go: зеленые детерминированные тесты в Touch-list.
- Rollback: revert commit.

## Invariant

- Не менять продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять LAW/policy/safety hard‑gates.
- Не вводить новые текстовые оракулы как primary acceptance.
- Не менять runtime семантику master‑ответов.

## Scope

- Миграция master‑info тестов на контрактные проверки `decision_meta`/`fact_intents`/`info_sections`.
- Удаление текстовых asserts как primary oracle.

## Out of scope

- Любые изменения runtime/семантики master‑ответов.
- Изменения acceptance lane или LLM quality раннеров.
- Миграция всех текстовых asserts вне master‑тестов (отдельный TP).

## Touch-list

- `truffles-api/tests/test_info_master_long_hair.py`
- (в случае необходимости) `truffles-api/app/routers/webhook/info.py`
- (в случае необходимости) `truffles-api/app/services/pack_runtime_service.py`

## Plan

1. Найти все текстовые asserts в `truffles-api/tests/test_info_master_long_hair.py`.
2. Заменить их на контрактные проверки: `meta.intent_class`, `fact_intents`, `info_sections`, `master_reply_mode`, `master_profiles`.
3. Убедиться, что тесты не требуют конкретной формулировки ответа.
4. Прогнать детерминированные tests в Touch-list.

## DoD

- В `truffles-api/tests/test_info_master_long_hair.py` нет проверок по содержимому текста ответа.
- Тесты проверяют только контрактные поля meta и не требуют конкретной фразы.
- Все проверки из секции `Checks` зелёные.

## Checks

- `pytest -q truffles-api/tests/test_info_master_long_hair.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py`

## Evidence

- `pytest -q truffles-api/tests/test_info_master_long_hair.py` (`2 passed in 2.94s`).
- `pytest -q truffles-api/tests/test_master_info_flow.py` (`29 passed in 3.22s`).
- Diff с удалением текстовых asserts.
- Запись в `STATE.md` не требуется (изменения тестовые, без runtime‑поведения).

## Rollback

- `git revert <commit>`.

## No-go

- Нельзя использовать текстовые asserts как primary oracle.
- Нельзя менять runtime семантику master‑ответа.
- Нельзя добавлять новые phrase/regex ветки в core‑файлы.

## Риски/блокеры

- Если meta‑поля окажутся недостаточными для проверки contract‑first, потребуется отдельный TP на расширение meta.

## Fitness Functions impacted

- P0 (Semantic Ownership): остаётся зеленым за счёт contract‑first тестов.
- P1 (Deterministic Boundaries): тесты не добавляют новый детерминизм, только проверяют контрактные поля.
- P2 (Evidence Integrity): checks генерируют чистое детерминированное evidence.

### Execution Status Update (2026-03-02)

- Done: текстовые asserts в `truffles-api/tests/test_info_master_long_hair.py` заменены на контрактные meta‑проверки; checks зелёные.
