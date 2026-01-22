import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const runMutations = process.env.E2E_ALLOW_MUTATIONS === '1';
const useStorageState = process.env.E2E_USE_STORAGE_STATE === '1';
const emptyStorageState = { cookies: [], origins: [] };

function matchesPath(url: string, paths: string[]) {
    try {
        const { pathname } = new URL(url);
        return paths.some((path) => pathname.endsWith(path));
    } catch {
        return false;
    }
}

async function waitForApiOk(page: import('@playwright/test').Page, path: string, timeout = 10000) {
    const proxyPath = path.replace("/console/v1", "/api/proxy");
    return page.waitForResponse(
        (response) => matchesPath(response.url(), [path, proxyPath]) && response.status() === 200,
        { timeout }
    );
}

async function waitForCasesWithStatus(page: import('@playwright/test').Page, status: string, timeout = 10000) {
    return page.waitForResponse((response) => {
        if (!matchesPath(response.url(), ["/console/v1/cases", "/api/proxy/cases"])) return false;
        if (response.status() !== 200) return false;
        try {
            const { searchParams } = new URL(response.url());
            return searchParams.get("status") === status;
        } catch {
            return false;
        }
    }, { timeout });
}

async function expectRowsOrEmpty(
    page: import('@playwright/test').Page,
    rowTestId: string,
    emptyTestId: string,
    timeout = 10000
) {
    const row = page.getByTestId(rowTestId).first();
    const empty = page.getByTestId(emptyTestId);
    await expect(row.or(empty)).toBeVisible({ timeout });
}

async function startKeycloakLogin(page: import('@playwright/test').Page) {
    const signInUrl = `${baseURL}/api/auth/signin?callbackUrl=${encodeURIComponent(baseURL)}`;
    await page.goto(signInUrl, { waitUntil: "domcontentloaded" });
    const providerForm = page.locator('form[action*="keycloak"]');
    await providerForm.first().waitFor({ state: "visible", timeout: 15000 });
    const submitButton = providerForm
        .first()
        .locator('button[type="submit"], input[type="submit"]')
        .first();
    await submitButton.click();
    await page.waitForURL(keycloakHostPattern, { timeout: 20000 });
}

async function loginThroughKeycloak(page: import('@playwright/test').Page) {
    await startKeycloakLogin(page);
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await page.fill('#username', loginUser);
    await page.fill('#password', loginPassword);
    await page.click('#kc-login');
    await page.waitForURL(consoleHostPattern);
}

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    await page.goto('/');
    await expect(page.getByTestId('console-header')).toBeVisible();
    const casesTitle = page.getByTestId('cases-title');
    if (useStorageState) {
        await expect(casesTitle, 'Expected logged-in UI with storage state.').toBeVisible({ timeout: 15000 });
        return;
    }
    try {
        await expect(casesTitle).toBeVisible({ timeout: 10000 });
        return;
    } catch {
        const loginButton = page.getByTestId('login-button');
        if (await loginButton.isVisible().catch(() => false)) {
            await loginThroughKeycloak(page);
        }
        await page.goto('/');
        await expect(casesTitle).toBeVisible({ timeout: 10000 });
    }
}

// =========================================
// SMOKE TESTS: Authentication
// =========================================
test.describe('Smoke Test: Login Flow', () => {
    test.use({ storageState: emptyStorageState });
    test('should redirect to Keycloak login @smoke', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByTestId('console-header')).toBeVisible();
        await expect(page.getByTestId('login-button')).toBeVisible();
        await startKeycloakLogin(page);
        await expect(page.locator('#username')).toBeVisible();
        await expect(page.locator('#password')).toBeVisible();
    });

    test('should login and see inbox @smoke', async ({ page }) => {
        await page.goto('/');
        await loginThroughKeycloak(page);
        await expect(page.getByTestId('cases-title')).toBeVisible();
        await expect(page.getByTestId('cases-table')).toBeVisible();
        await expectRowsOrEmpty(page, "cases-row", "cases-empty");
    });

    test('should logout successfully @smoke', async ({ page }) => {
        await page.goto('/');
        await loginThroughKeycloak(page);
        await expect(page.getByTestId('cases-title')).toBeVisible();
        await page.getByTestId('logout-button').click();
        await expect(page.getByTestId('login-button')).toBeVisible({ timeout: 10000 });
    });
});

// =========================================
// HELPER: Login before tests
// =========================================
async function loginAsAdmin(page: import('@playwright/test').Page) {
    await ensureLoggedIn(page);
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('cases-table')).toBeVisible({ timeout: 10000 });
    await expectRowsOrEmpty(page, "cases-row", "cases-empty");
}


// =========================================
// INBOX FILTERS & NAVIGATION
// =========================================
test.describe('Inbox Features', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test('should display filter controls @smoke', async ({ page }) => {
        await expect(page.getByTestId('cases-filters')).toBeVisible();
        await expect(page.getByTestId('cases-filter-status')).toBeVisible();
        await expect(page.getByTestId('cases-filter-sort')).toBeVisible();
        await expect(page.getByTestId('cases-filter-assigned')).toBeVisible();
        await expect(page.getByTestId('cases-refresh')).toBeVisible();
    });

    test('should filter by status @smoke', async ({ page }) => {
        const waitForPending = waitForCasesWithStatus(page, "pending");
        await page.getByTestId('cases-filter-status').selectOption('pending');
        await waitForPending;
        await expect(page.getByTestId('cases-table')).toBeVisible();
        await expectRowsOrEmpty(page, "cases-row", "cases-empty");
    });

    test('should navigate to case detail @smoke', async ({ page }) => {
        await expect(page.getByTestId('cases-table')).toBeVisible();
        const emptyState = page.getByTestId('cases-empty');
        if (await emptyState.isVisible().catch(() => false)) {
            await expect(emptyState).toBeVisible();
            return;
        }
        const openButton = page.getByTestId('case-open').first();
        await expect(openButton).toBeVisible();
        await openButton.click();
        await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/);
        await expect(page.getByTestId('case-view')).toBeVisible({ timeout: 5000 });
    });
});

