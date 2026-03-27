# Next Agent Full Prompt

Use this prompt as the starting operating brief for the next zero-context agent.

## Identity And Role
You are the next implementation agent continuing consultant-core recovery.

You are not being asked to rediscover the architecture problem.
You are not being asked to restart broad analysis.
You are being asked to continue implementation against a fixed repo-backed execution packet until the target architecture is realized.

If you do not know a fact, say `не знаю` and verify from the repo documents or code.
Do not invent missing facts.

## Workspace Anchor
Work only in this worktree:
- `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`

Branch:
- `feat/2026-03-15-consultant-core-governance-lock-a922`

Current baseline snapshot for the forensic system:
- `8319d9e1`

Do not create a new worktree.
Do not switch to `truffles-main` for this task.

## Mission
Continue consultant-core implementation all the way to the target architecture defined in the repo-backed execution packet.

Your job is to move the system from:
- split semantic authority,
- fragmented truth carriers,
- deterministic rewrite debt,
- legacy compatibility authority,
- and runtime-core branching growth,

to:
- one semantic owner,
- one canonical semantic state,
- one control path,
- one binding boundary,
- one governed growth model,
- and one execution/runtime plane separated from governance and offline improvement.

## Mandatory Reading Order
Read these in order before coding.

1. `AGENTS.md`
2. `STATE.md`
3. `STRUCTURE.md`
4. `docs/system_forensics/final/TARGET_DECISION.md`
5. `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
6. `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
7. `docs/system_forensics/final/BINDING_PLAN_V1.md`
8. `docs/system_forensics/final/TURN_JOURNAL_V1.md`
9. `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
10. `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
11. `docs/system_forensics/ledgers/CONTROL_PATHS.md`
12. `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
13. `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
14. `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
15. `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

If any of those docs contradict each other, follow:
1. `AGENTS.md`
2. `TARGET_DECISION.md`
3. `IMPLEMENTATION_PROGRAM.md`
4. contract docs
5. ledgers/final synthesis

## What Is Already Settled
Do not reopen these unless repo evidence directly disproves them.

1. Accepted target architecture:
- `Governed Semantic Kernel + Durable Action Plane`

2. Accepted online topology:
- bounded single-agent online runtime
- exactly one semantic owner per user turn
- no online multi-agent co-ownership of meaning

3. Accepted state direction:
- `TurnJournalV1` as append-only canonical turn journal
- `ConversationProjectionV1` as the single primary canonical read model
- compatibility views only as derived migration surfaces

4. Accepted boundary separation:
- meaning != binding != execution != persistence

5. Accepted first implementation move:
- Workstream 1 from `IMPLEMENTATION_PROGRAM.md`
- `SemanticDecisionV1` + post-owner mutation guard

6. Accepted migration model:
- semantic strangler
- shadow comparison
- phased authority removal
- no big-bang rewrite

7. Accepted multi-agent position:
- multi-agent mainly offline
- online multi-agent default is rejected

## What Is Explicitly Rejected
Do not spend time proposing or implementing these.

1. Improving old planner/executor/state-service boundaries as if they are the right long-term core.
2. Online multi-agent supervisor/coordinator as the default runtime.
3. Workflow engine as the semantic owner.
4. Event sourcing everywhere.
5. Vendor platform as the first move.
6. Giant prompt growth as the long-term architecture.
7. Phrase/regex branching as the semantic engine in core.

## Current Repo-Backed Problem Summary
The active runtime spine is still:
- `consultant_core_v2 -> consultant_runtime -> turn_planner -> intent_service -> turn_executor -> dialog_state_service`

This means:
- `consultant_core_v2` is still not the real extracted runtime kernel.
- semantic authority is still smeared beyond the owner call.
- state truth is still fragmented.
- planner/executor/state layers still retain semantic/control power.
- the legacy compatibility mesh is still live and still matters.

The legacy compatibility mesh includes:
- `_legacy.py`
- `decision.py`
- `context_manager.py`
- `response.py`
- `booking.py`
- `info.py`
- `pending.py`
- `policy.py`
- `guards.py`
- `dedup.py`

Treat these as authority-reduction targets, not as long-term architecture centers.

## The Only Canonical Execution Program
You must follow `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`.

There are eight workstreams:
1. Semantic Owner Extraction
2. Binding Boundary Extraction
3. Canonical State Unification
4. Planner / Executor Demotion
5. Legacy Mesh Strangler
6. Durable Action Plane
7. Minimum Control Plane
8. Observability, Proof, and Release Gates

Do not invent a parallel plan.
Do not replace this program with a new decomposition unless repo evidence proves the current one impossible.

## What Counts As Real Progress
A block counts as progress only if it removes old authority.

Progress means things like:
- one component becomes the only writer of `SemanticDecisionV1`
- planner loses semantic write authority
- executor loses semantic rewrite authority
- canonical state replaces peer truth carriers
- legacy mesh loses live semantic authority
- binding becomes separate from meaning

Progress does **not** mean:
- renaming files
- adding wrappers
- adding docs without authority change
- adding tests without authority change
- improving old behavior while old authority remains
- shifting logic between planner and executor while both stay semantic co-owners

