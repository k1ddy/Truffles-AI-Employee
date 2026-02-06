# TP-2026-02-05-doc-templates

- Название/цель: Шаблонизировать Legal/Onboarding/Support документы, заполнить проверенные данные Truffles и оставить неизвестные/клиентские поля пустыми для ручного заполнения.
- Canon refs: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `Business/РеквизитыДокументыКомпаний/Справка о государственной регистрации.md`, `Business/Legal/ДОГОВОР.md`, `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `STATE.md`, `STRUCTURE.md`.
- Invariant: doc-only (без runtime правок); все шаблоны остаются DERIVED; никаких новых обещаний/цифр/юридических трактовок вне канона.
- Scope:
  - Обновить шаблоны и подставить данные Truffles: `Business/Legal/ДОГОВОР.md`, `Business/Legal/NDA.md`, `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`, `Business/Legal/СЧЕТ_ШАБЛОН.md`, `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md`, `Business/Legal/ПОЛЬЗОВАТЕЛЬСКОЕ_СОГЛАШЕНИЕ.md`.
  - Обновить шаблоны и подставить контактные данные Truffles: `Business/Onboarding/Чеклист_запуска.md`, `Business/Onboarding/Инструкция_клиента.md`, `Business/Support/Регламент_техподдержки.md`.
- Out of scope: изменение правовых условий/обязательств, пересмотр тарифов/обещаний, создание новых документов, правки `Business/РеквизитыДокументыКомпаний/*`.
- Touch-list:
  - `Business/Legal/ДОГОВОР.md`
  - `Business/Legal/NDA.md`
  - `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`
  - `Business/Legal/СЧЕТ_ШАБЛОН.md`
  - `Business/Legal/ПОЛИТИКА_КОНФИДЕНЦИАЛЬНОСТИ.md`
  - `Business/Legal/ПОЛЬЗОВАТЕЛЬСКОЕ_СОГЛАШЕНИЕ.md`
  - `Business/Onboarding/Чеклист_запуска.md`
  - `Business/Onboarding/Инструкция_клиента.md`
  - `Business/Support/Регламент_техподдержки.md`
  - `docs/SESSIONS/SESSION-2026-02-05-doc-templates-a11.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-05-doc-templates.md`
- Plan:
  1) Старт сессии/worktree.
  2) Выписать подтверждённые данные Truffles из канон-источников.
  3) Превратить документы в шаблоны: заполнить Truffles данные, оставить все неизвестные/клиентские поля пустыми.
  4) Проверить на отсутствие новых обещаний/цифр.
  5) `scripts/session_check.sh`.
- DoD:
  - Все документы в scope содержат подтверждённые данные Truffles.
  - Все неизвестные/клиентские поля оставлены пустыми (явные плейсхолдеры).
  - DERIVED пометки сохранены.
- Checks:
  - `scripts/session_check.sh`
  - `rg -n "_{4,}|\[\s*\]" Business/Legal Business/Onboarding Business/Support`
- Evidence:
  - Коммит с обновлёнными документами + сессионный лог.
- Rollback: revert commit.
- No-go: любые новые продуктовые обещания/цифры, правки вне touch-list, заполнение непроверенными данными.
- Риски/блокеры: риск неверного заполнения данных без источника — проверять каждую вставку по канону.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-05-doc-templates-a11`
  - Worktree: `/home/zhan/worktrees/2026-02-05-doc-templates-a11`
  - Base: `origin/main`
  - Merge: PR -> `main` (не doc-only из-за `Business/`)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
