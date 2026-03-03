# TP-2026-03-02-uvc-ux-stage2-language-hints-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STAGE2-A705
- `PARENT_BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `DEPENDS_ON`: merge of PR `#874` (`80052230`) into `main`
- `UNLOCKS`: UVC-UX-STAGE3-A705

## Название/цель
Закрыть Stage 2 программы UVC UX: унифицировать язык интерфейса и контекстные подсказки в существующих вкладках без добавления новых продуктовых зон, чтобы ключевые бизнес-действия были понятны без внутреннего жаргона.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage1-ia-matrix-a705.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/tenants/tenants-page-view.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/app/settings/page.tsx`
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/app/marketing/page.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage2-language-glossary-a705.md`
- `Baseline commands`:
  - `git merge-base --is-ancestor 80052230 origin/main`
  - `rg -n "execution-flow|remediation|go-live|instance_id|paid_until|next_renewal_at|source:" console-web/src/app/tenants console-web/src/components/OpsPage.tsx console-web/src/app/settings/page.tsx console-web/src/app/knowledge/page.tsx`
  - `rg -n "plain-language|источник подсказки|owner:|paid_until|next_renewal_at|source:" console-web/e2e/platform-admin.spec.ts`
- `FACT findings`:
  - Stage 1 merged in `main` and deep-link contract is stable.
  - В primary loops (`Tenants/Integrations/Workspace`) язык улучшен, но в `Ops/Settings/Knowledge` и части `Tenants` остаются mixed technical labels.
  - Anti-drift для plain-language пока покрывает только subset потоков (`Tenants -> Workspace`).
- `Detected drift (docs vs code)`:
  - master plan ожидает отдельный TP Stage 2; до этого блока Stage 2 был только в плане, без выделенного implementation TP.

## One web search (mandatory before implementation)
- **Query (exact):** `site:design-system.service.gov.uk plain language content design`
- **Date/time (local):** `2026-03-03 10:25 +05`
- **Why this query is precise:** нужен high-signal стандарт для операционных интерфейсов с профессиональной аудиторией, где требуется минимум жаргона и короткие пояснения рядом с действием.
- **Sources opened (from this query):**
  - GOV.UK Content Design, Writing for GOV.UK: `https://www.gov.uk/guidance/content-design/writing-for-gov-uk`
  - GOV.UK Content Design, Writing for specialist audiences: `https://www.gov.uk/guidance/content-design/writing-for-specialist-audiences`
- **Existing solutions found:** plain English by default, раскрытие термина рядом с действием, удаление ненужных аббревиатур и внутренних кодов из пользовательского слоя.
- **Decision:** `integrate` — сохранить технические поля в API/contracts, но в UI показывать бизнес-лейблы + локальные подсказки.
- **Rejected options:** массовая замена терминов в backend schema/DTO (не нужно для UX Stage 2 и повышает риск контрактного дрейфа).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** в части вкладок пользователь видит смешение бизнес-языка и внутренних системных терминов (`instance_id`, `paid_until`, `source`, `execution-flow`), из-за чего растет когнитивная нагрузка и риск неверного действия.
- **Minimal reproduction:**
  1. Открыть `Tenants`, `Settings`, `Ops`, `Knowledge`.
  2. Перейти в блоки onboarding/remediation/readiness/incidents.
  3. Найти mixed labels и сравнить с plain-language блоками в `Workspace`.
- **Evidence to capture:** diff copy/hints, glossary artifact, e2e assertions на отсутствие raw technical labels в user-facing flow.
- **Five Whys (or equivalent):**
  1. Почему остался жаргон? Stage 1 закрывал ownership/action-source, не полный language sweep.
  2. Почему это мешает? Оператору нужно переводить термины в голове перед действием.
  3. Почему риск высокий? На инцидентных экранах возрастает вероятность неправильного шага.
  4. Почему не закрыто локально в каждой вкладке? Не было единого Stage2 glossary контракта.
  5. Почему нужно закрыть сейчас? Это прямое условие перед Stage 3 сквозных бизнес-циклов.
- **Root cause statement:** отсутствовал единый contract-level plain-language слой для всех критичных UX-панелей, поэтому терминология эволюционировала фрагментированно.
- **Fix mechanism:** расширить канонический glossary + применить labels/hints в remaining primary panels + закрепить anti-drift проверками.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `console-web/src/lib/provider-ops-language.ts` как базовый pattern для человекочитаемых labels/hints.
  - уже существующие e2e deterministic mocks и smoke сценарии в `console-web/e2e/platform-admin.spec.ts`.
- **External reuse:** GOV.UK content design plain-language guidance (источники выше).
- **Why not reinvent the wheel:** структура вкладок и action flows уже верная; нужен language-layer hardening, а не новый UI контур.

