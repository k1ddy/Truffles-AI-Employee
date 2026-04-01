Title/Goal
- Convert the existing forensic corpus and external architecture research into a concrete execution program: one target decision, one implementation program, and four mandatory runtime contracts that future work can execute against.

Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md`
- external analysis summary supplied by user on `2026-03-27`

Root cause (mandatory)
- Symptom
  - The repo now contains substantial forensic evidence and external architecture recommendations, but there is still no canonical execution program or bounded contract set that translates those findings into a finite implementation sequence.
- Minimal reproduction
  - We can answer "what is wrong" and "what target architecture is best" but cannot yet answer "what exactly do we build first, second, third, and under which invariants" from one canonical document set.
- Evidence
  - `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md` maps active runtime/legacy authority but does not define the accepted target decision or workstream program.
  - `docs/system_forensics/final/RESEARCH_BRIEF.md` and the external research output define design space and recommendations, but not a repo-canonical execution program.
- Five Whys
  1. Why is work sequencing still unclear? Because the repo has evidence and recommendations but no contract-level execution packet.
  2. Why does that matter? Because implementation can drift back into local fixes without a finite workstream map.
  3. Why would that happen? Because future sessions may re-argue target architecture or start coding without agreed artifacts.
  4. Why is that not already prevented? Because the forensic and research phases ended before a target-decision/program layer was written.
  5. Why must this be corrected now? Because further implementation without this layer will repeat the same ambiguity that caused prior drift.
- Root cause statement
  - The architecture program lacks a canonical bridge from forensic/research evidence to execution: accepted target decision, bounded workstreams, and contract artifacts are not yet fixed in repo documents.
- Fix mechanism
  - Create a docs-only execution packet: `TARGET_DECISION.md`, `IMPLEMENTATION_PROGRAM.md`, and four contract docs (`SEMANTIC_DECISION_V1.md`, `BINDING_PLAN_V1.md`, `TURN_JOURNAL_V1.md`, `CONVERSATION_PROJECTION_V1.md`), then register them in the forensic/final corpus.

One web search (mandatory before implementation)
- Query
  - `site:learn.microsoft.com event sourcing pattern architecture`
- Date/time
  - `2026-03-27T20:45:00+05:00`
- Opened sources
  - `https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing`
- Source quality
  - Official Microsoft architecture guidance.
- What was found
  - Event sourcing is valuable for append-only auditability and materialized views, but it is a high-cost architectural choice that must stay tightly scoped and vocabulary-controlled.
- Reuse / integrate / build decision
  - `integrate`
- Reason
  - The execution packet should adopt append-only journal + projection as a bounded contract, not a sprawling event-everything dogma.
- Rejected options
  - Treating event sourcing as a blanket rewrite pattern for the entire system: rejected because it would inflate scope and complexity.

Invariant
- No runtime behavior changes.
- No new claims that exceed the current forensic/research evidence.
- The resulting packet must reduce ambiguity, not expand design space again.

Scope
- Create one target-decision document.
- Create one implementation-program document.
- Create four mandatory contract docs for the new runtime core.
- Register the new docs in `INDEX`, `STRUCTURE`, `STATE`, and the final synthesis source list.

Out of scope
- Coding the runtime extraction itself.
- Choosing specific infrastructure vendors.
- Closing any strategic architecture item.

Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-target-decision-and-execution-program-a922.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `STRUCTURE.md`
- `STATE.md`

Plan
1. Fix one canonical target decision from the existing forensic+research corpus.
2. Convert that decision into one bounded implementation program with ordered workstreams.
3. Specify the four mandatory runtime contracts that gate implementation.
4. Register the new packet in the forensic/final document system.

DoD
- The repo contains one accepted target decision with explicit accepted / not accepted / hardening-needed statements.
- The repo contains one bounded implementation program with finite workstreams, dependencies, and completion criteria.
- The repo contains four explicit contract docs that future implementation can reference without ambiguity.
- `INDEX`, `STRUCTURE`, `STATE`, and final synthesis point to the new packet truthfully.
- `git diff --check` passes.

Work mode (mandatory)
- forensic

Checks
- `git diff --check`
- `rg -n "TARGET_DECISION|IMPLEMENTATION_PROGRAM|SEMANTIC_DECISION_V1|BINDING_PLAN_V1|TURN_JOURNAL_V1|CONVERSATION_PROJECTION_V1" docs/system_forensics/INDEX.md docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md STRUCTURE.md STATE.md`

Evidence
- New docs under `docs/system_forensics/final/`
- Updated `docs/system_forensics/INDEX.md`
- Updated `STRUCTURE.md`
- Updated `STATE.md`
- Check outputs recorded in the session response

Rollback
- Revert the docs-only commit that introduces the execution packet.

No-go
- No new runtime design branches beyond the already selected target recommendation.
- No implementation-level promises that are unsupported by the forensic corpus.
- No reopening of already settled questions without explicit `UNKNOWN` justification.

Risks/blockers
- The contract docs can still be too abstract if they do not specify writer/reader laws and forbidden mutations clearly enough.
- The implementation program can become too broad if workstreams are not kept authority-based.

Residual architecture debt (mandatory)
- Current residuals accepted in this block
  - The repo will still not have code changes toward the target architecture; this block only fixes the execution packet.
  - Some design details will remain intentionally open until later contract refinement (`event vocabulary`, `policy precedence`, `legacy kill ordering`).
- Why not in this block
  - This block is about converting evidence into a canonical program, not starting implementation.
- Risk if deferred
  - Future sessions can still drift into local fixes or reopen target-architecture debates.
- Linked follow-up Task Package(s)
  - Next TP should start Workstream 1 from the new implementation program: semantic owner extraction.
- Expiry/trigger to stop deferral
  - If coding resumes without referencing these documents, the packet failed its purpose.

Next-block contract (mandatory)
- Next block objective
  - Start Workstream 1: extract `SemanticDecisionV1` as the only hot-path meaning owner and define the first post-owner mutation guard.
- First deterministic check command
  - `rg -n "SemanticDecisionV1|post-owner|mutation guard|BindingPlanV1" docs/system_forensics/final/TARGET_DECISION.md docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md docs/system_forensics/final/SEMANTIC_DECISION_V1.md docs/system_forensics/final/BINDING_PLAN_V1.md`
- Blocked-by conditions
  - The execution packet docs are missing or not registered in `STATE.md` / `STRUCTURE.md`.
- Owner role for closure
  - Brain / Top Architect
