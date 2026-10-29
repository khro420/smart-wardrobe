import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/phase5f",
  testMatch: ["everyday-context.spec.ts", "professional-academic-context.spec.ts", "date-dinner-context.spec.ts", "general-context.spec.ts", "layout-integration-regression.spec.ts", "durable-logout.spec.ts"],
  workers: 1, retries: 0, timeout: 90000, expect: { timeout: 15000 },
  use: { channel: "chrome", headless: true, viewport: { width: 1280, height: 960 }, baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
});
