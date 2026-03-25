# TP-2026-03-25 Consultant Core Behavioral Proof Lock A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-BEHAVIORAL-PROOF-LOCK-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `f6eb0fc9`
- `UNLOCKS`: truthful behavioral proof for the semantic-unification chain, or one exact blocker family with current acceptance evidence

## Название/цель
Не менять runtime-архитектуру. Довести closure до behavioral proof через current `L0/L1/L2 -> L3` chain на текущем worktree runtime. Выход блока только два: `behaviorally proven with artifacts` или `blocked with current evidence`.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-evidence-closure-a922.md`

## FACT pre-check (before implementation)
- Current head is `f6eb0fc9`; semantic-unification code path is already committed and clean.
- `curl -fsS http://127.0.0.1:18190/admin/health` is green for demo-salon runtime safety; one generic-branch minimum-data gap remains out of scope.
- The old seed-19 artifact `/tmp/booking_quality/a922-go2f-seed19/summary.json` is not canonical proof because `semantic_valid=false`.
- No fresh non-acceptance green multi-seed evidence exists inside the last 24 hours for required seeds `7`, `19`, `42`; acceptance `lock` is therefore not yet admissible without rebuilding `go_to_full` evidence.

## One web search (mandatory before implementation)
- **Query (exact):** `pytest junitxml official docs`
- **Date/time (local):** `2026-03-25 23:27:00 +0500`
- **Why this query is precise:** the proof block needs one current official reference for the `--junitxml` evidence artifact that feeds `PG1` without inventing a custom report format.
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/_modules/_pytest/junitxml.html`
- **Decision:** reuse native `pytest --junitxml` output for `L1` evidence and keep the rest of the proof workflow in-repo (`docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, `scripts/llm_quality_guarded.sh`, `scripts/quality_chain_controller.sh`).
- **Rejected options:** custom JUnit emitter scripts, ad-hoc unguarded acceptance runs, replay against a semantically invalid baseline, and more runtime refactor before current proof is attempted.

## Root cause (mandatory)
- **Symptom:** semantic-unification is architecturally closed, but there is still no current behavioral proof artifact on the guarded acceptance lane.
- **Minimal reproduction:** produce fresh `L1` JUnit evidence, fresh green non-acceptance `L2` summaries for seeds `7`, `19`, `42`, assemble `PG0..PG6`, then run the guarded acceptance chain on the current runtime fingerprint.
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-25-consultant-core-policy-core-live-manual-closure-a922.md`
  - `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `scripts/quality_chain_controller.sh`
- **Five Whys:**
  1. Why is behavioral closure still open? Because no current guarded acceptance artifact exists for the current fingerprint.
  2. Why is manual closure insufficient? Because local manual dialogs do not satisfy acceptance-chain governance.
  3. Why can’t the old seed-19 artifact be reused? Because it is semantically invalid and therefore cannot be baseline/proof evidence.
  4. Why not keep coding? Because the next missing fact is proof, not another semantic refactor.
  5. Why rebuild `L1/L2` first? Because `go_to_full` gate fail-closes acceptance `lock` without fresh deterministic and green multi-seed dev evidence.
- **Root cause statement:** the remaining gap is missing current behavioral evidence and `go_to_full` readiness, not missing semantic-unification code.
- **Fix mechanism:** rebuild fresh `L1` and `L2` evidence, materialize `PG0..PG6`, then run one guarded acceptance promotion chain and publish the first truthful stop condition.

