# Wave 5 — Owner/Admin Acceptance Lane (a500)

Date
- 2026-02-20

Goal
- Close owner/admin acceptance ambiguity by adding a dedicated CI lane with explicit credentials contract, independent from generic/platform-admin smoke.

Changes
- Updated `.github/workflows/ci.yml`:
  - added mandatory job `console-e2e-owner-admin-live` for `console_web` changes;
  - lane uses live console URL and runs owner/admin smoke spec:
    - `npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --no-deps --reporter=list`;
  - lane fails hard when owner/admin credentials are absent (`CONSOLE_OWNER_E2E_USERNAME`, `CONSOLE_OWNER_E2E_PASSWORD`);
  - `build-push` now waits for owner/admin lane result.
- Updated runbook `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`:
  - documented mandatory CI lane, required secrets, command, and fail policy.
- Updated `STATE.md`:
  - recorded Wave 4 merge fact (`PR #772`);
  - replaced old owner/admin acceptance block with Wave 5 lane implementation fact + explicit remaining runtime evidence gap.

Checks
- `python3` workflow guard snippet (`env_file.write(...\\n)` policy) -> pass.
- `npm --prefix console-web run lint -- --file e2e/owner-admin-business.spec.ts --file e2e/auth.setup.ts --file e2e/login.spec.ts --file playwright.config.ts` -> pass.
- `npm --prefix console-web run build` -> pass.
- `PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --no-deps --list` (from `console-web/`) -> pass (`3 tests listed`).

Outcome
- Owner/admin lane is now codified as a separate CI contract and no longer depends on generic smoke interpretation.
- Deploy gate on main includes owner/admin acceptance lane result.

Open gap
- Runtime closure requires first green CI run of `console-e2e-owner-admin-live` with valid owner/admin secrets on GitHub Actions.
