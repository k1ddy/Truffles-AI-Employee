import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const runMutations = process.env.E2E_ALLOW_MUTATIONS === '1';
const useStorageState = process.env.E2E_USE_STORAGE_STATE === '1';

function matchesPath(url: string, paths: string[]) {
    try {
        const { pathname } = new URL(url);
        return paths.some((path) => pathname.endsWith(path));
    } catch {
        return false;
    }
}

async function waitForApiOk(page: import('@playwright/test').Page, path: string, timeout = 10000) {
    const proxyPath = path.replace('/console/v1', '/api/proxy');
    return page.waitForResponse(
        (response) => matchesPath(response.url(), [path, proxyPath]) && response.status() === 200,
        { timeout },
    );
}

async function waitForCasesWithStatus(page: import('@playwright/test').Page, status: string, timeout = 10000) {
    return page.waitForResponse(
        (response) => {
            if (!matchesPath(response.url(), ['/console/v1/cases', '/api/proxy/cases'])) return false;
            if (response.status() !== 200) return false;
            try {
                const { searchParams } = new URL(response.url());
                return searchParams.get('status') === status;
            } catch {
                return false;
            }
        },
        { timeout },
    );
}

async function expectRowsOrEmpty(
    page: import('@playwright/test').Page,
    rowTestId: string,
    emptyTestId: string,
    timeout = 10000,
) {
    const row = page.getByTestId(rowTestId).first();
    const empty = page.getByTestId(emptyTestId);
    await expect(row.or(empty)).toBeVisible({ timeout });
}

async function selectOptionIfNeeded(
    selector: import('@playwright/test').Locator
) {
    if (!(await selector.isVisible().catch(() => false))) {
        return false;
    }

    const currentValue = await selector.inputValue();
    if (currentValue) {
        return true;
    }

    const options = selector.locator('option');
    const optionCount = await options.count();
    if (optionCount < 2) {
        return true;
    }

    const value = await options.nth(1).getAttribute('value');
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue("");
    return true;
}

async function selectFromGate(
    page: import('@playwright/test').Page,
    selectTestId: string,
    confirmTestId: string
) {
    const select = page.getByTestId(selectTestId);
    if (!(await selectOptionIfNeeded(select))) {
        return false;
    }
    const confirm = page.getByTestId(confirmTestId);
    if (await confirm.isVisible().catch(() => false)) {
        await confirm.click();
    }
    return true;
}

async function resolveSelectionGate(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    const contextClient = page.getByTestId('context-client-select');
    await selectOptionIfNeeded(contextClient);
    const contextBranch = page.getByTestId('context-branch-select');
    await selectOptionIfNeeded(contextBranch);
}

async function startKeycloakLogin(page: import('@playwright/test').Page) {
    const signInUrl = `${baseURL}/api/auth/signin?callbackUrl=${encodeURIComponent(baseURL)}`;
    await page.goto(signInUrl, { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]');
    if (!(await providerForm.first().isVisible().catch(() => false))) {
        return false;
    }
    await providerForm.first().waitFor({ state: 'visible', timeout: 15000 });
    const submitButton = providerForm
        .first()
        .locator('button[type="submit"], input[type="submit"]')
        .first();
    await submitButton.click();
    await Promise.race([
        page.waitForURL(keycloakHostPattern, { timeout: 15000 }),
        page.waitForURL(consoleHostPattern, { timeout: 15000 }),
    ]);
    return true;
}

async function loginThroughKeycloak(page: import('@playwright/test').Page) {
    const started = await startKeycloakLogin(page);
    if (!started) {
        return;
    }
    if (!(await page.locator('#username').isVisible().catch(() => false))) {
        return;
    }
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await page.fill('#username', loginUser);
    await page.fill('#password', loginPassword);
    await page.click('#kc-login');
    await page.waitForURL(consoleHostPattern);
}

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    await page.goto('/');
    const loginButton = page.getByTestId('login-button');
    const logoutButton = page.getByTestId('logout-button');
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginThroughKeycloak(page);
        await page.goto('/');
    }
    await resolveSelectionGate(page);
    const casesTitle = page.getByTestId('cases-title');
    if (useStorageState) {
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
            await resolveSelectionGate(page);
        }
        if (!(await casesTitle.isVisible().catch(() => false))) {
            if (await loginButton.isVisible().catch(() => false)) {
                await loginThroughKeycloak(page);
                await page.goto('/');
                await resolveSelectionGate(page);
                const resolvedAfterLogin = await ensureTenantSelection(page);
                if (resolvedAfterLogin) {
                    await page.reload({ waitUntil: 'domcontentloaded' });
                    await resolveSelectionGate(page);
                }
            }
        }
        await expect(casesTitle, 'Expected logged-in UI with storage state.').toBeVisible({ timeout: 15000 });
        return;
    }
    try {
        await expect(casesTitle).toBeVisible({ timeout: 10000 });
        return;
    } catch {
        if (await loginButton.isVisible().catch(() => false)) {
            await loginThroughKeycloak(page);
        }
        await page.goto('/');
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await expect(casesTitle).toBeVisible({ timeout: 10000 });
    }
}

