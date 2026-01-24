# TP-2026-01-24 — Control Plane canon + Web-first alignment

- **Название/цель:** зафиксировать Control Plane как канон (новый `SPECS/CONTROL_PLANE.md`), привести дорожную карту к Web‑first, и заякорить план фаз.
- **Canon refs:** `Control Plane.md`, `SPECS/ESCALATION.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/TECH_ROADMAP.md`, `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Никаких изменений поведения/кода/БД — только документация.
- Web‑first/Telegram‑fallback не нарушается.
- Нет “god‑file”: ссылки на канон, без дублирования деталей.

## Scope
- Создать `SPECS/CONTROL_PLANE.md` как канон Control Plane.
- Обновить `STRATEGY/TECH_ROADMAP.md` (Web‑first).
- Обновить `STRUCTURE.md` (карта файлов).
- Превратить `/home/zhan/Control Plane.md` в ссылку‑указатель.
- Зафиксировать Task Package и запись в `STATE.md`.

## Out of scope
- Любые UI/Backend изменения.
- Миграции БД, API контракты, тесты.

## Touch-list
- `SPECS/CONTROL_PLANE.md`
- `STRUCTURE.md`
- `STRATEGY/TECH_ROADMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-canon.md`
- `/home/zhan/Control Plane.md`
- `STATE.md`

## Plan
1) Добавить канон‑док `SPECS/CONTROL_PLANE.md` (цели, роли, IA, capabilities, Knowledge Studio, фазы).
2) Привести `STRATEGY/TECH_ROADMAP.md` к Web‑first.
3) Обновить `STRUCTURE.md` (карта).
4) Сжать `/home/zhan/Control Plane.md` до ссылки на канон.
5) Зафиксировать результат в `STATE.md`.

## DoD
- Канон‑док создан и включён в карту.
- Roadmap согласован с Web‑first.
- Pointer‑файл обновлён.
- Task Package и запись в `STATE.md` добавлены.

## Checks
- `rg -n "CONTROL_PLANE" SPECS/CONTROL_PLANE.md STRUCTURE.md STRATEGY/TECH_ROADMAP.md`

## Evidence
- Док‑изменения отражены в `STATE.md` (PLAN/DONE).

## Rollback
- Откатить doc‑изменения.

## No-go
- Любые изменения runtime/DB/контрактов.

## Риски/блокеры
- Нет.

## Branch / Worktree / Merge
- Branch: `docs/control-plane-2026-01-24`
- Worktree: `/home/zhan/worktrees/control-plane-docs`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