## Reuse-first plan (mandatory)
- **Internal reuse:** `scripts/llm_quality_guarded.sh`, `scripts/quality_chain_controller.sh`, `ops/diagnose.py`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`, existing mandatory pytest suites.
- **External reuse:** none.
- **Decision:** `reuse -> integrate -> prove`.
- **Why not build new tooling:** the guarded workflow already enforces chain order, preflight, manual audit, scenario governance, and acceptance integrity.

## Invariant
- No runtime code edits in this block unless a new blocker family is proven and a new TP is opened.
- No hidden reruns: one explicit `L0/L1` package, one explicit `L2` seed set (`7/19/42`), then one guarded `L3` promotion chain that stops at the first non-canonical step or after `full` closure.
- No threshold, oracle, or chain-gate weakening.
- Demo-salon behavioral proof only; no generic-pack or platform-wide closure claim.

## Scope
- rerun the mandatory local guard and product suites on the current candidate
- materialize one fresh JUnit evidence pack for `PG1`
- produce fresh green non-acceptance `L2` summaries for seeds `7`, `19`, `42`
- assemble a current `PG0..PG6` checklist
- enter guarded acceptance `lock` and continue the chain only if the current step stays canonical
- publish exact proof or blocker facts

## Out of scope
- new runtime refactor
- generic-pack minimum-data remediation
- transport-only cleanup
- acceptance reruns after the first truthful stop condition

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-behavioral-proof-lock-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `/tmp/booking_quality/l1-a922-behavioral-proof-20260325/pytest-junit.xml`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260325/*`
- `/tmp/booking_quality/a922-l2-proof-seed19-20260325/*`
- `/tmp/booking_quality/a922-l2-proof-seed42-20260325/*`
- `/tmp/booking_quality/pg_checklist-a922-behavioral-proof-20260325.json`
- `/tmp/booking_quality/booking-lock-20260325-a922-semantic-proof/*`
- subsequent chain artifacts only if `next_command` is emitted from the same acceptance chain

## Plan (1..N)
1. Re-verify runtime health and rerun mandatory `L0/L1` checks on the current candidate.
2. Produce one fresh `L1` JUnit evidence pack for the semantic-unification closure family.
3. Produce fresh audited green `L2` dev summaries for seeds `7`, `19`, and `42`.
4. Assemble `PG0..PG6` from the fresh `L1/L2` evidence.
5. Run guarded acceptance `lock`; if canonical, execute exactly the emitted `next_command` and continue until the chain stops or reaches `full`.
6. Audit the stopping artifact and publish `behaviorally proven` or `blocked` with exact blocker family.

## DoD
- fresh `L1` JUnit exists and contains the mapped target tests as passed
- fresh audited `L2` summaries for seeds `7`, `19`, `42` exist with `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`, `quality_lane_effective=dev`
- one current `PG0..PG6` checklist exists and is accepted by the chain controller
- guarded acceptance chain is entered exactly once and stops truthfully at the first non-canonical step or after full closure
- canon docs record the result without hidden retries or runtime code edits

## Work mode (mandatory)
- `closure`

## Execution profile (mandatory for non-doc blocks)
- `TP mode:` `implementation`
- `Doc touch budget (files):` `2000`
- `Code dominance:` `off`
- `Override token:` `none`

