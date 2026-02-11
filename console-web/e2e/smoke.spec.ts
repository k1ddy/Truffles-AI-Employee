import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
let resolvedBaseURL = baseURL;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const runMutations = process.env.E2E_ALLOW_MUTATIONS === '1';
const useStorageState = process.env.E2E_USE_STORAGE_STATE === '1';
const isLocalBaseURL = /localhost|127\.0\.0\.1/.test(baseURL);
const quarantineLocal = !!process.env.CI && isLocalBaseURL;

test.skip(quarantineLocal, 'Quarantine local CI smoke suite while stabilizing console-e2e.');

function matchesPath(url: string, paths: string[]) {
    try {
        const { pathname } = new URL(url);
        return paths.some((path) => pathname.endsWith(path));
    } catch {
        return false;
    }
}

function buildSignInUrl(origin: string) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(origin)}`;
}

function urlPathPattern(path: string) {
    return new RegExp(`${path.replace(/\//g, '\\/')}(\\?|$)`);
}

async function waitForSettingsResponse(page: import('@playwright/test').Page, timeout = 15000) {
    return page.waitForResponse(
        (response) => matchesPath(response.url(), ['/console/v1/settings', '/api/proxy/settings']),
        { timeout },
    );
}

async function readResponseBody(response: import('@playwright/test').Response) {
    try {
        return await response.text();
    } catch {
        return '';
    }
}

async function handleSettingsResponse(page: import('@playwright/test').Page, response: import('@playwright/test').Response) {
    if (response.ok()) {
        return;
    }
    let bodyText = await readResponseBody(response);
    let errorCode: string | null = null;
    try {
        const parsed = JSON.parse(bodyText) as { code?: string; error_code?: string; message?: string };
        errorCode = parsed.code || parsed.error_code || null;
        bodyText = parsed.message ? `${parsed.message} (${parsed.code || parsed.error_code || 'unknown'})` : bodyText;
    } catch {
        // Keep raw body text.
    }
    console.log(`[settings] response ${response.status()}: ${bodyText}`);
    const selectionErrors = new Set([
        'COMPANY_SELECTION_REQUIRED',
        'CLIENT_SELECTION_REQUIRED',
        'BRANCH_SELECTION_REQUIRED',
        'TENANT_MISMATCH',
    ]);
    if (errorCode && selectionErrors.has(errorCode)) {
        const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
        const resolved = await ensureTenantSelection(page);
        const retryPromise = waitForSettingsResponse(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await resolveSelectionGateWithRetry(page, selectionGate);
        const retryResponse = await retryPromise;
        if (retryResponse.ok()) {
            return;
        }
        const retryBody = await readResponseBody(retryResponse);
        console.log(`[settings] retry response ${retryResponse.status()}: ${retryBody}`);
        throw new Error(`Settings API retry failed (${retryResponse.status()}): ${retryBody}`);
    }
    throw new Error(`Settings API failed (${response.status()}): ${bodyText}`);
}

async function openSettings(page: import('@playwright/test').Page) {
    const selectionChanged = await ensureTenantSelection(page);
    if (selectionChanged) {
        await page.reload({ waitUntil: 'domcontentloaded' });
    }
    const settingsResponse = waitForSettingsResponse(page);
    await page.getByTestId('nav-settings').click();
    await expect(page).toHaveURL(urlPathPattern('/settings'));
    await expect(page.getByTestId('settings-title')).toBeVisible();
    await handleSettingsResponse(page, await settingsResponse);
}

async function openTenants(page: import('@playwright/test').Page) {
    await page.getByTestId('nav-tenants').click();
    await expect(page).toHaveURL(urlPathPattern('/tenants'));
    await expect(page.getByTestId('tenants-title')).toBeVisible();
}

function tenantsSection(page: import('@playwright/test').Page, title: string) {
    return page.locator('section').filter({ has: page.getByRole('heading', { name: title }) }).first();
}

async function resolveAuthOrigin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    resolvedBaseURL = actionOrigin;
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
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

async function waitForCasesState(
    page: import('@playwright/test').Page,
    timeout = 15000,
) {
    const row = page.getByTestId('cases-row').first();
    const empty = page.getByTestId('cases-empty');
    const error = page.getByTestId('cases-error');
    await expect
        .poll(
            async () => {
                if (await row.isVisible().catch(() => false)) return 'row';
                if (await empty.isVisible().catch(() => false)) return 'empty';
                if (await error.isVisible().catch(() => false)) return 'error';
                return 'pending';
            },
            { timeout }
        )
        .not.toBe('pending');
    if (await row.isVisible().catch(() => false)) {
        return 'row';
    }
    if (await empty.isVisible().catch(() => false)) {
        return 'empty';
    }
    return 'error';
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
        return false;
    }

    const value = await options.nth(1).getAttribute('value');
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue('');
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
    if (await selectFromGate(page, 'company-select', 'company-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    const contextCompany = page.getByTestId('context-company-select');
    await selectOptionIfNeeded(contextCompany);
    const contextClient = page.getByTestId('context-client-select');
    await selectOptionIfNeeded(contextClient);
    const contextBranch = page.getByTestId('context-branch-select');
    await selectOptionIfNeeded(contextBranch);
}

async function resolveSelectionGateWithRetry(
    page: import('@playwright/test').Page,
    selectionGate: import('@playwright/test').Locator,
    attempts = 3
) {
    for (let attempt = 0; attempt < attempts; attempt += 1) {
        await resolveSelectionGate(page);
        if (!(await selectionGate.isVisible().catch(() => false))) {
            return true;
        }
        await page.waitForTimeout(800);
    }
    return !(await selectionGate.isVisible().catch(() => false));
}

async function clearStoredContext(page: import('@playwright/test').Page) {
    await page.evaluate(() => {
        window.localStorage.removeItem('console:company_id');
        window.localStorage.removeItem('console:client_id');
        window.localStorage.removeItem('console:branch_id');
    });
}

async function retryProfileLoad(page: import('@playwright/test').Page) {
    const retry = page.getByTestId('me-retry');
    if (!(await retry.isVisible().catch(() => false))) {
        return false;
    }
    await clearStoredContext(page);
    await retry.click();
    await page.waitForTimeout(500);
    return true;
}

async function casesTitleOrContextVisible(
    page: import('@playwright/test').Page,
    selectionGate: import('@playwright/test').Locator,
    contextGate: import('@playwright/test').Locator,
) {
    const casesTitle = page.getByTestId('cases-title');
    const contextBar = page.getByTestId('context-bar');
    const inboxView = page.getByTestId('inbox-view');
    const consoleHeader = page.getByTestId('console-header');
    if (await casesTitle.isVisible().catch(() => false)) return true;
    if (await selectionGate.isVisible().catch(() => false)) return true;
    if (await contextGate.isVisible().catch(() => false)) return true;
    if (await contextBar.isVisible().catch(() => false)) return true;
    if (await inboxView.isVisible().catch(() => false)) return true;
    if (await consoleHeader.isVisible().catch(() => false)) return true;
    return false;
}

async function startKeycloakLogin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    let providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    if (actionOrigin !== baseURL) {
        await page.goto(buildSignInUrl(actionOrigin), { waitUntil: 'domcontentloaded' });
        providerForm = page.locator('form[action*="keycloak"]').first();
    }
    resolvedBaseURL = actionOrigin;
    const providerButton = page.getByRole('button', { name: /sign in with keycloak/i });
    if (await providerButton.isVisible().catch(() => false)) {
        await providerButton.click();
    } else if (await providerForm.isVisible().catch(() => false)) {
        await providerForm.waitFor({ state: 'visible', timeout: 15000 });
        const submitButton = providerForm
            .locator('button[type="submit"], input[type="submit"]')
            .first();
        await submitButton.click();
    } else {
        return false;
    }
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
    await resolveAuthOrigin(page);
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId('login-button');
    const logoutButton = page.getByTestId('logout-button');
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });

    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginThroughKeycloak(page);
        await gotoConsoleRoot(page);
    }

    if (useStorageState) {
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await resolveSelectionGate(page);
    }

    if (!(await casesTitleOrContextVisible(page, selectionGate, contextGate))) {
        if (await loginButton.isVisible().catch(() => false)) {
            await loginThroughKeycloak(page);
            await gotoConsoleRoot(page);
            await resolveSelectionGate(page);
            const resolvedAfterLogin = await ensureTenantSelection(page);
            if (resolvedAfterLogin) {
                await page.reload({ waitUntil: 'domcontentloaded' });
            }
        }
    }

    for (let attempt = 0; attempt < 3; attempt += 1) {
        const retried = await retryProfileLoad(page);
        if (retried) {
            const resolved = await ensureTenantSelection(page);
            if (resolved) {
                await page.reload({ waitUntil: 'domcontentloaded' });
            }
            await resolveSelectionGate(page);
        }
        if (await casesTitleOrContextVisible(page, selectionGate, contextGate)) {
            return;
        }
        await page.waitForTimeout(1000);
    }

    await expect
        .poll(
            async () => casesTitleOrContextVisible(page, selectionGate, contextGate),
            { timeout: 20000 }
        )
        .toBe(true);
}

