import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests for Al-Hasade.
 *
 * Prerequisites:
 *   docker compose up -d          # start dev stack
 *   cd e2e && npx playwright test # run tests
 *
 * Or from CI:
 *   npx playwright install --with-deps chromium
 *   npx playwright test
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  retries: 1,
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    locale: "he-IL",
    // RTL direction
    contextOptions: { locale: "he-IL" },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: undefined, // Assumes docker compose is already running
});
