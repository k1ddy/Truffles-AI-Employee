# TP-2026-02-02-tp-batch-create

- Название/цель: Создать три Task Package (vertical pack kit, minimum data contract + safe-mode, consent/anon pack candidates) и зафиксировать их в `STATE.md`/`STRUCTURE.md`.
- Canon refs: `STATE.md` (NOW/PLAN), `docs/IMPERIUM_DECISIONS.yaml` (DEC-021/DEC-022), `STRATEGY/REQUIREMENTS.md`.
- Invariant: doc-only; truth-first; факты только из packs/tools; без изменений поведения/кода.
- Scope:
  - Создать TP для vertical pack kit (выбор вертикали как блокер).
  - Создать TP для runtime minimum data contract + safe-mode gate.
  - Создать TP для auto-ingest approvals: consent/anon + pack candidates.
  - Обновить `STATE.md` (PLAN) и `STRUCTURE.md` (active TP list).
  - Сессионный лог + индекс.
- Out of scope: код/схемы/пакеты/миграции.
- Touch-list:
  - `docs/TASK_PACKAGES/TP-2026-02-02-vertical-pack-kit.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-minimum-data-safe-mode.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-learning-consent-pack-candidates.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-tp-batch-create-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Создать три TP с полным шаблоном.
  2) Добавить PLAN entries в `STATE.md`.
  3) Зарегистрировать TP в `STRUCTURE.md`.
  4) Обновить сессионный лог и индекс.
- DoD:
  - 3 TP созданы и перечислены в `STRUCTURE.md`.
  - `STATE.md` отражает планы с ссылками на TP.
  - Сессионные файлы созданы.
- Checks:
  - `rg -n "TP-2026-02-02-vertical-pack-kit|TP-2026-02-02-minimum-data-safe-mode|TP-2026-02-02-learning-consent-pack-candidates" STRUCTURE.md`
- Evidence:
  - созданные TP + `STATE.md` + `STRUCTURE.md`.
- Rollback: revert commit.
- No-go: любые runtime/код изменения.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-tp-batch-create-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-tp-batch-create-a1`
  - Base: `main`
  - Merge: doc-only fast-forward to `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: выбор вертикали для pack kit (медицина/аптека/спорт) — нужен владелец.
