# TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500

## Block identity
- `BLOCK_ID`: UCPV1-GATES-SANITARY
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE2-SLICE2-IMPL1
- `UNLOCKS`: UCPV1-PHASE2-SLICE2-IMPL2

## Название/цель
Санитарный контур для program-трека `universal_control_plane_v1`: включить строгое zero-context enforcement только по явному opt-in в session log, без влияния на параллельные реализации.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/session_check.sh`
  - `scripts/zero_context_gate.sh`
  - `docs/BLOCK_GRAPH.yaml`
- `Baseline commands`:
  - `bash -n scripts/session_check.sh && bash -n scripts/zero_context_gate.sh`
  - `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml`
- `FACT findings`:
  - zero-context gate существует и проверяет обязательные секции TP/Report.
  - enforcement был ручным и не привязан к metadata текущей session.
  - параллельные треки не должны быть затронуты обязательными gate-ужесточениями.
- `Detected drift (docs vs code)`: `none`

## One web search (mandatory before implementation)
- Historical note: this section is backfilled on `2026-03-27` so the legacy block remains zero-context compliant under the current gate contract.
- **Query (exact):** `github actions bash ripgrep not installed fallback grep script`
- **Date/time (local):** `2026-03-27 13:47 Asia/Almaty`
- **Sources opened (from this query):**
  - GitHub Actions workflow syntax: `https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions`
  - GNU grep manual: `https://www.gnu.org/software/grep/manual/grep.html`
- **Decision:** keep the gate shell-only and add deterministic `grep` fallback instead of assuming `rg` availability on every CI runner.
- **Rejected options:** keep hard `rg` dependency; disable zero-context gate in CI; vendor-lock the gate to one runner image.

## Root cause (mandatory)
- **Symptom:** `session-gate` can fail on CI before evaluating the real TP/report contract because `scripts/zero_context_gate.sh` assumes `rg` exists and older zero-context documents miss newer mandatory sections.
- **Minimal reproduction:** `bash scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml`
- **Evidence:** historical TP/report predate the current zero-context template; current CI runner can execute without `rg`; gate aborts before real semantic validation.
- **Five Whys:**
  - Why did the gate fail? Because `zero_context_gate.sh` used `rg` unconditionally.
  - Why was that fatal? Because the runner image did not guarantee `rg`.
  - Why did the block still fail after adding fallback? Because the historical TP/report were missing newly-required sections.
  - Why were they missing? Because the block was authored before the current zero-context template hardened.
  - Why does that matter now? Because session-level zero-context enforcement validates old artifacts with the new contract.
- **Root cause statement:** zero-context enforcement assumed both a tool (`rg`) and a document template version that were not universal across CI and historical block artifacts.
- **Fix mechanism:** add `grep` fallback to the gate and backfill the historical TP/report to the current zero-context section contract.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse the existing zero-context gate/report structure and backfill only the missing mandatory sections instead of inventing a second compatibility gate.
- **External reuse:** reuse standard POSIX/GNU shell tools (`grep`) as the fallback mechanism instead of introducing a new dependency.
- **Decision:** `reuse -> integrate`; no new gate script or doc format fork.

## Invariant
- Параллельные worktree/ветки не блокируются нашими контрольно-качественными правилами.
- `truffles-main/main` не используется как рабочая директория.
- Zero-context полнота блоков становится проверяемой для нашего program-трека.

## Scope
- Добавить в `scripts/session_check.sh` opt-in zero-context gate (`required|off|optional`) на основе session metadata.
- Зафиксировать отдельный zero-context блок в `docs/BLOCK_GRAPH.yaml`.
- Подготовить session metadata для включения gate только в нашей сессии.
- Обновить runbook для явного protocol-level opt-in.

## Out of scope
- Любые изменения чужих worktree/веток.
- Принудительное включение zero-context gate для всех сессий проекта.
- Изменения runtime behavior или business logic.

## Touch-list
- `scripts/session_check.sh`
- `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
- `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`

## Plan (1..N)
1. Добавить в `session_check` opt-in enforcement, читающий `zero_context_*` поля только из текущей session log.
2. Оформить отдельный block-artifact pair (TP/Report) для санитарного контура.
3. Подключить блок в `BLOCK_GRAPH.yaml` как зависимость перед `UCPV1-PHASE2-SLICE2-IMPL2`.
4. Включить `zero_context_gate: required` в текущей session log только для нашего трека.
5. Прогнать проверки и зафиксировать outcomes в report.

## DoD
- `scripts/session_check.sh` валидирует zero-context block только при `zero_context_gate: required`.
- Для текущей сессии включен zero-context enforcement через session metadata.
- `docs/BLOCK_GRAPH.yaml` отражает новый блок и корректные `depends_on/unlocks`.
- Проверки `bash -n`, `zero_context_gate`, `session_check` проходят.

## Checks
- `bash -n scripts/session_check.sh`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml`
- `scripts/session_check.sh`

## Evidence
- Diff в `scripts/session_check.sh`.
- `docs/BLOCK_GRAPH.yaml` с новым `BLOCK_ID`.
- Session metadata в `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`.
- Report с командами и результатами.

## Token / run budget (mandatory for expensive suites)
- `Max full runs`: `0`
- `Budget rule`: только shell/doc deterministic checks; дорогие suites не требуются.
- `Stop condition`: любой fail в `zero_context_gate` или `session_check` останавливает блок до исправления контракта.

## Release safety (mandatory for non-doc changes)
- `Strategy:` docs/scripts only; rollout через обычный PR merge без runtime deploy.
- `Go/no-go signals:` `bash -n`, `zero_context_gate`, `session_check` проходят; параллельные сессии без `zero_context_gate: required` не ломаются.
- `Rollback:` revert shell/doc changes и убрать `zero_context_*` metadata у текущей session.
- `Post-release monitoring window:` первый CI/session-gate прогон после merge.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
  - `docs/runbooks/EXECUTION_CYCLE.md`
  - `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
  - `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
- `Drift closeout rule`:
  - если gate-контракт меняется, шаблоны и runbook синхронизируются в том же блоке;
  - несинхронность считается блокирующим GAP и не переносится молча.

## Rollback
- Revert commit этого блока.
- Удалить `zero_context_*` поля из session log текущего трека.
- Вернуть `BLOCK_GRAPH.yaml` к предыдущему состоянию.

## No-go
- Не включать global hard gate, который сломает чужие параллельные задачи.
- Не менять чужие ветки/worktree.
- Не выполнять работу в `truffles-main/main`.

## Risks/Blockers
- Исторические phase reports не в полном zero-context формате; gate включается по session opt-in, поэтому миграция делается поэтапно.
- Если `zero_context_*` пути в session metadata устареют, `session_check` корректно упадет и остановит commit.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml`
- `Do not touch`: чужие session logs и другие worktree
- `Open risks`: постепенная миграция старых фазовых документов к новому шаблону
- `First command to verify`: `scripts/session_check.sh`
