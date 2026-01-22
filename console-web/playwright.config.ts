import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const runWebServer = process.env.PLAYWRIGHT_WEB_SERVER !== '0';
const storageState = '.auth/console.json';

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL,
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'setup',
            testMatch: /.*\.setup\.ts/,
        },
        {
            name: 'chromium-login',
            testMatch: /.*login\.spec\.ts/,
            use: { ...devices['Desktop Chrome'] },
        },
        {
            name: 'chromium',
            testIgnore: /.*login\.spec\.ts/,
            dependencies: ['setup'],
            use: { ...devices['Desktop Chrome'], storageState },
        },
    ],
    webServer: runWebServer
        ? {
              command: 'npm run dev -- -H 0.0.0.0 -p 3000',
              url: baseURL,
              reuseExistingServer: !process.env.CI,
          }
        : undefined,
});
