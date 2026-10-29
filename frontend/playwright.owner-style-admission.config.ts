import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/phase5f", testMatch: "owner-style-admission.spec.ts",
  workers: 1, retries: 0, timeout: 90000, expect: { timeout: 15000 },
  outputDir: process.env.OWNER_STYLE_EVIDENCE + "/browser-artifacts",
  use: { channel: "chrome", headless: true, viewport: { width: 1280, height: 720 },
    baseURL: "http://127.0.0.1:3180", trace: "retain-on-failure" },
});
