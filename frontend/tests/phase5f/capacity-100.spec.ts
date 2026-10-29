// J10 verification only. All selectors belong to a disposable loopback test server.
import {test,expect} from '@playwright/test';
import {existsSync,readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

type Cell={workload:string;profile:string;suitability:boolean;request:string;http_repetitions:number;browser_repetitions:number};
type Cache={pairs:number;capacity:number;hits:number;misses:number;evictions:number;aggregations:{hits:number;misses:number;currsize:number;maxsize:number}[]};
type Job={done:boolean;status:string;candidate_count:number;id?:string;chat_id?:string;score:unknown;items:unknown[];provenance:Record<string,unknown>;cache:Cache;service_seconds:number;cpu_seconds:number};
type Expected=Cell&{fingerprint:string;counts:{structural:number;mandatory_valid:number;scored:number}};
function canonical(value:unknown):string{
  if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
  if(value!==null&&typeof value==='object'){
    const row=value as Record<string,unknown>;
    return '{'+Object.keys(row).sort().map(k=>JSON.stringify(k)+':'+canonical(row[k])).join(',')+'}';
  }
  return JSON.stringify(value);
}
function sha(value:string|Buffer){return createHash('sha256').update(value).digest('hex');}

test('frozen 100 garment capacity comparison',async({page,request})=>{
  test.skip(process.env.SMART_WARDROBE_CAPACITY_100!=='true','Explicit benchmark opt-in required.');
  const api='http://127.0.0.1:3201';
  const folder=resolve('../storage/verification/phase5f2e3j10');
  const label=process.env.SMART_WARDROBE_COMPACT_RUN_LABEL??'initial';
  if(!/^[a-z0-9-]+$/.test(label))throw new Error('Invalid new run label');
  const output=resolve(folder,'performance-'+label+'.json');
  if(existsSync(output))throw new Error('Refusing to overwrite retained evidence');
  const frozen=JSON.parse(readFileSync(resolve(folder,'frozen-manifest.json'),'utf8'));
  const expectedBytes=readFileSync(resolve(folder,'expected-results.json'));
  expect(sha(expectedBytes)).toBe(frozen.expected_sha256);
  const expected=JSON.parse(expectedBytes.toString()) as Expected[];
  const supplied=await(await request.get(api+'/_test/j10-plan')).json();
  expect(supplied.sha256).toBe(frozen.fixture_sha256);
  const plan=supplied.plan as {schedule:Cell[];requests:Record<string,string>;controls:{settle_ms:number;max_preflight_ms:number;cpu_max:number;ram_min_kib:number;consecutive:number}};
  const metadata=await(await request.get(api+'/_test/workloads')).json();
  expect(metadata.profile).toBe('compatibility_deferred');
  expect((await(await request.get(api+'/_test/diagnostics')).json()).enabled).toBe(false);
  const records:Record<string,unknown>[]=[];
  const collection={state:'preflight',preflight:[] as Record<string,unknown>[],consecutive:0};
  const save=()=>writeFileSync(output,JSON.stringify({label,metadata,frozen,records,collection,controls:plan.controls,formal_nfr_acceptance:false,method:'20 prespecified sequential calls: main experimental+suitability 1HTTP+5browser per workload; two diagnostics each 1HTTP+1browser per workload; same immutable population/preferences within each workload, two profiles and two evaluator configurations. Production Next proxy; direct HTTP comparison. No ranking warm-up, pruning, profiler or kernel stage instrumentation. Browser click to visible result, thumbnails not included as a completed-loading boundary.'},null,2));
  save();
  await page.waitForTimeout(plan.controls.settle_ms);
  const preflight=performance.now();
  while(collection.consecutive<plan.controls.consecutive&&performance.now()-preflight<plan.controls.max_preflight_ms){
    const sample=await(await request.get(api+'/_test/resources')).json();
    collection.preflight.push(sample);
    const good=sample.available===true&&Number.isFinite(sample.system?.cpu_load_percent)&&sample.system.cpu_load_percent<=plan.controls.cpu_max&&sample.system.free_physical_kib>=plan.controls.ram_min_kib;
    collection.consecutive=good?collection.consecutive+1:0;save();
    if(collection.consecutive<plan.controls.consecutive)await page.waitForTimeout(1000);
  }
  if(collection.consecutive<plan.controls.consecutive){collection.state='resource_blocked';save();throw new Error('Resource preflight blocked; zero timed submissions.');}
  collection.state='running';save();
  for(const cell of plan.schedule){
    const target=expected.find(e=>e.workload===cell.workload&&e.profile===cell.profile&&e.suitability===cell.suitability)!;
    expect(target).toBeTruthy();
    const login=await request.post(api+'/api/v1/account/login',{data:{email:`j10-${cell.workload}@example.test`,password:'Decision-test-password-123'}});
    expect(login.status()).toBe(200);
    const token=(await login.json()).access_token;
    expect((await request.post(`${api}/_test/j10-select/${cell.profile}/${cell.suitability?'enabled':'disabled'}`)).ok()).toBe(true);
    for(const layer of ['http','browser'])for(let trial=0;trial<(layer==='http'?cell.http_repetitions:cell.browser_repetitions);trial++){
      let key=crypto.randomUUID() as string;
      const row:Record<string,unknown>={...cell,layer,trial,key,error:null};
      row.resources_before=await(await request.get(api+'/_test/resources')).json();
      let started=performance.now();
      try{
        let outcome:string;
        if(layer==='http'){
          const response=await request.post(api+'/api/v1/recommendations?pipeline=integrated',{headers:{Authorization:`Bearer ${token}`},data:{request_text:plan.requests[cell.request],submission_key:key},timeout:240000});
          row.http_status=response.status();row.backend_seconds=Number(response.headers()['x-test-backend-seconds']);
          outcome=(await response.json()).outcome;row.seconds=(performance.now()-started)/1000;
        }else{
          await page.goto('/auth');
          await page.evaluate(t=>{sessionStorage.clear();sessionStorage.setItem('smart_wardrobe_access_token',t);},token);
          await page.goto('/assistant');await page.getByLabel('What would you like to wear?').fill(plan.requests[cell.request]);
          const pending=page.waitForResponse(r=>r.url().includes('pipeline=integrated')&&r.request().method()==='POST',{timeout:240000});
          started=performance.now();await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();
          const response=await pending;key=response.request().postDataJSON().submission_key;row.key=key;
          row.http_status=response.status();row.http_seconds=(performance.now()-started)/1000;
          row.backend_seconds=Number(response.headers()['x-test-backend-seconds']);
          if(response.status()>=500)throw new Error(`Proxy HTTP ${response.status()}: ${await response.text()}`);
          outcome=(await response.json()).outcome;
          await expect(page.getByTestId('recommendation-result')).toBeVisible({timeout:240000});
          row.seconds=(performance.now()-started)/1000;
        }
        row.outcome=outcome;expect(outcome).toBe('Selected');expect(row.http_status).toBe(201);
      }catch(error){row.error=String(error);row.seconds=(performance.now()-started)/1000;}
      records.push(row);save();
      const drain=performance.now();let job:Job;
      do{
        job=await(await request.get(`${api}/_test/job/${key}`)).json();
        if(job.done)break;
        await page.waitForTimeout(1000);
      }while(performance.now()-drain<240000);
      row.job=job;row.drain_seconds=(performance.now()-drain)/1000;save();
      if(!job.done){collection.state='backend_unsettled';save();throw new Error('No further timings while previous backend call remains unsettled.');}
      try{
        expect(job.status).toBe('Selected');expect(job.id).toBeTruthy();expect(job.chat_id).toBeTruthy();
        expect(job.provenance.scoring_profile).toBe(cell.profile);
        expect((job.provenance.assistant_execution_selection as {engine:string}).engine).toBe('compact_exhaustive');
        expect(job.provenance.request_evaluator).toBe(cell.suitability?'SuitabilityRequestEvaluator':'RequestConstraintEvaluator');
        expect(job.candidate_count).toBe(target.counts.scored);
        const cert=job.cache.aggregations.at(-1)!;
        expect(cert.hits+cert.misses).toBe(job.candidate_count);
        expect(job.cache.pairs).toBeLessThanOrEqual(19900);
        for(const memo of job.cache.aggregations)expect(memo.currsize).toBeLessThanOrEqual(256);
        row.counts={structural:target.counts.structural,mandatory_valid:job.candidate_count,scored:job.candidate_count};
        row.certificate={hits:cert.hits,misses:cert.misses,evictions:Math.max(0,cert.misses-cert.currsize),capacity:cert.maxsize};
        row.fingerprint=sha(canonical({items:job.items,score:job.score,provenance:job.provenance}));
        expect(row.fingerprint).toBe(target.fingerprint);
      }catch(error){row.error=[row.error,String(error)].filter(Boolean).join('\n');}
      row.resources_after=await(await request.get(api+'/_test/resources')).json();save();
      console.log(JSON.stringify({...row,job:undefined,resources_before:undefined,resources_after:undefined}));
    }
  }
  collection.state='complete';
  const counts:Record<string,unknown>={};
  for(const name of ['balanced-100','maximum-100'])counts[name]=await(await request.get(`${api}/_test/counts/${name}`)).json();
  records.push({persistence_counts:counts});save();
  expect(records.filter(r=>r.error)).toEqual([]);
  // Latency failure is retained and reported, never hidden by collector success.
});
