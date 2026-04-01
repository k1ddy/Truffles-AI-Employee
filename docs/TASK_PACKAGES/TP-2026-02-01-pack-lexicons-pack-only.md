# TP-2026-02-01-pack-lexicons-pack-only

- Название/цель: Полный перенос бизнес-лексиконов/anchors из кода в packs (domain/system) и pack-index; код использует только pack-данные.
- Canon refs: `STATE.md` (DEC-018 DONE), `docs/IMPERIUM_DECISIONS.yaml` (DEC-018), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Hard-LAW/policy/pending pre-LLM; decision_meta/trace на каждом раннем возврате; без оркестрации в entrypoints/_legacy.py; порядок стадий не меняем (stage order snapshot hash не трогаем).
- Scope:
  - Аудит всех бизнес-лексиконов/anchors в коде (info/booking/consult/ood).
  - Перенос лексиконов/anchors в packs (domain pack + system language pack).
  - Обновление pack-index/loader при необходимости для новых полей.
  - Замена использования код-лексиконов на pack-only lookup.
  - Тесты на pack-only поведение (decision_meta.signal_snapshot/intent signals).
- Out of scope: pack-compiler/DSL, shadow-replay, DB migrations, изменения stage order, изменение бизнес-логики вне лексиконов/anchors.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/ai_service.py`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/tests/test_message_endpoint.py`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-02-01-pack-lexicons-pack-only-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Инвентаризировать бизнес-лексиконы/anchors в коде и сопоставить с pack-ключами.
  2) Добавить/расширить pack-ключи (domain/system packs) и pack-index builder при необходимости.
  3) Заменить использование код-лексиконов на pack-only lookup.
  4) Добавить/обновить тесты на pack-only поведение и signal_snapshot.
  5) Прогнать targeted pytest и зафиксировать evidence.
- DoD:
  - Бизнес-лексиконы/anchors отсутствуют в коде; используются только pack-данные.
  - decision_meta.signal_snapshot содержит источники/версии.
  - Тесты зелёные, evidence записан в `STATE.md`.
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot or booking or info_bundle"`
  - `pytest -q truffles-api/tests/test_outbox_payload_contract.py::test_stage_order_snapshot_hash`
- Evidence:
  - pytest outputs (например, `/tmp/pytest_pack_lexicons_20260201.txt`).
  - Запись в `STATE.md` (Brain/Top Architect, до merge).
- Rollback: `git revert COMMIT_SHA`.
- No-go:
  - Не трогать `_legacy.py` и entrypoints orchestration.
  - Не менять порядок стадий без snapshot+hash.
  - Не делать pack-compiler/DSL в этом шаге.
- Branch/worktree: `feat/2026-02-01-pack-lexicons-pack-only-a1`, `/home/zhan/worktrees/2026-02-01-pack-lexicons-pack-only-a1`, base `origin/main`, merge policy PR→main, cleanup Top Architect.
- Риски/блокеры: часть лексиконов сейчас закодирована (info/часовые фразы); требуется аккуратная миграция в system pack без изменения поведения.
