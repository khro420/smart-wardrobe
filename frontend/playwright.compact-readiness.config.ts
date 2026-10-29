import {defineConfig} from '@playwright/test';
import base from './playwright.compact-integrated.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,
  testMatch:['compact-integrated.spec.ts','compact-readiness.spec.ts'],
  outputDir:'.next-integration-run/compact-readiness-artifacts',
  webServer:servers.map((server,index)=>index===1?{...server,
    env:{...server.env,SMART_WARDROBE_BUILD_DIR:'.next-integration-run/compact-readiness-production'}}:server),
});
