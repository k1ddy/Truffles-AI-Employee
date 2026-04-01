Title/Goal
- Create one full zero-context execution prompt for the next agent so implementation can continue from the accepted target decision and implementation program without reopening broad architectural debate.

Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

Root cause (mandatory)
- Symptom
  - Even with target decision and execution program fixed in repo docs, a future zero-context agent could still restart broad analysis or drift into local fixes if not given one explicit operator prompt.
- Minimal reproduction
  - A new agent without chat history may read only fragments of the forensic corpus and fail to see which questions are already settled versus which workstream must start next.
- Evidence
  - The repo now has many final/forensic documents, but no single next-agent execution prompt tying them together.
- Five Whys
  1. Why is handoff still risky? Because the document system is now rich but spread across many files.
  2. Why does that matter? Because zero-context execution can reintroduce drift.
  3. Why would drift happen? Because some questions are now settled and others are implementation-only, but that boundary is not yet encoded as one prompt.
  4. Why is that dangerous? Because implementation could restart broad analysis instead of executing Workstream 1.
  5. Why fix it now? Because the repo is finally ready to hand off direct implementation against a fixed target decision.
- Root cause statement
  - The execution packet lacks a single operator-facing prompt that tells the next agent exactly what to read, what is already decided, what not to repeat, and what to implement first.
- Fix mechanism
  - Create one full next-agent execution prompt document and register it in the final forensic corpus.

Invariant
- No runtime behavior changes.
- No new architecture branches.
- The prompt must point to repo-backed truth, not replace it.

Scope
- Create one full prompt document for the next implementation agent.
- Register it in `INDEX`, `STRUCTURE`, `STATE`, and final synthesis.

Out of scope
- Starting implementation work.
- Reopening target architecture decisions.

Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-next-agent-full-prompt-a922.md`
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `STRUCTURE.md`
- `STATE.md`

Plan
1. Create one full execution prompt for the next agent.
2. Point the prompt at the accepted target and mandatory contracts.
3. Register the prompt in the forensic/final corpus.

DoD
- A single prompt document exists and is sufficient for a zero-context next agent to continue implementation.
- It names the accepted target, forbidden regressions, mandatory reading order, current workstream, and completion criteria.
- `INDEX`, `STRUCTURE`, `STATE`, and final synthesis mention the prompt truthfully.
- `git diff --check` passes.

Work mode (mandatory)
- forensic

Checks
- `git diff --check`
- `rg -n "NEXT_AGENT_FULL_PROMPT" docs/system_forensics/INDEX.md docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md STRUCTURE.md STATE.md`

Evidence
- New prompt doc
- Updated index/synthesis/state references
- Check outputs recorded in session response

Rollback
- Revert the docs-only commit that introduces the next-agent prompt.

No-go
- No vague motivational language in the prompt.
- No reopening of already accepted architecture questions.
- No contradictions with target decision or implementation program.

Risks/blockers
- The prompt can still be too broad if it does not force Workstream 1 as the next move.
- The prompt can still permit drift if it does not clearly separate settled decisions from remaining unknowns.

Residual architecture debt (mandatory)
- Current residuals accepted in this block
  - The prompt itself does not execute any implementation; it only improves zero-context continuity.
- Why not in this block
  - This is a handoff-quality block, not a code block.
- Risk if deferred
  - A future agent can still waste time reopening analysis instead of continuing the execution program.
- Linked follow-up Task Package(s)
  - The next implementation TP must start Workstream 1.
- Expiry/trigger to stop deferral
  - If a future agent starts implementation without using this prompt, the handoff failed.

Next-block contract (mandatory)
- Next block objective
  - Start Workstream 1 implementation against `SemanticDecisionV1` and the post-owner mutation guard.
- First deterministic check command
  - `rg -n "Workstream 1|SemanticDecisionV1|post-owner mutation" docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- Blocked-by conditions
  - The prompt doc is missing or not registered.
- Owner role for closure
  - Brain / Top Architect
