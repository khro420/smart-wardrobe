import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/phase5f", testMatch: ["durable-logout.spec.ts", "layout-integration-regression.spec.ts"],
  workers: 1, retries: 0, timeout: 90000, expect: { timeout: 15000 },
  use: { channel: "chrome", headless: true, viewport: { width: 1280, height: 960 },
    baseURL: "http://127.0.0.1:3100", trace: "off" },
});
