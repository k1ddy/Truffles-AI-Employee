# TP-2026-02-05-control-plane-gonogo

- Название/цель: Добавить в `docs/PROCESSES.md` простой Go/No-Go чек‑лист готовности Control Plane и определения (онбординг/договор/техподдержка) строго по канону.
- Canon refs: `STATE.md` (TODO: автоматизация онбординга + go/no-go gate), `docs/IMPERIUM_DECISIONS.yaml` (DEC-014), `docs/PROCESSES.md`, `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `Business/Legal/ДОГОВОР.md`, `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md`, `Business/Legal/ПОЛЬЗОВАТЕЛЬСКОЕ_СОГЛАСЕНИЕ.md`, `Business/Sales/Чеклист_подключения_клиента.md`, `Business/Sales/Бриф_клиента.md`.
- Invariant: doc‑only; не меняем runtime/схемы/контракты; не добавляем новые обещания без подтверждения.
- Scope:
  - Добавить раздел Go/No‑Go готовности Control Plane и краткие определения (онбординг/договор/техподдержка/юридическая готовность) в `docs/PROCESSES.md`.
- Out of scope: любые код‑правки; создание новых юридических шаблонов; обновление `STATE.md`.
- Touch‑list:
  - `docs/PROCESSES.md`
  - `docs/SESSIONS/SESSION-2026-02-05-control-plane-gonogo-a10.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-05-control-plane-gonogo.md`
- Plan:
  1) Создать/подтвердить Task Package.
  2) Запустить сессию (worktree+log).
  3) Обновить `docs/PROCESSES.md` разделом Go/No‑Go + определения.
  4) Проверить `scripts/session_check.sh`.
- DoD:
  - В `docs/PROCESSES.md` есть структурированный Go/No‑Go список и определения, соответствующие DEC‑014.
  - Формулировки опираются только на существующие документы.
  - Session log + index обновлены; doc‑only путь соблюдён.
- Checks:
  - `scripts/session_check.sh`
- Evidence:
  - diff по `docs/PROCESSES.md` + session log.
- Rollback: revert commit.
- No‑go: кодовые правки; новые правовые обязательства; ссылки на несуществующие процессы.
- Риски/блокеры: риск добавить неверные/неподтверждённые формулировки — проверка по канону.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-control-plane-gonogo-a10`
  - Worktree: `/home/zhan/worktrees/2026-02-05-control-plane-gonogo-a10`
  - Base: `origin/main`
  - Merge: doc‑only fast‑forward в `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
