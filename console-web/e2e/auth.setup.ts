import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = /localhost|127\.0\.0\.1/.test(baseURL);
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

function buildSignInUrl(origin: string, callbackOrigin = origin) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(callbackOrigin)}`;
}

function resolvePreferredOrigin(actionOrigin: string) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
}

async function ensureAuthenticatedConsole(page: import('@playwright/test').Page) {
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId('login-button');
    const logoutButton = page.getByTestId('logout-button');

    await expect
        .poll(
            async () =>
                (await loginButton.isVisible().catch(() => false))
                || (await logoutButton.isVisible().catch(() => false)),
            { timeout: 20000 }
        )
        .toBe(true);

    const hasLogout = await logoutButton.isVisible().catch(() => false);
    const hasLogin = await loginButton.isVisible().catch(() => false);
    if (!hasLogout && hasLogin) {
        await loginThroughKeycloak(page);
        await gotoConsoleRoot(page);
    }
}

async function startKeycloakLogin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    let providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    if (actionOrigin !== baseURL) {
        const callbackOrigin = stayOnBaseOrigin ? baseURL : actionOrigin;
        await page.goto(buildSignInUrl(actionOrigin, callbackOrigin), { waitUntil: 'domcontentloaded' });
        providerForm = page.locator('form[action*="keycloak"]').first();
    }
    resolvedBaseURL = resolvePreferredOrigin(actionOrigin);
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

async function waitForConsoleReadyState(page: import('@playwright/test').Page, timeoutMs = 20000): Promise<boolean> {
    const deadline = Date.now() + timeoutMs;
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    const contextBar = page.getByTestId('context-bar');
    const inboxView = page.getByTestId('inbox-view');
    const consoleHeader = page.getByTestId('console-header');
    const casesTitle = page.getByTestId('cases-title');

    while (Date.now() < deadline) {
        if (await casesTitle.isVisible().catch(() => false)) return true;
        if (await selectionGate.isVisible().catch(() => false)) return true;
        if (await contextGate.isVisible().catch(() => false)) return true;
        if (await contextBar.isVisible().catch(() => false)) return true;
        if (await inboxView.isVisible().catch(() => false)) return true;
        if (await consoleHeader.isVisible().catch(() => false)) return true;
        await page.waitForTimeout(300);
    }
    return false;
}

test('setup auth @smoke', async ({ page }) => {
    const pageErrors: string[] = [];
    const consoleErrors: string[] = [];
    page.on('pageerror', (error) => {
        pageErrors.push(`${error.name}: ${error.message}\n${error.stack ?? ''}`);
    });
    page.on('console', (message) => {
        if (message.type() === 'error') {
            consoleErrors.push(message.text());
        }
    });

    await loginThroughKeycloak(page);
    await ensureAuthenticatedConsole(page);
    let ready = false;
    for (let attempt = 0; attempt < 3; attempt += 1) {
        ready = await waitForConsoleReadyState(page, 20000);
        if (ready) {
            break;
        }
        const hasChunkLoadError = pageErrors.some((entry) => entry.includes('ChunkLoadError'));
        if (hasChunkLoadError && attempt < 2) {
            pageErrors.length = 0;
            consoleErrors.length = 0;
            await gotoConsoleRoot(page);
            await ensureAuthenticatedConsole(page);
        }
    }

    if (!ready) {
        const diagnostics = [
            `final_url=${page.url()}`,
            pageErrors.length ? `page_errors:\n${pageErrors.join('\n---\n')}` : 'page_errors: none',
            consoleErrors.length ? `console_errors:\n${consoleErrors.join('\n')}` : 'console_errors: none',
        ].join('\n\n');
        throw new Error(`auth.setup readiness failed\n\n${diagnostics}`);
    }

    await selectCompanyIfNeeded(page);
    await selectClientIfNeeded(page);
    await selectBranchIfNeeded(page);

    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    await page.context().storageState({ path: authFile });
});
