import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
// A disposable supervisor owns the real app.main and production Next processes.
export default defineConfig({ ...base, webServer: undefined, testIgnore: [],
  testMatch: "functional-closure.spec.ts", timeout: 180000,
});
