import { test, expect, type Page } from "@playwright/test";

const token = process.env.SW_SETUP_TOKEN ?? "";
const root = process.env.SW_GARMENT_URL ?? "";
if (!root) throw new Error("Set SW_GARMENT_URL to an owned disposable fixture server.");
const evidence = process.env.SW_GARMENT_EVIDENCE_DIR;
type Item = { garment_role: string; garment_id: string; category: string };
const base = (items: Item[]) => items.filter(item => item.garment_role !== "outerwear").map(item => `${item.garment_role}:${item.garment_id}`).join("|");
async function setup(page: Page, wearer: string) {
  expect(token, "Owned setup token must be supplied explicitly").not.toBe("");
  expect(wearer).not.toBe("");
  await page.addInitScript(({ value, profile }) => {
    sessionStorage.setItem("smart_wardrobe_access_token", value);
    sessionStorage.setItem("smart_wardrobe_profile_id", profile);
  }, { value: token, profile: wearer });
  await page.goto(`${root}/assistant`);
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(wearer);
  await page.goto(`${root}/assistant`);
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
}
async function initial(page: Page, text: string, c2 = false) {
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(text);
  if (c2) await page.getByRole("checkbox", { name: "Use recorded palette colours for compatibility" }).check();
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const reply = await response;
  expect(reply.status()).toBe(201);
  return reply.json();
}
for (const gender of ["male", "female"] as const) {
  test(`${gender}: bound garment-only alternative, retry and visible history`, async ({ page }) => {
    const wearer = process.env[gender === "male" ? "SW_GARMENT_MALE" : "SW_GARMENT_FEMALE"] ?? "";
    await setup(page, wearer);
    const first = await initial(page, "i want a shirt with black trousers", gender === "female");
    expect(first.profile_id).toBe(wearer);
    expect(first.garment_continuation.ordinal).toBe(0);
    await expect(page.getByRole("region", { name: "Recommendation outcome" })).toContainText("Request match is Not applicable");
    const pending = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Suggest another outfit", exact: true }).click();
    const response = await pending;expect(response.status()).toBe(201);
    const second = await response.json();
    expect(second.profile_id).toBe(wearer);
    expect(second.request_text).toBe(first.request_text);
    expect(second.provenance.attribute_selection.intent).toEqual(first.provenance.attribute_selection.intent);
    expect(base(second.items)).not.toBe(base(first.items));
    if (gender === "male") expect(second.items.every((item: Item) => item.category !== "skirt" && !item.category.endsWith("_dress"))).toBe(true);
    const requestBody = response.request().postDataJSON();
    const replay = await page.request.post(`${root}/api/v1/recommendations?pipeline=integrated`, { headers: { Authorization: `Bearer ${token}`, "X-Wardrobe-Profile-Id": wearer }, data: requestBody });
    expect(replay.status()).toBe(200);expect((await replay.json()).id).toBe(second.id);
    await page.goto(`${root}/history/${second.chat_id}`);
    await expect(page.getByText(first.request_text, { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Garment recommendation sequence" })).toContainText("Garment alternative 1");
    if (evidence) await page.screenshot({ path: `${evidence}/${gender}-garment-history.png`, fullPage: true });
    await test.info().attach("actual-root-child", { body: JSON.stringify({ first, second, requestBody }, null, 2), contentType: "application/json" });
  });
}
test("singleton base exhausts without an outerwear-only replacement", async ({ page }) => {
  await setup(page, process.env.SW_GARMENT_MALE ?? "");
  await initial(page, "Give me a black top with blue trousers.");
  const pending = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest another outfit", exact: true }).click();
  const reply = await pending;expect(reply.status()).toBe(200);
  expect((await reply.json()).outcome).toBe("GarmentRefinementExhausted");
  await expect(page.getByRole("region", { name: "Recommendation outcome" }).getByRole("alert")).toContainText("No more distinct outfit bases");
  await expect(page.getByRole("button", { name: "Suggest another outfit", exact: true })).toBeDisabled();
});
test("coarse T-shirt limitation is visible and blouse precision requests get guidance", async ({ page }) => {
  await setup(page, process.env.SW_GARMENT_FEMALE ?? "");
  await initial(page, "i want a T-shirt with black jeans");
  await expect(page.getByRole("note")).toContainText("Exact T-shirt versus blouse subtype is not verified");
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill("i want a blouse with black trousers");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  await expect(page.getByRole("region", { name: "Recommendation outcome" }).getByRole("alert")).toContainText("That distinction cannot be verified");
});
