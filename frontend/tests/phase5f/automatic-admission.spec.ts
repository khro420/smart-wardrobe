import { test, expect, chromium, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";

const folder=process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const api='http://127.0.0.1:3101/api/v1';
const record=(name:string,value:unknown)=>writeFileSync(join(folder,name+'.json'),JSON.stringify(value,null,2));
async function setup(page:Page,request:APIRequestContext){
  const email=`automatic-${crypto.randomUUID()}@example.test`,password='Disposable-automatic-password-123';
  expect((await request.post(api+'/account/register',{data:{email,password,password_confirmation:password,display_name:'Automatic Test Owner'}})).status()).toBe(201);
  await page.goto('/auth');await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);
  await page.locator('form').getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('/');
  const token=(await page.evaluate(()=>sessionStorage.getItem('smart_wardrobe_access_token')))!;
  return {email,headers:{Authorization:`Bearer ${token}`}};
}
async function image(page:Page,code:number){
  return Buffer.from(await page.evaluate(value=>{const c=document.createElement('canvas');c.width=c.height=256;const ctx=c.getContext('2d')!;ctx.fillStyle=`rgb(${value},70,180)`;ctx.fillRect(0,0,256,256);return [...Uint8Array.from(atob(c.toDataURL('image/png').split(',')[1]),v=>v.charCodeAt(0))];},code));
}
async function addThroughUi(page:Page,code:number){
  const buffer=await image(page,code);await page.goto('/extract');
  await page.getByLabel('Wardrobe image',{exact:true}).setInputFiles({name:'synthetic.png',mimeType:'image/png',buffer});await page.waitForURL(/\/extract\/results/);
  await expect(page.getByRole('heading',{name:'Automatic garment addition',exact:true})).toBeVisible();
  return new URL(page.url()).searchParams.get('job')!;
}
async function ask(page:Page,text:string){
  await page.goto('/assistant');await page.getByRole('button',{name:'New Chat',exact:true}).click();
  await page.getByLabel('What would you like to wear?',{exact:true}).fill(text);
  const result=page.waitForResponse(r=>r.url().includes('/recommendations?pipeline=integrated')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Suggest an outfit',exact:true}).click();return (await result).json();
}
async function outcome(page:Page){
  const root=page.getByRole('region',{name:'Recommendation outcome',exact:true});await expect(root).toBeFocused();
  const box=await root.locator('h2').first().boundingBox();expect(box).not.toBeNull();expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.y+box!.height).toBeLessThanOrEqual(await page.evaluate(()=>innerHeight));
  expect(await page.evaluate(()=>{const a=document.querySelector('[aria-label="Recommendation outcome"]')!,b=document.querySelector('[aria-label="Understood situation"]');return !b||!!(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING);})).toBe(true);
}
async function bounds(page:Page){
  return page.evaluate(()=>{const root=document.querySelector('#main-content')!,width=document.documentElement.clientWidth,clipped:string[]=[];const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(walk.nextNode()){const n=walk.currentNode;if(!n.textContent?.trim()||!n.parentElement?.getClientRects().length||['SCRIPT','STYLE'].includes(n.parentElement.tagName))continue;const r=document.createRange();r.selectNodeContents(n);if([...r.getClientRects()].some(b=>b.width>0&&(b.left< -1||b.right>width+1)))clipped.push(n.textContent.trim());}return {width,scroll:document.documentElement.scrollWidth,clipped};});
}

