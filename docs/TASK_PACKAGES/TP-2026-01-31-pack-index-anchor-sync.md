# TP-2026-01-31-pack-index-anchor-sync

- Название/цель: Реализовать pack-index build/versioning + anchor-sync (DEC-018) для data-driven сигналов и устранения бизнес-лексиконов в коде.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-018), `STATE.md` (PLAN: Unified Reasoning Core), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard-LAW/policy/pending pre-LLM; decision_meta/trace на каждый ранний возврат; без оркестрации в entrypoints/_legacy.py; порядок стадий не меняем.
- Scope:
  - Собрать compiled pack-index (anchors/lexicons/cards) из payload pack на publish.
  - Писать pack-index version/hash/compiled_at в payload и в knowledge snapshot.
  - Синхронизировать domain_router anchors в client.config из pack-index при publish.
  - Записать pack-index meta в decision_meta.signal_snapshot (источник/хэш/версия).
- Out of scope: изменения LLM contract, pack compiler/DSL, новые пакеты/контент, refactor stage order, DB migrations.
- Touch-list:
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/services/knowledge_snapshot_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_message_endpoint.py`
- Plan:
  1) Определить минимальный schema pack-index (anchors/lexicons/cards) и build helper.
  2) Встроить build/versioning в publish (payload_json) + hash/compiled_at.
  3) Добавить anchor-sync в client.config domain_router при publish.
  4) Обновить knowledge snapshot и decision_meta.signal_snapshot с pack-index meta.
  5) Добавить/обновить тесты на pack-index meta в decision_meta.
  6) Прогнать targeted pytest и сохранить evidence.
- DoD:
  - pack-index строится при publish, хранит hash/version/compiled_at.
  - client.config.domain_router anchors синхронизируются из pack-index.
  - decision_meta.signal_snapshot содержит pack-index meta.
  - Тесты проходят, evidence зафиксировано в STATE.md.
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot and pack_index"`
- Evidence:
  - pytest output + пример decision_meta/trace с pack-index meta.
- Rollback: `git revert COMMIT_SHA`.
- No-go:
  - Не добавлять бизнес-лексиконы в код.
  - Не менять порядок стадий и не трогать `_legacy.py`/entrypoints.
  - Не делать DB migrations в рамках этого P0 шага.
- Branch/worktree: `feat/2026-01-31-pack-index-a1`, `/home/zhan/worktrees/2026-01-31-pack-index-a1`, base `origin/main`, merge policy PR+CI, cleanup by Brain/Top Architect.
- Риски/блокеры: domain_pack/anchors могут отсутствовать в текущих payload — pack-index будет частично пустым; нужно логировать источник/версию.
