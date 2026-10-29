// J-6: isolated explicit profile comparison; existing loopback-only selector, no production configuration changes.
import {test,expect} from '@playwright/test';
import {existsSync,mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const api='http://127.0.0.1:3201';
const deferred='compatibility_deferred',decision='experimental_compatibility_decision_v1';
const text='Suggest an outfit with vintage style';

// Normalise executor provenance for stable within-profile fingerprints.
function semanticProvenance(raw:Record<string,unknown>){
  const value={...raw};
  if(value.assistant_execution_selection){
    delete value.assistant_execution_selection;
    if(value.scoring_profile===decision)value.scorer_implementation='prepared-decision-1.0.0';
  }
  return value;
}


test('scoring acceptance browser and HTTP sanity',async({page,request})=>{
  test.skip(process.env.SMART_WARDROBE_SCORING_SANITY!=='true','Explicit long benchmark opt-in.');
  const records:Record<string,unknown>[]=[];
  const metadata=await(await request.get(api+'/_test/workloads')).json();
  expect(metadata.profile).toBe(deferred);
  const label=process.env.SMART_WARDROBE_COMPACT_RUN_LABEL??'';
  if(!/^[a-z0-9-]*$/.test(label))throw new Error('Invalid evidence run label');
  const output=resolve('../storage/verification/phase5f2e3j6/performance-sanity'+(process.env.SMART_WARDROBE_COMPACT_MULTI==='true'?'-multi':'')+(process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true'?'-diagnostic':'')+(label?'-'+label:'')+'.json');
  if(existsSync(output))throw new Error('Refusing to overwrite retained benchmark evidence: '+output);
  mkdirSync(resolve(output,'..'),{recursive:true});
  const collection:{state:string;preflight:Record<string,unknown>[];consecutive_quiet_samples:number}={state:'preflight',preflight:[],consecutive_quiet_samples:0};
  const controls={version:'readiness-collection-controls-1.1.0',max_idle_cpu_percent:20,min_free_physical_kib:4*1024*1024,required_samples:3,settle_milliseconds:10000,max_preflight_milliseconds:120000,note:'Collection controls only; not an approved FYP acceptance baseline. All settling observations retained; no recommendation warm-up or user processes stopped.'};
  const save=()=>writeFileSync(output,JSON.stringify({metadata,records,collection,controls,instrumented:process.env.SMART_WARDROBE_COMPACT_DIAGNOSTICS==='true',method:'36 sequential compact submissions: three per size/profile/layer, 50/100/200, deferred and experimental, HTTP and browser. No reference performance matrix or formal NFR baseline. Every error retained. Proxy policy unchanged. Diagnostic instrumentation selected separately; profiler times never used for acceptance.'},null,2));
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
  const baseline=JSON.parse(readFileSync(resolve('../storage/verification/phase5f2e3j5/performance-sanity-j5-initial.json'),'utf8'));
  const before=new Map<string,string>(baseline.records.map((r:{name:string;profile:string;fingerprint:string})=>[`${r.name}:${r.profile}`,r.fingerprint]));
  const sizes=('50,100,200').split(',');
  const profiles=[deferred,decision];
  const layers=['http','browser'];
  if(profiles.some(p=>![deferred,decision].includes(p))||layers.some(l=>!['http','browser'].includes(l)))throw new Error('Unknown benchmark profile/layer');
  for(const name of sizes){
    const login=await request.post(api+'/api/v1/account/login',{data:{email:`decision-${name}@example.test`,password:'Decision-test-password-123'}});
    expect(login.ok()).toBeTruthy();const token=(await login.json()).access_token,headers={Authorization:`Bearer ${token}`};
    const pairs=3;
    for(const profile of profiles)for(const layer of layers)for(let pair=0;pair<pairs;pair++){
      for(const arm of ['compact']){
        expect((await request.post(`${api}/_test/compact-integrated/${profile}/compact`)).ok()).toBeTruthy(); // Loopback test-only server control; normal submissions remain authenticated.
        const row:Record<string,unknown>={name,profile,layer,pair,arm};let key=crypto.randomUUID() as string;
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
        expect(job.provenance.assistant_execution_selection.engine).toBe('compact_exhaustive');expect(job.provenance.scoring_profile).toBe(profile);expect(job.status).toBe('Selected');expect(job.candidate_count).toBe(metadata.workloads[name].candidate_count);
        const identity={items:job.items,score:job.score,provenance:semanticProvenance(job.provenance)};
        row.fingerprint=createHash('sha256').update(JSON.stringify(identity)).digest('hex');
        const k=`${name}:${profile}`;if(fingerprints.has(k))expect(row.fingerprint).toBe(fingerprints.get(k));else fingerprints.set(k,row.fingerprint as string);
        expect(row.fingerprint).toBe(before.get(`${name}:${profile}`));
        row.resources_after=await(await request.get(api+'/_test/resources')).json();
        row.auxiliary=await(await request.get(api+'/_test/diagnostics')).json();
        save();console.log(JSON.stringify({...row,job:undefined,auxiliary:undefined}));
      }
    }
  }
  collection.state='complete';save();
  // Evidence collection succeeds despite retained transport failures; acceptance
  // is reported separately, never asserted by a five-second or error suppression.
});

