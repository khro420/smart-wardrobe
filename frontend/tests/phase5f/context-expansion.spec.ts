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
async function tags(request: APIRequestContext, headers: Record<string, string>, garment: { id: string; tag_edit: { revision: string } }, values: string[]) {
  expect((await request.patch(api + "/wardrobe/garments/" + garment.id, { headers: { ...headers, "If-Match": garment.tag_edit.revision }, data: { attributes: { custom_tags: values } } })).status()).toBe(200);
}
async function bounds(page: Page) {
  return page.evaluate(() => {
    const root = document.querySelector("#main-content")!, width = document.documentElement.clientWidth, clipped: string[] = [];
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) { const n = walk.currentNode; if (!n.textContent?.trim() || !n.parentElement?.getClientRects().length || ["SCRIPT", "STYLE"].includes(n.parentElement.tagName)) continue; const r = document.createRange(); r.selectNodeContents(n); if ([...r.getClientRects()].some(b => b.width > 0 && (b.left < -1 || b.right > width + 1))) clipped.push(n.textContent.trim()); }
    return { width, scroll: document.documentElement.scrollWidth, clipped };
  });
}


const expandedTexts = ["I'm going to study at the library.", "I have a group project meeting at university.", "I need to go to the office tomorrow.", "I have a meeting with my colleagues.", "I'm attending a birthday party.", "I'm visiting my friend's house.", "I'm going to watch a movie.", "I'm meeting someone at a café.", "I'm sightseeing around the city.", "I'm taking a train for a trip."];

test("BX01 normal Add and every new context, exact components and unchanged garments", async ({ page, request, browser }) => {
  const headers = await register(page); let reviews = 0;
  page.on("request", r => { if (r.method() === "POST" && (/\/(review|confirm)$/.test(r.url()) || r.url().includes("/contextual-suitability"))) reviews++; });
  for (let code = 20; code < 28; code++) await add(page, code);
  const before = await (await request.get(api + "/wardrobe/garments", { headers })).json();
  const capabilities = await (await request.get(api + "/recommendations/capabilities", { headers })).json();
  expect(capabilities.context_support.situations.filter((s: { policy_available: boolean }) => s.policy_available)).toHaveLength(18);
  expect(capabilities.context_ranking.objectives).toHaveLength(15);
  const results = [];
  for (let i = 0; i < expandedTexts.length; i++) {
    const value = await ask(page, expandedTexts[i]); expect(value.outcome).toBe("Selected");
    expect(value.items.map((g: { name: string }) => g.name)).toEqual([2,3].includes(i) ? ["Navy Dress", "Grey Jacket"] : ["Blue T-shirt", "Blue Jeans"]);
    expect(value.scoring_display.total).toEqual({ numerator: "4", denominator: "5" });
    await expect(page.getByLabel("Full R C P breakdown", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Context relevance ranking")).toContainText("prototype");
    await expect(page.getByRole("heading", { name: "Your outfit recommendation", exact: true })).toBeVisible();
    results.push(value);
  }
  expect(reviews).toBe(0);
  expect(await (await request.get(api + "/wardrobe/garments", { headers })).json()).toEqual(before);
  record("BX01", { browser: browser.version(), reviews, results, capabilities });
});

test("BX02 compound meanings, family dinner and cafe date retained", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers);
  const results = [];
  for (const [text, sid, facet] of [["I have a dinner date.", "social.date", "meal:dinner"], ["I'm attending a birthday dinner.", "social.meal", "celebration:birthday"], ["I'm going on a date at a café.", "social.date", ""], ["I'm having dinner with my family.", "social.meal", ""]]) {
    const value = await ask(page, text); expect(value.outcome).toBe("Selected");
    expect(value.provenance.general_context.situation).toBe(sid);
    expect(value.scoring_display.objective.target).toBe("smart casual");
    if (facet) { expect(value.provenance.general_context.facets).toContain(facet); await expect(page.getByLabel("Context suggestion basis")).toContainText("Also understood"); }
    results.push(value);
  }
  const ambiguous = await ask(page, "I have a meeting."); expect(ambiguous.context_reason).toBe("context_clarification_required");
  await expect(page.getByRole("heading", { name: "No outfit generated", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Recommendation outcome", exact: true }).getByRole("alert")).toContainText("missing purpose was not guessed"); record("BX02", { results, ambiguous });
});

test("BX03 broad work Deny, no hidden minimum R and unsupported formal stay distinct", async ({ page, request }) => {
  const headers = await register(page); const garments = await seed(page, request, headers, [10]);
  const zero = await ask(page, expandedTexts[2]); expect(zero.outcome).toBe("Selected");
  expect(zero.scoring_display.components[0].contribution).toEqual({ numerator: "0", denominator: "1" });
  await tags(request, headers, garments[0], ["rec:v1:occasion:work:deny"]);
  const denied = await ask(page, expandedTexts[3]); expect(denied.outcome).toBe("NoMatchingCandidates");
  const library = await ask(page, expandedTexts[0]); expect(library.outcome).toBe("Selected");
  const formal = await ask(page, "I have a formal office meeting."); expect(formal.outcome).toBe("PolicyUnavailable");
  await expect(page.getByRole("heading", { name: "No outfit generated", exact: true })).toBeVisible(); record("BX03", { zero, denied, library, formal });
});

test("BX04 explicit style override, exact duplicate and independent preference", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers);
  const explicit = await ask(page, "Suggest an outfit for an office workday with casual style");
  expect(explicit.scoring_display.objective.authority).toBe("explicit_user_style"); expect(explicit.items[0].name).toBe("Blue T-shirt");
  expect((await request.put(api + "/account/preferences/styles", { headers, data: { preference_value: { values: ["casual"] }, weight: 1 } })).status()).toBe(200);
  const duplicate = await ask(page, expandedTexts[0]); expect(duplicate.scoring_display.total).toEqual({ numerator: "4", denominator: "5" });
  await expect(page.getByLabel("Context relevance ranking")).toContainText("original positive-weight denominator");
  expect((await request.put(api + "/account/preferences/styles", { headers, data: { preference_value: { values: [] }, weight: 1 } })).status()).toBe(200);
  expect((await request.put(api + "/account/preferences/colours", { headers, data: { preference_value: { values: ["green"] }, weight: 1 } })).status()).toBe(200);
  const green = await ask(page, expandedTexts[0]); expect(green.items[0].name).toBe("Green Sweatshirt"); expect(green.scoring_display.total).toEqual({ numerator: "9", denominator: "10" }); record("BX04", { explicit, duplicate, green });
});

test("BX05 missing style, broad Allow and disclosed legacy fallback", async ({ page, request }) => {
  const headers = await register(page); let garments = await seed(page, request, headers, [12]);
  expect((await ask(page, expandedTexts[0])).outcome).toBe("InsufficientEvidence");
  await expect(page.getByRole("region", { name: "Recommendation outcome", exact: true }).getByRole("alert")).toContainText("without a separate review");
  await tags(request, headers, garments[0], ["rec:v1:occasion:campus:allow"]);
  const broad = await ask(page, expandedTexts[0]); expect(broad.outcome).toBe("InsufficientEvidence");
  garments = await (await request.get(api + "/wardrobe/garments", { headers })).json();
  await tags(request, headers, garments[0], ["rec:v1:occasion:shopping:allow"]);
  const fallback = await ask(page, texts[0]); expect(fallback.scoring_display.selection_mode).toBe("baseline_disclosed_v1");
  await expect(page.getByLabel("Context relevance ranking")).toContainText("Baseline fallback"); record("BX05", { broad, fallback });
});

test("BX06 technical retry retains key and outcome focus", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers, [10]); let first = true; const keys: string[] = [];
  await page.route("**/api/v1/recommendations?pipeline=integrated", async route => { const payload = route.request().postDataJSON(); if (payload.request_text !== expandedTexts[0]) { await route.continue(); return; } keys.push(payload.submission_key); if (first) { first = false; await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ outcome: "ProcessingFailure", complete: false }) }); } else await route.continue(); });
  expect((await ask(page, expandedTexts[0], true)).outcome).toBe("ProcessingFailure");
  await expect(page.getByRole("heading", { name: "Request could not be completed", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Retry same request", exact: true }).click();
  await expect(page.getByTestId("recommendation-result")).toBeVisible(); expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]); record("BX06", { keysEqual: true });
});

