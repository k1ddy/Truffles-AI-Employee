import { test, expect } from '@playwright/test';
import path from 'path';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';

async function gotoWithRetry(page: import('@playwright/test').Page, url: string, attempts = 3) {
    let lastError: unknown = null;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
            await page.goto(url, { waitUntil: 'domcontentloaded' });
            return;
        } catch (error) {
            lastError = error;
            if (attempt >= attempts) {
                break;
            }
            await page.waitForTimeout(500 * attempt);
        }
    }
    if (lastError instanceof Error) {
        throw lastError;
    }
    throw new Error(`Failed to navigate to ${url}`);
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
    const nextValue = await options.nth(1).getAttribute('value');
    if (nextValue) {
        await selector.selectOption(nextValue);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue('');
    return true;
}

async function resolveTenantSelection(page: import('@playwright/test').Page) {
    const gateSelectors = [
        page.getByTestId('company-select'),
        page.getByTestId('client-select'),
        page.getByTestId('branch-select'),
        page.getByTestId('context-company-select'),
        page.getByTestId('context-client-select'),
        page.getByTestId('context-branch-select'),
    ];
    for (const selector of gateSelectors) {
        await selectOptionIfNeeded(selector);
    }
}

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    await gotoWithRetry(page, baseURL);
    const casesTitle = page.getByTestId('cases-title');
    if (await casesTitle.isVisible().catch(() => false)) {
        return;
    }

    const loginButtonLocator = page.getByTestId('login-button').or(page.getByRole('button', { name: /войти/i })).first();
    for (let attempt = 0; attempt < 6; attempt += 1) {
        if (await casesTitle.isVisible().catch(() => false)) {
            return;
        }
        if (await loginButtonLocator.isVisible().catch(() => false)) {
            break;
        }
        await page.waitForTimeout(400);
    }

    if (await loginButtonLocator.isVisible().catch(() => false)) {
        let clicked = false;
        for (let attempt = 1; attempt <= 3; attempt += 1) {
            try {
                await loginButtonLocator.click({ timeout: 5000 });
                clicked = true;
                break;
            } catch {
                if (await casesTitle.isVisible().catch(() => false)) {
                    return;
                }
                await page.waitForTimeout(400 * attempt);
            }
        }
        if (!clicked && !(await casesTitle.isVisible().catch(() => false))) {
            throw new Error('Failed to click login button after retries');
        }

        await Promise.race([
            page.waitForURL(keycloakHostPattern, { timeout: 15000 }),
            page.waitForURL(consoleHostPattern, { timeout: 15000 }),
        ]);
        if (await page.locator('#username').isVisible().catch(() => false)) {
            await page.fill('#username', loginUser);
            await page.fill('#password', loginPassword);
            await page.click('#kc-login');
            await page.waitForURL(consoleHostPattern, { timeout: 20000 });
        }
        await gotoWithRetry(page, baseURL);
    }

    await resolveTenantSelection(page);
    await expect(casesTitle).toBeVisible({ timeout: 20000 });
}

test('inspect first case', async ({ page }) => {
    test.setTimeout(90000);
    await ensureLoggedIn(page);
    await resolveTenantSelection(page);
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 20000 });

    const tableHtml = await page.getByTestId('cases-table').innerHTML().catch(() => 'Table HTML not found');
    console.log('--- TABLE HTML START ---');
    console.log(tableHtml.slice(0, 2000));
    console.log('--- TABLE HTML END ---');

    const emptyState = page.getByTestId('cases-empty');
    if (await emptyState.isVisible().catch(() => false)) {
        console.log('No cases found to inspect.');
        const screenshotPath = path.resolve('inbox_debug.png');
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Debug screenshot saved to: ${screenshotPath}`);
        return;
    }

    const firstRow = page.getByTestId('cases-row').first();
    await expect(firstRow).toBeVisible({ timeout: 15000 });
    await firstRow.click();

    const casePane = page
        .getByTestId('case-conversation')
        .or(page.getByTestId('case-details'))
        .or(page.getByTestId('case-view'));

    if (!(await casePane.first().isVisible().catch(() => false))) {
        const openButton = page.getByTestId('case-open').first();
        if (await openButton.isVisible().catch(() => false)) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/, { timeout: 15000 });
        }
    }

    await expect(casePane.first()).toBeVisible({ timeout: 15000 });
    console.log(`Current URL: ${page.url()}`);

    let content = '';
    const contentCandidates = [
        page.getByTestId('case-conversation'),
        page.getByTestId('case-details'),
        page.getByTestId('case-view'),
    ];
    for (const candidate of contentCandidates) {
        if (await candidate.isVisible().catch(() => false)) {
            content = (await candidate.innerText().catch(() => '')).slice(0, 3000);
            if (content) {
                break;
            }
        }
    }
    console.log('--- CASE CONTENT START ---');
    console.log(content || 'Case content is empty');
    console.log('--- CASE CONTENT END ---');

    const screenshotPath = path.resolve('case_inspection.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved to: ${screenshotPath}`);
});
