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
- Quality constant: бюджет/время не уменьшают acceptance criteria и обязательные quality gates.

## Scope
- Program-level ТЗ и delivery map для Universal Control Plane v1.
- FACT/GAP аудит по ключевым блокам (tenant, RBAC, capabilities, onboarding, policy governance, tools/providers, knowledge, SLA/SLO, compliance).
- Документирование целевого контракта, Analysis Gates, migration waves и atomized block-by-block implementation path.

## Out of scope
- Big-bang rewrite LLM/runtime.
- Изменение продуктовых обещаний вне канона.
- Ручные прод-правки без contract-first и evidence.

## Program block map (atomic queue)

| Business block | Implementation block ID | Depends on | Expected outcome |
|---|---|---|---|
| B01 Tenant Core & Data Isolation | `UCPV1-PHASE2-SLICE2-IMPL2` (finishing block) | `UCPV1-GATES-SANITARY` | Все remaining `/admin/*` пути нормализованы по tenant+role guard без cross-tenant drift |
| B02 RBAC & Governance Model | `UCPV1-PHASE2-SLICE2-IMPL2` (finishing block) | `UCPV1-GATES-SANITARY` | Серверный RBAC консистентен для Platform Admin first во всех provisioning/governance endpoints |
| B03 Domain Catalog + Capabilities v2 | `UCPV1-PHASE3` | `UCPV1-PHASE2-SLICE2-IMPL2` | Новая ниша создается через Console без изменений в core-коде |
| B04 Onboarding State Machine v2 | `UCPV1-PHASE4` | `UCPV1-PHASE3` | Go-live блокируется при обязательных blockers, workflow полностью серверный |
| B05 Policy Governance Split | `UCPV1-PHASE5` | `UCPV1-PHASE4` | Hard-law versioned и доступен только Platform Admin; branch override только operational/SLA |
| B06 Tool Registry Certification | `UCPV1-PHASE6` | `UCPV1-PHASE5` | Несертифицированные инструменты не могут активироваться в effective capabilities |
| B07 Provider/Channel Control | `UCPV1-PHASE7` | `UCPV1-PHASE6` | Явный lifecycle каналов и deterministic degrade при provider issues |
| B08 Knowledge Studio + Pack Compiler | `UCPV1-PHASE8` | `UCPV1-PHASE7` | Draft->Validate->Publish->Rollback контур обязателен и auditable |
| B09 Runtime Pack-Agnostic Decoupling | `UCPV1-PHASE9` | `UCPV1-PHASE8` | Runtime core не зависит напрямую от demo packs |
| B10 SLA/SLO Engine | `UCPV1-PHASE10` | `UCPV1-PHASE9` | SLA-профили управляют routing/escalation/alerts предсказуемо и проверяемо |
| B11 Compliance KZ Lifecycle | `UCPV1-PHASE11` | `UCPV1-PHASE10` | Retention/delete/export lifecycle автоматизирован с audit trail |
| B12 Control Tower | `UCPV1-PHASE12` | `UCPV1-PHASE11` | Platform Admin управляет fleet через Console без CLI как default |
| B13 Migration Program | `UCPV1-PHASE13` | `UCPV1-PHASE12` | Канареечная миграция до fleet с wave rollback gates |

## Touch-list (planned)
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase1-a500.md`
- `SPECS/CONTROL_PLANE.md` (if canon gaps must be formalized)
- `SPECS/MULTI_TENANT.md` (if contract clarifications required)
- `truffles-api/app/services/*` + `truffles-api/app/routers/console.py` (phase-scoped implementation only)
- `truffles-api/tests/*` (phase-scoped tests)

## Plan (1..N)
1. Session bootstrap in dedicated worktree + hooks + governance checks.
2. Build/refresh FACT baseline for current block from code/tests/evidence (not docs-only).
3. Run analysis gate for selected block and produce block-specific TP/Report.
4. Implement only one full block end-to-end in scoped files.
5. Run deterministic + required realism checks from block TP.
6. Update `BLOCK_GRAPH`, `STATE.md`, block Report, and session artifacts for zero-context handoff.
7. Pre-create/refresh next block TP+Report pointers to avoid manual bootstrap by next agent.

## DoD
- Master ТЗ фиксирует полный атомарный план по B01..B13 и ожидаемые outcomes.
- Очередь выполнения отражена в `docs/BLOCK_GRAPH.yaml` с корректными зависимостями.
- Каждый completed block имеет evidence-backed Report (`Verdict=Passed`) и doc sync.
- Нет пересечения с параллельными треками и нет изменений в чужих worktree.

## Checks
- `scripts/session_check.sh`
- `python3 - <<'PY'\nimport yaml, pathlib\npath = pathlib.Path('docs/BLOCK_GRAPH.yaml')\nyaml.safe_load(path.read_text(encoding='utf-8'))\nprint('BLOCK_GRAPH parse: OK')\nPY`
- `rg -n "Full atomic business-block plan|Program block map|UCPV1-PHASE13" docs/REPORTS docs/TASK_PACKAGES docs/BLOCK_GRAPH.yaml`
- Phase-specific checks from active block TP.

## Evidence
- Master TP update (this file).
- Master report update with atomic outcomes and current queue.
- Updated dependency graph (`docs/BLOCK_GRAPH.yaml`).
- Session log + index update for current session when block work is executed.

## Rollback
- For docs-only sync: revert commit.
- For phase code changes: revert block commit + disable by feature/config gate where applicable.

## No-go
- Начинать код блока без FACT pre-check и analysis gate.
- Ослаблять hard-law/policy/tenant guards.
- Делать runtime client-specific hardcode под новую нишу.
- Закрывать блок без tests + evidence + doc sync.

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
- P3-16..21 semantic-first + no quality downgrade + no workaround-as-architecture

## Риски/блокеры
- Историческая demo-coupling в runtime fallback paths.
- Частично завершенный org/RBAC wiring и консольные legacy path.
- Большой blast radius при попытке сделать несколько бизнес-блоков в одном PR.
- Drift code/docs если пропускать обязательный FACT pre-check перед каждым блоком.
