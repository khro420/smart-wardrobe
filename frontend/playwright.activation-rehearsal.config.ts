import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
// The local supervisor owns actual app.main and production Next processes.
export default defineConfig({ ...base, webServer: undefined, testIgnore: [],
  testMatch: "activation-rehearsal.spec.ts", timeout: 180000,
});