test('B01 normal Add automatically saves and recommends without confirmation actions',async({page,request,browser})=>{
  const {headers}=await setup(page,request);let reviews=0,confirms=0;
  page.on('request',r=>{if(r.method()==='POST'&&(/\/review$/.test(r.url())||r.url().includes('/contextual-suitability')))reviews++;if(r.method()==='POST'&&/\/confirm$/.test(r.url()))confirms++;});
  const id=await addThroughUi(page,10);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Accept candidate',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Save selected garments',exact:true})).toHaveCount(0);
  const job=await(await request.get(api+'/processing/jobs/'+id,{headers})).json();expect(job.status).toBe('completed');
  await page.getByRole('link',{name:'Open wardrobe',exact:true}).click();await page.waitForURL('/wardrobe');
  const saved=await(await request.get(api+'/wardrobe/garments',{headers})).json();expect(saved).toHaveLength(1);expect(saved[0].contextual_edit.review_current).toBe(false);
  const results=[];for(const text of ["I'm going shopping.","I'm going to class."]){const value=await ask(page,text);expect(value.outcome).toBe('Selected');expect(value.recommendation.total_score).toBe(.7);await expect(page.getByTestId('recommendation-result')).toContainText('saved, unreviewed style');await expect(page.getByLabel('Stored ranking score')).toContainText('7/10');results.push(value);}
  const layouts=[];for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:960});const layout=await bounds(page);expect(layout.clipped).toEqual([]);expect(layout.scroll).toBeLessThanOrEqual(layout.width);layouts.push(layout);}
  await page.setViewportSize({width:360,height:960});await page.screenshot({path:join(folder,'B01-result-360.png'),fullPage:true});
  expect(reviews).toBe(0);expect(confirms).toBe(0);record('B01',{browser:browser.version(),reviews,confirms,job,results,layouts});
});

test('B02 eight legacy saved garments need no Edit or review for all five contexts',async({page,request})=>{
  const {email,headers}=await setup(page,request);
  for(let code=20;code<28;code++){
    const upload=await request.post(api+'/processing/jobs',{headers,multipart:{file:{name:'legacy-synthetic.png',mimeType:'image/png',buffer:await image(page,code)}}});expect(upload.status()).toBe(202);
    const id=(await upload.json()).id;let job=await(await request.get(api+'/processing/jobs/'+id,{headers})).json();
    await expect.poll(async()=>{job=await(await request.get(api+'/processing/jobs/'+id,{headers})).json();return job.status;}).toBe('review_required');
    expect((await request.post(api+'/processing/jobs/'+id+'/review',{headers,data:{items:[{item_id:job.items[0].id,decision:'accepted'}]}})).status()).toBe(200);
    expect((await request.post(api+'/processing/jobs/'+id+'/confirm',{headers,data:{item_ids:[job.items[0].id],save_mode:'garments'}})).status()).toBe(201);
  }
  execFileSync('py',['-3.12','-B',join(folder,'legacyify.py'),email],{stdio:'pipe'});
  const before=await(await request.get(api+'/wardrobe/garments',{headers})).json();expect(before).toHaveLength(8);expect(before.every((g:{contextual_edit:{review_current:boolean}})=>!g.contextual_edit.review_current)).toBe(true);
  const results=[];for(const text of ["I'm going shopping","I'm going to class","I'm going out with friends","I'm going on a date","I'm meeting friends for dinner"]){const value=await ask(page,text);expect(value.outcome).toBe('Selected');results.push(value);}
  expect(await(await request.get(api+'/wardrobe/garments',{headers})).json()).toEqual(before);record('B02',{source:'fixture-authored disposable replicas, not private wardrobe copies',results});
});

