# J-19: remaining acceptance and implementation decisions

2026-10-23, Asia/Kuala_Lumpur. **Decision packet only; no option below has been
approved or implemented by this verification.** See the
[J-19 report](FINAL_SHARED_ACCEPTANCE_VERIFICATION.md) and
[complete 155-row matrix](FINAL_SHARED_ACCEPTANCE_REQUIREMENT_MATRIX.md).

## D1. Responsive result and native zoom: actual defect

**Owner: R/shared frontend. Classification: missing usable layout for valid
content. Requirements: NFR-16 and NFR-18, both Partial.**

A normally accepted 100-character unbroken garment name expands the result grid
outside its viewport. Actual Chrome/Edge fail at 360,390,768 CSS pixels; both
also fail with native browser zoom2. Hiding body overflow conceals a scrollbar
while clipping content. Normal short names and keyboard interactions pass.
Screenshots, DOM bounds and failed traces are retained in J-19.

The minimum proposed correction is containment/wrapping of the garment name and
its grid child in `frontend/components/RecommendationResult.tsx`, with any
directly necessary shared style change named before editing. Review historical
result displays that reuse it. Keep the existing valid name length, semantics,
data and score presentation. Do not shorten stored names or loosen assertions to
make the check pass. Approval must identify these production files and their
owners; J-19 only authorizes verification, so this correction was not made.
Then verify the reproduced widths, native200% result/history actions, and the
missing current stable product delta. Firefox's current desktop runner clamps
width below500px; an actual suitable smaller viewport remains necessary there.
This does not require a new performance or capacity study.

## D2. RN-13 suitability and colour boundary

**Owner: R/supervisor. Classification: missing capability outside the implemented
bounded policy, plus pending acceptance decision. Status: Partial.**

Choose explicitly between accepting the eight occasions (campus, work,
casual_outing, shopping, dinner, party, date, travel), two formalities (casual,
smart_casual) and named/exact-anchor colours as an academic scope deviation, or
requiring separately designed policies/evidence for the missing original scope.
Exercise/formal remain PolicyUnavailable. Every member, including outerwear,
requires explicit Allow; Deny fails and missing/conflicting evidence is Unknown.
No general hex classification, style-to-occasion inference or missing-value
promotion is proposed. Existing black/foreground provenance and freshness
qualifications remain. Scope acceptance must describe what is excluded; it is
not approval that the unrestricted original requirement is already fulfilled.

## D3. VTON scope and independent evidence

**Owner: T/supervisor. Classification: missing outerwear capability, missing raw
evidence, and pending acceptance decision. FR-VIS-01 Partial; FR-VIS-09 Unverified.**

Choose whether to accept the current eleven supported categories (four tops,
three bottoms, four dresses) and existing sequential processing order, with
whole-outfit VIS unavailable when outerwear is present. Alternatively, separately
scope additional model support and its authorised verification. Never silently
remove outerwear from a source outfit. Recommendation validity is separate from
VIS availability. Obtain existing lawful raw model/config/input/output/failure
bundles and source-journey evidence first. The handoff is not an independent
inspection of real inference, fit or visual quality.

## D4. Durable logout: minimum proposed storage design

**Owner: shared authentication/storage/UI owners. Classification: missing
functional capability. FR-ACC-15 remains Partial. No migration or security change
is authorised in J-19.**

The current signed bearer contains user ID and expiry plus an HMAC signature.
It has no independently random session identifier. Browser logout clears local
authentication/drafts but cannot revoke a copied unexpired bearer.

For the existing bearer contract, the smallest proposed durable design is one
revocation table in the actual application database, keyed by SHA-256 of the
complete signed bearer, with its verified owner, expiry and revocation time.
Store no raw bearer or credential. Authenticate signature/expiry first; every
authenticated dependency then checks revocation using the same durable provider.
Revocation lookup failures must fail closed. A normal authenticated logout route
must commit revocation before the UI reports successful logout. A retry with an
already revoked but otherwise valid bearer needs an explicitly designed
idempotent logout-only response; it must not reopen ordinary authenticated
routes. Retain entries through expiry, with separately bounded cleanup. Define
the concurrent-request boundary: revocation prevents subsequent authentication,
not cancellation of a request already authenticated and executing.

This proposal revokes the bearer and all its copied instances. Current tokens
can be identical for the same owner and expiry second, so two logins producing
identical bytes cannot be distinguished as independent sessions. If the owner
requires separately revocable concurrent sessions, choose a versioned random
session identifier and durable session table instead; that changes token/session
semantics and needs an explicit legacy-token expiry/invalidation plan. A global
account token-version increment is smaller conceptually but revokes every
session, so it should not be presented as one-session logout. An in-memory set
does not meet restart or shared-worker durability.

Before implementation, agree the session meaning, actual SQLite/PostgreSQL
provider decision, schema migration and rollback, logout route/model/auth
dependency, UI failure/retry behavior and source ownership. Minimum evidence:
copied token rejected after logout and restart; other-owner isolation; agreed
distinct-session behavior; idempotent/concurrent logout; a database failure
cannot report successful server invalidation; no credential-bearing logs; and
ordinary login/history/replay still work. Persistent revocation is not a token
format redesign by implication, nor does a paper design advance FR-ACC-15.

## D5. Database architecture

**Owner: supervisor/shared provider/T/deployment. Classification: implemented
SQLite prototype differs from original PostgreSQL/pgvector design; acceptance
decision or conditional missing implementation.**

Option A is an explicit documented academic deviation accepting the actual
SQLite provider and its tested single-worker local topology. State that the
PostgreSQL/pgvector application architecture is not delivered. Option B requires
a separately approved genuine application adapter and schema/JSON/vector/ID
mapping, migrations, owner transaction/locking strategy, data preservation and
concurrency/replay tests. Compose, DDL and a standalone schema smoke are not a
live PostgreSQL application provider. SQLite BEGIN IMMEDIATE tests do not
transfer automatically. No provider connection, migration, private data
inventory or rewrite was performed here.

