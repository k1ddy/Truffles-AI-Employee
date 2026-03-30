# Consultant-Core Consolidation Doc Conflict Resolution

## Scope

Resolved the low-risk canon/doc conflicts inside the single consolidation worktree without touching consultant-core code conflicts.

## Source-of-Truth Decisions

- `STATE.md`: keep consolidation version rooted in consultant-core governance line and explicit consolidation truth entry.
- `STRUCTURE.md`: keep consolidation version rooted in consultant-core governance line and add consolidation reports/TP rows there.
- `TECH.md`: take `practical-closure` version as the newer practical operations source.
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`: take `practical-closure` version.
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`: take `practical-closure` version.
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922.md`: take `practical-closure` version.
- `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`: take `governance-lock` version.
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`: take `governance-lock` version.

## Remaining Manual Resolution

- `STATE.md` still needs later manual semantic merge against `practical-closure` if we decide to inline more practical truth than the current consolidation entry.
- `STRUCTURE.md` still needs later manual semantic merge if we decide to import more practical-closure indexing content than the current rows.
- Remaining unresolved non-doc inventory after this step is still the consultant-core code/test conflict set from the freeze inventory.

## Next Step

Build a code/test conflict shortlist and resolve only the consultant-core continuation files inside the consolidation worktree.
