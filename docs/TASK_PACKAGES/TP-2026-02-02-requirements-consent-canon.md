# TP-2026-02-02-requirements-consent-canon

- Название/цель: Обновить `STRATEGY/REQUIREMENTS.md` по DEC-021/DEC-022 (minimum data contract + safe-mode gate; consent/анонимизация/retention) и зафиксировать в `STATE.md`.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-021/DEC-022), `STRATEGY/REQUIREMENTS.md`, `STATE.md` (PLAN readiness/consent), `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: truth-first; факты только из packs/tools; LLM не коммитит решения/факты; никаких бизнес-лексиконов в коде.
- Scope:
  - Добавить в `STRATEGY/REQUIREMENTS.md` требования minimum data contract + safe-mode gate.
  - Добавить требования consent/анонимизации/retention и opt-in cross-tenant reuse.
  - Обновить `STATE.md` (ссылку на обновление требований/DEC, без evidence).
- Out of scope: код/пакеты/схемы/миграции; runtime поведение; вертикальные packs.
- Touch-list:
  - `STRATEGY/REQUIREMENTS.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-requirements-consent-canon-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Внести minimum data contract + safe-mode gate в раздел "Точность фактов".
  2) Внести consent/анонимизация/retention в раздел "Мультитенант и данные".
  3) Обновить `STATE.md` (PLAN/GAP с ссылкой на DEC-021/DEC-022 и этот TP).
  4) Обновить сессионный лог и индекс.
- DoD:
  - `STRATEGY/REQUIREMENTS.md` отражает DEC-021/DEC-022 без противоречий.
  - `STATE.md` обновлён планом.
  - Сессионные файлы созданы и статус done в том же коммите.
- Checks:
  - `rg -n "minimum data|safe-mode|consent|аноним" STRATEGY/REQUIREMENTS.md`
  - `rg -n "DEC-021|DEC-022" docs/IMPERIUM_DECISIONS.yaml`
- Evidence:
  - `STRATEGY/REQUIREMENTS.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-requirements-consent-canon-a1.md`
- Rollback: revert commit.
- No-go: любые изменения кода/схем/пакетов; live-check.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-requirements-consent-canon-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-requirements-consent-canon-a1`
  - Base: `main`
  - Merge: PR -> main
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: нет.
