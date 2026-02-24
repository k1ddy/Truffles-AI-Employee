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

## Contract delta
- <какой контракт изменился>

## Implemented changes
- `<file/path>`

## Checks + outcomes
- `<command>` -> <result>

## Evidence
- `<path/url>`

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