test("BX07 legacy and expanded history, saving and durable logout", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers, [10]);
  const legacy = await ask(page, "Suggest an outfit"); expect(legacy.outcome).toBe("Selected"); expect(legacy.scoring_display.version).toBe("assistant-scoring-display-1.0.0");
  const expanded = await ask(page, expandedTexts[0]); expect(expanded.scoring_display.version).toBe("assistant-scoring-display-2.1.0");
  await page.getByRole("button", { name: "Save as outfit", exact: true }).click(); await expect(page.getByRole("button", { name: "Saved as outfit", exact: true })).toBeDisabled();
  await page.goto("/history/" + legacy.chat_id); await expect(page.getByTestId("compatibility-explanation")).toBeVisible();
  await page.goto("/history/" + expanded.chat_id); await expect(page.getByLabel("Full R C P breakdown")).toBeVisible();
  expect((await (await request.get(api + "/chats/" + expanded.chat_id, { headers })).json()).recommendation.score_metadata).toEqual(expanded.score_metadata);
  await page.getByRole("button", { name: "Sign out", exact: true }).click(); await page.waitForURL("/auth"); expect((await request.get(api + "/wardrobe/garments", { headers })).status()).toBe(401); record("BX07", { legacy, expanded });
});

test("BX08 full names, keyboard submission and bounded narrow/full component layouts", async ({ page, request }) => {
  const headers = await register(page); await seed(page, request, headers, [10]);
  await ask(page, texts[0], true); await expect(page.getByRole("region", { name: "Recommendation outcome", exact: true })).toBeFocused();
  const layouts = [];
  for (const width of [360,390,768,1280,1920]) { await page.setViewportSize({ width, height: 960 }); const layout = await bounds(page); expect(layout.clipped).toEqual([]); expect(layout.scroll).toBeLessThanOrEqual(layout.width); layouts.push(layout); }
  await page.setViewportSize({ width: 390, height: 960 }); await page.screenshot({ path: join(folder, "BX08-full-components-390.png"), fullPage: true }); record("BX08", layouts);
});

test("BX09 actual native 200 percent Chrome zoom retains visible outcome and full components", async ({ request }) => {
  const profile = mkdtempSync(join(tmpdir(), "context-relevance-zoom-"));
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
    const cdp = await context.newCDPSession(page), shot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false }); writeFileSync(join(folder, "BX09-native-zoom.png"), Buffer.from(shot.data, "base64")); await cdp.detach(); record("BX09", { zoom, metrics, layout });
  } finally { await context.close(); }
});
