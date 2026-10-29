// Exercise the actual exported helper in a browser-like sandbox, without a server.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const source = fs.readFileSync(new URL("../../lib/api.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const calls = [];
let enabled = true;
const context = {
  exports: {}, process: { env: {} }, Headers, URLSearchParams,
  window: { sessionStorage: { getItem: () => "synthetic-token" } },
  fetch: async (url, init) => {
    calls.push({ url, method: init?.method ?? "GET", body: init?.body });
    return { ok: true, status: 200, json: async () => url.endsWith("/capabilities") ? { assistant_enabled: enabled } : { outcome: "Selected" } };
  },
};
vm.runInNewContext(compiled, context);
const api = context.exports;
await assert.rejects(api.createRecommendation("Suggest an outfit"), e => e.status === 422 && e.outcome === "InvalidInput" && e.message.includes("submission key"));
assert.equal(calls.length, 0);
await api.createRecommendation("Suggest an outfit", "durable-key");
assert.equal(calls.length, 2);
assert.equal(calls[1].url, "/api/v1/recommendations?pipeline=integrated");
assert.equal(JSON.parse(calls[1].body).submission_key, "durable-key");
enabled = false; calls.length = 0;
await assert.rejects(api.createRecommendation("Suggest an outfit", "disabled-key"), e => e.status === 404 && e.outcome === "IntegrationDisabled");
assert.equal(calls.length, 1);
assert.ok(calls[0].url.endsWith("/capabilities"));
console.log(JSON.stringify({ unkeyed_network_calls: 0, keyed_explicit_integrated: true, disabled_generation_posts: 0, result: "PASS" }));
