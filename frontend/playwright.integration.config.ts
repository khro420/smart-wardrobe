import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Intentional test configuration. Generated files stay under the ignored scratch
// tree; the normal suite, server fixtures, feature flags and test limits are reused.
const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];
export default defineConfig({
  ...base,
  webServer: servers.map((server, index) => index === 1 ? {
    ...server,
    env: { ...server.env, SMART_WARDROBE_BUILD_DIR: ".next-integration-run/history-ui-browser" },
  } : server),
});
