import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const api = "http://127.0.0.1:3101/api/v1";
const password = "J22-disposable-password-123";
const tokenKey = "smart_wardrobe_access_token";
const draftKey = "smart_wardrobe_interaction:j22-preserved";
const record = (name: string, result: unknown) => writeFileSync(resolve(process.env.SMART_WARDROBE_CLOSURE_EVIDENCE!, name + ".json"), JSON.stringify(result, null, 2));

async function owner(request: APIRequestContext, page: Page, name: string) {
  const email = `j22-${name}@example.test`;
  expect((await request.post(api + "/account/register", { data: { email, password, password_confirmation: password, display_name: "J22 Owner" } })).status()).toBe(201);
  await page.goto("/auth");
  const form = page.locator("form");
  await form.getByLabel("Email", { exact: true }).fill(email);
  await form.getByLabel("Password", { exact: true }).fill(password);
  await form.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("/");
  await page.goto("/profile");
  await expect(page.getByRole("form", { name: "Profile information" })).toBeVisible();
  await page.evaluate(key => sessionStorage.setItem(key, "saved draft"), draftKey);
  const token = (await page.evaluate(key => sessionStorage.getItem(key), tokenKey))!;
  return { token, email };
}
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });
async function cleared(page: Page) {
  await page.waitForURL("/auth");
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBeNull();
  expect(await page.evaluate(key => sessionStorage.getItem(key), draftKey)).toBeNull();
  expect(await page.evaluate(() => window.history.state?.wardrobeHomepage)).toBeUndefined();
}

test("committed logout pending protection keyboard cleanup and independent session", async ({ request, page }) => {
  const { token, email } = await owner(request, page, "success");
  const second = (await (await request.post(api + "/account/login", { data: { email, password } })).json()).access_token as string;
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let committed!: () => void;
  const wrote = new Promise<void>(resolve => { committed = resolve; });
  let posts = 0;
  await page.route("**/api/v1/account/logout", async route => {
    posts++;
    expect(route.request().headers().authorization).toBe(`Bearer ${token}`);
    const response = await route.fetch();
    expect(response.status()).toBe(204);
    committed(); await gate; await route.fulfill({ response });
  });
  const button = page.getByRole("button", { name: "Sign out", exact: true });
  await button.focus(); await page.keyboard.press("Enter"); await wrote;
  await expect(page.getByRole("button", { name: "Signing out…", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Signing out…", exact: true }).evaluate(element => (element as HTMLButtonElement).click());
  expect(posts).toBe(1);
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBe(token);
  expect((await request.get(api + "/account/profile", { headers: auth(token) })).status()).toBe(401);
  release(); await cleared(page);
  expect((await request.get(api + "/account/profile", { headers: auth(second) })).status()).toBe(200);
  record("logout-success", { committed: 204, copied: 401, independent: 200, posts, localCleanup: true, keyboard: true });
});

test("server and network failures preserve session and drafts then retry succeeds", async ({ request, page }) => {
  const { token } = await owner(request, page, "failures");
  await page.route("**/api/v1/account/logout", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "private internal sentinel" }) }));
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toHaveText("Could not sign out. Your session was kept. Use Retry sign out to try again.");
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBe(token);
  expect(await page.evaluate(key => sessionStorage.getItem(key), draftKey)).toBe("saved draft");
  expect((await request.get(api + "/account/profile", { headers: auth(token) })).status()).toBe(200);
  await page.unroute("**/api/v1/account/logout");
  await page.route("**/api/v1/account/logout", route => route.abort("failed"));
  await page.getByRole("button", { name: "Retry sign out", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toBeVisible();
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBe(token);
  await page.unroute("**/api/v1/account/logout");
  await page.getByRole("button", { name: "Retry sign out", exact: true }).click(); await cleared(page);
  record("logout-failure-retry", { serverFailurePreserved: true, networkFailurePreserved: true, retry: 204, noInternalMessage: true });
});

test("lost committed response preserves local state and idempotent retry completes", async ({ request, page }) => {
  const { token } = await owner(request, page, "lost-response");
  await page.route("**/api/v1/account/logout", async route => {
    expect((await route.fetch()).status()).toBe(204);
    await route.abort("failed");
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toBeVisible();
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBe(token);
  expect(await page.evaluate(key => sessionStorage.getItem(key), draftKey)).toBe("saved draft");
  expect((await request.get(api + "/account/profile", { headers: auth(token) })).status()).toBe(401);
  await page.unroute("**/api/v1/account/logout");
  const retried = page.waitForResponse(r => r.url().endsWith("/account/logout"));
  await page.getByRole("button", { name: "Retry sign out", exact: true }).click();
  expect((await retried).status()).toBe(204); await cleared(page);
  record("logout-lost-response", { committedButLost: true, copied: 401, localPreservedUntilRetry: true, retry: 204 });
});

test("stale logout completion cannot clear a newer login", async ({ request, page }) => {
  const { token, email } = await owner(request, page, "stale");
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let committed!: () => void;
  const wrote = new Promise<void>(resolve => { committed = resolve; });
  await page.route("**/api/v1/account/logout", async route => {
    expect(route.request().headers().authorization).toBe(`Bearer ${token}`);
    const response = await route.fetch(); expect(response.status()).toBe(204);
    committed(); await gate; await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click(); await wrote;
  const next = (await (await request.post(api + "/account/login", { data: { email, password } })).json()).access_token as string;
  expect(next).not.toBe(token);
  await page.evaluate(({ key, value }) => sessionStorage.setItem(key, value), { key: tokenKey, value: next });
  release();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeEnabled();
  expect(new URL(page.url()).pathname).toBe("/profile");
  expect(await page.evaluate(key => sessionStorage.getItem(key), tokenKey)).toBe(next);
  expect(await page.evaluate(key => sessionStorage.getItem(key), draftKey)).toBe("saved draft");
  expect((await request.get(api + "/account/profile", { headers: auth(next) })).status()).toBe(200);
  record("logout-stale", { oldRevoked: true, newerIdentityRetained: true, newerProtected: 200 });
});

test("invalid local credential ends local authentication without fabricated commit", async ({ request, page }) => {
  await owner(request, page, "invalid-local");
  await page.evaluate(key => sessionStorage.setItem(key, "invalid-local-bearer"), tokenKey);
  const response = page.waitForResponse(r => r.url().endsWith("/account/logout"));
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  expect((await response).status()).toBe(401); await cleared(page);
  record("logout-invalid-local", { server: 401, localCleanup: true, revocationAcknowledged: false });
});
