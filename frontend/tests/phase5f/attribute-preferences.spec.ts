import { test, expect, chromium, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

type GarmentDescriptor={id:string;name:string;category:string;description:{revision:string}};
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


test("P201 full grouped editor explicit save and Cancel with no writes",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);await page.goto("/profile");
  const form=page.getByRole("form",{name:/Soft preferences for/});await expect(form).toBeVisible();
  for(const name of ["Colour","Styles","Garment categories","Formality","Pattern","Material","Visible silhouette","Neckline","Sleeve length","Descriptive tags"]){await form.locator("summary").filter({hasText:new RegExp("^"+name+"$")}).first().click();await expect(form.getByLabel(name+" setting",{exact:true})).toBeVisible();}
  await form.getByLabel("Pattern setting",{exact:true}).selectOption("override");await form.locator("summary").filter({hasText:/^Pattern \(/}).last().click();
  await form.getByLabel("Search pattern",{exact:true}).fill("paisley");await form.getByRole("button",{name:"Like Pattern paisley",exact:true}).click();
  let writes=0;page.on("request",r=>{if(r.method()==="PUT"&&r.url().endsWith("/attribute-preferences"))writes++;});
  await form.getByRole("button",{name:"Cancel preference edits",exact:true}).click();expect(writes).toBe(0);
  await form.getByLabel("Pattern setting",{exact:true}).selectOption("override");await form.locator("summary").filter({hasText:/^Pattern \(/}).last().click();
  await form.getByLabel("Search pattern",{exact:true}).fill("paisley");await form.getByRole("button",{name:"Avoid Pattern paisley",exact:true}).click();
  const saved=page.waitForResponse(r=>r.request().method()==="PUT"&&r.url().endsWith("/attribute-preferences"));await form.getByRole("button",{name:"Save soft preferences",exact:true}).click();
  expect((await saved).status()).toBe(200);expect(writes).toBe(1);await expect(form.getByRole("status")).toContainText("Soft preferences saved");record("P201",{writes});
});

test("P202 pending P2 exact request survives reload and captured mode is retained",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);await fresh(page,"I'm going shopping.");
  const attempts:CapturedAttempt[]=[];await page.route("**/recommendations?pipeline=integrated",async route=>{attempts.push({body:route.request().postDataJSON(),wearer:route.request().headers()["x-wardrobe-profile-id"]});if(attempts.length===1)await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({outcome:"PersistenceFailure"})});else await route.continue();});
  await send(page);await expect(page.getByRole("button",{name:"Retry same request",exact:true})).toBeVisible();
  const restored=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");await page.reload();const result=await(await restored).json();
  expect(result.outcome).toBe("Selected");expect(attempts).toHaveLength(2);expect(attempts[0]).toEqual(attempts[1]);expect(attempts[0].body.preference_profile).toBe("attribute_preference_decision_v2");await expect(page.getByRole("region",{name:"Saved preference ranking",exact:true})).toBeVisible();record("P202",{attempts,result});
});

test("P203 old unscoped preference mode in pending draft remains P1 after enabling",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);await fresh(page,"I'm going shopping.");
  const key=await page.evaluate(()=>{const k=Object.keys(sessionStorage).find(k=>k.startsWith("smart_wardrobe_interaction:")&&!k.includes("p2settings:"))!;const v=JSON.parse(sessionStorage.getItem(k)!);delete v.preferenceProfile;v.submitted=v.text;sessionStorage.setItem(k,JSON.stringify(v));return v.key;});
  const restored=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");await page.reload();const reply=await restored;const result=await reply.json();
  expect(reply.request().postDataJSON().preference_profile).toBeUndefined();expect(reply.request().postDataJSON().submission_key).toBe(key);expect(result.provenance.attribute_preference).toBeUndefined();expect(result.provenance.refinement.request_fingerprint_version).toBe(3);record("P203",result);
});

test("P204 captured preferences survive historical view and changed preferences require fresh root",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);const wearer=(await(await request.get(api+"/account/wardrobe-profiles",{headers})).json())[0].id;
  const target=api+"/account/wardrobe-profiles/"+wearer+"/attribute-preferences";
  async function setPattern(value:string){const v=await(await request.get(target,{headers})).json();expect((await request.put(target,{headers,data:{contract:"attribute-preferences-update-1.0.0",wearer_id:wearer,expected_revision:v.revision,action_id:crypto.randomUUID(),families:{pattern:{mode:"override",importance:"1",axes:{pattern:{scope:"all_selected",importance:"1",liked:[value],avoided:[]}}}}}})).status()).toBe(200);}
  await setPattern("plain");await fresh(page,"I'm going shopping.");const root=await send(page);expect(root.outcome).toBe("Selected");await setPattern("stripe");
  await page.getByRole("button",{name:"Suggest another outfit",exact:true}).click();await expect(page.getByRole("alert").filter({hasText:/Wardrobe, preferences or ranking conditions changed/})).toBeVisible();
  await page.goto("/history/"+root.chat_id);await expect(page.getByRole("region",{name:"Saved preference ranking",exact:true})).toContainText("Pattern");record("P204",root);
});

