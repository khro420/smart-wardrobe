# Phase 5F-2E-3J-20: targeted recommendation layout, zoom and browser correction

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-19 is owner-closed PASS WITH LIMITATIONS. The approved one-file correction fixes
the demonstrated valid100-character garment-name overflow in the tested result
and history layouts. All14 Chrome/Edge production-browser cases and the scoped
actual Firefox collector pass. **NFR-16 and NFR-18 become Verified for the stated
tested local scope; NFR-19 remains Unverified.** No deployment or whole-FYP
acceptance is implied.

The155 original requirements now total **142 Verified,3 Partial,10 Unverified,
0 Blocked**, from J-19's140/5/10/0. The
[complete JSON matrix](../storage/verification/phase5f2e3j20/requirement-matrix.json)
and [CSV](../storage/verification/phase5f2e3j20/requirement-matrix.csv) preserve
original sentences/pages/priorities, J-19/current status, evidence, limits and
remaining owners/actions. Only NFR-16/18 advance. Whole-FYP readiness remains
NOT READY; **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED**.

## Approval and exact production change

J-20 section1 explicitly required R/shared-file approval before editing.
Preparation initially stopped at that boundary; its blocked report is preserved
as `preparation-report.md`, with its index and raw attempts unchanged. The owner
then answered **“Approve this one-file frontend scope”**. The exact response,
file and exclusions are recorded in `ownership-approval.json`. The pending
disposition is superseded by this authorised completion, not erased.

**Only `frontend/components/RecommendationResult.tsx` changes in production.**
Its article, grid and garment card receive min-width:0 so they can shrink to the
available width; its name paragraph receives overflow-wrap:anywhere so an
unbroken name can wrap. The full100-character string, image alt text, category/
role/order labels, score explanation, buttons and normal-name hierarchy remain.
No API response, stored name or truncation rule changes. Existing body overflow
hiding is unchanged and is not the fix: measured content bounds now fit.

OutfitAssistant, CompletedChatView and HomepageRecommendation reuse this component
and are covered. No shared/global CSS is needed. No backend source, source guard,
NLP vocabulary, score/suitability policy, candidate enumeration, preference
persistence, auth/logout, routing, quota, model, provider/schema or global default
changes. No backend suite is warranted by a styling-only frontend boundary;
read-only hashes establish all backend sources and earlier guards remain exact.

`recommendation_layout_sources.v1.json` records the one approved transition:

| Production file | Captured before SHA256 | Approved after SHA256 |
|---|---|---|
|frontend/components/RecommendationResult.tsx|`3003885d1fa37ec4a9caea9d539305de98417e073770f638b3524835cacc0607`|`df14339413fed1cc95eef4909952d515a2b176c8dae74cdff5e4c2be41585ed8`|

The phase patch/original identify only J-20 within the earlier uncommitted tree.
An exact expected-text check and comparison with className values masked confirm
that this component's business content/logic is unchanged. No earlier manifest
or reference hash was repinned; this component is outside the backend guard's
listed frontend replacements, so that guard needs no modification.

## Before/after reproduction and actual services

The unchanged J-19 failures remain historical evidence. New phase-specific test
copies retain the exact fixture: `J19` plus97 `x` characters, accepted by the
ordinary garment PATCH. Before-change runs use the existing J-18 build
`o2aRZKY_67KAiMV7I1qqh`; corrected runs use the new separate production build
**`wyOjW-hOqqSjE-aJgofVa`** under
`frontend/.next-integration-run/recommendation-layout-production`. Both prior
builds and all earlier phase evidence are retained.

Ordinary `app.main:app`, Uvicorn lifespan/composition, real register/login and
production Next/same-origin proxy3100->3101 serve the tests. No selector endpoint,
`/_test` business route or alternative ranking/service is introduced. Existing
test lifecycle wrappers only request shutdown. Each supervisor uses a new
disposable SQLite file, generated non-default child secret, development identity
off, synthetic normally reviewed/confirmed uploads, AI development processing
and VTOFF/VTON off. No private account/photo/database or real inference is used.

Explicit child flags select compact_exhaustive, experimental_compatibility_decision_v1,
suitability=true, Assistant=true and Homepage=true. Weights remain60/20/20; all
mandatory-valid candidates are evaluated, exact scores/history/replay are retained,
Homepage remains random/no-chat and quota stays100. These are disposable process
settings, not host/User/Machine defaults or installed-service activation.

