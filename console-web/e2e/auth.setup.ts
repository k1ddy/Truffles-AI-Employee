import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
let resolvedBaseURL = baseURL;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const authFile = path.resolve(__dirname, '..', '.auth', 'console.json');

async function waitForConsoleApp(page: import('@playwright/test').Page) {
    await page.waitForURL(
        (url) => consoleHostPattern.test(url.toString()) && !url.toString().includes('/api/auth'),
        { timeout: 30000 }
    );
}

function buildSignInUrl(origin: string) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(origin)}`;
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
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
        page.waitForURL(keycloakHostPattern, { timeout: 20000 }),
        waitForConsoleApp(page),
    ]);
    return true;
}

async function loginThroughKeycloak(page: import('@playwright/test').Page) {
    const started = await startKeycloakLogin(page);
    if (!started) {
        return;
    }
    if (!(await page.locator('#username').isVisible().catch(() => false))) {
        await waitForConsoleApp(page);
        await gotoConsoleRoot(page);
        return;
    }
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await page.fill('#username', loginUser);
    await page.fill('#password', loginPassword);
    await page.click('#kc-login');
    await waitForConsoleApp(page);
    await gotoConsoleRoot(page);
}

async function selectOptionIfNeeded(
    selector: import('@playwright/test').Locator
) {
    if (!(await selector.isVisible().catch(() => false))) {
        return;
    }

    const currentValue = await selector.inputValue();
    if (currentValue) {
        return;
    }

    const options = selector.locator('option');
    const optionCount = await options.count();
    if (optionCount < 2) {
        return;
    }

    const value = await options.nth(1).getAttribute('value');
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue('');
}

async function selectClientIfNeeded(page: import('@playwright/test').Page) {
    const gateSelector = page.getByTestId('client-select');
    const contextSelector = page.getByTestId('context-client-select');
    if (await gateSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(gateSelector);
        const confirm = page.getByTestId('client-select-confirm');
        if (await confirm.isVisible().catch(() => false)) {
            await confirm.click();
        }
        return;
    }
    if (await contextSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(contextSelector);
    }
}

async function selectCompanyIfNeeded(page: import('@playwright/test').Page) {
    const gateSelector = page.getByTestId('company-select');
    const contextSelector = page.getByTestId('context-company-select');
    if (await gateSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(gateSelector);
        const confirm = page.getByTestId('company-select-confirm');
        if (await confirm.isVisible().catch(() => false)) {
            await confirm.click();
        }
        return;
    }
    if (await contextSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(contextSelector);
    }
}

async function selectBranchIfNeeded(page: import('@playwright/test').Page) {
    const gateSelector = page.getByTestId('branch-select');
    const contextSelector = page.getByTestId('context-branch-select');
    if (await gateSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(gateSelector);
        const confirm = page.getByTestId('branch-select-confirm');
        if (await confirm.isVisible().catch(() => false)) {
            await confirm.click();
        }
        return;
    }
    if (await contextSelector.isVisible().catch(() => false)) {
        await selectOptionIfNeeded(contextSelector);
    }
}

test('setup auth @smoke', async ({ page }) => {
    await loginThroughKeycloak(page);
    await expect(page.getByTestId('logout-button')).toBeVisible({ timeout: 20000 });
    await selectCompanyIfNeeded(page);
    await selectClientIfNeeded(page);
    await selectBranchIfNeeded(page);
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    const contextBar = page.getByTestId('context-bar');
    const inboxView = page.getByTestId('inbox-view');
    const consoleHeader = page.getByTestId('console-header');
    await expect
        .poll(
            async () => {
                if (await page.getByTestId('cases-title').isVisible().catch(() => false)) return true;
                if (await selectionGate.isVisible().catch(() => false)) return true;
                if (await contextGate.isVisible().catch(() => false)) return true;
                if (await contextBar.isVisible().catch(() => false)) return true;
                if (await inboxView.isVisible().catch(() => false)) return true;
                if (await consoleHeader.isVisible().catch(() => false)) return true;
                return false;
            },
            { timeout: 20000 }
        )
        .toBe(true);

    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    await page.context().storageState({ path: authFile });
});
