import {defineConfig} from '@playwright/test';
import base from './playwright.compact.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,testMatch:'compact-integrated.spec.ts',outputDir:'.next-integration-run/compact-integrated-artifacts',
  webServer:servers.map((s,i)=>i===0?{...s,command:'uv run --no-project --python 3.12 --with fastapi==0.146.0 --with uvicorn==0.54.0 --with pillow==13.0.0 --with numpy==2.5.4 --with python-multipart==0.0.32 python -B tests/compact_integrated_server.py'}:{...s,env:{...s.env,SMART_WARDROBE_BUILD_DIR:'.next-integration-run/compact-integrated-production'}})});
