import { test, expect, type APIResponse, type Page } from "@playwright/test";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
type Json = Awaited<ReturnType<APIResponse["json"]>>;
type Clock = { mode: string; t0: number | null; t1: number | null; done: boolean; armed: boolean;
  ids: string[]; term: string; total: number; checks: number; observer_ms: number; kind: string };
declare global { interface Window { __nfr: Clock } }
const messages: Record<string, string> = {
  NoEligibleGarments: "No confirmed, available garments can be used.",
  NoMatchingCandidates: "No outfit meets all required conditions.",
  UnsupportedRequest: "This request contains unsupported or unrepresentable conditions.",
  PolicyUnavailable: "Matching rules for one or more requested conditions are not available.",
  InsufficientEvidence: "Garment information is insufficient to establish all required conditions.",
};

test("J16 frozen local NFR population with every observation retained", async ({ browser, request }) => {
  test.skip(!process.env.SMART_WARDROBE_NFR_RUN, "Explicit frozen collection only");
  const folder = resolve(process.env.SMART_WARDROBE_NFR_RUN!);
  const root = resolve("..");
  const plan = JSON.parse(readFileSync(resolve(root, "storage/verification/phase5f2e3j16/plan.json"), "utf8"));
  const scores = JSON.parse(readFileSync(resolve(root, "storage/verification/phase5f2e3j16/expected-scores.json"), "utf8"));
  const mix = JSON.parse(readFileSync(resolve(root, "backend/tests/fixtures/capacity_100.v1.json"), "utf8"));
  const expectedHistory = JSON.parse(readFileSync(resolve(folder, "history-expected.json"), "utf8"));
  const output = resolve(folder, "trials.json");
  expect(existsSync(output)).toBe(false);
  const rows: Json[] = [], invariants: Json[] = []; let phase = "waiting_resources";
  const save = () => { writeFileSync(output, JSON.stringify({ phase, rows, invariants, plan_version: plan.version }, null, 2)); writeFileSync(resolve(folder, "collector-phase.txt"), phase); };
  save();
  const probe = await browser.newContext(); const probePage = await probe.newPage();
  await probePage.goto("http://127.0.0.1:3100/auth"); await probe.close();
  writeFileSync(resolve(folder, "browser-environment.json"), JSON.stringify({ chromium: browser.version(), playwright: JSON.parse(readFileSync(resolve("node_modules/playwright-core/package.json"), "utf8")).version, viewport: "1280x960", mode: "headless", authentication_preparation: "Public auth route only; no recommendation warm-up" }, null, 2));
  writeFileSync(resolve(folder, "browser-ready"), "ready");
  const resourceWait = performance.now();
  while (!existsSync(resolve(folder, "resource-qualified"))) {
    if (existsSync(resolve(folder, "resource-blocked"))) throw new Error("Resource gate blocked; zero timed submissions");
    if (performance.now() - resourceWait > 150000) throw new Error("Resource gate controller did not settle");
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  phase = "running"; save();
  const api = "http://127.0.0.1:3101/api/v1";
  const login = async (owner: string) => {
    const response = await request.post(api + "/account/login", { data: { email: owner + "@nfr.example.test", password: "NFR-local-password-123" } });
    expect(response.status()).toBe(200); const token = (await response.json()).access_token;
    return { token, headers: { Authorization: "Bearer " + token } };
  };
  const install = async (page: Page, mode: string, initial: boolean, expected: Json) => {
    await page.addInitScript(({ mode, initial, expected }) => {
      const s: Clock = { mode, t0: mode === "history" && initial && location.pathname === "/history" ? 0 : null,
        t1: null, done: false, armed: mode === "home" || (mode === "history" && initial && location.pathname === "/history"),
        ids: expected.ids ?? [], term: expected.term ?? "", total: expected.total ?? 0, checks: 0, observer_ms: 0, kind: "" };
      window.__nfr = s;
      const begin = () => { s.t0 = performance.now(); s.t1 = null; s.done = false; s.armed = true; };
      window.addEventListener("load", () => { if (mode === "home" && location.pathname === "/") { s.t0 = performance.now(); if (s.t1 !== null) s.done = true; } }, { once: true });
      document.addEventListener("submit", event => {
        const form = event.target as HTMLFormElement;
        if ((mode === "assistant" && form.querySelector("#outfit-request")) || (mode === "history" && location.pathname === "/history")) begin();
      }, true);
      document.addEventListener("click", event => {
        const button = (event.target as Element)?.closest("button");
        if (mode === "history" && button?.textContent?.trim() === "Load more chats") begin();
      }, true);
      const tick = () => {
        const start = performance.now(); s.checks++;
        if (s.armed && !s.done && s.t1 === null) {
          let ready = false;
          if (mode === "history") {
            const status = [...document.querySelectorAll('[role="status"]')].find(e => e.textContent?.includes("completed interaction"));
            const ids = [...document.querySelectorAll('a[href^="/history/"]')].map(e => decodeURIComponent(e.getAttribute("href")!.split("/").pop()!));
            const text = status?.textContent ?? "";
            ready = text.startsWith(String(s.total) + " completed interaction") && (s.term ? text.includes(`matching “${s.term}”`) : !text.includes("matching")) && JSON.stringify(ids) === JSON.stringify(s.ids);
            if (ready) s.kind = "history";
          } else {
            const result = document.querySelector('[data-testid="recommendation-result"]');
            if (result) {
              const cards = [...(result.querySelector(".grid")?.children ?? [])];
              ready = cards.length > 0 && cards.every(card => { const image = card.querySelector("img"); return image?.complete && image.naturalWidth > 0; }) && result.getClientRects().length > 0;
              if (ready) s.kind = "recommendation_with_loaded_synthetic_images";
            } else if (mode === "assistant") {
              const alert = [...document.querySelectorAll('[role="alert"]')].find(e => e.id !== "__next-route-announcer__" && e.textContent?.trim());
              ready = Boolean(alert); if (ready) s.kind = "terminal_message";
            }
          }
          if (ready) { s.t1 = performance.now(); s.done = s.t0 !== null; }
        }
        s.observer_ms += performance.now() - start;
        if (!s.done) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { mode, initial, expected });
  };
  const authorize = async (page: Page, token: string) => {
    await page.goto("/auth");
    await page.evaluate(token => { sessionStorage.clear(); sessionStorage.setItem("smart_wardrobe_access_token", token); }, token);
  };
  const clock = async (page: Page, row: Json) => {
    await page.waitForFunction(() => window.__nfr?.done, null, { timeout: 30000 });
    const s = await page.evaluate(() => window.__nfr);
    row.browser_clock = s; row.raw_signed_seconds = (s.t1! - s.t0!) / 1000;
    row.seconds = Math.max(0, row.raw_signed_seconds); row.navigation_to_terminal_seconds = s.t1! / 1000;
  };
  const checkHistory = (body: Json, cell: Json) => {
    const target = expectedHistory[cell.id]; expect(body.total).toBe(target.total);
    expect(body.items.map((r: Json) => r.chat_id)).toEqual(target.http_ids);
    expect(body.items.every((r: Json) => r.chat_id.startsWith("history-owner-"))).toBe(true);
    expect(body.items).toEqual(target.rows.map((r: Json) => ({ ...r, completed_at: r.created_at, read_only: true })));
  };
  const checkRecommendation = (body: Json, cell: Json, home = false) => {
    const value = home ? body.recommendation : body;
    expect(value.user_id).toBe(cell.owner); expect(value.items.length).toBeGreaterThan(0);
    const roles = value.items.map((i: Json) => i.garment_role).join(",");
    expect(["upper,lower", "upper,lower,outerwear", "one_piece", "one_piece,outerwear"]).toContain(roles);
    const roleMap: Record<string, string> = { vest: "upper", sling: "upper", short_sleeve_top: "upper", long_sleeve_top: "upper", shorts: "lower", trousers: "lower", skirt: "lower", vest_dress: "one_piece", sling_dress: "one_piece", short_sleeve_dress: "one_piece", long_sleeve_dress: "one_piece", short_sleeve_outwear: "outerwear", long_sleeve_outwear: "outerwear" };
    expect(new Set(value.items.map((i: Json) => i.garment_id)).size).toBe(value.items.length);
    for (const [index, item] of value.items.entries()) {
      const garment = mix.mixes[cell.workload].find((g: Json) => g.id === item.garment_id);
      expect(garment).toBeTruthy(); expect(item.garment_role).toBe(roleMap[garment.category]); expect(item.item_order).toBe(index + 1); expect(item.currently_eligible).toBe(true);
      if (cell.request === "allow") for (const tag of ["rec:v1:occasion:campus:allow", "rec:v1:formality:casual:allow"]) expect(garment.custom_tags).toContain(tag);
    }
    if (!home) {
      const target = scores[cell.workload + "-" + cell.request];
      expect(value.items.map((i: Json) => [i.garment_id, i.garment_role, i.item_order])).toEqual(target.items);
      expect(value.score_metadata).toEqual(target.score);
      expect(value.score_metadata.weights).toEqual([{ numerator: 3, denominator: 5 }, { numerator: 1, denominator: 5 }, { numerator: 1, denominator: 5 }]);
      expect(value.provenance.scoring_profile).toBe("experimental_compatibility_decision_v1");
      expect(value.provenance.request_evaluator).toBe("SuitabilityRequestEvaluator");
      expect(value.provenance.assistant_execution_selection.engine).toBe("compact_exhaustive");
      expect(value.provenance.scored_count).toBe(cell.count);
      expect(value.provenance.mandatory_evaluation.conditions.every((r: Json) => r.state === "Pass")).toBe(true);
    } else expect(value.chat_id).toBeNull();
  };
  for (const cell of plan.history_cells) {
    phase = "NFR03:" + cell.id; save(); const auth = await login(cell.owner);
    const context = await browser.newContext({ viewport: { width: 1280, height: 960 } }); const page = await context.newPage();
    await install(page, "history", cell.id === "empty_first", { ids: expectedHistory[cell.id].browser_ids, term: cell.query, total: expectedHistory[cell.id].total });
    for (let trial = 0; trial < 5; trial++) {
      const row: Json = { nfr: "NFR03", cell: cell.id, layer: "browser", trial, principal: true, deadline: 2, error: null };
      try {
        await authorize(page, auth.token);
        let pending;
        if (cell.id === "empty_first") {
          pending = page.waitForResponse(r => new URL(r.url()).pathname === "/api/v1/chats" && r.request().method() === "GET"); await page.goto("/history");
        } else {
          await page.goto("/history"); await expect(page.locator('a[href^="/history/"]')).toHaveCount(50);
          if (cell.query) {
            if (cell.page === 2) {
              await page.getByLabel("Search original requests").fill(cell.query); await page.getByRole("button", { name: "Search history", exact: true }).click();
              await expect(page.getByText(`${expectedHistory[cell.id].total} completed interactions matching “${cell.query}”`, { exact: true })).toBeVisible();
            } else {
              await page.getByLabel("Search original requests").fill(cell.query);
            }
          }
          await page.evaluate(target => { const s = window.__nfr; s.armed = false; s.done = false; s.t1 = null; s.ids = target.ids; s.term = target.term; s.total = target.total; }, { ids: expectedHistory[cell.id].browser_ids, term: cell.query, total: expectedHistory[cell.id].total });
          pending = page.waitForResponse(r => new URL(r.url()).pathname === "/api/v1/chats" && r.request().method() === "GET");
          await page.getByRole("button", { name: cell.page === 2 ? "Load more chats" : "Search history", exact: true }).click();
        }
        const response = await pending; row.http = response.status(); row.result = await response.json();
        await clock(page, row); expect(row.http).toBe(200); checkHistory(row.result, cell);
      } catch (e) { row.error = String(e); }
      rows.push(row); save(); console.log(JSON.stringify({ ...row, result: undefined }));
    }
    const row: Json = { nfr: "NFR03", cell: cell.id, layer: "http", trial: 0, principal: true, deadline: 2, error: null };
    try {
      let cursor: string | undefined;
      if (cell.page === 2) cursor = (await (await request.get(api + "/chats", { headers: auth.headers, params: { search: cell.query, limit: 50 } })).json()).next_cursor;
      const start = performance.now(); const response = await request.get(api + "/chats", { headers: auth.headers, params: { search: cell.query, limit: 50, ...(cursor ? { cursor } : {}) } });
      row.result = await response.json(); row.seconds = (performance.now() - start) / 1000; row.http = response.status(); expect(row.http).toBe(200); checkHistory(row.result, cell);
    } catch (e) { row.error = String(e); }
    rows.push(row); save(); await context.close();
  }
  for (const [nfr, cells] of [["NFR01", plan.homepage_cells], ["NFR02", plan.assistant_cells]] as const) for (const cell of cells) {
    phase = nfr + ":" + cell.id; save(); const home = nfr === "NFR01"; const auth = await login(cell.owner);
    const headers = auth.headers;
    const context = await browser.newContext({ viewport: { width: 1280, height: 960 } }); const page = await context.newPage();
    await install(page, home ? "home" : "assistant", false, {});
    const quotaBefore = await (await request.get(api + "/wardrobe/quota", { headers })).json();
    for (const layer of ["browser", "http"]) for (let trial = 0; trial < (layer === "browser" ? 5 : 1); trial++) {
      const row: Json = { nfr, cell: cell.id, owner: cell.owner, layer, trial, principal: home || cell.principal, deadline: home ? 3 : 5, error: null };
      const chats = async () => (await (await request.get(api + "/chats", { headers, params: { limit: 1 } })).json()).total;
      const before = await chats();
      try {
        if (layer === "browser") {
          await authorize(page, auth.token);
          if (!home) { await page.goto("/assistant"); await page.getByLabel("What would you like to wear?").fill(cell.text); }
          const pending = page.waitForResponse(r => r.request().method() === "POST" && (home ? r.url().endsWith("/recommendations/homepage") : r.url().includes("/recommendations?pipeline=integrated")), { timeout: 30000 });
          if (home) await page.goto("/"); else await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
          const response = await pending; row.http = response.status(); row.key = response.request().postDataJSON().submission_key; row.result = await response.json();
          await clock(page, row);
          if (!home && cell.outcome !== "Selected") await expect(page.locator('[role="alert"]').filter({ hasText: messages[cell.outcome] })).toBeVisible();
        } else {
          row.key = crypto.randomUUID(); const start = performance.now();
          const response = await request.post(api + (home ? "/recommendations/homepage" : "/recommendations?pipeline=integrated"), { headers, data: { submission_key: row.key, ...(!home ? { request_text: cell.text } : {}) }, timeout: 30000 });
          row.result = await response.json(); row.seconds = (performance.now() - start) / 1000; row.http = response.status();
        }
        row.outcome = row.result.outcome ?? row.result.status;
        expect(row.outcome).toBe(home ? "Selected" : cell.outcome);
        expect(row.http).toBe(home || cell.outcome === "Selected" ? 201 : ["UnsupportedRequest", "PolicyUnavailable"].includes(cell.outcome) ? 422 : 200);
        if (home || cell.outcome === "Selected") checkRecommendation(row.result, cell, home);
        else { expect(row.result.id).toBeUndefined(); expect(row.result.chat_id).toBeUndefined(); }
        row.chat_count_before = before; row.chat_count_after = await chats();
        expect(row.chat_count_after).toBe(before + (!home && cell.outcome === "Selected" ? 1 : 0));
      } catch (e) { row.error = String(e); }
      rows.push(row); save(); console.log(JSON.stringify({ nfr, cell: row.cell, layer, trial, seconds: row.seconds, error: row.error }));
    }
    const quotaAfter = await (await request.get(api + "/wardrobe/quota", { headers })).json();
    invariants.push({ nfr, cell: cell.id, quota_before: quotaBefore, quota_after: quotaAfter }); save();
    expect(quotaAfter).toEqual(quotaBefore); await context.close();
  }
  phase = "complete"; save(); expect(rows.length).toBe(126);
  expect(rows.filter(r => r.error)).toEqual([]);
});