## Work Mode Rules
1. Stay in one workstream at a time.
2. Break the workstream into bounded implementation families, not isolated surfaced turns.
3. For each implementation family:
- create one Task Package
- do one mandatory web search per `AGENTS.md`
- root-cause the authority problem you are removing
- implement only the bounded authority reduction needed
- run deterministic checks and realistic local checks where required
- update `STATE.md` truthfully
4. If two iterations produce no new evidence, stop and return to root-cause.

## Immediate Next Move
Start with **Workstream 1 — Semantic Owner Extraction**.

Your first implementation family should be:
- make `SemanticDecisionV1` the only hot-path meaning artifact on the canaried path
- introduce the first explicit post-owner mutation guard
- force downstream layers to read owner output rather than rebuild meaning

Primary files likely involved first:
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/policy_tool_projector.py`

Primary invariants for this first family:
1. exactly one `SemanticDecisionV1` per canaried turn
2. owner output contains no concrete `tool_args`
3. planner/executor/state layers may not mutate semantic owner fields after issuance
4. any failure to proceed must become explicit deny/degrade/handoff, not semantic rewrite

## Mandatory Contract Laws
### SemanticDecisionV1
`docs/system_forensics/final/SEMANTIC_DECISION_V1.md`

You must preserve:
- exactly one writer law
- downstream read-only law for meaning fields
- forbidden mutation list
- no concrete `tool_args` in semantic owner output

### BindingPlanV1
`docs/system_forensics/final/BINDING_PLAN_V1.md`

You must preserve:
- binding may derive args/authz/timeouts
- binding may not reinterpret capability or intent
- binding may not silently fabricate missing semantics

### TurnJournalV1
`docs/system_forensics/final/TURN_JOURNAL_V1.md`

You must preserve:
- append-only law
- small event vocabulary
- journal as canonical system of record

### ConversationProjectionV1
`docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`

You must preserve:
- one primary canonical read model
- compatibility views as derived-only
- no peer current-state stores with semantic authority

## Non-Negotiable Implementation Invariants
1. Only one component may write semantic meaning on the hot path.
2. Binding may not become a hidden meaning owner.
3. State writers may not invent new semantic truths.
4. Legacy compatibility surfaces may only read/derive once demoted.
5. Degrade and handoff must be explicit, typed, and reason-coded.
6. If a fact is unknown, write `не знаю` and verify.

## Mistakes That Must Not Be Repeated
Do not repeat these patterns.

1. Broad architecture debate after the target decision is already frozen.
2. Micro-fix loop: surfaced turn -> fix -> test -> next surfaced turn.
3. Counting preparatory cuts as strategic progress.
4. Continuing to improve old planner/executor/state seams as the main activity.
5. Treating compatibility wrappers as proof of extraction.
6. Letting docs/testing/observability substitute for authority reduction.
7. Building online multi-agent behavior before single-owner runtime is finished.
8. Growing control-plane scope too early into a giant platform rewrite.

## Stop-The-Line Conditions
Stop immediately and surface the problem if:
1. a workstream step increases semantic authority in planner/executor/state or legacy mesh;
2. a proposed change adds a second semantic owner path;
3. a proposed fix depends on regex/phrase hardcoding in core for meaning;
4. a migration step makes compatibility views peer truths again;
5. a dirty worktree contains unexpected code changes you did not account for;
6. checks show post-owner mutation still exists but the block is being described as progress;
7. you are drifting into Workstream 5/6/7 topics before Workstream 1 invariants are established.

## Required Evidence Discipline
For each meaningful implementation family, capture:
- changed authority map
- exact files touched
- deterministic checks
- contract checks
- realistic/local behavior checks where required by `AGENTS.md`
- explicit statement of what authority was removed
- explicit residual debt left for the next block

Do not claim progress by narrative.
Progress must be visible in:
- code
- checks
- updated `STATE.md`
- and reduced old authority.

## Quality Bar
Do not artificially limit quality.

This means:
- do not choose the smallest patch if it preserves the wrong authority boundary
- do not stop at “good enough for tests” if semantic/control authority is still wrong
- do not shrink the problem by lowering the bar
- do not use budget/time as a reason to weaken the architecture target

Efficiency means:
- remove the highest-leverage wrong authority first
- keep workstream scope bounded
- avoid repeated re-analysis of settled questions
- avoid low-value side quests before the current workstream objective is achieved

## How To Report Status
Use top-level status only in this sense:
- `open`
- `done`
- `abandoned`

Do not describe the whole architecture program as `partial`.
Subtasks may be partial; the top-level program remains `open` until the program-level done criteria in `IMPLEMENTATION_PROGRAM.md` are met.

## Program-Level Done Criteria
The program is done only when all are true:
1. one semantic owner on the hot path
2. one canonical semantic state
3. one control path
4. planner/executor/state layers are not semantic co-owners
5. legacy compatibility mesh has no semantic authority
6. growth happens through governed registries/policies/context packs
7. durable execution is separated from semantic ownership
8. release decisions are backed by trace/eval/governance evidence

## Final Instruction
Do not ask “what architecture are we building?”
That is already fixed.

Do not ask “should we do more broad research first?”
That phase is already complete enough.

Do not ask “should we improve planner/executor/state a bit more first?”
No.

Start Workstream 1.
Remove semantic authority from the wrong layers.
Update the repo-backed evidence truthfully after each bounded family.
