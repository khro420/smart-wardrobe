# Phase 5F-2E-3J-21: final browser compatibility and durable logout readiness

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-20 is owner-closed PASS WITH LIMITATIONS. The updated actual installed products
pass14 focused Chrome/Edge cases and the scoped Firefox collector on unchanged
accepted J-20 sources/build. Durable logout has a reviewable implementation
specification, with no feature or migration implemented. Whole-FYP readiness
remains NOT READY.

The owner explicitly adopts generally available Windows Stable releases for this test environment. NFR-19 becomes Verified for that documented scope; Chrome157 Early Stable is not claimed.

The155 original requirements total **143 Verified,3 Partial,
9 Unverified,0 Blocked**. FR-ACC-15 remains Partial. The full
[JSON matrix](../storage/verification/phase5f2e3j21/requirement-matrix.json) and
[CSV](../storage/verification/phase5f2e3j21/requirement-matrix.csv) retain original
sentences/pages/priorities, J-20/current status, evidence and remaining owners.
NFR-16/17/18 retain their accepted bounded verification. **NFR-02 remains OPEN /
NOT FORMALLY ACCEPTED.**

## Actual browser versions and release applicability

| Product / actual executable | File and runtime version | Vendor release / executed result |
|---|---|---|
|C:/Program Files/Google/Chrome/Application/chrome.exe|156.0.8078.48|Matches normal Windows Stable156;7/7 focused cases pass in50.7s. Broader review also identifies staged157 Early Stable, untested.|
|C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe|156.0.4314.42|Matches published Stable;7/7 cases pass in40.1s.|
|C:/Users/chong/AppData/Local/Mozilla Firefox/firefox.exe|158.0.1|Matches Mozilla release authority; actual WebDriver collector exit0.|

Installed ProductVersion was checked before testing, Chrome/Edge actual runtime
versions were independently probed through installed product channels, and
Firefox's real browser capability version is asserted before registration.
Post-run file versions match. No system browser update, bundled Chromium
substitution or replacement application occurred. The user supplied the updates.

