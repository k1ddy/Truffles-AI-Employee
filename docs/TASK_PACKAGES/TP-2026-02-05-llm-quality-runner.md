# TP-2026-02-05-llm-quality-runner

## Название/цель
Единый LLM quality runner: генерирует LLM-сценарии, шлет в webhook, собирает decision_meta/trace, считает state-aware метрики и фиксирует summary/baseline для непрерывного улучшения.

## Canon refs
- `STATE.md` (GAP: booking dialogs missing replies/unknown_state).
- `STRATEGY/REQUIREMENTS.md`.
- `SPECS/CONSULTANT.md`.
- `SPECS/SYSTEM_REFERENCE.md`.
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
- `AGENTS.md` (P0/P1/P2 fitness + session rules).

## Invariant
- FACT/COLLECT/HANDOFF сохраняется.
- Hard-LAW/policy gates остаются жесткими.
- decision_meta/trace пишутся на ранних возвратах.
- `_legacy.py` = adapter-only, без оркестрации.
- Stage order snapshot не меняется.

## Scope
- State-aware LLM quality runner (scenario -> webhook -> trace/meta -> metrics -> summary).
- Симуляция manager_active/resolve в тестах и корректная оценка режимов.
- Summary + baseline (delta-метрики между прогонами).

## Out of scope
- Изменения core-пайплайна/поведения.
- Изменения packs/policy контента.
- Миграции БД, деплой, CI livecheck.

## Touch-list
- `ops/diagnose.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/results/booking_quality.json` (new)
- `docs/SESSIONS/SESSION-*.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1) Зафиксировать контракт оценки: правила по decision_meta/trace + state-aware (manager_active/resolve).
2) Добавить runner (единый output_dir + summary + baseline + delta).
3) Добавить симуляцию manager_active/resolve в runner.
4) Обновить runbook (команды + артефакты).
5) Smoke run + один live run (evidence).
6) Обновить `STATE.md` с evidence (Brain/Top Architect до merge).

## DoD
- Runner создаёт один run-dir с `scenarios.json`, `responses.jsonl`, `summary.json`.
- Оценка корректна для manager_active (нет bot_response = PASS) и после resolve (бот отвечает).
- Summary содержит метрики + delta к baseline.
- Evidence зафиксирован и отражен в `STATE.md`.

## Checks
- `python3 ops/diagnose.py llm-quality --help`
- `python3 ops/diagnose.py llm-quality --dry-run`
- `python3 ops/diagnose.py llm-quality --count 5 --mode llm` (allowlist JIDs)

## Evidence
- `/tmp/booking_quality/20260205-045542/summary.json` + `responses.jsonl` + `scenarios.json` + `trace_bundle.jsonl`.
- `ops/results/booking_quality.json` baseline.
- запись в `STATE.md`.

## Rollback
- revert commit(s).

## No-go
- Оркестрация в entrypoints/_legacy.py.
- Ослабление hard-LAW/policy.
- Изменение порядка стадий без DEC+tests.

## Branch + Worktree
- Branch: `feat/2026-02-05-llm-quality-runner-a1`
- Worktree: `/home/zhan/worktrees/2026-02-05-llm-quality-runner-a1`
- Base ref: `origin/main`
- Merge policy: PR -> main (Brain/Top Architect)
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch

## Риски/блокеры
- LLM генерация может вернуть невалидный JSON (нужны retries/batch).
- Manager_active может маскировать reply-rate без state-aware оценки.
- Отсутствие webhook_secret/instance_id ломает run (нужно авто-резолвить).
