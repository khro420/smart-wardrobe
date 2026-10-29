import { test, expect, chromium, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const api = "http://127.0.0.1:3101/api/v1";
const texts = ["I'm going shopping.", "I'm going to class.", "I'm going out with friends.", "I'm going on a date tonight.", "I'm meeting friends for dinner."];
const record = (name: string, data: unknown) => writeFileSync(join(folder, name + ".json"), JSON.stringify(data, null, 2));

async function register(page: Page) {
  const email = `relative-${crypto.randomUUID()}@example.test`, password = "Disposable-relative-password-123";
  await page.goto("/auth"); await page.getByRole("button", { name: "Register", exact: true }).click();
  await page.getByLabel("Full name", { exact: true }).fill("Disposable Ranking Owner");
  await page.getByLabel("Email", { exact: true }).fill(email); await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create private account", exact: true }).click();
  await expect(page.getByText("Account created. Sign in to continue.", { exact: true })).toBeVisible();
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.locator("form").getByRole("button", { name: "Sign in", exact: true }).click(); await page.waitForURL("/");
  const token = (await page.evaluate(() => sessionStorage.getItem("smart_wardrobe_access_token")))!;
  return { Authorization: `Bearer ${token}` };
}
async function image(page: Page, code: number) {
  return Buffer.from(await page.evaluate(value => { const c = document.createElement("canvas"); c.width = c.height = 256; const x = c.getContext("2d")!; x.fillStyle = `rgb(${value},70,180)`; x.fillRect(0, 0, 256, 256); return [...Uint8Array.from(atob(c.toDataURL("image/png").split(",")[1]), ch => ch.charCodeAt(0))]; }, code));
}
async function add(page: Page, code: number) {
  const buffer = await image(page, code); await page.goto("/extract");
  await page.getByLabel("Wardrobe image", { exact: true }).setInputFiles({ name: "synthetic.png", mimeType: "image/png", buffer });
  await page.waitForURL(/\/extract\/results/);
  await expect(page.getByRole("status").filter({ hasText: "automatically added" })).toBeVisible();
}
async function seed(page: Page, request: APIRequestContext, headers: Record<string, string>, codes = [20,21,22,23,24,25,26,27]) {
  for (const code of codes) {
    const result = await request.post(api + "/processing/jobs?admission_mode=automatic_structural_v1", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer: await image(page, code) } } });
    expect(result.status()).toBe(202); const job = await result.json();
    await expect.poll(async () => (await (await request.get(api + "/processing/jobs/" + job.id, { headers })).json()).status).toBe("completed");
  }
  return (await (await request.get(api + "/wardrobe/garments", { headers })).json()) as { id: string; name: string; tag_edit: { revision: string } }[];
}
async function ask(page: Page, text: string, keyboard = false) {
  await page.goto("/assistant"); await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(text);
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  if (keyboard) { await page.getByLabel("What would you like to wear?", { exact: true }).focus(); await page.keyboard.press("Tab"); await expect(page.getByRole("button", { name: "Suggest an outfit", exact: true })).toBeFocused(); await page.keyboard.press("Enter"); }
  else await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  return (await response).json();
}
async function bounds(page: Page) {
  return page.evaluate(() => {
    const root = document.querySelector("#main-content")!, width = document.documentElement.clientWidth, clipped: string[] = [];
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) { const n = walk.currentNode; if (!n.textContent?.trim() || !n.parentElement?.getClientRects().length || ["SCRIPT", "STYLE"].includes(n.parentElement.tagName)) continue; const r = document.createRange(); r.selectNodeContents(n); if ([...r.getClientRects()].some(b => b.width > 0 && (b.left < -1 || b.right > width + 1))) clipped.push(n.textContent.trim()); }
    return { width, scroll: document.documentElement.scrollWidth, clipped };
  });
}


async function clickAction(page: Page, label: string) {
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: label, exact: true }).click();
  return (await response).json();
}

