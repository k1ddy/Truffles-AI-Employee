# TP-2026-02-22-universal-control-plane-v1-master-a500

## Название/цель
Universal Control Plane v1: привести платформу к управлению любыми бизнес-нишами через Console Plane (Platform Admin first), с fail-closed governance, KZ data-compliance, pack/config-only onboarding новых ниш, и поэтапной миграцией production без переписывания core.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP)
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `SPECS/VERTICAL_PACK_KIT.md`
- `STRATEGY/REQUIREMENTS.md`
- `contracts/capabilities/capabilities.v1.jsonschema`

## Invariant
- Любое inbound-сообщение остается в контракте `FACT/COLLECT/HANDOFF`.
- Hard-law policy (payment/medical/legal/complaint/refund/reschedule) не может переопределяться branch-слоем.
- Tenant isolation fail-closed: без валидного tenant-context нет read/write действия.
- Любое управленческое действие в Console auditable (actor/scope/reason/diff/time).
- Подключение новой ниши делается только через packs/config/capabilities, без hardcode в core.

## Scope
- Program-level ТЗ и фазы реализации для Universal Control Plane v1.
- FACT/GAP аудит по ключевым блокам (tenant, RBAC, capabilities, onboarding, policy governance, tools/providers, knowledge, SLA/SLO, compliance).
- Документирование целевого контракта, Analysis Gates, migration waves и phase-by-phase implementation path.
- Запуск реализации Phase 1 (analysis + contract hardening bootstrap) в рамках текущей сессии.

## Out of scope
- Big-bang rewrite LLM/runtime.
- Изменение продуктовых обещаний вне канона.
- Ручные прод-правки без contract-first и evidence.

## Touch-list (planned)
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase1-a500.md`
- `SPECS/CONTROL_PLANE.md` (if canon gaps must be formalized)
- `SPECS/MULTI_TENANT.md` (if contract clarifications required)
- `truffles-api/app/services/*` + `truffles-api/app/routers/console.py` (Phase 1 scoped implementation only)
- `truffles-api/tests/*` (Phase 1 scoped tests)

## Plan (1..N)
1. Session bootstrap in dedicated worktree + hooks + governance checks.
2. Создать master-ТЗ документ (program contract + phases + analysis gates + DoD/evidence/rollback/no-go).
3. Выполнить FACT/GAP baseline-аудит по крупным блокам с привязкой к текущему коду/докам.
4. Сформировать отдельный Task Package на Phase 1 (contract hardening bootstrap).
5. Реализовать Phase 1 в рамках допустимого scope (без broad rewrite).
6. Прогнать проверки, собрать evidence и зафиксировать handoff для следующих фаз.

## DoD
- Master-ТЗ документ создан в repo и покрывает все major blocks + Analysis Gate protocol.
- Есть формализованный phase map (Phase 1..N) с acceptance criteria и rollback.
- Запущена Phase 1: минимум один реальный deliverable в коде/контрактах + тесты.
- Итог содержит FACT/GAP + риски + next implementation steps по фазам.

## Checks
- `scripts/session_check.sh`
- `rg -n "Universal Control Plane v1|Analysis Gate|Phase" docs/TASK_PACKAGES docs/REPORTS`
- Phase 1 checks (будут уточнены в phase package): pytest/lint/contract checks по затронутому scope.

## Evidence
- Master-ТЗ документ.
- FACT/GAP report с ссылками на файлы/контракты.
- Diff + test outputs + trace/audit evidence (для Phase 1 кодовых изменений).
- Session log + index update.

## Rollback
- Для doc-этапа: revert commit.
- Для Phase 1 кода: revert phase commit + disable via feature/config gates where applicable.

## No-go
- Начинать код без phase-specific analysis package.
- Ослаблять hard-law/policy/tenant guards.
- Делать runtime client-specific hardcode под новую нишу.
- Считать Phase закрытой без тестов и evidence.

## Branch / Worktree / Merge / Cleanup
- Branch: `feat/2026-02-22-universal-control-plane-v1-a500`
- Worktree: `/home/zhan/worktrees/2026-02-22-universal-control-plane-v1-a500`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после merge удалить worktree/branch

## Fitness Functions impacted
- P0-1 `_legacy.py` adapter-only
- P0-4 routing token for multi-branch
- P1-7 trace on early return
- P1-8 `decision_meta` required on user messages
- P1-9 policy rules-as-data
- P2-14 PR Task Package gate
- P2-15 local-first realism gate

## Риски/блокеры
- Историческая demo-coupling в runtime fallback paths.
- Частично завершенный org/RBAC wiring и консольные legacy path.
- Большой blast radius при попытке сделать много фаз в один PR.
- Требуется strict wave migration и feature gating.
