// Actual app.main routes only. Process lifecycle is controlled outside HTTP.
import { test, expect, type APIRequestContext, type APIResponse, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const folder = process.env.SMART_WARDROBE_REHEARSAL_EVIDENCE!;
const statePath = resolve(folder, "state.json");
const password = "Local-rehearsal-password-123";
const text = "Suggest a casual outfit for campus with vintage style using blue colours with a top and trousers";
type Json = Awaited<ReturnType<APIResponse["json"]>>; // Retain complete variable-shape API evidence.
const state = (): Json => JSON.parse(readFileSync(statePath, "utf8"));
const save = (value: Json) => writeFileSync(statePath, JSON.stringify(value, null, 2));
const evidence = (stage: string, value: Json) => writeFileSync(resolve(folder, stage + "-browser.json"), JSON.stringify(value, null, 2));
const fraction = (value: Json) => value.numerator / value.denominator;

async function login(request: APIRequestContext, kind = "owner") {
  const result = await request.post(api + "/account/login", { data: { email: `j14-${kind}@example.test`, password } });
  expect(result.status()).toBe(200); const body = await result.json();
  return { token: body.access_token as string, headers: { Authorization: `Bearer ${body.access_token}` } };
}
async function authorize(page: Page, token: string) {
  await page.addInitScript(t => sessionStorage.setItem("smart_wardrobe_access_token", t), token);
}
async function upload(request: APIRequestContext, headers: Record<string, string>, image: Buffer, category = "vest_dress") {
  const response = await request.post(api + "/processing/jobs", { headers, multipart: { file: { name: "synthetic.png", mimeType: "image/png", buffer: image } } });
  expect(response.status()).toBe(202); const id = (await response.json()).id;
  const read = async () => await (await request.get(api + "/processing/jobs/" + id, { headers })).json();
  await expect.poll(async () => (await read()).status).toBe("review_required");
  const item = (await read()).items[0].id;
  const review = await request.post(`${api}/processing/jobs/${id}/review`, { headers, data: { items: [{ item_id: item, decision: "accepted", category, primary_colour: "blue", attributes: { style: ["vintage"] } }] } });
  expect(review.status()).toBe(200);
  return { id, body: { item_ids: [item], save_mode: "garments" } };
}
async function submit(request: APIRequestContext, headers: Record<string, string>, value: string, key = crypto.randomUUID()) {
  const response = await request.post(api + "/recommendations?pipeline=integrated", { headers, data: { request_text: value, submission_key: key } });
  return { http: response.status(), body: await response.json(), key };
}
async function browserSubmit(page: Page, value: string) {
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill(value);
  const pending = page.waitForResponse(r => r.url().includes("pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const response = await pending;
  return { http: response.status(), body: await response.json(), key: response.request().postDataJSON().submission_key };
}
async function declarations(page: Page, gid: string, campus: string) {
  await page.goto("/wardrobe"); const card = page.locator(`[data-garment-id="${gid}"]`);
  await card.getByRole("button", { name: "Edit", exact: true }).click();
  const form = card.getByRole("form");
  await form.getByRole("combobox", { name: "Occasion: Campus", exact: true }).selectOption(campus);
  await form.getByRole("combobox", { name: "Formality: Casual", exact: true }).selectOption("allow");
  const pending = page.waitForResponse(r => r.url().endsWith("/garments/" + gid) && r.request().method() === "PATCH");
  await form.getByRole("button", { name: "Save changes", exact: true }).click();
  expect((await pending).status()).toBe(200);
  await expect(card.getByRole("form")).toHaveCount(0);
}
function exactExperimental(result: Json) {
  expect(result.provenance.scoring_profile).toBe("experimental_compatibility_decision_v1");
  expect(result.provenance.assistant_execution_selection.engine).toBe("compact_exhaustive");
  expect(result.provenance.request_evaluator).toBe("SuitabilityRequestEvaluator");
  expect(result.score_metadata.weights.map(fraction)).toEqual([.6, .2, .2]);
  expect(result.total_score).toBe(1);
  expect(result.score_metadata.compatibility.decision.basis).toBe("Computed");
}
async function quotaFull(request: APIRequestContext) {
  const auth = await login(request, "quota");
  const quota = await (await request.get(api + "/wardrobe/quota", { headers: auth.headers })).json();
  expect(quota.used).toBe(100);
  const response = await request.post(api + "/processing/jobs", { headers: auth.headers, multipart: { file: { name: "full.png", mimeType: "image/png", buffer: Buffer.from("not reached after capacity check") } } });
  expect(response.status()).toBe(409); expect((await response.json()).detail.code).toBe("WardrobeQuotaExceeded");
  return quota;
}
async function oldHistory(page: Page, request: APIRequestContext, headers: Record<string, string>, old: Json) {
  const replay = await submit(request, headers, text, old.key);
  expect(replay.http).toBe(200); expect(replay.body.replayed).toBe(true);
  for (const key of ["id", "chat_id", "score_metadata", "provenance", "items"]) expect(replay.body[key]).toEqual(old.body[key]);
  const history = await (await request.get(`${api}/chats/${old.body.chat_id}`, { headers })).json();
  expect(history.recommendation.score_metadata).toEqual(old.body.score_metadata);
  await page.goto("/history/" + old.body.chat_id);
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await expect(page.getByText("Already saved as an independent outfit.", { exact: true })).toBeVisible();
  return { replay: replay.body, history, display: await page.getByTestId("recommendation-result").innerText() };
}

test("activated journey", async ({ page, request }) => {
  const auth = await login(request); await authorize(page, auth.token); const s = state();
  await page.goto("/wardrobe");
  const encoded = await page.evaluate(() => { const c = document.createElement("canvas"); c.width = 256; c.height = 256; c.getContext("2d")!.fillRect(0, 0, 256, 256); return c.toDataURL("image/png").split(",")[1]; });
  const image = Buffer.from(encoded, "base64"); const ids: string[] = [];
  for (const category of ["short_sleeve_top", "trousers", "vest_dress"]) {
    const job = await upload(request, auth.headers, image, category);
    const result = await request.post(`${api}/processing/jobs/${job.id}/confirm`, { headers: auth.headers, data: job.body });
    expect(result.status()).toBe(201); ids.push((await result.json()).garment_ids[0]);
  }
  for (const id of ids) await declarations(page, id, "allow");
  expect((await request.put(api + "/account/preferences/colours", { headers: auth.headers, data: { preference_value: { values: ["blue"] }, weight: 1 } })).status()).toBe(200);
  const homePending = page.waitForResponse(r => r.url().endsWith("/recommendations/homepage") && r.request().method() === "POST");
  await page.goto("/"); const homepage = await (await homePending).json();
  expect(homepage.outcome ?? homepage.status).toBe("Selected");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  expect(homepage.recommendation.items.every((item: Json) => ids.includes(item.garment_id))).toBe(true);
  expect((await (await request.get(api + "/chats", { headers: auth.headers })).json()).total).toBe(0);
  const first = await browserSubmit(page, text); expect(first.http).toBe(201); exactExperimental(first.body);
  expect(first.body.items.map((item: Json) => item.garment_id)).toEqual(ids.slice(0, 2));
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  const savedPending = page.waitForResponse(r => r.url().endsWith("/save-as-outfit") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Save as outfit", exact: true }).click();
  const saved = await savedPending; expect(saved.status()).toBe(201); const outfit = await saved.json();
  const prepared = await request.post(api + "/visualisations/prepare", { headers: auth.headers, data: { outfit_id: outfit.id } }); expect(prepared.status()).toBe(200);
  const negative: Json[] = [];
  for (const [choice, outcome] of [["deny", "NoMatchingCandidates"], ["unknown", "InsufficientEvidence"]]) {
    await declarations(page, ids[1], choice); const result = await submit(request, auth.headers, text); expect(result.body.outcome).toBe(outcome); negative.push(result);
  }
  await declarations(page, ids[1], "allow");
  const garments = await (await request.get(api + "/wardrobe/garments", { headers: auth.headers })).json(); const bottom = garments.find((g: Json) => g.id === ids[1]);
  expect((await request.patch(`${api}/wardrobe/garments/${ids[1]}`, { headers: { ...auth.headers, "If-Match": bottom.tag_edit.revision }, data: { attributes: { custom_tags: [...bottom.tag_edit.tags, "rec:v1:occasion:campus:deny"] } } })).status()).toBe(200);
  const conflict = await submit(request, auth.headers, text); expect(conflict.body.outcome).toBe("InsufficientEvidence");
  await declarations(page, ids[1], "allow");
  const unsupported = [];
  for (const value of ["Suggest an outfit for exercise", "Suggest a formal outfit"]) { const result = await submit(request, auth.headers, value); expect(result.body.outcome).toBe("PolicyUnavailable"); unsupported.push(result); }
  const foreign = await login(request, "other");
  expect((await request.get(`${api}/chats/${first.body.chat_id}`, { headers: foreign.headers })).status()).toBe(404);
  expect((await request.post(api + "/visualisations/prepare", { headers: foreign.headers, data: { outfit_id: outfit.id } })).status()).toBe(404);
  expect((await request.post(`${api}/recommendations/${first.body.id}/save-as-outfit`, { headers: foreign.headers, data: {} })).status()).toBe(404);
  const qa = await login(request, "quota"); const jobs = [await upload(request, qa.headers, image), await upload(request, qa.headers, image)];
  expect((await request.post(`${api}/processing/jobs/${jobs[0].id}/confirm`, { headers: qa.headers, data: jobs[0].body })).status()).toBe(201);
  const over = await request.post(`${api}/processing/jobs/${jobs[1].id}/confirm`, { headers: qa.headers, data: jobs[1].body }); expect(over.status()).toBe(409);
  expect((await over.json()).detail.code).toBe("WardrobeQuotaExceeded");
  expect((await (await request.get(`${api}/processing/jobs/${jobs[1].id}`, { headers: qa.headers })).json()).status).toBe("review_required");
  expect((await request.delete(`${api}/wardrobe/garments/quota-seed-0`, { headers: qa.headers })).status()).toBe(204);
  expect((await request.post(`${api}/processing/jobs/${jobs[1].id}/confirm`, { headers: qa.headers, data: jobs[1].body })).status()).toBe(201);
  const quota = await quotaFull(request); const original = await oldHistory(page, request, auth.headers, first);
  save({ ...s, ids, first, outfit, history_text: original.display, activated_homepage: homepage });
  evidence("activated", { first, homepage, saved_outfit: outfit, prepared: await prepared.json(), negative, conflict, unsupported, quota, original_history: original.history });
});

test("restarted journey", async ({ page, request }) => {
  const s = state(), auth = await login(request); await authorize(page, auth.token);
  const historical = await oldHistory(page, request, auth.headers, s.first); expect(historical.display).toBe(s.history_text);
  const fresh = await browserSubmit(page, text); expect(fresh.http).toBe(201); exactExperimental(fresh.body);
  expect(fresh.body.items.map((item: Json) => item.garment_id)).toEqual(s.ids.slice(0, 2));
  const quota = await quotaFull(request);
  save({ ...s, restarted: fresh }); evidence("restarted", { fresh, historical, quota });
});

test("rolled-back journey", async ({ page, request }) => {
  const s = state(), auth = await login(request); await authorize(page, auth.token);
  const historical = await oldHistory(page, request, auth.headers, s.first); expect(historical.display).toBe(s.history_text);
  const unavailable = await submit(request, auth.headers, text); expect(unavailable.body.outcome).toBe("PolicyUnavailable");
  const fresh = await browserSubmit(page, "Suggest an outfit with vintage style using blue colours with a top and trousers");
  expect(fresh.http).toBe(201); expect(fresh.body.provenance.scoring_profile).toBe("compatibility_deferred");
  expect(fresh.body.provenance.request_evaluator).toBe("RequestConstraintEvaluator");
  expect(fresh.body.score_metadata.weights.map(fraction)).toEqual([.7, 0, .3]);
  expect(fresh.body.compatibility_score).toBeNull(); expect(fresh.body.score_metadata.compatibility.summary.state).toBe("Unavailable");
  expect(fresh.body.total_score).toBe(1);
  const prepared = await request.post(api + "/visualisations/prepare", { headers: auth.headers, data: { outfit_id: s.outfit.id } }); expect(prepared.status()).toBe(200);
  const quota = await quotaFull(request); save({ ...s, rollback: fresh }); evidence("rollback", { fresh, unavailable, historical, quota, prepared: await prepared.json() });
});

test("disabled legacy boundary", async ({ page, request }) => {
  const s = state(), auth = await login(request); await authorize(page, auth.token);
  const capabilities = await (await request.get(api + "/recommendations/capabilities", { headers: auth.headers })).json(); expect(capabilities.assistant_enabled).toBe(false);
  const explicit = await submit(request, auth.headers, text); expect(explicit.http).toBe(404); expect(explicit.body.outcome).toBe("IntegrationDisabled");
  const postUrls: string[] = []; page.on("request", r => { if (r.method() === "POST" && r.url().includes("/recommendations")) postUrls.push(r.url()); });
  await page.goto("/assistant"); await page.getByLabel("What would you like to wear?").fill("Suggest an outfit");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  await expect(page.getByText("This recommendation feature is disabled on the backend. No placeholder result will be used.", { exact: true })).toBeVisible(); expect(postUrls).toEqual([]);
  const blocked = [];
  for (const body of [{ request_text: "Suggest an outfit" }, { request_text: "Suggest an outfit", submission_key: "legacy-repeat" }, { request_text: "Suggest an outfit", submission_key: "legacy-repeat" }]) {
    const response = await request.post(api + "/recommendations", { headers: auth.headers, data: body });
    expect(response.status()).toBe(404);
    const value = await response.json(); expect(value).toEqual({ status: "IntegrationDisabled", outcome: "IntegrationDisabled", complete: false }); blocked.push(value);
  }
  const history = await (await request.get(`${api}/chats/${s.first.body.chat_id}`, { headers: auth.headers })).json(); expect(history.recommendation.score_metadata).toEqual(s.first.body.score_metadata);
  const quota = await quotaFull(request); evidence("disabled", { capabilities, explicit, blocked, frontend_generation_posts: postUrls, original_history: history, quota });
});
