import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/phase5f", workers: 1, timeout: 1800000,
  expect: {timeout: 90000},
  use: {baseURL:"http://127.0.0.1:3100",headless:true,navigationTimeout:90000},
  webServer: [
    {command:"uv run --no-project --python 3.12 --with fastapi --with uvicorn --with pillow --with numpy --with python-multipart python -B tests/phase5f_server.py",cwd:"../backend",url:"http://127.0.0.1:3101/health",timeout:120000},
    {command:"npm run start -- --hostname 127.0.0.1 --port 3100",url:"http://127.0.0.1:3100",timeout:120000,env:{SMART_WARDROBE_BUILD_DIR:".next-phase5f-build",SMART_WARDROBE_BACKEND_URL:"http://127.0.0.1:3101"}},
  ],
});
