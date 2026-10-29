import { test, expect, chromium, type Page } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const folder = process.env.OWNER_STYLE_EVIDENCE!;
const record = (name: string, value: unknown) => writeFileSync(join(folder, name + ".json"), JSON.stringify(value, null, 2));
async function register(page: Page) {
  const email = `style-${crypto.randomUUID()}@example.test`, password = "Disposable-style-password-123";
  await page.goto("/auth"); await page.getByRole("button", { name: "Register", exact: true }).click();
  await page.getByLabel("Full name", { exact: true }).fill("Disposable Style Owner");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create private account", exact: true }).click();
  await expect(page.getByText("Account created. Sign in to continue.", { exact: true })).toBeVisible();
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.locator("form").getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("/");
}
async function rows(page: Page) {
  return page.evaluate(async () => (await fetch("/api/v1/wardrobe/garments", { headers: { Authorization: "Bearer " + sessionStorage.getItem("smart_wardrobe_access_token") } })).json());
}
async function upload(page: Page, explicit: boolean) {
  // Retain the explicitly versioned legacy owner-confirmation journey; the new suite tests automatic default Add.
  await page.route("**/api/v1/processing/jobs?admission_mode=automatic_structural_v1", route => route.continue({ url: route.request().url().replace("admission_mode=automatic_structural_v1", "admission_mode=manual_review_v1") }));
  await page.goto("/extract"); await page.getByLabel("Wardrobe image", { exact: true }).setInputFiles(join(folder,"synthetic.png"));
  await page.waitForURL(/\/extract\/results/);
  const candidate = page.getByRole("article").first();
  await candidate.getByText("Edit details and review image", { exact: true }).click();
  await candidate.getByLabel("Category", { exact: true }).selectOption("vest_dress");
  await candidate.getByLabel("Garment name", { exact: true }).fill("Synthetic blue dress " + "x".repeat(79));
  await candidate.getByLabel("Primary colour", { exact: true }).fill("blue");
  if (explicit) await candidate.getByRole("combobox", { name: /^Style/ }).selectOption("casual");
  await candidate.getByRole("button", { name: "Accept candidate", exact: true }).click();
  await expect(candidate.getByText("Review: accepted", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Save selected garments", exact: true }).click();
  await page.waitForURL("/wardrobe");
  return (await rows(page))[0];
}
async function ask(page: Page, text: string) {
  await page.goto("/assistant"); await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(text);
  await page.getByLabel("What would you like to wear?", { exact: true }).focus(); await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Suggest an outfit", exact: true })).toBeFocused();
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.keyboard.press("Enter"); return (await response).json();
}
async function visibleOutcome(page: Page) {
  const outcome = page.getByRole("region", { name: "Recommendation outcome", exact: true });
  await expect(outcome).toBeFocused();
  const box = await outcome.locator("h2").first().boundingBox();
  expect(box).not.toBeNull(); expect(box!.y).toBeGreaterThanOrEqual(0); expect(box!.y + box!.height).toBeLessThanOrEqual(await page.evaluate(() => innerHeight));
  const ordering = await page.evaluate(() => {
    const outcome = document.querySelector('[aria-label="Recommendation outcome"]')!, detail = document.querySelector('[aria-label="Understood situation"]');
    return !detail || !!(outcome.compareDocumentPosition(detail) & Node.DOCUMENT_POSITION_FOLLOWING);
  }); expect(ordering).toBe(true);
  return box;
}
async function bounds(page: Page) {
  return page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth,
    outside: [...document.querySelectorAll<HTMLElement>('#main-content button,#main-content input,#main-content a,#main-content select')].filter(e => e.getClientRects().length).filter(e => { const r=e.getBoundingClientRect();return r.left < -1 || r.right > document.documentElement.clientWidth+1; }).length }));
}

