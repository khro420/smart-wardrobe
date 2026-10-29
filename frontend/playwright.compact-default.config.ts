import {defineConfig} from '@playwright/test';
import base from './playwright.compact-integrated.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,
  testMatch:['compact-integrated.spec.ts','compact-default.spec.ts'],
  outputDir:'.next-integration-run/compact-default-artifacts',
  webServer:servers.map((server,index)=>index===1?{...server,
    env:{...server.env,SMART_WARDROBE_BUILD_DIR:'.next-integration-run/compact-default-production'}}:server),
});
