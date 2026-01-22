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

test('setup auth @smoke', async ({ page }) => {
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

    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    await page.context().storageState({ path: authFile });
});
