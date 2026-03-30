import { test, expect } from "@playwright/test";

/**
 * Happy-path E2E: Register → Login → Generate → View result.
 *
 * Requires the full stack running (docker compose up -d).
 * The Gemini API key must be configured for generation to succeed.
 */

const uniqueEmail = () => `e2e-${Date.now()}@test.local`;
const TEST_PASSWORD = "Test1234!";

test.describe("Happy path", () => {
  let email: string;

  test.beforeAll(() => {
    email = uniqueEmail();
  });

  test("register a new user", async ({ page }) => {
    await page.goto("/register");
    await expect(page).toHaveURL(/register/);

    await page.getByLabel(/אימייל|email/i).fill(email);
    await page.getByLabel(/סיסמה|password/i).first().fill(TEST_PASSWORD);
    // Some forms have a confirm-password field
    const confirmField = page.getByLabel(/אימות סיסמה|confirm/i);
    if (await confirmField.isVisible()) {
      await confirmField.fill(TEST_PASSWORD);
    }

    await page.getByRole("button", { name: /הרשמה|register/i }).click();

    // Should redirect to login or dashboard
    await expect(page).toHaveURL(/login|dashboard/, { timeout: 10_000 });
  });

  test("login with the new user", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel(/אימייל|email/i).fill(email);
    await page.getByLabel(/סיסמה|password/i).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: /כניסה|login/i }).click();

    // Should land on dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10_000 });
    // Dashboard should show the generation table or empty state
    await expect(
      page.getByText(/יחידות|לוח בקרה|dashboard/i)
    ).toBeVisible();
  });

  test("submit a generation request", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.getByLabel(/אימייל|email/i).fill(email);
    await page.getByLabel(/סיסמה|password/i).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: /כניסה|login/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10_000 });

    // Navigate to new generation
    await page.getByRole("link", { name: /יצירה חדשה|new/i }).click();
    await expect(page).toHaveURL(/generate/, { timeout: 5_000 });

    // Fill in generation form
    await page.getByLabel(/מקצוע|subject/i).fill("עברית");
    await page.getByLabel(/נושא|topic/i).fill("פועל ושם פעולה");
    await page.getByLabel(/כיתה|grade/i).fill("ד");

    // Submit
    await page.getByRole("button", { name: /יצירה|generate|שלח/i }).click();

    // Should navigate to generation detail or show pending status
    await expect(page).toHaveURL(/generations\/|dashboard/, {
      timeout: 15_000,
    });

    // Wait for status to appear (pending or processing)
    await expect(
      page.getByText(/ממתין|בתהליך|pending|processing|הושלם|completed/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("view generation detail page", async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.getByLabel(/אימייל|email/i).fill(email);
    await page.getByLabel(/סיסמה|password/i).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: /כניסה|login/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10_000 });

    // Click first generation row (if exists)
    const viewButton = page.getByRole("button", { name: /צפייה|view/i }).first();
    if (await viewButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await viewButton.click();
      // Should show detail page with status
      await expect(page).toHaveURL(/generations\//);
      await expect(
        page.getByText(/מקצוע|נושא|subject|topic|סטטוס|status/i)
      ).toBeVisible();
    }
  });
});
