# TP-2026-01-24 — Knowledge Studio DEC (source of truth + safe publish)

- **Название/цель:** зафиксировать архитектурное решение по Knowledge Studio: DB‑registry как SoT, генерация pack‑файлов при publish, безопасный publish/rollback, и модель capabilities как отдельная сущность.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/ESCALATION.md`, `STRATEGY/REQUIREMENTS.md`, `docs/IMPERIUM_DECISIONS.yaml`, `STATE.md`.

## Invariant
- Нет изменений в коде/БД/контрактах — только документы.
- Knowledge publish остаётся fail‑closed.
- Web‑first не нарушается.

## Scope
- Добавить DEC‑014 (Knowledge Studio publish pipeline).
- Добавить DEC‑015 (capabilities модель).
- Обновить `STRUCTURE.md` (active TP).
- Зафиксировать результат в `STATE.md`.

## Out of scope
- Реализация registry/pack генерации.
- UI/Backend изменения.

## Touch-list
- `docs/IMPERIUM_DECISIONS.yaml`
- `docs/TASK_PACKAGES/TP-2026-01-24-knowledge-studio-dec.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Зафиксировать DEC‑014 и DEC‑015 в `docs/IMPERIUM_DECISIONS.yaml`.
2) Добавить Task Package в активный список.
3) Записать PLAN/DONE в `STATE.md`.

## DoD
- DEC‑014/DEC‑015 добавлены.
- Task Package в `STRUCTURE.md`.
- `STATE.md` отражает решение.

## Checks
- `rg -n "DEC-014|DEC-015" docs/IMPERIUM_DECISIONS.yaml`

## Evidence
- Док‑изменения отражены в `STATE.md`.

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
