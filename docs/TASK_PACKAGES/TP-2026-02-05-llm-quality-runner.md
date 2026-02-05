# TP-2026-02-05-llm-quality-runner

## Название/цель
Единый LLM quality runner: генерирует LLM-сценарии, шлет в webhook, собирает decision_meta/trace, считает state-aware метрики, добавляет LLM-judge и coverage-метрики, фиксирует summary/baseline для непрерывного улучшения.

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
- Coverage-метрики (state/intent/modality/noise/manager/tool-path) для хаос-контроля.
- LLM-judge (non-blocking, выборочная семантическая проверка).
- Summary + baseline (delta-метрики между прогонами).

## Out of scope
- Изменения core-пайплайна/поведения.
- Изменения packs/policy контента.
- Миграции БД, деплой, CI livecheck.

## Touch-list
- `ops/diagnose.py`
- `scripts/booking_dialog_scenarios.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/results/booking_quality.json` (new)
- `docs/SESSIONS/SESSION-*.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1) Зафиксировать контракт оценки: правила по decision_meta/trace + state-aware (manager_active/resolve) + allowed outcomes.
2) Усилить сценарии: ожидания/coverage-теги + tolerated reply_type/action наборы.
3) Добавить coverage-метрики и reason taxonomy для mismatch/хаоса.
4) Добавить LLM-judge (non-blocking): выборка + reason codes + summary.
5) Обновить runbook (команды + артефакты + judge).
6) Smoke run + live run (evidence, baseline/history).
7) Обновить `STATE.md` с evidence (Brain/Top Architect до merge).

## DoD
- Runner создаёт один run-dir с `scenarios.json`, `responses.jsonl`, `summary.json`.
- Оценка корректна для manager_active (нет bot_response = PASS) и после resolve (бот отвечает).
- Summary содержит метрики + delta к baseline + coverage + judge summary.
- LLM-judge включается выборочно (non-blocking) и сохраняет reason codes.
- Evidence зафиксирован и отражен в `STATE.md`.

## Checks
- `python3 ops/diagnose.py llm-quality --help`
- `python3 ops/diagnose.py llm-quality --dry-run --count 1 --mode template`
- `python3 ops/diagnose.py llm-quality --count 5 --mode llm --judge-sample 0.1` (allowlist JIDs)

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
- Branch: `feat/2026-02-05-llm-quality-judge-a1`
- Worktree: `/home/zhan/worktrees/2026-02-05-llm-quality-judge-a1`
- Base ref: `origin/main`
- Merge policy: PR -> main (Brain/Top Architect)
- Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch

## Риски/блокеры
- LLM генерация может вернуть невалидный JSON (нужны retries/batch).
- Manager_active может маскировать reply-rate без state-aware оценки.
- Отсутствие webhook_secret/instance_id ломает run (нужно авто-резолвить).
- LLM-judge требует ключей/лимитов; при отсутствии работает как SKIP (non-blocking).
