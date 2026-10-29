import {test,expect} from "@playwright/test";
import {existsSync,mkdirSync,readFileSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";
const backend="http://127.0.0.1:3201";
const profile=process.env.SMART_WARDROBE_ASSISTANT_SCORING_PROFILE??"compatibility_deferred";
const experimental=profile==="experimental_compatibility_decision_v1";
const labels={pair:"Rule-based compatibility",trio:"Rule-based compatibility",dress:"Default contribution for a single-piece outfit",dress_outer:"Rule-based compatibility",partial:"Partially estimated compatibility contribution",unknown:"Default compatibility contribution due to unavailable evidence",zero:"Rule-based compatibility"};

for(const [name,label] of Object.entries(labels)){
  test(`real Assistant and stored History display: ${name}`,async({page,request})=>{
    const login=await request.post(`${backend}/api/v1/account/login`,{data:{email:`decision-${name}@example.test`,password:"Decision-test-password-123"}});
    expect(login.ok()).toBeTruthy();const token=(await login.json()).access_token;
    await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),token);
    await page.goto("/assistant");
    const text="Suggest an outfit"+(["trio","dress_outer"].includes(name)?" including outerwear":"");
    await page.getByLabel("What would you like to wear?").fill(text);
    const response=page.waitForResponse(r=>r.url().includes("pipeline=integrated")&&r.request().method()==="POST");
    await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
    const value=await(await response).json();expect(value.outcome).toBe("Selected");
    await expect(page.getByTestId("recommendation-result")).toBeVisible();
    const wording=experimental?label:"Ranked using request and supported preferences. Compatibility was not measured.";
    await expect(page.getByText(wording,{exact:true})).toBeVisible();
    if(experimental&&name==="zero"){
      await page.getByText("Compatibility details",{exact:true}).click();
      await expect(page.getByText("Raw compatibility: 0%.",{exact:true})).toBeVisible();
    }
    await page.goto(`/history/${value.chat_id}`);
    await expect(page.getByText(wording,{exact:true})).toBeVisible();
    const screenshots=resolve('../storage/verification/phase5f2e3c3b/screenshots');
    mkdirSync(screenshots,{recursive:true});
    await page.screenshot({path:resolve(screenshots,`${profile}-${name}.png`),fullPage:true});
    const other=await request.post(`${backend}/api/v1/account/login`,{data:{email:"decision-empty@example.test",password:"Decision-test-password-123"}});
    expect((await request.get(`${backend}/api/v1/chats/${value.chat_id}`,{headers:{Authorization:`Bearer ${(await other.json()).access_token}`}})).status()).toBe(404);
  });
}

test("real controlled no-result and unsupported UI",async({page,request})=>{
  const login=await request.post(`${backend}/api/v1/account/login`,{data:{email:"decision-empty@example.test",password:"Decision-test-password-123"}});
  await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),(await login.json()).access_token);
  await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill('Suggest an outfit');
  await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
  await expect(page.getByRole('main').getByRole('alert')).toBeVisible();await expect(page.getByTestId('recommendation-result')).toHaveCount(0);
  await page.getByRole('button',{name:'New Chat',exact:true}).click();
  await page.getByLabel('What would you like to wear?').fill('Tell me a joke');
  await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
  await expect(page.getByRole('main').getByRole('alert')).toBeVisible();await expect(page.getByTestId('recommendation-result')).toHaveCount(0);
});

test("real unavailable server profile is a controlled UI failure",async({page,request})=>{
  test.skip(profile!=="invalid-test-profile","Separate deliberately invalid server configuration.");
  const login=await request.post(`${backend}/api/v1/account/login`,{data:{email:"decision-pair@example.test",password:"Decision-test-password-123"}});
  await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),(await login.json()).access_token);
  await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill('Suggest an outfit');
  const response=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
  const actual=await response;expect(actual.status()).toBe(422);expect((await actual.json()).outcome).toBe('ProfileUnavailable');
  await expect(page.getByRole('main').getByRole('alert')).toContainText('The approved scoring profile is unavailable.');
  await expect(page.getByTestId('recommendation-result')).toHaveCount(0);
});

