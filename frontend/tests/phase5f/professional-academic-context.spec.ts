import { test, expect, chromium, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const password = "General-disposable-password-123";
const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const record = (name: string, value: unknown) => writeFileSync(resolve(folder, name + ".json"), JSON.stringify(value, null, 2));
async function setup(page: Page, request: APIRequestContext, label: string) {
  const email = `professional-${label}@example.test`;
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

test("academic explicit role provisional appearance history save and Campus Deny", async ({ page, request, browser }) => {
  const { headers, gid, name } = await setup(page,request,"academic"); await review(page,gid);
  const missing = await ask(page,"I have a presentation at university"); expect(missing.outcome).toBe("PolicyUnavailable");
  await expect(page.getByRole("region",{ name:"Understood situation" })).toContainText("Missing context: role");
  const selected = await ask(page,"I'm presenting my project at university tomorrow"); expect(selected.outcome).toBe("Selected");
  const result = page.getByTestId("recommendation-result");
  await expect(result).toContainText("Stated role: presenter"); await expect(result).toContainText("provisional university-presenter");
  await expect(result.getByText(name,{exact:true})).toBeVisible();
  const layouts=[];
  for (const width of [360,390,768,1280,1920]) { await page.setViewportSize({width,height:960}); layouts.push(await bounds(page)); }
  await page.setViewportSize({width:360,height:960});await page.screenshot({path:resolve(folder,"academic-result-360.png"),fullPage:true});
  await result.getByRole("button",{name:"Save as outfit",exact:true}).click();await expect(result.getByRole("button",{name:"Saved as outfit",exact:true})).toBeVisible();
  const prepared=await request.post(api+"/visualisations/prepare",{headers,data:{recommendation_id:selected.recommendation.id}});expect(prepared.status()).toBe(200);
  await page.goto("/history/"+selected.recommendation.chat_id);await expect(page.getByRole("region",{name:"Context suggestion basis"})).toContainText("Stated role: presenter");
  const historical=await (await request.get(api+"/chats/"+selected.recommendation.chat_id,{headers})).json();expect(historical.recommendation.provenance).toEqual(selected.recommendation.provenance);
  const row=(await (await request.get(api+"/wardrobe/garments",{headers})).json())[0];
  expect((await request.patch(api+`/wardrobe/garments/${gid}`,{headers:{...headers,"If-Match":row.tag_edit.revision},data:{attributes:{custom_tags:["rec:v1:occasion:campus:deny"]}}})).status()).toBe(200);
  const denied=await ask(page,"Suggest an outfit for a university presentation as a presenter");expect(denied.outcome).toBe("NoMatchingCandidates");
  record("academic-selection",{browser:browser.version(),missing,selected,historical,denied,layouts});
  for (const layout of layouts) {expect(layout.clipped).toEqual([]);expect(layout.outside).toBe(0);}
});

test("interview reusable review failed-save preservation cancel and withdrawal", async ({page,request}) => {
  const {headers,gid}=await setup(page,request,"interview");await review(page,gid);
  const text="I'm attending a job interview as a candidate; the dress code is smart casual";
  expect((await ask(page,text)).outcome).toBe("InsufficientEvidence");
  await page.goto("/wardrobe");let card=page.locator(`[data-garment-id="${gid}"]`);await card.locator("summary").click();
  await card.getByLabel("structured shape",{exact:true}).selectOption("true");
  await card.getByLabel("Dated condition observation",{exact:true}).selectOption("clean_intact");
  await card.getByRole("button",{name:"I reviewed these appearance observations",exact:true}).click();await expect(card).toContainText("Current value-bound observations.");
  const selected=await ask(page,text);expect(selected.outcome).toBe("Selected");
  await expect(page.getByTestId("recommendation-result")).toContainText("additional owner-reviewed appearance observations");
  await expect(page.getByTestId("recommendation-result")).toContainText("structured shape: yes");
  await expect(page.getByTestId("recommendation-result")).toContainText("Dated condition observation: clean intact");
  expect((await ask(page,"I have a job interview tomorrow")).outcome).toBe("PolicyUnavailable");
  expect((await ask(page,"I'm attending a formal job interview as a candidate")).outcome).toBe("PolicyUnavailable");
  await page.goto("/wardrobe");card=page.locator(`[data-garment-id="${gid}"]`);await card.locator("summary").click();
  await card.getByLabel("structured shape",{exact:true}).selectOption("false");
  const route=`**/wardrobe/garments/${gid}/contextual-suitability`;await page.route(route,r=>r.abort("failed"));
  await card.getByRole("button",{name:"I reviewed these appearance observations",exact:true}).click();
  await expect(page.locator('p[role="alert"]')).toBeVisible();await expect(card.getByLabel("structured shape",{exact:true})).toHaveValue("false");
  await page.unroute(route);
  const stored=(await (await request.get(api+"/wardrobe/garments",{headers})).json())[0];expect(stored.attributes.appearance_evidence_v1.construction_features.structured_shape).toBe(true);
  await card.getByRole("button",{name:"Cancel appearance changes",exact:true}).click();await expect(card.getByLabel("structured shape",{exact:true})).toHaveValue("true");
  await card.getByRole("button",{name:"Withdraw appearance observations",exact:true}).click();await expect(card).toContainText("No current observations");
  expect((await ask(page,text)).outcome).toBe("InsufficientEvidence");
  record("interview-selection",{selected,failed_save_storage_preserved:true,cancel_restored:true,withdrawal_unknown:true});
});

test("professional context native 200 percent explanation and long-name actions", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "wardrobe-general-context-zoom-"));
  const context = await chromium.launchPersistentContext(profile, { channel: "chrome", headless: true, baseURL: "http://127.0.0.1:3100", viewport: null, args: ["--window-size=1440,1000"] });
  try {
    const page = context.pages()[0], { gid, name } = await setup(page, request, "professional-zoom");
    await review(page, gid);
    const token=(await page.evaluate(()=>sessionStorage.getItem("smart_wardrobe_access_token")))!;
    const headers={Authorization:`Bearer ${token}`};const row=(await (await request.get(api+"/wardrobe/garments",{headers})).json())[0];
    expect((await request.post(api+`/wardrobe/garments/${gid}/contextual-suitability`,{headers,data:{revision:row.appearance_edit.revision,appearance_review:{construction_features:{collared_neckline:null,tailored_cut:null,structured_shape:true},condition_observation:"clean_intact"}}})).status()).toBe(200);
    const settings = await context.newPage(); await settings.goto("chrome://settings");
    const zoom = await settings.evaluate(() => new Promise<number>(resolve => {
      const browser = globalThis as unknown as { chrome: { settingsPrivate: { setDefaultZoom: (value: number, callback: () => void) => void; getDefaultZoom: (callback: (value: number) => void) => void } } };
      browser.chrome.settingsPrivate.setDefaultZoom(2, () => browser.chrome.settingsPrivate.getDefaultZoom(resolve));
    })); await settings.close();
    const selected = await ask(page, "I'm attending a job interview as a candidate; the dress code is smart casual");
    expect(selected.outcome).toBe("Selected");
    const result = page.getByTestId("recommendation-result");
    await expect(result.getByText(name, { exact: true })).toBeVisible();
    await expect(result.getByRole("region", { name: "Context suggestion basis" })).toContainText("inferred from reviewed style attributes");
    const layout = await bounds(page);
    const metrics = await page.evaluate(() => ({ innerWidth, outerWidth, dpr: devicePixelRatio, scale: visualViewport!.scale, cssZoom: getComputedStyle(document.body).zoom }));
    await result.getByRole("button", { name: "Save as outfit", exact: true }).click();
    await expect(result.getByRole("button", { name: "Saved as outfit", exact: true })).toBeVisible();
    await page.goto("/history/" + selected.recommendation.chat_id);
    await expect(page.getByRole("region", { name: "Context suggestion basis" })).toContainText("additional owner-reviewed appearance observations");
    const history = await bounds(page);
    await page.getByRole("region",{name:"Context suggestion basis"}).scrollIntoViewIfNeeded();
    const cdp = await context.newCDPSession(page);
    const shot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
    writeFileSync(resolve(folder, "professional-native-zoom.png"), Buffer.from(shot.data, "base64")); await cdp.detach();
    record("professional-native-zoom", { zoom, metrics, layout, history, profile });
    expect(zoom).toBe(2); expect(metrics.dpr).toBe(2); expect(metrics.scale).toBe(1); expect(metrics.cssZoom).toBe("1");
    for (const state of [layout, history]) { expect(state.clipped).toEqual([]); expect(state.outside).toBe(0); }
  } finally { await context.close(); }
});
