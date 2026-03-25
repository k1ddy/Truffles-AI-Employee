# TP-2026-02-02-minimum-data-canon-alignment

- Название/цель: Канонизировать Minimum Data Contract + SAFE_MODE semantics (FACT/COLLECT/HANDOFF vs COLLECT/HANDOFF), добавить дисклеймеры и RU/KZ-варианты в канон, синхронизировать onboarding/console gate с новым контрактом.
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-021), `STRATEGY/REQUIREMENTS.md`, `docs/PROCESSES.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `STATE.md` (GAP: safe-mode semantics + RU/KZ/disclaimers).
- Invariant: truth-first; pack-only; нет runtime-поведенческих изменений вне gate/validation; trace/meta не ломаются.
- Scope:
  - Зафиксировать канон safe-mode outcomes и применить в `STRATEGY/REQUIREMENTS.md` + `docs/PROCESSES.md`.
  - Зафиксировать Minimum Data Contract в `SPECS/VERTICAL_PACK_KIT.md` (дисклеймеры, RU/KZ варианты, расположение полей и правила валидации).
  - Синхронизировать onboarding gate и UI (Go/No-Go missing labels) с новым контрактом.
  - Тесты на validation/onboarding.
- Out of scope: обновление pack-данных, миграции, LLM-промпты, runtime pipeline кроме gate/validation.
- Touch-list:
  - `STRATEGY/REQUIREMENTS.md`
  - `docs/PROCESSES.md`
  - `SPECS/VERTICAL_PACK_KIT.md`
  - `truffles-api/app/services/knowledge_validation.py`
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/tests/test_knowledge_validation.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1) Принять канон safe-mode outcomes и зафиксировать в `STRATEGY/REQUIREMENTS.md` + `docs/PROCESSES.md`.
  2) Зафиксировать Minimum Data Contract (дисклеймеры + RU/KZ варианты) в `SPECS/VERTICAL_PACK_KIT.md`.
  3) Синхронизировать onboarding gate/labels с контрактом.
  4) Обновить тесты и записать evidence в `STATE.md`.
- DoD:
  - Конфликт safe-mode semantics устранён в канон-доках.
  - Minimum Data Contract включает дисклеймеры и RU/KZ варианты.
  - Onboarding Go/No-Go использует тот же контракт; UI показывает missing поля.
  - Тесты зелёные.
- Checks:
  - `pytest -q truffles-api/tests/test_knowledge_validation.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - `npm --prefix console-web run lint` (если UI трогали)
- Evidence:
  - CI/test логи + ссылки на канон-доки + запись в `STATE.md`.
- Rollback: revert commit.
- No-go: любые runtime-изменения вне gate/validation; правки pack-данных; DB миграции.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-minimum-data-canon-alignment-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-minimum-data-canon-alignment-a1`
  - Base: `origin/main`
  - Merge: PR → `main`
  - Cleanup: `scripts/session_end.sh --status done` + удалить worktree/branch
- Риски/блокеры: нужно согласовать канон safe-mode outcomes (FACT допустим или нет); новые требования могут ломать существующие packs.
