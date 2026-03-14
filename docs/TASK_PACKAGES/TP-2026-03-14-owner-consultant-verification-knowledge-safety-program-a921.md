# TP-2026-03-14-owner-consultant-verification-knowledge-safety-program-a921

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-KNOWLEDGE-SAFETY-PROGRAM-A921`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-PROGRAM-A920`
- `DEPENDS_ON`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-CLOSEOUT-A920`
- `UNLOCKS`: `CONSOLE-OWNER-CONSULTANT-VERIFICATION-KNOWLEDGE-SAFETY-WAVE1-A921`

## Название/цель
Закрыть продуктовый и архитектурный разрыв между `Knowledge` и `Проверка консультанта`: владелец бизнеса должен безопасно видеть текущие знания, редактировать черновик без потери структурных данных, честно понимать, что именно проверяет consultant verification, и не попадать в deadlock `Validate/Compare/Publish`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ARCHITECTURE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md`
- `CA_IDs`: `UX-44`, `UX-45`, `UX-46`, `UX-47`, `UX-48`, `UX-49`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/business/consultant-verification/page.tsx`
  - `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
  - `console-web/src/components/provisioning-wizard-domain.ts`
  - `console-web/src/lib/api-client.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_consultant_verification.py`
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/services/knowledge_validation.py`
  - `truffles-api/app/services/knowledge_runtime.py`
  - `truffles-api/tests/test_console_consultant_verification_api.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `truffles-api/tests/test_knowledge_validation.py`
- `Baseline commands`:
  - `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'applyStructuredDraft|guest_policy|payment_info|reschedule|cancel|discounts' console-web/src/app/knowledge/page.tsx truffles-api/app/services/knowledge_validation.py`
  - `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'source_mode|runtime_truth_override|append_consultant_verification_message|LIVE_KNOWLEDGE_REQUIRED' truffles-api/app/services/console_consultant_verification.py`
  - `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'knowledge/current|knowledge/validate|knowledge/publish|KNOWLEDGE_COMPARE_REQUIRED' truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx`
- `FACT findings`:
  - `Structured Draft Builder` читает `client_pack.guest_policy` и `client_pack.policy.*` как строки и при сборке перезаписывает эти секции строками, хотя минимум-данных и реальные pack payloads ожидают structured objects.
  - `Consultant verification` sessions сохраняют `source_mode`, но message path не привязывает runtime truth к `draft`; `draft/live` переключатель в workspace сейчас не меняет источник фактов.
  - `Knowledge publish` всегда требует green compare, а compare требует существующую `live` published version; первый publish для branch без live version попадает в deadlock.
  - `Knowledge` UI загружает только published current (`GET /knowledge/current`), хотя `Validate` уже сохраняет draft в БД (`upsert_draft`); owner не может безопасно восстановить saved draft после refresh/navigation.
  - overview/readiness в consultant verification опирается на latest published knowledge по client scope, а не строго на выбранный branch; owner может видеть optimistic readiness не для того филиала, который собирается тестировать.
  - `Knowledge` UI молча проглатывает ошибки readiness-query для consultant verification, поэтому publish может выглядеть просто «недоступным» без честного объяснения причины.
- `Detected drift (docs vs code)`:
  - copy `Draft хранится локально до публикации` больше не соответствует реализации после `Validate`, потому что draft уже записывается в `knowledge_versions(status=draft)`.

## One web search (mandatory before implementation)
- **Query (exact):** `RFC 7386 JSON Merge Patch preserve unspecified fields`
- **Date/time (local):** `2026-03-14 14:05, Asia/Almaty`
- **Why this query is precise:** нам нужен lossless update contract для owner-friendly form поверх сложного `client_pack`, чтобы изменение нескольких редактируемых полей не разрушало неизвестные или structured sections.
- **Sources opened (from this query):**
  - `RFC 7386 — JSON Merge Patch` — `https://datatracker.ietf.org/doc/html/rfc7386`
