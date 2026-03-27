# TP-2026-03-15-knowledge-release-model-stoploss-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-STOPLOSS-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-KNOWLEDGE-STABILIZATION-RESET-A4`
- `DEPENDS_ON`: `CONSOLE-OWNER-KNOWLEDGE-STABILIZATION-RESET-A4`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-CORRECTION-P1-A30`

## Название/цель
Исправить ложный owner-facing контракт между `Knowledge` и `Проверка консультанта`: preview-проверка консультанта должна быть доступна по pinned knowledge snapshot без ожидания branch sync, а owner UI должен честно разделять `можно проверить` и `обновление для клиентов ещё выполняется`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-03-14-owner-consultant-verification-knowledge-safety-program-a921.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-owner-knowledge-stabilization-reset-a4.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-knowledge-sync-state-unification-a4.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-surface-decomposition-partb-a7.md`
- `CA_ID`: `UX-44`, `UX-45`, `UX-46`, `UX-47`, `UX-48`, `UX-49`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/console_consultant_verification.py`
  - `truffles-api/app/services/knowledge_runtime.py`
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/models/console_consultant_verification_session.py`
  - `truffles-api/app/models/knowledge_version.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_consultant_verification_api.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
  - `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`
- `Baseline commands`:
  - `cd /home/zhan/truffles-main && rg -n 'knowledge_sync_blocking|knowledge_sync_status != "ready"|knowledge_safe_mode|syncBlocked|workspaceReady' truffles-api/app/services/console_consultant_verification.py console-web/src/app/business/consultant-verification/page.tsx`
  - `cd /home/zhan/truffles-main && rg -n 'publish_version\(|sync_status=KNOWLEDGE_SYNC_STATUS_PENDING|status="published"|get_current_published\(' truffles-api/app/services/knowledge_registry_service.py truffles-api/app/services/knowledge_runtime.py`
  - `cd /home/zhan/truffles-main && rg -n '_resolve_verification_session_runtime_truth|append_consultant_verification_message|runtime_snapshot' truffles-api/app/services/console_consultant_verification.py`
- `FACT findings`:
  - `derive_consultant_verification_status()` treats `knowledge_sync_status != ready` or `knowledge_safe_mode` as a hard preview blocker, even though preview runtime truth is built from knowledge payloads and does not technically depend on branch sync completion.
  - `console-web/src/app/business/consultant-verification/page.tsx` computes `syncBlocked` and hides the interactive workspace until sync becomes `ready`, repeating the same false product contract in the owner UI.
  - `publish_version()` marks the new knowledge version as `published` immediately with `sync_status=pending`, while `build_runtime_truth()` reads the current published version directly; live semantic truth can therefore switch before sync finishes.
  - `append_consultant_verification_message()` re-resolves runtime truth on every turn; for `draft` mode it reads the mutable latest draft row again, so one verification session can drift after a new validate/publish.
  - `sync_status/sync_error/sync_completed_at` live on `KnowledgeVersion`, although they describe execution lifecycle of activation attempts rather than immutable artifact state.
- `Detected drift (docs vs code)`:
  - `STATE.md` currently records the March 15 stabilization slice as if blocking verification on pending/failed sync kept owner proof honest; the current deeper RCA shows this is the opposite of the intended release model.

## One web search (mandatory before implementation)
- **Query (exact):** `Argo Rollouts preview service active service blue green official docs`
- **Date/time (local):** `2026-03-15 14:22 +05`
- **Why this query is precise:** нужен high-signal reference для разделения `preview` и `active/live` состояний, чтобы закрепить owner-facing contract без смешения preview readiness и activation status.
- **Sources opened (from this query):**
  - `Argo Rollouts — BlueGreen Deployment Strategy` — `https://argoproj.github.io/argo-rollouts/features/bluegreen/`
- **Existing solutions found:** официальный rollout reference явно держит `preview service` и `active service` как отдельные поверхности, что подтверждает правильность раздельных статусов `preview` и `live activation` вместо одного merged `sync` gate.
- **Decision:** `integrate` — для console knowledge release model разделяем `preview readiness` и `live activation status`; preview не блокируется pending activation, а active/live остаётся отдельным operational state.
- **Rejected options:**
  - один merged `sync_status` как единственный продуктовый gate для owner preview;
  - publish-time switch живого semantic pointer без отдельной activation-ready стадии;
  - session proof, который каждый turn резолвит `latest draft` или `current published` заново.
- **Open questions:** как быстро после P0 вводить отдельный `active_version_id` pointer и dedicated activation job record без повторного owner-facing contract drift.

