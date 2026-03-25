# TP-2026-02-05-legal-readiness-pack

- Название/цель: Подготовить базовый набор бизнес/юридических документов (черновики/шаблоны) для готовности к запуску и поддержке клиентов.
- Canon refs: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `docs/PROCESSES.md` (Go/No-Go), `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `STRUCTURE.md`, `STATE.md`.
- Invariant: doc‑only; все новые документы помечены DERIVED/DRAFT; никаких новых продуктовых обещаний вне канона.
- Scope:
  - Создать: `Business/Legal/NDA.md`.
  - Создать: `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`.
  - Создать: `Business/Legal/СЧЕТ_ШАБЛОН.md`.
  - Создать: `Business/Support/Регламент_техподдержки.md`.
  - Создать: `Business/Onboarding/Чеклист_запуска.md`.
  - Создать: `Business/Onboarding/Инструкция_клиента.md`.
  - Обновить: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md` (статусы).
  - Обновить: `STRUCTURE.md` (карта новых папок/файлов).
  - Обновить: `STATE.md` (фиксация doc‑work как DONE с evidence).
- Out of scope: изменение тарифов/обещаний/юридических условий в `STRATEGY/PRODUCT.md` или `docs/SELLING_TRUTHS.md`, правки runtime, SLA/AI-disclosure.
- Touch‑list:
  - `Business/Legal/NDA.md`
  - `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`
  - `Business/Legal/СЧЕТ_ШАБЛОН.md`
  - `Business/Support/Регламент_техподдержки.md`
  - `Business/Onboarding/Чеклист_запуска.md`
  - `Business/Onboarding/Инструкция_клиента.md`
  - `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-05-legal-readiness-pack-a10.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-05-legal-readiness-pack.md`
- Plan:
  1) Старт сессии/worktree.
  2) Сверить канон `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md`.
  3) Создать черновые документы (DERIVED/DRAFT).
  4) Обновить `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `STRUCTURE.md`, `STATE.md`.
  5) `scripts/session_check.sh`.
- DoD:
  - Документы созданы и помечены DERIVED/DRAFT.
  - Нет новых обещаний вне канона.
  - Док‑карта и статусы актуальны.
- Checks:
  - `scripts/session_check.sh`
- Evidence:
  - Коммит с новыми документами + обновлённые `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `STRUCTURE.md`, `STATE.md`.
- Rollback: revert commit.
- No‑go: любые runtime‑правки; новые продуктовые обещания/цифры.
- Риски/блокеры: риск добавить спорные формулировки без канона — проверять по `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-legal-readiness-pack-a10`
  - Worktree: `/home/zhan/worktrees/2026-02-05-legal-readiness-pack-a10`
  - Base: `origin/main`
  - Merge: PR → `main` (не doc‑only из‑за `Business/`)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