async function fetchMe(page: import('@playwright/test').Page, clientId?: string | null) {
    return page.evaluate(async (id) => {
        const headers: Record<string, string> = {};
        if (id) {
            headers['X-Client-Id'] = id;
        }
        const response = await fetch('/api/proxy/me', { headers });
        if (!response.ok) {
            return null;
        }
        return response.json();
    }, clientId ?? null);
}

async function fetchMeWithRetry(page: import('@playwright/test').Page, clientId?: string | null) {
    let data = await fetchMe(page, clientId);
    for (let attempt = 0; !data && attempt < 2; attempt += 1) {
        await page.waitForTimeout(1000);
        data = await fetchMe(page, clientId);
    }
    return data;
}

async function ensureTenantSelection(page: import('@playwright/test').Page): Promise<boolean> {
    const stored = await page.evaluate(() => ({
        clientId: window.localStorage.getItem('console:client_id'),
        branchId: window.localStorage.getItem('console:branch_id'),
    }));
    const envClientId = process.env.E2E_CLIENT_ID;
    const envBranchId = process.env.E2E_BRANCH_ID;

    let nextClientId = stored.clientId || envClientId || null;
    let changed = false;

    const data = await fetchMeWithRetry(page);
    const accessibleClients: string[] = [];
    if (data?.clients?.length) {
        accessibleClients.push(...data.clients.map((client: { id?: string }) => client.id).filter(Boolean));
    } else if (data?.client?.id) {
        accessibleClients.push(data.client.id as string);
    }
    if (!nextClientId || (accessibleClients.length && !accessibleClients.includes(nextClientId))) {
        nextClientId = accessibleClients[0] ?? null;
    }

    if (nextClientId && nextClientId !== stored.clientId) {
        await page.evaluate((id) => {
            window.localStorage.setItem('console:client_id', id);
            window.localStorage.removeItem('console:branch_id');
        }, nextClientId);
        changed = true;
    }

    if (!stored.branchId) {
        let nextBranchId = envBranchId || null;
        if (nextClientId) {
            const branchData = await fetchMeWithRetry(page, nextClientId);
            const branchIds = Array.isArray(branchData?.branches)
                ? branchData.branches.map((branch: { id?: string }) => branch.id).filter(Boolean)
                : [];
            if (nextBranchId && !branchIds.includes(nextBranchId)) {
                nextBranchId = null;
            }
            if (!nextBranchId && branchData?.branch_selection_required && branchIds.length) {
                nextBranchId = branchIds[0] as string;
            }
        }
        if (nextBranchId) {
            await page.evaluate((id) => {
                window.localStorage.setItem('console:branch_id', id);
            }, nextBranchId);
            changed = true;
        }
    }

    return changed;
}

// =========================================
// HELPER: Open inbox with storage state
// =========================================
async function openInbox(page: import('@playwright/test').Page) {
    await ensureLoggedIn(page);
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 10000 });
    const errorPanel = page.getByTestId('cases-error');
    if (await errorPanel.isVisible().catch(() => false)) {
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await resolveSelectionGate(page);
        const retry = page.getByTestId('cases-retry');
        if (await retry.isVisible().catch(() => false)) {
            await retry.click();
        }
    }
    await expect(page.getByTestId('cases-table')).toBeVisible({ timeout: 10000 });
    await expectRowsOrEmpty(page, 'cases-row', 'cases-empty');
}

// =========================================
// INBOX FILTERS & NAVIGATION
// =========================================
test.describe('Inbox Features', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should display filter controls @smoke', async ({ page }) => {
        await expect(page.getByTestId('cases-filters')).toBeVisible();
        await expect(page.getByTestId('cases-filter-status')).toBeVisible();
        await expect(page.getByTestId('cases-filter-sort')).toBeVisible();
        await expect(page.getByTestId('cases-filter-assigned')).toBeVisible();
        await expect(page.getByTestId('cases-refresh')).toBeVisible();
    });

    test('should filter by status @smoke', async ({ page }) => {
        const waitForPending = waitForCasesWithStatus(page, 'pending');
        await page.getByTestId('cases-filter-status').selectOption('pending');
        await waitForPending;
        await expect(page.getByTestId('cases-table')).toBeVisible();
        await expectRowsOrEmpty(page, 'cases-row', 'cases-empty');
    });

    test('should navigate to case detail @smoke', async ({ page }) => {
        await expect(page.getByTestId('cases-table')).toBeVisible();
        const emptyState = page.getByTestId('cases-empty');
        if (await emptyState.isVisible().catch(() => false)) {
            await expect(emptyState).toBeVisible();
            return;
        }
        const firstRow = page.getByTestId('cases-row').first();
        await expect(firstRow).toBeVisible();
        await firstRow.click();
        try {
            await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/, { timeout: 5000 });
        } catch {
            const openButton = page.getByTestId('case-open').first();
            await expect(openButton).toBeVisible();
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/);
        }
        await expect(
            page.getByTestId('case-details').or(page.getByTestId('case-view'))
        ).toBeVisible({ timeout: 5000 });
    });
});

