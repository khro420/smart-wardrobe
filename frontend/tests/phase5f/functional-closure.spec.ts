import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const folder = process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!;
const password = "J18-disposable-password-123";
const evidence = (name: string, value: unknown) => writeFileSync(resolve(folder, name + ".json"), JSON.stringify(value, null, 2));
async function account(request: APIRequestContext, page: Page, name: string) {
  const email = `j18-${name}@example.test`;
  const registered = await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: name } });
  expect(registered.status()).toBe(201);
  expect((await registered.json()).access_token).toBeUndefined();
  const logged = await request.post(api + "/account/login", { data: { email, password } });
  expect(logged.status()).toBe(200); const token = (await logged.json()).access_token as string;
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token", value), token);
  return { Authorization: `Bearer ${token}` };
}
async function synthetic(page: Page) {
  return Buffer.from(await page.evaluate(() => { const canvas = document.createElement("canvas"); canvas.width = 256; canvas.height = 256; canvas.getContext("2d")!.fillRect(0, 0, 256, 256); return canvas.toDataURL("image/png").split(",")[1]; }), "base64");
}
async function garment(request: APIRequestContext, headers: Record<string, string>, image: Buffer, name: string, colour: string, style: string) {
  const upload = await request.post(api + "/processing/jobs", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer: image } } });
  expect(upload.status()).toBe(202);
  const base = api + "/processing/jobs/" + (await upload.json()).id;
  await expect.poll(async () => (await (await request.get(base, { headers })).json()).status).toBe("review_required");
  const item = (await (await request.get(base, { headers })).json()).items[0].id;
  expect((await request.post(base + "/review", { headers, data: { items: [{ item_id: item, decision: "accepted", name, category: "vest_dress", primary_colour: colour, attributes: { style: [style] } }] } })).status()).toBe(200);
  const confirmed = await request.post(base + "/confirm", { headers, data: { save_mode: "garments", item_ids: [item] } });
  expect(confirmed.status()).toBe(201); return (await confirmed.json()).garment_ids[0] as string;
}
async function save(page: Page, formName: string, button: string) {
  const form = page.getByRole("form", { name: formName });
  const pending = page.waitForResponse(response => response.url().includes("/account/") && ["PUT", "PATCH"].includes(response.request().method()));
  await form.getByRole("button", { name: button, exact: true }).click();
  expect((await pending).status()).toBe(200);
  await expect(form.getByRole("status")).toBeVisible();
}

