# TP-2026-02-04-consultant-livecheck

## Название/цель
Проверить фактические ответы консультанта в live-диалоге (CA06 consult; при готовности — CA05 booking-commit) и зафиксировать evidence.

## Canon refs
- `STATE.md` NOW: CA05 booking-commit live-check blocked by minimum_data_contract; CA06 consult уже был, нужна повторная фактическая проверка.
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md` (Live-check SOP)

## Invariant
- Pack-first: ответы только из pack/правил, без новых фактов.
- decision_meta/decision_trace сохраняются для live-check.
- No orchestration in entrypoints и `_legacy.py`.

## Scope
- Live-check CA06 (consult) на allowlist.
- При готовности (health + minimum_data_contract + provider ready) — CA05 booking-commit.
- Сохранить evidence (livecheck output + meta/trace/outbox).
- Обновить session log + при необходимости `STATE.md` (GAP/FACT).

## Out of scope
- Любые изменения кода/архитектуры.
- Миграции БД.
- Обновление packs/policy.

## Touch-list
- `docs/SESSIONS/SESSION-2026-02-04-consultant-livecheck-a6.md`
- `docs/SESSION_INDEX.md`
- `STATE.md` (только при необходимости фиксации GAP/FACT)

## Plan
1) Preflight: environment check + `/admin/health` + minimum_data_contract status.
2) Проверить allowlist/TEST_MODE/секреты (через livecheck preflight).
3) Запустить `livecheck-auto --suite ca06-consult`.
4) Если gates готовы — запустить `livecheck-auto --suite ca05-booking-commit`.
5) Сохранить evidence (stdout + trace/meta/outbox summary).
6) Обновить session log + при необходимости `STATE.md`.

## DoD
- Есть conversation_id/message_id + decision_meta/trace для CA06.
- Outbox status зафиксирован (queued/sent/failed) где применимо.
- Если блокирующие условия — записан GAP с evidence.

## Checks
- `curl -s http://localhost:8000/admin/health`
- `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca06-consult --client-slug demo_salon --base-url http://localhost:8000 --noise none`
- (опционально) `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca05-booking-commit --client-slug demo_salon --base-url http://localhost:8000 --noise none`

## Evidence
- stdout live-check (stdout file в `/tmp`).
- conversation_id/message_id + decision_meta/trace.
- outbox summary/rows (если есть).

## Rollback
- Нет (doc-only). При необходимости откатить commit.

## No-go
- allowlist отсутствует.
- TEST_MODE выключен.
- missing webhook secret/admin token.
- Красный CI (если затрагивается).

## Branch + Worktree
- Branch: `feat/2026-02-04-consultant-livecheck-a6`
- Worktree: `/home/zhan/worktrees/2026-02-04-consultant-livecheck-a6`
- Base ref: `origin/main`
- Merge policy: PR -> main (merge Brain)
- Cleanup: Brain удаляет ветку и worktree после merge
