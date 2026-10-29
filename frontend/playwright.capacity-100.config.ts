import {defineConfig} from '@playwright/test';
import base from './playwright.score-certificate.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer!];
export default defineConfig({...base,testMatch:'capacity-100.spec.ts',
  outputDir:'.next-integration-run/capacity-100-artifacts',
  webServer:servers.map((s,i)=>i===0?{...s,command:s.command.replace('compact_integrated_server.py','capacity_100_server.py').replace('uv run ','uv run --offline ')}:s)});