test('B03 missing style stores honestly; missing category needs one correction Save',async({page,request})=>{
  const {headers}=await setup(page,request);await addThroughUi(page,12);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
  expect((await ask(page,"I'm going shopping")).outcome).toBe('InsufficientEvidence');await outcome(page);
  await addThroughUi(page,13);await expect(page.getByRole('heading',{name:'Garments have not been added yet'})).toBeVisible();
  const candidate=page.getByRole('article').first();await candidate.getByText('Edit details and review image',{exact:true}).click();await candidate.getByLabel('Category',{exact:true}).selectOption('vest_dress');
  await candidate.getByRole('button',{name:'Save corrections',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
  const rows=await(await request.get(api+'/wardrobe/garments',{headers})).json();expect(rows).toHaveLength(2);expect(rows.every((g:{contextual_edit:{review_current:boolean}})=>!g.contextual_edit.review_current)).toBe(true);
  expect((await ask(page,"I'm going to class")).outcome).toBe('Selected');record('B03',{noStyleStored:true,incompleteCategoryCorrectedOnce:true});
});

test('B04 Deny, unavailable and technical outcomes precede context details',async({page,request})=>{
  const {headers}=await setup(page,request);await addThroughUi(page,10);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
  const row=(await(await request.get(api+'/wardrobe/garments',{headers})).json())[0];expect((await request.patch(api+'/wardrobe/garments/'+row.id,{headers:{...headers,'If-Match':row.tag_edit.revision},data:{attributes:{custom_tags:['rec:v1:occasion:shopping:deny']}}})).status()).toBe(200);
  await page.setViewportSize({width:390,height:844});
  for(const [text,expected] of [["I'm going shopping",'NoMatchingCandidates'],["I'm going shopping; the dress code is formal",'PolicyUnavailable'],['I have a job interview','PolicyUnavailable']]){expect((await ask(page,text)).outcome).toBe(expected);await outcome(page);}
  await page.route('**/recommendations?pipeline=integrated',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Synthetic unavailable'})}));await ask(page,"I'm going shopping");await expect(page.getByRole('heading',{name:'Request could not be completed'})).toBeVisible();await outcome(page);await page.unroute('**/recommendations?pipeline=integrated');
  await page.getByRole('button',{name:'Retry same request',exact:true}).click();await expect(page.getByRole('heading',{name:'No outfit generated',exact:true})).toBeVisible();await outcome(page);await page.screenshot({path:join(folder,'B04-outcome-390.png')});record('B04',{outcomeFirst:true});
});

test('B05 actual source remains distinct from optional owner review and withdrawal',async({page,request})=>{
  const {headers}=await setup(page,request);await addThroughUi(page,30);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
  const before=await ask(page,"I'm going shopping");expect(before.outcome).toBe('Selected');await expect(page.getByTestId('recommendation-result')).toContainText('origin: model_reported');
  const gid=(await(await request.get(api+'/wardrobe/garments',{headers})).json())[0].id;
  await page.goto('/wardrobe');let card=page.locator(`[data-garment-id="${gid}"]`);await card.getByRole('button',{name:'Edit',exact:true}).click();await card.getByRole('combobox',{name:/^Style evidence/}).selectOption('values');await card.getByLabel('Styles (comma-separated)',{exact:true}).fill('casual');await card.getByRole('button',{name:'Save changes',exact:true}).click();await expect(card.getByRole('button',{name:'Edit',exact:true})).toBeVisible();
  const reviewed=await ask(page,"I'm going shopping");expect(reviewed.recommendation.score_metadata).toEqual(before.recommendation.score_metadata);await expect(page.getByTestId('recommendation-result')).toContainText('inferred from reviewed style attributes');
  await page.goto('/wardrobe');card=page.locator(`[data-garment-id="${gid}"]`);await card.getByText('Contextual recommendations',{exact:true}).click();await card.getByRole('button',{name:'Remove style review',exact:true}).click();await expect(card).toContainText('Not reviewed for contextual inference');
  const withdrawn=await ask(page,"I'm going shopping");expect(withdrawn.outcome).toBe('Selected');expect(withdrawn.recommendation.provenance.general_context.members[0].style_verification).toBe('saved_unreviewed');record('B05',{before,reviewed,withdrawn});
});

test('B06 optional correction Cancel and failed saves preserve current evidence',async({page,request})=>{
  const {headers}=await setup(page,request);await addThroughUi(page,10);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();const row=(await(await request.get(api+'/wardrobe/garments',{headers})).json())[0];
  await page.goto('/wardrobe');const card=page.locator(`[data-garment-id="${row.id}"]`);await card.getByRole('button',{name:'Edit',exact:true}).click();await card.getByLabel('Styles (comma-separated)',{exact:true}).fill('classic');await card.getByRole('button',{name:'Cancel',exact:true}).click();
  expect((await(await request.get(api+'/wardrobe/garments',{headers})).json())[0]).toEqual(row);
  await card.getByRole('button',{name:'Edit',exact:true}).click();await card.getByLabel('Styles (comma-separated)',{exact:true}).fill('classic');const route=`**/wardrobe/garments/${row.id}`;await page.route(route,r=>r.abort('failed'));await card.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.locator('#main-content').getByRole('alert')).toBeVisible();await expect(card.getByLabel('Styles (comma-separated)',{exact:true})).toHaveValue('classic');await page.unroute(route);expect((await(await request.get(api+'/wardrobe/garments',{headers})).json())[0]).toEqual(row);await card.getByRole('button',{name:'Cancel',exact:true}).click();
  expect((await ask(page,"I'm going shopping")).outcome).toBe('Selected');record('B06',{cancelPreserved:true,failedDraftPreserved:true});
});

test('B07 automatic two-piece scores, save/history and durable logout',async({page,request})=>{
  const {headers}=await setup(page,request);await addThroughUi(page,11);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();const selected=await ask(page,"I'm going shopping");expect(selected.outcome).toBe('Selected');expect(selected.recommendation.items).toHaveLength(2);expect(selected.recommendation.total_score).toBe(.8);
  await expect(page.getByLabel('Stored ranking score')).toContainText('4/5');await page.getByTestId('recommendation-result').getByRole('button',{name:'Save as outfit',exact:true}).click();await expect(page.getByRole('button',{name:'Saved as outfit',exact:true})).toBeVisible();await page.goto('/history/'+selected.recommendation.chat_id);await expect(page.getByTestId('recommendation-result')).toContainText('saved, unreviewed style');await expect(page.getByLabel('Stored ranking score')).toContainText('4/5');
  const history=await(await request.get(api+'/chats/'+selected.recommendation.chat_id,{headers})).json();expect(history.recommendation.provenance).toEqual(selected.recommendation.provenance);expect(history.recommendation.score_metadata).toEqual(selected.recommendation.score_metadata);
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL('/auth');expect((await request.get(api+'/wardrobe/garments',{headers})).status()).toBe(401);record('B07',{selected,history,loggedOutBearerRejected:true});
});

test('B08 keyboard, full names, narrow bounds and actual native 200 percent zoom',async({request})=>{
  const profile=mkdtempSync(join(tmpdir(),'automatic-admission-zoom-'));const context=await chromium.launchPersistentContext(profile,{channel:'chrome',headless:true,baseURL:'http://127.0.0.1:3100',viewport:null,args:['--window-size=1440,1000']});
  try{
    const page=context.pages()[0];await setup(page,request);await addThroughUi(page,10);await expect(page.getByRole('status').filter({hasText:'automatically added'})).toBeVisible();
    const settings=await context.newPage();await settings.goto('chrome://settings');const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{const c=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};c.chrome.settingsPrivate.setDefaultZoom(2,()=>c.chrome.settingsPrivate.getDefaultZoom(resolve));}));await settings.close();
    await page.goto('/assistant');await page.getByRole('button',{name:'New Chat',exact:true}).click();await page.getByLabel('What would you like to wear?',{exact:true}).fill("I'm going shopping");await page.getByLabel('What would you like to wear?',{exact:true}).focus();await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'Suggest an outfit',exact:true})).toBeFocused();await page.keyboard.press('Enter');await expect(page.getByTestId('recommendation-result')).toBeVisible();const layout=await bounds(page),metrics=await page.evaluate(()=>({dpr:devicePixelRatio,width:innerWidth,scale:visualViewport!.scale,cssZoom:getComputedStyle(document.body).zoom}));expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe('1');expect(layout.clipped).toEqual([]);
    const heading=page.getByRole('heading',{name:'Your outfit recommendation',exact:true});
    await expect.poll(async()=>{const box=await heading.boundingBox(),header=await page.getByRole('banner').boundingBox();return !!box&&!!header&&box.y>=header.y+header.height&&box.y+box.height<=await page.evaluate(()=>innerHeight);}).toBe(true);
    const headingBounds=await heading.boundingBox();
    const cdp=await context.newCDPSession(page),shot=await cdp.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});writeFileSync(join(folder,'B08-native-zoom.png'),Buffer.from(shot.data,'base64'));await cdp.detach();record('B08-native',{zoom,metrics,layout,profile,headingBounds});
  }finally{await context.close();}
});
