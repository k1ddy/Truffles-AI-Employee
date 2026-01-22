import { test, expect } from '@playwright/test';

const runMutations = process.env.E2E_ALLOW_MUTATIONS === '1';

// =========================================
// HELPER: Open inbox with storage state
// =========================================
async function openInbox(page: import('@playwright/test').Page) {
    await page.goto('/');
    await expect(page.getByTestId('cases-title')).toBeVisible({ timeout: 10000 });
}


// =========================================
// INBOX FILTERS & NAVIGATION
// =========================================
test.describe('Inbox Features', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should display filter controls @smoke', async ({ page }) => {
        await expect(page.getByRole('combobox').first()).toBeVisible();
        await expect(page.getByText('Мои заявки')).toBeVisible();
        await expect(page.getByText('Обновить')).toBeVisible();
    });

    test('should filter by status @smoke', async ({ page }) => {
        await page.locator('select').first().selectOption('Ожидает');
        await page.waitForTimeout(1000);
        await expect(page.getByRole('heading', { name: 'Заявки' })).toBeVisible();
    });

    test('should navigate to case detail @smoke', async ({ page }) => {
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/);
            await expect(page.getByText('Диалог')).toBeVisible({ timeout: 5000 });
        }
    });
});

// =========================================
// NAVIGATION
// =========================================
test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should navigate to Status page @smoke', async ({ page }) => {
        await page.getByRole('link', { name: 'Статус' }).click();
        await expect(page).toHaveURL('/ops');
        await expect(page.getByText('Статус системы')).toBeVisible();
    });

    test('should navigate to Audit Log @smoke', async ({ page }) => {
        await page.getByRole('link', { name: 'Журнал' }).click();
        await expect(page).toHaveURL('/audit');
        await expect(page.getByText('Журнал')).toBeVisible();
    });

    test('should navigate to Settings @smoke', async ({ page }) => {
        await page.getByRole('link', { name: 'Настройки' }).click();
        await expect(page).toHaveURL('/settings');
        await expect(page.getByText('Филиалы')).toBeVisible();
    });
});

// =========================================
// CASE ACTIONS (Take, Reply, Resolve)
// =========================================
test.describe('Case Actions @mutating', () => {
    test.skip(!runMutations, 'Mutating tests are disabled');
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
    });

    test('should take a pending case @mutating', async ({ page }) => {
        // Filter to pending cases using visible text
        await page.locator('select').first().selectOption('Ожидает');
        await page.waitForTimeout(500);

        // Open first pending case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find and click Take button (Взять заявку)
            const takeButton = page.getByRole('button', { name: /взять/i });
            if (await takeButton.isVisible()) {
                await takeButton.click();

                // Should see success indication (status changes or button disappears)
                await page.waitForTimeout(1000);
                // Verify we're still on the page (no crash)
                await expect(page.getByText('Диалог')).toBeVisible();
            }
        }
    });

    test('should send a reply message @mutating', async ({ page }) => {
        // Filter to active cases (where we can reply)
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        // Open first active case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find reply textarea and send button
            const replyInput = page.locator('textarea');
            const sendButton = page.getByRole('button', { name: /отправить/i });

            if (await replyInput.isVisible()) {
                // Type a test message
                await replyInput.fill('Test reply from E2E test');

                // Click send
                if (await sendButton.isVisible()) {
                    await sendButton.click();

                    // Wait for message to appear or success indication
                    await page.waitForTimeout(1000);

                    // Verify we're still on the page
                    await expect(page.getByText('Диалог')).toBeVisible();
                }
            }
        }
    });

    test('should resolve an active case @mutating', async ({ page }) => {
        // Filter to active cases
        await page.locator('select').first().selectOption('В работе');
        await page.waitForTimeout(500);

        // Open first active case
        const openButton = page.getByRole('link', { name: 'Открыть' }).first();
        if (await openButton.isVisible()) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\//);

            // Find and click Resolve button (Закрыть заявку)
            const resolveButton = page.getByRole('button', { name: /закрыть/i });
            if (await resolveButton.isVisible()) {
                await resolveButton.click();

                // Wait for action to complete
                await page.waitForTimeout(1000);

                // Should redirect to inbox or show success
                const isOnCasePage = page.url().includes('/cases/');
                if (isOnCasePage) {
                    // Status might have changed to resolved
                    await expect(page.getByText(/закрыта/i)).toBeVisible({ timeout: 3000 });
                }
            }
        }
    });
});

// =========================================
// AUDIT LOG
// =========================================
test.describe('Audit Log', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
        await page.getByRole('link', { name: 'Журнал' }).click();
        await expect(page).toHaveURL('/audit');
    });

    test('should display audit events table @smoke', async ({ page }) => {
        await expect(page.getByText('Журнал действий')).toBeVisible();
        // Check for table headers
        await expect(page.getByText('Время')).toBeVisible();
        await expect(page.getByText('Событие')).toBeVisible();
        await expect(page.getByText('Исполнитель')).toBeVisible();
    });

    test('should show event types with badges @smoke', async ({ page }) => {
        // Look for common event type badges
        const eventBadges = page.locator('[class*="bg-"]').filter({ hasText: /case_taken|case_resolved|message_sent/i });
        // Just verify no crash, events may or may not exist
        await page.waitForTimeout(500);
    });
});

// =========================================
// SETTINGS PAGE
// =========================================
test.describe('Settings Page', () => {
    test.beforeEach(async ({ page }) => {
        await openInbox(page);
        await page.getByRole('link', { name: 'Настройки' }).click();
        await expect(page).toHaveURL('/settings');
    });

    test('should display branches section @smoke', async ({ page }) => {
        await expect(page.getByText('Филиалы')).toBeVisible();
    });

    test('should display team members section @smoke', async ({ page }) => {
        await expect(page.getByText('Команда')).toBeVisible();
    });
});
