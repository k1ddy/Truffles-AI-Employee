## Название/цель
Полный аудит возможностей системы и консультанта для тестирования и оценки качества, с фиксацией фактов/ограничений в Capabilities Passport.

## Canon refs
- `STATE.md` (NOW: GAP LLM policy core runtime; booking dialog gaps; RU/KZ variants gap)
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSULTANT_CODEMAP.md`
- `STRUCTURE.md`

## Invariant
- Никаких изменений поведения/кода/данных; только документация.
- Не создавать новые файлы без необходимости; обновить существующий документ.

## Scope
- Обновить `docs/CONSULTANT_CODEMAP.md` разделом “Capabilities Passport”.
- Охватить возможности консультанта и системы по всему репо и внешним папкам `/home/zhan` (infrastructure/landing и др.).
- Для каждой возможности: факты/код + тесты/ранбуки + ограничения/GAP.

## Out of scope
- Любые изменения runtime/логики/контрактов.
- Запуск тестов/CI/изменение БД/trace.
- Решения по продукту/архитектуре.

## Touch-list
- `docs/CONSULTANT_CODEMAP.md`
- `docs/SESSIONS/SESSION-2026-02-05-consultant-capabilities-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Провести инвентаризацию возможностей по `truffles-main` + внешним папкам `/home/zhan`.
2) Сгруппировать в Capabilities Passport (каналы, intent/LLM, booking/info/consult, escalation, media/ASR, state/pending, observability/ops, infra).
3) Для каждой группы указать: факт/код, тесты/ранбуки, ограничения/GAP.
4) Обновить `docs/CONSULTANT_CODEMAP.md`.
5) Проверить doc-only требования (session log + session index).

## DoD
- В `docs/CONSULTANT_CODEMAP.md` добавлен раздел “Capabilities Passport” с полным покрытием.
- Каждая capability содержит ссылки на код/контракты/ранбуки/тесты и ограничения/GAP.
- Нет новых файлов; все изменения doc-only.
- Сессионный лог и индекс обновлены.

## Checks
- `scripts/session_check.sh`

## Evidence
- Diff в `docs/CONSULTANT_CODEMAP.md`.
- `git status -sb` и `git diff --stat`.
- Сессионный лог + индекс.

## Rollback
- Откатить commit с изменениями документации.

## No-go
- Не трогать runtime/контракты/DB/trace.
- Не запускать тесты в прод-контейнере.

## Branch / Worktree / Merge
- Branch: `docs/2026-02-05-capabilities-passport-a1`
- Worktree: `/home/zhan/worktrees/2026-02-05-capabilities-passport-a1`
- Base ref: `origin/main`
- Merge policy: doc-only fast-forward в `main`
- Cleanup: удалить worktree и ветку после merge

## Риски/блокеры
- Риск пропуска возможностей в внешних папках `/home/zhan`; всё непроверенное помечать как GAP.
