# Consultant Core Research Output Schema

Status: `open`
Purpose: define the exact format expected from external research so the result is directly usable for architecture decisions.

## Response Contract
The returned research must be structured under the following sections.

## 1. Executive Verdict
Required fields:
- `recommended_target_architecture`: short name
- `recommended_agenticity_level`: e.g. bounded single-agent, bounded multi-agent, hybrid
- `recommended_first_extraction_block`: one sentence
- `migration_feasibility`: `high|medium|low`
- `rewrite_required`: `no|partial|yes`
- `summary`: short paragraph

## 2. Current-System Interpretation Check
Purpose: prove the researchers understood the repo-backed problem correctly.

Required fields:
- `active_runtime_spine`
- `legacy_compatibility_mesh`
- `top_failure_classes`
- `what_is_already_known`
- `what_remains_design_choice`

This section must map back to our forensic corpus rather than invent a different problem.

## 3. Architecture Option Set
Provide `2-4` options.

For each option include:
- `name`
- `runtime_plane_design`
- `control_plane_design`
- `offline_improvement_plane_design`
- `agent_topology`
- `canonical_state_model`
- `tool/capability_model`
- `governance_model`
- `observability/eval_model`
- `migration_shape`
- `strengths`
- `weaknesses`
- `main_risks`
- `why_this_option_might_fit_consultant_core`

## 4. Comparative Decision Matrix
Provide one matrix comparing all options.

Required comparison dimensions:
- semantic ownership purity
- canonical state purity
- control-path simplicity
- manifest/registry-centered extensibility
- governance strength
- operational observability
- proof/eval strength
- migration realism
- implementation complexity
- risk of recreating current failure classes
- long-term scalability across domains/tools/tenants/channels/models

## 5. Recommended Target Architecture
This must be one explicit recommendation.

Required fields:
- `why_recommended`
- `runtime_plane`
- `control_plane`
- `offline_improvement_plane`
- `semantic_owner_boundary`
- `canonical_state_boundary`
- `tool_binding_boundary`
- `degrade/handoff_boundary`
- `governance_and_registry_model`
- `how_growth_happens_without_core_branching`
- `where_multi_agent_is_allowed`
- `where_multi_agent_is_forbidden`
- `how_reasoning_artifacts_are_exposed_without_raw_cot_dependency`

## 6. Expansion Matrix
Show how the recommended architecture handles each growth axis.

Rows required:
- add new domain
- add new capability/tool
- add new tenant/branch/regulatory policy
- change model vendor or routing
- add new channel/UI
- add new specialist agent
- add new safety/policy regime
- add new proof/eval regime
- scale load/cost envelope
- add new human workflow/escalation flow

For each row include:
- `what_changes`
- `what_does_not_change`
- `which plane absorbs the change`
- `whether runtime-core changes are required`
- `main risks`

## 7. Migration Strategy
The response must include a realistic migration path from the current system.

Required fields:
- `migration_strategy_name`
- `why_this_migration_strategy`
- `prerequisites`
- `phase_sequence`
- `rollback_points`
- `shadow_or_canary_strategy`
- `evidence_needed_per_phase`
- `how_to_prevent_dual_semantic_authority_during_cutover`
- `what_can_be_demoted_early`
- `what_must_remain_until_late_cutover`

## 8. First Extraction Block
This section is mandatory.

Required fields:
- `objective`
- `why_this_is_the_first_block`
- `files_or_subsystems_primarily_affected`
- `architectural_leverage`
- `acceptance_criteria`
- `rollback_strategy`
- `how_we_know_it_reduces_old-authority_not_just_moves_code`

## 9. Salvage / Adapter / Delete Matrix
Required categories:
- `salvage_as_core_candidate`
- `keep_as_adapter_temporarily`
- `keep_as_shadow_only`
- `delete_when_unblocked`
- `unknown_requires_more_validation`

Each item should include:
- `component`
- `category`
- `reason`
- `blocking_dependency_if_any`

## 10. Governance and Control Plane Proposal
This section is mandatory.

Required fields:
- `registry_objects`
- `ownership_and_lifecycle_model`
- `identity_and_authz_model`
- `policy_enforcement_points`
- `approval_and_release_flow`
- `inventory_and_discovery_model`
- `anti-sprawl_mechanisms`

## 11. Observability / Proof / Agent Ops Proposal
Required fields:
- `required_turn_trace_artifacts`
- `required_metrics`
- `eval_dataset_strategy`
- `lm_judge_or_equivalent_role`
- `human_feedback_loop`
- `go_no_go_rules`
- `release_safety_model`
- `offline_simulation_or_agent_gym_role`

## 12. Rejected Alternatives
At least `3` rejected options or patterns.

For each include:
- `name`
- `why_it_is_tempting`
- `why_it_should_be_rejected_here`
- `which failure class it risks reintroducing`

## 13. Residual Unknowns
Required fields:
- `unknown`
- `why_it_remains_unknown`
- `how_to_resolve`
- `whether_it_blocks_first_extraction_block`

## 14. Source Discipline
The research must cite:
- which of our internal docs were used,
- which external modern sources/patterns/frameworks were used,
- and which claims are based on direct evidence versus architectural judgment.

## Minimum Quality Bar
The research output is not acceptable if it:
- only repeats our own documents,
- gives only one architecture option,
- ignores control-plane governance,
- ignores migration,
- depends on opaque multi-agent sprawl,
- or fails to name a first extraction block.
