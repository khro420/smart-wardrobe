import {test,expect} from "@playwright/test";
import {mkdirSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";

test("single-request HTTP stage diagnosis separated from repeated latency trials",async({request,page}) => {
  const auth=await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"load-200@example.test",password:"Isolated-test-password-123"}});
  const token=(await auth.json()).access_token,headers={Authorization:`Bearer ${token}`};
  const records: Record<string,unknown>[]=[];
  for(const flow of ["homepage","assistant"]){
    const start=performance.now();
    const response=await request.post(`http://127.0.0.1:3101/api/v1/recommendations${flow==="homepage"?"/homepage":"?pipeline=integrated"}`,{headers,timeout:120000,data:{submission_key:crypto.randomUUID(),...(flow==="assistant"?{request_text:"Suggest an outfit with vintage style"}:{})}});
    const value=await response.json(),elapsed=(performance.now()-start)/1000;
    expect(response.ok(),JSON.stringify(value)).toBeTruthy();
    const recorded=Object.values(value.timings as Record<string,number>).reduce((a,b)=>a+b,0);
    records.push({flow,garments:200,http_seconds:elapsed,production_stage_timers:value.timings,unaccounted_http_and_orchestration_seconds:elapsed-recorded,notes:"One diagnostic trial, not latency acceptance; residual includes authentication/DI/serialization/transport and un-timed orchestration, not pure HTTP."});
  }
  await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with vintage style");
  const cdp=await page.context().newCDPSession(page);
  await cdp.send("Performance.enable");
  const readMetrics=async()=>Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((entry:{name:string;value:number})=>[entry.name,entry.value]));
  const before=await readMetrics(),start=performance.now();
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  const after=await readMetrics();
  records.push({flow:"frontend_assistant",garments:200,wall_seconds:(performance.now()-start)/1000,cdp_delta_seconds:Object.fromEntries(["TaskDuration","ScriptDuration","LayoutDuration","RecalcStyleDuration"].map(name=>[name,after[name]-before[name]])),notes:"Chromium process metrics over submit-to-visible window; JS includes automation/application work, layout/style are browser work, not React component attribution. No latency acceptance claim from this diagnostic."});
  await cdp.detach();
  const output=resolve("../storage/verification/phase5f/http-stages.json");
  mkdirSync(resolve(output,".."),{recursive:true});writeFileSync(output,JSON.stringify(records,null,2));
  console.log(JSON.stringify(records));
});
