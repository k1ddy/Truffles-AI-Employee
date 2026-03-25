# TP-2026-02-05-legal-rk-fill

- Название/цель: Заполнить черновики юридических/поддержка/онбординг документов реквизитами из Business‑доков и сослаться на нормы РК по персональным данным.
- Canon refs: `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md` (закон РК + контакты), `Business/Legal/ДОГОВОР.md` (реквизиты/банк), `Business/РеквизитыДокументыКомпаний/Справка о государственной регистрации.md` (наименование/адрес/директор), `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`.
- Invariant: doc‑only; новые формулировки без новых обещаний; все документы остаются DERIVED/DRAFT.
- Scope:
  - Заполнить реквизиты/контакты в `Business/Legal/NDA.md`.
  - Заполнить реквизиты/контакты и ссылку на закон РК в `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`.
  - Заполнить реквизиты/банк в `Business/Legal/СЧЕТ_ШАБЛОН.md`.
  - Заполнить канал поддержки (support@) в `Business/Support/Регламент_техподдержки.md`.
  - Заполнить блок поддержки/каналы в `Business/Onboarding/Инструкция_клиента.md`.
  - Обновить `STATE.md` (docs‑DONE с evidence).
- Out of scope: изменение тарифов/обещаний, правки кода, новые юридические условия/пункты.
- Touch‑list:
  - `Business/Legal/NDA.md`
  - `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`
  - `Business/Legal/СЧЕТ_ШАБЛОН.md`
  - `Business/Support/Регламент_техподдержки.md`
  - `Business/Onboarding/Инструкция_клиента.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-05-legal-rk-fill-a10.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-05-legal-rk-fill.md`
- Plan:
  1) Старт сессии/worktree.
  2) Сверить реквизиты в Business‑доках.
  3) Заполнить черновики и добавить ссылку на закон РК (94‑V от 21.05.2013).
  4) Обновить `STATE.md`.
  5) `scripts/session_check.sh`.
- DoD:
  - Черновики заполнены данными только из Business‑доков.
  - Закон РК о персональных данных указан.
  - `STATE.md` обновлён с evidence.
- Checks:
  - `scripts/session_check.sh`
- Evidence:
  - Коммит с изменениями в указанных файлах.
- Rollback: revert commit.
- No‑go: новые продуктовые обещания/юридические обязательства, правки runtime.
- Риски/блокеры: риск переноса неканоничных данных — использовать только Business‑доки.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-legal-rk-fill-a10`
  - Worktree: `/home/zhan/worktrees/2026-02-05-legal-rk-fill-a10`
  - Base: `origin/main`
  - Merge: PR → `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
