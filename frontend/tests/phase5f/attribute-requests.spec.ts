import { test, expect, chromium, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

type GarmentDescriptor={id:string;name:string;category:string;description:{revision:string}};
type RecommendationItem={name:string;garment_id:string;garment_role:string};
type CapturedAttempt={body:Record<string,unknown>;wearer?:string;header?:string};

const api="http://127.0.0.1:3101/api/v1", folder=process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const record=(name:string,value:unknown)=>writeFileSync(join(folder,name+".json"),JSON.stringify(value,null,2));
async function owner(page:Page,request:APIRequestContext){
  const email=`attribute-${crypto.randomUUID()}@example.test`,password="Disposable-attribute-password-123";
  expect((await request.post(api+"/account/register",{data:{email,password,password_confirmation:password,display_name:"Attribute mechanics"}})).status()).toBe(201);
  const auth=await(await request.post(api+"/account/login",{data:{email,password}})).json();
  await page.goto("/auth");await page.evaluate(token=>{sessionStorage.clear();sessionStorage.setItem("smart_wardrobe_access_token",token);},auth.access_token);
  return {Authorization:`Bearer ${auth.access_token}`};
}
async function seed(page:Page,request:APIRequestContext,headers:Record<string,string>){
  for(const code of [20,23,27]){
    const buffer=Buffer.from(await page.evaluate(value=>{const c=document.createElement("canvas");c.width=c.height=256;const x=c.getContext("2d")!;x.fillStyle=`rgb(${value},70,180)`;x.fillRect(0,0,256,256);return [...Uint8Array.from(atob(c.toDataURL("image/png").split(",")[1]),v=>v.charCodeAt(0))];},code));
    const response=await request.post(api+"/processing/jobs?admission_mode=automatic_structural_v1",{headers,multipart:{file:{name:"synthetic.png",mimeType:"image/png",buffer}}});
    expect(response.status()).toBe(202);const job=await response.json();
    await expect.poll(async()=>(await(await request.get(api+"/processing/jobs/"+job.id,{headers})).json()).status).toBe("completed");
  }
  return await(await request.get(api+"/wardrobe/garments",{headers})).json();
}
async function qualify(request:APIRequestContext,headers:Record<string,string>,g:GarmentDescriptor,values:Record<string,unknown>){
  const response=await request.patch(api+"/wardrobe/garments/"+g.id,{headers,data:{description_update:{contract:"garment-description-update-1.0.0",expected_revision:g.description.revision,operations:Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{kind:"set",value}]))}}});
  expect(response.status()).toBe(200);return response.json();
}
async function fresh(page:Page,text="Suggest an outfit."){
  await page.goto("/assistant");await page.getByRole("button",{name:"New Chat",exact:true}).click();
  await page.getByLabel("What would you like to wear?",{exact:true}).fill(text);
}
async function send(page:Page,name="Suggest an outfit"){
  const response=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");
  await page.getByRole("button",{name,exact:true}).click();return (await response).json();
}
async function edit(page:Page){
  await page.getByText("Optional garment requirements",{exact:true}).click();
  await page.getByRole("button",{name:"Edit garment requirements",exact:true}).click();
}
async function feature(page:Page,field:string,value:string|string[],index=1,operator?:string){
  await page.getByLabel(`Feature ${index} in rule 1`,{exact:true}).selectOption(field);
  if(operator)await page.getByLabel(`Match ${index} in rule 1`,{exact:true}).selectOption(operator);
  if(operator==="exact_text")await page.getByLabel(`Exact text 1 for feature ${index} in rule 1`,{exact:true}).fill(String(value));
  else if(operator==="exact_hex")await page.getByLabel(`Exact hex ${index} in rule 1`,{exact:true}).fill(String(value));
  else if(field==="colour_dominance")await page.getByLabel(`Observation ${index} in rule 1`,{exact:true}).selectOption(String(value));
  else await page.getByLabel(`Values ${index} in rule 1`,{exact:true}).selectOption(value);
}

