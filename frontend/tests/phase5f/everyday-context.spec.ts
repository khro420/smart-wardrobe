import { test, expect, chromium, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const password = "General-disposable-password-123";
const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const record = (name: string, value: unknown) => writeFileSync(resolve(folder, name + ".json"), JSON.stringify(value, null, 2));
async function setup(page: Page, request: APIRequestContext, label: string) {
  const email = `everyday-${label}@example.test`;
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "General Owner" } })).status()).toBe(201);
  await page.goto("/auth");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.locator("form").getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("/");
  const token = (await page.evaluate(() => sessionStorage.getItem("smart_wardrobe_access_token")))!;
  const headers = { Authorization: `Bearer ${token}` };
  const buffer = Buffer.from(await page.evaluate(() => { const canvas = document.createElement("canvas"); canvas.width = 256; canvas.height = 256; canvas.getContext("2d")!.fillRect(0, 0, 256, 256); return canvas.toDataURL("image/png").split(",")[1]; }), "base64");
  const upload = await request.post(api + "/processing/jobs", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer } } });
  expect(upload.status()).toBe(202);
  const base = api + "/processing/jobs/" + (await upload.json()).id;
  await expect.poll(async () => (await (await request.get(base, { headers })).json()).status).toBe("review_required");
  const item = (await (await request.get(base, { headers })).json()).items[0].id;
  const name = "General" + "x".repeat(93);
  expect((await request.post(base + "/review", { headers, data: { items: [{ item_id: item, decision: "accepted", name, category: "vest_dress", primary_colour: "blue", attributes: { style: ["smart casual"] } }] } })).status()).toBe(200);
  const confirmed = await request.post(base + "/confirm", { headers, data: { save_mode: "garments", item_ids: [item] } });
  expect(confirmed.status()).toBe(201);
  return { headers, name, gid: (await confirmed.json()).garment_ids[0] as string };
}
async function ask(page: Page, text: string) {
  await page.goto("/assistant");
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  const input = page.getByLabel("What would you like to wear?");
  await input.focus(); await page.keyboard.type(text);
  const response = page.waitForResponse(response => response.url().includes("/recommendations?pipeline=integrated") && response.request().method() === "POST");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Suggest an outfit", exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  return (await response).json();
}
async function review(page: Page, gid: string) {
  await page.goto("/wardrobe");
  const card = page.locator(`[data-garment-id="${gid}"]`);
  await card.locator("summary").click();
  await card.getByRole("button", { name: "I reviewed the current style", exact: true }).click();
  await expect(card).toContainText("Reviewed for contextual inference.");
}
async function bounds(page: Page) {
  return page.evaluate(() => {
    const root = document.querySelector("#main-content")!, limit = document.documentElement.clientWidth;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), clipped: string[] = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent?.trim() || !node.parentElement?.getClientRects().length || ["SCRIPT", "STYLE"].includes(node.parentElement.tagName)) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      if ([...range.getClientRects()].some(r => r.width > 0 && (r.left < -1 || r.right > limit + 1))) clipped.push(node.textContent.trim());
    }
    const outside = [...root.querySelectorAll<HTMLElement>("button,input,textarea,a,select")].filter(e => e.getClientRects().length).filter(e => { const r = e.getBoundingClientRect(); return r.left < -1 || r.right > limit + 1; }).length;
    return { width: innerWidth, clientWidth: limit, documentWidth: document.documentElement.scrollWidth, clipped, outside };
  });
}


