# Phase 5F-2E-3J-10: 100-garment maximum-capacity feasibility verification

2026-10-23, Asia/Kuala_Lumpur. **100 FEASIBLE FOR FORMAL ACCEPTANCE PLANNING.**
The intended compact/experimental+suitability configuration completed every
required observation correctly below5s, including the maximum structural-count
distribution. Its worst browser response was2.346690s, leaving2.653310s observed
headroom. This supports100 as a **proposed** product maximum to take into formal
planning; it does not approve/enforce a quota or universally accept NFR-02.
**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** J-9 is owner-closed PASS WITH LIMITATIONS.

## Frozen populations and independent maximum

`backend/tests/fixtures/capacity_100.v1.json` freezes exact rows, J-9/J-7 source IDs,
seed20261023, evidence histograms, requests/preferences, policy/config references,
expected counts and the measurement schedule. SHA256:
`54a7982de411102d88149e958d875155ce67b489fd881b4169df4483470a9776`.
Expected exact identities and tool/policy/source hashes were frozen before timing
in `expected-results.json` and `frozen-manifest.json`.

| Population | Tops / bottoms / dresses / outerwear | Actual pair / trio / dress / dress+outerwear enumeration | Total |
|---|---|---|---:|
| Balanced100 | 40 / 40 / 10 / 10 | 1,600 / 16,000 / 10 / 100 | 17,710 |
| Maximum100 | 34 / 34 / 0 / 32 | 1,156 / 36,992 / 0 / 0 | 38,148 |

**Independent derivation:** disjoint role counts T,B,D,O and the unchanged four
structures give TB+TBO+D+DO=(TB+D)(O+1). An application-independent integer
calculation checked **all176,851 nonnegative allocations** with T+B+D+O=100.
The global maximum is **38,148**, attained at (34,34,0,32), (33,34,0,33),
(34,33,0,33). The expression is nondecreasing in each count, so it also bounds
populations of at most100. This is a structural bound, not a latency guarantee.
Actual complete `RecommendationEngine` enumeration over strict owned, confirmed,
available query snapshots independently reproduced both table counts. The current
structural-policy compositions are asserted unchanged; mandatory constraints can
only remove candidates. No new structure, role overlap, category quota or pruning.

Balanced subcategories:10 each top;14shorts/13trousers/13skirt;
3short/3long/2vest/2sling dresses;5 each outwear. Maximum:9/9/8/8 tops,
12shorts/11trousers/11skirt,16 each outwear, no dresses. Existing spellings retained.
The smaller public-oracle cases and focused regressions retain all four structures.

**Synthetic coverage, not empirical representativeness:** seeded selection/cycling
from J-9 frozen rows uses the same supported names, exact anchors, non-anchor hex,
missing/empty styles, ordinary tags and patterns. Balanced colours:73named,
13anchors,8non-anchor,6missing; styles:62single/27multiple/6missing/5empty.
Maximum colours:66named/15anchors/15non-anchor/4missing;
styles:67single/13multiple/12missing/8empty. Unknown evidence stays unknown; no
approximate hex, model prediction, confidence or human fashion label is invented.

On request:`Suggest a casual outfit for campus.` Every member, including
outerwear, has explicit synthetic owner campus-Allow and casual-Allow tags.
The real8-occasion/2-formality evaluator, all-member mandatory checks and
independent verifier are used. Off request:`Suggest an outfit`. Three supported
preferences remain identical per comparison:blue colour, vintage style, top group,
importance1 each. Full frozen rows retain exact tag/value/identifier provenance.

## Complete measurements and deadline evidence

**20 predeclared fresh submissions:** per population, main experimental+suitability
1authenticated HTTP+5browser calls; experimental/off and deferred/on diagnostics
each1HTTP+1browser. Main HTTP is the first actual recommendation in each population;
no ranking warm-up or slow-sample replacement. Diagnostic browser median/max below
are single observations, not distributions. Offline setup is a separate disposable
process and cannot warm transport recommendation caches.

