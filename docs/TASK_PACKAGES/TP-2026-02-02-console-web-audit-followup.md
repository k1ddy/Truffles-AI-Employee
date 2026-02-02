# Task Package: Console web audit follow-up (evidence + UX backlog)

- Название/цель (1–2 предложения)
  - Зафиксировать фактическое закрытие найденных UX/bug issues из console-web fact audit и собрать подробный UX backlog по реализованным страницам.
- Canon refs (owner‑doc + `STATE.md` NOW/GAP + CA_ID при наличии)
  - `docs/REPORTS/2026-02-01-console-web-fact-audit.md`
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `STATE.md` (DONE entry: Web Console fact audit)
- Invariant
  - Только реализованное поведение, без планов/догадок.
  - Документация и evidence соответствуют фактическому состоянию main.
- Scope
  - Обновить отчет аудит‑фактов с фиксацией статусов и evidence.
  - Создать UX backlog (bugs/UX debt/code smells) с ссылками на код.
  - Синхронизировать inventory docs по фактическим изменениям (Load more, Calendar date).
  - Обновить `STATE.md` + `STRUCTURE.md` по новым документам.
- Out of scope
  - Любые изменения кода/поведения UI/API.
  - Любые новые фичи или редизайн компонентов.
- Touch-list (файлы/таблицы)
  - `docs/REPORTS/2026-02-01-console-web-fact-audit.md`
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `docs/CONSOLE_AUDIT/pages/inbox.md`
  - `docs/CONSOLE_AUDIT/pages/calendar.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (new)
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md` (если нужно)
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-audit-followup-a4.md`
- Plan (1..N)
  1) Зафиксировать статусы Find 1–5 в `docs/REPORTS/2026-02-01-console-web-fact-audit.md` с evidence (PR/CI/build).
  2) Создать `docs/CONSOLE_AUDIT/UX_BACKLOG.md` с issues по страницам и ссылками на код.
  3) Обновить inventory docs (Inbox/Calendar) под фактическое поведение.
  4) Обновить `STATE.md` и `STRUCTURE.md` под новые документы и evidence.
- DoD
  - В отчете fact audit у каждого Finding есть статус + evidence.
  - UX backlog создан и связан с inventory docs и кодом.
  - Inventory docs отражают фактическое поведение после фиксов.
  - `STATE.md` и `STRUCTURE.md` актуализированы.
- Checks
  - `git status -sb`
  - `git diff --stat`
- Evidence
  - CI run URLs (PRs #493–#497) + build `4614530`.
  - Ссылки на обновленные docs + `STATE.md` запись.
- Rollback
  - `git revert COMMIT_SHA`
- No-go
  - Не менять код/поведение UI/API.
- Branch / Worktree / Base / Merge / Cleanup
  - Branch: `feat/2026-02-02-console-audit-followup-a4`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-audit-followup-a4`
  - Base: `origin/main`
  - Merge: PR в `main` (doc-only)
  - Cleanup: удалить worktree/branch после merge
- Риски/блокеры
  - Нужны CI/build ссылки для доказательств фиксов.
