import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/phase5f",
  testMatch: ["automatic-admission.spec.ts", "owner-style-admission.spec.ts", "everyday-context.spec.ts", "date-dinner-context.spec.ts", "general-context.spec.ts", "professional-academic-context.spec.ts", "layout-integration-regression.spec.ts", "durable-logout.spec.ts"],
  workers: 1, retries: 0, timeout: 90000, expect: { timeout: 15000 },
  outputDir: process.env.SMART_WARDROBE_CLOSURE_EVIDENCE + "/browser-artifacts",
  use: { channel: "chrome", headless: true, baseURL: "http://127.0.0.1:3100", viewport: { width: 1280, height: 960 }, trace: "retain-on-failure" },
});
