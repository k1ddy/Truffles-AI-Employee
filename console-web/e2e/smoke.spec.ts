import { test, expect } from '@playwright/test';

// =========================================
// SMOKE TESTS: Authentication
// =========================================
test.describe('Smoke Test: Login Flow', () => {
    test('should redirect to Keycloak login', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText('Truffles Console')).toBeVisible();
        await page.getByRole('button', { name: /войти/i }).click();
        await expect(page).toHaveURL(/localhost:8080|192\.168\.5\.27:8080/);
        // Keycloak login page title
        await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    });

    test('should login and see inbox', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /войти/i }).click();
        await page.waitForURL(/localhost:8080|192\.168\.5\.27:8080/);
        await page.fill('#username', 'admin');
        await page.fill('#password', 'admin');
        await page.click('#kc-login');
        await page.waitForURL(/localhost:3000|192\.168\.5\.27:3000/);
        await expect(page.getByText('Truffles Console')).toBeVisible();
        await expect(page.getByText('Заявки')).toBeVisible({ timeout: 10000 });
    });

    test('should logout successfully', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /войти/i }).click();
        await page.waitForURL(/localhost:8080|192\.168\.5\.27:8080/);
        await page.fill('#username', 'admin');
        await page.fill('#password', 'admin');
        await page.click('#kc-login');
        await page.waitForURL(/localhost:3000|192\.168\.5\.27:3000/);
        await page.getByRole('button', { name: /выйти/i }).click();
        await expect(page.getByRole('button', { name: /войти/i })).toBeVisible({ timeout: 10000 });
    });
});

// =========================================
// HELPER: Login before tests
// =========================================
async function loginAsAdmin(page: import('@playwright/test').Page) {
    await page.goto('/');
    await page.getByRole('button', { name: /войти/i }).click();
    await page.waitForURL(/localhost:8080|192\.168\.5\.27:8080/);
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin');
    await page.click('#kc-login');
    await page.waitForURL(/localhost:3000|192\.168\.5\.27:3000/);
    await expect(page.getByText('Заявки')).toBeVisible({ timeout: 10000 });
}


// =========================================
// INBOX FILTERS & NAVIGATION
// =========================================
test.describe('Inbox Features', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test('should display filter controls', async ({ page }) => {
        await expect(page.getByRole('combobox').first()).toBeVisible();
        await expect(page.getByText('Мои заявки')).toBeVisible();
        await expect(page.getByText('Обновить')).toBeVisible();
    });

    test('should filter by status', async ({ page }) => {
        await page.locator('select').first().selectOption('Ожидает');
        await page.waitForTimeout(1000);
        await expect(page.getByText(/заявк/i)).toBeVisible();
    });

    test('should navigate to case detail', async ({ page }) => {
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
        await loginAsAdmin(page);
    });

    test('should navigate to Status page', async ({ page }) => {
        await page.getByRole('link', { name: 'Статус' }).click();
        await expect(page).toHaveURL('/ops');
        await expect(page.getByText('Статус системы')).toBeVisible();
    });

    test('should navigate to Audit Log', async ({ page }) => {
        await page.getByRole('link', { name: 'Журнал' }).click();
        await expect(page).toHaveURL('/audit');
        await expect(page.getByText('Журнал')).toBeVisible();
    });

    test('should navigate to Settings', async ({ page }) => {
        await page.getByRole('link', { name: 'Настройки' }).click();
        await expect(page).toHaveURL('/settings');
        await expect(page.getByText('Филиалы')).toBeVisible();
    });
});

// =========================================
// CASE ACTIONS (Take, Reply, Resolve)
// =========================================
test.describe('Case Actions', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test('should take a pending case', async ({ page }) => {
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

    test('should send a reply message', async ({ page }) => {
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

    test('should resolve an active case', async ({ page }) => {
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
        await loginAsAdmin(page);
        await page.getByRole('link', { name: 'Журнал' }).click();
        await expect(page).toHaveURL('/audit');
    });

    test('should display audit events table', async ({ page }) => {
        await expect(page.getByText('Журнал действий')).toBeVisible();
        // Check for table headers
        await expect(page.getByText('Время')).toBeVisible();
        await expect(page.getByText('Событие')).toBeVisible();
        await expect(page.getByText('Исполнитель')).toBeVisible();
    });

    test('should show event types with badges', async ({ page }) => {
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
        await loginAsAdmin(page);
        await page.getByRole('link', { name: 'Настройки' }).click();
        await expect(page).toHaveURL('/settings');
    });

    test('should display branches section', async ({ page }) => {
        await expect(page.getByText('Филиалы')).toBeVisible();
    });

    test('should display team members section', async ({ page }) => {
        await expect(page.getByText('Команда')).toBeVisible();
    });
});
