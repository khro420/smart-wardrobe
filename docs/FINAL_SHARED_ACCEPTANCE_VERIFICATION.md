# Phase 5F-2E-3J-19: final shared acceptance evidence and release-readiness verification

2026-10-23, Asia/Kuala_Lumpur. **Overall: NOT READY for final whole-FYP acceptance.**
J-18 is owner-closed PASS WITH LIMITATIONS. Its approved corrections pass the
focused regression. The intended explicitly configured recommendation workflow
remains READY WITH LIMITATIONS for bounded local demonstration. This phase also
reproduces a valid-content responsive/zoom defect; accessibility is not wholly
passing. Verification and consolidation are complete for owner review, with
failures retained. No deployment or whole-FYP approval is implied.

The original155 requirements now total **140 Verified,5 Partial,10 Unverified,
0 Blocked**, from J-18's139/3/13/0. Only NFR-16/17/18 change status: keyboard
NFR-17 becomes Verified; responsive NFR-16 and zoom NFR-18 become Partial after
actual failures. NFR-19 stays Unverified because the installed Chrome/Edge
versions are behind published stable releases. The
[complete155-row matrix](FINAL_SHARED_ACCEPTANCE_REQUIREMENT_MATRIX.md),
[JSON](../storage/verification/phase5f2e3j19/requirement-matrix.json) and
[CSV](../storage/verification/phase5f2e3j19/requirement-matrix.csv) retain original
sentences, pages, priorities, J-18/current statuses, owners, evidence and actions.
The [decision packet](FINAL_SHARED_ACCEPTANCE_DECISIONS.md) specifies remaining
scope, logout, provider, architecture, NFR and deployment decisions.

## Authority, baseline and verification boundary

The owner's J-19 attachment authorises focused verification, one qualified
bounded lifecycle cycle, raw-evidence inspection and paper decisions. It
explicitly withholds automatic production UI fixes, logout/schema/provider work,
global defaults, model acquisition/inference and another performance study.
No such change occurred. Only new documentation, verification sources and
artifacts were added. Existing application sources, tests/guards, policy inputs,
historical reports and raw evidence retain their bytes.

The original Project I PDF was read directly, including requirement and database
architecture pages. SHA256 remains
`5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`.
Its100 FRs,25 NFRs and30 RNs form the155 denominator; CA constraints and teammate
O1/O2/AIR IDs are not added. J-10 through J-18 reports/closure evidence and both
teammate handoffs were reviewed. `phase-register.json` retains report hashes and
session closure authority. No old acceptance status or failed population was
rewritten.

All browser services used unchanged `app.main:app`, ordinary Uvicorn lifespan/
composition and the existing J-18 production Next build
**`o2aRZKY_67KAiMV7I1qqh`**, normal same-origin proxy3100->3101. The lifecycle
wrappers control stopping/observing only; there are no `/_test` business routes,
profile/evaluator selectors, ranking substitutes or fake browser API results.
Focused backend fault tests deliberately inject failures and use their existing
test fixtures; those are distinguished from ordinary-service browser flows.

Disposable new SQLite databases, normal account registration/login and generated
non-default child-process secrets were used. Development identity was disabled
for actual browser/lifecycle services. Synthetic uploads were normally reviewed
and confirmed; AI development processing and VTOFF/VTON off do not certify real
models. No real accounts/photos/private deployment database were inspected.
Separate runs use distinct disposable files; each ledger identifies its path.

The five explicit child settings were compact_exhaustive,
experimental_compatibility_decision_v1, suitability=true, Assistant=true and
Homepage=true. Exact60/20/20 scoring, all-candidate evaluation, tie order,8/2
suitability, strict owner/confirmed/available query,100-active quota and J-14
fail-closed routing remain unchanged. No installed/User/Machine environment was
edited; the audited host process flags remain unset. No new build was required.

## J-18 and shared-boundary regression

