import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", workers: 1, timeout: 120000,
  testIgnore: "**/phase5f/**",
  expect: { timeout: 30000 },
  use: { baseURL: "http://127.0.0.1:3100", headless: true, trace: "retain-on-failure", navigationTimeout: 90000 },
  webServer: [
    { command: "uv run --no-project --python 3.12 --with fastapi --with uvicorn --with pillow --with numpy --with python-multipart python -B tests/frontend_integration_server.py", cwd: "../backend", url: "http://127.0.0.1:3101/health", timeout: 120000, reuseExistingServer: false },
    { command: "npm run dev -- --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100", timeout: 600000, reuseExistingServer: false, env: { SMART_WARDROBE_BACKEND_URL: "http://127.0.0.1:3101", SMART_WARDROBE_BUILD_DIR: ".next-browser-verification" } },
  ],
});
