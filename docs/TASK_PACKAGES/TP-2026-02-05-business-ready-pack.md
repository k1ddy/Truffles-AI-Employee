# TP-2026-02-05-business-ready-pack

- Название/цель: Подготовить полный пакет бизнес‑документов и процессный контур “договор → онбординг → поддержка” для старта с клиентами (шаблоны, без новых обещаний).
- Canon refs: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `docs/PROCESSES.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `STRUCTURE.md`, `STATE.md`.
- Invariant: doc‑only; все документы DERIVED/DRAFT; только подтверждённые данные Truffles; никаких новых обещаний/цифр вне канона.
- Scope:
  - Создать шаблоны:
    - `Business/Legal/SLA.md`
    - `Business/Legal/АКТ_ПРИЕМА_ПЕРЕДАЧИ.md`
    - `Business/Legal/ПОЛИТИКА_ВОЗВРАТА.md`
    - `Business/Legal/СОГЛАСИЕ_НА_ОБРАБОТКУ_ДАННЫХ.md`
    - `Business/Legal/AI_DISCLOSURE.md`
    - `Business/Legal/ОГРАНИЧЕНИЕ_ОТВЕТСТВЕННОСТИ.md`
  - Обновить процессный контур: `docs/PROCESSES.md`.
  - Обновить карту документов/структуру/статусы: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `STRUCTURE.md`.
  - Обновить `STATE.md` (фиксировать doc‑work как DONE с evidence).
- Out of scope: изменение условий договора/тарифов/обещаний; любые runtime‑правки.
- Touch‑list:
  - `Business/Legal/SLA.md`
  - `Business/Legal/АКТ_ПРИЕМА_ПЕРЕДАЧИ.md`
  - `Business/Legal/ПОЛИТИКА_ВОЗВРАТА.md`
  - `Business/Legal/СОГЛАСИЕ_НА_ОБРАБОТКУ_ДАННЫХ.md`
  - `Business/Legal/AI_DISCLOSURE.md`
  - `Business/Legal/ОГРАНИЧЕНИЕ_ОТВЕТСТВЕННОСТИ.md`
  - `docs/PROCESSES.md`
  - `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-05-business-ready-pack-a11.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-05-business-ready-pack.md`
- Plan:
  1) Старт сессии/worktree.
  2) Сверить канон `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md`.
  3) Создать недостающие шаблоны (плейсхолдеры для неизвестных/клиентских данных).
  4) Обновить `docs/PROCESSES.md` (сквозной процесс + ссылки на документы).
  5) Обновить `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `STRUCTURE.md`, `STATE.md`.
  6) `scripts/session_check.sh`.
- DoD:
  - Все шаблоны из scope созданы.
  - Процессы зафиксированы и ссылаются на документы.
  - Карта документов/структура/статусы обновлены.
  - Нет новых обещаний/цифр вне канона.
- Checks:
  - `scripts/session_check.sh`
- Evidence:
  - Коммит с новыми документами + обновлённые карты/процессы + запись в `STATE.md`.
- Rollback: revert commit.
- No-go: любые неподтверждённые данные/обещания; правки вне touch-list.
- Риски/блокеры: риск добавить формулировки вне канона — сверять с `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-business-ready-pack-a11`
  - Worktree: `/home/zhan/worktrees/2026-02-05-business-ready-pack-a11`
  - Base: `origin/main`
  - Merge: PR -> `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
