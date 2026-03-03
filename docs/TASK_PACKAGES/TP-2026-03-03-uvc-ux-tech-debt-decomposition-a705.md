# TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `PARENT_BLOCK_ID`: UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705
- `DEPENDS_ON`: merge of PR `#884` (`de3988e9`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE2-A705 (deep split of ProvisioningWizard + domain modules from console router)

## Название/цель
Закрыть первый полноценный этап structural-debt по `UX-11` и `UX-12` без изменения бизнес-поведения: вынести reusable pure-helpers из `console.py` и `ProvisioningWizard.tsx` в отдельные модули, одновременно устранить merge-red e2e регрессию deep-link flow.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-operations-governance-closeout-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: fix flaky deep-link fallback in `platform-admin.spec.ts` so `Tenants -> Workspace -> Ops` loop survives login redirect.
  - proof: targeted Playwright smoke passes.
- `REQ-2` no shortcut/costyl in runtime path:
  - solution: decomposition uses `reuse -> integrate` pure helper extraction; no behavior hardcode.
  - proof: extracted modules + unchanged domain contracts.
- `REQ-3` optimize existing surfaces before adding new tabs:
  - solution: no new routes/tabs; work only in existing `ProvisioningWizard`/`console.py` internals.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_router_utils.py` (new)
  - `truffles-api/tests/test_console_router_utils.py` (new)
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/components/provisioning-wizard-utils.ts` (new)
  - `console-web/e2e/platform-admin.spec.ts`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `rg -n "^def _parse_env_|^def _request_with_query_params|^def _dedupe_list" truffles-api/app/routers/console.py`
  - `rg -n "function normalizeCapabilities|function parseOptionalJson|function qualityStatusClass" console-web/src/components/ProvisioningWizard.tsx`
- `FACT findings`:
  - `console.py` and `ProvisioningWizard.tsx` remain overgrown (`25418` and `5591` LOC snapshot in this branch).
  - merge-red root-cause was unstable deep-link fallback after `/login` redirect in one smoke e2e.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com refactoring by abstraction`
- **Date/time (local):** `2026-03-03 18:19 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/articles/refactoring-2nd-ed.html`
- **Found reusable solution:** incremental extraction in behavior-preserving small steps before larger modular split.
- **Decision:** `reuse/integrate` existing logic into dedicated util modules first, then continue deeper split in follow-up wave.
- **Rejected options:** big-bang rewrite of `console.py`/`ProvisioningWizard.tsx` in one block.

## Root cause (mandatory)
- **Symptom:** high blast-radius files (`console.py`, `ProvisioningWizard.tsx`) and flaky merge due to deep-link login fallback losing context.
- **Minimal reproduction:**
  1. Run `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "deep-link from Tenants action queue to Workspace execute"`.
  2. Observe occasional `/login` redirect and missing return to the same ops deep-link.
  3. Check `console.py` and `ProvisioningWizard.tsx` monolith helper concentration.
- **Evidence:** failing run `22623388801` (historical), backlog `UX-11/UX-12`, current LOC snapshot.
- **Five Whys:**
  1. Почему merge red? Login fallback reopened generic view instead of original deep-link.
  2. Почему это повторяется? Fallback path lost target URL context.
  3. Почему structural debt мешает? Helper logic mixed with domain workflow in giant files.
  4. Почему риск высокий? Любая правка затрагивает много несвязанных участков.
  5. Почему не делать big rewrite? Слишком высокий regression risk без атомарных волн.
- **Root cause statement:** отсутствует стабильный deep-link restore path в e2e fallback и отсутствует поэтапная декомпозиция helper-слоя из монолитных файлов.
- **Fix mechanism:** deterministic deep-link restore + extraction of pure helper modules with targeted tests.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing helper logic from `console.py` and `ProvisioningWizard.tsx` moved as-is to service/util modules.
- **External reuse:** Fowler incremental refactoring guidance.
- **Why not build from scratch:** текущая логика рабочая; нужен перенос без изменения поведения.

## Invariant
- Не менять runtime business semantics и backend/frontend API contracts.
- Не добавлять новые top-level tabs/routes.
- Не ослаблять anti-drift/CI/session gates.

## Scope
- Исправить merge-red e2e deep-link fallback.
- Вынести pure-helpers из `ProvisioningWizard.tsx` в `provisioning-wizard-utils.ts`.
- Вынести env/query/dedupe helpers из `console.py` в `console_router_utils.py`.
- Добавить deterministic pytest для нового router-utils модуля.
- Обновить task/session/state/structure/index документы под новый блок.

## Out of scope
- Full domain split `console.py` по feature routers.
- Full split `ProvisioningWizard` по sub-components/containers.
- Любые LLM policy-core/runtime semantic changes.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-utils.ts` (new)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_router_utils.py` (new)
- `truffles-api/tests/test_console_router_utils.py` (new)

## Plan (1..N)
1. Create TP + switch active session to `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`.
2. Fix deep-link merge-red in Playwright (`Tenants -> Workspace -> Ops` with login fallback restore).
3. Extract `ProvisioningWizard` pure helpers to a dedicated util module and rewire imports.
4. Extract `console.py` env/query/dedupe helpers to `console_router_utils.py` and keep behavior identical.
5. Add targeted tests/checks, capture evidence, open PR.

## DoD
- Targeted deep-link Playwright smoke passes reliably.
- New `provisioning-wizard-utils.ts` is used by `ProvisioningWizard.tsx` and lint passes.
- New `console_router_utils.py` is used by `console.py` and pytest for this module passes.
- Session/state/index/structure synced for current block.

## Checks
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-utils.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "deep-link from Tenants action queue to Workspace execute"`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py`
- `pytest -q truffles-api/tests/test_console_router_utils.py`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Playwright output for deep-link smoke (`1 passed`).
- `pytest -q truffles-api/tests/test_console_router_utils.py` (`5 passed`).
- Lint and py_compile outputs.
- Diff for extracted utility modules and router/component rewiring.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` targeted Playwright smoke runs for the flaky deep-link path.
- Fail-fast / scenario lock: run only `--grep "deep-link from Tenants action queue to Workspace execute"` for e2e; full suite is out of scope.
- Stop condition: repeated e2e failure without new RCA evidence.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** behavior-preserving extraction only + targeted smoke.
- **Go/no-go signals:** lint green, pytest green, targeted e2e green.
- **Rollback:** revert current commit and re-run targeted checks.
- **Post-release monitoring window:** next PR CI run with `console-e2e` smoke.

## Rollback
- `git revert COMMIT_SHA` and rerun target checks from `Checks`.

## No-go
- Rewrite business flow while decomposing helper layer.
- Add fallback hacks in runtime path.
- Skip session/canon synchronization.

## Risks/Blockers
- Additional hidden e2e flakes may still exist outside this specific deep-link test.
- Structural debt remains large after wave1 extraction.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `console.py` and `ProvisioningWizard.tsx` are still large after helper extraction.
- `Why not in this block`: keeping atomic low-risk boundary for merge-red fix + first decomposition wave.
- `Risk if deferred`: medium regression risk on future cross-cutting edits.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE2-A705`.
- `Expiry/trigger to stop deferral`: if next feature requires touching >3 unrelated concerns in either monolith.

## Next-block contract (mandatory)
- `Next block objective`: split `ProvisioningWizard` into domain slices (state/actions/view) and extract `console.py` control-tower/onboarding routers into domain modules.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: current decomposition wave not merged or target checks not green.
- `Owner role for closure`: Brain + Top Architect.
