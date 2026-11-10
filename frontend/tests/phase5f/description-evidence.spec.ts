import { test, expect, chromium, type Page, type APIRequestContext } from "@playwright/test";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const api="http://127.0.0.1:3101/api/v1";
const folder=process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const record=(name:string,data:unknown)=>writeFileSync(join(folder,name+".json"),JSON.stringify(data,null,2));

async function owner(page:Page,request:APIRequestContext){
  const email=`description-${crypto.randomUUID()}@example.test`,password="Disposable-description-password-123";
  expect((await request.post(api+"/account/register",{data:{email,password,password_confirmation:password,display_name:"Description mechanics"}})).status()).toBe(201);
  const auth=await(await request.post(api+"/account/login",{data:{email,password}})).json();
  const headers={Authorization:`Bearer ${auth.access_token}`};
  await page.goto("/auth");await page.evaluate(token=>{sessionStorage.clear();sessionStorage.setItem("smart_wardrobe_access_token",token);},auth.access_token);
  return headers;
}
async function upload(page:Page,request:APIRequestContext,headers:Record<string,string>,automatic=true,code=20){
  const buffer=Buffer.from(await page.evaluate(value=>{const c=document.createElement("canvas");c.width=c.height=256;const x=c.getContext("2d")!;x.fillStyle=`rgb(${value},70,180)`;x.fillRect(0,0,256,256);return [...Uint8Array.from(atob(c.toDataURL("image/png").split(",")[1]),v=>v.charCodeAt(0))];},code));
  const response=await request.post(api+"/processing/jobs"+(automatic?"?admission_mode=automatic_structural_v1":""),{headers,multipart:{file:{name:"synthetic.png",mimeType:"image/png",buffer}}});
  expect(response.status()).toBe(202);const submitted=await response.json();
  await expect.poll(async()=> (await(await request.get(api+"/processing/jobs/"+submitted.id,{headers})).json()).status).toBe(automatic?"completed":"review_required");
  return (await(await request.get(api+"/processing/jobs/"+submitted.id,{headers})).json());
}
async function garments(request:APIRequestContext,headers:Record<string,string>){return(await(await request.get(api+"/wardrobe/garments",{headers})).json());}
async function edit(page:Page){await page.goto("/wardrobe");const article=page.locator("[data-garment-id]").first();await article.getByRole("button",{name:"Edit",exact:true}).click();await expect(article.getByRole("region",{name:"Optional recorded descriptions"})).toBeVisible();return article;}
async function setValue(page:Page,label:string,value:string){await page.getByRole("combobox",{name:label+" action",exact:true}).selectOption("set");await page.getByLabel(label+" value",{exact:true}).selectOption(value);}

test("B001 optional observed false/neutral and material uncertainty are explicit, Cancel writes nothing",async({page,request})=>{
  const headers=await owner(page,request);await upload(page,request,headers);await edit(page);
  const before=(await garments(request,headers))[0];const writes:unknown[]=[];
  page.on("request",r=>{if(r.method()==="PATCH"&&r.url().includes("/wardrobe/garments/"))writes.push(r.postDataJSON());});
  await setValue(page,"Colour temperature","neutral");await page.getByRole("button",{name:"Cancel description changes",exact:true}).click();expect(writes).toHaveLength(0);
  await setValue(page,"Colour temperature","neutral");await setValue(page,"One dominant colour","false");
  await page.getByRole("combobox",{name:"Material action",exact:true}).selectOption("unsure");
  await page.getByRole("button",{name:"Save changes",exact:true}).click();await expect(page.getByText("Garment updated.",{exact:true})).toBeVisible();
  const after=(await garments(request,headers))[0];expect(writes).toHaveLength(1);
  expect(after.description.evidence.fields.colour_dominance.canonical_values).toEqual([false]);
  expect(after.description.evidence.fields.colour_temperature.canonical_values).toEqual(["neutral"]);
  expect(after.description.evidence.fields.material.state).toBe("Unsure");
  expect(after.description.evidence.fields.style.selected.event_id).toBeNull();
  record("B001",{before,after,writes});
});