test("ordinary UI Add confirms once, recommends, saves and preserves history", async ({page,browser}) => {
  await register(page); let separateReviews=0;
  page.on("request", r => { if(r.url().includes("/contextual-suitability") && r.method()==="POST") separateReviews++; });
  const row=await upload(page,true); expect(row.contextual_edit.review_current).toBe(true);expect(row.style_confirmation.source).toBe("candidate_accept");
  const shopping=await ask(page,"I'm going shopping");expect(shopping.outcome).toBe("Selected");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  expect(shopping.recommendation.items.map((i:{garment_id:string})=>i.garment_id)).toEqual([row.id]);
  expect(shopping.recommendation.total_score).toBe(.7);
  const campus=await ask(page,"I'm going to class");expect(campus.outcome).toBe("Selected");expect(campus.recommendation.score_metadata).toEqual(shopping.recommendation.score_metadata);
  const layouts=[];
  for(const width of [360,390,768,1280,1920]) { await page.setViewportSize({width,height:844});await expect(page.getByTestId("recommendation-result")).toContainText(row.name);const b=await bounds(page);expect(b.scroll).toBeLessThanOrEqual(b.width);expect(b.outside).toBe(0);layouts.push(b); }
  await page.getByTestId("recommendation-result").getByRole("button",{name:"Save as outfit",exact:true}).click();await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeVisible();
  await page.goto('/history/'+campus.recommendation.chat_id);await expect(page.getByTestId("recommendation-result")).toContainText(row.name);
  const current=(await rows(page))[0];
  const denied=await page.evaluate(async g=>(await fetch('/api/v1/wardrobe/garments/'+g.id,{method:'PATCH',headers:{Authorization:'Bearer '+sessionStorage.getItem('smart_wardrobe_access_token'),'Content-Type':'application/json','If-Match':g.tag_edit.revision},body:JSON.stringify({attributes:{custom_tags:['rec:v1:occasion:shopping:deny']}})})).status,current);
  expect(denied).toBe(200);expect((await ask(page,"I'm going shopping")).outcome).toBe('NoMatchingCandidates');await visibleOutcome(page);
  await page.goto('/history/'+campus.recommendation.chat_id);await expect(page.getByTestId("recommendation-result")).toContainText(row.name);
  expect(separateReviews).toBe(0);record("add-result",{browser:browser.version(),separateReviews,layouts,shopping,campus});
});

test("ordinary Edit same style, Cancel, failed save and stale revision", async ({page}) => {
  await register(page);const row=await upload(page,false);expect(row.contextual_edit.review_current).toBe(false);
  await page.setViewportSize({width:390,height:844});expect((await ask(page,"I'm going shopping")).outcome).toBe("InsufficientEvidence");await visibleOutcome(page);
  await page.goto('/wardrobe');const card=page.locator(`[data-garment-id="${row.id}"]`);
  await card.getByRole('button',{name:'Edit',exact:true}).click();await card.getByLabel('Styles (comma-separated)',{exact:true}).fill('casual');await card.getByRole('button',{name:'Cancel',exact:true}).click();
  expect((await rows(page))[0].contextual_edit.review_current).toBe(false);
  await card.getByRole('button',{name:'Edit',exact:true}).click();await card.getByLabel('Styles (comma-separated)',{exact:true}).fill('casual');
  const route=`**/wardrobe/garments/${row.id}`;await page.route(route,r=>r.abort('failed'));
  await card.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.locator('#main-content').getByRole('alert')).toBeVisible();
  await expect(card.getByLabel('Styles (comma-separated)',{exact:true})).toHaveValue('casual');expect((await rows(page))[0].contextual_edit.review_current).toBe(false);await page.unroute(route);
  await page.evaluate(async id=>{await fetch('/api/v1/wardrobe/garments/'+id,{method:'PATCH',headers:{Authorization:'Bearer '+sessionStorage.getItem('smart_wardrobe_access_token'),'Content-Type':'application/json'},body:JSON.stringify({name:'Concurrent synthetic edit'})});},row.id);
  await card.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.locator('#main-content').getByRole('alert')).toContainText('changed');expect((await rows(page))[0].contextual_edit.review_current).toBe(false);
  await page.reload();const refreshed=page.locator(`[data-garment-id="${row.id}"]`);await refreshed.getByRole('button',{name:'Edit',exact:true}).click();await refreshed.getByLabel('Styles (comma-separated)',{exact:true}).fill('casual');await refreshed.getByRole('button',{name:'Save changes',exact:true}).click();await expect(refreshed.getByRole('button',{name:'Edit',exact:true})).toBeVisible();
  expect((await rows(page))[0].style_confirmation.source).toBe('garment_edit');expect((await ask(page,"I'm going shopping")).outcome).toBe('Selected');
  record('edit-protection',{cancel:true,failedSave:true,staleRejected:true,normalSaveSelected:true});
});