test("registration to login and controlled profile save cancel failure", async ({ page, request }) => {
  await page.goto("/auth"); await page.getByRole("button", { name: "Register", exact: true }).click();
  const form = page.locator("form");
  await form.getByLabel("Full name", { exact: true }).fill("J18 Browser Owner");
  await form.getByLabel("Email", { exact: true }).fill("j18-browser@example.test");
  await form.getByLabel(/^Password/).fill(password);
  await form.getByLabel("Confirm password", { exact: true }).fill("mismatched-password");
  let registrationPosts = 0;
  page.on("request", response => { if (response.url().endsWith("/account/register") && response.method() === "POST") registrationPosts++; });
  await form.getByRole("button", { name: "Create private account", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toHaveText("Passwords must match."); expect(registrationPosts).toBe(0);
  await form.getByLabel("Confirm password", { exact: true }).fill(password);
  await form.getByRole("button", { name: "Create private account", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Account created. Sign in to continue.");
  expect(registrationPosts).toBe(1); expect(new URL(page.url()).pathname).toBe("/auth");
  expect(await page.evaluate(() => sessionStorage.getItem("smart_wardrobe_access_token"))).toBeNull();
  await expect(form.getByLabel(/^Password/)).toHaveValue("");
  await form.getByLabel(/^Password/).fill("wrong-password");
  await form.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toHaveText("Invalid email or password.");
  await form.getByLabel(/^Password/).fill(password);
  await form.getByRole("button", { name: "Sign in", exact: true }).click(); await page.waitForURL("/");
  const token = await page.evaluate(() => sessionStorage.getItem("smart_wardrobe_access_token"));
  const headers = { Authorization: `Bearer ${token}` };
  await page.goto("/profile");
  const profile = page.getByRole("form", { name: "Profile information" });
  await profile.getByLabel("Display name", { exact: true }).fill("Cancelled name");
  await profile.getByRole("button", { name: "Cancel profile", exact: true }).click();
  await expect(profile.getByLabel("Display name", { exact: true })).toHaveValue("J18 Browser Owner");
  await profile.getByLabel("Display name", { exact: true }).fill("Saved name");
  const savedProfile = page.waitForResponse(r => r.request().method() === "PATCH" && r.url().endsWith("/account/profile"));
  await profile.getByRole("button", { name: "Save profile", exact: true }).click(); expect((await savedProfile).status()).toBe(200);
  await expect(page.getByRole("status")).toHaveText("Profile updated.");
  await profile.getByLabel("Display name", { exact: true }).fill("Failed name");
  await page.route("**/api/v1/account/profile", route => route.request().method() === "PATCH" ? route.abort("failed") : route.continue());
  await profile.getByRole("button", { name: "Save profile", exact: true }).click(); await expect(page.locator("p[role=alert]")).toContainText("Could not connect");
  await expect(profile.getByLabel("Display name", { exact: true })).toHaveValue("Failed name");
  expect((await (await request.get(api + "/account/profile", { headers })).json()).display_name).toBe("Saved name");
  await page.unroute("**/api/v1/account/profile"); await profile.getByRole("button", { name: "Cancel profile", exact: true }).click();
  const choices = [
    { form: "Colours", label: "blue", button: "colours" }, { form: "Styles", label: "classic", button: "styles" },
    { form: "Garment categories", label: "group: dress", button: "garment categories" }, { form: "Formality", label: "casual", button: "formality" },
  ];
  for (const choice of choices) {
    const editor = page.getByRole("form", { name: choice.form + " preferences", exact: true });
    await editor.getByLabel(choice.label, { exact: true }).check();
    await editor.getByLabel(choice.form + " importance", { exact: true }).fill("0.5");
    await save(page, choice.form + " preferences", "Save " + choice.button);
  }
  const stored = await (await request.get(api + "/account/preferences", { headers })).json();
  expect(stored).toHaveLength(4); expect(stored.every((row: { weight: number }) => row.weight === .5)).toBe(true);
  const colours = page.getByRole("form", { name: "Colours preferences", exact: true });
  await colours.getByLabel("blue", { exact: true }).uncheck(); await colours.getByLabel("red", { exact: true }).check();
  await page.route("**/api/v1/account/preferences/colours", route => route.abort("failed"));
  await colours.getByRole("button", { name: "Save colours", exact: true }).click(); await expect(colours.getByRole("alert")).toContainText("Could not connect");
  await expect(colours.getByLabel("red", { exact: true })).toBeChecked();
  expect(await (await request.get(api + "/account/preferences", { headers })).json()).toEqual(stored);
  await page.unroute("**/api/v1/account/preferences/colours");
  await colours.getByRole("button", { name: "Cancel colours", exact: true }).click();
  await expect(colours.getByLabel("blue", { exact: true })).toBeChecked(); await expect(colours.getByLabel("red", { exact: true })).not.toBeChecked();
  await page.reload(); await expect(page.getByRole("form", { name: "Styles preferences" }).getByLabel("classic", { exact: true })).toBeChecked();
  const reloadedColours = page.getByRole("form", { name: "Colours preferences" });
  await reloadedColours.getByRole("button", { name: "Clear colours selection", exact: true }).click();
  await save(page, "Colours preferences", "Save colours");
  expect((await (await request.get(api + "/account/preferences", { headers })).json()).map((row: { preference_type: string }) => row.preference_type)).not.toContain("colours");
  evidence("account-profile-browser", { registration_posts: registrationPosts, registration_auto_session: false, profile: "Saved name", preferences: stored, cancelled_and_failed_updates_preserved: true });
});

test("listing filters preserve quota and independent current eligibility", async ({ page, request }) => {
  const headers = await account(request, page, "filters"); await page.goto("/wardrobe"); const image = await synthetic(page);
  const blue = await garment(request, headers, image, "Blue classic", "blue", "classic");
  const red = await garment(request, headers, image, "Red vintage", "red", "vintage");
  const archived = await garment(request, headers, image, "Archived blue", "blue", "classic");
  expect((await request.delete(api + "/wardrobe/garments/" + archived, { headers })).status()).toBe(204);
  await page.reload(); const cards = page.locator("[data-garment-id]"); await expect(cards).toHaveCount(2);
  const quota = await (await request.get(api + "/wardrobe/quota", { headers })).json(); expect(quota.used).toBe(2);
  await page.getByLabel("Primary colour", { exact: true }).fill("blue"); await expect(cards).toHaveCount(1); await expect(cards.first()).toHaveAttribute("data-garment-id", blue);
  await page.getByLabel("Style filter", { exact: true }).fill("vintage"); await expect(cards).toHaveCount(0);
  await page.getByLabel("Style filter", { exact: true }).fill("classic"); await expect(cards).toHaveCount(1);
  await page.getByLabel("Filter garments by availability").selectOption("archived"); await expect(cards).toHaveCount(1); await expect(cards.first()).toHaveAttribute("data-garment-id", archived);
  await expect(cards.getByRole("button", { name: "Edit", exact: true })).toBeDisabled(); await expect(cards.getByRole("checkbox")).toBeDisabled();
  await page.getByLabel("Filter garments by availability").selectOption("all"); await expect(cards).toHaveCount(2);
  expect(await (await request.get(api + "/wardrobe/quota", { headers })).json()).toEqual(quota);
  const generated = await request.post(api + "/recommendations?pipeline=integrated", { headers, data: { request_text: "Suggest a classic outfit", submission_key: "listing-independent" } });
  expect(generated.status()).toBe(201); expect((await generated.json()).items.map((item: { garment_id: string }) => item.garment_id)).toEqual([blue]);
  evidence("listing-browser", { blue, red, archived, quota, archived_read_only: true, recommendation_eligible_id: blue });
});

test("normal Assistant consumes saved preferences and classic phrase preserves replay", async ({ page, request }) => {
  const headers = await account(request, page, "recommendation"); await page.goto("/wardrobe");
  const id = await garment(request, headers, await synthetic(page), "Classic dress", "blue", "classic");
  await page.goto("/profile");
  const colours = page.getByRole("form", { name: "Colours preferences" });
  await colours.getByLabel("blue", { exact: true }).check(); await save(page, "Colours preferences", "Save colours");
  await page.goto("/assistant"); await page.getByLabel("What would you like to wear?").fill("Suggest a classic outfit");
  const pending = page.waitForResponse(response => response.url().includes("pipeline=integrated") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const response = await pending; expect(response.status()).toBe(201); const result = await response.json();
  expect(result.preference_score).toBe(1); expect(result.items[0].garment_id).toBe(id);
  expect(result.provenance.scoring_profile).toBe("experimental_compatibility_decision_v1");
  expect(result.provenance.request_evaluator).toBe("SuitabilityRequestEvaluator");
  expect(result.score_metadata.weights.map((value: { numerator: number; denominator: number }) => value.numerator / value.denominator)).toEqual([.6, .2, .2]);
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  const body = response.request().postDataJSON();
  await request.put(api + "/account/preferences/colours", { headers, data: { preference_value: { values: ["red"] }, weight: 1 } });
  const replay = await request.post(api + "/recommendations?pipeline=integrated", { headers, data: body }); expect(replay.status()).toBe(200);
  expect((await replay.json()).score_metadata).toEqual(result.score_metadata);
  await page.goto("/history/" + result.chat_id); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  evidence("recommendation-browser", { result, replay: await replay.json(), history_preserved: true });
});