## Root cause (mandatory)
- **Symptom:** owner не может честно проверить консультанта тогда, когда уже должен мочь, а live runtime может переключиться на новую published version раньше завершения sync.
- **Minimal reproduction:**
  1. В `Knowledge` опубликовать валидную версию для branch.
  2. Получить `sync_status=pending` и открыть `Business -> Проверка консультанта`.
  3. Увидеть blocked workspace и copy `дождитесь завершения синхронизации`, хотя preview runtime truth уже может быть построен из knowledge payload.
  4. Создать verification session в `draft` режиме, затем изменить draft через `Validate` и отправить следующее сообщение в уже созданную session.
  5. Убедиться, что session truth дрейфует, потому что runtime truth на новом turn резолвится заново из latest draft/current published.
- **Evidence to capture:** targeted backend/frontend tests covering sync-block removal, session pinning, separate preview/live status copy, and no-drift behavior after draft mutation.
- **Five Whys (or equivalent):**
  1. Почему owner preview блокируется? Потому что overview/UI используют `knowledge_sync_status` как продуктовый gate вместо preview truth contract.
  2. Почему это случилось? Потому что preview readiness, live activation, и artifact existence не разделены как разные состояния.
  3. Почему session evidence недостоверно? Потому что verification session хранит только mode label, а не immutable truth snapshot.
  4. Почему live может переключаться слишком рано? Потому что runtime читает `current published` напрямую, а publish уже двигает published row до activation completion.
  5. Почему owner видит не тот смысл? Потому что surface показывает operational terms (`sync`, `safe mode`) вместо business contract (`можно проверить`, `обновление для клиентов`).
- **Root cause statement:** в knowledge lifecycle нет корректного разделения между `artifact exists`, `preview is ready`, и `live activation is ready`; из-за этого preview ошибочно блокируется sync-state, live truth переключается слишком рано, а verification sessions не pinned к immutable snapshot.
- **Fix mechanism:**
  - в P0 убрать sync как preview gate и вывести отдельные `preview` vs `live activation` статусы в backend/frontend contracts;
  - pin consultant verification session to immutable snapshot payload/hash at session creation and reuse it on every turn;
  - в P1 ввести `active_version_id` и dedicated activation job lifecycle вместо implicit `published + sync_status` coupling.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `RuntimeTruth` + `build_runtime_truth_from_payload()` in `knowledge_runtime.py`
  - existing `runtime_snapshot` persistence in `ConsoleConsultantVerificationSession`
  - `ConsoleConsultantVerificationOverviewResponse` / current readiness cards and actions
  - `knowledge_sync_status_label()` for operational secondary disclosure
- **External reuse:** Argo Rollouts `preview service` vs `active service` separation as rollout-state reference.
- **Why not reinvent the wheel:** нам не нужен новый temporary owner-specific state machine с ad-hoc flags; мы reuse existing snapshot/runtime plumbing and only correct the contract boundary so preview and live activation become explicit separate states.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** блок меняет owner-visible behavior and backend session contract, but deliberately keeps P1 migrations/job-model work out of scope.

## Invariant
- Verification preview must remain truthful and reproducible: one session = one immutable truth snapshot.
- Preview availability must not silently weaken live safety; live activation status remains visible but separate.
- No change in this block may cause live traffic to use draft payloads or bypass existing publish validation.

## Scope
- Remove `sync` / `knowledge_safe_mode` as hard blockers for consultant verification preview readiness and workspace availability.
- Add explicit overview contract fields for `verification_ready`, `preview_status`, `live_activation_status`, `can_verify_now`, and `blockers`.
- Pin consultant verification sessions to an immutable truth snapshot at create time and use that snapshot for all subsequent turns.
- Update owner-facing copy so the primary path says `Проверка консультанта` vs `Обновление для клиентов`, not raw operational internals.
- Add deterministic backend/frontend/E2E coverage for the corrected P0 contract.

## Out of scope
- Introducing `branches.active_knowledge_version_id`.
- Dedicated `knowledge_activation_jobs` table, heartbeat, retries, or stuck detection.
- Changing live runtime selection away from `get_current_published()`.
- Full owner/admin surface split for activation observability.
- Retroactive migration of existing verification sessions.

## Touch-list
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Correct the backend overview contract: separate preview readiness from live activation status and stop deriving `status=blocked` from sync pending/failed.
2. Resolve and persist an immutable truth snapshot when a consultant verification session is created; reuse it on every subsequent turn.
3. Update the owner UI so the workspace availability follows preview readiness, while live activation status remains a secondary disclosure.
4. Add deterministic API/frontend/Playwright proof for `pending activation but verification available` and `session does not drift after draft mutation`.
5. Sync docs/state to record the contract correction and the remaining P1/P2 release-model debt.

