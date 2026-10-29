import {test,expect} from '@playwright/test';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const api='http://127.0.0.1:3201';
const deferred='compatibility_deferred',decision='experimental_compatibility_decision_v1';
const text='Suggest an outfit with vintage style';

for(const profile of [deferred,decision])for(const name of ['pair','trio','dress','dress_outer','partial','unknown','zero']){
  test(`compact functional ${profile}: ${name}`,async({page,request})=>{
    expect((await request.post(`${api}/_test/compact/${profile}/compact`)).ok()).toBeTruthy();
    const login=await request.post(api+'/api/v1/account/login',{data:{email:`decision-${name}@example.test`,password:'Decision-test-password-123'}});
    const token=(await login.json()).access_token;await page.addInitScript(t=>sessionStorage.setItem('smart_wardrobe_access_token',t),token);
    await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill('Suggest an outfit'+(['trio','dress_outer'].includes(name)?' including outerwear':''));
    const response=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();const received=await response;const submission=received.request().postDataJSON();const value=await received.json();
    expect(value.outcome).toBe('Selected');await expect(page.getByTestId('recommendation-result')).toBeVisible();
    const expected=profile===deferred?'Ranked using request and supported preferences. Compatibility was not measured.':name==='dress'?'Default contribution for a single-piece outfit':name==='partial'?'Partially estimated compatibility contribution':name==='unknown'?'Default compatibility contribution due to unavailable evidence':'Rule-based compatibility';
    await expect(page.getByText(expected,{exact:true})).toBeVisible();await page.goto(`/history/${value.chat_id}`);await expect(page.getByText(expected,{exact:true})).toBeVisible();
    const other=await request.post(api+'/api/v1/account/login',{data:{email:'decision-empty@example.test',password:'Decision-test-password-123'}});
    expect((await request.get(`${api}/api/v1/chats/${value.chat_id}`,{headers:{Authorization:`Bearer ${(await other.json()).access_token}`}})).status()).toBe(404);
    const replay=await request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers:{Authorization:`Bearer ${token}`},data:submission});
    const restored=await replay.json();expect(restored.replayed).toBe(true);expect(restored.id).toBe(value.id);expect(restored.score_metadata).toEqual(value.score_metadata);
  });
}

