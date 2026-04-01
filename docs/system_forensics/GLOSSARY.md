# Consultant Core Forensics Glossary

## Purpose
Give external researchers one stable vocabulary for the consultant-core corpus.

## Terms
- `semantic owner`: the component allowed to decide user-turn meaning (`intent`, requested outcome, main slots, fact/tool grounding)
- `boundary`: deterministic layer that validates, blocks, or degrades without inventing new business meaning
- `degrade`: explicit fallback path with reason code and trace evidence
- `truth carrier`: any artifact that stores or transports meaning-bearing state
- `failure family`: repeatable cluster of bad turns sharing one broken invariant and one root cause
- `shared mechanism`: the reusable architectural unit that should be repaired instead of patching one scenario
- `FACT`: product outcome where the bot answers from packs or trusted data
- `COLLECT`: product outcome where the bot gathers missing booking/contact/preference state
- `HANDOFF`: product outcome where the bot transparently transfers to a human workflow
- `interaction architecture`: contracts governing per-turn meaning, pending question continuity, and semantic state
- `fact architecture`: contracts governing fact selection, composition, rendering, and emitted fact scope
- `pack`: tenant/domain data layer that should supply truth as data, not code branching
- `executive packet`: top-level self-contained docs for outside readers
- `evidence archive`: deeper `files/`, `ledgers/`, and `final/` docs backing executive claims
- `anti-repeat rule`: an explicit rule added because earlier truthful analysis still allowed bad implementations
- `machine-readable companion`: JSON registries and questionnaire artifacts that make the packet consumable without manual inventory rebuilding
- `external review questionnaire`: structured response contract for outside architecture reviewers
- `primary deep audit`: fresh first-hand system research that must exist before the external packet is treated as a final outside handoff
