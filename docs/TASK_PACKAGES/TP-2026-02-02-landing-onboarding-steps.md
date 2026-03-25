- Title/goal: Add a simple onboarding steps section to landing to communicate easy setup.
- Canon refs: AGENTS.md; STATE.md (update with evidence); N/A CA_ID
- Invariant: No change to existing pricing/copy semantics; keep current visual language.
- Scope: Add a 3-step onboarding section + wire into landing; rebuild and redeploy.
- Out of scope: Any other copy changes, pricing, analytics, backend.
- Touch-list: /home/zhan/infrastructure/frontend/src/components/landing/*; /home/zhan/infrastructure/frontend/src/pages/Index.tsx; docs/SESSIONS/*; docs/SESSION_INDEX.md; STATE.md.
- Plan:
  1) Create onboarding steps component with short, plain-language steps.
  2) Insert section into landing page flow.
  3) Build and redeploy landing container.
  4) Capture evidence logs and update STATE.md + session log.
- DoD: Onboarding steps visible on prod; anchor navigation intact; evidence recorded.
- Checks: Build, docker deploy, curl homepage 200.
- Evidence: Build log + docker up log + curl log (files under /tmp), recorded in STATE.md by Top Architect.
- Rollback: Remove the new section and redeploy previous image.
- No-go: Do not introduce jargon or complex claims; avoid layout refactor.
- Risks/blockers: None.
