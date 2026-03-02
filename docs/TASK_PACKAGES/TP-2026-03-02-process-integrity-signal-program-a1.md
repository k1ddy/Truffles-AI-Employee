# TP-2026-03-02-process-integrity-signal-program-a1

## Block identity
- `BLOCK_ID`: SIG-PROGRAM-S0-S4
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: none
- `UNLOCKS`: TP-S1 signal-manifest-externalization, TP-S2 signal-runtime-compiler, TP-S3 no-hardcode-gate-v2, TP-S4 cross-domain-contract-suite

## Название/цель
Собрать и зафиксировать обязательный process-контур для полной реализации `S0..S4` без потери контекста между сессиями: явный residual-debt register, программная карта шагов, и автоматический gate в session tooling.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/session_check.sh`
  - `scripts/session_start.sh`
  - `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/runbooks/EXECUTION_CYCLE.md`
- `Baseline commands`:
  - `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES|_llm_quality_build_hardcode_core_gate_status" ops/diagnose.py`
  - `rg -n "research_gate|root_cause_gate|reuse_gate|release_safety_gate" scripts/session_start.sh scripts/session_check.sh`
- `FACT findings`:
  - Hardcode gate покрывает только core files (`decision.py`, `booking.py`, `info.py`, `tool_registry_service.py`) и не покрывает `*_signal_service.py`.
  - session tooling уже enforce-ит research/root_cause/reuse/release, но не enforce-ит residual-debt continuity.
- `Detected drift (docs vs code)`: process drift exists (continuity gate missing).

## One web search (mandatory before implementation)
- **Query (exact):** architecture decision record technical debt register definition of done best practices
- **Date/time (local):** 2026-03-02 08:53, Asia/Almaty
- **Why this query is precise:** нужны практики, которые напрямую поддерживают непрерывность решений между сессиями: ADR рядом с кодом и управляемый debt register.
- **Sources opened (from this query):**
  - Google Cloud Architecture Center, ADR overview: https://cloud.google.com/architecture/architecture-decision-records
  - Scrum.org, Technical Debt Register: https://www.scrum.org/resources/blog/using-technical-debt-register-scrum
- **Existing solutions found:** ADR рядом с кодом + explicit debt register (с impact/remedy/ownership) как непрерывный backlog-механизм.
- **Decision:** integrate — внедрить в TP/session tooling обязательный residual-debt register + next-block contract.
- **Rejected options:** оставить только свободный текст в сессионных заметках (не enforce-ится, теряется между агентами).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** агенты закрывают локальный scope, но residual архитектурный долг теряется или переносится неявно; follow-up шаги не enforce-ятся процессом.
- **Minimal reproduction:**
  - `rg -n "Out of scope|массовая миграция всех regex" docs/TASK_PACKAGES/TP-2026-03-02-core-dehardcoding-sweep-a1.md`
  - `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES" ops/diagnose.py`
  - `rg -n "research_gate|root_cause_gate|reuse_gate|release_safety_gate" scripts/session_check.sh`
- **Evidence to capture:** diff session tooling/template/runbook + successful `session_check` after process updates.
- **Five Whys (or equivalent):**
  1. Почему остаточные долги теряются? — Нет обязательного поля в TP и нет tooling gate на continuity.
  2. Почему не ловится автоматически? — `session_check` валидирует только research/root_cause/reuse/release.
  3. Почему появляются повторные костыли? — Follow-up план не является блокирующим контрактом.
  4. Почему это критично? — Без continuity агенты стабилизируют локально и оставляют системный риск.
  5. Почему нужно чинить сейчас? — Перед S1..S4 нужно закрыть процессный источник повторения ошибок.
- **Root cause statement:** отсутствует enforce-имый process-контракт на residual architecture debt и next-block continuity.
- **Fix mechanism:** добавить mandatory секции в TP template + gate в `session_check` + default required flag в `session_start` + runbook/session-start protocol updates.

