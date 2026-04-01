# 2026-03-30 Consultant-Core Machine-Readable Research Companion (a922)

## Scope
Add the machine-readable companion for the external-research corpus so outside researchers can consume stable registries and answer a structured questionnaire without source access.

## Outcome
- Status: `done`
- Practical truth: unchanged (`r35f` remains current truth)
- Product closure: still `open`
- Runtime behavior: unchanged

## What changed
1. Published machine-readable packet artifacts under `docs/system_forensics/`:
   - `artifact_index.json`
   - `module_inventory.json`
   - `failure_family_registry.json`
   - `runtime_path_registry.json`
   - `glossary.json`
   - `external_review_questionnaire.json`
2. Published `docs/system_forensics/EXTERNAL_REVIEW_QUESTIONNAIRE.md` as the human-readable reviewer response contract.
3. Updated the root packet docs so the machine-readable companion is explicit, not hidden.
4. Synced canon so this remains a doc-only external-research block, not a runtime implementation block.

## Governing conclusion
The consultant-core corpus is no longer only readable prose. It now has a stable machine-readable companion and a structured review questionnaire, which reduces the chance that outside reviewers or future internal implementers rebuild partial context from narrative documents alone.

## Checks
- JSON companion parse check -> `external_machine_companion_ok`
- packet presence check -> `external_review_packet_ok`
- `git diff --check`
