import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const record = (name: string, value: unknown) => writeFileSync(join(process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!, `${name}.json`), JSON.stringify(value, null, 2));
async function seed(page: Page, request: APIRequestContext) {
  const email = `palette-${crypto.randomUUID()}@example.test`, password = "Disposable-palette-password-123";
  expect((await request.post(`${api}/account/register`, { data: { email, password, password_confirmation: password, display_name: "Palette mechanics" } })).status()).toBe(201);
  const auth = await (await request.post(`${api}/account/login`, { data: { email, password } })).json();
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  await page.goto("/auth"); await page.evaluate(token => { sessionStorage.clear(); sessionStorage.setItem("smart_wardrobe_access_token", token); }, auth.access_token);
  for (const code of [20, 23, 27]) {
    const buffer = Buffer.from(await page.evaluate(value => { const c = document.createElement("canvas"); c.width = c.height = 256; const x = c.getContext("2d")!; x.fillStyle = `rgb(${value},70,180)`; x.fillRect(0, 0, 256, 256); return [...Uint8Array.from(atob(c.toDataURL("image/png").split(",")[1]), v => v.charCodeAt(0))]; }, code));
    const response = await request.post(`${api}/processing/jobs?admission_mode=automatic_structural_v1`, { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer } } });
    expect(response.status()).toBe(202); const job = await response.json();
    await expect.poll(async () => (await (await request.get(`${api}/processing/jobs/${job.id}`, { headers })).json()).status).toBe("completed");
  }
  const garments = await (await request.get(`${api}/wardrobe/garments`, { headers })).json();
  for (const garment of garments) {
    expect((await request.patch(`${api}/wardrobe/garments/${garment.id}`, { headers, data: { description_update: { contract: "garment-description-update-1.0.0", expected_revision: garment.description.revision, operations: { colour_palette: { kind: "set", value: [{ hex: "#0000ff", coverage: "1" }] } } } } })).status()).toBe(200);
  }
  await page.goto("/assistant"); await page.getByRole("button", { name: "New Chat", exact: true }).click();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill("I'm going shopping.");
}
async function send(page: Page, button = "Suggest an outfit") {
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: button, exact: true }).click(); return await response;
}

test("B301 explicit C2 choice affects submitted mode and is retained for alternatives and history", async ({ page, request }) => {
  await seed(page, request); const checkbox = page.getByLabel("Use recorded palette colours for compatibility", { exact: true });
  await expect(checkbox).not.toBeChecked(); await checkbox.check();
  const response = await send(page), root = await response.json(); expect(root.outcome).toBe("Selected");
  expect(response.request().postDataJSON().compatibility_profile).toBe("recorded_palette_compatibility_v1");
  await expect(page.getByRole("region", { name: "Recorded palette compatibility", exact: true })).toBeVisible(); await expect(checkbox).toBeDisabled();
  const next = await send(page, "Suggest another outfit"), child = await next.json(); expect(child.outcome).toBe("Selected");
  expect(next.request().postDataJSON().compatibility_profile).toBe("recorded_palette_compatibility_v1"); expect(child.items).not.toEqual(root.items);
  await page.goto(`/history/${child.chat_id}`); await expect(page.getByRole("region", { name: "Recorded palette compatibility", exact: true })).toContainText("prototype");
  record("B301", { root, child });
});

test("B302 pending C2 exact retry survives reload and old omitted-mode draft stays C1", async ({ page, request }) => {
  await seed(page, request); await page.getByLabel("Use recorded palette colours for compatibility", { exact: true }).check();
  const attempts: unknown[] = [];
  await page.route("**/recommendations?pipeline=integrated", async route => {
    attempts.push({ body: route.request().postDataJSON(), wearer: route.request().headers()["x-wardrobe-profile-id"] });
    if (attempts.length === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ outcome: "PersistenceFailure" }) });
    await route.continue();
  });
  await send(page); await expect(page.getByRole("button", { name: "Retry same request", exact: true })).toBeVisible();
  const restored = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.reload(); expect((await (await restored).json()).outcome).toBe("Selected"); expect(attempts).toHaveLength(2); expect(attempts[0]).toEqual(attempts[1]);
  await page.getByRole("button", { name: "New Chat", exact: true }).click(); await page.getByLabel("What would you like to wear?", { exact: true }).fill("I'm going shopping.");
  await page.evaluate(() => { const key = Object.keys(sessionStorage).find(k => k.startsWith("smart_wardrobe_interaction:") && !k.includes("p2settings:"))!; const draft = JSON.parse(sessionStorage.getItem(key)!); delete draft.compatibilityProfile; draft.submitted = draft.text; sessionStorage.setItem(key, JSON.stringify(draft)); });
  const old = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST"); await page.reload(); const reply = await old;
  expect(reply.request().postDataJSON().compatibility_profile).toBeUndefined(); const result = await reply.json(); expect(result.provenance.palette_compatibility).toBeUndefined();
  record("B302", { attempts, omittedModeResult: result });
});
