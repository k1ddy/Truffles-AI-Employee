# TP-2026-02-02-learning-consent-pack-candidates

- Название/цель: Реализовать consent/анонимизацию/retention + auto-ingest approvals для pack candidates (DEC-022).
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-022), `STRATEGY/REQUIREMENTS.md`, `SPECS/ACTIVE_LEARNING.md`, `SPECS/SYSTEM_REFERENCE.md`, `STATE.md` (PLAN).
- Invariant: consent-first; anonymized-only learning; pack-only facts; ручное одобрение перед попаданием в packs; trace/meta обязательны.
- Scope:
  - Модель согласия: флаги consent, режим анонимизации, retention_days.
  - Автоматический сбор pack candidates (facts/anchors/lexicon hints) только при consent.
  - Очередь кандидатов + approval workflow (API + audit).
  - Интеграция с pack compiler (approved-only).
  - Тесты и документация.
- Out of scope: обучение LLM, авто-деплой packs без ревью, сбор данных без consent.
- Touch-list:
  - `truffles-api/app/models/`
  - `truffles-api/app/migrations/`
  - `truffles-api/app/schemas/`
  - `truffles-api/app/services/learning_service.py`
  - `truffles-api/app/services/learned_response_service.py`
  - `truffles-api/app/services/pack_compiler_service.py`
  - `truffles-api/app/routers/admin.py`
  - `console-web/` (approval UI)
  - `SPECS/ACTIVE_LEARNING.md`
  - `STATE.md`
- Plan:
  1) Добавить data model для consent/retention + audit trail.
  2) Реализовать candidate extractor + anonymizer (PII redaction).
  3) Создать approval API + audit + console UI.
  4) Подключить approved candidates к pack compiler (feature-flag).
  5) Покрыть тестами (unit/integration) и обновить docs/STATE.
- DoD:
  - Без consent кандидаты не создаются.
  - Approved-only попадают в pack compiler.
  - Audit trail фиксирует approve/reject.
  - Тесты green + evidence (CI/logs/SQL).
- Checks:
  - `pytest -q truffles-api/tests/test_learning_service.py`
  - `pytest -q truffles-api/tests/test_pack_compiler.py -k candidates`
- Evidence:
  - CI run + test logs.
  - SQL/trace для consent и approval.
- Rollback: revert commit; disable candidate ingest feature-flag.
- No-go: автопубликация без approval; хранение PII; обход consent.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-learning-consent-pack-candidates-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-learning-consent-pack-candidates-a1`
  - Base: `origin/main`
  - Merge: PR to `main` (code)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: политика consent/retention должна быть согласована с owner/legal.
