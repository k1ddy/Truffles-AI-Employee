# <Block report title>

Date
- YYYY-MM-DD

## Block identity
- `BLOCK_ID`: <required>
- `PARENT_BLOCK_ID`: <required|none>
- `DEPENDS_ON`: <required|none>
- `UNLOCKS`: <required|none>

## Input baseline (FACT)
- <что было до правки>

## FACT pre-check evidence (before changes)
- `<command>` -> <result>
- `<file/path:line>` -> <fact>

## One web search evidence
- `Query (exact)` -> <value>
- `Sources opened` -> <list>
- `Decision` -> <reuse|integrate|build> + reason
- `What was reused` -> <modules/libs/contracts>

## Root cause validation
- `Symptom` -> <statement>
- `Minimal reproduction` -> <command/steps>
- `Root cause statement` -> <mechanism>
- `Proof after fix` -> <evidence that mechanism is removed>

## Reuse-first outcome
- `Internal reuse applied` -> <yes/no + details>
- `External reuse applied` -> <yes/no + details>
- `If build-new` -> <why reuse/integration was not viable>

## Contract delta
- <какой контракт изменился>

## Implemented changes
- `<file/path>`

## Checks + outcomes
- `<command>` -> <result>

## Iteration budget outcomes
- `Planned max runs` -> <N>
- `Actual runs` -> <N>
- `Stop condition respected` -> <yes/no>
- `If exceeded` -> <approved by + reason>

## Evidence
- `<path/url>`

## Release safety decision
- `Strategy used` -> <canary|blue-green|flags|n/a>
- `Go/no-go signals observed` -> <summary>
- `Rollback readiness` -> <verified/not required + evidence>

## Canon/doc sync updates
- `Updated docs/specs`:
  - `<file/path>`
- `Drift resolved`: `yes` | `no`
- `If no`: <explicit GAP + owner + follow-up block>

## Residual GAP / Risks
- <что осталось>

## Handoff (for zero-context next agent)
- `Ready for next agent`: <yes/no>
- `Start from`: <first file/command>
- `Do not touch`: <sensitive areas>
- `Open risks`: <list>
- `First command to verify`: `<command>`

## Verdict
- `Passed` | `Blocked`