test("B002 technical retry pins its revision and literal tags preserve Deny",async({page,request})=>{
  const headers=await owner(page,request);await upload(page,request,headers);let g=(await garments(request,headers))[0];
  expect((await request.patch(api+"/wardrobe/garments/"+g.id,{headers:{...headers,"If-Match":g.tag_edit.revision},data:{attributes:{custom_tags:["rec:v1:occasion:shopping:deny"]}}})).status()).toBe(200);
  await edit(page);const captured:unknown[]=[];
  await page.route("**/wardrobe/garments/*",async route=>{if(route.request().method()!=="PATCH"){await route.continue();return;}captured.push(route.request().postDataJSON());if(captured.length===1){await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({detail:"Synthetic temporary failure"})});return;}await route.continue();});
  await page.getByRole("combobox",{name:"Literal descriptive tags action",exact:true}).selectOption("set");
  await page.getByLabel("Literal descriptive tags values",{exact:true}).fill("a literal note");
  await page.getByRole("button",{name:"Save changes",exact:true}).click();await expect(page.getByRole("alert").filter({hasText:"Synthetic temporary failure"})).toContainText("Synthetic temporary failure");
  await page.getByRole("button",{name:"Save changes",exact:true}).click();await expect(page.getByText("Garment updated.",{exact:true})).toBeVisible();
  expect(captured).toHaveLength(2);expect(captured[0]).toEqual(captured[1]);g=(await garments(request,headers))[0];
  expect(g.attributes.custom_tags).toContain("rec:v1:occasion:shopping:deny");expect(g.description.evidence.fields.descriptive_tags.canonical_values).toEqual(["a literal note"]);
  record("B002",{captured,garment:g});
});

test("B003 candidate raw prediction stays separate and chosen neckline transfers unchanged",async({page,request})=>{
  const headers=await owner(page,request);const job=await upload(page,request,headers,false);await page.goto("/extract/results?job="+job.id);
  await page.getByText("Edit details and review image",{exact:true}).click();
  const silhouette=page.getByRole("group",{name:"Visible silhouette",exact:true});await expect(silhouette).toContainText("Model suggestion: loose");
  expect(job.items[0].attributes.fit).toBeNull();
  await setValue(page,"Neckline","square");
  const response=page.waitForResponse(r=>r.url().endsWith("/review")&&r.request().method()==="POST");
  await page.getByRole("button",{name:"Accept candidate",exact:true}).click();expect((await response).status()).toBe(200);
  const savedResponse=page.waitForResponse(r=>r.url().endsWith("/confirm")&&r.request().method()==="POST");
  await page.getByRole("button",{name:"Save selected garments",exact:true}).click();expect((await savedResponse).status()).toBe(201);
  const g=(await garments(request,headers))[0];expect(g.description.evidence.fields.neckline.canonical_values).toEqual(["square"]);
  expect(g.description.evidence.fields.neckline.suggestion.value).toEqual(["crew"]);
  expect(g.description.source_qualified.neckline).toBe(true);expect(g.style_confirmation.source).toBeNull();
  record("B003",{job,garment:g});
});

test("B004 complete finite dropdowns, rare values and exact palette coverage",async({page,request})=>{
  const headers=await owner(page,request);await upload(page,request,headers);await edit(page);
  const labels=JSON.parse(readFileSync(process.env.SMART_WARDROBE_B0_LABELS!,"utf8")) as {cases:{id:string;field?:string;expected_canonical_values?:unknown[]}[]};
  for(const [field,label] of [["category","Category"],["style","Style"],["pattern","Pattern"],["material","Material"],["silhouette","Visible silhouette"],["neckline","Neckline"],["sleeve_length","Sleeve length"]]){
    const expected=[...new Set(labels.cases.filter(c=>c.id.startsWith("F")&&c.field===field).flatMap(c=>c.expected_canonical_values??[]))].sort();
    await page.getByRole("combobox",{name:label+" action",exact:true}).selectOption("set");
    const control=page.getByLabel(label+(field==="style"||field==="material"?" values":" value"),{exact:true});
    expect((await control.locator("option").evaluateAll(nodes=>nodes.map(n=>(n as HTMLOptionElement).value).filter(Boolean))).sort()).toEqual(expected);
    await page.getByRole("combobox",{name:label+" action",exact:true}).selectOption("keep");
  }
  await setValue(page,"Visible silhouette","mermaid");await setValue(page,"Neckline","queen anne");await setValue(page,"Sleeve length","elbow-length");
  await page.getByRole("combobox",{name:"Palette and coverage action",exact:true}).selectOption("set");await page.getByRole("button",{name:"Add palette entry",exact:true}).click();
  await page.getByLabel("Palette colour 1",{exact:true}).fill("#123abc");await page.getByLabel("Palette coverage 1",{exact:true}).fill("0.500000");
  await page.getByRole("button",{name:"Save changes",exact:true}).click();await expect(page.getByText("Garment updated.",{exact:true})).toBeVisible();
  const g=(await garments(request,headers))[0];expect(g.description.evidence.fields.colour_palette.canonical_values).toEqual([{hex:"#123abc",coverage:"0.500000"}]);
  expect(g.description.evidence.fields.silhouette.canonical_values).toEqual(["mermaid"]);record("B004",g);
});

