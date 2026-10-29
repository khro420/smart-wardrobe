# Phase 5F-2E-3J-22: durable logout implementation and FR-ACC-15 verification

2026-10-24, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-21 is owner-closed PASS WITH LIMITATIONS. The expressly approved durable logout
contract is implemented and verified for the actual SQLite prototype. **FR-ACC-15
advances from Partial to Verified for this supported local scope.** The155 original
requirements now total **144 Verified,2 Partial,9 Unverified,0 Blocked**. Whole-FYP
acceptance remains NOT READY; **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED**.
This is no deployment, private-database migration or final PostgreSQL acceptance.

## Recorded authority and exact change boundary

J-22 preparation initially stopped before editing at its explicit approval gate.
The owner subsequently answered all three questions:

- “Shared owners approve this file scope”.
- “Auth owners approve this token and session contract”.
- “Storage owner and supervisor approve these prototype migration semantics”.

`ownership-approval.json` records A through E, the six existing production files,
two new persistence modules, directly necessary new tests and source-guard
transition. The approval covers v2 nonce issuance, legacy expiry, independent
new sessions/identical legacy identities, additive prototype migration and retained
DB/secret/revocations/v2 verification on restart and rollback. It excludes private
database migration, deployment and final architecture acceptance. No additional
ownership authority is inferred. No existing test module is edited; only the
approved integration source guard advances among existing test/support files.

| Production file | Actual implementation |
|---|---|
|`backend/app/infrastructure/security.py`|Versioned signed issuance, verified claims/digest, legacy verification, threaded authoritative auth lookup, logout-only verification and no supplied-bearer development fallback.|
|`backend/app/api/account_routes.py`|Bodyless POST /api/v1/account/logout; empty204 after service acknowledgement.|
|`backend/app/application/account/account_service.py`|Revocation orchestration and controlled503 mapping after store failure.|
|`backend/app/infrastructure/persistence/postgresql_repository.py`|Call the isolated additive auth migration during initialization; generic failed readiness on migration error. Actual provider remains sqlite3.|
|`backend/app/infrastructure/persistence/session_revocation_store.py` (new)|Independent one-second-timeout connections, authoritative read, transactional idempotent insert/compare, bounded explicit cleanup and fixed safe diagnostics.|
|`backend/app/infrastructure/persistence/session_revocation_migrations.py` (new)|One revocation table and expiry index, atomic DDL plus exact existing-schema validation.|
|`frontend/lib/api.ts`|Typed captured-bearer logout helper; request respects an explicitly supplied Authorization header. Other callers still use the current browser token.|
|`frontend/components/Layout.tsx`|Asynchronous pending/retry/error flow and identity-aware cleanup/redirect.|

The NLP grammar/vocabulary, all scoring weights/policies, suitability rules,
100-garment quota, ConfirmedGarmentQuery, random Homepage, Assistant selection/
persistence, J-14 routing, CV/VTON and feature defaults remain byte-identical.
No historical chat/recommendation or actual-account data was opened or changed.
Only synthetic disposable databases receive the new migration and test writes.

## Signed-token and authentication contract

New bearer shape is `v2.base64url_owner.expiry_epoch_second.nonce.signature`.
Owner encoding is canonical unpadded base64url. The nonce uses secrets.token_hex(16),
128 cryptographic random bits. Signature is HMAC-SHA256 over a distinct fixed v2
signing context followed by the complete payload, including version/owner/expiry/
nonce. This prevents ambiguity with a valid legacy owner ID beginning `v2.`.
It eliminates the deterministic same-second collision; random uniqueness is a
cryptographic probability, not a mathematical guarantee of no possible collision.
The existing12-hour default TTL and secret/default configuration remain unchanged.
This local signed format is not described as JWT/OIDC.

Legacy `owner.expiry.signature` uses its original HMAC context and remains
verifiable through its original expiry unless revoked. Correctly signed legacy
dotted owner IDs, including the ambiguous-looking prefix, are covered. New v2
logins are independent sessions. Identical legacy bytes are one revocation
identity and every copy is invalidated together. No account-wide logout or
global secret rotation is introduced. Malformed bounds/encoding/version/nonce,
tampered signed fields/signature and expired credentials reject safely.

