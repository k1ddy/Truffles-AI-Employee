import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const runWebServer = process.env.PLAYWRIGHT_WEB_SERVER !== '0';
const useStorageState = process.env.E2E_USE_STORAGE_STATE === '1';
const storageStatePath = useStorageState ? 'e2e/.auth/state.json' : '.auth/console.json';

const projects = [] as ReturnType<typeof defineConfig>['projects'];

if (!useStorageState) {
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
    ...(useStorageState ? {} : { dependencies: ['setup'] }),
    use: { ...devices['Desktop Chrome'], storageState: storageStatePath },
});

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
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
              command: 'npm run dev -- -H 0.0.0.0 -p 3000',
              url: baseURL,
              reuseExistingServer: !process.env.CI,
          }
        : undefined,
});
