# Task Package: Case dedup + open filter (4h cooldown)

Title/Goal
- Убрать визуальные дубли в Console (по умолчанию показывать только open cases).
- Ввести 4‑часовой cooldown: при повторной эскалации на того же клиента переоткрывать последнюю resolved заявку вместо создания новой.
- Сохранить бесшовную синхронизацию Console ↔ Telegram ↔ WhatsApp.

Canon refs
- AGENTS.md
- STATE.md (P1: убрать дубли заявок на одного клиента)
- STRUCTURE.md
- STRATEGY/REQUIREMENTS.md
- SPECS/ESCALATION.md
- SPECS/SYSTEM_REFERENCE.md
- docs/CONSOLE_GUIDE.md
- contracts/console_api/openapi.v1.yaml

Invariant
- Открытая заявка = active/pending handover; pending/manager_active без handover запрещены.
- Telegram topic для клиента сохраняется; новые уведомления идут в тот же topic.
- Trace/meta пишутся для новых гейтов; entrypoints остаются тонкими.

Scope
- Backend: 4h cooldown по клиенту при эскалации (reopen resolved handover вместо новой).
- Console API: `status=open` (эквивалент pending+active) и default filter в UI.
- Docs/contracts/tests обновлены.

Out of scope
- Изменения провайдера/инфры.
- Миграции БД, если можно без них.
- Изменение Telegram UX или кнопок.

Touch-list
- truffles-api/app/services/escalation_service.py
- truffles-api/app/services/state_service.py
- truffles-api/app/routers/console.py
- truffles-api/app/routers/webhook/decision.py (trace)
- console-web/src/components/CaseList.tsx
- contracts/console_api/openapi.v1.yaml
- console-web/src/types/api.generated.ts
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-02-01-case-dedup.md

Plan
1) Добавить поиск последней resolved заявки по клиенту/каналу в окне 4 часа.
2) Реализовать reopen: status->pending, очистить resolved_* и SLA поля, обновить timestamps/assignment, сохранять Telegram topic.
3) Добавить `status=open` в /cases и UI default filter.
4) Добавить trace для cooldown‑гейта и обновить docs/contracts.
5) Тесты + lint + evidence.

DoD
- При повторной эскалации в течение 4h не создаётся новая заявка, а переоткрывается последняя resolved.
- Console по умолчанию показывает open cases (pending/active).
- Telegram topic и handover синхронизированы.
- Тесты/линт проходят, контракты актуальны.

Checks
- pytest -q truffles-api/tests/test_state_service.py -k "handover_dedupe"
- pytest -q truffles-api/tests/test_console_cases_helpers.py -k "status_open"
- npm --prefix console-web run generate:api
- npm --prefix console-web run lint

Evidence
- /tmp/console_case_dedup_pytest_20260201.txt
- /tmp/console_case_status_open_pytest_20260201.txt
- /tmp/console_web_generate_api_20260201.txt
- /tmp/console_web_lint_case_dedup_20260201.txt
- STATE.md updated by Brain/Top Architect with evidence.

Rollback
- git revert COMMIT_SHA

No-go
- Нельзя создавать новые handover при наличии open.
- Нельзя ломать trace/meta или Telegram topic связку.
- Нельзя менять поведение через хардкод в entrypoints.

Branch
- feat/2026-02-01-case-dedup-a1

Worktree path
- /home/zhan/worktrees/2026-02-01-case-dedup-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase.

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Возможны устаревшие resolved заявки без conversation.state sync — нужен guard и trace.
- UI может кэшировать результаты без status фильтра — обновить queryKey/params.
