# 2026-03-17 Consultant Core Architecture Truth Audit (a922)

## Verdict Summary
- **FACT:** `Governance Lock` is done.
- **FACT:** `Runtime Contracts` are materialized.
- **FACT:** `Semantic Core Cutover` is partial.
- **FACT:** `Continuity Collapse` is partial.
- **FACT:** `Proof Path Excision` is partial.
- **FACT:** `Multi-Pack Proof` is not started.
- **Inference from repo evidence:** the current new-core scaffold should be kept, not fully deleted.
- **Inference from repo evidence:** bounded rework may still be needed later, but there is not enough evidence right now to justify deleting the new-core scaffold wholesale.
- **Recommendation:** continue only under stricter truth accounting: no percentage-based progress claims, no new implementation block before using the authority-deletion ledger below, and no continuation of continuity micro-slices.
- **Next recommended track:** boundary-owner audit, unless a new bounded-rework verdict is triggered by later evidence.

## Master-Block Truth Table
| Master block | Status | Factual basis | Remaining gap |
| --- | --- | --- | --- |
| Governance Lock | `done` | guards, packet generation, architecture checks are in repo and green | none at this block level |
| Runtime Contracts | `done` | four runtime contracts exist in `contracts/runtime/` and are exercised by `truffles-api/tests/test_consultant_core_runtime_contracts.py` | broader runtime migration still uses them only partially |
| Semantic Core Cutover | `partial` | many bounded safe semantic families have moved out of frozen `decision.py` into new core | semantic center still remains legacy-heavy in `prompts/llm_policy_core.md` and `truffles-api/app/routers/webhook/decision.py` |
| Continuity Collapse | `partial` | many continuity writers moved into `truffles-api/app/core/dialog_state_service.py`; Block F completed expected-reply/question-contract sync | direct pending-resume authority remains in frozen `truffles-api/app/routers/webhook/pending.py`; broader reset/state-restore seams remain |
| Proof Path Excision | `partial` | current canon states several proof-only helper families are no longer the only owners | broader scenario rewrite authority and narrower proof-only observers still remain |
| Multi-Pack Proof | `not started` | no repo evidence of platform-level closure on `beauty`, `clinic_or_dental`, `generic_service` | full block still open |

## Authority Deletion Ledger
| Track | Real deletion already proved | Surviving authority |
| --- | --- | --- |
| Semantic | many bounded safe fact/collect/smalltalk/handoff/booking-prompt families no longer require frozen `decision.py` on their safe paths | richer semantic routing and the main policy center still live in legacy |
| Continuity | expected-reply/question-contract state sync now owned in `DialogStateService`; many session-memory and payload writers already delegate there | direct pending-resume snapshot/restore remains in frozen `pending.py`; broader reset/state-restore seams remain |
| Boundary | typed contracts and bounded builders exist in `boundary_validator.py` / `turn_executor.py` | broader boundary authoring still remains mixed with `reasoning_core.py` and legacy behavior |
| Proof | some proof-only helper ownership has been excised from being the sole authority | broader scenario rewrite authority still remains |
| Pack-agnostic runtime | no factual closure | salon/demo coupling still not removed as a program-level fact |
| Multi-pack acceptance | no factual closure | no closure artifact across required pack profiles |

## Old-Architecture Reproduction Checklist
| Risk | Verdict | Basis |
| --- | --- | --- |
| Semantic ownership still split | `yes, still present` | semantic center remains partially in legacy router + prompt core |
| Multiple continuity writers still exist | `yes, still present` | continuity is improved but not converged; `pending.py` remains a frozen authority |
| Boundary mixed with semantic/orchestration | `yes, still present` | current canon itself says broader boundary ownership remains mixed |
| Phrase/keyword hardcode driving new core | `not proved as dominant current failure` | guards exist and program forbids bridge growth, but this must keep being watched |
| Demo/domain coupling leaking into generic core | `still unresolved at program level` | neutral runtime block has not been closed |
| New core merely duplicates old authority without retiring it | `partially mitigated, not fully gone` | many bounded seams were actually retired; main legacy authority still survives in key areas |

## Behavior Evidence Gap Map
| Area | Deterministic evidence | Realism / broader behavior evidence |
| --- | --- | --- |
| Governance / guards | strong | not applicable |
| Bounded semantic cutovers | strong for targeted families | still incomplete as a full-program realism closure |
| Continuity cutovers | strong for targeted bounded families | still incomplete as a whole-program behavior proof |
| Boundary cutovers | partial deterministic evidence | broader behavior evidence still incomplete |
| Proof / multi-pack | insufficient for closure | insufficient for closure |

## Rewrite / No-Rewrite Verdict By Subsystem
| Subsystem | Verdict | Reason |
| --- | --- | --- |
| `truffles-api/app/core/turn_planner.py` path | `keep` | real bounded semantic deletions already proved |
| `truffles-api/app/core/dialog_state_service.py` path | `keep` | real continuity ownership consolidation already proved |
| `truffles-api/app/core/boundary_validator.py` and `truffles-api/app/core/turn_executor.py` scaffold | `keep, audit further` | scaffold exists and some bounded ownership moved, but broader boundary truth is still incomplete |
| current audit/canon/guard layer | `keep` | this is the strongest part of the program and prevents obvious fake progress |
| full new-core architecture as a whole | `do not delete wholesale` | repo evidence does not justify total rebuild; too many bounded deletions are already real |
| possible bounded rework later | `possible` | if later audit shows a new-core slice preserves old authority shape without real deletion, bounded rework is justified |

## Rewrite Thresholds
If any future block proves one of the following, bounded rework should be opened immediately:
- a new-core slice adds a wrapper but leaves old authority effectively live for the same family
- a continuity contract regains multiple live writers without an explicit convergence path
- boundary code in new core starts substituting semantic ownership rather than validating/blocking/degrading contractually
- new core starts accumulating phrase-hardcode families as the main way to control business meaning

## Decision
- **Recommended decision now:** continue with the current new-core scaffold.
- **Do not** delete the new architecture wholesale now.
- **Do** keep using stop-the-line audits when the next owner track becomes ambiguous.
- **Do** use this report instead of percentages when discussing remaining work.

## Next Step
- Author and run `boundary-owner audit` as the next implementation-planning block, unless a new bounded-rework trigger appears first.
