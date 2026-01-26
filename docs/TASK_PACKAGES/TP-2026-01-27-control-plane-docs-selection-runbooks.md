# TP-2026-01-27 — Control Plane docs refresh + tenant selection plan + role runbooks

- **Название/цель:** привести Control Plane docs в соответствие с реальным кодом, добавить план полного Company→Client→Branch selection в UI и короткие runbooks по ролям.
- **Invariant:** не менять поведение/код/контракты; только документация и ссылки.
- **Scope:** `docs/CONSOLE_GUIDE.md`, `SPECS/CONTROL_PLANE.md` (уточнение текущего статуса и план), ссылки на код; краткие runbooks по ролям.
- **Out of scope:** изменения API/DB/UI; миграции; CI/деплой.
- **Touch-list:**
  - `docs/CONSOLE_GUIDE.md`
  - `SPECS/CONTROL_PLANE.md`
  - `STRUCTURE.md`
  - `STATE.md`
- **Plan:**
  1) Сверить текущую реализацию tenant/role в коде (console-web + console API).
  2) Обновить docs (CONSOLE_GUIDE + CONTROL_PLANE) на основании кода.
  3) Добавить план Company→Client→Branch selection и runbooks по ролям.
  4) Зарегистрировать TP в STRUCTURE/STATE.
- **DoD:**
  - Документы обновлены и не противоречат коду (есть ссылки на реальные файлы).
  - План Company→Client→Branch selection описан пошагово.
  - Runbooks по ролям (global admin/owner/admin/manager) добавлены.
- **Checks:** не требуется (docs-only).
- **Evidence:** diff в репозитории.
- **Rollback:** вернуть изменения в документах (git revert/checkout).
- **No-go:** не менять код, схемы или runtime поведение; не трогать `docs/CONSULTANT_CODEMAP.md`.
- **Риски/блокеры:** нет.