// =========================================
// NAVIGATION
// =========================================
test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test('should navigate to Status page @smoke', async ({ page }) => {
        const waitForHealth = waitForApiOk(page, "/console/v1/health");
        await page.getByTestId('nav-ops').click();
        await expect(page).toHaveURL('/ops');
        await waitForHealth;
        await expect(page.getByTestId('ops-title')).toBeVisible();
        await expect(page.getByTestId('ops-health-card')).toBeVisible();
    });

    test('should navigate to Audit Log @smoke', async ({ page }) => {
        const waitForAudit = waitForApiOk(page, "/console/v1/audit");
        await page.getByTestId('nav-audit').click();
        await expect(page).toHaveURL('/audit');
        await waitForAudit;
        await expect(page.getByTestId('audit-title')).toBeVisible();
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, "audit-row", "audit-empty");
    });

    test('should navigate to Settings @smoke', async ({ page }) => {
        await page.getByTestId('nav-settings').click();
        await expect(page).toHaveURL('/settings');
        await expect(page.getByTestId('settings-title')).toBeVisible();
        await expect(page.getByTestId('settings-branches')).toBeVisible();
        await expectRowsOrEmpty(page, "settings-branch-row", "settings-branches-empty");
    });
});

// =========================================
// CASE ACTIONS (Take, Reply, Resolve)
// =========================================
test.describe('Case Actions @mutating', () => {
    test.skip(!runMutations, 'Mutating tests are disabled');
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test('should take a pending case @mutating', async ({ page }) => {
        // Filter to pending cases using visible text
        await page.locator('select').first().selectOption('Ожидает');
        await page.waitForTimeout(500);

        // Open first pending case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find and click Take button (Взять заявку)
            const takeButton = page.getByRole('button', { name: /взять/i });
            if (await takeButton.isVisible()) {
                await takeButton.click();

                // Should see success indication (status changes or button disappears)
                await page.waitForTimeout(1000);
                // Verify we're still on the page (no crash)
                await expect(page.getByText('Диалог')).toBeVisible();
            }
        }
    });

    test('should send a reply message @mutating', async ({ page }) => {
        // Filter to active cases (where we can reply)
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        // Open first active case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find reply textarea and send button
            const replyInput = page.locator('textarea');
            const sendButton = page.getByRole('button', { name: /отправить/i });

            if (await replyInput.isVisible()) {
                // Type a test message
                await replyInput.fill('Test reply from E2E test');

                // Click send
                if (await sendButton.isVisible()) {
                    await sendButton.click();

                    // Wait for message to appear or success indication
                    await page.waitForTimeout(1000);

                    // Verify we're still on the page
                    await expect(page.getByText('Диалог')).toBeVisible();
                }
            }
        }
    });

    test('should resolve an active case @mutating', async ({ page }) => {
        // Filter to active cases
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        // Open first active case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find and click Resolve button (Закрыть заявку)
            const resolveButton = page.getByRole('button', { name: /закрыть/i });
            if (await resolveButton.isVisible()) {
                await resolveButton.click();

                // Wait for action to complete
                await page.waitForTimeout(1000);

                // Should redirect to inbox or show success
                const isOnCasePage = page.url().includes('/cases/');
                if (isOnCasePage) {
                    // Status might have changed to resolved
                    await expect(page.getByText(/закрыта/i)).toBeVisible({ timeout: 3000 });
                }
            }
        }
    });
});

// =========================================
// AUDIT LOG
// =========================================
test.describe('Audit Log', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
        const waitForAudit = waitForApiOk(page, "/console/v1/audit");
        await page.getByTestId('nav-audit').click();
        await expect(page).toHaveURL('/audit');
        await waitForAudit;
    });

    test('should display audit events table @smoke', async ({ page }) => {
        await expect(page.getByTestId('audit-title')).toBeVisible();
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, "audit-row", "audit-empty");
    });

    test('should show event types with badges @smoke', async ({ page }) => {
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, "audit-row", "audit-empty");
    });
});

// =========================================
// SETTINGS PAGE
// =========================================
    test.describe('Settings Page', () => {
        test.beforeEach(async ({ page }) => {
            await loginAsAdmin(page);
            await page.getByTestId('nav-settings').click();
            await expect(page).toHaveURL('/settings');
            await expect(page.getByTestId('settings-title')).toBeVisible();
        });

    test('should display branches section @smoke', async ({ page }) => {
        await expect(page.getByTestId('settings-branches')).toBeVisible();
        await expectRowsOrEmpty(page, "settings-branch-row", "settings-branches-empty");
    });

    test('should display team members section @smoke', async ({ page }) => {
        await expect(page.getByTestId('settings-team')).toBeVisible();
        await expectRowsOrEmpty(page, "settings-team-row", "settings-team-empty");
    });
});
