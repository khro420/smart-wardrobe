import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const password = "Contextual-disposable-password-123";
const record = (name: string, value: unknown) => writeFileSync(resolve(process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!, name + ".json"), JSON.stringify(value, null, 2));
async function setup(page: Page, request: APIRequestContext, label: string) {
  const email = `wedding-${label}@example.test`;
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "Wedding Owner" } })).status()).toBe(201);
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
  const name = "Wedding" + "x".repeat(93);
  expect((await request.post(base + "/review", { headers, data: { items: [{ item_id: item, decision: "accepted", name, category: "vest_dress", primary_colour: "blue", attributes: { style: ["smart casual"] } }] } })).status()).toBe(200);
  const confirmed = await request.post(base + "/confirm", { headers, data: { save_mode: "garments", item_ids: [item] } });
  expect(confirmed.status()).toBe(201);
  return { headers, name, gid: (await confirmed.json()).garment_ids[0] as string };
}
async function ask(page: Page, text: string) {
  await page.goto("/assistant");
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?").fill(text);
  const response = page.waitForResponse(response => response.url().includes("/recommendations?pipeline=integrated") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).focus();
  await page.keyboard.press("Enter");
  return (await response).json();
}

test("review once then natural wedding selection immutable history and saved outfit", async ({ page, request, browser }) => {
  const { headers, gid, name } = await setup(page, request, "selection");
  const missing = await ask(page, "I'm going to a wedding");
  expect(missing.outcome).toBe("InsufficientEvidence");
  await expect(page.getByRole("alert").filter({ hasText: "No outfit passed the wedding rules." })).toContainText("Review the garment style evidence");
  await page.goto("/wardrobe");
  const card = page.locator(`[data-garment-id="${gid}"]`);
  await card.locator("summary").click();
  await card.getByRole("button", { name: "I reviewed the current style", exact: true }).click();
  await expect(card).toContainText("Reviewed for contextual inference.");
  const selected = await ask(page, "I'm going to a wedding");
  expect(selected.outcome).toBe("Selected");
  const result = page.getByTestId("recommendation-result");
  await expect(result.getByRole("region", { name: "Wedding suggestion basis" })).toContainText("dress code unspecified. Check the invitation.");
  await expect(result).toContainText("Guest role assumed");
  await expect(result).toContainText("inferred from reviewed style attributes");
  await expect(result.getByText(name, { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 360, height: 960 });
  const fits = await result.evaluate(element => { const box = element.getBoundingClientRect(); return box.left >= 0 && box.right <= innerWidth && element.scrollWidth <= element.clientWidth + 1; });
  expect(fits).toBe(true);
  await page.screenshot({ path: resolve(process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!, "wedding-result-360.png"), fullPage: true });
  await result.getByRole("button", { name: "Save as outfit", exact: true }).click();
  await expect(result.getByRole("button", { name: "Saved as outfit", exact: true })).toBeVisible();
  const id = selected.recommendation.id;
  const prepared = await request.post(api + "/visualisations/prepare", { headers, data: { recommendation_id: id } });
  expect(prepared.status()).toBe(200);
  expect((await prepared.json()).items.map((item: { garment_id: string }) => item.garment_id)).toEqual([gid]);
  const saved = await request.get(api + `/recommendations/${id}/saved-outfit`, { headers });
  expect((await saved.json()).saved).toBe(true);
  await page.goto("/history/" + selected.recommendation.chat_id);
  await expect(page.getByRole("region", { name: "Wedding suggestion basis" })).toContainText("inferred from reviewed style attributes");
  const historical = await (await request.get(api + "/chats/" + selected.recommendation.chat_id, { headers })).json();
  expect(historical.recommendation.provenance).toEqual(selected.recommendation.provenance);
  record("contextual-selection", { browser: browser.version(), selected, historical, narrow_layout_fits: fits });
});

test("explicit Deny blocks inference and formal wedding is unavailable", async ({ page, request }) => {
  const { gid } = await setup(page, request, "denial");
  await page.goto("/wardrobe");
  const card = page.locator(`[data-garment-id="${gid}"]`);
  await card.locator("summary").click();
  await card.getByRole("button", { name: "I reviewed the current style", exact: true }).click();
  await expect(card).toContainText("Reviewed for contextual inference.");
  await card.locator("summary").click();
  await card.getByLabel("Wedding suitability override (optional)").selectOption("deny");
  await card.getByRole("button", { name: "Save wedding override", exact: true }).click();
  await expect(card.getByLabel("Wedding suitability override (optional)")).toHaveValue("deny");
  const denied = await ask(page, "I'm going to a wedding");
  expect(denied.outcome).toBe("NoMatchingCandidates");
  await expect(page.getByRole("alert").filter({ hasText: "No outfit passed the wedding rules." })).toContainText("explicit suitability choices");
  const formal = await ask(page, "I'm going to a formal wedding");
  expect(formal.outcome).toBe("PolicyUnavailable");
  await expect(page.getByRole("alert").filter({ hasText: "This wedding role or dress code" })).toContainText("role or dress code is not supported");
  record("contextual-denial-unavailable", { denied, formal });
});