| Population | Profile | Suitability | HTTP seconds | Browser seconds, all in order | Browser median / max | Minimum headroom to 5s |
|---|---|---|---:|---|---|---:|
| Balanced | Experimental | On | 0.914751 | 1.188316, 1.152132, 1.011963, 1.024992, 1.077888 | 1.077888 / 1.188316 | 3.811684s |
| Balanced | Experimental | Off | 0.728459 | 0.988457 | 0.988457 / 0.988457 | 4.011543s |
| Balanced | Deferred | On | 0.579400 | 0.764445 | 0.764445 / 0.764445 | 4.235555s |
| Maximum | Experimental | On | 1.825851 | 1.931571, 2.346690, 1.922517, 2.080630, 1.978091 | 1.978091 / 2.346690 | 2.653310s |
| Maximum | Experimental | Off | 1.398785 | 1.475858 | 1.475858 / 1.475858 | 3.524142s |
| Maximum | Deferred | On | 1.253773 | 1.287803 | 1.287803 / 1.287803 | 3.712197s |

**20/20 Selected,HTTP201;0errors,0timeouts,0above5s,0unfinished jobs.** All12 required
main observations pass individually, rather than merely their medians. All first
calls and resource disturbances remain in `performance-initial.json`; no timed
retry occurred. The Playwright collector passed1test in2.7m, with2.4m test duration.
Every call exhausted17,710 or38,148 structures; all were mandatory-valid and
scored under the frozen all-Allow/generic requests. Total actual scored/examined
ledger across20 calls:**558,580**. Score-certificate hits+misses equal the scored
count on every call; no candidate or mandatory evaluation was sampled/pruned.

Separate actual service/process-CPU boundaries (same observation order):

| Population | Profile | Suitability | Service seconds: HTTP then browser calls | Process CPU seconds, same order |
|---|---|---|---|---|
| Balanced | Experimental | On | 0.906277, 1.016930, 1.051756, 0.927191, 0.928009, 0.974946 | 0.906250, 1.000000, 1.015625, 0.921875, 0.921875, 0.953125 |
| Balanced | Experimental | Off | 0.722594, 0.899288 | 0.703125, 0.875000 |
| Balanced | Deferred | On | 0.573236, 0.683089 | 0.578125, 0.640625 |
| Maximum | Experimental | On | 1.818815, 1.866923, 2.209351, 1.826108, 1.989641, 1.884891 | 1.765625, 1.812500, 1.968750, 1.781250, 1.906250, 1.781250 |
| Maximum | Experimental | Off | 1.393247, 1.392571 | 1.218750, 1.296875 |
| Maximum | Deferred | On | 1.247549, 1.223198 | 1.203125, 1.203125 |

Browser T0 is submit click,T1 visible complete correct recommendation component,
matching J-9. Login/page preparation are outside timing. Authorised synthetic
protected thumbnails exist, but completed image loading is not required at T1.
Direct HTTP includes response decoding. Raw backend-request/service/HTTP/browser
timings are separately retained. Real image loading, remote networks and deployed
GPU/database performance are not certified by this boundary.

## Exact correctness and bounded caches

| Population | Profile | Certificate hits / misses / evictions | Pair hits / misses / evictions | Final pair size |
|---|---|---|---|---:|
| Balanced | Experimental | 15,288 / 2,422 / 2,166 | 47,200 / 2,500 / 0 | 2,500 |
| Balanced | Deferred | 17,636 / 74 / 0 | 0 / 0 / 0 | 0 |
| Maximum | Experimental | 35,614 / 2,534 / 2,278 | 108,800 / 3,332 / 0 | 3,332 |
| Maximum | Deferred | 38,084 / 64 / 0 | 0 / 0 / 0 | 0 |

