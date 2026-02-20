# TP-2026-02-19-onboarding-any-niche-end2end-tz

- Название/цель: Canonical end-to-end ТЗ по onboarding any-niche (beauty first) с последовательным закрытием readiness -> go/no-go -> delivery -> reference normalization, без хардкода и без ослабления fail-closed контрактов.
- Статус: `active (post-merge baseline + next wave plan)`.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- Инварианты:
  - Продуктовый контракт `FACT/COLLECT/HANDOFF` неизменен.
  - Go-live gate остается fail-closed.
  - Pack-first + policy/data-driven, без client-specific ветвлений.
  - Любой rollout управляется через env/config/contracts, не через ручные DB bypass.

## Фактический срез (2026-02-20)

- Кодовая база: `origin/main` (локально обновлено до `f82ae24c`).
- Источники фактов:
  - TP/Report артефакты:
    - `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-acceptance-a131.md`
    - `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-step123-a131.md`
    - `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-delivery-contour-step2-a131.md`
    - `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
    - `docs/TASK_PACKAGES/TP-2026-02-20-onboarding-followup123-a131.md`
    - `docs/REPORTS/2026-02-19-onboarding-any-niche-acceptance-a131.md`
    - `docs/REPORTS/2026-02-19-onboarding-any-niche-step123-a131.md`
    - `docs/REPORTS/2026-02-19-onboarding-delivery-contour-step2-a131.md`
    - `docs/REPORTS/2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
    - `docs/REPORTS/2026-02-20-onboarding-followup123-a131.md`
  - UI snapshot evidence (fresh):
    - `/tmp/console_screens_2026-02-20/*`
  - Runtime evidence:
    - `/tmp/onboarding_any_niche_step123_a131/*`
    - `/tmp/onboarding_delivery_step2_a131/*`
    - `/tmp/onboarding_reference_branch_step3_a131/*`
    - `/tmp/onboarding_followup123_a131/*`

## Реализация по этапам (факт)

1) Этап `1` (acceptance contour) закрыт частично в первом проходе, затем доведен follow-up этапами.
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-acceptance-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-any-niche-acceptance-a131.md`
- Итог на тот момент: `A=PASS`, `B=PASS`, `C=FAIL` (фиксировался как честный operational gap).

2) Этапы `1/2/3` закрыты в рабочем проходе step123.
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-step123-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-any-niche-step123-a131.md`
- Итог: `PASS`.
- Что реализовано:
  - hard-gate shadow/canary/enforced rollout;
  - blueprint contract (`required_fields_profile`, `readiness_weights`);
  - ops acceptance C доведен до PASS evidence.

