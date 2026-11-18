import { expect, test } from "@playwright/test";

test("resume a group job and remove a completed preview from history", async ({ page }) => {
  await page.addInitScript(() => { sessionStorage.setItem("smart_wardrobe_access_token", "test"); sessionStorage.setItem("smart_wardrobe_profile_id", "profile"); });
  let removed = false;
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (path.endsWith("/account/wardrobe-profiles")) body = [];
    else if (path.endsWith("/activity")) body = { queue_order: "not_guaranteed", jobs: [{ kind: "group", id: "g1", status: "queued", progress_message: "Waiting for GPU", progress_percent: null, created_at: "2026-11-14T10:00:00Z", updated_at: "2026-11-14T10:00:00Z" }] };
    else if (path.endsWith("/visualisations/history/group/g2") && route.request().method() === "DELETE") { removed = true; return route.fulfill({ status: 204 }); }
    else if (path.endsWith("/visualisations/history")) body = removed ? [] : [{ kind: "group", id: "g2", output_media_id: "result", created_at: "2026-11-14T10:00:00Z", finished_at: "2026-11-14T10:00:00Z", output_kind: "generated" }];
    else if (path.endsWith("/visualisations/groups/g1")) body = { id: "g1", status: "processing", progress_message: "Generating", error_message: null, output_media_id: null };
    else if (path.includes("/media/")) return route.fulfill({ status: 200, contentType: "image/png", body: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=", "base64") });
    else return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/activity");
  await expect(page.getByText("Waiting for GPU")).toBeVisible();
  await page.getByRole("article").filter({ hasText: "Group try-on" }).getByRole("link", { name: "View progress" }).click();
  await expect(page.getByText("Generating", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Try-on history" }).last().click();
  await expect(page.getByRole("heading", { name: "Group try-on" })).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText(/No completed try-ons yet/)).toBeVisible();
  expect(removed).toBe(true);
});