**217 focused backend tests passed in106.14s**, native exit0. The selected modules
cover all44 J-18 functional-closure cases and30 diagnostic cases, J-14 routing,
quota, strict saved-outfit/VIS eligibility, startup selection, completed history
and the compact frozen-source guard. These counts overlap J-18 and prior phase
coverage; do not add them as new distinct historical tests. Exact commands,
responses and native return codes are in `backend-checks.json`,
`focused-backend.log` and `api-trials.jsonl`.

| Boundary | Actual new verification |
|---|---|
|Registration/login|Required confirmation, syntax/empty/mismatch rejection, duplicate/concurrent account checks and general wrong-login messages in focused API cases. Actual Chrome/Edge form mismatch, Registered/no-token success-to-login and normal login pass; Firefox normal register/login also passes.|
|Profile/preferences|Owner isolation, supported-type/value/weight validation, Cancel, clear/save, network-failed-save draft preservation and trigger-injected transaction rollback pass. Existing independent-connection acknowledgement-race case passes. Actual Chrome/Edge exercise the full J-18 profile journey; Firefox covers saved colour/cancel.|
|Listing/quota|Colour/style/availability filters compose without changing independent usage or recommendation eligibility; non-available rows remain read-only. Actual filter/archive journey passes. API quota99/100, concurrent/batch/rollback/source conditions remain enforced.|
|NLP/scoring|Normal classic-outfit submissions select confirmed classic garments with unchanged exact profile, components, preference snapshot and provenance. Original J-15 S07/S15 failures remain historical, not relabelled passes.|
|Homepage/history|Actual valid random Homepage result creates no chat; Assistant stores/replays immutable history, original scores and request. Keyboard searches/opening reach the correct completed record.|
|Saved outfit/VIS|Normal authenticated save and current-source preparation pass, including owner/confirmed/reference checks in backend cases. Firefox also executes actual save/preparation. No inference/output quality claim.|
|Diagnostics/routing|Existing production logger fault/redaction/hostile-handler checks pass with generic outcomes and rollback/replay. Disabled qualified/unqualified generation writes remain closed; no legacy dispatch.|

The independent canonical architecture assertion was also run: **1 failed
in0.13s**, at the retained `ai-services` existence check. This is not included
in the217 passes or hidden by a combined green result. Its disposition is below.
No broad regression suite, NFR matrix, new capacity population or model ran.

## Actual product versions and browser outcomes

| Product | Actual installed executable/version | Retained result |
|---|---|---|
|Google Chrome|`C:/Program Files/Google/Chrome/Application/chrome.exe`;155.0.8059.85|Initial collection5 passed/1 failed; all three integration journeys, keyboard and normal200% pass. Viewport boundary fails. Separate native200% maximum-name case fails.|
|Microsoft Edge|`C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`;155.0.4283.62|Same5 passed/1 failed outcome; separate native200% maximum-name case fails.|
|Mozilla Firefox|User-installed `C:/Users/chong/AppData/Local/Mozilla Firefox/firefox.exe`;158.0.1|Real WebDriver collector exit0; normal auth/profile/filter/Homepage/Assistant/history/save/source, keyboard and native200% checks pass within disclosed scope.|

Firefox was initially absent in standard locations. After the user's installation
reply, it was found at the per-user path and tested. Chrome/Edge use Playwright
installed product channels, not the bundled Chromium executable. Firefox uses
Selenium4.51.0/geckodriver0.37.1 with the actual installed release, not a patched
Playwright Firefox substitute. Only this isolated test dependency/driver was
added to tool caches; application dependency/lock files did not change.
All three products ran headless on Windows11 build26200, Ryzen5 7235HS/8 logical
processors and19.692GiB physical RAM. Raw OS/CPU/file-version captures accompany
the product results. These functional checks have no idle CPU qualification or
performance acceptance claim; a headed human readability review remains useful
within the screenshot limitations below.