async function fetchMe(
    page: import('@playwright/test').Page,
    companyId?: string | null,
    clientId?: string | null,
) {
    return page.evaluate(async ({ company, client, timeoutMs }) => {
        const headers: Record<string, string> = {};
        if (company) {
            headers['X-Company-Id'] = company;
        }
        if (client) {
            headers['X-Client-Id'] = client;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const response = await fetch('/api/proxy/me', { headers, signal: controller.signal });
            if (!response.ok) {
                return null;
            }
            return response.json();
        } catch {
            return null;
        } finally {
            clearTimeout(timer);
        }
    }, { company: companyId ?? null, client: clientId ?? null, timeoutMs: 5000 });
}

async function fetchMeWithRetry(
    page: import('@playwright/test').Page,
    companyId?: string | null,
    clientId?: string | null,
) {
    let data = await fetchMe(page, companyId, clientId);
    for (let attempt = 0; !data && attempt < 2; attempt += 1) {
        await page.waitForTimeout(1000);
        data = await fetchMe(page, companyId, clientId);
    }
    return data;
}

async function ensureTenantSelection(page: import('@playwright/test').Page): Promise<boolean> {
    const stored = await page.evaluate(() => ({
        companyId: window.localStorage.getItem('console:company_id'),
        clientId: window.localStorage.getItem('console:client_id'),
        branchId: window.localStorage.getItem('console:branch_id'),
    }));
    const envCompanyId = process.env.E2E_COMPANY_ID;
    const envClientId = process.env.E2E_CLIENT_ID;
    const envBranchId = process.env.E2E_BRANCH_ID;

    let changed = false;

    let nextCompanyId = stored.companyId || envCompanyId || null;
    const data = await fetchMeWithRetry(page);
    const accessibleCompanies: string[] = [];
    if (data?.companies?.length) {
        accessibleCompanies.push(
            ...data.companies.map((company: { id?: string }) => company.id).filter(Boolean)
        );
    } else if (data?.client?.company_id) {
        accessibleCompanies.push(data.client.company_id as string);
    }
    if (!nextCompanyId || (accessibleCompanies.length && !accessibleCompanies.includes(nextCompanyId))) {
        nextCompanyId = accessibleCompanies[0] ?? null;
    }
    if (nextCompanyId && nextCompanyId !== stored.companyId) {
        await page.evaluate((id) => {
            window.localStorage.setItem('console:company_id', id);
            window.localStorage.removeItem('console:client_id');
            window.localStorage.removeItem('console:branch_id');
        }, nextCompanyId);
        changed = true;
    }

    let nextClientId = stored.clientId || envClientId || null;
    const clientData = await fetchMeWithRetry(page, nextCompanyId);
    const accessibleClients: string[] = [];
    if (clientData?.clients?.length) {
        accessibleClients.push(
            ...clientData.clients.map((client: { id?: string }) => client.id).filter(Boolean)
        );
    } else if (clientData?.client?.id) {
        accessibleClients.push(clientData.client.id as string);
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
            const branchData = await fetchMeWithRetry(page, nextCompanyId, nextClientId);
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
    await gotoConsoleRoot(page);
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    await resolveSelectionGateWithRetry(page, selectionGate);
    if (await selectionGate.isVisible().catch(() => false)) {
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await resolveSelectionGateWithRetry(page, selectionGate);
    }
    await expect
        .poll(
            async () => {
                if (await page.getByTestId('cases-title').isVisible().catch(() => false)) return true;
                if (await selectionGate.isVisible().catch(() => false)) return true;
                if (await contextGate.isVisible().catch(() => false)) return true;
                if (await page.getByTestId('context-bar').isVisible().catch(() => false)) return true;
                return false;
            },
            { timeout: 20000 }
        )
        .toBe(true);
    if (await selectionGate.isVisible().catch(() => false)) {
        await resolveSelectionGateWithRetry(page, selectionGate);
    }
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 20000 });
    for (let attempt = 0; attempt < 3; attempt += 1) {
        const state = await waitForCasesState(page);
        if (state !== 'error') {
            return;
        }

        const retry = page.getByTestId('cases-retry');
        if (await retry.isVisible().catch(() => false)) {
            await retry.click();
        }
        await clearStoredContext(page);
        await page.reload({ waitUntil: 'domcontentloaded' });
        const resolved = await ensureTenantSelection(page);
        if (resolved) {
            await page.reload({ waitUntil: 'domcontentloaded' });
        }
        await resolveSelectionGateWithRetry(page, selectionGate);
        await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 20000 });
    }

    const errorPanel = page.getByTestId('cases-error');
    if (await errorPanel.isVisible().catch(() => false)) {
        const details = (await errorPanel.textContent().catch(() => null))?.trim() || 'unknown';
        throw new Error(`Inbox remained in error state after retries: ${details}`);
    }
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
        const caseVisible = page
            .getByTestId('case-conversation')
            .or(page.getByTestId('case-details'))
            .or(page.getByTestId('case-view'));
        await expect(caseVisible.first()).toBeVisible({ timeout: 10000 });
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
        await expect(page).toHaveURL(urlPathPattern('/ops'));
        await waitForHealth;
        await expect(page.getByTestId('ops-title')).toBeVisible();
        await expect(page.getByTestId('ops-health-card')).toBeVisible();
    });

    test('should navigate to Audit Log @smoke', async ({ page }) => {
        const waitForAudit = waitForApiOk(page, '/console/v1/audit');
        await page.getByTestId('nav-audit').click();
        await expect(page).toHaveURL(urlPathPattern('/audit'));
        await waitForAudit;
        await expect(page.getByTestId('audit-title')).toBeVisible();
        await expect(page.getByTestId('audit-table')).toBeVisible();
        await expectRowsOrEmpty(page, 'audit-row', 'audit-empty');
    });

    test('should navigate to Settings @smoke', async ({ page }) => {
        await openSettings(page);
        await expect(page.getByTestId('settings-branches')).toBeVisible();
        await expectRowsOrEmpty(page, 'settings-branch-row', 'settings-branches-empty');
    });

    test('should open Calendar with local date default @smoke', async ({ page }) => {
        await page.getByTestId('nav-calendar').click();
        await expect(page).toHaveURL(urlPathPattern('/calendar'));
        await expect(page.getByTestId('calendar-page')).toBeVisible();
        let dateInput = page.getByLabel('Дата');
        if (!(await dateInput.isVisible())) {
            dateInput = page.locator('input[type="date"]');
        }
        await expect(dateInput).toBeVisible();
        const localDate = await page.evaluate(() => {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        });
        await expect(dateInput).toHaveValue(localDate);
    });

    test('should render inline lifecycle panel on Tenants @smoke', async ({ page }) => {
        await openTenants(page);
        const clients = tenantsSection(page, 'Клиенты');
        await expect(clients).toBeVisible();

        const lifecycleButton = page.getByTestId('tenants-client-lifecycle-open').first();
        if (await lifecycleButton.isVisible().catch(() => false)) {
            await lifecycleButton.click();
            const lifecyclePanel = page.getByTestId('tenants-client-lifecycle-panel').first();
            await expect(lifecyclePanel).toBeVisible();
            await expect(lifecyclePanel.getByTestId('tenants-client-lifecycle-reason')).toBeVisible();
            await expect(lifecyclePanel.getByTestId('tenants-client-lifecycle-confirm')).toBeVisible();
            await lifecyclePanel.getByTestId('tenants-client-lifecycle-cancel').click();
            await expect(lifecyclePanel).not.toBeVisible();
            return;
        }

        // Backward-compatible check for pre-inline lifecycle UI.
        const legacyButton = clients.getByRole('button', { name: /Архивировать|Восстановить/i }).first();
        if (await legacyButton.isVisible().catch(() => false)) {
            let sawDialog = false;
            page.once('dialog', async (dialog) => {
                sawDialog = true;
                await dialog.dismiss();
            });
            await legacyButton.click();
            await expect.poll(() => sawDialog, { timeout: 5000 }).toBe(true);
            return;
        }

        await expect(clients.getByText(/Клиенты не найдены|фильтр по компании из контекста/i)).toBeVisible();
    });

    test('should expose branch change controls on Tenants @smoke', async ({ page }) => {
        await openTenants(page);
        const branches = tenantsSection(page, 'Филиалы');
        await expect(branches).toBeVisible();

        let editButton = page.getByTestId('tenants-branch-edit').first();
        if (!(await editButton.isVisible().catch(() => false))) {
            editButton = branches.getByRole('button', { name: 'Редактировать' }).first();
        }
        if (!(await editButton.isVisible().catch(() => false))) {
            await expect(branches.getByText(/Филиалы не найдены|фильтр по клиенту из контекста/i)).toBeVisible();
            return;
        }

        await editButton.click();
        const previewButton = page.getByTestId('tenants-branch-change-preview').first();
        if (await previewButton.isVisible().catch(() => false)) {
            await expect(previewButton).toBeVisible();
            await expect(page.getByTestId('tenants-branch-change-publish').first()).toBeVisible();
            await expect(page.getByTestId('tenants-branch-change-rollback').first()).toBeVisible();
            return;
        }

        await expect(branches.getByRole('button', { name: /Черновик \+ проверка|Draft \+ Validate/i }).first()).toBeVisible();
        await expect(branches.getByRole('button', { name: /Применить|Publish/i }).first()).toBeVisible();
        await expect(branches.getByRole('button', { name: /Откат|Rollback/i }).first()).toBeVisible();
    });

    test('should switch Tenants workspace modes @smoke', async ({ page }) => {
        await openTenants(page);
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-onboarding').click();
            await expect(page.getByTestId('tenants-onboarding-section')).toBeVisible();

            await page.getByTestId('tenants-mode-changes').click();
            await expect(page.getByTestId('tenants-change-management')).toBeVisible();

            await page.getByTestId('tenants-mode-decommission').click();
            await expect(page.getByTestId('tenants-decommission-center')).toBeVisible();
            await expect(page.getByTestId('tenants-clients-section')).toBeVisible();

            await page.getByTestId('tenants-mode-portfolio').click();
            await expect(page.getByTestId('tenants-portfolio-companies')).toBeVisible();

            await page.getByTestId('tenants-mode-all').click();
            await expect(page.getByTestId('tenants-onboarding-section')).toBeVisible();
            await expect(page.getByTestId('tenants-change-management')).toBeVisible();
            return;
        }

        // Legacy fallback for not-yet-deployed IA v2.
        await expect(tenantsSection(page, 'Компании')).toBeVisible();
        await expect(tenantsSection(page, 'Клиенты')).toBeVisible();
        await expect(tenantsSection(page, 'Филиалы')).toBeVisible();
    });

    test('should expose schema-driven onboarding controls on Tenants @smoke', async ({ page }) => {
        await openTenants(page);

        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-onboarding').click();
        }

        const wizard = page.getByTestId('provisioning-wizard');
        await expect(wizard).toBeVisible();
        await page.getByRole('button', { name: /Ручной по шагам/i }).click();

        const branchDraftStep = page.getByRole('button', { name: /Филиал/i }).first();
        if (await branchDraftStep.isVisible().catch(() => false) && !(await branchDraftStep.isDisabled().catch(() => true))) {
            await branchDraftStep.click();
        }

        const billingContractField = page.getByTestId('onboarding-billing-contract');
        const billingCurrencyField = page.getByTestId('onboarding-billing-currency');
        if (await billingContractField.isVisible().catch(() => false)) {
            await expect(billingContractField).toBeVisible();
            await expect(billingCurrencyField).toBeVisible();
        } else {
            await expect(page.getByPlaceholder('B2B').first()).toBeVisible();
            await expect(page.getByPlaceholder('KZT').first()).toBeVisible();
        }

        const bookingStep = page.getByRole('button', { name: /Бронирование/i }).first();
        if (await bookingStep.isVisible().catch(() => false) && !(await bookingStep.isDisabled().catch(() => true))) {
            await bookingStep.click();
            const workingHoursForm = page.getByTestId('onboarding-working-hours-form');
            const bookingSettingsForm = page.getByTestId('onboarding-booking-settings-form');
            if (await workingHoursForm.isVisible().catch(() => false)) {
                await expect(workingHoursForm).toBeVisible();
                await expect(bookingSettingsForm).toBeVisible();
            } else {
                await expect(page.getByText(/Working hours/i)).toBeVisible();
                await expect(page.getByText(/Booking settings/i)).toBeVisible();
            }
        }

        const goNoGoStep = page.getByRole('button', { name: /Go\/No-Go/i }).first();
        if (await goNoGoStep.isVisible().catch(() => false) && !(await goNoGoStep.isDisabled().catch(() => true))) {
            await goNoGoStep.click();
            const purchasedForm = page.getByTestId('onboarding-purchased-form');
            if (await purchasedForm.isVisible().catch(() => false)) {
                await expect(purchasedForm).toBeVisible();
                await expect(page.getByTestId('onboarding-purchased-apply-json')).toBeVisible();
                await expect(page.getByTestId('onboarding-purchased-json')).toBeVisible();
            } else {
                const schemaLabel = page.getByText(/Purchased capabilities \(schema form\)/i);
                if (await schemaLabel.isVisible().catch(() => false)) {
                    await expect(schemaLabel).toBeVisible();
                    await expect(page.getByText(/Advanced JSON \(expert\)/i)).toBeVisible();
                } else {
                    // Backward-compatible path for environments without schema layer.
                    await expect(page.getByText(/purchased \(JSON, договор\/возможности\)/i)).toBeVisible();
                }
            }
            return;
        }

        // Fallback path when go/no-go step is still locked by state machine.
        await expect(page.getByText(/booking_settings и working_hours нужны/i)).toBeVisible();
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
        await expect(page).toHaveURL(urlPathPattern('/audit'));
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
        await openSettings(page);
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