The expiry comparison remains exp<int(now): the exact expiry second is valid.
The normalized extracted bearer is hashed with SHA-256 over its exact UTF-8
bytes. Raw bearers, signatures, passwords and Authorization headers are never
written to the revocation table or emitted by the new diagnostics.

All35 existing protected handlers across7 mounted API routers retain their
current_user_id dependency, now backed by authoritative storage. Protected media
uses it too. Revoked credentials produce generic401 before handler execution;
missing table/lock/read/I/O/metadata inconsistency or lookup failure produces
generic503. No negative cache, in-memory revocation substitute or old-verifier
fallback exists. A supplied invalid/revoked bearer cannot fall through to
X-User-Id even when development identity is enabled. The explicitly configured
credential-free development fixture path remains; actual browser/transport
services use development identity off. Public registration/login/health remain
separate and retain their contracts.

The new SQLite reads use the framework threadpool from the async dependency.
Independent connections wait at most1s for SQLite locks; global recommendation/
quota connection behavior is unchanged. A controlled slow-store check confirms
the event loop continues to progress. Pure signature parsing remains a helper;
it is not used as an alternative protected-route dependency.

## Logout, concurrency and frontend completion

| Request/state | Verified response and effect |
|---|---|
|Valid unrevoked bearer|Short BEGIN IMMEDIATE, insert verified digest/owner/expiry/first revocation time, commit, then empty204.|
|Otherwise-valid already-revoked bearer|Logout-only dependency allows retry; stored owner/expiry must match; original row/time retained;204. Ordinary protected routes still reject it.|
|Concurrent duplicate logout|Independent connections serialize; both204, one durable row.|
|Copied bearer after acknowledged commit|401 on fresh protected access, including separate-process application restart retaining DB/secret.|
|Expired/missing/malformed/invalid bearer|Generic401; no fabricated revocation write or successful server acknowledgement.|
|Missing schema/read/write/lock/commit failure|Generic503; no false204, real insertion rollback, no development fallback.|
|Request authenticated before revocation commit|May finish after logout. The barrier check retains its200 followed by fresh401; logout is not cancellation.|

The logout operation takes no owner/expiry input. On an insert conflict it
compares existing verified metadata instead of overwriting it. Success occurs
only after leaving the commit context. A process restart test invokes untouched
app.main in a separate Python process against the same disposable DB/secret,
and verifies copied-token401. This is actual process/state persistence evidence,
not service-manager, in-flight-drain or multi-worker certification.

The Layout button has an immediate pending guard and disabled state. It captures
the bearer, sends the server request and clears that matching local identity,
owner draft keys and Homepage history state only after204. It redirects to /auth.
Stale success cannot clear a distinct newer login. On503/network failure it
retains the token/drafts and shows a fixed error with Retry sign out; no internal
response detail is displayed. A committed but lost response leaves local state
until retry receives the idempotent204. Invalid/expired401 can end local
authentication without claiming a new revocation commit. No-token local cleanup
likewise sends no fabricated server operation.

The actual Chrome production-browser cases cover pending/double-click protection,
keyboard activation, committed-copy rejection, independent sessions,503 and
network preservation/retry, lost-response recovery, stale completion versus a
new login and invalid-local401 cleanup. Three reused J-20 cases also cover real
registration/login/profile/cancel/failed save, listing/quota/eligibility and normal
classic Assistant/preference/history replay. These are functional checks, not
new browser deadline measurements.

## Additive migration, failure security and retention

The table contains only token_sha256 (64 lowercase hex primary key), verified
user_id foreign key, original INTEGER expires_at and first INTEGER revoked_at.
It has one expiry index. No unrelated schema/record is rewritten by this migration.
It creates/validates table and index inside one BEGIN IMMEDIATE transaction,
and the provider commits on success. Existing shape/constraints must match the
expected definition; weak table/wrong index or disabled foreign keys are errors.
DDL/commit/shape failures prevent application startup readiness rather than
starting authentication without its store. Original numbered PostgreSQL SQL
assets are unchanged and are not presented as the SQLite migration mechanism.

