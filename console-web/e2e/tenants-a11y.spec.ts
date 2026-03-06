import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import {
    loginThroughKeycloak,
    shouldStayOnBaseOrigin,
} from "./support/keycloak-auth";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPORT_ARTIFACTS_DIR = path.resolve(
    __dirname,
    "..",
    "..",
    "docs",
    "REPORTS",
    "artifacts",
    "2026-02-20-tenants-a11y",
);
const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const stayOnBaseOrigin = shouldStayOnBaseOrigin(baseURL);
const loginUser = process.env.E2E_USERNAME ?? "admin";
const loginPassword = process.env.E2E_PASSWORD ?? "admin";
const failOnThresholds = process.env.A11Y_FAIL_ON_THRESHOLDS === "1";
const deterministicAuthEnabled = process.env.E2E_DETERMINISTIC_AUTH !== "0";
const TENANTS_FIXTURE_COMPANY_ID = "11111111-1111-4111-8111-111111111111";
const TENANTS_FIXTURE_CLIENT_ID = "22222222-2222-4222-8222-222222222222";
const TENANTS_FIXTURE_BRANCH_ID = "33333333-3333-4333-8333-333333333333";
const TENANTS_FIXTURE_AGENT_ID = "44444444-4444-4444-8444-444444444444";
const TENANTS_FIXTURE_NOW = "2026-02-22T12:00:00.000Z";
let resolvedBaseURL = baseURL;

type AxeImpact = "minor" | "moderate" | "serious" | "critical";

type AxeSummary = {
    url: string;
    timestamp: string;
    violations_total: number;
    impacts: Record<AxeImpact, number>;
    violations: Array<{
        id: string;
        impact: AxeImpact | null;
        description: string;
        help: string;
        nodes: number;
        targets: string[];
    }>;
};

function urlPathPattern(pathValue: string) {
    return new RegExp(`${pathValue.replace(/\//g, "\\/")}(\\?|$)`);
}

function toJsonResponse(route: import("@playwright/test").Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
    });
}

function buildTenantsFixtureBundle() {
    const company = {
        id: TENANTS_FIXTURE_COMPANY_ID,
        name: "Demo Holding",
        billing_info: {},
    };
    const client = {
        id: TENANTS_FIXTURE_CLIENT_ID,
        slug: "demo_salon",
        name: "Demo Salon",
        status: "active",
        company_id: TENANTS_FIXTURE_COMPANY_ID,
        company_name: "Demo Holding",
        lifecycle_state: "active",
        payment_status: "confirmed",
        commercial_state: "payment_confirmed",
        service_state: "ok",
        owner_name: "Owner",
        next_action: "monitor_sla_and_quality",
        total_branches: 1,
        active_branches: 1,
        degraded_branches: 0,
        go_live_ready_branches: 1,
        reference_branch_ids: [TENANTS_FIXTURE_BRANCH_ID],
        reference_branch_reason: "active_live_signals",
    };
    const branch = {
        id: TENANTS_FIXTURE_BRANCH_ID,
        client_id: TENANTS_FIXTURE_CLIENT_ID,
        company_id: TENANTS_FIXTURE_COMPANY_ID,
        slug: "almaty_downtown",
        name: "Almaty Downtown",
        is_active: true,
        instance_id: "instance-demo-01",
        telegram_chat_id: "-100100200300",
        phone: "+77001234567",
        knowledge_tag: "demo_salon",
        timezone: "Asia/Almaty",
        go_live_state: "approved",
        go_live_waiver_active: false,
        go_live_allowed: true,
    };
    const fleetSummary = {
        total_companies: 1,
        total_clients: 1,
        active_clients: 1,
        onboarding_clients: 0,
        archived_clients: 0,
        paused_clients: 0,
        go_live_ready_clients: 0,
        degraded_clients: 0,
        payment_pending_clients: 0,
        payment_confirmed_clients: 1,
        lifecycle_counts: {
            lead: 0,
            contracting: 0,
            onboarding: 0,
            go_live_ready: 0,
            active: 1,
            paused: 0,
            archived: 0,
        },
        payment_counts: {
            pending: 0,
            confirmed: 1,
            rejected: 0,
            unknown: 0,
        },
        service_counts: {
            ok: 1,
            degraded: 0,
            attention: 0,
        },
        onboarding_throughput: {
            window_hours: 720,
            approved_branches_total: 1,
            first_pass_approved_branches: 1,
            time_to_go_live_median_hours: 12.0,
            blocker_age_p95_hours: 4.0,
            first_pass_go_live_rate_pct: 100.0,
            incident_reopen_rate_24h_pct: 0.0,
        },
    };
    const attention = {
        generated_at: TENANTS_FIXTURE_NOW,
        stale_after_minutes: 60,
        summary: {
            active_clients_total: 1,
            clients_with_attention: 0,
            high_risk_clients: 0,
            medium_risk_clients: 0,
            low_risk_clients: 0,
            stale_branches_total: 0,
            integration_error_branches_total: 0,
            integration_warn_branches_total: 0,
            outbox_failed_24h_total: 0,
            pending_handovers_total: 0,
        },
        items: [],
    };
    return {
        company,
        client,
        branch,
        fleetSummary,
        attention,
    };
}

