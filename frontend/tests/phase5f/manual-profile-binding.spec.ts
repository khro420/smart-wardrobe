import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const review = process.env.SW_REVIEW_DIR!;
const a = "99cc52e8-473e-4192-b6d9-a6fa3227d45c";
const b = "94f3e9af-86ce-48a1-b21d-c0612526dde3";
const token = process.env.SW_SETUP_TOKEN!;
type Item = { garment_id: string; preferred_media_id: string; name: string; garment_role: string; category: string };
type Result = { id: string; chat_id: string; outcome: string; profile_id: string; request_text: string; items: Item[] };
const media = JSON.parse(fs.readFileSync(path.join(review, "MEDIA_LIVE_RESULT.json"), "utf8")) as { results: { key: string; new_media_id: string; garment: { id: string } }[] };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(({ token, a }) => {
    sessionStorage.setItem("smart_wardrobe_access_token", token);
    if (!sessionStorage.getItem("smart_wardrobe_profile_id")) sessionStorage.setItem("smart_wardrobe_profile_id", a);
  }, { token, a });
});

async function send(page: Page, text: string): Promise<Result> {
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(text);
  const pending = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const response = await pending; expect(response.status()).toBe(201);
  const value = await response.json() as Result; expect(value.outcome).toBe("Selected");
  await expect(page.getByText(text, { exact: true }).first()).toBeVisible();
  return value;
}

test("current images, scoped free text, preferences, alternatives and immutable history", async ({ page }) => {
  await page.goto("/assistant");
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(a);
  await page.waitForLoadState("networkidle");
  const cases = ["i want a blue cotton top with long sleeves", "something blue and cotton with long sleeves", "give me a black top with blue trousers", "i want a cotton top without short sleeves"];
  const responses: Result[] = [];
  for (const text of cases) {
    const value = await send(page, text); responses.push(value);
    if (text === cases[0] || text === cases[1]) {
      const selected = value.items.find(i => i.name.includes("MD03 ")); expect(selected).toBeDefined();
      const corrected = media.results.find(g => g.key === "MD03")!;
      expect(selected!.preferred_media_id).toBe(corrected.new_media_id);
      await expect(page.locator("img").first()).toBeAttached();
    }
    if (text === cases[2]) {
      expect(value.items.find(i => i.garment_role === "lower")!.category).toBe("trousers");
      expect(value.items.find(i => i.garment_role === "upper")!.name).toContain("MD02 ");
    }
    if (text === cases[0]) await page.screenshot({ path: path.join(review, "corrected-long-sleeve.png"), fullPage: true });
  }
  const original = responses[0]; await page.goto("/history/" + original.chat_id); await page.reload();
  await expect(page.getByRole("heading", { name: /Saved recommendation/ })).toBeVisible();
  const personalized: Result[] = [];
  for (const wearer of [a, b]) {
    await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(wearer);
    await page.goto("/assistant"); const value = await send(page, "Recommend an outfit.");
    expect(value.profile_id).toBe(wearer); personalized.push(value);
  }
  expect(personalized[0].items.map(i => i.garment_id)).not.toEqual(personalized[1].items.map(i => i.garment_id));
  await page.goto("/assistant"); await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill("i dont want floral patterns for shopping");
  await page.getByLabel("Use recorded palette colours for compatibility", { exact: true }).check();
  const initialPending = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click(); const root = await (await initialPending).json() as Result;
  const childPending = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest another outfit", exact: true }).click(); const child = await (await childPending).json() as Result;
  expect(child.outcome).toBe("Selected"); expect(child.request_text).toBe(root.request_text); expect(child.profile_id).toBe(b);
  expect(child.items.map(i => i.garment_id)).not.toEqual(root.items.map(i => i.garment_id));
  fs.writeFileSync(path.join(review, "FINAL_BROWSER_RESPONSES.json"), JSON.stringify({ responses, personalized, root, child }, null, 2));
});

test("optional wearer metadata saves independently and retains a conflicting draft", async ({ page }) => {
  await page.goto("/profile");
  const select = page.getByRole("combobox", { name: "Select active wardrobe profile" }).first();
  await select.selectOption(a); await page.goto("/profile");
  const form = page.getByRole("form", { name: "Wearer information", exact: true });
  await expect(form.getByLabel("Gender (optional)")).toHaveValue("male");
  await form.getByLabel("Gender (optional)").selectOption("custom"); await form.getByLabel("Gender description", { exact: true }).fill("Retained test draft");
  const headers = { Authorization: "Bearer " + token, "X-Wardrobe-Profile-Id": a };
  const url = `/api/v1/account/wardrobe-profiles/${a}/details`;
  const current = await (await page.request.get(url, { headers })).json() as { version: string; revision: string };
  expect((await page.request.put(url, { headers, data: { version: current.version, expected_revision: current.revision, gender_identity: "female" } })).status()).toBe(200);
  const conflict = page.waitForResponse(r => r.url().endsWith(`/wardrobe-profiles/${a}/details`) && r.request().method() === "PUT");
  await form.getByRole("button", { name: "Save wearer information", exact: true }).click(); expect((await conflict).status()).toBe(409);
  await expect(form.getByLabel("Gender description", { exact: true })).toHaveValue("Retained test draft");
  await form.getByRole("button", { name: "Reload wearer revision", exact: true }).click(); await expect(form.getByRole("status")).toContainText("Your draft is retained");
  await form.getByLabel("Gender (optional)").selectOption("male");
  await form.getByRole("button", { name: "Save wearer information", exact: true }).click(); await expect(form.getByRole("status")).toHaveText("Wearer information saved.");
  await page.screenshot({ path: path.join(review, "male-wearer-information.png"), fullPage: true });
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(b); await page.goto("/profile");
  await expect(page.getByRole("form", { name: "Wearer information", exact: true }).getByLabel("Gender (optional)")).toHaveValue("female");
  await expect(page.getByRole("form", { name: /Soft preferences for/ })).toBeVisible();
  await page.screenshot({ path: path.join(review, "female-wearer-information.png"), fullPage: true });
});