test("everyday three contexts reuse one style review exact history names and bounds", async ({page,request,browser}) => {
  const {headers,gid,name}=await setup(page,request,"three");
  const unknown=await ask(page,"I'm going shopping");expect(unknown.outcome).toBe("Selected"); // Approved 1.4 saved-style transition.
  await expect(page.getByTestId("recommendation-result")).toContainText("saved, unreviewed style");
  await review(page,gid);
  const cases=[
    ["I'm going to class","campus"], ["I have university tomorrow","campus"],
    ["I'm going shopping","shopping"], ["I'm going out with friends","casual_outing"]];
  const observations=[];
  for(const [text,target] of cases){
    const selected=await ask(page,text);expect(selected.outcome).toBe("Selected");
    const proof=selected.recommendation.provenance.general_context;
    expect(proof.declaration_target).toBe(target);expect(proof.formality).toBeNull();
    const result=page.getByTestId("recommendation-result");
    await expect(result).toContainText("provisional");
    await expect(result).toContainText("No dress code was inferred");
    await expect(result.getByText(name,{exact:true})).toBeVisible();
    const layouts=[];for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:960});layouts.push(await bounds(page));}
    await page.setViewportSize({width:360,height:960});await page.screenshot({path:resolve(folder,target+"-result-360-"+observations.length+".png"),fullPage:true});
    await result.getByRole("button",{name:"Save as outfit",exact:true}).click();await expect(result.getByRole("button",{name:"Saved as outfit",exact:true})).toBeVisible();
    expect((await request.post(api+"/visualisations/prepare",{headers,data:{recommendation_id:selected.recommendation.id}})).status()).toBe(200);
    await page.goto("/history/"+selected.recommendation.chat_id);
    await expect(page.getByRole("region",{name:"Context suggestion basis"})).toContainText("provisional");
    const historical=await(await request.get(api+"/chats/"+selected.recommendation.chat_id,{headers})).json();
    expect(historical.recommendation.provenance).toEqual(selected.recommendation.provenance);
    expect(historical.recommendation.score_metadata).toEqual(selected.recommendation.score_metadata);
    layouts.push(await bounds(page));
    for(const layout of layouts){expect(layout.clipped).toEqual([]);expect(layout.outside).toBe(0);}
    observations.push({text,selected,historical,layouts});
  }
  const row=(await(await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect((await request.patch(api+`/wardrobe/garments/${gid}`,{headers:{...headers,"If-Match":row.tag_edit.revision},data:{attributes:{custom_tags:["rec:v1:occasion:campus:deny"]}}})).status()).toBe(200);
  const denied=await ask(page,"Suggest an outfit for class");expect(denied.outcome).toBe("NoMatchingCandidates");
  expect((await ask(page,"Suggest an outfit for shopping")).outcome).toBe("Selected");
  record("everyday-three-contexts",{browser:browser.version(),observations,denied,style_review_reused:true,no_appearance_review:true});
});

test("everyday explicit formality denied unavailable and specialised requests", async ({page,request}) => {
  const {headers,gid}=await setup(page,request,"conditions");await review(page,gid);
  const selected=await ask(page,"I'm going shopping; the dress code is smart casual");expect(selected.outcome).toBe("Selected");
  expect((await ask(page,"I'm going shopping; the dress code is casual")).outcome).toBe("InsufficientEvidence");
  const outcomes=[];
  for(const [text,expected] of [
    ["I'm going shopping; the dress code is formal","PolicyUnavailable"],
    ["I have a university presentation","PolicyUnavailable"], ["I have a job interview","PolicyUnavailable"],
    ["I'm attending a graduation as a guest","PolicyUnavailable"], ["I'm going hiking","PolicyUnavailable"],
    ["I'm going to a fitness class","UnsupportedRequest"], ["I want something smart casual","UnsupportedRequest"],
    ["I'm having dinner with my family","UnsupportedRequest"]]){
    const result=await ask(page,text);expect(result.outcome).toBe(expected);outcomes.push({text,result});
  }
  const row=(await(await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect((await request.patch(api+`/wardrobe/garments/${gid}`,{headers:{...headers,"If-Match":row.tag_edit.revision},data:{attributes:{custom_tags:["rec:v1:occasion:shopping:allow","rec:v1:formality:smart_casual:deny"]}}})).status()).toBe(200);
  const denied=await ask(page,"Suggest a smart casual outfit for shopping");expect(denied.outcome).toBe("NoMatchingCandidates");
  record("everyday-controlled-contexts",{selected,outcomes,denied});
});

test("everyday native 200 percent keyboard long-name history and saved actions", async ({request}) => {
  const profile=mkdtempSync(join(tmpdir(),"wardrobe-everyday-zoom-"));
  const context=await chromium.launchPersistentContext(profile,{channel:"chrome",headless:true,baseURL:"http://127.0.0.1:3100",viewport:null,args:["--window-size=1440,1000"]});
  try{
    const page=context.pages()[0],{name}=await setup(page,request,"zoom");
    const token=(await page.evaluate(()=>sessionStorage.getItem("smart_wardrobe_access_token")))!;
    const row=(await(await request.get(api+"/wardrobe/garments",{headers:{Authorization:`Bearer ${token}`}})).json())[0];
    await review(page,row.id);
    const settings=await context.newPage();await settings.goto("chrome://settings");
    const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{
      const browser=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};
      browser.chrome.settingsPrivate.setDefaultZoom(2,()=>browser.chrome.settingsPrivate.getDefaultZoom(resolve));
    }));await settings.close();
    const selected=await ask(page,"I'm going out with friends tonight");expect(selected.outcome).toBe("Selected");
    const result=page.getByTestId("recommendation-result");await expect(result.getByText(name,{exact:true})).toBeVisible();
    await expect(result).toContainText("Stated companions: friends");
    const layout=await bounds(page),metrics=await page.evaluate(()=>({innerWidth,outerWidth,dpr:devicePixelRatio,scale:visualViewport!.scale,cssZoom:getComputedStyle(document.body).zoom}));
    await result.getByRole("button",{name:"Save as outfit",exact:true}).click();await expect(result.getByRole("button",{name:"Saved as outfit",exact:true})).toBeVisible();
    await page.goto("/history/"+selected.recommendation.chat_id);await expect(page.getByRole("region",{name:"Context suggestion basis"})).toContainText("ordinary casual outing");
    const history=await bounds(page);const cdp=await context.newCDPSession(page);
    const shot=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true,captureBeyondViewport:false});
    writeFileSync(resolve(folder,"everyday-native-zoom.png"),Buffer.from(shot.data,"base64"));await cdp.detach();
    record("everyday-native-zoom",{zoom,metrics,layout,history,profile});
    expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe("1");
    for(const state of [layout,history]){expect(state.clipped).toEqual([]);expect(state.outside).toBe(0);}
  }finally{await context.close();}
});

