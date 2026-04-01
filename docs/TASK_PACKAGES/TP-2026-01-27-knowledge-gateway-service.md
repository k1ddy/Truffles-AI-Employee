# TP-2026-01-27 — Knowledge Gateway Service (shadow)

## Название/цель
Вынести Knowledge Gateway в отдельный контейнер (shadow), без переключения трафика core, с верификацией snapshot API и фиксацией evidence.

## Canon refs
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-016)
- `STATE.md` (Provider Gateway + Knowledge Snapshot roadmap)
- `SPECS/ARCHITECTURE.md`

## Invariant
- Hard‑LAW/policy/pending остаются pre‑LLM и fail‑closed.
- tenant_context обязателен, cross‑tenant запрещён.
- consult остаётся pack‑only; core не трогаем.

## Scope
- Новый entrypoint `knowledge_gateway_app` (FastAPI) для `/knowledge/snapshot` + `/health`.
- Отдельный контейнер knowledge‑gateway (shadow, без внешнего трафика).
- Обновление docs (ARCH/TECH/STRUCTURE/STATE) и session log.

## Out of scope
- Перевод core на HTTP‑gateway.
- Внешний ingress/Traefik‑маршрутизация.
- Изменения decision pipeline.

## Touch‑list
- `truffles-api/app/knowledge_gateway_app.py`
- `truffles-api/tests/test_knowledge_snapshot_gateway.py`
- `scripts/restart_knowledge_gateway.sh`
- `TECH.md`
- `SPECS/ARCHITECTURE.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-27-knowledge-gateway-service-arch.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Добавить `knowledge_gateway_app` (router + /health).
2) Обновить тесты для нового app (snapshot enabled/disabled + /health).
3) Добавить `scripts/restart_knowledge_gateway.sh` (docker run, internal‑net, порт 8010, env override `KNOWLEDGE_SNAPSHOT_ENABLED=1`).
4) Обновить `TECH.md`, `SPECS/ARCHITECTURE.md`, `STRUCTURE.md`.
5) Запустить контейнер, проверить `/health` и `/knowledge/snapshot` (curl → `/tmp`).
6) Записать evidence в `STATE.md` (до merge).

## DoD
- Контейнер `truffles-knowledge-gateway` запущен и отвечает `/health`.
- `/knowledge/snapshot` отдаёт валидный snapshot (tenant_context + packs).
- Тесты проходят.
- Docs и evidence отражены в `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_knowledge_snapshot_gateway.py`

## Evidence
- CI run URL.
- `curl -s http://127.0.0.1:8010/health`.
- `/tmp/knowledge_gateway_snapshot_20260127_140612.json`.
- Запись в `STATE.md`.

## Rollback
- Остановить/удалить контейнер `truffles-knowledge-gateway`.
- Откатить скрипт/entrypoint/доки.

## No‑go
- Маршрутизировать core через gateway.
- Открывать публичный доступ без токена/allowlist.
- Менять decision pipeline.

## Branch / Worktree
- Branch: `feat/2026-01-27-knowledge-gateway-service-arch`
- Worktree: `/home/zhan/worktrees/2026-01-27-knowledge-gateway-service-arch`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain/Top Architect после merge