## Checks
- `curl -fsS http://127.0.0.1:18190/admin/health`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py::test_consultant_runtime_closure_proof_preserves_canonical_semantic_and_question_contracts truffles-api/tests/test_consultant_core_runtime_contracts.py::test_turn_executor_builds_typed_explicit_handoff_owner_cutover_artifact truffles-api/tests/test_message_endpoint.py::test_policy_collect_interrupt_arbitration_keeps_hours_interrupt_without_active_slot_question_owner truffles-api/tests/test_message_endpoint.py::test_set_expected_reply_context_records_canonical_pending_question_contract_in_evidence --junitxml=/tmp/booking_quality/l1-a922-behavioral-proof-20260325/pytest-junit.xml`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18190 --client-slug demo_salon --count 10 --seed 7 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-l2-proof-seed7-20260325 --run-id a922-l2-proof-seed7-20260325 --history-max 20 --fail-on-thresholds --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-l2-proof-seed7-20260325 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18190 --client-slug demo_salon --count 10 --seed 19 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-l2-proof-seed19-20260325 --run-id a922-l2-proof-seed19-20260325 --history-max 20 --fail-on-thresholds --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-l2-proof-seed19-20260325 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18190 --client-slug demo_salon --count 10 --seed 42 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-l2-proof-seed42-20260325 --run-id a922-l2-proof-seed42-20260325 --history-max 20 --fail-on-thresholds --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-l2-proof-seed42-20260325 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from datetime import datetime, timezone
payload = {
    "go_to_full": {
        "PG0": {"status": "pass"},
        "PG1": {"status": "pass"},
        "PG2": {"status": "pass"},
        "PG3": {"status": "pass"},
        "PG4": {"status": "pass"},
        "PG5": {"status": "pass"},
        "PG6": {"status": "pass"},
        "root_cause_statement": "The remaining gap after semantic-unification was missing current behavioral proof: canonical semantic state was structurally aligned, but no fresh governed L1/L2 evidence existed to admit the acceptance chain on the current runtime fingerprint.",
        "defect_mapping": [
            {
                "defect_class": "canonical_semantic_closure_contract",
                "target_test": "truffles-api/tests/test_consultant_core_runtime_contracts.py::test_consultant_runtime_closure_proof_preserves_canonical_semantic_and_question_contracts",
                "gate": "PG1",
                "owner": "a922"
            },
            {
                "defect_class": "explicit_handoff_trace_contract",
                "target_test": "truffles-api/tests/test_consultant_core_runtime_contracts.py::test_turn_executor_builds_typed_explicit_handoff_owner_cutover_artifact",
                "gate": "PG1",
                "owner": "a922"
            },
            {
                "defect_class": "booking_interrupt_hours_owner_contract",
                "target_test": "truffles-api/tests/test_message_endpoint.py::test_policy_collect_interrupt_arbitration_keeps_hours_interrupt_without_active_slot_question_owner",
                "gate": "PG1",
                "owner": "a922"
            },
            {
                "defect_class": "canonical_pending_question_evidence_contract",
                "target_test": "truffles-api/tests/test_message_endpoint.py::test_set_expected_reply_context_records_canonical_pending_question_contract_in_evidence",
                "gate": "PG1",
                "owner": "a922"
            }
        ],
        "l1_evidence": {
            "junit_xml_path": "/tmp/booking_quality/l1-a922-behavioral-proof-20260325/pytest-junit.xml",
            "recorded_at": datetime.now(timezone.utc).isoformat()
        },
        "l2_evidence": {
            "summary_path": "/tmp/booking_quality/a922-l2-proof-seed19-20260325/summary.json",
            "run_id": "a922-l2-proof-seed19-20260325",
            "recorded_at": datetime.now(timezone.utc).isoformat()
        },
        "multi_seed_evidence": {
            "required_seeds": [7, 19, 42],
            "summaries": [
                {"seed": 7, "summary_path": "/tmp/booking_quality/a922-l2-proof-seed7-20260325/summary.json", "recorded_at": datetime.now(timezone.utc).isoformat()},
                {"seed": 19, "summary_path": "/tmp/booking_quality/a922-l2-proof-seed19-20260325/summary.json", "recorded_at": datetime.now(timezone.utc).isoformat()},
                {"seed": 42, "summary_path": "/tmp/booking_quality/a922-l2-proof-seed42-20260325/summary.json", "recorded_at": datetime.now(timezone.utc).isoformat()},
            ]
        },
        "evidence_freshness_hours": 24
    }
}
with open('/tmp/booking_quality/pg_checklist-a922-behavioral-proof-20260325.json', 'w', encoding='utf-8') as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
PY`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-20260325-a922-semantic-proof --pg-checklist /tmp/booking_quality/pg_checklist-a922-behavioral-proof-20260325.json --allow-pending-previous -- --base-url http://127.0.0.1:18190 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260325-a922-semantic-proof --status done --strict-artifacts`
- `scripts/quality_chain_controller.sh status --chain-id "$(python3 - <<'PY'\nimport json\nfrom pathlib import Path\nsummary = Path('/tmp/booking_quality/booking-lock-20260325-a922-semantic-proof/summary.json')\nif summary.exists():\n    payload = json.loads(summary.read_text())\n    quality = payload.get('quality_status') or {}\n    print((quality.get('chain_id') or payload.get('run_id') or '').strip())\nPY\n)"`
- `execute exactly the emitted next_command if and only if the current chain status remains canonical and unblocked`

