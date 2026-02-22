# TP-2026-02-21-marketing-pro-v1-a300

- Название/цель: Полная production-реализация Marketing Pro v1 в Console Plane без временных решений: сегментация аудитории, безопасный execute, контроль retry, approval workflow, операционная диагностика и обязательные safety-gates.
- Canon refs: `AGENTS.md`, `STATE.md` (Wave 3/4 marketing entries + runtime gaps), `STRUCTURE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`, `contracts/console_api/openapi.v1.yaml`.
- CA_ID: N/A.

## Invariant
- `No cross-tenant leakage`: все выборки и действия строго в границах `client_id` + `branch_id`.
- `No duplicate recipient`: в одной кампании один `recipient_jid` получает максимум одну доставку.
- `No unsafe execute`: execute запрещен при `health=critical`, при провале preflight, без approval и без preview snapshot.
- `Audit completeness`: create/review/approve/execute/pause/resume/retry всегда фиксируются в `audit_events`.
- `Reply attribution integrity`: inbound reply корректно связывается с campaign delivery в `decision_meta` и `decision_trace`.

## Scope
- Backend:
  - state machine кампаний (`draft -> in_review -> approved -> scheduled|running -> completed|paused|cancelled|failed`);
  - audience engine + сегменты + reason codes;
  - suppression/consent/frequency/permanent-failure фильтры;
  - preflight gate перед execute;
  - execute/retry safety (dedupe + retryable-only);
  - diagnostics + delivery funnel + failure classes;
  - audit hardening и контрактные endpoint-ы.
- Data model:
  - расширение `marketing_campaigns`;
  - новые таблицы: recipients snapshot, consents, suppressions, delivery events.
- Console UI:
  - campaign lifecycle with approval;
  - audience preview table с конкретными клиентами и причинами;
  - preflight result panel;
  - execute/retry UX с прозрачными блокировками.
- Contracts/tests/docs:
  - OpenAPI sync;
  - unit/integration/e2e coverage;
  - Console audit docs for marketing page.

## Out of scope
- ML personalization/LLM content generation.
- Multi-channel beyond WhatsApp.
- Full legal automation for all jurisdictions (v1 только технические consent/suppression gates).

## Product Contract (Marketing Pro v1)
- Every campaign lifecycle:
  1. Audience snapshot is materialized before send.
  2. Preflight is evaluated and stored.
  3. Execute is allowed only for approved + valid preflight campaigns.
  4. Delivery telemetry is observable (`queued/sent/failed/replied` + reasons).
  5. Retry never re-queues permanent provider failures.

## Target Reliability
- Critical invariants: 100% compliance.
- Non-critical operational scenarios: >=95% success rate in deterministic + integration suites.

## Data Model (DDL-level requirements)
1. `marketing_campaigns`:
   - add `status_v2` enum-like text (`draft|in_review|approved|scheduled|running|paused|completed|cancelled|failed`);
   - add `segment_code`, `approved_by`, `approved_at`, `preflight_snapshot` JSONB, `preflight_valid` bool;
   - keep backward compatibility with existing `status` until migration cutover is complete.
2. `marketing_campaign_recipients`:
   - `campaign_id`, `client_id`, `branch_id`, `recipient_jid`, `user_id`, `conversation_id`,
     `reason_codes` JSONB, `suppressed` bool, `suppression_reasons` JSONB, timestamps;
   - unique index `(campaign_id, recipient_jid)`.
3. `marketing_consents`:
   - `client_id`, `recipient_jid`, `status` (`opt_in|opt_out`), `source`, `changed_at`.
4. `marketing_suppressions`:
   - `client_id`, `recipient_jid`, `reason`, `source`, `expires_at`, `active`.
5. `marketing_delivery_events`:
   - timeline of delivery transitions and retry decisions (`event_type`, `payload`, `recorded_at`).

## Audience & Segments (v1 required)
- `reactivation_30_120`: last visit in `[30,120]` days, no future booking.
- `no_show_recovery_14d`: no-show in last 14 days, no rebooking.
- `engaged_no_booking_7d`: recent service/pricing engagement, no booking commit.
- For each selected recipient persist machine-readable reasons (`reason_codes`) and suppression reasons.

## Preflight Gates (hard block)
- Runtime health gate (`admin/health`): reject execute when critical.
- Campaign state gate: only `approved|scheduled` can execute.
- Audience gate: recipients snapshot exists and `eligible_count > 0`.
- Compliance gate: consent + suppression checks passed.
- Throughput gate: queue/backlog threshold not exceeded.
- Template gate (if configured): disallow execute for non-approved template state.

