import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];
const production = process.env.SMART_WARDROBE_QUOTA_PRODUCTION === "true";
export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: "wardrobe-quota.spec.ts",
  webServer: servers.map((server, index) => index === 0 ? {
    ...server,
    command: "uv run --offline --no-project --python 3.12 --with fastapi==0.146.0 --with uvicorn==0.54.0 --with pillow==13.0.0 --with numpy==2.5.4 --with python-multipart==0.0.32 python -B tests/frontend_quota_server.py",
  } : {
    ...server,
    command: production ? "npm run start -- --hostname 127.0.0.1 --port 3100" : server.command,
    env: { ...server.env, SMART_WARDROBE_BUILD_DIR: production ? ".next-integration-run/wardrobe-quota-production" : ".next-integration-run/wardrobe-quota-browser" },
  }),
});
