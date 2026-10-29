import { defineConfig } from "@playwright/test";
export default defineConfig({
  outputDir: ".next-integration-run/decision-playwright-artifacts",
  testDir:"./tests/phase5f",testMatch:"decision*.spec.ts",workers:1,timeout:3600000,
  expect:{timeout:120000},use:{baseURL:"http://127.0.0.1:3200",headless:true,trace:"retain-on-failure"},
  webServer:[
    {command:"uv run --no-project --python 3.12 --with fastapi==0.146.0 --with uvicorn --with pillow==13.0.0 --with numpy==2.5.4 --with python-multipart==0.0.32 python -B tests/assistant_decision_server.py",cwd:"../backend",url:"http://127.0.0.1:3201/health",timeout:120000,reuseExistingServer:false},
    {command:"npm run start -- --hostname 127.0.0.1 --port 3200",url:"http://127.0.0.1:3200",timeout:120000,reuseExistingServer:false,env:{SMART_WARDROBE_BUILD_DIR:".next-integration-run/decision-production"}},
  ],
});
