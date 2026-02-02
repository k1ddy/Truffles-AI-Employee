# TP-2026-02-02-hybrid-llm-plan-dec

- Название/цель: Зафиксировать DEC и канон по гибридному LLM‑плану (plan → validate → tool → compose), закрепить минимальный what‑if набор, синхронизировать owner‑docs и подготовить TP на имплементацию.
- Canon refs: `STATE.md` (2026-01-22 Plan #1), `docs/IMPERIUM_DECISIONS.yaml`, `STRATEGY/REQUIREMENTS.md`, `STRATEGY/VISION.md`, `STRATEGY/TECH_ROADMAP.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ESCALATION.md`.
- Invariant: факты только через packs/tools; лексиконы без расширения (fallback‑механика); LLM — pack‑ref‑only; порядок стадий неизменен; trace/meta пишутся на ранних возвратах; `_legacy.py` adapter‑only.
- Scope:
  - DEC: hybrid LLM‑plan (JSON‑контракт + валидатор + tool‑first).
  - Контракт LLM‑плана и правила валидации (pack_refs/tool_args/outcome/language/confidence/goal/slot_state).
  - Noise‑policy и re‑entry как канон (без сценарного кода).
  - Минимальный what‑if набор (tool/шум/состояния).
  - Синхронизация owner‑docs + roadmap.
  - Подготовка TP на имплементацию (код + тест‑матрица).
  - Обновление `STATE.md`.
- Out of scope: реализация в коде, изменение порядка стадий, расширение лексиконов, live‑check.
- Touch-list:
  - `docs/IMPERIUM_DECISIONS.yaml`
  - `STRATEGY/REQUIREMENTS.md`
  - `STRATEGY/VISION.md`
  - `STRATEGY/TECH_ROADMAP.md`
  - `SPECS/ARCHITECTURE.md`
  - `SPECS/CONSULTANT.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `SPECS/ESCALATION.md`
  - `STATE.md` (обновление только Brain/Top Architect)
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-hybrid-llm-plan-dec.md`
- Plan:
  1) Зафиксировать DEC “Hybrid LLM‑plan” в `docs/IMPERIUM_DECISIONS.yaml`.
  2) Описать контракт LLM‑плана и валидатор (rules + rejection paths) в specs.
  3) Закрепить noise‑policy/re‑entry/goal‑persistence.
  4) Добавить минимальный what‑if набор в канон консультанта.
  5) Синхронизировать Vision/Requirements/Roadmap.
  6) Подготовить TP на имплементацию (код + тест‑матрица).
  7) Обновить `STATE.md` с evidence.
- DoD:
  - DEC записан и согласован в `docs/IMPERIUM_DECISIONS.yaml`.
  - Контракт LLM‑плана + правила валидатора описаны в спецификациях.
  - Минимальный what‑if набор закреплён в каноне.
  - Roadmap/Requirements синхронизированы.
  - TP на имплементацию подготовлен.
  - `STATE.md` обновлён (FACT/PLAN с путями evidence).
- Checks:
  - `scripts/session_check.sh` (doc‑only).
- Evidence:
  - Обновлённые документы (DEC + specs/strategy).
  - Запись в `STATE.md` (ссылки на изменения).
- Rollback: revert doc‑commit.
- No-go:
  - Изменения кода или порядка стадий.
  - Расширение лексиконов.
  - Live‑check/прод‑интеграции.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-02-hybrid-llm-plan-dec-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-02-hybrid-llm-plan-dec-a1`
  - Base: `origin/main`
  - Merge: doc‑only fast‑forward в `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: несогласованность с уже принятым DEC‑010; потребуется чёткое позиционирование как расширения/уточнения, без противоречий.