function buildDeterministicSessionPayload() {
    return {
        user: {
            name: "Platform Admin",
            email: "platform-admin@truffles.local",
        },
        expires: "2099-01-01T00:00:00.000Z",
        accessToken: "e2e-platform-admin-token",
    };
}

async function mockDeterministicAuthSession(page: import("@playwright/test").Page) {
    await page.route("**/api/auth/session**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, buildDeterministicSessionPayload());
    });
    await page.route("**/api/auth/csrf", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { csrfToken: "e2e-csrf" });
    });
    await page.route("**/api/auth/providers", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            keycloak: {
                id: "keycloak",
                name: "Keycloak",
                type: "oauth",
                signinUrl: `${baseURL}/api/auth/signin/keycloak`,
                callbackUrl: `${baseURL}/api/auth/callback/keycloak`,
            },
        });
    });
}

async function mockTenantsDeterministicApis(page: import("@playwright/test").Page) {
    const fixture = buildTenantsFixtureBundle();
    await page.route("**/api/proxy/me", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        const headers = route.request().headers();
        const selectedCompanyId = headers["x-company-id"] || "";
        const selectedClientId = headers["x-client-id"] || "";
        const selectedBranchId = headers["x-branch-id"] || "";
        const selectedClient = selectedClientId === fixture.client.id ? fixture.client : null;
        const selectedCompany = selectedCompanyId === fixture.company.id ? fixture.company.id : null;
        const selectedBranch = selectedBranchId === fixture.branch.id ? fixture.branch.id : null;
        await toJsonResponse(route, {
            agent: {
                id: TENANTS_FIXTURE_AGENT_ID,
                name: "Platform Admin",
                role: "platform_admin",
                client_id: fixture.client.id,
                branch_id: null,
                is_active: true,
            },
            client: selectedClient,
            branches: [fixture.branch],
            clients: [fixture.client],
            companies: [fixture.company],
            company_selection_required: false,
            selection_required: false,
            branch_selection_required: false,
            selected_company_id: selectedCompany,
            selected_branch_id: selectedBranch,
        });
    });
    await page.route("**/api/proxy/admin/companies**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.company],
            cursor: null,
            has_more: false,
        });
    });
    await page.route("**/api/proxy/admin/clients**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.client],
            cursor: null,
            has_more: false,
            summary: fixture.fleetSummary,
        });
    });
    await page.route("**/api/proxy/admin/branches**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.branch],
            cursor: null,
            has_more: false,
        });
    });
    await page.route("**/api/proxy/admin/tenants/portfolio**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            generated_at: TENANTS_FIXTURE_NOW,
            clients: {
                items: [fixture.client],
                cursor: null,
                has_more: false,
                summary: fixture.fleetSummary,
            },
            fleet_attention: fixture.attention,
        });
    });
    await page.route("**/api/proxy/admin/tenants/company-cockpit**", async (route) => {
        if (route.request().method() !== "GET") {
            await route.fallback();
            return;
        }
        const url = new URL(route.request().url());
        const selectedClientId = url.searchParams.get("client_id");
        await toJsonResponse(route, {
            generated_at: TENANTS_FIXTURE_NOW,
            company_id: fixture.company.id,
            selected_client_id: selectedClientId || null,
            clients: {
                items: [fixture.client],
                cursor: null,
                has_more: false,
                summary: null,
            },
            branches: {
                items: [fixture.branch],
                cursor: null,
                has_more: false,
            },
        });
    });
}

async function selectOptionIfNeeded(selector: import("@playwright/test").Locator) {
    if (!(await selector.isVisible().catch(() => false))) {
        return false;
    }
    const currentValue = await selector.inputValue();
    if (currentValue) {
        return true;
    }
    const options = selector.locator("option");
    const optionCount = await options.count();
    if (optionCount < 2) {
        return false;
    }
    const value = await options.nth(1).getAttribute("value");
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue("");
    return true;
}

