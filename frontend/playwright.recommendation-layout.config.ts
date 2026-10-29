import { defineConfig } from "@playwright/test";
const channel = process.env.SMART_WARDROBE_J20_BROWSER;
if (channel !== "chrome" && channel !== "msedge") throw new Error("Select the actual installed browser channel.");
export default defineConfig({
  testDir: "./tests/phase5f", testMatch: ["layout-integration-regression.spec.ts", "recommendation-layout.spec.ts"],
  workers: 1, retries: 0, timeout: 180000, expect: { timeout: 15000 },
  use: { channel, headless: true, viewport: { width: 1280, height: 960 }, baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
});