test("RF01 automatic Add, unchanged first outfit and deterministic distinct sequence", async ({ page }) => {
  await register(page); let reviews = 0;
  page.on("request", r => { if (r.method() === "POST" && (/\/review$/.test(r.url()) || /\/confirm$/.test(r.url()) || r.url().includes("/contextual-suitability"))) reviews++; });
  for (let code=20;code<28;code++) await add(page,code);
  let result=await ask(page,texts[0],true);
  expect(result.items.map((i:{name:string})=>i.name)).toEqual(["Blue T-shirt","Blue Jeans"]);
  expect(result.scoring_display.version).toBe("assistant-scoring-display-2.2.0");
  const results=[result], signatures=new Set<string>();
  for(let ordinal=0;ordinal<4;ordinal++) {
    signatures.add(JSON.stringify(result.items.filter((i:{garment_role:string})=>i.garment_role!=="outerwear").map((i:{garment_id:string})=>i.garment_id)));
    expect(result.scoring_display.refinement.ordinal).toBe(ordinal);
    if(ordinal) await expect(page.getByLabel("Recommendation sequence")).toContainText("lower total");
    result=await clickAction(page,"Suggest another outfit");results.push(result);
    if(ordinal<3) expect(result.scoring_display.total).toEqual({numerator:"7",denominator:"10"});
  }
  expect(result.outcome).toBe("RefinementExhausted");expect(signatures.size).toBe(4);expect(reviews).toBe(0);
  await expect(page.getByRole("region",{name:"Recommendation outcome"})).toContainText("No other base outfit remains");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();record("RF01",{reviews,results});
});

test("RF02 exclusion draft Cancel, Apply, clear and immutable history", async ({ page, request }) => {
  const headers=await register(page);await seed(page,request,headers);const root=await ask(page,texts[3]);
  let posts=0;page.on("request",r=>{if(r.method()==="POST"&&r.url().includes("/recommendations?"))posts++;});
  await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();
  await expect(page.getByText("Hard exclusions for this request only. These are not your saved preferences.")).toBeVisible();
  await page.getByRole("button",{name:"Dresses",exact:true}).click();await page.getByRole("button",{name:"Cancel",exact:true}).click();expect(posts).toBe(0);
  await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();
  await page.getByRole("button",{name:"Dresses",exact:true}).click();const excluded=await clickAction(page,"Apply exclusions");
  expect(excluded.items.map((i:{name:string})=>i.name)).toEqual(["White Shirt","Black Trousers"]);
  expect(excluded.scoring_display.refinement.root_id).not.toBe(root.id);expect(excluded.scoring_display.refinement.ordinal).toBe(0);
  await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();
  await page.getByRole("button",{name:"Clear draft",exact:true}).click();const cleared=await clickAction(page,"Apply exclusions");
  expect(cleared.scoring_display.refinement.excluded_categories).toEqual([]);
  const history=await(await request.get(api+"/chats/"+root.chat_id,{headers})).json();expect(history.recommendation.scoring_display).toEqual(root.scoring_display);
  record("RF02",{root,excluded,cleared,posts});
});

test("RF03 exact retry and reload recover the same alternative action", async ({ page, request }) => {
  const headers=await register(page);await seed(page,request,headers);const root=await ask(page,texts[0]);
  const sent:unknown[]=[];let fail=true;
  await page.route("**/recommendations?pipeline=integrated",async route=>{
    const body=route.request().postDataJSON();sent.push(body);
    if(body.refinement?.kind==="alternative"&&fail){fail=false;await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({outcome:"PersistenceFailure",complete:false})});}else await route.continue();
  });
  await page.getByRole("button",{name:"Suggest another outfit",exact:true}).click();
  await expect(page.getByRole("button",{name:"Retry same request",exact:true})).toBeVisible();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  const response=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");
  let releasePrevious!: () => void;
  const previousGate = new Promise<void>(resolve => { releasePrevious = resolve; });
  await page.route("**/chats/" + root.chat_id, async route => { await previousGate; await route.continue(); });
  const previousRead = page.waitForRequest(r => r.url().endsWith("/chats/" + root.chat_id));
  await page.reload(); await previousRead;
  await expect(page.getByRole("button", { name: "New Chat", exact: true })).toBeDisabled();
  expect(sent).toHaveLength(1); releasePrevious();
  const child=await(await response).json();expect(child.outcome).toBe("Selected");
  expect(sent[0]).toEqual(sent[1]);expect(child.scoring_display.refinement.parent_id).toBe(root.id);
  await expect(page.getByLabel("Recommendation sequence")).toContainText("Alternative 1");record("RF03",{sent,child});
});