test("everyday style review network failure and style draft cancel preservation", async ({page,request}) => {
  const {headers,gid}=await setup(page,request,"review-protection");
  await page.goto("/wardrobe");let card=page.locator(`[data-garment-id="${gid}"]`);
  await card.locator("summary").click();
  const reviewRoute=`**/wardrobe/garments/${gid}/contextual-suitability`;
  let reviewAttempts=0;
  await page.route(reviewRoute,r=>{reviewAttempts++;return r.abort("failed");});
  await card.getByRole("button",{name:"I reviewed the current style",exact:true}).click();
  await expect.poll(()=>reviewAttempts).toBe(1);
  await expect(page.locator("#main-content").getByRole("alert")).toBeVisible();
  let stored=(await(await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect(stored.contextual_edit.review_current).toBe(false);
  await page.unroute(reviewRoute);
  await card.getByRole("button",{name:"Edit",exact:true}).click();
  await card.getByLabel("Styles (comma-separated)",{exact:true}).fill("classic");
  await card.getByRole("button",{name:"Cancel",exact:true}).click();
  stored=(await(await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect(stored.style_tags).toEqual(["smart casual"]);
  await card.getByRole("button",{name:"Edit",exact:true}).click();
  await card.getByLabel("Styles (comma-separated)",{exact:true}).fill("classic");
  const editRoute=`**/wardrobe/garments/${gid}`;let editAttempts=0;
  await page.route(editRoute,r=>{editAttempts++;return r.abort("failed");});
  await card.getByRole("button",{name:"Save changes",exact:true}).click();
  await expect.poll(()=>editAttempts).toBe(1);
  await expect(card.getByLabel("Styles (comma-separated)",{exact:true})).toHaveValue("classic");
  stored=(await(await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect(stored.style_tags).toEqual(["smart casual"]);expect(stored.contextual_edit.review_current).toBe(false);
  await page.unroute(editRoute);
  await card.getByRole("button",{name:"Cancel",exact:true}).click();
  await review(page,gid);card=page.locator(`[data-garment-id="${gid}"]`);
  await expect(card).toContainText("Reviewed for contextual inference.");
  const selected=await ask(page,"I'm going shopping");expect(selected.outcome).toBe("Selected");
  record("everyday-review-preservation",{reviewAttempts,editAttempts,cancel_preserved:true,failed_save_preserved_draft_and_storage:true,selected});
});
