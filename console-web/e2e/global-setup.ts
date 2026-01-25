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

    const projectBaseURL = config.projects[0]?.use?.baseURL;
    const baseURL = process.env.PLAYWRIGHT_BASE_URL
        ?? (typeof projectBaseURL === "string" ? projectBaseURL : undefined)
        ?? "http://localhost:3000";
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
    await page.waitForURL(consoleHostPattern, { timeout: 30000 });
    await page.waitForLoadState("domcontentloaded");
    await page.locator('[data-testid="logout-button"]').waitFor({ state: "visible", timeout: 20000 });

    const envClientId = process.env.E2E_CLIENT_ID;
    const envBranchId = process.env.E2E_BRANCH_ID;
    const meData = await page.evaluate(async () => {
        const response = await fetch("/api/proxy/me");
        if (!response.ok) {
            return null;
        }
        return response.json();
    });
    const accessibleClients: string[] = [];
    if (meData?.clients?.length) {
        accessibleClients.push(...meData.clients.map((client: { id?: string }) => client.id).filter(Boolean));
    } else if (meData?.client?.id) {
        accessibleClients.push(meData.client.id as string);
    }

    let selectedClientId = envClientId ?? null;
    if (!selectedClientId || (accessibleClients.length && !accessibleClients.includes(selectedClientId))) {
        selectedClientId = accessibleClients[0] ?? null;
    }
    if (selectedClientId) {
        await page.evaluate((id) => {
            window.localStorage.setItem("console:client_id", id);
            window.localStorage.removeItem("console:branch_id");
        }, selectedClientId);
    }

    let selectedBranchId = envBranchId ?? null;
    if (selectedClientId) {
        const resolvedBranch = await page.evaluate(async (clientId) => {
            const response = await fetch("/api/proxy/me", {
                headers: { "X-Client-Id": clientId },
            });
            if (!response.ok) {
                return { required: false, ids: [] as string[] };
            }
            const data = await response.json();
            const ids = Array.isArray(data?.branches)
                ? data.branches.map((branch: { id?: string }) => branch.id).filter(Boolean)
                : [];
            return { required: !!data?.branch_selection_required, ids };
        }, selectedClientId);
        if (selectedBranchId && !resolvedBranch.ids.includes(selectedBranchId)) {
            selectedBranchId = null;
        }
        if (!selectedBranchId && resolvedBranch.required) {
            selectedBranchId = resolvedBranch.ids[0] ?? null;
        }
    }
    if (selectedBranchId) {
        await page.evaluate((id) => {
            window.localStorage.setItem("console:branch_id", id);
        }, selectedBranchId);
    }

    await page.context().storageState({ path: "e2e/.auth/state.json" });
    await browser.close();
}
