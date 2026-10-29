import { test, expect, type Page } from "@playwright/test";

const backend = "http://127.0.0.1:3101";
async function prepare(page: Page, used: number) {
  expect((await page.request.post(`${backend}/_test/quota/setup/${used}`)).ok()).toBeTruthy();
  const response = await page.request.post(`${backend}/api/v1/account/login`, { data: { email: "quota@example.test", password: "Quota-test-password-123" } });
  expect(response.ok()).toBeTruthy();
  const token = (await response.json()).access_token as string;
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token", value), token);
  return { Authorization: `Bearer ${token}` };
}
const capacity = (page: Page) => page.getByRole("region", { name: "Wardrobe capacity" });

test("unfiltered usage refreshes after a committed UI archive", async ({ page }) => {
  await prepare(page, 100); await page.goto("/wardrobe");
  await expect(capacity(page)).toContainText("Active garments: 100 / 100");
  await expect(page.getByRole("button", { name: "Add from image (wardrobe full)" })).toBeDisabled();
  await page.getByRole("textbox", { name: "Search garments" }).fill("does not exist");
  await expect(page.getByText("No matching garments.", { exact: false })).toBeVisible();
  await expect(capacity(page)).toContainText("100 / 100");
  await page.getByRole("textbox", { name: "Search garments" }).fill("");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Archive Existing quota-existing-0", exact: true }).click();
  await expect(capacity(page)).toContainText("Active garments: 99 / 100");
  await expect(page.getByRole("link", { name: "Add from image" })).toBeVisible();
});

test("full upload and over-limit UI keep existing management available", async ({ page }) => {
  await prepare(page, 101); await page.goto("/extract");
  await expect(capacity(page)).toContainText("Active garments: 101 / 100");
  await expect(capacity(page)).toContainText("over capacity");
  await expect(page.getByRole("button", { name: /upload|choose.*photo/i })).toBeDisabled();
  await page.goto("/wardrobe");
  await expect(page.locator("[data-garment-id]")).toHaveCount(101);
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Archive Existing quota-existing-0", exact: true }).click();
  await expect(capacity(page)).toContainText("Active garments: 100 / 100");
  await expect(page.getByRole("button", { name: "Add from image (wardrobe full)" })).toBeDisabled();
});

test("explicit subset saves only selected accepted candidates and completes job", async ({ page }) => {
  const headers = await prepare(page, 99); await page.goto("/extract/results?job=quota-job");
  await expect(page.getByRole("button", { name: "Save selected garments", exact: true })).toBeDisabled();
  await page.getByTestId("save-candidate-quota-new-1").uncheck();
  await expect(page.getByText("Only these selected garments will be saved.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Save selected garments", exact: true }).click();
  await expect(page).toHaveURL(/\/wardrobe$/);
  await expect(capacity(page)).toContainText("Active garments: 100 / 100");
  const job = await (await page.request.get(`${backend}/api/v1/processing/jobs/quota-job`, { headers })).json();
  expect(job.status).toBe("completed");
  expect(job.items.map((item: { review_status: string }) => item.review_status)).toEqual(["confirmed", "accepted"]);
  const duplicate = await page.request.post(`${backend}/api/v1/processing/jobs/quota-job/confirm`, { headers, data: { item_ids: ["quota-new-1"], save_mode: "garments" } });
  expect(duplicate.status()).toBe(409);
});

test("stale capacity conflict preserves selection and outfit name then refreshes", async ({ page }) => {
  const headers = await prepare(page, 99); await page.goto("/extract/results?job=quota-job");
  await expect(capacity(page)).toContainText("99 / 100");
  await page.getByTestId("save-candidate-quota-new-1").uncheck();
  await page.getByRole("textbox", { name: "Outfit name (required when saving as an outfit)" }).fill("Preserved name");
  await page.request.post(`${backend}/_test/quota/fill`);
  await page.getByRole("button", { name: "Save as outfit", exact: true }).click();
  await expect(page.getByText("You have 100 of 100 active garments and selected 1.", { exact: false })).toBeVisible();
  await expect(capacity(page)).toContainText("100 / 100");
  await expect(page.getByTestId("save-candidate-quota-new-1")).not.toBeChecked();
  await expect(page.getByRole("textbox", { name: "Outfit name (required when saving as an outfit)" })).toHaveValue("Preserved name");
  expect((await page.request.delete(`${backend}/api/v1/wardrobe/garments/quota-existing-0`, { headers })).status()).toBe(204);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(capacity(page)).toContainText("99 / 100");
  await page.getByRole("button", { name: "Save as outfit", exact: true }).click();
  await expect(page).toHaveURL(/\/wardrobe$/);
  await expect(capacity(page)).toContainText("100 / 100");
});

test("unavailable capacity can refresh without inventing a count", async ({ page }) => {
  await prepare(page, 99);
  await page.route("**/api/v1/wardrobe/quota", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.goto("/wardrobe");
  await expect(capacity(page)).toContainText("Capacity unavailable");
  await expect(page.locator("[data-garment-id]")).toHaveCount(99);
  await page.unroute("**/api/v1/wardrobe/quota");
  await page.getByRole("button", { name: "Refresh capacity" }).click();
  await expect(capacity(page)).toContainText("99 / 100");
});

test("lost confirmation response reconciles completed job without another write", async ({ page }) => {
  const headers = await prepare(page, 99); await page.goto("/extract/results?job=quota-job");
  await expect(capacity(page)).toContainText("99 / 100");
  await page.getByTestId("save-candidate-quota-new-1").uncheck();
  let submissions = 0;
  await page.route("**/processing/jobs/quota-job/confirm", async route => {
    submissions++;
    const response = await route.fetch(); expect(response.status()).toBe(201);
    await route.abort("failed");
  });
  await page.getByRole("button", { name: "Save selected garments", exact: true }).click();
  await expect(page.getByText("These candidates have already been saved.", { exact: false })).toBeVisible();
  await expect(capacity(page)).toContainText("100 / 100");
  await expect(page.getByRole("button", { name: "Save selected garments", exact: true })).toHaveCount(0);
  expect(submissions).toBe(1);
  const result = await page.request.get(`${backend}/api/v1/wardrobe/quota`, { headers });
  expect((await result.json()).used).toBe(100);
});
