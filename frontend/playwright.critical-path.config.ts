import { defineConfig } from "@playwright/test";
import base from "./playwright.decision.config";
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,testMatch:"critical-path.spec.ts",outputDir:".next-integration-run/critical-path-artifacts",
  webServer:servers.map((server,index)=>index===0?{...server,
    command:"uv run --no-project --python 3.12 --with fastapi==0.146.0 --with uvicorn --with pillow==13.0.0 --with numpy==2.5.4 --with python-multipart==0.0.32 python -B tests/assistant_critical_path_server.py"}:{...server,env:{...server.env,SMART_WARDROBE_BUILD_DIR:'.next-integration-run/critical-path-production'}})});
