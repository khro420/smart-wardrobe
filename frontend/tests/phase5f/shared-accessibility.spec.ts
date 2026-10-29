import { test, expect, chromium, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const channel = process.env.SMART_WARDROBE_J19_BROWSER as "chrome" | "msedge";
const widths = [360, 375, 390, 412, 480, 639, 640, 641, 767, 768, 769, 1023, 1024, 1025, 1280, 1440, 1920];
const text = "Suggest a classic outfit";
const save = (name: string, value: unknown) => writeFileSync(resolve(folder, name + ".json"), JSON.stringify(value, null, 2));

async function setup(request: APIRequestContext, page: Page, name: string) {
  const email = `j19-${name}-${channel}@example.test`, password = "J19-disposable-password-123";
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "J19 " + name } })).status()).toBe(201);
  const response = await request.post(api + "/account/login", { data: { email, password } }); expect(response.status()).toBe(200);
  const token = (await response.json()).access_token as string, headers = { Authorization: `Bearer ${token}` };
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token", value), token);
  await page.goto("http://127.0.0.1:3100/wardrobe");
  const image = Buffer.from(await page.evaluate(() => { const canvas = document.createElement("canvas"); canvas.width = 256; canvas.height = 256; canvas.getContext("2d")!.fillRect(0, 0, 256, 256); return canvas.toDataURL("image/png").split(",")[1]; }), "base64");
  const uploaded = await request.post(api + "/processing/jobs", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer: image } } }); expect(uploaded.status()).toBe(202);
  const base = api + "/processing/jobs/" + (await uploaded.json()).id;
  await expect.poll(async () => (await (await request.get(base, { headers })).json()).status).toBe("review_required");
  const item = (await (await request.get(base, { headers })).json()).items[0].id;
  expect((await request.post(base + "/review", { headers, data: { items: [{ item_id: item, decision: "accepted", name: "J19 classic dress", category: "vest_dress", primary_colour: "blue", attributes: { style: ["classic"] } }] } })).status()).toBe(200);
  const confirmed = await request.post(base + "/confirm", { headers, data: { save_mode: "garments", item_ids: [item] } }); expect(confirmed.status()).toBe(201);
  return { headers, garmentId: (await confirmed.json()).garment_ids[0] as string };
}

async function layout(page: Page) {
  return page.evaluate(() => {
    const limit = document.documentElement.clientWidth;
    const root = document.querySelector("#main-content")!;
    const nodes = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), clipped: { tag: string; text: string; left: number; right: number }[] = [];
    while (nodes.nextNode()) {
      const node = nodes.currentNode, raw = node.textContent ?? "", start = raw.search(/\S/);
      if (start < 0 || !node.parentElement?.getClientRects().length || ["SCRIPT", "STYLE"].includes(node.parentElement.tagName)) continue;
      const range = document.createRange(); range.setStart(node, start); range.setEnd(node, raw.trimEnd().length);
      for (const rect of range.getClientRects()) if (rect.width > 0 && (rect.left < -1 || rect.right > limit + 1)) clipped.push({ tag: node.parentElement.tagName, text: raw.trim().slice(0, 110), left: rect.left, right: rect.right });
    }
    const controls = [...root.querySelectorAll<HTMLElement>("input,textarea,button,select,a,summary")].filter(element => element.getClientRects().length && !element.closest("[hidden]"));
    const outside = controls.filter(element => { const r = element.getBoundingClientRect(); return r.left < -1 || r.right > limit + 1; }).map(element => ({ tag: element.tagName, text: (element.textContent || element.getAttribute("aria-label") || "").trim().slice(0, 80) }));
    return { width: innerWidth, clientWidth: limit, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, clipped, outside };
  });
}

