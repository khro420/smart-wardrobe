import {defineConfig} from '@playwright/test';
import base from './playwright.score-certificate.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,testMatch:'suitability-hot-path.spec.ts',webServer:servers.map((s,i)=>i===0?{...s,command:s.command.replace('compact_integrated_server.py','suitability_hot_path_server.py'),env:{...s.env,SMART_WARDROBE_J8_FROZEN_FACTS:process.env.SMART_WARDROBE_J8_FROZEN_FACTS==='true'?'true':'false'}}:s)});
