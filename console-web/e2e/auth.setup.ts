import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const authFile = path.resolve(__dirname, '..', '.auth', 'console.json');

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
    await page.goto('/');
    await page.getByRole('button', { name: /войти/i }).click();
    await page.waitForURL(keycloakHostPattern);
    await page.fill('#username', loginUser);
    await page.fill('#password', loginPassword);
    await page.click('#kc-login');
    await page.waitForURL(consoleHostPattern);
    await expect(page.getByRole('button', { name: /выйти/i })).toBeVisible({ timeout: 10000 });
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