async function submit(page: Page) {
  await page.goto("http://127.0.0.1:3100/assistant");
  await page.getByLabel("What would you like to wear?").fill(text);
  const pending = page.waitForResponse(r => r.url().includes("pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const response = await pending; expect(response.status()).toBe(201);
  await expect(page.getByTestId("recommendation-result")).toBeVisible(); return response.json();
}

async function tabTo(page: Page, target: Locator, label: string, observations: unknown[]) {
  await expect(target).toBeVisible();
  for (let count = 0; count < 90; count++) {
    await page.keyboard.press("Tab");
    if (await target.evaluate(element => element === document.activeElement)) {
      const focus = await target.evaluate(element => { const s = getComputedStyle(element), r = element.getBoundingClientRect(); return { visible: element.matches(":focus-visible"), outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth, outlineColour: s.outlineColor, rect: { x: r.x, y: r.y, width: r.width, height: r.height } }; });
      observations.push({ label, tabs: count + 1, focus }); expect(focus.visible).toBe(true); expect(parseFloat(focus.outlineWidth)).toBeGreaterThan(0);
      await page.screenshot({ path: resolve(folder, "focus-" + label + ".png") }); return;
    }
  }
  throw new Error("Keyboard could not reach " + label);
}

test("viewport range and valid maximum-length garment name", async ({ page, request }) => {
  const owner = await setup(request, page, "viewports"); const records: unknown[] = [], problems: unknown[] = [];
  const sweep = async (state: string, values = widths) => {
    for (const width of values) {
      await page.setViewportSize({ width, height: 960 }); await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      const result = await layout(page); records.push({ state, ...result });
      if (result.documentWidth > result.clientWidth + 1 || result.clipped.length || result.outside.length) { problems.push({ state, ...result }); await page.screenshot({ path: resolve(folder, `${state}-${width}-failure.png`), fullPage: true }); }
      else if ([360, 768, 1920].includes(width)) await page.screenshot({ path: resolve(folder, `${state}-${width}.png`), fullPage: true });
    }
  };
  await page.goto("/assistant"); await expect(page.getByLabel("What would you like to wear?")).toBeVisible(); await sweep("assistant-draft");
  const selected = await submit(page); await sweep("assistant-result");
  await page.goto("/history"); await expect(page.getByRole("link", { name: "Open completed interaction" })).toBeVisible(); await sweep("history-list");
  await page.goto("/history/" + selected.chat_id); await expect(page.getByTestId("recommendation-result")).toBeVisible(); await sweep("history-detail");
  expect((await request.patch(api + "/wardrobe/garments/" + owner.garmentId, { headers: owner.headers, data: { name: "J19" + "x".repeat(97) } })).status()).toBe(200);
  await page.goto("/assistant"); await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?").fill(text);
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click(); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await sweep("maximum-name-result", [360, 390, 768, 1280, 1920]);
  save("viewport-results", { channel, records, problems }); expect(problems, "Retain clipped content even when body overflow-x hides a scrollbar").toEqual([]);
});

test("keyboard-only Assistant and history actions with visible focus", async ({ page, request }) => {
  await setup(request, page, "keyboard"); const observations: unknown[] = [];
  await page.goto("/assistant");
  await tabTo(page, page.getByLabel("What would you like to wear?"), "assistant-request", observations); await page.keyboard.type(text);
  await tabTo(page, page.getByRole("button", { name: "Suggest an outfit", exact: true }), "assistant-submit", observations);
  await page.keyboard.press("Enter"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await page.goto("/history"); await tabTo(page, page.getByLabel("Search original requests"), "history-input", observations); await page.keyboard.type("classic");
  await tabTo(page, page.getByRole("button", { name: "Search history", exact: true }), "history-search", observations); await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("matching");
  await tabTo(page, page.getByRole("link", { name: "Open completed interaction" }).first(), "history-open", observations); await page.keyboard.press("Enter");
  await expect(page.getByTestId("recommendation-result")).toBeVisible(); save("keyboard-results", { channel, observations, result: "PASS" });
});

test("native 200 percent zoom and required actions", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "wardrobe-j19-native-zoom-"));
  const context = await chromium.launchPersistentContext(profile, { channel, headless: true, viewport: null, args: ["--window-size=1440,1000"] });
  try {
    const page = context.pages()[0]; await setup(request, page, "zoom"); await page.goto("http://127.0.0.1:3100/assistant");
    const metrics = () => page.evaluate(() => ({ innerWidth, innerHeight, outerWidth, outerHeight, dpr: devicePixelRatio, scale: visualViewport!.scale, cssZoom: getComputedStyle(document.body).zoom }));
    const before = await metrics(); const settings = await context.newPage(); await settings.goto(channel === "chrome" ? "chrome://settings" : "edge://settings");
    const zoom = await settings.evaluate(() => new Promise<number>(resolve => {
      const browser = globalThis as unknown as { chrome: { settingsPrivate: { setDefaultZoom: (value: number, callback: () => void) => void; getDefaultZoom: (callback: (value: number) => void) => void } } };
      browser.chrome.settingsPrivate.setDefaultZoom(2, () => browser.chrome.settingsPrivate.getDefaultZoom(resolve));
    }));
    await settings.close(); await page.reload(); const after = await metrics();
    expect(zoom).toBe(2); expect(after.outerWidth).toBe(before.outerWidth); expect(after.dpr / before.dpr).toBeCloseTo(2); expect(before.innerWidth / after.innerWidth).toBeCloseTo(2, 1); expect(after.scale).toBe(1); expect(after.cssZoom).toBe("1");
    const observations: unknown[] = [], states: unknown[] = [];
    await tabTo(page, page.getByLabel("What would you like to wear?"), "zoom-request", observations); await page.keyboard.type(text);
    await tabTo(page, page.getByRole("button", { name: "Suggest an outfit", exact: true }), "zoom-submit", observations); await page.keyboard.press("Enter"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
    states.push({ state: "result", ...(await layout(page)) }); await page.screenshot({ path: resolve(folder, "zoom-result.png"), fullPage: true });
    await page.goto("http://127.0.0.1:3100/history"); await tabTo(page, page.getByLabel("Search original requests"), "zoom-history-input", observations); await page.keyboard.type("classic");
    await tabTo(page, page.getByRole("button", { name: "Search history", exact: true }), "zoom-history-search", observations); await page.keyboard.press("Enter"); await expect(page.getByRole("status")).toContainText("matching");
    states.push({ state: "history", ...(await layout(page)) }); await page.screenshot({ path: resolve(folder, "zoom-history.png"), fullPage: true });
    await tabTo(page, page.getByRole("link", { name: "Open completed interaction" }).first(), "zoom-history-open", observations); await page.keyboard.press("Enter"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
    states.push({ state: "detail", ...(await layout(page)) }); await page.screenshot({ path: resolve(folder, "zoom-detail.png"), fullPage: true });
    save("zoom-results", { channel, nativeZoom: zoom, before, after, profile, observations, states });
    for (const state of states as Awaited<ReturnType<typeof layout>>[]) { expect(state.clipped).toEqual([]); expect(state.outside).toEqual([]); }
  } finally { await context.close(); }
});

test("native 200 percent zoom valid maximum-name boundary", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "wardrobe-j19-boundary-zoom-"));
  const context = await chromium.launchPersistentContext(profile, { channel, headless: true, viewport: null, args: ["--window-size=1440,1000"] });
  try {
    const page = context.pages()[0], owner = await setup(request, page, "zoom-boundary");
    expect((await request.patch(api + "/wardrobe/garments/" + owner.garmentId, { headers: owner.headers, data: { name: "J19" + "x".repeat(97) } })).status()).toBe(200);
    const settings = await context.newPage(); await settings.goto(channel === "chrome" ? "chrome://settings" : "edge://settings");
    const zoom = await settings.evaluate(() => new Promise<number>(resolve => {
      const browser = globalThis as unknown as { chrome: { settingsPrivate: { setDefaultZoom: (value: number, callback: () => void) => void; getDefaultZoom: (callback: (value: number) => void) => void } } };
      browser.chrome.settingsPrivate.setDefaultZoom(2, () => browser.chrome.settingsPrivate.getDefaultZoom(resolve));
    })); await settings.close();
    const result = await submit(page), inspection = await layout(page);
    const metrics = await page.evaluate(() => ({ innerWidth, outerWidth, dpr: devicePixelRatio, scale: visualViewport!.scale, cssZoom: getComputedStyle(document.body).zoom }));
    await page.screenshot({ path: resolve(folder, "zoom-maximum-name.png"), fullPage: true });
    save("zoom-boundary-results", { channel, nativeZoom: zoom, metrics, inspection, recommendationId: result.id, nameLength: 100 });
    expect(zoom).toBe(2); expect(metrics.dpr).toBe(2); expect(inspection.clipped).toEqual([]);
  } finally { await context.close(); }
});
