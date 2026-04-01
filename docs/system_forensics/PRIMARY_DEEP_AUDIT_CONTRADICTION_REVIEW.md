# Primary Deep Audit Contradiction Review

Status: `completed`
Reviewed packet status after this pass: `reviewed_not_ready_for_external_handoff`
Current packet status after the follow-up packet-closure block: `ready_for_external_handoff`

## Purpose
Resolve the explicit contradictions between the fresh seven-track primary deep audit and the older archive-layer synthesis/program docs.

## Governing precedence after this review
For current packet status and outside-handoff decisions, use this order:
1. `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
2. the seven fresh deep-audit docs
3. `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
4. `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
5. the root-level executive packet
6. archive evidence under `docs/system_forensics/final/`, `files/`, and `ledgers/`

Archive docs remain evidence and target-hypothesis material.
They are not current go-signals by themselves.

## Resolved contradictions

### C1. Archive synthesis said broad analysis was finished and direct implementation could proceed
Older claim:
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md` said the repo contained enough continuity for direct implementation and that broad analysis was no longer the next useful work.

Fresh deep-audit finding:
- the order-of-work was corrected precisely because packet structure had outpaced fresh first-hand analysis;
- the packet required a new primary deep audit before outside handoff or architecture implementation could restart safely.

Resolution:
- keep `SYSTEM_FINAL_ANALYSIS.md` as archive synthesis;
- demote its old implementation go-signal language;
- current go/no-go authority now lives in the deep-audit program plus this contradiction review and the readiness review.

### C2. Archive program docs looked more authoritative than the new scaffold
Older claim:
- `docs/system_forensics/final/TARGET_DECISION.md` and `IMPLEMENTATION_PROGRAM.md` were written as if target direction and workstream order were already frozen enough for implementation.

Fresh deep-audit finding:
- the new packet exists specifically because earlier truthful docs were still too fragmented and too easy to misuse;
- the fresh audit confirmed a stronger asymmetry on the fact side than the archive program had foregrounded.

Resolution:
- treat the archived target/program docs as strong internal hypotheses, not as the final outside-reader contract;
- root-level `TARGET_ARCHITECTURE.md` now describes the direction as the current leading hypothesis, not an unchallengeable finished decision.

### C3. Archive target freeze conflicted with the new external-review mission
Older claim:
- `docs/system_forensics/final/TARGET_DECISION.md` froze `Governed Semantic Kernel + Durable Action Plane` as the accepted target architecture.

Fresh deep-audit finding:
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md` still correctly asks outside researchers to validate or replace the current target architecture if needed.

Resolution:
- keep the broad target direction as the current leading internal hypothesis;
- explicitly allow outside reviewers to challenge it;
- do not present `final/TARGET_DECISION.md` as the unchallengeable answer for external researchers.

### C4. Archive first-extraction order conflicted with the newly exposed fact-side asymmetry
Older claim:
- archive program docs emphasized `SemanticDecisionV1 + BindingGatewayV1` as the first extraction block.

Fresh deep-audit finding:
- the fresh deep audit shows that interaction-side artifacts are materially ahead of fact-side architecture;
- current practical residue and architecture asymmetry both point to the missing fact-side executable contract.

Resolution:
- archive first-extraction ordering is no longer binding on the current packet;
- after outside-readiness blockers close, the first implementation candidate remains `fact architecture contract materialization`, unless outside review replaces that ordering with a stronger repo-backed plan.

### C5. Archived prompts still instructed work in obsolete worktrees and implementation mode
Older claim:
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md` still told the next agent to work in an older governance-lock worktree and continue implementation immediately.
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md` still looked like a ready-to-send external packet prompt.

Fresh deep-audit finding:
- the only valid continuation worktree is the consolidation worktree;
- runtime architecture implementation is blocked while the outside packet is still not ready.

Resolution:
- both prompts are now explicitly marked archive-only;
- they cannot be used as current starting material.

## Claims retained with narrower meaning
The contradiction review does not delete every older conclusion.
These archive conclusions still survive as narrowed working hypotheses:
1. one semantic owner / one canonical semantic state / one control path remain the right target invariants
2. `Governed Semantic Kernel + Durable Action Plane` remains the strongest current internal direction, but it is still challengeable
3. semantic strangler / phased authority removal / no big-bang rewrite remains the right migration posture
4. typed contract artifacts remain strategically important, but they are not by themselves proof that packet readiness is closed

## Archive disposition after this review
| Archive doc | New status | How to use it now |
| --- | --- | --- |
| `final/SYSTEM_FINAL_ANALYSIS.md` | archive synthesis, not current go-signal | use as deep evidence and historical synthesis only |
| `final/RESEARCH_BRIEF.md` | archive research contract | use as challenge brief behind the current packet |
| `final/TARGET_DECISION.md` | archived target hypothesis | use as internal leading hypothesis, not as outside-reader freeze |
| `final/IMPLEMENTATION_PROGRAM.md` | archive-only implementation hypothesis | do not restart runtime work from it directly |
| `final/NEXT_AGENT_FULL_PROMPT.md` | obsolete operational prompt | do not use as current starting brief |
| `final/EXTERNAL_RESEARCH_PROMPT.md` | archived external prompt | do not send until the packet-readiness blockers are closed |

## Result
The corpus no longer has a silent contradiction about whether analysis is still required.
The fresh deep audit wins.
The archive remains valuable, but only as archive evidence and challenge material.
The remaining self-contained packet gaps were later closed by the root-level contract summaries and end-to-end walkthrough.