- **Existing solutions found:** JSON Merge Patch сохраняет unspecified fields и меняет только явно переданные ветки; это подходит для owner-safe partial edits поверх existing draft/published payload.
- **Decision:** `integrate` — builder и guided editors должны формировать bounded patch поверх server-selected edit base (`draft -> published -> template`) вместо полной пересборки payload из ограниченной формы.
- **Rejected options:**
  - полная client-side reserialization всего `client_pack` из упрощенной формы;
  - приведение structured policy objects к plain strings;
  - скрытый auto-fill missing mandatory fields без явного owner confirmation.
- **Open questions:** где держать canonical patch application boundary — в backend helper или во frontend builder с backend validation/echo-check.

## Root cause (mandatory)
- **Symptom:** владелец бизнеса не может надежно перейти из `Knowledge` в `Проверка консультанта`, потому что draft path теряет данные, compare path может быть недостоверным или недоступным, а publish law не учитывает first-live сценарий.
- **Minimal reproduction:**
  1. Открыть `Knowledge` для branch с structured `guest_policy`/`policy.*`.
  2. Нажать `Собрать structured draft` и затем `Validate`.
  3. Получить `Missing required field` по structured sections, хотя published pack для branch уже содержит эти sections в object form.
  4. Создать consultant verification session в режиме `draft` и отправить prompt — runtime path всё равно идет по live truth, потому что `append_consultant_verification_message()` не подставляет draft truth override.
  5. На branch без published knowledge выполнить `Validate`, затем попробовать `Publish`: backend требует compare; compare требует live published version; first publish блокируется.
  6. Обновить страницу `Knowledge` после `Validate`: UI снова показывает только published current, а не сохраненный server draft.
- **Evidence to capture:** code refs из `knowledge/page.tsx`, `console_consultant_verification.py`, `knowledge_registry_service.py`, `knowledge_validation.py`, `console.py`; owner reproduction steps; failing validation messages.
- **Five Whys (or equivalent):**
  1. Почему owner видит `Missing required field` после builder-а? Потому что builder пересобирает весь payload из неполной формы и обнуляет structured sections.
  2. Почему builder может это сделать? Потому что edit base и patch contract не отделены от итогового payload; UI пишет full payload вместо bounded patch.
  3. Почему consultant verification не доказывает `draft`? Потому что session contract хранит только label `source_mode`, но не bound runtime truth snapshot/hash.
  4. Почему publish блокирует first-live onboarding? Потому что compare hard-gate внедрен как universal law, хотя compare физически невозможен без существующего live baseline.
  5. Почему owner не понимает, что именно исправить? Потому что UI и validation outputs показывают schema paths, а не business-readable remediation steps, и не раскрывают provenance `published/draft/effective`.
- **Root cause statement:** между `Knowledge` и `Consultant Verification` отсутствует единый server-owned source/provenance contract: нет безопасной edit base + lossless patch semantics для draft, нет bound truth source для verification sessions, и нет publish-governance ветки для first-live branch onboarding.
- **Fix mechanism:**
  - ввести server-owned workspace contract `published + draft + effective_edit_base + provenance + missing_fields`;
  - перевести structured builder на bounded merge-patch поверх edit base;
  - привязать consultant verification sessions к конкретному truth source/hash;
  - отделить first-live publish gate от regular `live vs draft` compare;
  - показывать owner-friendly labels/questions для remediation.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `knowledge_registry_service.upsert_draft()` и `get_current_published()`
  - `knowledge_validation.get_required_fields_for_domain()`
  - `console_knowledge_preflight.py`
  - `console-web/src/components/provisioning-wizard-domain.ts` (`MISSING_LABELS`)
  - Wave2 safe simulation kernel and Wave6 compare contract
