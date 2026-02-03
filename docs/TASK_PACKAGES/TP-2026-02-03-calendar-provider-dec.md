# TP-2026-02-03 — Calendar provider policy (Google) + GAP

- **Название/цель:** зафиксировать политику calendar‑provider (Google) для SoT appointments: outbound/inbound sync, конфликт‑политика, staleness‑gate для confirm_slots, и оформить GAP.
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml` (DEC-013), `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `contracts/integrations/calendar_port.v1.md`, `STATE.md`.

## Invariant
- SoT по записям — Postgres; внешний календарь = проекция + источник занятости.
- Внешние вызовы только async через outbox (без request‑path блокировок).
- Branch isolation для токенов, календарей и доступности.
- Без здорового провайдера — только collect_preferences, без обещаний слотов.

## Scope
- Анализ текущей реализации (appointments/blocks/tokens/OAuth/legacy sync).
- Решения: outbound‑sync, inbound‑busy‑only, conflict policy, staleness‑gate.
- Обновление DEC/Specs + GAP/PLAN в `STATE.md`.

## Out of scope
- Код/миграции/worker запуск.
- UI/Console изменения.

## Touch-list
- `docs/IMPERIUM_DECISIONS.yaml`
- `docs/IMPERIUM_GAPS.yaml`
- `SPECS/ARCHITECTURE.md`
- `SPECS/MULTI_TENANT.md`
- `contracts/integrations/calendar_port.v1.md`
- `STATE.md`

## Plan
1) Зафиксировать анализ текущего календарного контура (SoT vs legacy booking).
2) Прописать provider policy: outbound via outbox, inbound busy-only, conflict policy, staleness gate.
3) Обновить DEC/Specs для канонизации правил.
4) Добавить GAP в `docs/IMPERIUM_GAPS.yaml` + PLAN в `STATE.md`.

## DoD
- DEC обновлён с правилами provider‑sync/conflict/staleness.
- Specs отражают gating и branch‑scope.
- GAP и PLAN зафиксированы в `STATE.md`.

## Checks
- `rg -n "calendar_scheduling|availability_provider|confirm_slots|outbox" docs/IMPERIUM_DECISIONS.yaml SPECS/ARCHITECTURE.md SPECS/MULTI_TENANT.md`

## Evidence
- Док‑диффы + запись PLAN/GAP в `STATE.md` (без runtime evidence).

## Rollback
- Откат doc‑изменений.

## No-go
- Любые code changes/миграции.
- Изменения в `_legacy.py`.

## Branch / Worktree / Merge
- Branch: `docs/calendar-provider-dec-2026-02-03`
- Worktree: `/home/zhan/worktrees/2026-02-03-calendar-provider-dec-a1`
- Base ref: `origin/main`
- Merge policy: PR + CI green (doc-only допустим fast-forward по решению Brain/Top Architect)
- Cleanup: удалить ветку и worktree после merge