test("AT01 complete NLP conjunction filters actual garments and historical result retains its captured requirements",async({page,request})=>{
  const headers=await owner(page,request),rows=await seed(page,request,headers),blue=rows.find((g:GarmentDescriptor)=>g.name==="Blue T-shirt");
  await qualify(request,headers,blue,{pattern:"plain",material:["cotton"],neckline:"v-neck"});
  await fresh(page,"I'm going shopping and want a plain cotton v-neck top.");const root=await send(page);
  expect(root.outcome).toBe("Selected");expect(root.items.map((i:RecommendationItem)=>i.name)).toEqual(["Blue T-shirt","Blue Jeans"]);
  await expect(page.getByRole("region",{name:"Matched garment requirements",exact:true})).toContainText("cotton");
  expect(root.scoring_display.total).toEqual({numerator:"4",denominator:"5"});
  await page.goto("/history/"+root.chat_id);
  await expect(page.getByRole("region",{name:"Matched garment requirements",exact:true})).toContainText("v-neck");
  record("AT01",root);
});

test("AT02 optional controls Cancel sends nothing; complete rare typed values and false enforce a fresh request",async({page,request})=>{
  const headers=await owner(page,request),rows=await seed(page,request,headers),blue=rows.find((g:GarmentDescriptor)=>g.name==="Blue T-shirt");
  await qualify(request,headers,blue,{pattern:"houndstooth",material:["wool"],neckline:"queen anne",silhouette:"mermaid",colour_temperature:"neutral",colour_dominance:false,secondary_colour:"cream",colour_palette:[{hex:"#123abc",coverage:"0.500000"}],descriptive_tags:["handmade"]});
  await fresh(page);let posts=0;page.on("request",r=>{if(r.method()==="POST"&&r.url().includes("/recommendations?"))posts++;});
  await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();await feature(page,"pattern","paisley");
  await page.getByRole("button",{name:"Cancel garment changes",exact:true}).click();expect(posts).toBe(0);
  await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();
  await page.getByLabel("Garment scope for rule 1",{exact:true}).selectOption("upper");
  const fields:[[string,string,string?],...Array<[string,string,string?]>]=[["pattern","houndstooth"],["material","wool"],["neckline","queen anne"],["silhouette","mermaid"],["colour_temperature","neutral"],["colour_dominance","false"],["secondary_colour","cream"],["palette_colour","#123abc","exact_hex"],["descriptive_tag","handmade","exact_text"],["garment_name","Blue T-shirt","exact_text"]];
  for(let i=0;i<fields.length;i++){if(i)await page.getByRole("button",{name:"Add a feature to this same garment",exact:true}).click();const [field,value,operator]=fields[i];await feature(page,field,value,i+1,operator);}
  await page.getByRole("button",{name:"Apply garment requirements",exact:true}).click();expect(posts).toBe(0);
  const root=await send(page);expect(root.outcome).toBe("Selected");expect(root.items.some((i:RecommendationItem)=>i.garment_id===blue.id)).toBe(true);
  expect(root.provenance.attribute_selection.intent.typed_input.groups[0].conditions.find((c:{attribute:string})=>c.attribute==="colour_dominance").values).toEqual([false]);
  await expect(page.getByRole("region",{name:"Matched garment requirements",exact:true})).toContainText("queen anne");record("AT02",root);
});

test("AT03 failed typed action keeps exact body/key through reload and retry",async({page,request})=>{
  const headers=await owner(page,request),rows=await seed(page,request,headers);await qualify(request,headers,rows.find((g:GarmentDescriptor)=>g.name==="Blue T-shirt"),{material:["cotton"]});
  await fresh(page);await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();
  await page.getByLabel("Garment scope for rule 1",{exact:true}).selectOption("upper");await feature(page,"material","cotton");
  await page.getByRole("button",{name:"Apply garment requirements",exact:true}).click();
  const attempts:CapturedAttempt[]=[];await page.route("**/recommendations?pipeline=integrated",async route=>{attempts.push({body:route.request().postDataJSON(),wearer:route.request().headers()["x-wardrobe-profile-id"]});if(attempts.length===1)await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({outcome:"PersistenceFailure"})});else await route.continue();});
  await send(page);await expect(page.getByRole("button",{name:"Retry same request",exact:true})).toBeVisible();
  const restored=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");await page.reload();
  const result=await(await restored).json();await expect(page.getByText("Captured typed requirements",{exact:true})).toBeVisible();
  expect(result.outcome).toBe("Selected");expect(attempts).toHaveLength(2);expect(attempts[1]).toEqual(attempts[0]);record("AT03",{attempts,result});
});