test('matched paired actual HTTP and production browser evidence',async({page,request})=>{
  test.skip(process.env.SMART_WARDROBE_COMPACT_BENCHMARK!=='true','Explicit long benchmark opt-in.');
  const records:Record<string,unknown>[]=[];
  const metadata=await(await request.get(api+'/_test/workloads')).json();
  const label=process.env.SMART_WARDROBE_COMPACT_RUN_LABEL??'';
  if(!/^[a-z0-9-]*$/.test(label))throw new Error('Invalid evidence run label');
  const output=resolve('../storage/verification/phase5f2e3c3e/transport'+(process.env.SMART_WARDROBE_COMPACT_MULTI==='true'?'-multi':'')+(process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true'?'-diagnostic':'')+(label?'-'+label:'')+'.json');
  if(existsSync(output))throw new Error('Refusing to overwrite retained benchmark evidence: '+output);
  mkdirSync(resolve(output,'..'),{recursive:true});
  const save=()=>writeFileSync(output,JSON.stringify({metadata,records,instrumented:process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true',method:'Sequential matched profile/arm pairs, six pairs at 100/200, two at 20/50/stress. Every error retained. Proxy policy unchanged. Diagnostic instrumentation selected separately; profiler times never used for acceptance.'},null,2));
  const fingerprints=new Map<string,string>();
  const sizes=(process.env.SMART_WARDROBE_COMPACT_SIZES??'20,50,100,200,stress').split(',');
  const profiles=(process.env.SMART_WARDROBE_COMPACT_PROFILES??[deferred,decision].join(',')).split(',');
  const layers=(process.env.SMART_WARDROBE_COMPACT_LAYERS??'http,browser').split(',');
  if(profiles.some(p=>![deferred,decision].includes(p))||layers.some(l=>!['http','browser'].includes(l)))throw new Error('Unknown benchmark profile/layer');
  for(const name of sizes){
    const login=await request.post(api+'/api/v1/account/login',{data:{email:`decision-${name}@example.test`,password:'Decision-test-password-123'}});
    expect(login.ok()).toBeTruthy();const token=(await login.json()).access_token,headers={Authorization:`Bearer ${token}`};
    const pairs=process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true'?1:['100','200'].includes(name)?6:2;
    for(const profile of profiles)for(const layer of layers)for(let pair=0;pair<pairs;pair++){
      for(const arm of pair%2===0?['reference','compact']:['compact','reference']){
        expect((await request.post(`${api}/_test/compact/${profile}/${arm}`)).ok()).toBeTruthy();
        const row:Record<string,unknown>={name,profile,layer,pair,arm};let key=crypto.randomUUID() as string;
        let started=performance.now();
        try{
          let value;
          if(layer==='http'){
            const response=await request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers,data:{request_text:text,submission_key:key},timeout:240000});
            row.http_status=response.status();row.backend_seconds=Number(response.headers()['x-test-backend-seconds']);
            value=await response.json();row.seconds=(performance.now()-started)/1000;
          }else{
            await page.goto('/auth');await page.evaluate(t=>{sessionStorage.clear();sessionStorage.setItem('smart_wardrobe_access_token',t);},token);
            await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill(text);
            const response=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST',{timeout:240000});
            started=performance.now();await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
            const received=await response;key=received.request().postDataJSON().submission_key;
            row.http_status=received.status();row.http_seconds=(performance.now()-started)/1000;
            if(!received.ok())throw new Error(`Proxy HTTP ${received.status()}: ${await received.text()}`);
            row.backend_seconds=Number(received.headers()['x-test-backend-seconds']);value=await received.json();
            await expect(page.getByTestId('recommendation-result')).toBeVisible({timeout:240000});row.seconds=(performance.now()-started)/1000;
          }
          expect(value.outcome).toBe('Selected');row.error=null;
        }catch(error){row.error=String(error);row.seconds=(performance.now()-started)/1000;}
        // Read-only completion telemetry also handles late processing failures.
        const settle=performance.now();let job;
        do{
          job=await(await request.get(`${api}/_test/job/${key}`)).json();
          if(job.done)break;
          await page.waitForTimeout(1000);
        }while(performance.now()-settle<240000);
        row.job=job;row.drain_seconds=(performance.now()-settle)/1000;
        if(!job.done){records.push(row);save();throw new Error('Backend not settled; no overlapping timing trial permitted.');}
        records.push(row);save(); // Also retain unexpected terminal failures before assertions.
        expect(job.status).toBe('Selected');expect(job.candidate_count).toBe(metadata.workloads[name].candidate_count);
        const identity={items:job.items,score:job.score,provenance:job.provenance};
        row.fingerprint=createHash('sha256').update(JSON.stringify(identity)).digest('hex');
        const k=`${name}:${profile}`;if(fingerprints.has(k))expect(row.fingerprint).toBe(fingerprints.get(k));else fingerprints.set(k,row.fingerprint as string);
        row.auxiliary=await(await request.get(api+'/_test/diagnostics')).json();
        save();console.log(JSON.stringify({...row,job:undefined,auxiliary:undefined}));
      }
    }
  }
  // Evidence collection succeeds despite retained transport failures; acceptance
  // is reported separately, never asserted by a five-second or error suppression.
});

test('real timeout retry, atomic late failure and concurrent submissions',async({request,page})=>{
  test.skip(process.env.SMART_WARDROBE_COMPACT_SAFETY!=='true','Explicit long safety opt-in.');
  const login=await request.post(api+'/api/v1/account/login',{data:{email:'decision-200@example.test',password:'Decision-test-password-123'}});
  const headers={Authorization:`Bearer ${(await login.json()).access_token}`};
  const arm=process.env.SMART_WARDROBE_COMPACT_SAFETY_ARM??'compact';
  await request.post(`${api}/_test/compact/${decision}/${arm}`);
  const output=resolve(`../storage/verification/phase5f2e3c3e/timeout-safety-${arm}.json`);const records=[];
  for(const mode of ['success','failure']){
    const before=await(await request.get(api+'/_test/counts/200')).json();
    let key=(mode==='failure'?'late-failure-':'timeout-')+crypto.randomUUID();let transport;
    if(mode==='success'){
      await page.goto('/auth');await page.evaluate(t=>{sessionStorage.clear();sessionStorage.setItem('smart_wardrobe_access_token',t);},headers.Authorization.slice(7));
      await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill(text);
      if(arm==='compact'){
        await page.evaluate(()=>{
          const original=window.fetch;let once=true;
          window.fetch=(input,init)=>{
            if(once&&String(input).includes('pipeline=integrated')&&init?.method==='POST'){
              once=false;const controller=new AbortController();setTimeout(()=>controller.abort(),100);
              return original(input,{...init,signal:controller.signal});
            }
            return original(input,init);
          };
        });
        const sent=page.waitForRequest(r=>r.url().includes('pipeline=integrated')&&r.method()==='POST');const start=performance.now();
        await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();key=(await sent).postDataJSON().submission_key;
        await expect(page.getByRole('button',{name:'Retry same request',exact:true})).toBeVisible();
        transport={status:0,seconds:(performance.now()-start)/1000,reason:'controlled_browser_abort_100ms'};
      }else{
        const received=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST',{timeout:240000});const start=performance.now();
        await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();const response=await received;
        key=response.request().postDataJSON().submission_key;transport={status:response.status(),seconds:(performance.now()-start)/1000};
        expect(response.status()).toBe(500);await expect(page.getByRole('button',{name:'Retry same request',exact:true})).toBeVisible();
      }
    }else{
      const start=performance.now();const response=await request.post('http://127.0.0.1:3200/api/v1/recommendations?pipeline=integrated',{headers,data:{request_text:text,submission_key:key},timeout:240000});
      transport={status:response.status(),seconds:(performance.now()-start)/1000};expect([500,503]).toContain(response.status());
    }
    let job;const wait=performance.now();
    do{job=await(await request.get(`${api}/_test/job/${key}`)).json();if(job.done)break;await new Promise(r=>setTimeout(r,1000));}while(performance.now()-wait<240000);
    expect(job.done).toBe(true);expect(job.status).toBe(mode==='failure'?'PersistenceFailure':'Selected');
    const after=await(await request.get(api+'/_test/counts/200')).json();
    expect(after.nlp_chats-before.nlp_chats).toBe(mode==='failure'?0:1);expect(after.recommendations-before.recommendations).toBe(mode==='failure'?0:1);
    if(mode==='success'){
      const received=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST');
      await page.getByRole('button',{name:'Retry same request',exact:true}).click();const uiReplay=await received;
      expect(uiReplay.request().postDataJSON().submission_key).toBe(key);const uiValue=await uiReplay.json();expect(uiValue.replayed).toBe(true);expect(uiValue.id).toBe(job.id);
      await expect(page.getByTestId('recommendation-result')).toBeVisible();
      const replay=await request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers,data:{request_text:text,submission_key:key},timeout:240000});
      const result=await replay.json();expect(result.replayed).toBe(true);expect(result.id).toBe(job.id);expect(result.score_metadata).toEqual(job.score);
      expect(await(await request.get(api+'/_test/counts/200')).json()).toEqual(after);
    }
    records.push({mode,transport,job,before,after});writeFileSync(output,JSON.stringify(records,null,2));
  }
  const auth=await request.post(api+'/api/v1/account/login',{data:{email:'decision-100@example.test',password:'Decision-test-password-123'}});
  const h={Authorization:`Bearer ${(await auth.json()).access_token}`};const key=crypto.randomUUID();const start=performance.now();
  const beforeConcurrent=await(await request.get(api+'/_test/counts/100')).json();
  const responses=await Promise.all([0,1].map(()=>request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers:h,data:{request_text:text,submission_key:key},timeout:240000})));
  const values=await Promise.all(responses.map(r=>r.json()));expect(new Set(values.map(v=>v.id)).size).toBe(1);expect(values.every(v=>v.outcome==='Selected')).toBe(true);
  expect(values.map(v=>v.replayed).sort()).toEqual([false,true]);expect(values[0].score_metadata).toEqual(values[1].score_metadata);
  const afterConcurrent=await(await request.get(api+'/_test/counts/100')).json();
  expect(afterConcurrent.nlp_chats-beforeConcurrent.nlp_chats).toBe(1);expect(afterConcurrent.recommendations-beforeConcurrent.recommendations).toBe(1);
  records.push({mode:'concurrent_same_key',seconds:(performance.now()-start)/1000,values,before:beforeConcurrent,after:afterConcurrent});writeFileSync(output,JSON.stringify(records,null,2));
  const beforeDistinct=afterConcurrent;const distinctStart=performance.now();
  const distinct=await Promise.all([0,1].map(()=>request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers:h,data:{request_text:text,submission_key:crypto.randomUUID()},timeout:240000})));
  const distinctValues=await Promise.all(distinct.map(r=>r.json()));expect(new Set(distinctValues.map(v=>v.id)).size).toBe(2);expect(distinctValues.every(v=>v.outcome==='Selected')).toBe(true);
  const afterDistinct=await(await request.get(api+'/_test/counts/100')).json();
  expect(afterDistinct.nlp_chats-beforeDistinct.nlp_chats).toBe(2);expect(afterDistinct.recommendations-beforeDistinct.recommendations).toBe(2);
  records.push({mode:'concurrent_distinct_keys',seconds:(performance.now()-distinctStart)/1000,values:distinctValues,before:beforeDistinct,after:afterDistinct});writeFileSync(output,JSON.stringify(records,null,2));
});
