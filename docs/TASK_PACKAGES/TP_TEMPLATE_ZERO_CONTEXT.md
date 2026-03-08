# TP-YYYY-MM-DD-<slug>-<agent>

## Block identity
- `BLOCK_ID`: <required>
- `PARENT_BLOCK_ID`: <required|none>
- `DEPENDS_ON`: <required|none>
- `UNLOCKS`: <required|none>

## Название/цель
<1-2 предложения>

## Canon refs
- `AGENTS.md`
- `STATE.md`
- <owner docs/specs>

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: <list>
- `Baseline commands`:
  - `<command>`
- `FACT findings`:
  - <what is implemented now; with file refs>
- `Detected drift (docs vs code)`: `none` | <list>

## One web search (mandatory before implementation)
- **Query (exact):** <exact search query string>
- **Date/time (local):** <YYYY-MM-DD HH:MM, Asia/Almaty>
- **Why this query is precise:** <1-3 lines>
- **Sources opened (from this query):**
  - <source 1: title + link>
  - <source 2: title + link>
- **Existing solutions found:** <libraries/tools/patterns>
- **Decision:** <reuse|integrate|build> + why it fits Truffles constraints
- **Rejected options:** <option + why rejected>
- **Open questions:** <if any>

## Root cause (mandatory)
- **Symptom:** <what is observed>
- **Minimal reproduction:** <steps/commands>
- **Evidence to capture:** <logs/trace/sql/tests>
- **Five Whys (or equivalent):**
  1. Why? ...
  2. Why? ...
  3. Why? ...
  4. Why? ...
  5. Why? ...
- **Root cause statement:** <mechanism>
- **Fix mechanism:** <change that removes the cause>

## Reuse-first plan (mandatory)
- **Internal reuse:** <existing modules/contracts/packs to extend>
- **External reuse:** <libs/tools/containers/services considered>
- **Why not reinvent the wheel:** <concrete reasons and constraints>

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation` | `closure_review` | `doc_only`
- **Doc touch budget (files):** <N>
- **Code dominance:** `required` | `off`
- **Override token:** `none` | `<UPPERCASE_OVERRIDE_TOKEN>`
- **Why this profile fits:** <1-3 lines>

## Invariant
- <что защищаем>

## Scope
- <что делаем>

## Out of scope
- <что не делаем>

## Touch-list
- `<file/path>`

## Plan (1..N)
1. <step>
2. <step>

## DoD
- <измеримые критерии>

## Checks
- `<command>`

## Evidence
- <какие артефакты и где>

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** <N>
- **Fail-fast / scenario lock:** <how loops are constrained>
- **Stop condition:** <when to stop and re-open RCA>
- **Escalation path:** <who approves extra loops>

## Release safety (mandatory for non-doc changes)
- **Strategy:** <canary|blue-green|flags|phased rollout>
- **Go/no-go signals:** <metrics/logs/traces + thresholds>
- **Rollback:** <fast and safe rollback path>
- **Post-release monitoring window:** <duration + checks>

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `<file/path>`
- `Drift closeout rule`:
  - update docs in this block; if impossible, record explicit `GAP` with owner + next block

## Rollback
- <как откатить>

## No-go
- <что запрещено>

## Risks/Blockers
- <риски и блокеры>

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: <explicit list>
- `Why not in this block`: <scope boundary + reason>
- `Risk if deferred`: <explicit risk>
- `Linked follow-up Task Package(s)`: <TP IDs>
- `Expiry/trigger to stop deferral`: <gate condition>

## Next-block contract (mandatory)
- `Next block objective`: <single objective for next block>
- `First deterministic check command`: `<command>`
- `Blocked-by conditions`: <what must be true first>
- `Owner role for closure`: <Brain|Top Architect|Hands>

## Handoff (for zero-context next agent)
- `Ready for next agent`: <yes/no>
- `Start from`: <first file/command>
- `Do not touch`: <sensitive areas>
- `Open risks`: <list>
- `First command to verify`: `<command>`
