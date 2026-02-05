# TP-2026-02-05-llm-quality-p1p4

## Название/цель
Доделать LLM quality runner: хаос‑карта покрытия + tool‑sandbox хуки + регрессионные гейты/таксономия ошибок, чтобы стабильнее выявлять некорректное поведение в booking‑диалогах.

## Canon refs
- `STATE.md` (GAP: booking dialog scenario runs missing replies/unknown_state).
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
- `SPECS/CONSULTANT.md`.
- `SPECS/SYSTEM_REFERENCE.md`.
- `STRATEGY/REQUIREMENTS.md`.
- `AGENTS.md` (P0/P1/P2 fitness + session rules).

## Invariant
- FACT/COLLECT/HANDOFF сохраняется.
- Hard-LAW/policy gates остаются жесткими.
- decision_meta/trace пишутся на ранних возвратах.
- `_legacy.py` = adapter-only, без оркестрации.
- Stage order snapshot не меняется.

## Scope
- Chaos‑coverage оси (state/intent/language/modality/noise/tool success/failure) + метрики покрытия.
- Tool‑sandbox hooks для booking confirm/cancel/calendar paths в рамках runner.
- Таксономия ошибок (expectation vs canon vs code vs data) + регрессионные гейты и тренды.
- Обновление runbook и evidence фиксирование в `STATE.md`.

## Out of scope
- Изменения core‑пайплайна/поведения.
- Изменения packs/policy контента.
- Миграции БД, деплой, CI livecheck.

## Touch-list
- `ops/diagnose.py`
- `scripts/booking_dialog_scenarios.py` (если нужен chaos‑labeling)
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/results/booking_quality.json`
- `docs/SESSIONS/SESSION-*.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1) Добавить chaos‑осевые метки в генератор/runner и посчитать покрытие.
2) Встроить tool‑sandbox hooks (confirm/cancel/calendar) в runner без влияния на core.
3) Добавить таксономию ошибок и регрессионные гейты (baseline diff + thresholds).
4) Обновить runbook (правила/команды/артефакты).
5) Прогон allowlist (LLM, sample judge) + фиксация evidence в `STATE.md`.

## DoD
- Summary содержит метрики по chaos‑осям + таксономию ошибок + regression/threshold статус.
- Tool‑hooks отражены в trace/meta и не ломают flow.
- Runbook обновлён и описывает новые метрики/гейты.
- Evidence зафиксирован и отражен в `STATE.md`.

## Checks
- `python3 ops/diagnose.py llm-quality --help`
- `python3 ops/diagnose.py llm-quality --dry-run`
- `python3 ops/diagnose.py llm-quality --mode llm --count 5 --scenario-coverage booking,info,interrupt,handoff`

## Evidence
- `/tmp/booking_quality/20260205-114556/summary.json` + `responses.jsonl` + `scenarios.json` + `trace_bundle.jsonl`.
- `ops/results/booking_quality.json` (baseline/history).
- запись в `STATE.md`.

## Rollback
- revert commit(s).

## No-go
- Оркестрация в entrypoints/_legacy.py.
- Ослабление hard-LAW/policy.
- Изменение порядка стадий без DEC+tests.

## Branch + Worktree
- Branch: `feat/2026-02-05-llm-quality-p1p4-a1`
- Worktree: `/home/zhan/worktrees/2026-02-05-llm-quality-p1p4-a1`
- Base ref: `feat/2026-02-05-llm-quality-evidence-a1`
- Merge policy: PR -> main (Brain/Top Architect)
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch

## Риски/блокеры
- Tool‑hooks могут требовать секреты/инстанс; нужен safe‑mode/skip.
- LLM генерация может вернуть невалидный JSON (нужны retries/batch).
- Регрессионные гейты могут давать false‑positive при изменении ожиданий.