test("RF04 changed competitor refuses continuation and preserves prior card", async ({ page, request }) => {
  const headers=await register(page);const garments=await seed(page,request,headers);const root=await ask(page,texts[0]);
  const competitor=garments.find(g=>g.name==="Navy Dress")!;
  expect((await request.patch(api+"/wardrobe/garments/"+competitor.id,{headers,data:{name:"Changed disposable competitor"}})).status()).toBe(200);
  const changed=await clickAction(page,"Suggest another outfit");expect(changed.outcome).toBe("RefinementScopeChanged");
  await expect(page.getByRole("region",{name:"Recommendation outcome"})).toContainText("Start a fresh recommendation");
  await expect(page.getByTestId("recommendation-result")).toContainText("Blue T-shirt");record("RF04",{root,changed});
});

test("RF05 explicit hard conflict and excluding every base give honest outcomes", async ({ page, request }) => {
  const headers=await register(page);await seed(page,request,headers);await ask(page,"Suggest an outfit for shopping with trousers");
  await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();await page.getByRole("button",{name:"Trousers",exact:true}).click();
  const conflict=await clickAction(page,"Apply exclusions");expect(conflict.outcome).toBe("RefinementConflict");
  await ask(page,texts[0]);await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();
  await page.getByText("All garment categories",{exact:true}).click();
  for(const label of ["short sleeve top","long sleeve top","vest","sling","shorts","trousers","skirt","short sleeve dress","long sleeve dress","vest dress","sling dress"]) await page.getByLabel(label,{exact:true}).check();
  const empty=await clickAction(page,"Apply exclusions");expect(empty.outcome).toBe("InsufficientStructure");expect(empty.refinement_summary.cause).toBe("request_category_exclusion");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();record("RF05",{conflict,empty});
});

test("RF06 smart sequence, saved history and durable copied bearer denial", async ({ page, request }) => {
  const headers=await register(page);await seed(page,request,headers);const root=await ask(page,texts[3]);
  const child=await clickAction(page,"Suggest another outfit");expect(child.items.map((i:{name:string})=>i.name)).toEqual(["White Shirt","Black Trousers"]);
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click();await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  const exhausted=await clickAction(page,"Suggest another outfit");expect(exhausted.outcome).toBe("RefinementExhausted");
  await page.goto("/history/"+child.chat_id);await expect(page.getByLabel("Recommendation sequence")).toContainText("Alternative 1");
  await page.getByRole("button",{name:"Sign out",exact:true}).click();await page.waitForURL("/auth");
  const next=root.scoring_display.refinement.next_action;
  expect((await request.post(api+"/recommendations?pipeline=integrated",{headers,data:{request_text:root.request_text,...next}})).status()).toBe(401);record("RF06",{root,child,exhausted,logoutDenied:true});
});

test("RF07 full names, keyboard and optional controls across viewport widths", async ({ page, request }) => {
  const headers=await register(page);await seed(page,request,headers,[10]);await ask(page,texts[0],true);
  await expect(page.getByTestId("recommendation-result")).toContainText("x".repeat(79));
  await page.getByRole("button",{name:"Exclude garment categories",exact:true}).click();await page.getByText("All garment categories",{exact:true}).click();
  const layouts=[];for(const width of [360,390,768,1280,1920]){await page.setViewportSize({width,height:1000});const layout=await bounds(page);expect(layout.clipped).toEqual([]);expect(layout.scroll).toBeLessThanOrEqual(width);layouts.push(layout);}
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:join(folder,"RF07-narrow.png"),fullPage:true});record("RF07",layouts);
});
test("RF08 actual native 200 percent Chrome zoom retains visible outcome and full components", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "refinement-zoom-"));
  const context = await chromium.launchPersistentContext(profile, { channel: "chrome", headless: true, baseURL: "http://127.0.0.1:3100", viewport: null, args: ["--window-size=1440,1000"] });
  try {
    const page = context.pages()[0]; const headers = await register(page); await seed(page, request, headers, [10]);
    const settings = await context.newPage(); await settings.goto("chrome://settings");
    const zoom = await settings.evaluate(() => new Promise<number>(resolve => { const c = globalThis as unknown as { chrome: { settingsPrivate: { setDefaultZoom: (v: number, cb: () => void) => void; getDefaultZoom: (cb: (v: number) => void) => void } } }; c.chrome.settingsPrivate.setDefaultZoom(2, () => c.chrome.settingsPrivate.getDefaultZoom(resolve)); })); await settings.close();
    await ask(page, texts[0], true); await expect(page.getByLabel("Full R C P breakdown")).toBeVisible();
    await expect.poll(async () => { const heading = await page.getByRole("heading", { name: "Your outfit recommendation", exact: true }).boundingBox(), header = await page.getByRole("banner").boundingBox(); return !!heading && !!header && heading.y >= header.y + header.height && heading.y + heading.height <= await page.evaluate(() => innerHeight); }).toBe(true);
    const layout = await bounds(page); expect(layout.clipped).toEqual([]);
    const metrics = await page.evaluate(() => ({ dpr: devicePixelRatio, width: innerWidth, scale: visualViewport!.scale, cssZoom: getComputedStyle(document.body).zoom }));
    expect(zoom).toBe(2); expect(metrics.dpr).toBe(2); expect(metrics.scale).toBe(1); expect(metrics.cssZoom).toBe("1");
    const cdp = await context.newCDPSession(page), shot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false }); writeFileSync(join(folder, "RF08-native-zoom.png"), Buffer.from(shot.data, "base64")); await cdp.detach(); record("RF08", { zoom, metrics, layout });
  } finally { await context.close(); }
});