| Actual product | Before corrected test fixture, old production source | Approved corrected source |
|---|---|---|
|Chrome|2 layout/zoom tests fail;9 failed layouts among83 observations; native200% long-name result/history overflow|7/7 cases pass in50.3s;83/83 layouts fit; long-name native200% states/actions pass.|
|Edge|Same2 failures and9/83 overflowing layouts; native200% overflow|7/7 cases pass in45.4s;83/83 layouts fit; long-name native200% states/actions pass.|
|Firefox|J-19 normal/keyboard/zoom evidence retained; no new pre-fix maximum-name run claimed|Actual installed-product collector exit0; normal flows,31 viewport observations, long names, keyboard, native200% and save/source actions pass within actual width limits.|

These are functional test durations, not NFR latency measurements. No J-16
performance matrix, new capacity population or timing acceptance was run.

## NFR-16: viewport/component verification

Chrome and Edge each collect83 layouts. Ordinary Assistant draft/result and
history list/detail use17 representative widths:360,375,390,412,480,639,640,641,
767,768,769,1023,1024,1025,1280,1440,1920. The maximum-length Assistant result,
historical result and Homepage card each use360,390,768,1280,1920. This samples
the requested range and breakpoint boundaries; it does not claim every integer
width or every possible content population.

Before correction, each of those three long-name states overflows at360/390/768,
with approximately862/862/857px content;1280/1920 fit. After correction, all
document/text/control bounds fit at every observed width. The full name is equal
in response, DOM and history snapshot. Role/category labels and the score
explanation remain; historical score metadata compares equal and Homepage adds
no chat. Component behavior is checked through the actual rendered production
component, rather than a class-name-only test or synthetic replacement page.

Firefox has21 ordinary draft/result/history observations and10 maximum-name
result/history observations. Its actual desktop runner clamps requested360/390
to500px: observed widths are500,640,768,1024,1280,1920. All observed layouts fit.
**Firefox sub500px coverage is not claimed**, nor is its long-name Homepage sweep.
The360–1920 result is established in actual Chrome/Edge; broader current-product
coverage remains the separate NFR-19 limitation.

Screenshots, DOM range bounds and complete JSON remain under `runs/verified/`.
[Corrected360px result](../storage/verification/phase5f2e3j20/runs/verified/chrome/maximum-name-result-360.png)
shows the whole name wrapped, labels/explanation and usable actions.
The earlier before-change failures/screenshots/traces are retained alongside
their exact test/config snapshots. **NFR-16: Verified for this supported local
product/content scope**, not a universal arbitrary-content claim.

## NFR-18: native200% and keyboard/actions

The checks use actual browser-native zoom2, not CSS zoom, DPR-only simulation or
pinch scale. Chrome/Edge use their own settings API in isolated profiles;
Firefox uses its native zoom manager through WebDriver. Physical browser
dimensions remain1440x1000. DPR doubles1->2; content width halves to711px Chrome,
707px Edge and720px Firefox, with CSS zoom1 and visualViewport.scale1. Firefox's
content-reported outer dimensions scale too, so independent browser-chrome
physical dimensions are retained.

Normal-content request/search/open controls and long-name Assistant/history
screens pass. The name wraps without clipping, complete text remains in DOM,
score/category/explanation content fits, Save as outfit succeeds and its saved
state appears, and the visualisation link retains the correct reference. History
retains its original score metadata and name. All three products retain Tab/type/
Enter request/search/open paths with visible focus; NFR-17 remains Verified.
VIS source preparation is exercised without inference, not model output quality.

Visual review inspected corrected360px, native200% Edge result and Firefox
historical long-name screenshots. New Chrome/Edge CDP viewport captures scroll
to the name and avoid the prior full-page CSS clipping parameter; the original
full-page captures also remain. Firefox PNGs are CSS-normalized, so native
setting/geometry is established independently. Headless screenshot review is
not a full accessibility or subjective typography study. **NFR-18: Verified for
the tested native200% content/actions**, with these capture/product qualifications.

## NFR-19: actual product versions and missing coverage

| Product / executable | Actual tested version | Result / remaining qualification |
|---|---|---|
|C:/Program Files/Google/Chrome/Application/chrome.exe|155.0.8059.85|Seven corrected-source cases pass; latest-stable coverage remains missing.|
|C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe|155.0.4283.62|Seven corrected-source cases pass; latest-stable coverage remains missing.|
|C:/Users/chong/AppData/Local/Mozilla Firefox/firefox.exe|158.0.1|Real release executable via Selenium4.51/geckodriver0.37.1; scoped corrected-source collector passes; desktop minimum width disclosed.|

