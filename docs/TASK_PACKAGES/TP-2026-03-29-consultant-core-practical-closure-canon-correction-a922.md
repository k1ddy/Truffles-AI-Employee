# TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922

- Status: `done`
- Owner: `Brain/Architect`
- Date: `2026-03-29`

## Название/цель
Закрепить в каноне различие между structural/contract closeout и practical/product closure, чтобы следующие блоки закрывались только после полного human-semantic proof, family-level RCA и понятного end-to-end debug path.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260329-r25/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не переписывать историю так, будто `single semantic owner` опровергнут: текущее evidence этого не доказывает.
- Не откатывать structural/contract workstream closeout без точного evidence.
- Не объявлять product/practical `done` только по deterministic/structural pass.

## Scope
- Канонический correction block для closure model.
- Явное разделение `structural_complete`, `contract_complete`, `practical_behavior_complete`, `human_semantic_complete`.
- Обязательный full path RCA и запрет scenario-fitting.
- Обязательная mechanism-first интерпретация: surfaced family must be translated into `broken invariant + shared mechanism`, а не прямо в domain-labeled branch.
- Понятный debug SOP для replay/live dialog проблем.

## Out of scope
- Runtime fix families (`owner service grounding`, `check-booking live fallback`, `parking composition`).
- Изменение evaluator/oracle logic beyond documentation/process contract.
- Повторные quality runs.

## Touch-list
- `/home/zhan/truffles-main/AGENTS.md`
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/TECH.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `/home/zhan/truffles-main/docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `/home/zhan/truffles-main/docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `/home/zhan/truffles-main/docs/REPORTS/2026-03-29-consultant-core-practical-closure-correction-a922.md`
- `/home/zhan/truffles-main/docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com architectural fitness functions software`
- Date/time: `2026-03-29 Asia/Almaty`
- Opened source: `https://martinfowler.com/articles/fitness-functions-data-products.html`
- High-signal class: primary source / Thoughtworks-MF engineering article
- Found solution: use explicit automated governance/fitness layers, but treat them as necessary governance proof rather than sufficient product proof.
- Decision: `integrate` — keep structural fitness functions and add a second practical closure layer instead of replacing deterministic proof.
- Rejected variants:
  - `rewrite all previous closeout docs` — too noisy, loses historical truth.
  - `leave canon as-is and only add more tests` — repeats the same overclaim failure.

## Root cause (mandatory)
- Symptom:
  - Earlier `W1-W8 done` claim was interpreted as product-ready closure.
  - Practical replay `r25` remained `semantic_valid=false`, `human_semantic_valid=false` despite substantial structural work.
- Minimal reproduction:
  - Compare structural closeout claims against `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md` and `summary.json` for `r25`.
- Evidence:
  - `r25` failure families: owner-side booking service grounding, live check-booking fallback residue, parking composition regression.
  - Current evidence does not show a second semantic owner; it shows owner-quality, fallback, and fact-composition defects.
- Five Whys:
  1. Why did `done` overclaim happen? Because structural/deterministic pass was treated as practical closure.
  2. Why was that possible? Because canon did not define separate closure layers.
  3. Why did follow-up fixes drift toward scenario patching? Because full end-to-end path RCA was not made mandatory before code changes.
  4. Why was debugging too hard? Because artifact-reading order and layer classification were not formalized in one canonical SOP.
  5. Why did this survive review? Because human semantic audit existed operationally but was not yet a full closure contract across all claims.
- Root cause statement:
  - The canon lacked an explicit practical closure model and a mandatory full-path RCA/debug contract, so structural evidence was over-interpreted as product closure.
- Fix mechanism:
  - Publish a practical-closure addendum, sync AGENTS/TECH/runbook/STATE/STRUCTURE, and require family-level RCA + full human audit before any future product-ready claim.
  - Extend the same canon so surfaced domain families are treated as evidence labels only; each behavioral fix must repair one shared mechanism and state the broken invariant explicitly.

## Plan
1. Add a canonical practical-closure addendum that separates structural and product closure.
2. Update `AGENTS.md` with closure, RCA, and anti-scenario-patch gates.
3. Update `TECH.md` and `BOOKING_CONFIRM_VERIFY.md` with a readable full-path debug SOP.
4. Correct `STATE.md` and `STRUCTURE.md` to reflect current truth and new canon docs.
5. Sync `/home/zhan/AGENTS.md` with repo canon and run doc hygiene checks.

## DoD
- Canon explicitly states that structural closeout != product-ready closure.
- `single semantic owner` is not declared broken without exact evidence.
- Future behavioral blocks require full-path RCA and family-level fixes.
- Future behavioral blocks also require `broken invariant + shared mechanism` before implementation.
- Human semantic audit is mandatory for any product-quality claim.
- Debug SOP is written in one obvious place and linked from canon docs.
- Repo/root `AGENTS.md` are synchronized.

## Checks
- `cmp -s /home/zhan/AGENTS.md /home/zhan/truffles-main/AGENTS.md`
- `git -C /home/zhan/truffles-main diff --check`

## Evidence
- Updated canon docs listed in `Touch-list`
- `docs/REPORTS/2026-03-29-consultant-core-practical-closure-correction-a922.md`
- `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md`
- follow-up strengthening captured in `docs/PRACTICAL_CLOSURE_ADDENDUM.md`, `TECH.md`, and `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

## Rollback
- Revert the doc-only block as one bounded change if wording is wrong.
- Do not rollback runtime code or quality artifacts from this block.

## No-go
- Do not reopen runtime fixes before canon correction is merged.
- Do not claim `second semantic owner` without exact path evidence.
- Do not use scenario-turn labels as fix units; only failure families are allowed.
- Do not weaken acceptance language to protect previous `done` claims.

## Риски/блокеры
- Existing docs already contain newer human-audit rules; the correction must extend them without contradiction.
- `STATE.md` first-screen truth must be updated carefully so it stays factual and not narrative-only.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Runtime families remain open: owner service grounding, live check-booking fallback, parking composition.
### Why not in this block
- This block is doc/process correction only; mixing runtime fixes would obscure the canon change.
### Risk if deferred
- Without canon correction, further work is likely to repeat overclaims and scenario patching.
### Linked follow-up Task Package(s)
- Next TP will target `owner-side booking service grounding family` with full-path RCA.
### Expiry/trigger to stop deferral
- No further behavioral `done` claim is allowed until the next family TP follows the corrected canon.

## Next-block contract (mandatory)
### Next block objective
- Build exact live-path RCA for the `owner-side booking service grounding family` surfaced in `r25` and fix it at the owner layer, not by scenario patching.
### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "service_grounding or booking_opening"`
### Blocked-by conditions
- Canon correction must land first.
- `r25` artifacts and human audit must remain the active truth inputs.
### Owner role for closure
- `Brain/Architect`