test("repeated real service HTTP and production-browser measurements",async({page,request})=>{
  test.skip(process.env.SMART_WARDROBE_DECISION_BENCHMARK!=="true","Explicit benchmark opt-in; no fabricated timing results.");
  const metadata=await(await request.get(`${backend}/_test/workloads`)).json();
  const output=resolve(`../storage/verification/phase5f2e3c3b/latency-${profile}.json`);
  mkdirSync(resolve(output,'..'),{recursive:true});
  const prior=process.env.SMART_WARDROBE_DECISION_BENCHMARK_RESUME==='true'&&existsSync(output)?JSON.parse(readFileSync(output,'utf8')):null;
  if(prior){expect(prior.profile).toBe(profile);expect(prior.metadata.workloads).toEqual(metadata.workloads);}
  const records:Record<string,unknown>[]=prior?.records??[];
  const sessions=[...(prior?.sessions??[]),{started_at:new Date().toISOString(),resumed:!!prior,environment:metadata.environment}];
  const save=()=>writeFileSync(output,JSON.stringify({profile,metadata,records,sessions,method:"Three retained repetitions per workload/layer, including errors; max is observed tail, not p95. No warm-up or slow/error sample excluded. Resume retains previous records and restarts only the disposable server. The first pre-resume browser error timer included page setup; later errors are timed from submission. Backend completion after proxy errors is checked read-only before another trial."},null,2));
  for(const name of ['20','50','100','200','stress']){
    const login=await request.post(`${backend}/api/v1/account/login`,{data:{email:`decision-${name}@example.test`,password:"Decision-test-password-123"}});
    const token=(await login.json()).access_token,headers={Authorization:`Bearer ${token}`};
    for(const layer of ['service','http','browser'])for(let trial=0;trial<3;trial++){
      if(records.some(r=>r.name===name&&r.layer===layer&&r.trial===trial))continue;
      const start=performance.now();
      let observedStart=start,submissionKey:string|undefined;
      try{
        let value,backendSeconds:number|undefined,httpSeconds:number|undefined,serviceSeconds:number|undefined;
        if(layer==='service'){
          const response=await request.post(`${backend}/_test/service/${name}`,{timeout:180000});
          const result=await response.json();value=result.result;serviceSeconds=result.seconds;
        }else if(layer==='http'){
          submissionKey=crypto.randomUUID();
          const response=await request.post(`${backend}/api/v1/recommendations?pipeline=integrated`,{headers,data:{request_text:'Suggest an outfit with vintage style',submission_key:submissionKey},timeout:180000});
          backendSeconds=Number(response.headers()['x-test-backend-seconds']);httpSeconds=(performance.now()-start)/1000;value=await response.json();
        }else{
          await page.goto('/auth');await page.evaluate(value=>{sessionStorage.clear();sessionStorage.setItem('smart_wardrobe_access_token',value);},token);
          await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill('Suggest an outfit with vintage style');
          const response=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST',{timeout:180000});
          const submitted=performance.now();observedStart=submitted;await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
          const received=await response;httpSeconds=(performance.now()-submitted)/1000;
          submissionKey=received.request().postDataJSON().submission_key;
          if(!received.ok())throw new Error(`Production proxy HTTP ${received.status()}: ${await received.text()}`);
          backendSeconds=Number(received.headers()['x-test-backend-seconds']);value=await received.json();
          await expect(page.getByTestId('recommendation-result')).toBeVisible({timeout:180000});
          records.push({name,layer,trial,seconds:(performance.now()-submitted)/1000,http_seconds:httpSeconds,backend_seconds:backendSeconds,outcome:value.outcome,scored_count:value.provenance?.scored_count,error:null});
        }
        if(layer!=='service')expect(Number.isFinite(backendSeconds)).toBeTruthy();
        expect(value.outcome??value.status).toBe('Selected');
        expect(value.provenance.scored_count).toBe(metadata.workloads[name].candidate_count);
        if(layer!=='browser')records.push({name,layer,trial,seconds:serviceSeconds??httpSeconds,backend_seconds:backendSeconds,outcome:value.outcome??value.status,scored_count:value.provenance.scored_count,error:null});
      }catch(error){
        const failure:Record<string,unknown>={name,layer,trial,seconds:(performance.now()-observedStart)/1000,error:String(error)};
        records.push(failure);save();
        if(submissionKey){
          const drainStart=performance.now();let completed=false;
          while(performance.now()-drainStart<180000){
            const result=await(await request.get(`${backend}/_test/submission/${name}/${submissionKey}`)).json();
            if(result.complete){failure.eventual_backend_completion=result;completed=true;break;}
            await page.waitForTimeout(1000);
          }
          failure.drain_seconds=(performance.now()-drainStart)/1000;save();
          expect(completed,'Do not overlap a still-running failed transport request with another timing trial.').toBeTruthy();
        }
      }
      save();console.log(JSON.stringify(records.at(-1)));
    }
  }
  expect(records.filter(r=>r.error),'Retained real transport/application failures; see measurement JSON.').toHaveLength(0);
});