async function selectFromGate(
    page: import("@playwright/test").Page,
    selectTestId: string,
    confirmTestId: string,
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

async function resolveSelectionGate(page: import("@playwright/test").Page) {
    if (await selectFromGate(page, "company-select", "company-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }
    if (await selectFromGate(page, "client-select", "client-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }
    if (await selectFromGate(page, "branch-select", "branch-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }

    await selectOptionIfNeeded(page.getByTestId("context-company-select"));
    await selectOptionIfNeeded(page.getByTestId("context-client-select"));
    await selectOptionIfNeeded(page.getByTestId("context-branch-select"));
}

async function gotoConsoleRoot(page: import("@playwright/test").Page) {
    await page.goto(resolvedBaseURL, { waitUntil: "domcontentloaded" });
}

function keycloakAuthOptions() {
    return {
        baseURL,
        consoleHostPattern,
        keycloakHostPattern,
        stayOnBaseOrigin,
        authWaitTimeoutMs: 15000,
        onResolvedOrigin: (origin: string) => {
            resolvedBaseURL = origin;
        },
    };
}

async function loginWithSharedHelper(page: import("@playwright/test").Page) {
    await loginThroughKeycloak(page, {
        ...keycloakAuthOptions(),
        loginUser,
        loginPassword,
    });
}

async function ensureLoggedIn(page: import("@playwright/test").Page) {
    if (deterministicAuthEnabled) {
        await mockDeterministicAuthSession(page);
        resolvedBaseURL = baseURL;
        return;
    }
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId("login-button");
    const logoutButton = page.getByTestId("logout-button");
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginWithSharedHelper(page);
        await gotoConsoleRoot(page);
    }
    await resolveSelectionGate(page);
}

async function openTenants(page: import("@playwright/test").Page): Promise<boolean> {
    const navTenants = page.getByTestId("nav-tenants");
    if (await navTenants.isVisible().catch(() => false)) {
        await navTenants.click();
    } else {
        await page.goto(`${resolvedBaseURL}/tenants`, { waitUntil: "domcontentloaded" });
    }
    await expect(page).toHaveURL(urlPathPattern("/tenants"));
    const tenantsPage = page.getByTestId("tenants-page");
    const title = page.getByTestId("tenants-title");
    const deniedHeading = page.getByRole("heading", { name: "Нет доступа" });

    // Wait for a definitive tenants outcome to avoid flaky early skips on slow UI hydration.
    await Promise.race([
        tenantsPage.waitFor({ state: "visible", timeout: 15000 }).catch(() => undefined),
        title.waitFor({ state: "visible", timeout: 15000 }).catch(() => undefined),
        deniedHeading.waitFor({ state: "visible", timeout: 15000 }).catch(() => undefined),
    ]);

    if (await tenantsPage.isVisible().catch(() => false)) {
        return true;
    }
    if (await title.isVisible().catch(() => false)) {
        return true;
    }
    if (await deniedHeading.isVisible().catch(() => false)) {
        return false;
    }
    return false;
}

function summarizeAxe(result: Awaited<ReturnType<AxeBuilder["analyze"]>>, url: string): AxeSummary {
    const impacts: Record<AxeImpact, number> = {
        minor: 0,
        moderate: 0,
        serious: 0,
        critical: 0,
    };
    for (const violation of result.violations) {
        if (violation.impact && violation.impact in impacts) {
            impacts[violation.impact as AxeImpact] += 1;
        }
    }
    return {
        url,
        timestamp: new Date().toISOString(),
        violations_total: result.violations.length,
        impacts,
        violations: result.violations.map((violation) => ({
            id: violation.id,
            impact: violation.impact as AxeImpact | null,
            description: violation.description,
            help: violation.help,
            nodes: violation.nodes.length,
            targets: violation.nodes.map((node) => JSON.stringify(node.target)),
        })),
    };
}

async function captureTenantsArtifacts(
    page: import("@playwright/test").Page,
    variant: "desktop" | "mobile",
): Promise<AxeSummary> {
    fs.mkdirSync(REPORT_ARTIFACTS_DIR, { recursive: true });
    await page.waitForTimeout(400);

    const screenshotPath = path.join(REPORT_ARTIFACTS_DIR, `tenants-${variant}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const axeResult = await new AxeBuilder({ page }).analyze();
    const summary = summarizeAxe(axeResult, page.url());
    const summaryPath = path.join(REPORT_ARTIFACTS_DIR, `tenants-${variant}-axe.json`);
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf-8");

    if (failOnThresholds) {
        expect(summary.impacts.critical, `${variant} critical axe violations`).toBe(0);
        expect(summary.impacts.serious, `${variant} serious axe violations`).toBe(0);
    }
    return summary;
}

test.describe("Tenants a11y evidence", () => {
    test.describe.configure({ timeout: 120000 });

    test.beforeEach(async ({ page }) => {
        if (deterministicAuthEnabled) {
            await mockTenantsDeterministicApis(page);
        }
        await ensureLoggedIn(page);
        if (deterministicAuthEnabled) {
            await page.goto(resolvedBaseURL, { waitUntil: "domcontentloaded" });
            await resolveSelectionGate(page);
        } else {
            await gotoConsoleRoot(page);
        }
        const tenantsAvailable = await openTenants(page);
        expect(tenantsAvailable).toBe(true);
    });

    test("desktop snapshot + axe @smoke", async ({ page }) => {
        await expect(page.getByTestId("tenants-workspace-guide")).toBeVisible();
        const summary = await captureTenantsArtifacts(page, "desktop");
        test.info().annotations.push({
            type: "a11y-desktop",
            description: `critical=${summary.impacts.critical}, serious=${summary.impacts.serious}`,
        });
    });

    test.describe("mobile", () => {
        test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

        test("mobile snapshot + axe @smoke", async ({ page }) => {
            await expect(page.getByTestId("tenants-workspace-guide")).toBeVisible();
            const summary = await captureTenantsArtifacts(page, "mobile");
            test.info().annotations.push({
                type: "a11y-mobile",
                description: `critical=${summary.impacts.critical}, serious=${summary.impacts.serious}`,
            });
        });
    });
});
