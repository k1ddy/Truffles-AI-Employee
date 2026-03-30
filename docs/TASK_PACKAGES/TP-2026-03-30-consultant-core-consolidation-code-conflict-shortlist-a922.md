# TP-2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922

- Title/Goal: Prioritize the remaining consultant-core code/test true-conflict files so manual resolution can start with the smallest high-value hotspot set.
- Canon refs: `STATE.md`; `STRUCTURE.md`; `docs/REPORTS/2026-03-30-consultant-core-consolidation-freeze-inventory-a922.md`
- Invariant: Continue only in the single consolidation worktree; no blind merge from dirty sources.
- Scope:
  - classify remaining code/test true-conflict files into `P0/P1/P2`
  - define the first manual-merge hotspot set
- Out of scope:
  - no file content merge yet
  - no behavior/runtime changes
- Touch-list:
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Plan:
  1. Pull remaining true-conflict files from the freeze inventory.
  2. Mark P0 hotspot files needed for product/practical continuation.
  3. Record the shortlist and next manual merge target.
- Work mode: forensic
- DoD:
  - shortlist exists with explicit P0/P1/P2 grouping
  - next manual merge target is named explicitly
- Checks:
  - `python3 - <<'PY'
from pathlib import Path
import json
obj = json.loads(Path('/home/zhan/consolidation_freeze/2026-03-30-consultant-core-consolidation-a922/inventory.json').read_text())
print(sum(1 for _,e in obj['paths'].items() if e['_meta']['classification']=='true-conflict'))
PY`
- Evidence:
  - `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922.md`
- Rollback:
  - remove the shortlist report and restore `STATE.md` / `STRUCTURE.md` from previous commit
- No-go:
  - no actual code merge in this block
- Risks/blockers:
  - file priority does not replace manual semantic diffing; each P0 file still needs path-by-path review
- Residual architecture debt (mandatory):
  - Current residuals accepted in this block: all code/test true-conflict files remain unresolved.
  - Why not in this block: this is the prioritization step only.
  - Risk if deferred: continuation work will restart conflict resolution in the wrong order.
  - Linked follow-up Task Package(s): next manual merge block for P0 hotspot files.
  - Expiry/trigger to stop deferral: before next product/runtime implementation block.
- Next-block contract (mandatory):
  - Next block objective: manually resolve the P0 hotspot files first (`ops/diagnose.py`, `prompts/llm_policy_core.md`, `booking.py`, `decision.py`, `info.py`, `intent_service.py`, and paired quality tests).
  - First deterministic check command: `sed -n '1,120p' docs/REPORTS/2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922.md`
  - Blocked-by conditions: missing source-of-truth choice per P0 file.
  - Owner role for closure: Brain / Top Architect.
