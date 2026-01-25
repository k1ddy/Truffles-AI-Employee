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

async function selectClientIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-client-select');
    await selectOptionIfNeeded(contextSelector);
}

async function selectBranchIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-branch-select');
    await selectOptionIfNeeded(contextSelector);
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
        await expect(page.getByRole('button', { name: /выйти/i })).toBeVisible({ timeout: 10000 });
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 10000 });
    });

    test('should logout successfully @smoke', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /войти/i }).click();
        await page.waitForURL(keycloakHostPattern);
        await page.fill('#username', loginUser);
        await page.fill('#password', loginPassword);
        await page.click('#kc-login');
        await page.waitForURL(consoleHostPattern);
        await expect(page.getByRole('button', { name: /выйти/i })).toBeVisible({ timeout: 10000 });
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await page.getByRole('button', { name: /выйти/i }).click();
        await expect(page.getByRole('button', { name: /войти/i })).toBeVisible({ timeout: 10000 });
    });
});
