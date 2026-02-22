# TP-2026-02-21-deploy-console-type-compat-a1

- Title/Goal: Unblock `main` deploy by fixing `console-web` build failures caused by OpenAPI schema key drift (`Company`/legacy names vs `Console*` names), while preserving runtime behavior.
- Canon refs: `STATE.md` (deploy blocker on `main`), `AGENTS.md` quality gates, `TECH.md` CI/deploy.
- Invariant: No functional regressions in Console flows; change scope is compile/type compatibility and request payload typing.
- Scope:
  - Fix TypeScript build blockers in `console-web`.
  - Restore backward-compatible typing for legacy OpenAPI keys used by existing UI code.
  - Keep API request shapes valid with current generated contracts.
- Out of scope:
  - Large UX refactors.
  - Backend behavior changes.
  - Re-generating OpenAPI contract sources outside current branch.
- Touch-list (allowed):
  - `console-web/src/types/api.generated.ts`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/app/insights/page.tsx`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/team/page.tsx`
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
- Plan:
  1. Reproduce deploy build failure locally with `npm --prefix console-web run build`.
  2. Add OpenAPI type compatibility aliases for legacy schema/operation keys.
  3. Fix strict type mismatches introduced by current contract fields (string booleans, record-string-never payloads, nullable fields).
  4. Re-run full `console-web` build until green.
  5. Commit and open PR with concise risk/next-step summary.
- DoD:
  - `npm --prefix console-web run build` passes locally.
  - No unrelated files modified.
  - PR is opened from worktree branch.
- Checks:
  - `npm --prefix console-web run build`
- Evidence:
  - Local successful build output from Next.js (compile + lint/type + static generation).
- Rollback:
  - Revert the single fix commit in PR.
- No-go:
  - Do not change backend semantics.
  - Do not bypass failing checks with `any`-only suppression in app code.
  - Do not introduce destructive git operations.
- Risks/Blockers:
  - Generated type aliases may diverge on next OpenAPI regeneration; follow-up is needed to formalize compat strategy in generator pipeline.
