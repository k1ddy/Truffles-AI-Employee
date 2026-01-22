import { chromium, type FullConfig } from "@playwright/test";

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;

export default async function globalSetup(config: FullConfig) {
    if (process.env.E2E_USE_STORAGE_STATE !== "1") {
        return;
    }

    const username = process.env.E2E_USERNAME;
    const password = process.env.E2E_PASSWORD;
    if (!username || !password) {
        throw new Error("E2E_USERNAME and E2E_PASSWORD are required for storageState");
    }

    const baseURL = config.projects[0]?.use?.baseURL ?? "http://localhost:3000";
    const browser = await chromium.launch();
    const page = await browser.newPage();

    const signInUrl = `${baseURL}/api/auth/signin?callbackUrl=${encodeURIComponent(baseURL)}`;
    await page.goto(signInUrl, { waitUntil: "domcontentloaded" });
    const providerForm = page.locator('form[action*="keycloak"]');
    await providerForm.first().waitFor({ state: "visible", timeout: 15000 });
    const submitButton = providerForm.first().locator('button[type="submit"], input[type="submit"]').first();
    await submitButton.click();
    await page.waitForURL(keycloakHostPattern, { timeout: 20000 });
    await page.waitForSelector("#username", { timeout: 20000 });
    await page.fill("#username", username);
    await page.fill("#password", password);
    await page.click("#kc-login");
    await page.waitForURL(consoleHostPattern, { timeout: 15000 });

    await page.context().storageState({ path: "e2e/.auth/state.json" });
    await browser.close();
}
