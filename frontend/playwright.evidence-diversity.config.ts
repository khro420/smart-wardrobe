import {defineConfig} from '@playwright/test';
import base from './playwright.score-certificate.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,testMatch:'evidence-diversity.spec.ts',webServer:servers.map((s,i)=>i===0?{...s,command:s.command.replace('compact_integrated_server.py','evidence_diversity_server.py')}:s)});
