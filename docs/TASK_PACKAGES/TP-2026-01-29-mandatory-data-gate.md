# Task Package: Mandatory Data Gate Extension

## Name / Goal
Extend Go/No-Go to enforce mandatory business data from the published knowledge pack (address/hours, services/prices, policies) and surface missing fields in Console.

## Invariant
- No change to runtime message/LLM flow.
- No DB migrations.
- Only onboarding gate + validation + UI visibility.

## Scope
- Use required fields from `knowledge_validation` for Go/No-Go gating.
- Add required policy sections to pack validation.
- Show missing pack fields in Console Go/No-Go step.

## Out of scope
- Policy gate runtime behavior.
- Provider gateway changes.
- Qdrant or data backfills.

## Touch-list
- truffles-api/app/services/onboarding_state.py
- truffles-api/app/services/knowledge_validation.py
- truffles-api/app/services/knowledge_registry_service.py
- truffles-api/tests/test_console_onboarding_state.py
- truffles-api/tests/test_knowledge_validation.py
- console-web/src/components/ProvisioningWizard.tsx
- docs/PROCESSES.md

## Plan
1) Add helper in `knowledge_validation` to compute missing required fields; extend required fields to include policy sections.
2) Use published pack in `onboarding_state` to add missing pack fields to Go/No-Go (and knowledge step if applicable).
3) Update Console labels and Go/No-Go readiness to include pack-missing fields.
4) Update tests for validation and onboarding.
5) Document enforced mandatory fields in processes.

## DoD
- Go/No-Go blocks when required pack fields are missing (address/hours/services/prices/policies).
- Console shows missing pack fields in Go/No-Go step.
- Tests pass: `pytest -q truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_knowledge_validation.py`.

## Checks
- pytest -q truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_knowledge_validation.py
- npm --prefix console-web run lint (if UI changed)

## Evidence
- Test logs + updated `STATE.md` entry (by Brain) with evidence.

## Rollback
- Revert commit.

## No-go
- Red CI.
- Any change to runtime message flow.

## Branch / Worktree / Base / Merge / Cleanup
- Branch: a1/mandatory-data-gate
- Worktree: /home/zhan/truffles-main/.worktrees/mandatory-data-gate-a1
- Base ref: origin/main
- Merge policy: merge commit (no rebase)
- Cleanup: remove worktree + branch after merge (Brain)

## Risks / Blockers
- Existing packs without required policy sections will fail validation until updated.