test("P205 settings failure retains exact revision action and captured wearer through reload",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);await page.goto("/profile");const form=page.getByRole("form",{name:/Soft preferences for/});await expect(form).toBeVisible();
  await form.locator("summary").filter({hasText:/^Pattern$/}).first().click();await form.getByLabel("Pattern setting",{exact:true}).selectOption("override");await form.locator("summary").filter({hasText:/^Pattern \(/}).last().click();await form.getByRole("button",{name:"Like Pattern plain",exact:true}).click();
  const actions:CapturedAttempt[]=[];await page.route("**/attribute-preferences",async route=>{if(route.request().method()!=="PUT")return route.continue();actions.push({body:route.request().postDataJSON(),wearer:route.request().headers()["x-wardrobe-profile-id"]});if(actions.length===1)await route.fulfill({status:503,contentType:"application/json",body:"{}"});else await route.continue();});
  await form.getByRole("button",{name:"Save soft preferences",exact:true}).click();await expect(form.getByRole("alert")).toBeVisible();await page.reload();await expect(form.getByRole("status")).toContainText("restored");await form.getByRole("button",{name:"Save soft preferences",exact:true}).click();await expect(form.getByRole("status")).toContainText("saved");expect(actions).toHaveLength(2);expect(actions[1]).toEqual(actions[0]);record("P205",actions);
});

test("P206 preferences and explanation fit five widths and native Chrome200 percent zoom",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);
  for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:960});await page.goto("/profile");await expect(page.getByRole("form",{name:/Soft preferences for/})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
  await page.setViewportSize({width:1280,height:960});await fresh(page,"I'm going shopping.");await send(page);await expect(page.getByRole("region",{name:"Saved preference ranking",exact:true})).toBeVisible();
  for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:960});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
  const context=await chromium.launchPersistentContext(mkdtempSync(join(tmpdir(),"p2-zoom-")),{channel:"chrome",headless:true,baseURL:"http://127.0.0.1:3100",viewport:null,args:["--window-size=1440,1000"]});
  try{
    const native=context.pages()[0];await owner(native,request);const settings=await context.newPage();await settings.goto("chrome://settings");
    const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{const c=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};c.chrome.settingsPrivate.setDefaultZoom(2,()=>c.chrome.settingsPrivate.getDefaultZoom(resolve));}));await settings.close();
    await native.goto("/profile");const form=native.getByRole("form",{name:/Soft preferences for/});await expect(form).toBeVisible();const summary=form.locator("summary").filter({hasText:/^Colour$/}).first();await summary.focus();await native.keyboard.press("Enter");await expect(form.getByLabel("Colour setting",{exact:true})).toBeVisible();await native.keyboard.press("Tab");
    const metrics=await native.evaluate(()=>({dpr:devicePixelRatio,scale:visualViewport!.scale,width:innerWidth,scroll:document.documentElement.scrollWidth,cssZoom:getComputedStyle(document.body).zoom}));expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe("1");expect(metrics.scroll).toBeLessThanOrEqual(metrics.width);record("P206",metrics);
  }finally{await context.close();}
});

test("P207 pending P2 alternative remains A while B starts an independent fresh request",async({page,request})=>{
  const headers=await owner(page,request);await seed(page,request,headers);
  const a=(await(await request.get(api+"/account/wardrobe-profiles",{headers})).json())[0].id;
  const b=(await(await request.post(api+"/account/wardrobe-profiles",{headers,data:{name:"Wearer B"}})).json()).id;
  const choose=async(id:string)=>{const loaded=page.waitForEvent("load");await page.getByRole("combobox",{name:"Select active wardrobe profile"}).first().selectOption(id);await loaded;};
  await page.goto("/assistant");await choose(a);await page.getByLabel("What would you like to wear?",{exact:true}).fill("I'm going shopping.");const root=await send(page);expect(root.score_metadata.profile_name).toBe("attribute_preference_decision_v2");
  const captured:CapturedAttempt[]=[];await page.route("**/recommendations?pipeline=integrated",async route=>{const body=route.request().postDataJSON();if(body.refinement?.kind==="alternative"){captured.push({body,header:route.request().headers()["x-wardrobe-profile-id"]});if(captured.length===1)return route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({outcome:"PersistenceFailure"})});}await route.continue();});
  await page.getByRole("button",{name:"Suggest another outfit",exact:true}).click();await expect(page.getByRole("button",{name:"Retry same request",exact:true})).toBeVisible();
  await choose(b);await expect(page.getByLabel("What would you like to wear?",{exact:true})).toHaveValue("");expect(captured).toHaveLength(1);await page.getByLabel("What would you like to wear?",{exact:true}).fill("I'm going shopping.");const second=await send(page);expect(second.intended_wearer.profile_id).toBe(b);expect(second.provenance.refinement.root_id).not.toBe(root.id);
  await choose(a);await expect(page.getByLabel("Recommendation sequence")).toContainText("Alternative 1");expect(captured).toHaveLength(2);expect(captured[1]).toEqual(captured[0]);expect(captured[1].body.preference_profile).toBe("attribute_preference_decision_v2");expect(captured[1].header).toBe(a);record("P207",{captured,second});
});