Tests verify initial/idempotent initialization and retained rows, foreign-key/
type/hash constraints, invalid shape/index, injected DDL and commit faults,
real exclusive-lock failures, SELECT faults, trigger-aborted INSERT rollback,
metadata inconsistency and successful recovery/retry. Full sorted unrelated-table
rows compare equal in the preservation cases. Bounded explicit cleanup retains
expires_at==now and deletes only expires_at<now; no automatic request cleanup or
housekeeping schedule is activated. A write that began valid may commit after
expiry; no false expires_at>=revoked_at constraint is imposed.

The fixed app.authentication.failure schema records UTC time, a generated
diagnostic ID, lookup/write/migration stage and static StorageUnavailable kind.
It never serializes exception messages/classes/args/chains/locals, token/hash/
header/password/owner/private request, and uses no exc_info. Hostile exception
and failing-log-sink tests preserve generic503 and inspect complete captured text.
Production log delivery/access/retention remain deployment responsibilities.

This is an approved SQLite prototype feature only. Keep the configured DB,
secret, revocation rows and v2 verifier across restarts/rollback. No mixed old
non-revocation workers may serve after rollout. Dropping this table or returning
to the old unchecked verifier can resurrect revoked credentials; old parsers
also cannot read new v2 bearers. There is no destructive down-migration or
secret rotation. Any actual private-target backup/migration/cutover/deployment
still needs its separate data/deployment authority.

## Relevant authentication/performance delta

The final comparison uses exact pre-J22 backend originals in a temporary source
copy versus the final approved backend, one actual Uvicorn app.main worker at a
time on loopback. Both start from copies of the same synthetic DB. Its empty auth
table is present in both arms to isolate the authentication-code delta. Existing
unchanged J-16 seeding/J-10 inputs supply100 balanced garments and20k coherent
history rows; this is no new capacity population. Only five profile reads, five
campus first-page history reads and three balanced100 generic submissions run per
arm. No ranking warm-up or first-sample exclusion. Exact J-10 selected members,
full17,710 scored candidates and score metadata match for all six selected results.
History totals1000/50 owner-only IDs match. Each arm adds exactly3 chats and3
recommendations and zero revocation rows.

Plan/source hashes were frozen before final collection. Direct time includes full
JSON consumption; it is not a UI Homepage post-load stopwatch or formal NFR
acceptance. All observations, including first values, are retained below in seconds:

| Operation | Pre-J22 baseline, all in order | Final auth, all in order | Median baseline / final |
|---|---|---|---|
|profile|0.021859, 0.003757, 0.003442, 0.021020, 0.004075|0.005866, 0.004918, 0.004954, 0.004276, 0.004701|0.004075 / 0.004918|
|history_campus_first|0.084069, 0.071063, 0.062054, 0.060745, 0.062448|0.100593, 0.054187, 0.058737, 0.088917, 0.087570|0.062448 / 0.087570|
|balanced_100_generic|0.951808, 0.922235, 0.997774|0.929023, 0.929322, 0.850101|0.951808 / 0.929023|

The200-read local microdiagnostic median is
0.006000ms for legacy pure verification and
0.648800ms for final v2 verification plus one
authoritative SQLite read. This local microdiagnostic excludes framework
threadpool/HTTP cost; direct requests above include it. The new connection/read
has measurable cost. Sequential order, caches, process activity and background
contention are not controlled sufficiently to attribute differences in the
ranking/history samples causally to authentication, or claim a speedup/guarantee.

All17 one-second resource samples remain: observed CPU
28.46–66.54%,
freeRAM7.517–7.681GiB.
No test/build/model collector ran concurrently with this final comparison;
continuous idle/background isolation is not established. This small justified
transport delta does not replace or reapprove J-16, establish concurrent-user/
real-image/PostgreSQL equivalence or change its3/5/2s deadlines. Formal NFR-01/02/03
remain Unverified pending their separate accepted baseline/history maximum.

