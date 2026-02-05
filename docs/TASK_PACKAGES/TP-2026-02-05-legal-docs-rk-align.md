# TP-2026-02-05-legal-docs-rk-align

- Название/цель: Привести legal/support шаблоны к фактам системы (провайдеры/категории/сроки ПДн), убрать SLA, обновить возвраты/ответственность по нормам РК, заполнить контактные данные/ответственного.
- Canon refs: `docs/SELLING_TRUTHS.md`, `Business/Legal/*`, `Business/Support/Регламент_техподдержки.md`, `STATE.md` (docs‑templates DONE), законы РК: ГК РК K990000409_ (ст. 683–686, 947–950), Закон РК «О защите прав потребителей» Z100000274_ (ст. 8‑1, 35, 42‑4).
- Invariant: doc‑only; никаких новых обещаний/гарантий; SLA не добавлять; провайдеры/категории/сроки ПДн только из кода.
- Scope:
  - Заполнить ответственного и контакты (ваши данные) в privacy/data‑policy/support.
  - Список провайдеров/субобработчиков — строго из кода.
  - Категории/цели/сроки ПДн — из моделей/настроек (learning_retention_days, media TTL и др.).
  - Убрать SLA из договора и связанных шаблонов.
  - Обновить возвраты/ответственность с отсылками к нормам РК.
  - Обновить регламент поддержки (best‑practice, без гарантий времени ответа).
- Out of scope: код/инфра/поведение, новые product claims, утверждение юристом.
- Touch‑list:
  - `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md`
  - `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`
  - `Business/Legal/ДОГОВОР.md`
  - `Business/Legal/ПОЛИТИКА_ВОЗВРАТА.md`
  - `Business/Legal/ОГРАНИЧЕНИЕ_ОТВЕТСТВЕННОСТИ.md`
  - `Business/Legal/SLA.md` (deprecated/не используется)
  - `Business/Legal/СОГЛАСИЕ_НА_ОБРАБОТКУ_ДАННЫХ.md`
  - `Business/Legal/AI_DISCLOSURE.md`
  - `Business/Support/Регламент_техподдержки.md`
  - `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`
  - `docs/SESSIONS/SESSION-2026-02-05-legal-docs-rk-align-a11.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Старт сессии/worktree.
  2) Снять факты из кода: провайдеры, категории ПДн, сроки хранения (learning/media TTL).
  3) Обновить legal/support шаблоны и убрать SLA.
  4) Зафиксировать ссылки на нормы РК в возвратах/ответственности.
  5) `scripts/session_check.sh`, коммит doc‑only, push на `main`.
- DoD:
  - Контакты/ответственный заполнены.
  - Провайдеры/категории/сроки ПДн соответствуют коду.
  - SLA удалён из договора и не используется.
  - Возвраты/ответственность с отсылками к РК нормам.
- Checks:
  - `scripts/session_check.sh`
- Evidence:
  - Коммит + ссылки на нормы РК (adilet).
- Rollback: revert commit.
- No‑go: новые обещания, SLA, правки runtime.
- Риски/блокеры: отсутствуют данные о хостинг‑провайдере в коде.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-legal-docs-rk-align-a11`
  - Worktree: `/home/zhan/worktrees/2026-02-05-legal-docs-rk-align-a11`
  - Base: `origin/main`
  - Merge: doc‑only fast‑forward push to `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
