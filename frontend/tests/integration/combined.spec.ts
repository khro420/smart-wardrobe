import { test, expect, type APIResponse, type Response } from "@playwright/test";
import { randomUUID } from "node:crypto";

// Normal authenticated HTTP and browser workflows. The development image adapter
// is explicit: owner declarations below are synthetic, never model accuracy proof.
test("combined processing, subtype transfer, assistant, alternatives and wearer history", async ({ page, request }) => {
  const email = `integration-${randomUUID()}@example.test`;
  const password = `Functional-only-${randomUUID()}`;
  async function json(response: APIResponse | Response, status: number) {
    expect(response.status(), await response.text()).toBe(status);
    return response.json();
  }
  await json(await request.post("/api/v1/account/register", { data: {
    email, password, password_confirmation: password, display_name: "Disposable integration owner",
  }}), 201);
  const login = await json(await request.post("/api/v1/account/login", { data: { email, password } }), 200);
  const headers: Record<string, string> = { Authorization: `Bearer ${login.access_token}` };
  const profiles = await json(await request.get("/api/v1/account/wardrobe-profiles", { headers }), 200);
  const male = profiles.find((p: { is_default: boolean }) => p.is_default) ?? profiles[0];
  const female = await json(await request.post("/api/v1/account/wardrobe-profiles", {
    headers, data: { name: "Integration female" },
  }), 201);
  for (const [wearer, gender] of [[male.id, "male"], [female.id, "female"]]) {
    const h = { ...headers, "X-Wardrobe-Profile-Id": wearer };
    const url = `/api/v1/account/wardrobe-profiles/${wearer}/details`;
    const current = await json(await request.get(url, { headers: h }), 200);
    await json(await request.put(url, { headers: h, data: {
      version: "wearer-profile-details-1.0.0", expected_revision: current.revision, gender_identity: gender,
    }}), 200);
  }
  headers["X-Wardrobe-Profile-Id"] = female.id;
  await page.goto("/auth");
  const png = await page.evaluate(() => {
    const canvas = document.createElement("canvas"); canvas.width = canvas.height = 256;
    const context = canvas.getContext("2d")!; context.fillStyle = "blue"; context.fillRect(0, 0, 256, 256);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  const garments: string[] = [];
  for (const [index, category] of ["short_sleeve_top", "short_sleeve_top", "trousers", "trousers"].entries()) {
    const created = await json(await request.post("/api/v1/processing/jobs", {
      headers, multipart: { file: { name: "synthetic-owner-declaration.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") } },
    }), 202);
    let job;
    for (let poll = 0; poll < 100; poll++) {
      job = await json(await request.get(`/api/v1/processing/jobs/${created.id}`, { headers }), 200);
      if (job.status === "review_required" || job.status === "failed") break;
      await page.waitForTimeout(100);
    }
    expect(job.status).toBe("review_required"); expect(job.items).toHaveLength(1);
    const item = job.items[0];
    expect(item.id).toMatch(/^[0-9a-f-]{36}$/);
    const subtype = category === "short_sleeve_top" ? { subtype_update: {
      action_id: randomUUID(), expected_revision: null, state: "Known", value: "t_shirt",
      review_basis: "synthetic_fixture_declaration", reason: "Authored functional-test declaration, not a model claim",
    }} : {};
    await json(await request.post(`/api/v1/processing/jobs/${created.id}/review`, {
      headers, data: { items: [{ item_id: item.id, decision: "accepted", category,
        name: `Synthetic ${category} ${index}`, primary_colour: "blue", pattern: "plain",
        attributes: { style: ["casual"], material: ["cotton"] }, ...subtype }] },
    }), 200);
    const confirmed = await json(await request.post(`/api/v1/processing/jobs/${created.id}/confirm`, {
      headers, data: { item_ids: [item.id], save_mode: "garments" },
    }), 201);
    const gid = confirmed.garment_ids[0]; expect(gid).not.toBe(item.id); garments.push(gid);
    if (category === "short_sleeve_top") {
      const evidence = await json(await request.get(`/api/v1/wardrobe/garments/${gid}/subtype`, { headers }), 200);
      expect(evidence.state).toBe("Known"); expect(evidence.value).toBe("t_shirt");
    }
  }
  expect(await json(await request.get("/api/v1/wardrobe/garments", { headers }), 200)).toHaveLength(4);
  // Sign in through the rendered app rather than installing a fake browser identity.
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.locator("form").getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL(url => url.pathname === "/");
  await page.goto("/assistant");
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(male.id);
  await page.getByRole("button", { name: "New Chat", exact: true }).click();
  const text = "I want a T-shirt.";
  await page.getByLabel("What would you like to wear?", { exact: true }).fill(text);
  const rootResponse = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
  const root = await json(await rootResponse, 201);
  expect(root.outcome).toBe("Selected"); expect(root.replayed).toBe(false);
  expect(root.items.every((i: { garment_id: string }) => garments.includes(i.garment_id))).toBe(true);
  await expect(page.getByRole("region", { name: "Captured garment types" })).toContainText("T-shirt");
  const childResponse = page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Suggest another outfit", exact: true }).click();
  const child = await json(await childResponse, 201);
  expect(child.id).not.toBe(root.id);
  expect(child.items.map((i: { garment_id: string }) => i.garment_id)).not.toEqual(root.items.map((i: { garment_id: string }) => i.garment_id));
  expect(child.provenance.attribute_selection.intent).toEqual(root.provenance.attribute_selection.intent);
  const maleHeaders = { ...headers, "X-Wardrobe-Profile-Id": male.id };
  const saved = await json(await request.get(`/api/v1/chats/${child.chat_id}`, { headers: maleHeaders }), 200);
  expect(saved.recommendation.scoring_display).toEqual(child.scoring_display);
  await page.goto(`/history/${child.chat_id}`);
  await expect(page.getByRole("region", { name: "Captured garment types" })).toContainText("T-shirt");
  await page.reload();
  await expect(page.getByRole("region", { name: "Captured garment types" })).toContainText("T-shirt");
  await page.getByRole("combobox", { name: "Select active wardrobe profile" }).first().selectOption(female.id);
  expect((await request.get(`/api/v1/chats/${child.chat_id}`, { headers })).status()).toBe(404);
  const shared = await json(await request.get("/api/v1/wardrobe/garments", { headers }), 200);
  expect(shared).toHaveLength(4);
  const unchanged = await json(await request.get(`/api/v1/chats/${child.chat_id}`, { headers: maleHeaders }), 200);
  expect(unchanged.recommendation).toEqual(saved.recommendation);
  await test.info().attach("normal-lifecycle-identities", { body: JSON.stringify({ male: male.id, female: female.id, garments, root: root.id, child: child.id }), contentType: "application/json" });
});
