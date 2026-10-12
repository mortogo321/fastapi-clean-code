import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: a real browser against the running stack
 * (browser → Next.js → FastAPI → PostgreSQL). Start it first, for example with
 * `ENV=development docker compose up --build -d` from the repository root.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