3) Этап `4` (delivery contour stabilization) закрыт.
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-delivery-contour-step2-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-delivery-contour-step2-a131.md`
- Итог: `PASS`.
- Что реализовано:
  - reason-aware delivery critical blockers;
  - ops команда `onboarding-delivery-stabilize`;
  - fail-on-critical gate.

4) Этап `5` (reference branch normalization) закрыт.
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
- Итог: `PASS`.
- Что реализовано:
  - единый reference-branch selection kernel;
  - normalized scope для fleet/diagnose;
  - override `--all-active-branches`.

5) Follow-up `1/2/3` (после merge) закрыт.
- TP: `docs/TASK_PACKAGES/TP-2026-02-20-onboarding-followup123-a131.md`
- Report: `docs/REPORTS/2026-02-20-onboarding-followup123-a131.md`
- Итог: `PASS`.
- Что реализовано:
  - delivery noise filtering (только релевантные outbound события в delivery readiness);
  - reference scope выведен в Console UX/UI;
  - contract sync (`openapi.v1.yaml`, `console-web/src/types/api.generated.ts`);
  - восстановлен canonical umbrella-doc (этот файл).

## Что уже встроено в UX/UI (факт)

- Tenants:
  - `console-web/src/app/tenants/page.tsx`
  - есть `ProvisioningWizard` и reference-scope отображение.
- Settings:
  - `console-web/src/app/settings/page.tsx`
  - есть `ProvisioningWizard` (через advanced toggle).
- Company Workspace:
  - `console-web/src/app/company-workspace/page.tsx`
  - есть "Следующее рекомендуемое действие", "Инцидентный гайд", "Линейный hard-stop онбординга", переходы в Ops/Integrations.
- Integrations:
  - `console-web/src/app/integrations/page.tsx`
  - есть fleet view + queue + переход в Workspace, reference-scope отображение.
- Ops:
  - `console-web/src/components/OpsPage.tsx`
  - есть incident state workflow (`open/in_progress/resolved`) + incident actions + jobs history.

## Выявленные остаточные UX/операционные разрывы (после закрытых этапов 1-5)

1) Дублированные точки входа онбординга повышают когнитивную нагрузку.
- Факт: wizard доступен и в `Tenants`, и в `Settings`, а оперативные действия идут в `Company Workspace`/`Ops`.
- Риск: platform admin тратит время на переключение между экранами и может терять контекст шага.

2) Закрытие причины инцидента все еще требует ручной проверки нескольких экранов.
- Факт: есть incident guide и actions, но оператору нужно руками сверять эффект по метрикам/очереди после действия.
- Риск: медленное и неравномерное закрытие инцидентов между операторами.

3) Для нетехнического owner-языка остается избыток тех-терминов в основном потоке.
- Факт: ключевые поля/действия используют technical vocabulary (`instance_id`, `webhook`, `provider binding`).
- Риск: platform admin выступает "переводчиком" вместо продукта, рост времени onboarding.

4) Нет явной продуктовой панели скорости онбординга в контуре onboarding/workspace.
- Факт: в текущих onboarding-панелях нет явных KPI вида `time_to_go_live`, `blocker_age`, `first_pass_go_live_rate`.
- Риск: сложно измерять, ускоряется ли процесс по факту.

## Обновленный план работ (next wave)

### Step 6: Single-Operator Flow Consolidation
- Цель: один основной entrypoint для онбординга platform admin (без удаления текущих экранов, через мягкую консолидацию).
- Реализация:
  - объявить `Company Workspace` каноническим execution-потоком;
  - в `Tenants`/`Settings` оставить wizard как read/launch view с явным deep-link "Продолжить в Workspace";
  - сохранить context carry-over (`company/client/branch`).
- Бизнес-ценность:
  - меньше переключений;
  - быстрее путь `контекст -> действие -> проверка -> go-live`.

### Step 7: Evidence-Closed Incident Remediation
- Цель: управляемое закрытие причин, не только запуск действий.
- Реализация:
  - после execute действия показывать встроенный post-check блок (дельта `failed_24h`, backlog, state transition);
  - добавить явный checklist "cause closed evidence";
  - разрешать "закрыть инцидент" только после минимального evidence-чека.
- Бизнес-ценность:
  - меньше повторных инцидентов;
  - единый операционный стандарт для всей команды.

### Step 8: Onboarding Throughput Metrics
- Цель: сделать скорость онбординга измеримой и управляемой.
- Реализация:
  - добавить метрики для onboarding pipeline:
    - `time_to_go_live_median`,
    - `blocker_age_p95`,
    - `first_pass_go_live_rate`,
    - `incident_reopen_rate_24h`.
  - вывести их в `Tenants`/`Company Workspace` как операторские KPI.
- Бизнес-ценность:
  - owner и platform admin видят эффект изменений в цифрах;
  - решения по приоритетам принимаются по фактам, а не по ощущениям.

## Обновленный acceptance contract (для next wave)

- A) Contract:
  - py_compile + ruff + targeted pytest + OpenAPI check.
- B) UX:
  - e2e/screenshot evidence: единый flow без потери контекста.
- C) Ops:
  - evidence-closed remediation (до/после метрик), без ручных SQL bypass.
- D) Product:
  - KPI панели доступные platform admin, с прозрачной методикой расчета.

## Rollback

- `git revert COMMIT_SHA` per concrete step commit.

## No-go

- Не ослаблять hard-gate для "зеленого" статуса.
- Не делать client-specific hardcode.
- Не подменять evidence ручной правкой БД/trace.
- Не плодить новый параллельный onboarding flow без решения про канонический entrypoint.
