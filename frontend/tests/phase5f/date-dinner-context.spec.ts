import { test, expect, chromium, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const password = "General-disposable-password-123";
const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const record = (name: string, value: unknown) => writeFileSync(resolve(folder, name + ".json"), JSON.stringify(value, null, 2));
async function setup(page: Page, request: APIRequestContext, label: string) {
  const email = `date-dinner-${label}@example.test`;
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "Date Dinner Owner" } })).status()).toBe(201);
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
  expect((await request.post(base + "/review", { headers, data: { items: [{ item_id: item, decision: "accepted", name, category: "vest_dress", primary_colour: "blue", attributes: { style: ["casual"] } }] } })).status()).toBe(200);
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

test("date dinner common review explicit restrictions immutable history and source eligibility", async ({ page, request, browser }) => {
  const { headers, gid, name } = await setup(page, request, "selection");
  const missing = await ask(page, "I'm going on a date");
  expect(missing.outcome).toBe("Selected"); // Approved 1.4 saved-style transition.
  await expect(page.getByTestId("recommendation-result")).toContainText("saved, unreviewed style");
  await review(page, gid);
  const selected = await ask(page, "I'm going on a date at a restaurant");
  expect(selected.outcome).toBe("Selected");
  const result = page.getByTestId("recommendation-result");
  await expect(result).toContainText("No dress code was supplied");
  await expect(result).toContainText("Stated venue: restaurant");
  await expect(result).not.toContainText("Guest role assumed");
  await expect(result).toContainText("inferred from reviewed style attributes");
  await expect(result.getByText(name, { exact: true })).toBeVisible();
  const layouts = [];
  for (const width of [360,390,768,1280,1920]) { await page.setViewportSize({ width, height: 960 }); layouts.push(await bounds(page)); }
  await page.setViewportSize({ width: 360, height: 960 });
  await page.screenshot({ path: resolve(folder,"date-result-360.png"), fullPage: true });
  await result.getByRole("button", { name: "Save as outfit", exact: true }).click();
  await expect(result.getByRole("button", { name: "Saved as outfit", exact: true })).toBeVisible();
  const prepared = await request.post(api+"/visualisations/prepare", { headers, data: { recommendation_id: selected.recommendation.id } });
  expect(prepared.status()).toBe(200);
  expect((await prepared.json()).items.map((item: { garment_id: string }) => item.garment_id)).toEqual([gid]);
  await page.goto("/history"); await page.getByLabel("Search original requests").fill("date");
  await page.getByRole("button", { name: "Search history", exact: true }).focus(); await page.keyboard.press("Enter");
  await page.getByRole("link", { name: "Open completed interaction" }).first().focus(); await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Context suggestion basis" })).toContainText("Stated venue: restaurant");
  const historical = await (await request.get(api+"/chats/"+selected.recommendation.chat_id,{ headers })).json();
  expect(historical.recommendation.provenance).toEqual(selected.recommendation.provenance);
  const dinner = await ask(page,"I'm meeting friends for dinner at a restaurant"); expect(dinner.outcome).toBe("Selected");
  await expect(page.getByTestId("recommendation-result")).toContainText("friends");
  expect(dinner.score_metadata).toEqual(selected.score_metadata);
  const row = (await (await request.get(api+"/wardrobe/garments",{ headers })).json())[0];
  expect((await request.patch(api+`/wardrobe/garments/${gid}`,{ headers: { ...headers, "If-Match": row.tag_edit.revision },data: { attributes: { custom_tags: ["rec:v1:occasion:date:deny"] } } })).status()).toBe(200);
  const denied = [];
  for (const text of ["I'm going on a date", "Suggest an outfit for a date"]) { const outcome = await ask(page,text); expect(outcome.outcome).toBe("NoMatchingCandidates"); denied.push(outcome); }
  expect((await ask(page,"I'm going to dinner")).outcome).toBe("Selected");
  record("date-dinner-selection",{ browser: browser.version(), selected, dinner, historical, denied, layouts });
  for (const layout of layouts) { expect(layout.clipped).toEqual([]); expect(layout.outside).toBe(0); }
});

test("date dinner controlled formal compound weather and unavailable venue outcomes", async ({ page, request }) => {
  const { gid } = await setup(page,request,"unsupported"); await review(page,gid);
  const outcomes = [];
  for (const [text, expected] of [["I'm going on a formal date","PolicyUnavailable"],["I'm going to dinner at a hotel","PolicyUnavailable"],["I'm going on a dinner date","UnsupportedRequest"],["I'm going to dinner in hot weather","UnsupportedRequest"],["I'm going hiking","PolicyUnavailable"]]) {
    const result = await ask(page,text); expect(result.outcome).toBe(expected); outcomes.push({ text,result });
  }
  record("date-dinner-controlled",outcomes);
});

test("date dinner native 200 percent explanation and long-name actions", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "wardrobe-general-context-zoom-"));
  const context = await chromium.launchPersistentContext(profile, { channel: "chrome", headless: true, baseURL: "http://127.0.0.1:3100", viewport: null, args: ["--window-size=1440,1000"] });
  try {
    const page = context.pages()[0], { gid, name } = await setup(page, request, "date-zoom");
    await review(page, gid);
    const settings = await context.newPage(); await settings.goto("chrome://settings");
    const zoom = await settings.evaluate(() => new Promise<number>(resolve => {
      const browser = globalThis as unknown as { chrome: { settingsPrivate: { setDefaultZoom: (value: number, callback: () => void) => void; getDefaultZoom: (callback: (value: number) => void) => void } } };
      browser.chrome.settingsPrivate.setDefaultZoom(2, () => browser.chrome.settingsPrivate.getDefaultZoom(resolve));
    })); await settings.close();
    const selected = await ask(page, "I'm going out for dinner tonight");
    expect(selected.outcome).toBe("Selected");
    const result = page.getByTestId("recommendation-result");
    await expect(result.getByText(name, { exact: true })).toBeVisible();
    await expect(result.getByRole("region", { name: "Context suggestion basis" })).toContainText("inferred from reviewed style attributes");
    const layout = await bounds(page);
    const metrics = await page.evaluate(() => ({ innerWidth, outerWidth, dpr: devicePixelRatio, scale: visualViewport!.scale, cssZoom: getComputedStyle(document.body).zoom }));
    await result.getByRole("button", { name: "Save as outfit", exact: true }).click();
    await expect(result.getByRole("button", { name: "Saved as outfit", exact: true })).toBeVisible();
    await page.goto("/history/" + selected.recommendation.chat_id);
    await expect(page.getByRole("region", { name: "Context suggestion basis" })).toContainText("No dress code was supplied");
    const history = await bounds(page);
    const cdp = await context.newCDPSession(page);
    const shot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
    writeFileSync(resolve(folder, "date-dinner-native-zoom.png"), Buffer.from(shot.data, "base64")); await cdp.detach();
    record("date-dinner-native-zoom", { zoom, metrics, layout, history, profile });
    expect(zoom).toBe(2); expect(metrics.dpr).toBe(2); expect(metrics.scale).toBe(1); expect(metrics.cssZoom).toBe("1");
    for (const state of [layout, history]) { expect(state.clipped).toEqual([]); expect(state.outside).toBe(0); }
  } finally { await context.close(); }
});