- **External reuse:** `RFC 7386 JSON Merge Patch` for preserving unknown/unedited branches.
- **Why not reinvent the wheel:** главная проблема не в отсутствии еще одной формы, а в отсутствии safe partial-update contract. RFC 7386 already gives the right semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `10`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** блок меняет owner-visible behavior, publish law, knowledge lifecycle semantics, and consultant runtime evidence. Нужны code, tests, docs, rollout.

## Invariant
- `Текущая версия` и `Черновик` в consultant verification must use different truth sources when their hashes differ.
- Owner-friendly tools must never destroy unknown or structured knowledge fields.
- First publish for a new branch must be possible without hidden bypasses.
- Publish cannot silently weaken validation or compare law for already-live branches.
- Owner must always see which data source is being edited/tested: `published`, `draft`, `template`, `effective overrides`.

## Scope
- Fix draft/live truth-source correctness in consultant verification sessions.
- Make consultant verification overview/readiness branch-accurate.
- Introduce recoverable knowledge workspace source contract (`published`, `draft`, `effective edit base`, provenance, timestamps).
- Replace lossy structured builder semantics with bounded merge-patch semantics.
- Add owner-readable missing-field remediation labels and guided questions.
- Remove first-publish compare deadlock while preserving compare law for branches that already have live knowledge.
- Add deterministic tests and targeted E2E coverage for the repaired flow.

## Out of scope
- Full domain-specific WYSIWYG knowledge editor for every policy subtype.
- Automatic generation of missing legal/medical/hard-law content.
- Fleet-wide migration of all legacy knowledge packs.
- Reworking the entire onboarding wizard.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/src/components/provisioning-wizard-domain.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/services/knowledge_validation.py`
- `truffles-api/app/services/console_knowledge_preflight.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_knowledge_validation.py`
- `truffles-api/tests/test_console_knowledge_preflight.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`

## Program waves
1. **Wave1 — Truth Source And Gate Repair**
   - Bind consultant verification sessions to actual `live` or `draft` truth.
   - Make overview/readiness strictly selected-branch-aware.
   - Remove first-publish compare deadlock by conditioning compare requirement on existence of live published version.
2. **Wave2 — Knowledge Workspace Provenance**
   - Add backend contract to load `published`, `draft`, and `effective edit base` with provenance/timestamps.
   - Fix misleading copy around local-vs-server draft persistence.
   - Add explicit UI state for `published exists`, `draft exists`, `editing from`, `testing against`.
3. **Wave3 — Lossless Draft Editing**
   - Replace full-payload builder overwrite with merge-patch application.
   - Preserve structured policy objects and unknown branches.
   - Respect branch effective overrides where runtime truth differs from published pack.
4. **Wave4 — Owner Remediation UX And Proof**
   - Map missing validation fields to business-readable labels/questions.
   - Add deterministic tests for preservation, first publish, draft recovery, and source correctness.
   - Add targeted owner/admin e2e for `current -> draft -> validate -> compare/publish`.

## DoD
- Draft-mode verification sessions demonstrably use draft truth, not live truth.
- Branch without live published knowledge can complete first publish after valid draft without compare deadlock.
- Structured Draft Builder never removes untouched structured policy/guest sections.
- Owner can reload and continue the last saved draft after refresh/navigation.
- Validation errors surface owner-safe labels and, where possible, guided remediation prompts.
- Consultant verification and knowledge pages both show explicit provenance (`published/draft/effective`) and selected branch.
- Deterministic tests cover the newly repaired invariants.

## Checks
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/truffles-api && pytest -q tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py tests/test_console_knowledge_preflight.py tests/test_knowledge_validation.py -k 'consultant_verification or knowledge'`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --grep 'consultant verification|knowledge'`

## Evidence
- before/after reproduction for lossy builder with structured `guest_policy` and `policy.*`
- proof that draft session uses a different truth source/hash than live session
- first-publish success evidence on a branch with no prior live knowledge
- reload/continue saved draft proof after `Validate`
- screenshot or trace showing owner-readable missing-field remediation
- tests proving branch-accurate readiness and no silent readiness-query block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `4`
- **Fail-fast / scenario lock:** start with one beauty branch fixture containing structured `guest_policy` and `policy.payment_info`; then one empty-live branch for first-publish path.
- **Stop condition:** any attempt to fix one defect by weakening publish/validation law or by adding lossy hardcoded coercion reopens RCA.
- **Escalation path:** Top Architect if product wants a temporary publish override instead of proper first-live branching.

## Release safety (mandatory for non-doc changes)
- **Strategy:** owner/admin feature-flag canary on one client with one branch containing structured policy pack and one branch with first-live onboarding.
- **Go/no-go signals:**
  - draft/live turns differ when draft hash differs;
  - no regression in publish for already-live branches;
  - first publish succeeds on branch without live version;
  - no field-loss after structured builder round-trip.
- **Rollback:** disable new knowledge workspace contract and revert to raw-draft editing only; keep safe simulation kernel intact.
- **Post-release monitoring window:** `72h` on compare/publish failures, validation error families, and owner feedback about missing-field guidance.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_GUIDE.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
- `Drift closeout rule`:
  - owner-facing wording around draft persistence, first publish, and compare law must match backend semantics in the same block.

## Rollback
- Revert new workspace provenance endpoints/helpers.
- Hide structured builder if safe patch semantics fail.
- Keep raw JSON draft editing + validate/publish path usable.
- Preserve existing consultant verification findings/sessions tables; only source-binding behavior rolls back.

## No-go
- Do not solve data loss by downgrading validation requirements.
- Do not fake `draft` mode with relabeled live sessions.
- Do not add hidden publish bypasses for owner/admin in UI.
- Do not overwrite unknown JSON/object sections from a partial form.
- Do not show schema paths to owners when human labels already exist in the codebase.

## Risks/Blockers
- Legacy packs may mix string and object forms in policy sections; patch logic must preserve both.
- Existing saved drafts may already contain flattened fields and need compatibility handling.
- Selected branch vs client scope semantics in owner/admin context can still surprise if not made explicit in UI.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`:
  - owner still edits part of knowledge through raw JSON for advanced sections not covered by guided editors;
  - no tenant-wide migration of old malformed packs in this block.
