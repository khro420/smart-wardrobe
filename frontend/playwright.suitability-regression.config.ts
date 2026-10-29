import { defineConfig } from "@playwright/test";
import base from "./playwright.integration.config";
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,webServer:servers.map((server,index)=>index===1?{...server,env:{...server.env,SMART_WARDROBE_BUILD_DIR:".next-integration-run/suitability-disabled-regressions"}}:server)});