Experimental/off has exactly the same cache ledger as experimental/on for each
population; all repeated main ledgers match. Pair bound19,900; each aggregation/
certificate LRU bound256. Evictions above are misses minus final certificate size
for an initially empty, uncleared session LRU. Pair evictions are0. No capacity,
numeric algorithm or cache policy changed. Candidate facts/mandatory/independent
checks still run before numeric certificate reuse; hits do not skip enumeration.

All20 exact score/winner/provenance identities match the frozen expectation.
Full Fraction components, decision bounds/bases, raw unknown evidence, policy and
preference snapshots are in every raw job and `expected-results.json`. The table
uses ID suffixes (`balanced-100-NNNN` / `maximum-100-NNNN`), ordered upper/lower/
optional outerwear, and hash prefixes for scanning; full SHA256 values are retained.

| Population | Profile | Suitability | Ordered selected IDs (suffixes) | Exact total | Full identity SHA256 prefix |
|---|---|---|---|---:|---|
| Balanced | Experimental | On | 0018, 0055 | 1/1 | `b1630fc4a2354838` |
| Balanced | Experimental | Off | 0018, 0055 | 2/5 | `7ff08d38f194f163` |
| Balanced | Deferred | On | 0003, 0040, 0097 | 1/1 | `1472c112d5cd5d7b` |
| Maximum | Experimental | On | 0023, 0036, 0099 | 19/20 | `5b759500b5db19a7` |
| Maximum | Experimental | Off | 0023, 0036, 0099 | 7/20 | `8bb8cded628d3cef` |
| Maximum | Deferred | On | 0001, 0036, 0091 | 1/1 | `17253cc4f4e8cf88` |

These are arithmetic/persistence correctness checks, not independent fashion
ratings. The reduced-population public oracle checks every candidate against
independent public evaluators/scorers. Full-population selected scores additionally
pass production public reconstruction and independent eligibility verification.
There are20distinct keys/recommendations/chats,10recommendations and10completed
chats per owner. Focused regressions separately cover ownership/availability,
all-member Allow/Deny/Unknown/malformed/conflict, atomic rollback/idempotent replay,
immutable historical read-only behaviour and bounded-session optimisations.

## Resources and comparison with J-9

After regression work ended, host CPU samples19/6/17%,free RAM7.7GiB; largest
sampled competing process was Code0.85% of total CPU. Automated preflight retained
13samples,CPU15-43%,RAM7.19-7.23GiB,then qualified at **19/15/15%**. Existing
three-sample CPU<=20%/RAM>=4GiB gate,10s settle and120s wait were unchanged.
All40 before/after timed snapshots show CPU6-68%,RAM6.73-7.21GiB. No failures or
disturbed observations were excluded. These are preflight-qualified sequential
samples, **not continuous process isolation** or matched cross-phase conditions.
Post-run CPU7/8/12%; a separate process delta found OneDrive.Sync.Service5.19%,
Code2.53%. No individual delay is attributed to a proven background cause.
One collector attempt, no blocked attempt or replacement run; all preflight
settling observations are retained. No user processes were terminated.

One Uvicorn0.54.0 process,production Next16.4.2,unchanged3201/3200 loopback proxy,
real JWT and disposable SQLite retain J-9's configuration. Same J-6/J-9 build
`Q3jwGpqXBc9FUVrN9gGr8`; no build needed. No tests/builds/profilers overlapped timing.
Collector waits240s and existing proxy timeouts are unchanged. Server selectors
exist only in the isolated fixture; production defaults and APIs are untouched.

| Population | Candidates | Experimental+suitability HTTP | Browser median / maximum | Above5s / measurements |
|---|---:|---:|---|---|
| J10 balanced100 | 17,710 | 0.914751s | 1.077888 / 1.188316s | 0 / 6 |
| J10 maximum100 | 38,148 | 1.825851s | 1.978091 / 2.346690s | 0 / 6 |
| J9 balanced150 | 57,840 | 2.809353s | 2.927672 / 3.076685s | 0 / 6 |
| J9 heavy150 | 127,500 | 5.675732s | 5.813074 / 6.013035s | 6 / 6 |

