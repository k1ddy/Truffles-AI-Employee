# TP-2026-03-02-chain-controller-bootstrap-a1

- Название/цель: Добавить bootstrap/import команду для `scripts/quality_chain_controller.sh`, чтобы можно было импортировать существующие run-артефакты в chain state и продолжать canonical `lock -> replay -> full` без ручной правки состояния.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- STATE refs: `STATE.md` NOW — указано отсутствие bootstrap/migration для chain controller (legacy run artifacts не импортируются в chain state).
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Root cause (mandatory)

- Symptom: Нельзя импортировать существующие run‑артефакты в chain controller (нет команды), из‑за чего legacy lock/replay/full не могут быть продолжены без ручной правки state.
- Minimal reproduction: `scripts/quality_chain_controller.sh --help` не содержит bootstrap/import команды.
- Evidence: `scripts/quality_chain_controller.sh` (usage/command list).
- Five whys:
  - Почему нельзя импортировать? — Нет команды для bootstrap.
  - Почему это важно? — Legacy run‑артефакты не попадают в chain state.
  - Почему это блокирует процесс? — controller требует chain state для prepare/resume.
  - Почему не было ранее? — Фокус был на strict enforcement, не на миграции.
  - Почему сейчас? — Закрываем последний пробел chain controller.
- Root cause statement: отсутствует официальный bootstrap/import entrypoint для chain state.
- Fix mechanism: добавить команду `bootstrap` в `scripts/quality_chain_controller.sh` и детерминированные тесты.

## One web search (mandatory before implementation)

- Query: `python fcntl flock file lock example`
- Date/time: `2026-03-02T02:08:51Z`
- Opened sources:
  - `https://docs.python.org/3/library/fcntl.html#fcntl.flock` (primary)
  - `https://linuxize.com/post/python-file-lock/` (secondary)
- Ready solutions found:
  - `fcntl.flock` обеспечивает межпроцессный эксклюзивный lock файла; подходит для chain state.
- Decision: `reuse/integrate`
  - использовать текущий `with_lock()` (fcntl) без изменений; bootstrap использует тот же lock.
- Rejected options:
  - отдельный lock‑daemon или DB‑lock (избыточно для задачи).

## Reuse-first (mandatory)

- Reuse: `infer_step_status`, `derive_target_blocker_total`, `write_brief`, `write_json_atomic` в `scripts/quality_chain_controller.sh`.
- Integrate: существующий формат chain state.
- Configure: нет.
- Build: новый command handler `bootstrap`.

## Release safety (mandatory)

- Rollout strategy: N/A (tooling only).
- Go/No-go: зелёный детерминированный тест в `truffles-api/tests/test_booking_quality_chain_controller.py`.
- Rollback: revert commit.

## Invariant

- Не ослаблять chain controller enforcement.
- Не менять acceptance criteria.
- Bootstrap не должен затирать существующий chain state без явного действия.

## Scope

- Добавить `bootstrap` команду в `scripts/quality_chain_controller.sh`.
- Добавить детерминированный тест, который импортирует canonical lock run в chain state.

## Out of scope

- Изменения runtime семантики.
- Изменения LLM quality lane логики.

## Touch-list

- `scripts/quality_chain_controller.sh`
- `truffles-api/tests/test_booking_quality_chain_controller.py`

## Plan

1. Добавить команду `bootstrap` в CLI usage и в обработчик команд.
2. Реализовать `cmd_bootstrap()` (fail‑closed при отсутствии summary, не перезаписывает существующий chain state).
3. Добавить тест на импорт canonical lock run и проверку chain state (`next_command`, `active.step`).
4. Прогнать детерминированный тест из `Checks`.

## DoD

- `scripts/quality_chain_controller.sh bootstrap ...` создает chain state из summary + run_manifest.
- Chain state содержит статус шага, next_command и brief_for_next_agent.
- Тесты из `Checks` зелёные.

## Checks

- `pytest -q truffles-api/tests/test_booking_quality_chain_controller.py`

## Evidence

- Вывод `Checks`.
- Новый test кейс в `truffles-api/tests/test_booking_quality_chain_controller.py`.

## Rollback

- `git revert <commit>`.

## No-go

- Нельзя добавлять обход chain controller.
- Нельзя переписывать существующий chain state без явного решения.

## Риски/блокеры

- Если legacy run артефакты неполные (`summary.json` отсутствует), bootstrap должен fail‑closed.

## Fitness Functions impacted

- P0 (Semantic Ownership): не затрагивается.
- P1 (Deterministic Boundaries): остаётся зеленым, bootstrap использует deterministic state.
- P2 (Evidence Integrity): улучшает, добавляя chain state для legacy артефактов.