- `Why not in this block`: the immediate product risk is data loss and incorrect verification evidence; universal knowledge authoring can follow later.
- `Risk if deferred`: medium; advanced users still need raw JSON for some deep policy structures, but owner-safe path becomes honest and bounded.
- `Linked follow-up Task Package(s)`: `TBD after Wave4 closeout if richer authoring remains justified`
- `Expiry/trigger to stop deferral`: if owner/admin still cannot fix the top 10 missing-field families without raw JSON after this program, open a dedicated guided-authoring block immediately.

## Next-block contract (mandatory)
- `Next block objective`: implement `Wave1 — Truth Source And Gate Repair`.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && rg -n 'append_consultant_verification_message|LIVE_KNOWLEDGE_REQUIRED|knowledge_compare_required|source_mode' truffles-api/app/services/console_consultant_verification.py truffles-api/app/routers/console.py console-web/src/app/knowledge/page.tsx`
- `Blocked-by conditions`: this RCA/TP must be accepted as the canonical scope for the remediation block.
- `Owner role for closure`: `Brain | Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `truffles-api/app/services/console_consultant_verification.py` and `console-web/src/app/knowledge/page.tsx`
- `Do not touch`: validation law in `knowledge_validation.py` except for owner-safe labeling/preservation compatibility; no lowering of required fields.
- `Open risks`: false fix via string coercion, silent publish bypass, branch/provenance ambiguity.
- `First command to verify`: `cd /home/zhan/worktrees/2026-03-13-owner-consultant-verification-program-a920 && git diff --stat && rg -n 'Draft хранится локально|Собрать structured draft|LIVE_KNOWLEDGE_REQUIRED' console-web/src/app/knowledge/page.tsx truffles-api/app/services/console_consultant_verification.py truffles-api/app/routers/console.py`
