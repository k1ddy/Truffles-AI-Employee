import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const baseURLPort = new URL(baseURL).port || (baseURL.startsWith('https://') ? '443' : '80');
const runWebServer = process.env.PLAYWRIGHT_WEB_SERVER !== '0';
const useStorageState = process.env.E2E_USE_STORAGE_STATE === '1';
const deterministicAuthEnabled = process.env.E2E_DETERMINISTIC_AUTH !== '0';
const storageStatePath = useStorageState ? 'e2e/.auth/state.json' : '.auth/console.json';
// Deterministic auth lane stubs session/cookies and should not depend on Keycloak setup project.
const needsSetupProject = !useStorageState && !deterministicAuthEnabled;

const projects: NonNullable<ReturnType<typeof defineConfig>['projects']> = [];

if (needsSetupProject) {
    projects.push({
        name: 'setup',
        testMatch: /.*\.setup\.ts/,
    });
}

projects.push({
    name: 'chromium-login',
    testMatch: /.*login\.spec\.ts/,
    use: { ...devices['Desktop Chrome'] },
});

projects.push({
    name: 'chromium',
    testIgnore: /.*login\.spec\.ts/,
    ...(needsSetupProject ? { dependencies: ['setup'] } : {}),
    use: {
        ...devices['Desktop Chrome'],
        ...(deterministicAuthEnabled ? {} : { storageState: storageStatePath }),
    },
});

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'html',
    globalSetup: useStorageState ? './e2e/global-setup' : undefined,
    use: {
        baseURL,
        trace: 'on-first-retry',
    },
    projects,
    webServer: runWebServer
        ? {
              command: `npm run dev -- -H 0.0.0.0 -p ${baseURLPort}`,
              url: baseURL,
              env: {
                  ...process.env,
                  NEXTAUTH_URL: baseURL,
                  NEXT_PUBLIC_E2E_BYPASS_AUTH: process.env.NEXT_PUBLIC_E2E_BYPASS_AUTH ?? '1',
              },
              reuseExistingServer: process.env.PLAYWRIGHT_REUSE_SERVER === '1' && !process.env.CI,
          }
        : undefined,
});