## Regression evidence and retained attempts

| Check | Final evidence |
|---|---|
|Focused backend|517 passed, including45 new logout checks and affected account/profile/quota/style/routing/preferences/ranking/persistence/Homepage/Assistant and original compact/transitive source guards.|
|Legacy-prefix boundary|The same new case was rechecked with the precise three-component dotted legacy owner;1 passed, overlapping the517, not another distinct case.|
|Actual production Chrome|8/8 passed in18.8s; five logout plus three reused shared integration cases; actual installed Chrome156.0.8078.48, no bundled-browser substitution.|
|TypeScript / lint|Final noEmit/nonincremental TypeScript and scoped ESLint passed; production build TypeScript also passed.|
|Production build|Passed; separate retained build `AozB2g_eYG3WtplDyqYxW`. No earlier build overwritten.|
|Final transport delta|26/26 correct;200 technical micro reads per arm; all values retained, no deadline acceptance inferred.|
|Integrity|All3718 starting paths present;3711 unchanged, exactly7 approved existing-file changes (six production plus guard); two production modules added. All190 accepted J-21 indexed deliverables unchanged.|
|Whitespace/source/staging|git diff --check, explicit new-source whitespace/Python AST and exact source transition pass; staging empty; generated tsconfig/next-env copies retained and original bytes restored.|

An initial new route-inventory test counted app.routes wrappers and reported
1 failure/42 passes. Inspecting the actual seven mounted routers corrected the
test; no auth production assertion was weakened. The43-case correction and
later44-case/515-test passes remain overlapping intermediate evidence. Final
review added unambiguous v2 signing context and the legacy-prefix/tampering case;
the517-test and final browser results cover that production state. The precise
prefix fixture refinement was separately rechecked. No old test/oracle changed.

The first frontend-check driver rejected --noEmit as its own argparse option
before TypeScript executed; its argument forwarding was corrected. Subsequent
native exit0 records determine TypeScript/lint/build results. Existing uv
no-project, Starlette/httpx deprecation and Playwright colour warnings are
retained; PowerShell stderr wrappers do not replace captured child exit codes.

The first transport attempt stopped at the collector's incorrect expected-case
lookup (generic was wrongly required to have J-10 suitability=true). Ten cheap
profile/history checks had completed, but their timing values were only in
memory and were not archived; they cannot be used as timing evidence. There
were no generation POSTs in that attempt. Its plan/executed scripts/logs/clean
stop remain. The corrected collector writes each observation incrementally.
Its completed26-request intermediate comparison is retained separately.
The final signing-context correction justifies the distinct final comparison;
it does not erase or replace earlier measurements. No full NFR matrix was run.

Both browser-attempt backends and all transport-arm backends log complete clean
shutdown with native exit0; owned frontend/browsers stop and ports3100/3101 are
released. Synthetic DBs remain at ledger paths. No unrelated process was stopped.
These stops do not diagnose or erase J-16's historical shutdown timeout or certify
installed-service/multi-worker/in-flight/forced-termination recovery.

`durable_logout_sources.v1.json` pins exactly six replacements and two additions.
The existing guard follows that explicit transition; prior manifests/reference
ZIPs and arithmetic oracles remain unchanged. `phase-existing-files.patch`,
original copies and full starting hashes distinguish J-22 from the earlier
uncommitted working tree. No commit/reset/staging/packaging approval is inferred.

## Requirement totals and remaining decisions

The complete [JSON matrix](../storage/verification/phase5f2e3j22/requirement-matrix.json)
and [CSV](../storage/verification/phase5f2e3j22/requirement-matrix.csv) preserve all155
original sentences/pages/priorities and J-21/current statuses. Only FR-ACC-15
advances. Counts are traceability statuses for supported local scope, not a
universal accuracy percentage or whole-FYP acceptance rate.