## Reuse-first plan (mandatory)
- **Internal reuse:** использовать текущий framework `session_check` gate-механизм (`required|optional|off`) и существующий TP template.
- **External reuse:** ADR + debt-register практики (Google Cloud ADR guidance, Scrum debt-register pattern).
- **Why not reinvent the wheel:** расширяем уже существующую модель gate-ов, а не создаем новый независимый pipeline.

## Invariant
- Не ломать существующие сессии retroactively.
- Новые сессии должны получать continuity gate по умолчанию.
- Никаких runtime behavioral changes в этом блоке.

## Scope
- Добавить process continuity gate для TP (`Residual architecture debt` + `Next-block contract`).
- Сделать default `required` для новых сессий.
- Зафиксировать программный контекст `S0..S4` как единый reference TP.

## Out of scope
- Реализация S1/S2/S3/S4 runtime/code migration.
- Изменение бизнес-логики webhook/runtime.

## Touch-list
- `scripts/session_check.sh`
- `scripts/session_start.sh`
- `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-process-integrity-signal-program-a1.md`

## Plan (1..N)
1. Добавить process gate mode `context_integrity_gate` в session tooling.
2. Добавить mandatory continuity секции в TP template.
3. Обновить session/runbook протокол, чтобы continuity был частью обязательного цикла.
4. Зафиксировать S0..S4 program map и link из parent TP.
5. Прогнать deterministic checks для tooling.

## DoD
- В `session_start` новые сессии получают `context_integrity_gate: required`.
- `session_check` при `required` блокирует TP без continuity секций.
- TP template содержит mandatory continuity секции.
- Parent TP содержит явную ссылку на program TP `S0..S4`.
- `scripts/session_check.sh` проходит в текущей сессии.

## Checks
- `bash -n scripts/session_check.sh`
- `bash -n scripts/session_start.sh`
- `scripts/session_check.sh`

## Evidence
- Diff tooling/template/runbook/TP.
- Вывод `bash -n` checks.
- Вывод `scripts/session_check.sh`.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0 (doc/process only).
- **Fail-fast / scenario lock:** not applicable.
- **Stop condition:** если gate ломает backward compatibility существующих сессий — откат и перевод gate в opt-in.
- **Escalation path:** Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout for process gate (new sessions only by default, legacy unaffected).
- **Go/no-go signals:** `session_check` green в текущей сессии; отсутствие регресса в existing metadata parsing.
- **Rollback:** revert commit.
- **Post-release monitoring window:** next 3 sessions using `session_start.sh`.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/runbooks/EXECUTION_CYCLE.md`
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `Drift closeout rule`:
  - process/tooling/doc updates only in one block; no deferred doc sync.

## Rollback
- `git revert <commit>` in this branch.

## No-go
- Не изменять runtime business logic.
- Не вводить gate, который ломает legacy sessions без metadata fallback.

## Risks/Blockers
- Слишком жесткий gate может блокировать текущие legacy TPs; mitigation: gate active only when `context_integrity_gate=required`.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:` signal literals/regex still exist in `*_signal_service.py`.
- `Why not in this block:` этот TP про process continuity, не runtime migration.
- `Risk if deferred:` повторный перенос hardcode между слоями и разрыв контекста между агентами.
- `Linked follow-up Task Package(s):` `TP-S1`, `TP-S2`, `TP-S3`, `TP-S4` under this program block.
- `Expiry/trigger to stop deferral:` перед закрытием `S2` residual должен стать data-driven manifest + compiler, иначе S2 = BLOCKED.

## Next-block contract (mandatory)
- `Next block objective:` S0 gate-fix + start S1 signal manifest externalization.
- `First deterministic check command:` `rg -n "LLM_QUALITY_HARDCODE_CORE_PREFIXES|context_integrity_gate" ops/diagnose.py scripts/session_check.sh scripts/session_start.sh`
- `Blocked-by conditions:` continuity gate not enforced in tooling.
- `Owner role for closure:` Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `scripts/session_check.sh` continuity gate section + TP template continuity sections
- `Do not touch`: runtime behavior files outside process scope
- `Open risks`: legacy TP compatibility
- `First command to verify`: `scripts/session_check.sh`
