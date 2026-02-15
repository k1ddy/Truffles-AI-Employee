import { expect, test } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const isLocalBaseURL = /localhost|127\.0\.0\.1/.test(baseURL);
const quarantineLocal = !!process.env.CI && isLocalBaseURL;

let resolvedBaseURL = baseURL;

test.skip(quarantineLocal, 'Quarantine local CI owner/admin suite while stabilizing console-e2e.');

function buildSignInUrl(origin: string) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(origin)}`;
}

function urlPathPattern(path: string) {
    return new RegExp(`${path.replace(/\//g, '\\/')}(\\?|$)`);
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

async function selectOptionIfNeeded(selector: import('@playwright/test').Locator) {
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
    confirmTestId: string,
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
    await selectOptionIfNeeded(page.getByTestId('context-company-select'));
    await selectOptionIfNeeded(page.getByTestId('context-client-select'));
    await selectOptionIfNeeded(page.getByTestId('context-branch-select'));
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
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginThroughKeycloak(page);
        await gotoConsoleRoot(page);
    }
    await resolveSelectionGate(page);
}

test.describe('Owner/Admin Business Control', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
    });

    test('should expose owner/admin control navigation and business summary @smoke', async ({ page }) => {
        await expect(page.getByTestId('nav-business')).toBeVisible();
        await expect(page.getByTestId('nav-data-trust')).toBeVisible();
        await expect(page.getByTestId('nav-team-performance')).toBeVisible();
        await expect(page.getByTestId('nav-subscription')).toBeVisible();

        await page.getByTestId('nav-business').click();
        await expect(page).toHaveURL(urlPathPattern('/business'));
        await expect(page.getByTestId('business-title')).toBeVisible();
        await expect(page.getByTestId('business-status-card')).toBeVisible();
        await expect(page.getByTestId('business-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('business-actions')).toBeVisible();

        await expect(page.getByTestId('business-wave2-shortcuts')).toBeVisible();
        await page.getByRole('link', { name: 'Открыть Data Trust' }).click();
        await expect(page).toHaveURL(urlPathPattern('/business/data-trust'));
        await expect(page.getByTestId('data-trust-title')).toBeVisible();
    });

    test('should render data-trust and team-performance operational surfaces @smoke', async ({ page }) => {
        await page.getByTestId('nav-data-trust').click();
        await expect(page).toHaveURL(urlPathPattern('/business/data-trust'));
        await expect(page.getByTestId('data-trust-title')).toBeVisible();
        await expect(page.getByTestId('data-trust-status-card')).toBeVisible();
        await expect(page.getByTestId('data-trust-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('data-trust-actions')).toBeVisible();

        await page.getByTestId('nav-team-performance').click();
        await expect(page).toHaveURL(urlPathPattern('/business/team-performance'));
        await expect(page.getByTestId('team-performance-title')).toBeVisible();
        await expect(page.getByTestId('team-performance-status-card')).toBeVisible();
        await expect(page.getByTestId('team-performance-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('team-performance-actions')).toBeVisible();
        const quickProfile = page.getByTestId('team-performance-quick-profile');
        if (await quickProfile.isVisible().catch(() => false)) {
            await expect(page.getByTestId('team-performance-quick-profile-apply')).toBeVisible();
            await expect(page.getByTestId('team-performance-remediation-guide')).toBeVisible();
            await expect(page.getByTestId('team-performance-quick-profile-rollback-card')).toBeVisible();
        }
        const teamTable = page.getByTestId('team-performance-table');
        const teamEmpty = page.getByText('Нет открытых заявок в текущем scope.');
        await expect(teamTable.or(teamEmpty)).toBeVisible();

        await page.getByTestId('nav-subscription').click();
        await expect(page).toHaveURL(urlPathPattern('/subscription'));
        await expect(page.getByTestId('subscription-title')).toBeVisible();
        await expect(page.getByTestId('subscription-alert')).toBeVisible();
        await expect(page.getByTestId('subscription-forecast-v2')).toBeVisible();
    });

    test('should render simple owner settings and explainability surface @smoke', async ({ page }) => {
        await page.getByTestId('nav-settings').click();
        await expect(page).toHaveURL(urlPathPattern('/settings'));
        await expect(page.getByTestId('settings-simple-card')).toBeVisible();
        await expect(page.getByTestId('settings-after-save')).toBeVisible();
        await expect(page.getByTestId('settings-telegram-connector')).toBeVisible();
        await expect(page.getByTestId('settings-subscription-snapshot')).toBeVisible();
        await expect(page.getByTestId('settings-input-reminder1')).toBeVisible();
        await expect(page.getByTestId('settings-input-reminder2')).toBeVisible();
        await expect(page.getByTestId('settings-input-escalation')).toBeVisible();
        await expect(page.getByTestId('settings-save-simple')).toBeVisible();

        await page.getByTestId('settings-preset-fast').click();
        await expect(page.getByTestId('settings-input-reminder1')).toHaveValue('5');
        await expect(page.getByTestId('settings-input-reminder2')).toHaveValue('30');
        await expect(page.getByTestId('settings-input-escalation')).toHaveValue('60');

        await page.getByTestId('settings-advanced-toggle').click();
        await expect(page.getByTestId('settings-branches')).toBeVisible();
    });
});