test("RF09 optional pre-submit exclusions and legacy-profile history", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers);
  const legacy = await ask(page, "Suggest an outfit");
  expect(legacy.scoring_display.version).toBe("assistant-scoring-display-1.0.0");
  await expect(page.getByRole("button", { name: "Suggest another outfit", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  const posts: unknown[] = []; page.on("request", r => { if (r.method() === "POST" && r.url().includes("/recommendations?pipeline=integrated")) posts.push(r.postDataJSON()); });
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(texts[3]);
  await page.getByRole("button", { name: "Exclude garment categories", exact: true }).click();
  await page.getByRole("button", { name: "Dresses", exact: true }).click();
  await page.getByRole("button", { name: "Apply exclusions", exact: true }).click(); expect(posts).toHaveLength(0);
  const root = await clickAction(page, "Suggest an outfit"); expect(posts).toHaveLength(1);
  expect(root.items.map((i: { name: string }) => i.name)).toEqual(["White Shirt", "Black Trousers"]);
  expect(root.scoring_display.refinement.ordinal).toBe(0);
  await page.goto("/history/" + legacy.chat_id); await expect(page.getByTestId("compatibility-explanation")).toBeVisible();
  expect((await (await request.get(api + "/chats/" + legacy.chat_id, { headers })).json()).recommendation.score_metadata).toEqual(legacy.score_metadata);
  await page.goto("/history/" + root.chat_id); await expect(page.getByLabel("Recommendation sequence")).toContainText("Initial option");
  record("RF09", { legacy, root, posts });
});

test("RF10 missing alternative evidence and ten-result cap have distinct outcomes", async ({ page, request }) => {
  const headers = await register(page); const garments = await seed(page, request, headers, [12,21,22,26]);
  const unknown = garments.find(g => g.name === "Synthetic missing style")!;
  expect((await request.patch(api + "/wardrobe/garments/" + unknown.id, { headers: { ...headers, "If-Match": unknown.tag_edit.revision }, data: { attributes: { custom_tags: ["rec:v1:occasion:dinner:allow"] } } })).status()).toBe(200);
  const root = await ask(page, texts[4]); expect(root.outcome).toBe("Selected");
  const missing = await clickAction(page, "Suggest another outfit"); expect(missing.outcome).toBe("RefinementInsufficientEvidence");
  await expect(page.getByRole("region", { name: "Recommendation outcome", exact: true })).toContainText("evidence");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.waitForURL("**/auth"); await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  const capHeaders = await register(page); await seed(page, request, capHeaders, Array(11).fill(10));
  let current = await ask(page, texts[0]);
  for (let step = 1; step <= 9; step++) { current = await clickAction(page, "Suggest another outfit"); expect(current.scoring_display.refinement.ordinal).toBe(step); }
  await expect(page.getByRole("button", { name: "Suggest another outfit", exact: true })).toBeDisabled();
  await expect(page.getByLabel("Recommendation sequence")).toContainText("ten");
  record("RF10", { root, missing, final: current });
});