| Family | Total | Verified | Partial | Unverified | Blocked |
|---|---:|---:|---:|---:|---:|
|RN|30|29|1|0|0|
|FR-HR|12|12|0|0|0|
|FR-OA|12|12|0|0|0|
|FR-CH|16|16|0|0|0|
|FR-DW|20|16|0|4|0|
|FR-VIS|16|14|1|1|0|
|FR-ACC|15|15|0|0|0|
|FR-PP|9|9|0|0|0|
|NFR|25|21|0|4|0|
|**All**|**155**|**144**|**2**|**9**|**0**|

Still Partial: RN-13 and FR-VIS-01. Still Unverified: FR-DW-03/04/06/07,
FR-VIS-09 and NFR-01/02/03/11. NFR-19 retains the owner's J-21 generally available
Windows Stable scope and Firefox minimum-width limitation; no new all-product
compatibility claim is made here.

| Outstanding dependency | Classification / remaining owner action |
|---|---|
|RN-13|Supervisor accepts bounded8 occasions/2 formalities/named-anchor policy, or separately approves missing capability/evidence. No Unknown evidence promotion.|
|VTON/CV/VTOFF|T transfers existing lawful real-model/input/output/config/weight/failure/source evidence; T/supervisor accepts11 top/bottom/dress classes excluding outerwear or separately scopes support. Missing files do not disprove teammate execution.|
|SQLite/PostgreSQL|One auth migration is approved for the prototype; final original PostgreSQL/pgvector design deviation/provider decision remains OPEN. No PG adapter/migration/locking certification is supplied.|
|Formal NFR-01/02/03|Owner/supervisor adopts actual baseline/history maximum/images/resources/statistics and determines retained J-16 sufficiency plus any necessary auth delta; no automatic remeasurement.|
|HTTPS/deployment/data|Actual TLS, launcher, secret/DB retention, source packaging, approved private quota/status inventory/support, cutover/drain and recovery remain separate. No private target touched.|
|Canonical ai-services|Shared architecture/T owner reconciles existing layout/assertion inconsistency; no deletion, assertion weakening or claim that the known broad-suite failure is now green.|

`decision-register.json` retains these distinctions and the prototype approval.
**FR-ACC-15 recommendation: Verified for the approved, executed local contract.**
**Final phase recommendation: PASS WITH LIMITATIONS.** The authorised durable
logout correction is implemented and tested; whole-FYP acceptance remains NOT
READY. No global defaults, recommendation policies, historical data, private DB,
CV/VTON or final provider choice changed. No deployment, automatic full benchmark
or J-23 begins. Wait for owner review.

## Exact production transition

| Path | Before SHA256 | After SHA256 |
|---|---|---|
|`backend/app/infrastructure/security.py`|`2e2bddc52b2f426a5bb341a12accc1b7317a4f0d0142842591557d4fb93de9fb`|`90a697837c99f9bf19ed59ff2cb722c55b819a8bad40447d0e5604560c6f26fa`|
|`backend/app/api/account_routes.py`|`d5e94e18d47142f5f3bb5276d2dcd2829dee317f6f567c68e6fdcaed3a5964b0`|`407e8fab387f5aea272a88e3177a218ae62cb41aef5af5a436d72483dd4853d5`|
|`backend/app/application/account/account_service.py`|`7c958085a47915f6c06d1fea3f23e26d03ce5f40f83a7600fe7eaffea7e86982`|`5c28d75148e670b0de27345073aae48c709e36fe80964758a7442aa206ab67ae`|
|`backend/app/infrastructure/persistence/postgresql_repository.py`|`063ca9d67fadd13a3c646b64447403587fb95c6d7084c2508507b91b245aca29`|`41eadf98f56d4cf7ae4c8132ddb719de7cce31f260dd159ac52814ba9e845ade`|
|`frontend/lib/api.ts`|`7279714227c63c4e4e13f805e235a1f6928adf99f67d7533c97e804c5eb325b3`|`5acada3cf1742ffcc7795b0641979e7d35e735dddbe93be2639a16c7eaa2ab5f`|
|`frontend/components/Layout.tsx`|`acdcc87e3d08f1c72876847eb8189e2965cb83e2e10f26a1477fafaf815daff0`|`5135f2e2854eab9045c92e7a96f91dd61125becad36645a2ceec4498c8b4ff68`|
