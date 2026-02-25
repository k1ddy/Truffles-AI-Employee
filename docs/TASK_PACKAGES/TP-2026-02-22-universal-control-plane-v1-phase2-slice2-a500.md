# TP-2026-02-22-universal-control-plane-v1-phase2-slice2-a500

## Название/цель
Universal Control Plane v1 / Phase 2 (slice 2): завершить анализ и нормализацию role-boundary для оставшихся `/admin/*` endpoint’ов (branch provisioning, identity/memberships, onboarding contracts, reference packs).

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-a500.md`

## Invariant
- Tenant isolation fail-closed.
- Branch-scoped operations не должны терять audit/rollback semantics.
- Никаких silent RBAC breaks без тестов/канон-синхронизации.

## Scope
- Analysis gate по оставшимся `/admin/*` endpoint’ам.
- Явная классификация endpoint’ов: `platform-only`, `client-owner/admin`, `manager-eligible`.
- Подготовка implementation очереди для следующей кодовой волны.

## Out of scope
- Полное завершение всех Phase 2 изменений в одной правке.
- Runtime decision-core изменения.

## Touch-list
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-analysis-a500.md`
- `SPECS/CONTROL_PLANE.md` (только если требуется явный canon delta)
- `truffles-api/app/routers/console.py` (только в последующей implementation wave)
- `truffles-api/tests/test_console_admin_provisioning.py` (только в последующей implementation wave)

## Plan (1..N)
1. Зафиксировать endpoint map (`/admin/*`) и фактические guards.
2. Сопоставить endpoints с целевой governance-моделью Platform Admin control plane.
3. Сформировать приоритетную implementation-очередь и risk/fallback notes.
4. Зафиксировать analysis output и перейти к коду в отдельной wave.

## DoD
- Есть evidence-backed analysis doc с endpoint map и очередью внедрения.
- Для каждой группы endpoint’ов определён целевой access contract.

## Checks
- `rg -n '\"/admin/' truffles-api/app/routers/console.py`
- scripted guard map extraction (local shell).

## Evidence
- Phase 2 slice 2 analysis report.

## Rollback
- Revert analysis docs commit.

## No-go
- Не применять массовые RBAC изменения без отдельной implementation wave и тестов.

## Branch / Worktree / Base
- Branch: `feat/2026-02-22-universal-control-plane-v1-a500`
- Worktree: `/home/zhan/worktrees/2026-02-22-universal-control-plane-v1-a500`
- Base: `origin/main`