test("AT04 missing fine description stays Unknown while explicit negative and changed requirements start fresh roots",async({page,request})=>{
  const headers=await owner(page,request),rows=await seed(page,request,headers);
  await fresh(page,"I want a cotton top.");const unknown=await send(page);expect(unknown.outcome).toBe("InsufficientEvidence");
  for(const g of rows.filter((g:GarmentDescriptor)=>g.category!=="trousers"))await qualify(request,headers,g,{material:[g.name==="Blue T-shirt"?"cotton":"linen"]});
  await fresh(page,"I want a top with no cotton material.");const result=await send(page);
  expect(result.outcome).toBe("Selected");expect(result.items.find((i:RecommendationItem)=>i.garment_role==="upper").name).toBe("Green Sweatshirt");record("AT04",{unknown,result});
});

test("AT05 typed controls and captured output fit all named widths with keyboard focus",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);await fresh(page);
  await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();
  await feature(page,"garment_name","\u8863".repeat(100),1,"exact_text");
  const input=page.getByLabel("Exact text 1 for feature 1 in rule 1",{exact:true});await input.focus();await expect(input).toBeFocused();
  const measurements=[];for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:960});const value=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));expect(value.scroll).toBeLessThanOrEqual(value.width+1);measurements.push(value);}
  record("AT05",measurements);
});

test("AT06 pending typed A action cannot be resubmitted as B",async({page,request})=>{
  const headers=await owner(page,request),rows=await seed(page,request,headers);
  await qualify(request,headers,rows.find((g:GarmentDescriptor)=>g.name==="Blue T-shirt"),{material:["cotton"]});
  const profiles=await(await request.get(api+"/account/wardrobe-profiles",{headers})).json(),a=profiles[0].id;
  const b=(await(await request.post(api+"/account/wardrobe-profiles",{headers,data:{name:"B"}})).json()).id;
  const choose=async(id:string)=>{const loaded=page.waitForEvent("load");await page.getByRole("combobox",{name:"Select active wardrobe profile"}).first().selectOption(id);await loaded;};
  await page.goto("/assistant");await choose(a);await page.getByLabel("What would you like to wear?",{exact:true}).fill("Suggest an outfit.");
  await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();
  await page.getByLabel("Garment scope for rule 1",{exact:true}).selectOption("upper");await feature(page,"material","cotton");
  await page.getByRole("button",{name:"Apply garment requirements",exact:true}).click();
  const attempts:CapturedAttempt[]=[];await page.route("**/recommendations?pipeline=integrated",async route=>{
    const body=route.request().postDataJSON();if(body.attribute_conditions){attempts.push({body,header:route.request().headers()["x-wardrobe-profile-id"]});if(attempts.length===1){await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({outcome:"PersistenceFailure"})});return;}}await route.continue();});
  await send(page);await expect(page.getByRole("button",{name:"Retry same request",exact:true})).toBeVisible();
  await choose(b);await expect(page.getByLabel("What would you like to wear?",{exact:true})).toHaveValue("");expect(attempts).toHaveLength(1);
  await page.getByLabel("What would you like to wear?",{exact:true}).fill("I'm going shopping.");const second=await send(page);expect(second.intended_wearer.profile_id).toBe(b);expect(second.attribute_display).toBeUndefined();
  await choose(a);await expect(page.getByRole("region",{name:"Matched garment requirements",exact:true})).toContainText("cotton");
  expect(attempts).toHaveLength(2);expect(attempts[1]).toEqual(attempts[0]);expect(attempts[1].header).toBe(a);record("AT06",{attempts,second});
});

test("AT07 native Chrome 200 percent zoom retains optional typed controls",async({request})=>{
  const context=await chromium.launchPersistentContext(mkdtempSync(join(tmpdir(),"attribute-zoom-")),{channel:"chrome",headless:true,baseURL:"http://127.0.0.1:3100",viewport:null,args:["--window-size=1440,1000"]});
  try{const page=context.pages()[0];await owner(page,request);
    const settings=await context.newPage();await settings.goto("chrome://settings");
    const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{const c=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};c.chrome.settingsPrivate.setDefaultZoom(2,()=>c.chrome.settingsPrivate.getDefaultZoom(resolve));}));await settings.close();
    await fresh(page);await edit(page);await page.getByRole("button",{name:"Add another garment rule",exact:true}).click();await feature(page,"neckline","queen anne");
    const metrics=await page.evaluate(()=>({dpr:devicePixelRatio,scale:visualViewport!.scale,width:innerWidth,scroll:document.documentElement.scrollWidth,cssZoom:getComputedStyle(document.body).zoom}));
    expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe("1");expect(metrics.scroll).toBeLessThanOrEqual(metrics.width);
    record("AT07",metrics);
  }finally{await context.close();}
});