test("B005 optional description controls support keyboard and all named widths",async({page,request})=>{
  const headers=await owner(page,request);await upload(page,request,headers,true,10);await edit(page);
  const action=page.getByRole("combobox",{name:"Neckline action",exact:true});await action.focus();await expect(action).toBeFocused();await page.keyboard.press("ArrowDown");await page.keyboard.press("Enter");
  const layouts=[];for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:1000});const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));expect(layout.scroll).toBeLessThanOrEqual(width);layouts.push(layout);}
  await page.screenshot({path:join(folder,"B005-controls.png"),fullPage:true});record("B005",layouts);
});

test("B006 native Chrome 200 percent zoom retains optional editor",async({request})=>{
  const context=await chromium.launchPersistentContext(mkdtempSync(join(tmpdir(),"description-zoom-")),{channel:"chrome",headless:true,baseURL:"http://127.0.0.1:3100",viewport:null,args:["--window-size=1440,1000"]});
  try{const page=context.pages()[0];const headers=await owner(page,request);await upload(page,request,headers);
    const settings=await context.newPage();await settings.goto("chrome://settings");
    const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{const c=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};c.chrome.settingsPrivate.setDefaultZoom(2,()=>c.chrome.settingsPrivate.getDefaultZoom(resolve));}));await settings.close();
    await edit(page);await setValue(page,"Colour temperature","neutral");const metrics=await page.evaluate(()=>({dpr:devicePixelRatio,scale:visualViewport!.scale,width:innerWidth,scroll:document.documentElement.scrollWidth,cssZoom:getComputedStyle(document.body).zoom}));
    expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe("1");expect(metrics.scroll).toBeLessThanOrEqual(metrics.width);
    const cdp=await context.newCDPSession(page);const screenshot=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true,captureBeyondViewport:false});writeFileSync(join(folder,"B006-native-zoom.png"),Buffer.from(screenshot.data,"base64"));await cdp.detach();record("B006",metrics);
  }finally{await context.close();}
});

test("B007 Cancel descriptions preserves an unsaved image choice",async({page,request})=>{
  const headers=await owner(page,request);const job=await upload(page,request,headers,false,20);const alternate=await upload(page,request,headers,false,21);
  expect((await request.post(api+"/processing/jobs/"+job.id+"/review",{headers,data:{items:[{item_id:job.items[0].id,decision:"accepted"}]}})).status()).toBe(200);
  // Synthetic transport fixture supplies a different owned preview; no model
  // runs and no changed representation is submitted to the backend.
  await page.route("**/processing/jobs/"+job.id,async route=>{
    if(route.request().method()!=="GET"){await route.continue();return;}
    const response=await route.fetch();const data=await response.json();data.items[0].vtoff_media_id=alternate.items[0].crop_media_id;await route.fulfill({response,json:data});
  });
  await page.goto("/extract/results?job="+job.id);await page.getByText("Edit details and review image",{exact:true}).click();
  await page.locator('input[type="radio"][value="vtoff"]').check();
  await expect(page.getByRole("button",{name:"Save selected garments",exact:true})).toBeDisabled();
  let writes=0;page.on("request",r=>{if(r.method()==="POST"&&(r.url().endsWith("/review")||r.url().endsWith("/confirm")))writes++;});
  await setValue(page,"Neckline","square");await page.getByRole("button",{name:"Cancel description changes",exact:true}).click();
  await expect(page.getByRole("button",{name:"Save selected garments",exact:true})).toBeDisabled();
  expect(writes).toBe(0);record("B007",{unsavedImageRetained:true,writes,syntheticOwnedPreview:true});
});
