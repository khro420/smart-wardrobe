import { defineConfig } from "@playwright/test";

const baseURL = process.env.SW_INTEGRATION_URL;
if (!baseURL) throw new Error("Set SW_INTEGRATION_URL to an owned disposable full-feature server.");
export default defineConfig({
  testDir: "./tests/integration", workers: 1, retries: 0, timeout: 180000,
  expect: { timeout: 15000 },
  outputDir: "test-results/integrated",
  use: { baseURL, channel: "chrome", headless: true, trace: "retain-on-failure" },
});
