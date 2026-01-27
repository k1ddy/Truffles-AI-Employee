import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';

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

async function selectClientIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-client-select');
    await selectOptionIfNeeded(contextSelector);
}

async function selectCompanyIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'company-select', 'company-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-company-select');
    await selectOptionIfNeeded(contextSelector);
}

async function selectBranchIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-branch-select');
    await selectOptionIfNeeded(contextSelector);
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

async function waitForConsoleReady(page: import('@playwright/test').Page) {
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    const casesTitle = page.getByTestId('cases-title');
    const contextBar = page.getByTestId('context-bar');
    const inboxView = page.getByTestId('inbox-view');
    const consoleHeader = page.getByTestId('console-header');
    for (let attempt = 0; attempt < 3; attempt += 1) {
        await retryProfileLoad(page);
        if (await casesTitle.isVisible().catch(() => false)) return;
        if (await selectionGate.isVisible().catch(() => false)) return;
        if (await contextGate.isVisible().catch(() => false)) return;
        if (await contextBar.isVisible().catch(() => false)) return;
        if (await inboxView.isVisible().catch(() => false)) return;
        if (await consoleHeader.isVisible().catch(() => false)) return;
        await page.waitForTimeout(1000);
    }
    await expect
        .poll(
            async () => {
                if (await casesTitle.isVisible().catch(() => false)) return true;
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
}

test.describe('Smoke Test: Login Flow', () => {
    test('should redirect to Keycloak login @smoke', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('button', { name: /войти/i })).toBeVisible();
        await page.getByRole('button', { name: /войти/i }).click();
        await expect(page).toHaveURL(keycloakHostPattern);
        await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    });

    test('should login and see inbox @smoke', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /войти/i }).click();
        await page.waitForURL(keycloakHostPattern);
        await page.fill('#username', loginUser);
        await page.fill('#password', loginPassword);
        await page.click('#kc-login');
        await page.waitForURL(consoleHostPattern);
        await page.goto('/');
        await expect(page.getByRole('button', { name: /выйти/i })).toBeVisible({ timeout: 10000 });
        await selectCompanyIfNeeded(page);
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await waitForConsoleReady(page);
    });

    test('should logout successfully @smoke', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /войти/i }).click();
        await page.waitForURL(keycloakHostPattern);
        await page.fill('#username', loginUser);
        await page.fill('#password', loginPassword);
        await page.click('#kc-login');
        await page.waitForURL(consoleHostPattern);
        await page.goto('/');
        await expect(page.getByRole('button', { name: /выйти/i })).toBeVisible({ timeout: 10000 });
        await selectCompanyIfNeeded(page);
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await page.getByRole('button', { name: /выйти/i }).click();
        await expect(page.getByRole('button', { name: /войти/i })).toBeVisible({ timeout: 10000 });
    });
});
