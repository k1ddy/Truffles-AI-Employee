# TP-2026-01-28 — Consultant canon alignment (ChatGPT-like + media/noise)

## Название/цель
Обновить канон консультанта и эскалации под требования ChatGPT‑5‑like поведения, медиа/аудио/шум, quiet‑hours и запрет demo_salon‑only подхода.

## Invariant
- Контракт FACT/COLLECT/HANDOFF не меняется.
- Hard‑LAW/policy/opt‑out выше consult/booking/info.
- Pack‑first: никаких выдуманных фактов/скидок/медицины.
- Никаких demo_salon‑only правил или “подгон под тесты”.

## Scope
- Canon/процесс: правила поведения (memory/goal‑lock/quiet‑hours/шум/медиа/аудио/переходы в pending), порядок предупреждений, onboarding для новых агентов.
- Док‑фиксация “demo_salon = тестовый pack, не целевая реализация”.

## Out of scope
- Любые изменения кода/тестов/CI/данных.
- Изменения архитектуры без DEC.

## Touch-list (файлы)
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/SESSIONS/SESSION-2026-01-28-consultant-canon-alignment-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Сверить требования пользователя с текущим каноном (SPECS/CONSULTANT.md, SPECS/ESCALATION.md).
2) Зафиксировать правила: consult‑first, goal‑lock, noise‑handling, quiet‑hours greeting, memory capsule/TTL, media/audio ordering, pending/manager_active notice.
3) Обновить onboarding/diagnose‑first в `SPECS/SYSTEM_REFERENCE.md` и `docs/CONSULTANT_CODEMAP.md`.
4) Обновить session log + session index.

## DoD
- Канон описывает все новые требования без ослабления safety.
- Есть явная фиксация, что demo_salon — тестовый pack и не цель.
- Добавлены инструкции для новых агентов (onboarding/diagnose‑first).
- Session log + index обновлены.

## Checks
- `scripts/session_check.sh`

## Evidence
- Diff в указанных документах + session log.
- Запись в `STATE.md` (если Brain решит зафиксировать как факт).

## Rollback
- Откатить док‑коммит.

## No-go
- Любая правка кода или тестов.
- Любое ослабление Hard‑LAW/policy/pack‑first.
- Любые demo_salon‑specific правила.

## Риски/блокеры
- Риск: противоречия между SPECS/CONSULTANT и SPECS/ESCALATION → проверить согласованность формулировок.

## Branch/Worktree
- Branch: `feat/2026-01-28-consultant-canon-alignment-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-consultant-canon-alignment-a1`
- Base ref: `origin/main`
- Merge policy: doc‑only fast‑forward to `main`
- Cleanup: после merge удалить branch/worktree
