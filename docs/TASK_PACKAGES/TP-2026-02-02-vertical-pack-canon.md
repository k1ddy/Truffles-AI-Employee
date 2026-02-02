# TP-2026-02-02-vertical-pack-canon

- Название/цель: Зафиксировать канон vertical pack readiness (minimum data contract + safe-mode gate) и правила consent/анонимизации для обучения; обновить требования/STATE/STRUCTURE под дальнейшую реализацию.
- Canon refs: `STATE.md` (TODO обязательные данные филиала + валидация), `docs/IMPERIUM_DECISIONS.yaml` (DEC-010/DEC-018/DEC-019/DEC-020), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: truth-first; факты только из packs/tools; LLM не коммитит решения/факты; никаких бизнес-лексиконов в коде; doc-only (без изменений поведения/кода).
- Scope:
  - Добавить DEC-021 (vertical pack readiness + safe-mode gate).
  - Добавить DEC-022 (consent/анонимизация/retention для улучшений).
  - Обновить `STATE.md` (PLAN/GAP по readiness и consent).
  - Обновить `STRUCTURE.md` (активный Task Package).
- Out of scope: код/пакеты/схемы/миграции; любые runtime изменения; новые вертикальные packs; обновление `STRATEGY/REQUIREMENTS.md` (отдельный TP).
- Touch-list:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-vertical-pack-canon.md`
  - `docs/SESSIONS/SESSION-2026-02-02-vertical-pack-canon-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Зафиксировать DEC-021/DEC-022 в `docs/IMPERIUM_DECISIONS.yaml`.
  2) Внести PLAN/GAP в `STATE.md` с ссылками на DEC и TP.
  3) Добавить TP в список активных в `STRUCTURE.md`.
  4) Создать/обновить сессионный лог и индекс.
- DoD:
  - DEC-021/DEC-022 добавлены.
  - `STATE.md` отражает PLAN/GAP и ссылки на TP.
  - `STRUCTURE.md` включает новый TP в активных.
  - Сессионные файлы созданы.
- Checks:
  - `rg -n "DEC-021|DEC-022" docs/IMPERIUM_DECISIONS.yaml`
- Evidence:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-vertical-pack-canon-a1.md`
- Rollback: revert commit (doc-only).
- No-go: любые изменения кода/схем/пакетов; новые runtime-фичи.
- Branch/worktree/base/merge/cleanup:
  - Branch: `docs/2026-02-02-vertical-pack-canon-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-vertical-pack-canon-a1`
  - Base: `origin/main`
  - Merge: doc-only fast-forward to `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: нет (doc-only).