## DoD
- Owner can open consultant verification when preview truth exists, even if live activation is still `pending` or `failed`.
- Backend overview returns separate `preview` and `live activation` states plus explicit blockers.
- Verification session turns do not drift after a later `Validate` or `Publish` changes the draft/live rows.
- Owner UI primary copy uses business semantics (`доступно проверить`, `обновление для клиентов выполняется/требует внимания`).
- Targeted tests and E2E proof are green.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py -k 'consultant_verification or knowledge'`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/services/console_consultant_verification.py app/services/knowledge_runtime.py app/schemas/console.py tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'consultant verification preview contract|consultant verification pinned snapshot'`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 scripts/session_check.sh`

## Evidence
- API response showing `verification_ready=true` while `live_activation_status=pending`.
- Test proving an existing session keeps the same truth hash/payload after a later draft mutation.
- UI proof that workspace remains available with separate activation badge/message.
- Updated `STATE.md` FACT entry with commands/results before merge.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `4`
- **Fail-fast / scenario lock:** start with deterministic API tests for overview/session pinning before frontend build/E2E.
- **Stop condition:** if the easiest path requires weakening publish law or introducing draft-into-live bleed, stop and reopen RCA.
- **Escalation path:** Top Architect if P0 cannot be completed without immediate `active_version_id` migration.

## Release safety (mandatory for non-doc changes)
- **Strategy:** fail-closed preview contract correction; live runtime behavior stays unchanged in P0, so rollback is bounded to owner-facing overview/session logic.
- **Go/no-go signals:**
  - preview available while activation pending;
  - no verification-session drift after draft mutation;
  - live activation message still visible and truthful.
- **Rollback:** revert the P0 stop-loss branch; existing publish/sync path remains as before.
- **Post-release monitoring window:** `72h` watching consultant verification usage, failed session creation, and owner reports about misleading activation copy.

## Rollback
- Revert the P0 stop-loss branch.
- Keep existing published/draft rows untouched.
- Remove new overview fields from UI contract if they cause regression.

## No-go
- Do not pretend P1 is solved in this block.
- Do not route live traffic through draft payloads or preview snapshot overrides.
- Do not keep `sync` as a hidden preview blocker under a renamed flag.
- Do not make session pinning depend on mutable `latest draft` lookups.
- Do not expose raw `safe mode` / timeout internals as primary owner copy.

## Risks/Blockers
- Current schema may need careful compatibility handling for sessions created before pinned snapshot fields exist in `runtime_snapshot`.
- Frontend may still have follow-up assumptions that `status=ready` implies activation-ready, not preview-ready.
- P0 intentionally leaves the deeper live pointer defect untouched; owner copy must stay honest about that residual.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `KnowledgeVersion` still stores `sync_status` even though it models activation execution rather than immutable artifact state.
- Live runtime still reads `get_current_published()` directly instead of `active_version_id`.
- Activation still rides the generic outbox path without a dedicated job record.

### Why not in this block
- P0 is a stop-loss correction to owner proof and session integrity; schema/job-model changes are a larger P1 migration and must be done deliberately.

### Risk if deferred
- Live activation can still switch too early after publish, even though owner preview becomes honest.
- Operational observability for stuck/failed activation remains weak.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-release-model-correction-p1-a30.md`

### Expiry/trigger to stop deferral
- If another publish/sync defect appears after P0, `active_version_id + activation_jobs` becomes blocking and cannot stay deferred.

## Next-block contract (mandatory)
### Next block objective
- Introduce `active_version_id` and a dedicated activation-job lifecycle so publish creates an immutable artifact, preview uses that artifact immediately, and live traffic switches only after activation-ready.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'get_current_published\(|sync_status|knowledge_safe_mode|published"' truffles-api/app/services/knowledge_runtime.py truffles-api/app/services/knowledge_registry_service.py truffles-api/app/routers/console.py`

### Blocked-by conditions
- P0 preview/session contract must land first so owner proof stops depending on sync.
- Need closure evidence that P0 does not regress existing consultant verification session APIs.

### Owner role for closure
- `Brain | Top Architect`

## Git / worktree
- `Branch`: `feat/2026-03-15-knowledge-release-model-stoploss-a30`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30`
- `Base ref`: `origin/main`
- `Merge policy`: `PR + CI after deterministic local proof`
- `Cleanup`: `Brain/Top Architect removes worktree + branch after merge`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py`
- `Do not touch`: publish validation law and live runtime pointer semantics beyond owner-facing contract separation.
- `Open risks`: false preview/live wording, session snapshot compatibility for older rows, temptation to “fix” live early-switch inside P0.
- `First command to verify`: `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'syncBlocked|workspaceReady|_resolve_verification_session_runtime_truth|runtime_snapshot' console-web/src/app/business/consultant-verification/page.tsx truffles-api/app/services/console_consultant_verification.py`