## D6. Canonical architecture assertion

**Owner: shared architecture/T. Classification: actual layout/assertion
inconsistency.**

The existing canonical-location test still fails because `ai-services` exists.
The read-only inventory finds five descendant directories and no files. That
does not establish an active second backend. The owner must establish the
intended layout and whether these are obsolete empty placeholders, required
structure or an intentionally supported boundary. Any approved reconciliation
must explain the architecture and preserve necessary assets/evidence. J-19
neither removes directories nor weakens the assertion. Its one failed focused
architecture check remains separate from the217 passing functional regressions.

## D7. Formal NFR-01/02/03 baseline and maximum

**Owner: owner/supervisor/deployment. Classification: pending formal acceptance,
not an observed latency defect. All three remain Unverified for formal acceptance;
NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.**

Adopt or amend each field below in the actual system test plan and identify the
approver/date. No response has yet made these decisions.

| Decision | Retained J-16 boundary requiring adoption |
|---|---|
|Capacity|Owner-selected100 active non-archived garments; preserve balanced17,710 and maximum-combination38,148 candidates. No reopening of150/200 studies.|
|History maximum|Proposed10,000 personal plus10,000 foreign coherent completed chats,50-row pages; empty/common/none/Unicode/literal percent/underscore/many/few and later-page queries. It is not an enforced storage quota or already approved formal maximum.|
|Environment|Ryzen5 7235HS,8 logical CPUs,19.692GiB RAM, Windows11 build26200, local C: disk/temp SQLite/media/logs; OneDrive source/build, loopback same-origin proxy, one active interaction and one Uvicorn worker. Pin actual provider/runtime/build/browser hashes from J-16.|
|Release selection|Compact execution, experimental60/20/20 profile, suitability and both integrated features explicitly on;100 quota and fail-closed generation. Defaults remain off/deferred.|
|Images|Protected256x256 synthetic PNGs; all result images loaded. Decide whether that represents the accepted image scope; it does not establish real-photo/network/GPU contention performance.|
|T0/T1|Homepage native document load to complete visible result/images; Assistant captured submit to correct terminal UI/images; history navigation/search/Load more to exact visible ordered rows. Later-page setup and detail opening excluded from search timing.|
|Population/statistic|Five browser observations plus one separate HTTP comparison per cell; retain every first/slow sample, require correctness and each original3/5/2s bound, not merely median/p95.105 browser+21 HTTP total, diagnostics separately labelled.|
|Resources|Idle gate qualified; active CPU47.88–100%, freeRAM5.477–6.026GiB. No continuous background isolation, cold-disk, concurrent-user or production guarantee. No overhead subtraction.|
|Operations|J-16 response/history checks completed before one30s shutdown timeout. J-19's idle clean stop adds narrower evidence and does not identify its cause.|

Retained browser maxima are **2.2861/3.471/0.3994s** against **3/5/2s**. Approvers
must decide whether the retained qualified observations suffice for the adopted
scope. A material approved change, such as required PostgreSQL, external network,
real images or GPU contention, needs only its missing verification delta. Do not
repeat a completed matrix to obtain more passing numbers or relabel synthetic
SQLite results as a different environment.

## D8. Deployment, data and release packaging

**Owner: deployment/shared frontend/T/data owners. Classification: missing
environment/data proof and pending release approval. NFR-11 and NFR-19 Unverified.**

Provide the actual HTTPS/proxy/certificate/origin configuration and authenticated
transport proof, persistent five-flag launcher, private non-default secret and
explicit database retention path. Uvicorn does not prove loading a plain .env
file, and process-local examples are not installed service settings. Preserve
J-14 fail-closed routing; rollback scoring/suitability without rewriting stored
experimental history. Same-origin tests do not resolve separate-origin PUT and
If-Match CORS requirements. Multi-worker/in-flight drain and forced termination
during writes remain outside this idle local check.

Separately authorise the target real-account read-only quota/status inventory
and support plan. Preserve over-limit/unusual-status/historical records; no
automatic archive, repair or invented confirmation links. Pending jobs reserve
no slots. No such private inventory occurred in J-19.

Curate the exact tracked and untracked working-tree source set for release; HEAD
alone omits verified implementations. Keep raw evidence separately, pin source,
policies, packages and the chosen production build, and publish registration
confirmation/login and disabled-generation compatibility changes to legitimate
external consumers. No staging/commit/deployment permission is inferred.

Current stable Chrome/Edge product coverage remains missing. Firefox158.0.1 is
installed and exercised, while the installed Chrome/Edge155 versions are below
their published stable156 releases. Keep those product results useful but
accurately qualified; update/provide the required products through the owner's
normal mechanism, then verify the focused missing delta.

## Minimum route to a final acceptance decision

1. Obtain D2/D3/D5/D6/D7 scope/architecture/test-plan decisions and T's existing
   raw model evidence. These can proceed together; artifact absence is not proof
   that T never tested.
2. Separately approve the narrow D1 layout correction and D4 durable logout
   implementation/storage design. Verify only changed paths and remaining
   product/viewport/zoom gaps, retaining J-19 failures.
3. Complete the approved actual deployment/TLS/launcher/quota/source-package
   evidence and any specifically missing model coverage. Reuse unchanged exact
   scoring,100-capacity and J-16 observations where applicable.
4. Reconcile the155-row matrix against original wording and accepted deviations,
   then have the owner/supervisor decide whole-FYP acceptance. No automatic new
   phase, implementation, model run, remeasurement or deployment starts here.