## Invariant
- Не добавлять новые top-level вкладки.
- Не менять backend contracts и API payload keys.
- Не дублировать execute-действия вне `Company Workspace`.
- Любой primary CTA/статус в Stage 2 scope должен иметь понятный бизнес-лейбл.

## Scope
- Wave 1: создать Stage2 glossary artifact (`term -> UI label -> hint -> location`) для `Tenants/Ops/Settings/Knowledge/Integrations/Workspace`.
- Wave 2: применить copy/hints в user-facing блоках и убрать raw technical labels из primary panels.
- Wave 3: добавить anti-drift deterministic checks для Stage2 language-contract.

## Out of scope
- Backend schema/key renaming (`instance_id`, `paid_until`, `next_renewal_at` в API остаются).
- Полные cross-tab flow refactors Stage 3.
- Любые новые runtime feature flags для language layer.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage2-language-hints-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage2-language-glossary-a705.md`
- `console-web/src/app/tenants/tenants-page-view.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/settings/page.tsx`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/app/marketing/page.tsx`
- `console-web/e2e/platform-admin.spec.ts`
- `STATE.md`

## Plan (1..N)
1. Зафиксировать glossary artifact с полным маппингом primary labels и подсказок.
2. Обновить copy/hints в `Tenants/Ops/Settings/Knowledge` и синхронизировать с `Integrations/Workspace`.
3. Добавить anti-drift e2e assertions на отсутствие raw technical labels в primary flow.
4. Прогнать lint + targeted e2e и зафиксировать evidence.
5. Подготовить PR + next-block contract для Stage 3.

## DoD
- Stage2 glossary artifact существует и покрывает primary панели в scope.
- В user-facing primary panels нет raw-labels `owner:`, `source:`, `paid_until`, `next_renewal_at`.
- Тексты CTA/подсказок в `Tenants/Ops/Settings/Knowledge` согласованы с `Workspace/Integrations`.
- Targeted lint/e2e зеленые, `session_check` зеленый.

## Checks
- `git merge-base --is-ancestor 80052230 origin/main`
- `cd console-web && npm run lint -- --file src/app/tenants/tenants-page-view.tsx --file src/components/OpsPage.tsx --file src/app/settings/page.tsx --file src/app/knowledge/page.tsx --file src/app/integrations/page.tsx --file src/app/company-workspace/page.tsx --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff по затронутым UI-файлам с unified plain-language copy.
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage2-language-glossary-a705.md`.
- e2e run output с assertions для language anti-drift.
- Запись в `STATE.md` (Brain/Top Architect до merge, т.к. меняется поведение пользовательского слоя).

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted e2e прогон для Stage 2.
- **Fail-fast / scenario lock:** только `Platform Admin Navigation|Platform Admin Tenants`.
- **Stop condition:** 2 подряд прогона без новой RCA evidence.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** low-risk copy/hints rollout в существующих вкладках без backend изменений.
- **Go/no-go signals:** zero regressions in existing deep-link flows; anti-drift checks green.
- **Rollback:** `git revert HEAD` + rerun checks.
- **Post-release monitoring window:** `24h` по incident/remediation UX сигналам.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage2-language-glossary-a705.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-*.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - Stage 2 не закрывается без glossary artifact + e2e anti-drift evidence.

## Rollback
- `git revert HEAD` с повторным прогоном lint + e2e.

## No-go
- Добавлять новый top-level раздел вместо оптимизации текущих вкладок.
- Менять API payload keys ради UI-copy.
- Ослаблять e2e/oracle ради прохождения.

## Risks/Blockers
- Часть secondary тех-полей может быть нужна в debug-зонах; их нельзя удалять, только явно маркировать как технические.
- Большой copy-diff может задеть существующие e2e selectors по тексту.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: secondary advanced/debug surfaces могут сохранить технические поля в raw-виде.
- `Why not in this block`: Stage 2 закрывает primary user-facing flow; deep forensic/debug панели будут нормализованы в Stage 4 anti-drift governance.
- `Risk if deferred`: отдельные edge-path экраны останутся менее дружелюбными для новых операторов.
- `Linked follow-up Task Package(s)`: `TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705.md`.
- `Expiry/trigger to stop deferral`: если raw-термины появятся в primary panels после Stage 2, откладывание запрещено.

## Next-block contract (mandatory)
- `Next block objective`: Stage 3 full cross-tab business loops hardening (`Tenants -> Workspace -> Ops` и `Integrations -> Workspace -> Tenants`).
- `First deterministic check command`: `rg -n "workspace-recommended-open-execute|integrations-row-open-workspace|ops-incident-" console-web/e2e/platform-admin.spec.ts`
- `Blocked-by conditions`: Stage 2 language anti-drift checks не зелёные.
- `Owner role for closure`: Brain + Top Architect.
