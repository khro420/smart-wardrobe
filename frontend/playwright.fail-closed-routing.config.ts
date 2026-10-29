import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
// The isolated supervisor owns actual application processes and production Next.
export default defineConfig({ ...base, webServer: undefined, testIgnore: [],
  testMatch: "fail-closed-routing.spec.ts", timeout: 180000,
});
