# TP-2026-01-30 — Canon Alignment: Expected-Reply, Reset, Signal Sources

## Название/цель
Обновить канон-документы, чтобы они соответствовали текущей архитектуре и согласованному плану: expected-reply matcher, reset semantics, signal snapshot и контролируемый lexical fallback в consult.

## Invariant
- Hard-LAW/policy/pending остаются pre-LLM и fail-closed.
- decision_meta/decision_trace пишутся на каждый вход и ранний выход.
- Оркестрация не переносится в entrypoints/_legacy.py; порядок стадий не меняется.
- Изменения только в документах.

## Scope
- Обновление канона: expected-reply mismatch, reset semantics (pending), signal sources/snapshot, consult lexical fallback.
- Синхронизация описания с фактическими модулями и планом P0.

## Out of scope
- Изменения кода, тестов, или data packs.
- DEC/архитектурные перестройки.
- Обновление STATE.md.

## Touch-list
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/SESSIONS/SESSION-2026-01-30-canon-contradictions-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать противоречия между планом и каноном.
2. Обновить SPECS: expected-reply mismatch, reset semantics, signal snapshot, consult fallback.
3. Прогнать quick consistency check (rg) по измененным секциям.
4. Обновить session log и SESSION_INDEX.

## DoD
- Канон отражает: expected-reply mismatch gate, pending reset semantics, signal sources/snapshot, consult lexical fallback.
- Нет противоречий в описании consult resolver/lexicon roles.
- Только doc-изменения.

## Checks
- `rg -n "expected-reply|reset|signal snapshot|lexical fallback" SPECS/CONSULTANT.md SPECS/ESCALATION.md SPECS/ARCHITECTURE.md SPECS/SYSTEM_REFERENCE.md`

## Evidence
- Диффы измененных канон-доков + session log.

## Rollback
- `git revert COMMIT_SHA`

## No-go
- Любые code changes.
- Любые изменения stage order или runtime behavior.

## Branch/worktree
- Branch: `docs/2026-01-30-canon-contradictions-a1`
- Worktree: `/home/zhan/worktrees/2026-01-30-canon-contradictions-a1`
- Base: `origin/main`
- Merge policy: doc-only fast-forward to main
- Cleanup: Brain

## Риски/блокеры
- Конфликт с уже открытыми сессиями по агенту.
- Неочевидные расхождения между SPECS и реализацией (требуют отдельного TP).
