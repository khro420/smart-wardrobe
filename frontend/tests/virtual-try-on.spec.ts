import { expect, test } from "@playwright/test";

const pixel = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=", "base64");

test("select people independently and submit their assigned outfits", async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("smart_wardrobe_access_token", "test-token");
    sessionStorage.setItem("smart_wardrobe_profile_id", "profile");
  });
  let submitted: unknown;
  const photo = { id: "photo-1", media_id: "media-1", display_name: "Saved photo", status: "available" };
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (path.endsWith("/account/wardrobe-profiles")) body = [{ id: "profile", name: "Me", status: "active", is_default: true }];
    else if (path.endsWith("/visualisations/person-images")) body = [photo];
    else if (path.endsWith("/wardrobe/outfits")) body = [{ id: "a", name: "Outfit A", items: [{ garment_id: "red", name: "Red top", preferred_media_id: "red-media" }, { garment_id: "pants", name: "Black trousers", preferred_media_id: "pants-media" }] }, { id: "b", name: "Outfit B", items: [{ garment_id: "blue", name: "Blue dress", preferred_media_id: "blue-media" }] }];
    else if (path.endsWith("/media/person-images")) body = { ...photo, id: "uploaded", display_name: "Uploaded photo" };
    else if (path.endsWith("/visualisations/groups/detect")) body = { id: "group-1", width: 300, height: 400, people: [{ index: 0, box: [10, 40, 90, 380] }, { index: 1, box: [100, 40, 190, 380] }, { index: 2, box: [200, 40, 290, 380] }] };
    else if (path.endsWith("/visualisations/groups/group-1") && route.request().method() === "POST") { submitted = route.request().postDataJSON(); body = { id: "group-1", status: "queued" }; }
    else if (path.endsWith("/visualisations/groups/group-1")) body = { id: "group-1", status: "completed", progress_message: "Ready", error_message: null, output_media_id: "media-1" };
    else if (path.includes("/media/")) return route.fulfill({ status: 200, contentType: "image/png", body: pixel });
    else return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/try-on/group");
  await expect(page.getByRole("link", { name: "Virtual try-on" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Saved photo" }).click();
  await expect(page.getByRole("heading", { name: "Who would you like to dress?" })).toBeVisible();
  await page.getByRole("button", { name: "Select person 1" }).click();
  await page.getByRole("button", { name: "Select person 2" }).click();
  await page.getByRole("button", { name: "Select person 3" }).click();
  await expect(page.getByText(/You can select up to two people/)).toBeVisible();
  await page.getByRole("button", { name: "Remove person 1" }).click();
  await page.getByRole("button", { name: "Select person 3" }).click();
  await page.getByRole("button", { name: "Confirm people" }).click();
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeDisabled();
  const first = page.getByRole("region", { name: "Outfits for person 2" });
  const second = page.getByRole("region", { name: "Outfits for person 3" });
  await expect(first.getByRole("img", { name: "Red top" })).toBeVisible();
  await expect(first.getByRole("img", { name: "Black trousers" })).toBeVisible();
  await expect(second.getByRole("img", { name: "Blue dress" })).toBeVisible();
  await first.getByRole("article").filter({ hasText: "Outfit A" }).getByRole("button", { name: "Select outfit" }).click();
  await second.getByRole("article").filter({ hasText: "Outfit B" }).getByRole("button", { name: "Select outfit" }).click();
  await page.getByRole("button", { name: "Generate preview" }).click();
  await expect(page.getByRole("button", { name: "Download preview" })).toBeVisible();
  expect(submitted).toEqual({ assignments: [{ person_index: 1, outfit_id: "a" }, { person_index: 2, outfit_id: "b" }] });
  await page.getByRole("button", { name: "Start another try-on" }).click();
  await page.getByLabel("Upload a photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: pixel });
  await expect(page.getByRole("heading", { name: "Who would you like to dress?" })).toBeVisible();
});
