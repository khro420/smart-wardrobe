// J12 matched regression only: frozen J10 rows, eight fresh-key calls, no selectors.
import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

function canonical(value: unknown): string {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value !== null && typeof value === "object") {
    const row = value as Record<string, unknown>;
    return "{" + Object.keys(row).sort().map(key => JSON.stringify(key) + ":" + canonical(row[key])).join(",") + "}";
  }
  return JSON.stringify(value);
}
const sha = (value: string | Buffer) => createHash("sha256").update(value).digest("hex");
type RecordRow = Record<string, unknown>;

test("J12 frozen release regression through HTTP and normal browser submission", async ({ page, request }) => {
  test.skip(process.env.SMART_WARDROBE_RELEASE_PERFORMANCE !== "true", "Explicit timing opt-in required");
  const api = "http://127.0.0.1:3101";
  const folder = resolve("../storage/verification/phase5f2e3j12");
  const label = process.env.SMART_WARDROBE_RELEASE_LABEL ?? "initial";
  if (!/^[a-z0-9-]+$/.test(label)) throw new Error("Invalid label");
  const output = resolve(folder, "performance-" + label + ".json");
  if (existsSync(output)) throw new Error("Refusing to overwrite retained trial evidence");
  const frozen = JSON.parse(readFileSync(resolve("../storage/verification/phase5f2e3j10/frozen-manifest.json"), "utf8"));
  const bytes = readFileSync(resolve("../storage/verification/phase5f2e3j10/expected-results.json"));
  expect(sha(bytes)).toBe(frozen.expected_sha256);
  const expected = JSON.parse(bytes.toString()) as { workload: string; profile: string; suitability: boolean; fingerprint: string; counts: { scored: number } }[];
  const runtime = await (await request.get(api + "/_test/release")).json();
  expect(runtime.plan_sha256).toBe(frozen.fixture_sha256);
  expect(runtime.engine).toBe("compact_exhaustive");
  expect(runtime.profile).toBe("experimental_compatibility_decision_v1");
  expect(runtime.evaluator).toBe("SuitabilityRequestEvaluator");
  const controls = runtime.plan.controls;
  const records: RecordRow[] = [], preflight: RecordRow[] = [];
  let state = "preflight", consecutive = 0;
  const save = () => writeFileSync(output, JSON.stringify({ label, state, runtime, controls, preflight, records,
    schedule: "balanced-100 then maximum-100; each 1HTTP followed by3browser; first call included; no warm-up or selection override",
    boundary: runtime.plan.browser_boundary, formal_nfr_acceptance: false }, null, 2));
  save(); await page.waitForTimeout(controls.settle_ms);
  const preflightStart = performance.now();
  while (consecutive < controls.consecutive && performance.now() - preflightStart < controls.max_preflight_ms) {
    const sample = await (await request.get(api + "/_test/resources")).json(); preflight.push(sample);
    consecutive = sample.available && Number.isFinite(sample.system?.cpu_load_percent) && sample.system.cpu_load_percent <= controls.cpu_max && sample.system.free_physical_kib >= controls.ram_min_kib ? consecutive + 1 : 0;
    save(); if (consecutive < controls.consecutive) await page.waitForTimeout(1000);
  }
  if (consecutive < controls.consecutive) { state = "resource_blocked"; save(); throw new Error("Resource gate blocked; zero timed submissions"); }
  state = "running"; save();
  for (const workload of ["balanced-100", "maximum-100"]) {
    const target = expected.find(row => row.workload === workload && row.suitability && row.profile === runtime.profile)!;
    expect(target).toBeTruthy();
    const login = await request.post(api + "/api/v1/account/login", { data: { email: `j10-${workload}@example.test`, password: "Decision-test-password-123" } });
    expect(login.status()).toBe(200); const token = (await login.json()).access_token;
    const headers = { Authorization: `Bearer ${token}` };
    const before = await (await request.get(api + "/api/v1/wardrobe/quota", { headers })).json(); expect(before.used).toBe(100);
    for (const layer of ["http", "browser"]) for (let trial = 0; trial < (layer === "http" ? 1 : 3); trial++) {
      let key: string = crypto.randomUUID(); const row: RecordRow = { workload, layer, trial, key, error: null };
      row.resources_before = await (await request.get(api + "/_test/resources")).json();
      let started = performance.now();
      try {
        if (layer === "http") {
          const response = await request.post(api + "/api/v1/recommendations?pipeline=integrated", { headers,
            data: { request_text: runtime.plan.requests.suitability, submission_key: key }, timeout: 240000 });
          row.seconds = (performance.now() - started) / 1000; row.http_status = response.status(); row.outcome = (await response.json()).outcome;
        } else {
          await page.goto("/auth"); await page.evaluate(t => { sessionStorage.clear(); sessionStorage.setItem("smart_wardrobe_access_token", t); }, token);
          await page.goto("/assistant"); await page.getByLabel("What would you like to wear?").fill(runtime.plan.requests.suitability);
          const pending = page.waitForResponse(r => r.url().includes("pipeline=integrated") && r.request().method() === "POST", { timeout: 240000 });
          started = performance.now(); await page.getByRole("button", { name: "Suggest an outfit", exact: true }).click();
          const response = await pending; key = response.request().postDataJSON().submission_key; row.key = key; row.http_status = response.status();
          row.outcome = (await response.json()).outcome;
          await expect(page.getByTestId("recommendation-result")).toBeVisible({ timeout: 240000 }); row.seconds = (performance.now() - started) / 1000;
        }
        expect(row.http_status).toBe(201); expect(row.outcome).toBe("Selected");
      } catch (error) { row.error = String(error); row.seconds = (performance.now() - started) / 1000; }
      records.push(row); save();
      const drain = performance.now(); let job;
      do { job = await (await request.get(api + "/_test/job/" + key)).json(); if (job.done) break; await page.waitForTimeout(1000); } while (performance.now() - drain < 240000);
      row.job = job; save();
      if (!job.done) { state = "backend_unsettled"; save(); throw new Error("Previous backend call unsettled; no more timings"); }
      try {
        expect(job.provenance.scored_count).toBe(target.counts.scored);
        expect(job.provenance.scoring_profile).toBe(runtime.profile);
        expect(job.provenance.request_evaluator).toBe(runtime.evaluator);
        row.fingerprint = sha(canonical({ items: job.items, score: job.score, provenance: job.provenance }));
        expect(row.fingerprint).toBe(target.fingerprint);
        expect(job.cache.pairs).toBeLessThanOrEqual(19900);
        for (const memo of job.cache.aggregations) expect(memo.currsize).toBeLessThanOrEqual(256);
      } catch (error) { row.error = [row.error, String(error)].filter(Boolean).join("\n"); }
      row.resources_after = await (await request.get(api + "/_test/resources")).json(); save();
      console.log(JSON.stringify({ workload, layer, trial, seconds: row.seconds, error: row.error }));
    }
    const after = await (await request.get(api + "/api/v1/wardrobe/quota", { headers })).json(); expect(after).toEqual(before);
  }
  state = "complete"; save(); expect(records.filter(row => row.error)).toEqual([]);
  // Deadline failures stay in the ledger; collector completion is not NFR acceptance.
});