## Evidence
- local check outputs from this block
- `/tmp/booking_quality/l1-a922-behavioral-proof-20260325/pytest-junit.xml`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260325/{summary.json,brief.md,manual_audit.json}`
- `/tmp/booking_quality/a922-l2-proof-seed19-20260325/{summary.json,brief.md,manual_audit.json}`
- `/tmp/booking_quality/a922-l2-proof-seed42-20260325/{summary.json,brief.md,manual_audit.json}`
- `/tmp/booking_quality/pg_checklist-a922-behavioral-proof-20260325.json`
- acceptance chain artifacts beginning at `/tmp/booking_quality/booking-lock-20260325-a922-semantic-proof/`
- canon doc updates with the exact stop condition

## Token / run budget (mandatory for expensive suites)
- `Max full runs:` `1` guarded behavioral-proof chain entry on the current fingerprint
- `Cheap prerequisite budget:` `1` fresh `L1` JUnit pack plus `3` audited `L2` seed runs (`7`, `19`, `42`)
- `Stop condition:` stop immediately on the first failed mandatory deterministic suite, the first non-green required `L2` seed, rejected `PG0..PG6`, or the first non-canonical acceptance chain step
- `Escalation path:` only Brain / Top Architect can authorize another expensive proof chain after a blocked result

## Release safety (mandatory for non-doc changes)
- `Strategy:` local proof-only validation on the current worktree runtime; no runtime rollout or behavior change is introduced in this block
- `Go/no-go signals:` all mandatory `L0/L1` checks pass, all required `L2` seeds are green and audited, `PG0..PG6` is accepted, and the guarded chain either reaches canonical closure or stops with one exact blocker family
- `Rollback:` no runtime rollback path is needed; if proof blocks, keep code unchanged and publish the blocker artifact
- `Post-release monitoring window:` not applicable in this block because no rollout is performed

## Rollback
- No runtime rollback in this block.
- If any `L2` seed or acceptance step fails, publish the blocker and stop the chain.

## No-go
- no runtime code edits inside this proof block
- no replay against semantically invalid baseline
- no acceptance `lock` without fresh `PG0..PG6`
- no second chain start under a different run-id after the first truthful stop condition
- no product-wide proof claim beyond demo-salon acceptance evidence

## Risks/Blockers
- one of the required `L2` seeds may still fail semantically, which blocks `L3`
- the chain controller may reject the checklist if `L1/L2` freshness or target-test mapping is wrong
- acceptance `lock` may still surface a new blocker family on the current runtime fingerprint

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: generic-pack minimum-data debt and compatibility transport fields remain outside demo-salon proof scope.
- `Why not in this block`: this block proves current behavior; it does not expand architecture scope.
- `Risk if deferred`: broader platform-wide proof claims remain invalid even if demo-salon acceptance goes green.
- `Linked follow-up Task Package(s)`: open only if the chain stops on a new blocker family or if broader open-world proof is requested.
- `Expiry/trigger to stop deferral`: any claim that the whole platform is behaviorally proven beyond the demo-salon closure family.

## Next-block contract (mandatory)
- `Next block objective`: either close behavioral proof from the accepted chain artifact or open exactly one blocker TP from the first non-canonical step.
- `First deterministic check command`: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260325-a922-semantic-proof --status done --strict-artifacts`
- `Blocked-by conditions`: failed `L1`, any non-green required `L2` seed, rejected `PG0..PG6`, or non-canonical acceptance step
- `Owner role for closure`: Brain / Top Architect
