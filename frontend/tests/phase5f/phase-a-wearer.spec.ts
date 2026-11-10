import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const record = (name: string, data: unknown) => writeFileSync(join(process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!, name + ".json"), JSON.stringify(data, null, 2));

async function account(page: Page, request: APIRequestContext) {
  const email = `wearer-${crypto.randomUUID()}@example.test`, password = "Disposable-Wearer-Password-123";
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "Wearer mechanics" } })).status()).toBe(201);
  const auth = await (await request.post(api + "/account/login", { data: { email, password } })).json();
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  const profiles = await (await request.get(api + "/account/wardrobe-profiles", { headers })).json();
  await page.goto("/auth");
  await page.evaluate(token => { sessionStorage.clear(); sessionStorage.setItem("smart_wardrobe_access_token", token); }, auth.access_token);
  return { headers, a: profiles[0].id as string };
}

async function seed(page: Page, request: APIRequestContext, headers: Record<string, string>) {
  for (const code of [20, 21, 22, 23, 24, 25, 26, 27]) {
    const buffer = Buffer.from(await page.evaluate(value => { const canvas = document.createElement("canvas"); canvas.width = canvas.height = 256; const context = canvas.getContext("2d")!; context.fillStyle = `rgb(${value},70,180)`; context.fillRect(0, 0, 256, 256); return [...Uint8Array.from(atob(canvas.toDataURL("image/png").split(",")[1]), c => c.charCodeAt(0))]; }, code));
    const submitted = await request.post(api + "/processing/jobs?admission_mode=automatic_structural_v1", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer } } });
    expect(submitted.status()).toBe(202); const job = await submitted.json();
    await expect.poll(async () => (await (await request.get(api + "/processing/jobs/" + job.id, { headers })).json()).status).toBe("completed");
  }
}

async function choose(page: Page, wearer: string) {
  const loaded = page.waitForEvent("load");
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(wearer);
  await loaded;
  await expect(page.getByRole("combobox", { name: "Select active wardrobe profile" }).first()).toHaveValue(wearer);
}

async function ask(page: Page) {
  await expect(page.getByLabel("What would you like to wear?", { exact: true })).toBeVisible();
  await page.getByLabel("What would you like to wear?", { exact: true }).fill("I'm going shopping.");
  const response = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  return (await response).json();
}

test("PA01 explicit wearer, pending alternative survives only in its own namespace", async ({ page, request }) => {
  const { headers, a } = await account(page, request); await seed(page, request, headers);
  const b = (await (await request.post(api + "/account/wardrobe-profiles", { headers, data: { name: "Wearer B" } })).json()).id;
  await page.goto("/assistant");
  await expect(page.getByRole("combobox", { name: "Select active wardrobe profile" }).first()).toHaveValue("");
  await expect(page.getByRole("button", { name: "Suggest an outfit", exact: true })).toBeDisabled();
  await choose(page, a); const root = await ask(page);
  expect(root.intended_wearer.profile_id).toBe(a);
  const captured: {body: Record<string, unknown>; header: string | undefined}[] = [];
  await page.route("**/recommendations?pipeline=integrated", async route => {
    const body = route.request().postDataJSON();
    if (body.refinement?.kind === "alternative") {
      captured.push({ body, header: route.request().headers()["x-wardrobe-profile-id"] });
      if (captured.length === 1) { await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ outcome: "PersistenceFailure", complete: false }) }); return; }
    }
    await route.continue();
  });
  await page.getByRole("button", { name: "Suggest another outfit", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry same request", exact: true })).toBeVisible();
  await choose(page, b);
  await expect(page.getByLabel("What would you like to wear?", { exact: true })).toHaveValue("");
  expect(captured).toHaveLength(1); const second = await ask(page);
  expect(second.intended_wearer.profile_id).toBe(b);
  expect(second.provenance.refinement.root_id).not.toBe(root.id);
  await choose(page, a);
  await expect(page.getByLabel("Recommendation sequence")).toContainText("Alternative 1");
  expect(captured).toHaveLength(2); expect(captured[0]).toEqual(captured[1]);
  expect(captured[1].header).toBe(a); record("PA01", { root, second, captured });
});

test("PA02 archive retains history and exposes read-only historical processing", async ({ page, request }) => {
  const { headers, a } = await account(page, request); await seed(page, request, headers);
  await page.goto("/assistant"); const root = await ask(page);
  await request.post(api + "/account/wardrobe-profiles", { headers, data: { name: "Successor" } });
  await page.goto("/profile");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("listitem").filter({ hasText: "My wardrobe" }).getByRole("button", { name: "Archive wearer", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Archived wearers", exact: true })).toBeVisible();
  await page.goto(`/history/${root.chat_id}?view=historical&wearer_profile_id=${a}`);
  await expect(page.getByTestId("recommendation-result")).toContainText("My wardrobe — Archived");
  await expect(page.getByRole("button", { name: "Save as outfit", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Suggest another outfit", exact: true })).toHaveCount(0);
  await page.goto(`/extract/results?view=historical&wearer_profile_id=${a}`);
  await page.getByRole("link", { name: /^completed/ }).first().click();
  await expect(page.getByRole("heading", { name: "Processing history — read-only", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Save|Retry automatic|Accept/ })).toHaveCount(0);
  record("PA02", { historicalRead: true, wearer: a, originalScore: root.scoring_display });
});

test("PA03 Homepage back never submits the previous wearer's key as another wearer", async ({ page, request }) => {
  const { headers, a } = await account(page, request); await seed(page, request, headers);
  const b = (await (await request.post(api + "/account/wardrobe-profiles", { headers, data: { name: "B" } })).json()).id;
  await page.goto("/assistant"); await choose(page, a);
  const posts: {submission_key: string; wearer_profile_id: string}[] = [];
  page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/recommendations/homepage")) posts.push(r.postDataJSON()); });
  await page.goto("/"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await page.getByRole("link", { name: "Outfit Assistant", exact: true }).first().click();
  await choose(page, b); await page.goBack();
  await page.goto("/"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  const first = posts.find(p => p.wearer_profile_id === a), second = posts.find(p => p.wearer_profile_id === b);
  expect(first).toBeTruthy(); expect(second).toBeTruthy(); expect(first!.submission_key).not.toBe(second!.submission_key);
  for (const x of posts) for (const y of posts) if (x.submission_key === y.submission_key) expect(x.wearer_profile_id).toBe(y.wearer_profile_id);
  record("PA03", posts);
});
