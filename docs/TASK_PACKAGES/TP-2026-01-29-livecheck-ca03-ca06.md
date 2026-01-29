# TP-2026-01-29-livecheck-ca03-ca06

## Название/цель
Стабилизировать CA03/CA06 live-check: сохранить trace для info_class и обеспечить short-circuit consult при запросах «совет + цена/время» без генерации новых фактов. Уточнить CA04 live-check кейс на услугу, которой нет в demo pack.

## Invariant
- Pack-first: консультации и факты только из паков/правил (LLM не генерирует факты).
- decision_trace/decision_meta сохраняются на ранних возвратах и при short-circuit.
- Никакой оркестрации в entrypoints и `_legacy.py`.

## Scope
- Уточнить эвристику force-consult для запросов с consult-cue + price/duration/hours.
- Добавить `info_class` в критический retention decision_trace.
- Разрешить запуск `Livecheck Only` на ветках через явный флаг (без снятия гейта для main).
- Обновить CA04 live-check сервис на гарантированно отсутствующую услугу в demo pack.
- Обновить session/docs для новой сессии.

## Out of scope
- Переписывать intent decomposition/LLM промпты.
- Менять контракты паков или policy rules.
- Любые миграции БД.

## Touch-list
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/routers/webhook/trace.py`
- `.github/workflows/livecheck-only.yml`
- `ops/diagnose.py`
- `docs/TASK_PACKAGES/TP-2026-01-29-livecheck-ca03-ca06.md`
- `docs/SESSIONS/SESSION-2026-01-29-livecheck-ca03-ca06-a2.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Зафиксировать текущие симптомы CA03/CA06 (лог live-check, trace retention).
2) Исправить retention: добавить `info_class` в `DECISION_TRACE_CRITICAL_STAGES`.
3) Исправить consult heuristics: разрешить consult_intent при consult-cue + price/duration/hours (без booking).
4) Добавить флаг `allow_non_main` для `Livecheck Only`.
5) Обновить CA04 live-check case на отсутствующую услугу.
6) Прогнать локальные тесты для CA03/CA06.
7) Открыть PR и запустить CI `Livecheck Only` с `allow_non_main=true`.

## DoD
- CA03: decision_trace содержит `info_class` и `truth_gate` на live-check.
- CA06: consult short-circuit фиксируется в `consult_flow` trace.
- CA04: live-check `service_not_found` использует услугу, которой нет в demo pack.
- Локальные тесты для CA03/CA06 проходят.
- Livecheck Only зелёный и приложен evidence.

## Checks
- `pytest -q truffles-api/tests/test_demo_salon_eval.py -k "truth_first_info_bundle or consult_pack_only_and_short_circuit"`
- CI: `Livecheck Only` (workflow_dispatch) на PR с `allow_non_main=true`.

## Evidence
- Локальные тесты (stdout).
- CI run URL (Livecheck Only) + `livecheck-evidence.md` артефакт.
- Обновление `STATE.md` (если требуется) с evidence ссылками.

## Rollback
- Откатить PR (git revert) и перезапустить Livecheck Only.

## No-go
- Красный CI/live-check.
- Отсутствует trace/meta для CA03/CA06.

## Риски/блокеры
- Эвристики consult могут пере-матчить price-only запросы; отслеживать через live-check.
- Если live-check недоступен (allowlist), требуется согласованный симуляционный прогон.

## Branch + Worktree
- Branch: `feat/2026-01-29-livecheck-ca03-ca06-a2`
- Worktree: `/home/zhan/worktrees/2026-01-29-livecheck-ca03-ca06-a2`
- Base ref: `origin/main`
- Merge policy: PR -> main (merge только Brain)
- Cleanup: Brain удаляет ветку и worktree после merge
