import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';

async function selectClientIfNeeded(page: import('@playwright/test').Page) {
    const clientSelector = page.getByTestId('client-selector');
    if (!(await clientSelector.isVisible())) {
        return;
    }

    const currentValue = await clientSelector.inputValue();
    if (currentValue) {
        return;
    }

    const options = clientSelector.locator('option');
    const optionCount = await options.count();
    if (optionCount < 2) {
        return;
    }

    const value = await options.nth(1).getAttribute('value');
    if (value) {
        await clientSelector.selectOption(value);
    } else {
        await clientSelector.selectOption({ index: 1 });
    }
    await expect(clientSelector).not.toHaveValue("");
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
        await page.getByRole('button', { name: /выйти/i }).click();
        await expect(page.getByRole('button', { name: /войти/i })).toBeVisible({ timeout: 10000 });
    });
});
