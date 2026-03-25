# DEC-2026-03-15 — Consultant Core Controlled Demolition

- Status: accepted
- Owner: Top Architect
- Date: 2026-03-15

## Decision

Truffles stops treating the current consultant firebreak lane as a path to final convergence.
From this point, the project adopts `controlled demolition` of the current consultant runtime core.

The project will:
- preserve reusable pack/capability/compiler assets
- freeze semantic growth in the legacy router core
- surface one executable source-of-truth map
- generate one minimal agent packet for every new agent
- move toward one semantic owner and one continuity owner
- remove semantic authority from proof/eval before any platform-level claim

## Why

The current system already mined the right architecture in `P1.6o79..P1.6o83`, but the mined truth is still documentary:
- semantic ownership is still partially split between policy docs, legacy router branches, continuity recovery paths, and proof/oracle tooling
- continuity truth still spans multiple live containers
- proof/eval still has the power to look like an authority instead of a black-box observer
- a fresh agent still needs too much narrative context to start correctly

That means the architecture is still vulnerable to agent amnesia, not just model quality.

## Final Architecture

The target runtime is:
1. Ingress
2. Pack/Capability Context Loader
3. Policy Core Planner
4. Boundary Validator
5. Capability Executor
6. Response Realizer
7. Dialog State Writer
8. Offline Proof/Eval

## Binding Rules

1. Semantic owner is only `PolicyDecision`.
2. Continuity owner is only `DialogState`.
3. Deterministic runtime may only validate, block, degrade, or request replan with explicit reason-code.
4. No runtime layer may silently rewrite:
   - `outcome`
   - `interaction_owner`
   - `interaction_target`
   - `interaction_relation`
   - `pending_question_contract`
5. Legacy router files are sunset files and may not receive new semantic branches without recorded waiver.
6. Proof/eval files are observers of runtime artifacts, not semantic authorities.
7. `demo_salon` is canary only, never platform proof.

## Governance Phase

Week 1 is governance-first, not runtime migration.
This DEC accepts that current runtime cutover is incomplete and requires the repo to become self-constraining before new migration work continues.

## Success Metrics

Progress is measured by reduction, not row closure theater:
- semantic authorities count
- continuity writers count
- legacy semantic files count
- proof semantic rewrite count
- demo-specific references in generic path count
- multi-pack acceptance pass count

## Rejected Path

The project explicitly rejects:
- continuing row-by-row closure as the main strategy
- growing `decision.py` while describing future architecture elsewhere
- using proof-lane progress as a proxy for runtime convergence
- claiming business-agnostic readiness from beauty-only evidence