As checked on2026-10-23, Google announces stable Chrome156.0.8078.47/.48 for
Windows and Microsoft lists Edge156.0.4314.42; installed155 is older. Mozilla's
release authority identifies Firefox158.0.1. Therefore functional product
coverage does **not** close the original latest-stable three-product NFR-19.
[Google release](https://chromereleases.googleblog.com/2026/10/stable-channel-update-for-desktop_02018666648.html),
[Microsoft release](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel),
[Mozilla release authority](https://product-details.mozilla.org/1.0/firefox_versions.json).
No installed product was updated by this collector; only the missing focused
current-product delta is needed after owner provisioning/approved UI correction.

## Viewports, keyboard and native browser zoom

Chrome and Edge each retained **73 layout observations**: four normal-content
states (Assistant draft/result, history list/detail) across17 sampled widths
360,375,390,412,480,639,640,641,767,768,769,1023,1024,1025,1280,1440,1920;
plus a maximum-name result at360,390,768,1280,1920. All68 normal-content
observations per product pass. This samples the requested range and breakpoint
boundaries; it does not claim testing every integer width or all possible text.

The boundary uses an ordinary accepted garment PATCH with a valid100-character
unbroken name (`J19` plus97 `x` characters). **Both products fail at360,390,768**;
document content reaches approximately862/862/857px respectively. At1280/1920
the boundary fits. The result name/grid expands and content clips beyond the
viewport. Body overflow-x:hidden does not make that usable. The unchanged
application accepts the name, so this is not malformed test data.
[360px failure screenshot](../storage/verification/phase5f2e3j19/runs/initial/chrome/maximum-name-result-360-failure.png)
and per-product `viewport-results.json`/failed traces retain the evidence.
**NFR-16 is Partial.** No production UI file was patched without its separately
required ownership/scope approval.

Firefox retained21 observations across three states (draft/result/history).
Requested360/390 desktop widths were clamped by this actual browser to500px;
actual widths are500,640,768,1024,1280,1920. Those observed normal-content
layouts pass; Firefox360/390 and maximum-name coverage are **not** claimed.

All three products perform request entry/submission, history search and opening
using Tab, typing and Enter. Required actions are not reached with a test DOM
focus/click shortcut. Five required focus targets per product have visible
solid3px outlines and retained screenshots; the correct persisted result opens.
Setup/navigation uses ordinary automation outside the keyboard interaction.
**NFR-17 is Verified for its stated required controls**, not a full WCAG audit.

The200% checks use **native browser zoom**, not CSS zoom, deviceScaleFactor-only
emulation or pinch scale. Chrome/Edge isolated profiles set native default zoom2
through their own settings page API. Firefox uses its privileged native Zoom
manager through WebDriver. Recorded DPR doubles1->2, content width halves
(Chrome1422->711, Edge1414->707, Firefox1440->720), CSS zoom remains1 and
visualViewport.scale remains1. Physical browser dimensions remain1440x1000;
Firefox's content-reported outer dimensions scale, so its independent browser
chrome dimensions are also retained.

Normal-content result/history actions pass at native200% in all three. The
viewport failure justified one separately declared **maximum-name native200%
case**, without repeating passing journeys: both Chrome/Edge fail it, with
approximately857px content in711/707px viewports. **NFR-18 is Partial.** Firefox
did not run that boundary case; no cross-product boundary pass is inferred.

Native-zoom screenshot capture has an observer qualification: Playwright's
full-page PNGs have CSS-sized output with native scaling/cropping, while
Firefox's PNGs are CSS-normalized. They are preserved as captured, not described
as physical-screen photographs or independent glyph-size measurements. Native
setting/geometry, action success and DOM text bounds establish the reported
zoom facts; the100% screenshot independently shows the real overflow. Screenshot
normalization itself is not classified as an extra application defect.
`screenshot-observer-limitations.json` retains visual review and its limits.

## Bounded lifecycle and the retained J-16 problem

The predeclared qualified cycle used normal app.main/Uvicorn with the same five
intended release flags, new disposable SQLite, real login, reviewed synthetic
classic dress, one authenticated selected recommendation and history detail/list
retrieval. HTTP response contexts were closed with Connection:close before stop.
The new test runner observes async task frame locations/counts, never locals or
credentials, and requests ordinary Uvicorn should_exit. It changes no application
service, provider or shutdown implementation.

| Qualified lifecycle fact | Actual evidence |
|---|---|
|Application / launcher PID|27684 /10820|
|Stop bound / observed exit|30s / **0.4220000000204891s**|
|Exit/logs|Native exit0; Application shutdown complete and Finished server process|
|Before-stop requests/connections|Uvicorn request tasks0; connections0; task-frame snapshot retained|
|Persisted stopped state|Exactly one recommendation/chat/metadata/receipt/item/item-snapshot; normal experimental provenance and exact selected score retained|
|Cleanup|All HTTP contexts closed; owned process exited normally;3101 released|

`lifecycle-qualified/plan.json`, `result.json`, `before-graceful-stop.json` and
`backend.log` retain commands, flags, state and timing. This is one qualified
idle stop cycle, not a latency study, restart, in-flight drain or forced-kill test.

An earlier **preparation attempt** indexed processing items while the normal
asynchronous job was still queued and raised IndexError. It never reached the
submission/history/declared stop stopwatch. Its owned backend25936 nevertheless
shut down cleanly in cleanup. The original collector/log/plan remain under
`lifecycle/`. A new labelled collector polls the existing job API until
review_required and completes the one qualified cycle above; the initial file
was not rewritten. `lifecycle-preparation-summary.json` records this test setup
mistake. It is not a second application shutdown failure or an invented complete
pass; no speculative shutdown reproduction or infrastructure patch followed.

J-16's backend14568 timeout after all measurements/history checks remains
unexplained and unchanged. This small clean cycle and earlier clean browser
service stops add evidence without identifying the cause of that larger-run
failure. Reliable service-manager persistence, multi-worker recovery, in-flight
drain and termination during writes remain unverified.

## Teammate model evidence and architecture

`GARMENT_WORKFLOW_HANDOFF.md` and `VTON_HANDOFF.md` were read, including reported
segmentation/held-out, attributes/embedding, VTOFF standardisation/smoke, VTON
real-model/supported categories and PostgreSQL standalone smoke claims. Handoff
hashes and exact named paths/source lines are retained. The final inventory
checks **65 distinct local file/directory candidates and mirrors:0 present**.
This includes browser/capacity/audit references as well as model evidence; it
does not mean65 independent model tests were expected. Exact missing locations
and responsible owner are in
[teammate-evidence-presence-final.json](../storage/verification/phase5f2e3j19/teammate-evidence-presence-final.json).

| Missing bundle / examples under storage/verification, with backend/runs mirrors checked | Required owner/evidence |
|---|---|
|segmentation/results.json; segmentation/held_out_evaluation/; backend/runs/held_out_segmentation/metrics/|T: original category/mask/box/confidence and held-out inputs, outputs, failures/model/config hashes|
|attributes/results.json; embeddings/results.json|T: exact supported/absent-field outputs, model/weight/config/source provenance|
|vtoff_standardisation/results.json and pairs/; vtoff/smoke/results.json; paired_evaluation/ and paired_dataset_audit.json|T: retained standardisation/fallback/foreground/colour provenance, lawful pairs and known failures|
|vton/smoke/results.json; vton/reconstruction/results.json; vton/dresscode_paired_evaluation/results.json; backend/models/vton/manifest.json|T: pinned real weights/config/input/output/failure hashes and supported source journeys|
|o1/requirements-audit.json; o2/requirements-audit.json; O1 capacity/browser evidence; workflow-latency.json; pgvector/results.json|T/shared provider: original handoff acceptance/latency and standalone schema records, clearly distinct from live-provider proof|

The handoff's pinned CatVTON source/weight revisions, academic/noncommercial
conditions,11-class boundary and reported real upper-body smoke remain claims
of that evidence owner. Their raw outputs are absent here; neither development
processing nor source preparation independently verifies them. No model weights,
private images, dataset acquisition or inference ran. Transfer existing lawful
evidence first; missing local files do not establish that a teammate never tested.

The first path inventory mistakenly treated three semicolon-separated lists as
filenames. It is retained unchanged. The final read-only script splits each
path, deduplicates, includes exact handoff/auditor references and checks mirrors
separately; no missing raw file was fabricated or old evidence rewritten.

Actual application storage remains sqlite3/BEGIN IMMEDIATE. The original report
specifies PostgreSQL/pgvector; Compose/DDL or a claimed independent schema smoke
does not supply an application adapter. Supervisor acceptance of an explicit
SQLite prototype deviation or separately approved shared provider/migration/
locking work is still required. RN-13 bounded scope,11-class/outerwear VIS and
durable logout decisions also remain unapproved. The decision packet gives the
smallest logout proposal and its identical-token/session limitation; no in-memory
revocation substitute, migration or token redesign was implemented.

The failing canonical test still sees `ai-services`. Read-only inventory finds
five descendant directories and no files; it does not prove a second active
runtime. Architecture/T owners must reconcile intended layout and assertion.
Nothing was deleted and the test was not weakened.

## Formal NFR and deployment readiness

| Original requirement | Reused J-16 maximum / deadline | Current status |
|---|---|---|
|NFR-01 Homepage|2.2861s /3s;10 browser+2 HTTP|Observed local pass; formal baseline/image/network/resource adoption pending. Unverified.|
|NFR-02 Assistant|3.471s /5s;35 principal browser+7 HTTP;10+2 diagnostics separate|OPEN / NOT FORMALLY ACCEPTED. Unverified.|
|NFR-03 history|0.3994s /2s;50 browser+10 HTTP|Observed local pass at proposed10k personal+10k foreign,50-row pages; formal maximum pending. Unverified.|

All105 browser/21 HTTP observations and original deadlines/first/slow samples
remain unchanged. No J-16 collector was rerun. Its idle qualification and active
47.88–100% CPU,5.477–6.026GiB freeRAM, small five-per-cell samples, synthetic256px
images, headless local loopback/single worker and post-collection shutdown
failure retain their limitations. J-19 introduces no real-photo, external-network,
GPU-contention, concurrent-user or PostgreSQL performance claim. The exact
capacity/history/environment/T0/T1/images/resources/every-observation acceptance
decisions are enumerated in D7. Existing100 capacity is not reopened.

Deployment remains unapproved: no actual HTTPS certificate/proxy journey or
installed persistent launcher was inspected, so NFR-11 stays Unverified. Normal
same-origin local HTTP does not close separate-origin PUT/If-Match CORS, TLS,
secret lifecycle or multi-worker/drain requirements. Existing authentication is
signed HMAC bearer, not separately certified JWT/OIDC. The production secret
guard and local non-default test secret do not prove a deployed secret policy.

No private real-account quota/status inventory was authorised or performed.
Deployment/T owners must separately select that target, inventory read-only and
agree preservation/recovery for over-limit and unusual/non-visible statuses.
Never prune/repair history or manufacture confirmed links. Actual flags, secret
and DB retention path, rollback/history proof and curated release-source/build
set still require owners. No staging, commit, reset, deployment or rollback of
data occurred.

## Integrity, additions and all retained failures

Read-only final checks verify **all2,961 starting file hashes,144 accepted J-18
indexed deliverables and226 J-18 final source/build entries unchanged**. These
overlap and are not additive. The existing current/reference compact guard
passes through the accepted source-transition chain; no repinning/new transition
is needed for verification-only additions. HEAD remains
`e717f5f785a6325894981a025aeb313167df850e` (2026-10-11). The baseline working tree
contains earlier uncommitted tracked and untracked source; verified state is not
a clean committed/deployable HEAD. There are35 tracked modified paths both
before and after, with407 initial and414 final Git-reported untracked entries
(the7 new external files; verification storage is ignored by Git).
Staging remains empty. Before/after statuses
and counts are in `working-tree-summary.json` and raw Git captures.

New external files are the lifecycle test runner, two frontend verification
tests/configuration, this report, decision packet and complete matrix. All other
new scripts, browser versions, responses, metrics, screenshots/traces, temporary
database paths and ledgers are under `storage/verification/phase5f2e3j19/`.
`deliverables.json` hashes this complete new set, excluding itself. Final
TypeScript, scoped ESLint, Python AST, explicit new-source whitespace and
`git diff --check` pass. There is no new production build or dependency-lock edit.

All failures remain visible: Chrome/Edge viewport tests and separate native200%
boundary tests fail; the known architecture test fails. No retry, production fix,
deadline extension or assertion relaxation turns those into passes. The isolated
Firefox collector passes its disclosed narrower scope. Test probes initially
failed to apply native zoom through profile preferences; the correct native
settings path was validated before collection. An initial Firefox probe passed
an unsupported system-access argument through browser capabilities; corrected
geckodriver service permission enables the real native zoom observation. Probe
logs remain; those are tooling setup failures, not app/browser compliance results.

PDF extraction initially used a wrong platform text decoding for comparison;
the corrected new extraction matches original wording. Final matrix assembly
then caught two inherited J-18 mojibake apostrophes (FR-DW-20/NFR-24). The new
matrix restores U+2019 to match the original PDF/catalog; J-18 files are not
rewritten. `pdf-decoding-reconciliation.json` and
`matrix-decoding-reconciliation.json` disclose both steps. No requirement meaning
or priority changed.

The lifecycle preparation error and path-list parsing correction are disclosed
above. Existing Starlette/httpx deprecation, uv no-project and Playwright colour
warnings remain in raw logs. PowerShell may report NativeCommandError/shell1 for
uv's stderr warning despite passing child work; native check/Playwright/driver
return codes and actual result artifacts control the reported outcomes. The
three ordinary browser supervisors and qualified lifecycle log clean backend
shutdowns; their owned frontends/browsers stop and ports3100/3101 are released.
No unrelated application was stopped.

## Current matrix and minimum remaining work

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
|NFR|25|18|2|5|0|
|**All original requirements**|**155**|**140**|**5**|**10**|**0**|

| Remaining rows | Exact owner/dependency and minimum action |
|---|---|
|RN-13 Partial|R/supervisor: explicit bounded8/2/named-anchor acceptance or separately designed missing policies.|
|FR-VIS-01 Partial|T/supervisor:11-class/outerwear scope decision plus existing raw source journeys; additional support only if separately required.|
|FR-ACC-15 Partial|Shared auth/storage/UI: approve and implement durable session invalidation design/migration, then copied-token/restart/isolation/failure tests.|
|NFR-16,18 Partial|R/shared frontend: approve narrow valid-name/result-grid correction; verify retained width/native200% failures and history/actions.|
|FR-DW-03,04,06,07; FR-VIS-09 Unverified|T: transfer exact lawful segmentation/attributes/VTOFF/VTON raw input/output/model/config/failure bundles; inspect only missing authorised coverage.|
|NFR-01,02,03 Unverified|Owner/supervisor/deployment: formal environment,100-capacity,10k+10k maximum,image/resource/boundary/sample adoption and retained-evidence acceptance.|
|NFR-11 Unverified|Deployment: actual approved HTTPS/proxy/authenticated transport and launcher/secret/DB proof.|
|NFR-19 Unverified|Shared frontend/deployment: current stable Chrome/Edge availability and focused missing product checks; retain real Firefox evidence and its sub500px limitation.|

Provider/architecture decisions, real quota/support inventory and curated source
packaging remain cross-cutting dependencies, even where they are not additional
rows in the155 denominator. The full matrix gives each non-Verified row its
classification, named owner and completion action. No row is marked Blocked merely
because an approval/artifact is pending; this verification could finish honestly.

**NOT READY for final whole-FYP acceptance.** The approved J-18 corrections and
bounded recommendation workflow remain supported; keyboard accessibility now has
actual three-product evidence. The new layout/zoom failures, durable logout gap,
unaccepted RN/VTON/provider scope, missing model evidence, formal NFR decisions
and deployment/latest-product proof prevent final closure. Complete the precise
decisions and narrow approved corrections/evidence deltas in the packet; there
is no basis for another recommendation algorithm, capacity reduction or full
J-16 rerun. **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** J-19 verification is
complete for owner review. No next phase or deployment begins automatically.