test("clear no-result before explanations across widths, versions and technical retry", async ({page}) => {
  await register(page);await upload(page,false);const observations=[];
  for(const width of [1280,390]) {
    await page.setViewportSize({width,height:width===390?844:720});
    for(const [text,expected] of [["I'm going shopping","InsufficientEvidence"],["I have a job interview","PolicyUnavailable"],["I'm going shopping; the dress code is formal","PolicyUnavailable"]]) {
      const response=await ask(page,text);expect(response.outcome).toBe(expected);observations.push({width,outcome:expected,box:await visibleOutcome(page)});
    }
  }
  await page.route('**/recommendations?pipeline=integrated',async route=>{const response=await route.fetch();const value=await response.json();if(value.context_summary)value.context_summary.version='future-unknown';await route.fulfill({response,json:value});});
  expect((await ask(page,"I'm going shopping")).outcome).toBe('InsufficientEvidence');await visibleOutcome(page);await page.unroute('**/recommendations?pipeline=integrated');
  await page.route('**/recommendations?pipeline=integrated',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Synthetic unavailable'})}));
  await ask(page,"I'm going shopping");await expect(page.getByRole('heading',{name:'Request could not be completed'})).toBeVisible();await visibleOutcome(page);
  await page.unroute('**/recommendations?pipeline=integrated');await page.getByRole('button',{name:'Retry same request',exact:true}).click();await expect(page.getByRole('heading',{name:'No outfit generated',exact:true})).toBeVisible();await visibleOutcome(page);
  await page.screenshot({path:join(folder,'outcome-390.png')});record('outcome-visibility',observations);
});

test("native Chrome 200 percent outcome and keyboard", async () => {
  const profile=mkdtempSync(join(tmpdir(),'owner-style-zoom-'));
  const context=await chromium.launchPersistentContext(profile,{channel:'chrome',headless:true,baseURL:process.env.SMART_WARDROBE_BROWSER_BASE_URL ?? 'http://127.0.0.1:3180',viewport:null,args:['--window-size=1440,1000']});
  try {
    const page=context.pages()[0];await register(page);await upload(page,false);
    const settings=await context.newPage();await settings.goto('chrome://settings');
    const zoom=await settings.evaluate(()=>new Promise<number>(resolve=>{const c=globalThis as unknown as {chrome:{settingsPrivate:{setDefaultZoom:(v:number,cb:()=>void)=>void;getDefaultZoom:(cb:(v:number)=>void)=>void}}};c.chrome.settingsPrivate.setDefaultZoom(2,()=>c.chrome.settingsPrivate.getDefaultZoom(resolve));}));await settings.close();
    expect((await ask(page,"I'm going shopping")).outcome).toBe('InsufficientEvidence');const box=await visibleOutcome(page),layout=await bounds(page),metrics=await page.evaluate(()=>({dpr:devicePixelRatio,scale:visualViewport!.scale,cssZoom:getComputedStyle(document.body).zoom,width:innerWidth}));
    expect(zoom).toBe(2);expect(metrics.dpr).toBe(2);expect(metrics.scale).toBe(1);expect(metrics.cssZoom).toBe('1');expect(layout.outside).toBe(0);
    const cdp=await context.newCDPSession(page);const shot=await cdp.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});writeFileSync(join(folder,'outcome-native-zoom.png'),Buffer.from(shot.data,'base64'));await cdp.detach();record('native-zoom',{zoom,metrics,layout,box});
  } finally { await context.close(); }
});