## API Contract (v1)
- Existing endpoints to keep (backward-compatible where possible):
  - `GET /admin/marketing/campaigns`
  - `POST /admin/marketing/campaigns`
  - `POST /admin/marketing/campaigns/{campaign_id}/preview`
  - `POST /admin/marketing/campaigns/{campaign_id}/execute`
  - `GET /admin/marketing/campaigns/{campaign_id}/diagnostics`
  - `POST /admin/marketing/campaigns/{campaign_id}/retry-failed`
- New endpoints:
  - `POST /admin/marketing/campaigns/{campaign_id}/request-approval`
  - `POST /admin/marketing/campaigns/{campaign_id}/approve`
  - `POST /admin/marketing/campaigns/{campaign_id}/pause`
  - `POST /admin/marketing/campaigns/{campaign_id}/resume`
  - `GET /admin/marketing/campaigns/{campaign_id}/audience`
  - `GET /admin/marketing/campaigns/{campaign_id}/preflight`

## Console UX Requirements
- Campaign detail:
  - lifecycle badge + last preflight status;
  - explicit blocked reasons when execute is unavailable.
- Audience preview table:
  - columns: recipient, user/conversation ref, segment, reasons, suppression state.
- Approval step:
  - separate action before execute, with audit actor/time.
- Execute modal:
  - show eligible count, suppressed count, max recipients, expected queue risk.
- Error handling:
  - API failures must be shown as failures, never as empty list fallback.

## Technical Design Constraints
- No new business orchestration in entrypoints/legacy adapters.
- Marketing business logic must live in dedicated services under `app/services/marketing/`.
- Router remains thin and contract-oriented.
- Migrations must be forward-safe and rollback-aware.

## Touch-list
- `truffles-api/migrations/*.sql` (new marketing v1 migrations)
- `truffles-api/app/models/*.py` (marketing entities)
- `truffles-api/app/services/marketing/*`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/decision.py` (reply attribution compatibility)
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_marketing_*`
- `truffles-api/tests/test_webhook_marketing_reply_context.py`
- `truffles-api/tests/test_message_endpoint.py` (targeted marketing slices)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/marketing/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/*` (new marketing spec)
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/CONSOLE_AUDIT/pages/marketing.md`
- `STATE.md` (FACT/GAP evidence after implementation)

## Plan
1. Define and merge new DB schema + models + migration tests.
2. Implement marketing service layer (audience, suppression, preflight, execution, retry).
3. Refactor console marketing router to use new services + state machine gates.
4. Extend diagnostics and audit consistency checks.
5. Update console API contracts and generated types.
6. Rebuild marketing UI around preview/approval/preflight/execute flow.
7. Add deterministic tests + integration tests + e2e smoke.
8. Run full checks, capture evidence, and update docs/state.

## DoD
- Audience preview returns concrete recipient list with reason codes and suppression.
- Execute path is blocked on critical/preflight-invalid/approval-missing.
- Recipient dedupe is guaranteed by code + DB uniqueness.
- Retry only requeues retryable failures.
- Marketing audit trail is complete and queryable.
- UI supports lifecycle from draft to execute with clear operator feedback.
- OpenAPI/types/tests are green and aligned.

## Checks
- Backend:
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/routers/webhook/decision.py`
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/marketing truffles-api/tests/test_console_marketing_campaigns.py truffles-api/tests/test_webhook_marketing_reply_context.py`
  - `pytest -q truffles-api/tests/test_console_marketing_campaigns.py truffles-api/tests/test_webhook_marketing_reply_context.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "marketing or campaign"`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
- Frontend:
  - `npm --prefix console-web run lint -- --file src/app/marketing/page.tsx --file src/lib/api-client.ts`
  - `npm --prefix console-web run build`
- E2E:
  - `npx playwright test console-web/e2e/marketing.spec.ts --project=chromium --reporter=list`

## Evidence
- Migration SQL + applied check output.
- API request/response artifacts for preview/approve/preflight/execute/retry.
- SQL evidence: recipients snapshot, suppressions, deliveries, audit rows.
- `decision_meta` + `decision_trace` sample for inbound reply attribution.
- UI screenshots of preview + approval + execute guard messages.
- Test outputs + CI run links.
- `STATE.md` update with FACT/GAP.

## Rollback
- Feature-flag execute/approval endpoints to off.
- Revert app changes and keep legacy wave3 path read-only.
- Backward migration script for new marketing tables if rollback is required.

## No-go
- No execute when runtime guard is critical.
- No “send all active conversations” without recipient-level dedupe.
- No silent API failure fallback as empty state.
- No merge without deterministic tests and evidence artifacts.

## Risks/Blockers
- Runtime backlog pressure may block execute despite valid campaign setup.
- Consent data may be incomplete for old recipients (requires explicit default policy).
- Historical conversation quality affects segment precision.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-21-marketing-pro-v1-a300`
- Worktree: `/home/zhan/worktrees/2026-02-21-marketing-pro-v1-a300`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase).
- Cleanup: Brain/Top Architect after merge.
