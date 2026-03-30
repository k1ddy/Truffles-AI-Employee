# TP-2026-03-30-consultant-core-consolidation-doc-conflict-resolution-a922

- Title/Goal: Resolve the low-risk canon/doc conflicts in the consolidation worktree by explicit source-of-truth selection, without touching consultant-core code/test conflicts yet.
- Canon refs: `STATE.md`; `STRUCTURE.md`; `TECH.md`; `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- Invariant: Keep one continuation worktree; preserve all consultant-core code artifacts already imported; do not attempt code conflict merge in this block.
- Scope:
  - resolve low-risk docs by explicit source pick
  - record remaining conflict scope for code/tests
- Out of scope:
  - no code conflict resolution
  - no runtime behavior changes
- Touch-list:
  - `TECH.md`
  - `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922.md`
  - `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
  - `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-doc-conflict-resolution-a922.md`
- Plan:
  1. Pick source of truth for each low-risk doc conflict.
  2. Copy the selected versions into the consolidation worktree.
  3. Record remaining unresolved code/test conflict scope.
- Work mode: implementation
- DoD:
  - selected doc conflicts are resolved in the consolidation worktree
  - a report exists with explicit source picks
  - remaining code/test conflict scope is named explicitly
- Checks:
  - `git status --short` in the consolidation worktree
  - manual file-source verification against selected worktree
- Evidence:
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-doc-conflict-resolution-a922.md`
- Rollback:
  - restore these doc files from the previous consolidation commit
- No-go:
  - no blind merge
  - no code/test conflict resolution in this block
- Risks/blockers:
  - `STATE.md`/`STRUCTURE.md` remain partial semantic merges until a later pass
- Residual architecture debt (mandatory):
  - Current residuals accepted in this block: code/test conflict set still unresolved; `STATE.md`/`STRUCTURE.md` not fully semantically merged with practical-closure.
  - Why not in this block: this block is only for low-risk doc unification.
  - Risk if deferred: truth/index drift if later conflicts are resolved without updating canon docs.
  - Linked follow-up Task Package(s): upcoming code/test conflict shortlist block.
  - Expiry/trigger to stop deferral: before any new consultant-core runtime implementation work.
- Next-block contract (mandatory):
  - Next block objective: shortlist and resolve consultant-core code/test conflicts in owner/runtime/practical-quality hotspots first.
  - First deterministic check command: `python3 - <<'PY'
from pathlib import Path
import json
obj = json.loads(Path('/home/zhan/consolidation_freeze/2026-03-30-consultant-core-consolidation-a922/inventory.json').read_text())
print(sum(1 for _,e in obj['paths'].items() if e['_meta']['classification']=='true-conflict'))
PY`
  - Blocked-by conditions: missing conflict shortlist or unclear source-of-truth for a hotspot file.
  - Owner role for closure: Brain / Top Architect.