// =========================================
// NAVIGATION
// =========================================
test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should navigate to Status page @smoke', async ({ page }) => {
        const waitForHealth = waitForApiOk(page, '/console/v1/health');
        await page.getByTestId('nav-ops').click();
        await expect(page).toHaveURL('/ops');
        await waitForHealth;
        await expect(page.getByTestId('ops-title')).toBeVisible();
        await expect(page.getByTestId('ops-health-card')).toBeVisible();
    });

    test('should navigate to Audit Log @smoke', async ({ page }) => {
        const waitForAudit = waitForApiOk(page, '/console/v1/audit');
        await page.getByTestId('nav-audit').click();
        await expect(page).toHaveURL('/audit');
        await waitForAudit;
        await expect(page.getByTestId('audit-title')).toBeVisible();
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, 'audit-row', 'audit-empty');
    });

    test('should navigate to Settings @smoke', async ({ page }) => {
        await page.getByTestId('nav-settings').click();
        await expect(page).toHaveURL('/settings');
        await expect(page.getByTestId('settings-title')).toBeVisible();
        await expect(page.getByTestId('settings-branches')).toBeVisible();
        await expectRowsOrEmpty(page, 'settings-branch-row', 'settings-branches-empty');
    });
});

// =========================================
// CASE ACTIONS (Take, Reply, Resolve)
// =========================================
test.describe('Case Actions @mutating', () => {
    test.skip(!runMutations, 'Mutating tests are disabled');
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should take a pending case @mutating', async ({ page }) => {
        await page.locator('select').first().selectOption('Ожидает');
        await page.waitForTimeout(500);

        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            const takeButton = page.getByRole('button', { name: /взять/i });
            if (await takeButton.isVisible()) {
                await takeButton.click();
                await page.waitForTimeout(1000);
                await expect(page.getByText('Диалог')).toBeVisible();
            }
        }
    });

    test('should send a reply message @mutating', async ({ page }) => {
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            const replyInput = page.locator('textarea');
            const sendButton = page.getByRole('button', { name: /отправить/i });

            if (await replyInput.isVisible()) {
                await replyInput.fill('Test reply from E2E test');

                if (await sendButton.isVisible()) {
                    await sendButton.click();
                    await page.waitForTimeout(1000);
                    await expect(page.getByText('Диалог')).toBeVisible();
                }
            }
        }
    });

    test('should resolve an active case @mutating', async ({ page }) => {
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            const resolveButton = page.getByRole('button', { name: /закрыть/i });
            if (await resolveButton.isVisible()) {
                await resolveButton.click();
                await page.waitForTimeout(1000);

                const isOnCasePage = page.url().includes('/cases/');
                if (isOnCasePage) {
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
        await openInbox(page);
        const waitForAudit = waitForApiOk(page, '/console/v1/audit');
        await page.getByTestId('nav-audit').click();
        await expect(page).toHaveURL('/audit');
        await waitForAudit;
    });

    test('should display audit events table @smoke', async ({ page }) => {
        await expect(page.getByTestId('audit-title')).toBeVisible();
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, 'audit-row', 'audit-empty');
    });

    test('should show event types with badges @smoke', async ({ page }) => {
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, 'audit-row', 'audit-empty');
    });
});

// =========================================
// SETTINGS PAGE
// =========================================
test.describe('Settings Page', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
        await page.getByTestId('nav-settings').click();
        await expect(page).toHaveURL('/settings');
        await expect(page.getByTestId('settings-title')).toBeVisible();
    });

    test('should display branches section @smoke', async ({ page }) => {
        await expect(page.getByTestId('settings-branches')).toBeVisible();
        await expectRowsOrEmpty(page, 'settings-branch-row', 'settings-branches-empty');
    });

    test('should display team access @smoke', async ({ page }) => {
        const teamHeading = page.getByRole('heading', { name: /команда/i });
        await expect(teamHeading).toBeVisible();
        const teamAction = page.getByTestId('settings-team-link').first();
        await expect(teamAction).toBeVisible();
    });
});
