import { defineConfig } from "@playwright/test";
import base from "./playwright.integration.config";
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({ ...base, testMatch:"**/phase5f/scoring-suitability.spec.ts", testIgnore:[], webServer:servers.map((server,index)=>index===0?{...server,command:server.command.replace("frontend_integration_server.py","scoring_suitability_server.py")}:{...server,env:{...server.env,SMART_WARDROBE_BUILD_DIR:".next-integration-run/scoring-suitability-browser"}}) });
