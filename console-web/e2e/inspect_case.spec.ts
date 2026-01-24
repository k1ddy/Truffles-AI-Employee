import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';

test('inspect first case', async ({ page }) => {
    // 1. Check if already logged in or need login
    await page.goto('/');
    try {
        await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 5000 });
        console.log('Already logged in.');
    } catch {
        console.log('Not logged in, attempting login...');
        const loginButton = page.getByRole('button', { name: /войти/i });
        if (await loginButton.isVisible()) {
            await loginButton.click();
            await page.waitForURL(keycloakHostPattern);
            await page.fill('#username', loginUser);
            await page.fill('#password', loginPassword);
            await page.click('#kc-login');
            await page.waitForURL(consoleHostPattern);
        }
    }

    // 2. Select Client if needed
    const clientSelector = page.getByTestId('client-selector');
    if (await clientSelector.isVisible()) {
        const currentValue = await clientSelector.inputValue();
        if (!currentValue) {
            const options = clientSelector.locator('option');
            if (await options.count() >= 2) {
                const value = await options.nth(1).getAttribute('value');
                if (value) await clientSelector.selectOption(value);
            }
        }
    }

    // 3. Wait for Inbox
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 15000 });

    // 4. Click first case
    // Debug: Dump HTML of the first row or table
    const tableHtml = await page.getByTestId('cases-table').innerHTML().catch(() => 'Table HTML not found');
    console.log('--- TABLE HTML START ---');
    console.log(tableHtml.slice(0, 2000)); // Print first 2000 chars
    console.log('--- TABLE HTML END ---');

    // Try finding by text "Открыть"
    const openButton = page.getByText('Открыть').first();
    if (await openButton.isVisible()) {
        console.log('Clicking first case (text "Открыть")...');
        await openButton.click();
        await page.waitForURL(/\/cases\//);
        await expect(page.getByTestId('case-view')).toBeVisible();

        // 5. Capture Info
        const url = page.url();
        console.log(`Navigated to: ${url}`);

        const content = await page.getByTestId('case-view').innerText();
        console.log('--- CASE CONTENT START ---');
        console.log(content);
        console.log('--- CASE CONTENT END ---');

        // Screenshot
        const screenshotPath = path.resolve('case_inspection.png');
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Screenshot saved to: ${screenshotPath}`);
    } else {
        console.log('No cases found to open.');
        const inboxContent = await page.getByTestId('cases-table').innerText().catch(() => 'Table not found');
        console.log('Inbox Table Content:', inboxContent);
        const emptyState = await page.getByTestId('cases-empty').innerText().catch(() => 'Empty state not found');
        console.log('Empty State Content:', emptyState);

        const screenshotPath = path.resolve('inbox_debug.png');
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Debug screenshot saved to: ${screenshotPath}`);
    }
});