Chrome/Edge use actual installed product channels, not bundled Chromium. All
three run headless in the local Windows11/Ryzen5 environment. Official stable
records during this test period identify Chrome156.0.8078.47/.48 for Windows and
Edge156.0.4314.42, while Firefox158.0.1 matches its release authority. Installed
Chrome/Edge155 therefore cannot close the original latest-stable requirement.
[Google release](https://chromereleases.googleblog.com/2026/10/stable-channel-update-for-desktop_02018666648.html),
[Microsoft release](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel),
[Mozilla authority](https://product-details.mozilla.org/1.0/firefox_versions.json).

No system browser update was performed. **NFR-19 remains Unverified.** The
shared frontend/deployment owner must provide the required current stable
products and run only the missing focused compatibility delta; no full J-16
matrix is needed. Do not relabel installed155 passes as156, or Firefox500px
observations as360/390px.

## Regression, source integrity and retained attempts

| Check | Result |
|---|---|
|Rendered component/browser regression|Chrome7/7 and Edge7/7; full names, ordinary layouts, roles/category, explanation, history, preferences/classic request, registration/profile/cancel/failure and listing/quota regression.|
|Firefox|Scoped actual-product collector exit0; normal account/profile/filter/Homepage/Assistant/history/save/preparation, keyboard,31 viewports and native200% long-name checks pass. No fabricated Playwright test count.|
|TypeScript / scoped lint|Native exit0 on approved component, new test/config sources.|
|Production build|Native exit0, new build `wyOjW-hOqqSjE-aJgofVa`; generated tsconfig/next-env copies retained and original bytes restored.|
|Exact production transition|One component only, four className changes; business content/logic exact. No global CSS/backend/guard/policy edit.|
|Starting/evidence integrity|All3,199 starting files present:3,198 unchanged and exactly the approved component advanced. All234 accepted J-19 deliverables unchanged.|
|Whitespace/syntax/staging|Git diff --check, explicit new-source whitespace/Python AST pass; staging empty.|

All before attempts remain. The initial new-test run expected “dress” where the
existing role label is “one piece”; its four product test failures are setup/
expectation failures, not a new application defect. Only that new assertion was
corrected. The labelled before-corrected-fixture run then reaches and retains
the real nine overflow observations per product and failed native200% cases.
The approved CSS correction makes the after cases pass with no retries, altered
deadline or weakened overflow/full-name condition. A quoted one-line proposal
command also failed with SyntaxError without changing production; its separate
proposal script succeeded. Existing uv no-project and Playwright colour warnings
remain in logs; native child codes determine reported checks rather than
PowerShell's stderr NativeCommandError wrapper.

J-20's initial pending-approval report/index/status remain as preparation
artifacts. Current report/matrix and verification helper/test paths legitimately
advance after consent; raw before artifacts and exact executed source snapshots
retain their bytes. `preparation-index-reconciliation.json` discloses those
within-phase references; no prior J-19 index/report or frozen evidence is edited.
`deliverables.json` hashes the final new deliverables and actual component;
phase originals/patch/manifest identify the approved transition.

Corrected-run backend PIDs12176 and23276 log Application shutdown complete and
Finished server process with native exit0; owned frontends/browsers stop and
ports3100/3101 are released. Temporary synthetic databases remain at ledger
paths. No unrelated process is stopped. These ordinary functional-cycle stops
do not diagnose or erase J-16's earlier large-run shutdown timeout, nor establish
multi-worker/in-flight/forced-termination/service-manager recovery.

## Updated totals and disposition

| Family | Total | Verified | Partial | Unverified | Blocked |
|---|---:|---:|---:|---:|---:|
|RN|30|29|1|0|0|
|FR-HR|12|12|0|0|0|
|FR-OA|12|12|0|0|0|
|FR-CH|16|16|0|0|0|
|FR-DW|20|16|0|4|0|
|FR-VIS|16|14|1|1|0|
|FR-ACC|15|14|1|0|0|
|FR-PP|9|9|0|0|0|
|NFR|25|20|0|5|0|
|**All original requirements**|**155**|**142**|**3**|**10**|**0**|

Still Partial: RN-13, FR-VIS-01 and FR-ACC-15. Still Unverified:
FR-DW-03/04/06/07, FR-VIS-09, NFR-01/02/03/11/19. Existing model-evidence transfer,
bounded suitability/VTON scope, durable logout, SQLite/PostgreSQL/architecture,
formal NFR baseline/history maximum, actual TLS/launcher/quota inventory and
curated source-release decisions remain separate. Missing latest-product and
Firefox sub500px coverage are explicitly retained; no unseen test or approval
is invented.

**PASS WITH LIMITATIONS.** The authorised layout correction and targeted
verification are complete for owner review. NFR-16/18 advance on actual rendered
evidence within the stated local scope; NFR-19 stays open for missing stable
product coverage. Whole-FYP acceptance remains NOT READY. Global defaults,
backend/data/policies and previous results remain unchanged apart from the one
approved frontend source transition. No staging, commit, reset, deletion,
deployment, automatic performance remeasurement or J-21 starts. Wait for review.
