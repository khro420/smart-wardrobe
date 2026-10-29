// J-6: isolated explicit profile comparison; existing loopback-only selector, no production configuration changes.
import {test,expect} from '@playwright/test';
import {existsSync,mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const api='http://127.0.0.1:3201';
const deferred='compatibility_deferred',decision='experimental_compatibility_decision_v1';


// Normalise executor provenance for stable within-profile fingerprints.
function semanticProvenance(raw:Record<string,unknown>){
  const value={...raw};
  if(value.assistant_execution_selection){
    delete value.assistant_execution_selection;
    if(value.scoring_profile===decision)value.scorer_implementation='prepared-decision-1.0.0';
  }
  return value;
}


test('bounded suitability performance comparison',async({page,request})=>{
  test.skip(process.env.SMART_WARDROBE_SCORING_SANITY!=='true','Explicit long benchmark opt-in.');
  const records:Record<string,unknown>[]=[];
  const metadata=await(await request.get(api+'/_test/workloads')).json();
  expect(metadata.profile).toBe(deferred);
  const label=process.env.SMART_WARDROBE_COMPACT_RUN_LABEL??'';
  if(!/^[a-z0-9-]*$/.test(label))throw new Error('Invalid evidence run label');
  const output=resolve('../storage/verification/phase5f2e3j8/performance-sanity'+(process.env.SMART_WARDROBE_COMPACT_MULTI==='true'?'-multi':'')+(process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true'?'-diagnostic':'')+(label?'-'+label:'')+'.json');
  if(existsSync(output))throw new Error('Refusing to overwrite retained benchmark evidence: '+output);
  mkdirSync(resolve(output,'..'),{recursive:true});
  const collection:{state:string;preflight:Record<string,unknown>[];consecutive_quiet_samples:number}={state:'preflight',preflight:[],consecutive_quiet_samples:0};
  const controls={version:'readiness-collection-controls-1.1.0',max_idle_cpu_percent:20,min_free_physical_kib:4*1024*1024,required_samples:3,settle_milliseconds:10000,max_preflight_milliseconds:120000,note:'Collection controls only; not an approved FYP acceptance baseline. All settling observations retained; no recommendation warm-up or user processes stopped.'};
  const save=()=>writeFileSync(output,JSON.stringify({metadata,records,collection,controls,instrumented:process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true',method:'J8:16 main submissions per arm plus four terminal checks after correction; frozen J7 data and J8 collection-plan.json. No reference performance matrix or formal NFR baseline. Every error retained. Proxy policy unchanged. Diagnostic instrumentation selected separately; profiler times never used for acceptance.'},null,2));
  save();
  // Let server startup settle; no recommendation warm-up is performed.
  await page.waitForTimeout(controls.settle_milliseconds);
  const qualifies=(sample:Record<string,unknown>)=>{
    const system=sample.system as Record<string,number>|undefined;
    return sample.available===true&&system!==undefined&&Number.isFinite(system.cpu_load_percent)
      &&system.cpu_load_percent<=controls.max_idle_cpu_percent
      &&system.free_physical_kib>=controls.min_free_physical_kib;
  };
  const preflightStarted=performance.now();
  while(collection.consecutive_quiet_samples<controls.required_samples&&performance.now()-preflightStarted<controls.max_preflight_milliseconds){
    const sample=await(await request.get(api+'/_test/resources')).json();
    collection.preflight.push(sample);
    collection.consecutive_quiet_samples=qualifies(sample)?collection.consecutive_quiet_samples+1:0;
    save();
    if(collection.consecutive_quiet_samples<controls.required_samples)await page.waitForTimeout(1000);
  }
  const quiet=collection.consecutive_quiet_samples>=controls.required_samples;
  collection.state=quiet?'running':'resource_blocked';save();
  if(!quiet)throw new Error('Resource preflight blocked controlled timings; retained observations are not an application regression or NFR result.');
  const fingerprints=new Map<string,string>();
  const plan=await(await request.get(api+'/_test/j7-plan')).json();
  const expected=JSON.parse(readFileSync(resolve('../storage/verification/phase5f2e3j7/expected-results.json'),'utf8'));
  const collectionPlan=JSON.parse(readFileSync(resolve('../storage/verification/phase5f2e3j8/collection-plan.json'),'utf8'));
  const schedule=label.includes('before')?collectionPlan.before:collectionPlan.after;
  const priorPath=resolve('../storage/verification/phase5f2e3j8/performance-sanity-j8-before-retry.json');
  const prior=label.includes('before')?undefined:JSON.parse(readFileSync(priorPath,'utf8'));
  for(const cell of schedule){
    const {workload:name,request:requestName,profile,layer}=cell;
    const text=plan.requests[requestName];
    const target=expected.find((x:{workload:string;request:string;profile:string})=>x.workload===name&&x.request===requestName&&x.profile===profile);
    expect(target).toBeTruthy();
    const login=await request.post(api+'/api/v1/account/login',{data:{email:`j7-${name}@example.test`,password:'Decision-test-password-123'}});
    expect(login.ok()).toBeTruthy();const token=(await login.json()).access_token,headers={Authorization:`Bearer ${token}`};
    for(let pair=0;pair<cell.repetitions;pair++){
      for(const arm of ['compact']){
        expect((await request.post(`${api}/_test/j7-select/${profile}/${requestName==='suitability'?'enabled':'disabled'}`)).ok()).toBeTruthy();
        const row:Record<string,unknown>={name,request:requestName,profile,layer,pair,arm};let key=crypto.randomUUID() as string;
        row.resources_before=await(await request.get(api+'/_test/resources')).json();
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
            if(received.status()>=500)throw new Error(`Proxy HTTP ${received.status()}: ${await received.text()}`);
            row.backend_seconds=Number(received.headers()['x-test-backend-seconds']);value=await received.json();
            if(target.status==='Selected')await expect(page.getByTestId('recommendation-result')).toBeVisible({timeout:240000});else await expect(page.locator('[role=alert]:not(#__next-route-announcer__)')).toBeVisible({timeout:240000});row.seconds=(performance.now()-started)/1000;
          }
          expect(value.outcome).toBe(target.status);row.error=null;
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
        expect(job.status).toBe(target.status);
        if(target.status==='Selected'){
          expect(job.provenance.assistant_execution_selection.engine).toBe('compact_exhaustive');expect(job.provenance.scoring_profile).toBe(profile);expect(job.candidate_count).toBe(target.counts.scored);
          expect(createHash('sha256').update(JSON.stringify(job.items.map((x:[string,string,number])=>[x[1],x[0]]))).digest('hex')).toBe(target.winner_id);
          const identity={items:job.items,score:job.score,provenance:semanticProvenance(job.provenance)};
          row.fingerprint=createHash('sha256').update(JSON.stringify(identity)).digest('hex');
          if(prior){const previous=prior.records.find((r:{name:string;request:string;profile:string})=>r.name===name&&r.request===requestName&&r.profile===profile);expect(row.fingerprint).toBe(previous.fingerprint);}
          const k=`${name}:${requestName}:${profile}`;if(fingerprints.has(k))expect(row.fingerprint).toBe(fingerprints.get(k));else fingerprints.set(k,row.fingerprint as string);
        }else{expect(job.id).toBeFalsy();expect(job.chat_id).toBeFalsy();}
        row.resources_after=await(await request.get(api+'/_test/resources')).json();
        row.auxiliary=await(await request.get(api+'/_test/diagnostics')).json();
        save();console.log(JSON.stringify({...row,job:undefined,auxiliary:undefined}));
      }
    }
  }
  collection.state='complete';save();
  expect(records.filter(r=>r.error)).toEqual([]);
  // Evidence collection succeeds despite retained transport failures; acceptance
  // is reported separately, never asserted by a five-second or error suppression.
});




