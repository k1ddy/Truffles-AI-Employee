# TP-2026-02-02-vertical-pack-kit

- Название/цель: Зафиксировать спецификацию Vertical Pack Kit (readiness checklist, minimum data contract, safe-mode, QA/Eval) для быстрого подключения новых вертикалей.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-021/DEC-022), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/ACTIVE_LEARNING.md`, `SPECS/SYSTEM_REFERENCE.md`, `STATE.md` (PLAN).
- Invariant: truth-first; факты только из packs/tools; LLM не коммитит решения/факты; без расширения бизнес-лексиконов в коде; doc-only (без runtime/БД изменений).
- Scope:
  - Подготовить `SPECS/VERTICAL_PACK_KIT.md` с:
    - Minimum Data Contract (обязательные поля и допустимые источники).
    - Readiness checklist + критерии SAFE_MODE/GO.
    - Требования к multi-lang (RU/KZ/mixed) через packs, без кодовых словарей.
    - Требования к policy/anchors/booking-signal и fallback поведению.
    - QA/Eval требования (chaos, dialog suites, mixed-lang smoke).
    - Шаблон секций vertical pack (services/pricing/location/hours/policy/booking).
  - Обновить `STRUCTURE.md` и `STATE.md` под новую спецификацию.
- Out of scope: код, миграции, pack-данные, runtime поведение, UI/console.
- Touch-list:
  - `SPECS/VERTICAL_PACK_KIT.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-vertical-pack-kit-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Создать `SPECS/VERTICAL_PACK_KIT.md` по шаблону выше.
  2) Зафиксировать ссылки/статусы в `STATE.md`.
  3) Добавить документ в `STRUCTURE.md`.
  4) Сформировать session log + index.
- DoD:
  - `SPECS/VERTICAL_PACK_KIT.md` создан и содержит readiness/contract/safe-mode/QA.
  - `STRUCTURE.md` обновлён.
  - `STATE.md` отражает план.
- Checks:
  - `rg -n "Vertical Pack Kit|Minimum Data Contract|Safe-Mode" SPECS/VERTICAL_PACK_KIT.md`
- Evidence:
  - `SPECS/VERTICAL_PACK_KIT.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Rollback: revert commit (doc-only).
- No-go: любые runtime/DB/pack изменения; попытка расширять словари в коде.
- Branch/worktree/base/merge/cleanup:
  - Branch: `docs/2026-02-02-vertical-pack-kit-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-vertical-pack-kit-a1`
  - Base: `origin/main`
  - Merge: doc-only fast-forward to `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: выбор вертикали/доменной терминологии (медицина/спорт/аптеки) требует owner input.
