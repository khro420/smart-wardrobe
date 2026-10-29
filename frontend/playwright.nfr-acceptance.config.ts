import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({ ...base, webServer: undefined, testIgnore: [],
  testMatch: "nfr-acceptance.spec.ts", timeout: 900000,
  use: { ...base.use, viewport: { width: 1280, height: 960 } },
});