The initial gate used Google's normal Stable announcement for Windows
156.0.8078.47/.48, Microsoft's156.0.4314.42 record and Mozilla's158.0.1 authority.
Those versions are the actual tested general-Stable products.
[Google normal Stable](https://chromereleases.googleblog.com/2026/10/stable-channel-update-for-desktop_02018666648.html),
[Microsoft](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel),
[Mozilla](https://product-details.mozilla.org/1.0/firefox_versions.json).

A later broader review of Google's release index found **157.0.8103.15/.16
Early Stable for a small Windows cohort, dated October22**. Google distinguishes
this initial rollout from normal Stable/download availability about a week later.
The initial commentary treated matching normal Stable as sufficient; this newer
finding qualifies that conclusion rather than being hidden.
[Early Stable announcement](https://chromereleases.googleblog.com/2026/10/early-stable-update-for-desktop_02123641300.html),
[rollout definition](https://developer.chrome.com/blog/early-stable/).

The original NFR-19 says latest stable versions available during system testing;
it does not explicitly settle staged-cohort applicability. The owner explicitly
answered **“Use generally available Stable releases”**. This adopts the tested
general Windows Stable scope and closes NFR-19 for that scope using the completed
observations. Chrome157 Early Stable remains untested. The exact decision is in
`browser-scope-decision.json`; it grants no logout, migration or final-provider
approval. No browser check was rerun or replaced after this decision.
`browser-authority.json` preserves the initial normal-Stable gate;
`release-scope-review.json` discloses the later finding and initially pending
boundary. The pending report, matrix, register and181-entry index are preserved
under `pre-scope-decision/`; only NFR-19 advances from the J-20 status baseline.
The supplemental Google version-history API was inaccessible and a search
returned no result; accessible vendor announcements/index supply the evidence.

## Focused execution and preserved functionality

The exact J-20 frontend test/config files were reused unchanged. Their executed
source snapshots/hashes, commands, outcomes and screenshots are retained under
`storage/verification/phase5f2e3j21/runs/verified/`. The Firefox collector is a
new verification-only copy with its account namespace and explicit runtime
version assertion; outcomes are unchanged. Its31 viewport observations are not
presented as31 distinct test cases or added to the14 Playwright passes.

| Covered boundary | New result |
|---|---|
|Registration/login/profile|Real confirmation mismatch/success-to-login, normal login and controlled profile save/cancel/failed-save checks pass. Firefox also uses the real form/login.|
|Homepage / Assistant|Actual random valid Homepage/no-chat and normal classic request flows pass; exact experimental60/20/20 provenance, preferences and history replay remain.|
|Names / responsive layout|83/83 observations per Chrome/Edge fit, including ordinary four-state17-width sweep and100-character Assistant/history/Homepage cases at360/390/768/1280/1920.|
|History / keyboard|Search/open, original scores/name/snapshots and Tab/type/Enter required actions with visible focus pass.|
|Native200%|Normal-content and full100-character result/history states/actions pass. Native setting2/DPR2 and halved CSS widths are recorded; CSS zoom1/visualViewport.scale1, not CSS-only zoom.|
|Saved outfit / source|Save action and saved state/link retain correct references; Firefox also performs real current-source VIS preparation without inference.|
|Firefox actual limits|21 ordinary plus10 maximum-name viewport observations pass at observed500/640/768/1024/1280/1920. Requested360/390 clamp to500; no sub500 or long-name Homepage sweep is claimed.|

All three products run headless in the same local Windows prototype topology.
Normal `app.main:app`, Uvicorn lifespan/composition, existing J-20 production Next
build **wyOjW-hOqqSjE-aJgofVa** and same-origin3100->3101 proxy serve the flows.
No new build or application source change was necessary. There is no test-only
business service/route or engine/evaluator selector. Lifecycle wrappers only
control normal shutdown; the retained network-abort case simulates a failed save.

Separate supervisors create new disposable SQLite fixtures, normally register/
log in accounts, review/confirm synthetic development uploads, turn development
identity off and pass non-default child secrets. Existing initialization runs
only for those fixtures; no new auth migration or production migration runs.
VTOFF/VTON stay off; no model or private user data is opened. Explicit child flags
retain compact/experimental/suitability/Assistant/Homepage,100 quota and J-14
fail-closed behavior. None are global environment/default activation.

There are **zero functional test failures** in the new final browser collections.
Existing Playwright colour and uv no-project warnings remain in raw logs. Native
child return codes distinguish warnings from PowerShell's stderr wrapper status.
J-19 failed layouts, J-20 before failures and corrected results remain unchanged.
Test durations50.7/40.1s are suite durations, not new NFR latency measurements.
No capacity study or J-16 performance matrix ran.

## FR-ACC-15 implementation-ready specification; no implementation

[Durable logout readiness](DURABLE_LOGOUT_IMPLEMENTATION_READINESS.md) traces the
original PDF162 requirement, current security/account/provider/UI sources and
J-19 D4. Static review identifies35 protected handlers across7 routers, browser-only
logout, no revocation store and the actual SQLite provider. It supplies exact
future file ownership, record/transaction/API/UI/migration contracts and focused
acceptance gates. This is readiness evidence, not executed logout tests or a
claim that FR-ACC-15 has been closed.

The recommended persistent record contains SHA-256 of the normalised verified
full bearer, verified owner/expiry and first revocation time, plus an expiry
index. Never raw tokens. Every protected authentication reads authoritative
revocation state; errors fail closed503. Logout commits before204; an otherwise
valid already-revoked bearer may retry only that logout operation idempotently.
Copied-token rejection survives restart with the same approved DB/secret.
Already-authenticated requests may finish; logout is not in-flight cancellation.

Two source findings refine D4:

1. The current deterministic owner/expiry-second issuer can reissue the same
   revoked bearer on immediate re-login. The recommended separately approved
   scope adds signed versioned random-nonce issuance while accepting/revoking
   legacy bearers until their original expiry. Hash storage alone cannot promise
   distinct identical legacy sessions. No token redesign is implemented here.
2. Current validation accepts exp equal to int(now). Cleanup must use strictly
   expires_at<int(now), not<=, or a revoked token could revive during its last
   valid second. The spec preserves this boundary, short transaction/threadpool
   behavior, retry/commit failures and credential-free diagnostics.

Future proposed existing production files: security.py, account_routes.py,
account_service.py, the actual provider initializer, frontend/lib/api.ts and
frontend/components/Layout.tsx. New proposed files are session_revocation_store.py
and session_revocation_migrations.py under the existing persistence package.
Directly necessary tests/guard transition and a new frontend build also require
named approval. The complete paths/owners are in the specification.

Required approvals are shared auth/account/API/frontend ownership; explicit
versioned-issuance/legacy/session/retry semantics; storage/supervisor approval of
the actual prototype/provider/migration target; and deployment/data authority
for cutover/retention/rollback. The conditional SQLite plan is not acceptance of
SQLite as final FYP architecture. A PostgreSQL decision needs genuine separate
provider/migration/locking work. No executable migration, auth helper, revocation
set, new logout route or frontend logout change is introduced in J-21.

## Outstanding implementation versus acceptance/evidence decisions

`decision-register.json` gives exact classifications, owners, evidence and
minimum actions. All remain open unless explicitly resolved by the browser
scope disposition above.

| Item | Type / owner | Remaining minimum action |
|---|---|---|
|RN-13|Missing out-of-scope capability / R+supervisor|Accept supported8 occasions/2 formalities/named-exact-anchor boundary or approve missing policies/evidence. No promotion of Unknown.|
|VTON/model evidence|Outerwear capability/scope plus raw-evidence gap / T+supervisor|Accept11-class exclusion or design missing support; transfer lawful original model/config/input/output/failure/source bundles before fresh runs.65 named local candidates/mirrors still absent.|
|SQLite/PostgreSQL|Architecture decision/conditional implementation / supervisor+shared storage+T|Explicit prototype deviation/target decision or separately approved real provider/migrations; Compose is not a live adapter.|
|NFR-01/02/03|Formal acceptance / owner+supervisor+deployment|Adopt exact100-capacity, proposed10k+10k history maximum, environment/images/T0-T1/resource/sample scope; decide retained J-16 sufficiency. Maxima2.2861/3.471/0.3994s against3/5/2s unchanged.|
|HTTPS/deployment|Missing environment/data/operational proof / deployment+T/shared|Actual TLS/launcher/secret/DB retention, separate-origin CORS, approved real quota/status inventory/support, source packaging and drain/recovery proof. No private inventory occurs here.|
|ai-services|Layout/assertion inconsistency / shared architecture+T|Still5 descendant directories/0 files; reconcile intended layout. Do not delete or weaken assertion merely to pass. Prior failure is retained, not rerun.|
|FR-ACC-15|Missing implementation and approvals / shared auth/storage/frontend|Review and explicitly approve the specification/target before code/migration, then copied-token/restart/concurrency/error/browser checks.|
|NFR-19|Resolved applicability decision / owner+shared frontend|Owner adopts generally available Windows Stable. Completed actual-product checks establish Verified within that scope; retain untested Early Stable and Firefox width limits.|

Normal new browser shutdowns do not diagnose or erase J-16's historical timeout.
Formal baselines, real-model quality, private account inventory, deployed TLS,
installed service persistence, multi-worker/in-flight recovery and final provider
architecture are not certified by compatibility passes or a paper auth design.

## Integrity and closure

All **3,527 starting file hashes and328 accepted J-20 indexed deliverables**
remain unchanged. These sets overlap. No production source, prior test/guard,
policy/default, build, previous report or historical raw result is edited.
No source transition is required. New additions are this report, the logout
specification and J-21 verification/review/matrix/index artifacts. Original
requirement wording/pages/priorities are checked against J-20.

Read-only source/evidence checks, Git diff --check, new Python/JavaScript syntax
and explicit whitespace checks pass; staging remains empty. There is no backend
suite, TypeScript rerun or new build for unchanged app/test sources. New scripts
are syntax-checked and actual collectors executed. The working tree still contains
earlier uncommitted tracked/untracked implementations; this is not clean deployable
HEAD or permission to package/commit/deploy it.

Both supervisors log native exit0 and complete backend shutdown, close their
owned frontend/browser processes and release3100/3101. Temporary synthetic DB
paths and process flags/PIDs are in their ledgers. No unrelated process is stopped.
`deliverables.json` hashes the final new set; all original failed evidence remains.

**PASS WITH LIMITATIONS.** Requested independent compatibility execution and
durable logout readiness review are complete for owner review. NFR-19 is Verified
under the owner's explicit generally available Stable scope. The completed test
population remains unchanged; paper design and missing evidence do not close
the other requirements.
FR-ACC-15 remains Partial, whole-FYP acceptance remains NOT READY and NFR-02 stays
OPEN / NOT FORMALLY ACCEPTED. No logout implementation, migration, system browser
update, deployment, automatic benchmark or J-22 begins. Wait for review.
