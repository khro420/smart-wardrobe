import { defineConfig } from "@playwright/test";
import base from "./playwright.wardrobe-quota.config";
const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];
const performance = process.env.SMART_WARDROBE_RELEASE_PERFORMANCE === "true";
export default defineConfig({ ...base, timeout: performance ? 360000 : 120000,
  testMatch: performance ? "release-performance.spec.ts" : ["wardrobe-quota.spec.ts", "scoring-suitability.spec.ts", "release-configuration.spec.ts"],
  webServer: servers.map((server,index) => index === 0 ? { ...server,
    command: server.command.replace("frontend_quota_server.py", "release_configuration_server.py"),
    env: { ...server.env, SMART_WARDROBE_ASSISTANT_ENABLED: "true", SMART_WARDROBE_HOMEPAGE_ENABLED: "true",
      SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE: "compact_exhaustive",
      SMART_WARDROBE_ASSISTANT_SCORING_PROFILE: "experimental_compatibility_decision_v1",
      SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED: "true" },
  } : { ...server, command: "npm run start -- --hostname 127.0.0.1 --port 3100",
    env: { ...server.env, SMART_WARDROBE_BACKEND_URL: "http://127.0.0.1:3101", SMART_WARDROBE_BUILD_DIR: ".next-integration-run/wardrobe-quota-production" },
  }),
});
