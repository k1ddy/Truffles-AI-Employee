# TP-2026-02-18-wave3-marketing-mvp-control-plane-a88

- Название/цель: Запустить Marketing MVP в Console Plane (campaign + audience + send + delivery diagnostics + reply context), без потери контекста консультанта.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP, `SPECS/CONTROL_PLANE.md` (roles/tenant fail-closed), `SPECS/ARCHITECTURE.md` (outbox-first/idempotency/trace-meta), `SPECS/CONSULTANT.md` (FACT/COLLECT/HANDOFF), `TECH.md` (outbox/runtime guard), `contracts/capabilities/capabilities.v1.jsonschema`.
- CA_ID: N/A.

## Invariant
- Marketing отправки только через существующий outbox/idempotency контур.
- Любая массовая операция только через `dry_run -> confirmation -> execute`.
- Консультант обязан видеть контекст кампании и корректно обрабатывать reply.

## Scope
- Модель данных MVP:
  - campaigns (scope: client/branch)
  - audience snapshots/segment criteria
  - campaign deliveries (queued/sent/failed/replied)
  - campaign message context link (outbound -> inbound reply correlation)
- API:
  - create/update/pause/resume campaign
  - preview audience (dry-run)
  - execute send (confirmed)
  - delivery diagnostics + retry safe path
- UI:
  - campaign list/detail
  - preview + confirm send
  - delivery diagnostics panel
- Runtime:
  - inbound reply должен не терять campaign context в `decision_meta/trace`.

## Out of scope
- Полноценная CDP/ML-сегментация.
- Автоматическая оптимизация частоты/AB testing.
- Финальная legal/compliance автоматизация для всех юрисдикций.

## Touch-list
- `truffles-api/migrations/` (new campaign tables)
- `truffles-api/app/routers/console.py` (marketing endpoints)
- `truffles-api/app/schemas/console.py` (marketing schemas)
- `truffles-api/app/services/*` (marketing orchestration + context resolver)
- `truffles-api/app/routers/webhook/decision.py` (reply context wiring)
- `truffles-api/tests/test_console_*.py` (contract/rbac/integration)
- `truffles-api/tests/test_message_endpoint.py` (reply-context behavior)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/` (new marketing pages)
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_AUDIT/` (new pages + role audit)
- `STATE.md`

## Plan
1. Зафиксировать MVP contracts (data + API + RBAC + dry-run/execute flow).
2. Реализовать backend entities/endpoints с tenant isolation и confirmation gate.
3. Подключить outbox delivery + idempotency + failure diagnostics.
4. Привязать inbound replies к campaign context в decision meta/trace.
5. Добавить UI flow (preview/send/diagnostics/pause).
6. Прогнать deterministic + local-first behavior checks.
7. Зафиксировать evidence (API/UI/tests/SQL/trace/meta).

## DoD
- Platform/Owner/Admin могут запускать branch-scoped кампанию через confirm flow.
- Для каждой отправки есть delivery status (`queued/sent/failed`) и безопасный retry.
- Ответ клиента на маркетинговое сообщение обрабатывается в корректном campaign context.
- Нет cross-tenant/cross-branch утечек аудитории и отправок.
- OpenAPI/types синхронизированы.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/routers/webhook/decision.py`
- `pytest -q truffles-api/tests/test_console_rbac.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "campaign or marketing or expected_reply"`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- Local realism contour for reply-context:
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id marketing-context-<id>`

## Evidence
- Migration DDL + schema diff evidence
- API evidence: campaign create/preview/execute/status logs
- SQL evidence: campaigns + deliveries + correlation rows
- decision evidence:
  - `decision_meta` on inbound reply has campaign context fields
  - `decision_trace` records campaign-aware stage
- UI evidence: campaign preview/send/diagnostics screenshots
- `docs/REPORTS/<date>-wave3-marketing-mvp-control-plane-a88.md`
- `STATE.md` FACT/GAP update

## Rollback
- Feature flag disable for marketing endpoints/UI.
- Revert migration only via explicit backward migration script (no destructive manual DB edits).
- Pause all active campaigns before rollback.

## No-go
- Нельзя запускать campaign execute при runtime `guard.status=critical`.
- Нельзя отправлять массовые сообщения без dry-run preview + confirmation.
- Нельзя принимать campaign rollout без reply-context evidence в `decision_meta/trace`.
- Нельзя встраивать маркетинг хардкодом в pack/runtime без контрактов и тестов.

## Риски/блокеры
- Runtime backlog (outbox critical) блокирует безопасный массовый send.
- Legal/consent ограничения требуют явной opt-in/quiet-hours модели.
- Без anti-spam caps возможны UX/brand риски для клиентов.
- Нужен owner/admin auth-state для стабильной e2e-приемки.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave3-marketing-mvp-control-plane-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave3-marketing-mvp-control-plane-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