Balanced100 has30.62% of J-9 balanced150's candidates; maximum100 has29.92% of
J-9 heavy150's candidates. Cache comparison (experimental):J-9 balanced hits/misses/
evictions51,437/6,403/6,147;heavy121,537/5,963/5,707. Its pair misses5,625/7,500,
with no pair evictions. J-10 ledgers are above; reuse depends on exact evidence
keys, not size alone. These populations, compositions and resource conditions
differ; lower J-10 latency is **not an isolated causal speedup claim**. J-9's seven
slow trials, including all6experimental+suitability heavy measurements, remain
unchanged. Its 150-garment maximum remains unapproved.

## Focused regressions, integrity and acceptance limits

- **425focused backend tests passed,58.31s**:new independent-maximum/actual-
  enumeration/public-oracle checks plus certificate reuse,J-8 request-detail,
  suitability integration,persistence/replay and historical-action regressions.
- TypeScript and scoped new collector/config ESLint:exit0. Actual production
  browser verification:20correct submissions; no unnecessary J-9 four-way/broad
  suite repeated. No new production defect warranted broader regressions. The
  known ai-services assertion and separate CV/torch/model environment are not
  newly certified or weakened.
- Source integrity:750pre-existing files checked;749unchanged,only ignored
  `frontend/tsconfig.tsbuildinfo` regenerated. All20frozen-input hashes/build
  manifests match;239retained J-6/J-7/J-8/J-9 evidence files unchanged. An explicit
  comparison finds all215production app/frontend/package/config files equal to
  J-9. Exact20identities/cache ledgers/persistence counts match. `integrity.json`
  and `production-comparison-to-j9.json` retain evidence; `git diff --check` is
  recorded in `diff-check-final.log`.

Only new verification files are added:capacity fixture,independent arithmetic
helper,disposable server,focused backend test,Playwright collector/config,this
report and phase evidence/helpers. Commands, hashes and all raw records are under
`storage/verification/phase5f2e3j10/`. No production source,upload/confirmation,
batch restriction,schema,frontend upload validation,NLP,CV/VTON,legacy route,
weights,caches,mandatory evaluation,persistence or historical record changed.
The accepted J-6 certificate/J-8 exact request-detail corrections remain present.
Production stays **compact_exhaustive / compatibility_deferred**, suitability
default-off; isolated experimental remains exact60/20/20 with independent checks.

**Recommendation:100 FEASIBLE FOR FORMAL ACCEPTANCE PLANNING**, including the
maximum structural-count population under the four current roles/structures.
The worst required response leaves2.653310s measured margin; the decision uses
every required observation and exact correctness, not a passing median alone.
It supports proposing100 for owner/supervisor review, not immediate quota adoption.

**NFR-02 remains formally unaccepted.** One synthetic seed,two requests,three
preferences,five browser trials/one HTTP per main population and one sequential
local process do not prove all evidence/request distributions,all five-field
requests,concurrency,history growth,real media,remote deployment or a universal
five-second guarantee. No-result/unsupported formal timing,final deployment/DB,
image boundary,release configuration,baseline and acceptance statistic still need
their separate approval. Structural maximum does not bound all per-candidate
work or environmental variation. Prior150/200slow/failing results are preserved.

No total wardrobe quota is enforced. The100-ID review/confirmation batch limit
remains unrelated to total per-user capacity. Any future enforced maximum needs
separate owner/teammate approval,defined active/archive counts,transaction-bound
whole-batch/concurrent-confirm protection,atomic rollback and clear frontend/API
feedback. No scoring-default/global suitability activation,quota or J-11 begins.
**J-10 is complete for owner review; wait for review before proceeding.**
