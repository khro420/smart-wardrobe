# J-21: FR-ACC-15 durable logout implementation readiness

2026-10-23, Asia/Kuala_Lumpur. **Specification only; NOT IMPLEMENTED.** Shared
authentication/storage ownership, token-contract and database migration approval
are still required. This document does not select SQLite as the final FYP
architecture or authorise PostgreSQL work. FR-ACC-15 remains Partial.

The original requirement is: “The system shall invalidate the active session,
clear the stored authentication information and direct the user to the login
page after logout.” Authority: Project I PDF162/printed151, unchanged155-row
catalog and J-20 matrix. J-19 decision packet D4 is the starting proposal.

## Inspected current implementation

`backend/app/infrastructure/security.py` signs `user_id.expiry_epoch_second`
using HMAC-SHA256. There is no nonce/session ID. The default TTL is12 hours.
`current_user_id` authenticates API dependencies using signature and expiry;
the source inventory finds35 protected handlers across7 API routers. Public
registration/login and health are separate. `token_user_id` is called only by
that application authentication dependency. Protected media uses the same
dependency; an already authorised response/stream is not reauthenticated per byte.

`frontend/components/Layout.tsx:signOut` only calls `clearAccessToken` and
navigates to `/auth`. The helper removes the sessionStorage token, owner draft
keys and Homepage history state. There is no server logout route or revocation
lookup. The generic API helper throws on401 but does not itself clear the token.
No copied-token invalidation is supplied by browser deletion.

The actual provider is `sqlite3` in the misleadingly named
`postgresql_repository.py`; its connection manager enables foreign keys,
commits on successful exit, rolls back on failure and closes the connection.
Its SQLite connection has the library's default busy timeout. Application startup
already calls this provider's initializer and a separate recommendation migration.
The original PostgreSQL/pgvector design and Compose/SQL assets are not a live
PostgreSQL application adapter. No private database was inspected.

`authentication-source-review.json` records exact source hashes, line references
and handler inventory. This phase implements no token, auth dependency, route,
store, migration or frontend logout change.

## Readiness finding: deterministic re-login collision

For the same owner and expiry second, the current issuer produces identical
bearer bytes. Revoking their hash correctly invalidates every copy, but cannot
distinguish two independently initiated logins with identical bytes. More subtly,
an immediate login after logout in the same second can reissue the already revoked
bearer. Adding only a hash table would then make a successful login unusable.
This follows from the inspected issuer expression; it is not a claimed new
execution test or resolved defect.

**Recommended approval target:** one durable hash-revocation table, plus minimal
versioned random-nonce issuance for newly issued tokens. Keep legacy signed
tokens verifiable/revocable until their original expiry. This changes issuance
and parsing, so it must be expressly included in shared authentication approval;
it is not inferred from permission to add a table.

Newly issued tokens would carry a signed version, owner, unchanged expiry and a
cryptographically random nonce of at least128 bits, for example an unambiguous
v2 payload plus HMAC-SHA256 signature. All claims, including version and nonce,
are signed. Validate format/bounds before use and retain the existing HMAC and
expiry protection; do not describe the local format as JWT/OIDC. Login responses
still carry an opaque `access_token` string. New logins in the same clock second
then have distinct bearer values; one logout revokes its copies, not another
distinct new session. Legacy identical values remain one revocation identity.

If owners reject versioned issuance, the strict hash-only alternative needs an
explicit renewal/retry contract for same-second re-login and cannot promise
independently revocable identical sessions. It must not silently issue a revoked
token or change expiry to manufacture uniqueness. A global account version logs
out every session and is a different contract. An in-memory set does not meet
restart/shared-worker durability. The recommended v2/legacy contract below is
implementation-ready once approved; no alternative is treated as accepted.

## Persistent record and normalisation

For an explicitly approved SQLite prototype target, use one new
`revoked_access_tokens` table in the **same actual configured application DB**:

| Field/index | Proposed exact meaning |
|---|---|
|token_sha256 TEXT primary key|64 lowercase hexadecimal SHA-256 of the normalised, successfully verified full bearer bytes; validate hex/length. Never raw bearer, signature or password.|
|user_id TEXT NOT NULL|Owner derived from verified claims; reference users(id) with foreign keys enabled. Do not accept owner in a logout body. User-deletion policy is not expanded by this change.|
|expires_at INTEGER NOT NULL|Verified original UTC epoch second, unchanged by logout or retries.|
|revoked_at INTEGER NOT NULL|Server UTC epoch second of the first successful revocation; later retries preserve it.|
|expiry index|Index expires_at for bounded cleanup; primary key supplies authenticated digest lookup. No owner-wide query/index or logout-all feature is needed.|

Normalisation is the same bearer extraction/outer whitespace stripping used by
the existing boundary. Hash the resulting exact verified token's UTF-8 bytes;
never hash a different raw header representation or reconstructed claims.
Versioned and legacy tokens use the same digest table. Treat digests as sensitive
opaque authentication metadata: no public listing, API echo or ordinary logs.

The current verifier rejects only `exp < int(now)`; **exp equal to the current
second remains valid**. Preserve that boundary unless a separately approved
contract changes it. Therefore cleanup may delete only `expires_at < int(now)`,
not `<=`. Retain rows through the full valid expiry second, so cleanup cannot
make a revoked still-valid token usable again. Expiry is never extended by a
duplicate logout. A write begun while valid may complete after expiry; this does
not require an expires_at>=revoked_at constraint. Use no unbounded request-time
cleanup; any housekeeping must be bounded, failure-isolated and separately
operationally scheduled. Retain the table/database across ordinary restarts.

## Authentication and logout transaction contract

Normal protected requests must validate token signature/version/expiry, then
read the authoritative digest store before returning an owner ID. A matching
revoked row means generic401 and no endpoint execution. Missing table, SQLite
busy/I/O/corruption, unexpected row owner/expiry mismatch or query failure means
controlled503 and no authenticated data/action. Never interpret an error as
“not revoked.” Do not cache negative lookups in process memory or fall back to
the pre-revocation verifier.

Keep public login/registration separate from protected dependencies. On the
development identity path, a supplied revoked/invalid bearer must not fall
through to X-User-Id; the release requires development identity off. This
tightening of the current development fallback needs explicit shared approval
and focused tests. Preserve the intended credential-free development fixture
path only as separately configured, never as a revocation bypass.

Do not block the event loop with synchronous SQLite I/O from the existing async
dependency: execute store operations through the framework threadpool, with
independent short-lived connections. Proposed SQLite busy wait is at most1s
on those new connections only, then fail closed503. Do not change global
recommendation/quota connection timeouts. The timeout and chosen provider must
be approved/tested; this paper value is not an observed deadline guarantee.

Add `POST /api/v1/account/logout`, with Authorization bearer and no body/owner/
expiry parameter. A dedicated logout-only verification dependency accepts an
otherwise valid signed bearer even if already revoked, solely to perform the
idempotent logout operation. It must never return protected data or be used by
ordinary routes. Malformed/missing/invalid/expired credentials return generic401.

| Request state | Proposed response/effect |
|---|---|
|Valid unrevoked bearer|Begin short write transaction, insert digest/verified owner/expiry/first revoked_at, commit, then204 with empty body.|
|Same otherwise-valid bearer already revoked|Read/verify matching owner/expiry, preserve original row/time, complete transaction,204; enables lost-response retry.|
|Duplicate/concurrent logout|Primary key plus BEGIN IMMEDIATE serialises insert; one record, both successful idempotent acknowledgements after their transactions.|
|Store unavailable/missing schema/lock timeout/write or commit error|Rollback; controlled503, never a successful logout acknowledgement. No raw exception/credential in response.|
|Ordinary protected request after successful logout|401 before handler; copied bearer cannot read/write/replay even across restart with retained DB/secret.|

An insert conflict must verify that the existing row's owner/expiry match the
verified token; do not overwrite inconsistent metadata. The response must occur
after leaving the commit context. Never use the normal “reject revoked”
dependency for logout retry, or a lost successful response would become
unrecoverable. An expired token may return401 without a new row because it is
already invalid; it is not reported as a newly committed revocation.

Revocation takes effect for authentications whose authoritative lookup occurs
after commit. A request already authenticated before commit may finish and
write afterwards; logout is not request cancellation. Concurrent lookup versus
commit can be ordered either way. A new request started after the logout response
must fail with the copied token. Multiple deployed workers must all consult the
same approved durable provider and all enforce this rule; separate local files
or mixed old/new authentication workers do not meet it.

## Frontend completion and failure behavior

Add a typed bodyless logout helper through the existing API request path. The
Layout button becomes asynchronous and disables repeated clicks while pending.
Capture the current bearer identity at submission; after204, clear that same
browser token/owner drafts/Homepage state using the existing cleanup and navigate
to `/auth`. Ignore stale completion if the local token changed to a different
new login, rather than clearing the new identity.

Network timeout,503 or failed commit keeps the captured token/drafts and displays
a generic visible error with Retry. Do not claim server logout succeeded.
If commit succeeded but its response was lost, retry with that bearer gets the
idempotent204 and then performs local cleanup. An ordinary request in between
may correctly receive401. A401 logout response for an already expired/invalid
local credential can end local authentication and direct to login, without
claiming a successful revocation write. No-token local cleanup likewise must
not fabricate a server operation. Define this UI distinction in acceptance tests.

Use a fixed structured account/auth failure logger for lookup/write stage,
static error kind and generated diagnostic ID. Do not log raw token/header,
digest, signature, password, owner, private request or exception message/locals.
Do not expand the recommendation logger's operation allowlist for this separate
account concern. Current frontend API error behavior and owner draft boundaries
must remain covered. No such UI/logging change is made in J-21.

## Exact proposed files and owners

These are the recommended **future approval scope**, not J-21 changes:

| Path | Proposed change | Required owner |
|---|---|---|
|backend/app/infrastructure/security.py|Verified claims/digest extraction, versioned nonce issuer plus legacy verification, async authoritative revocation check, logout-only dependency, development fallback boundary.|Shared auth/security|
|backend/app/api/account_routes.py|Bodyless logout route and204/401/503 mapping; existing account contracts preserved.|Shared account/API|
|backend/app/application/account/account_service.py|Logout orchestration and acknowledgement after commit; retain registration/preferences/login contracts while using approved issuer.|Shared account|
|backend/app/infrastructure/persistence/postgresql_repository.py|Call the separately approved additive auth migration during existing initialization; keep actual provider/other schemas unchanged.|Shared storage/provider|
|backend/app/infrastructure/persistence/session_revocation_store.py (new)|SELECT plus atomic idempotent insert/compare; existing configured DB, independent bounded connections, no raw credential storage.|Shared storage/security|
|backend/app/infrastructure/persistence/session_revocation_migrations.py (new)|One table/expiry index, own atomic migration/shape validation; no historical row rewrite.|Shared storage/migration|
|frontend/lib/api.ts|Typed logout request; preserve all existing keyed recommendations, account/profile and media helpers.|Shared frontend/API|
|frontend/components/Layout.tsx|Await logout, pending/retry/error, identity-aware local cleanup/redirect.|Shared frontend|

The SQLite initializer can import the new migration inside its function, avoiding
a module cycle. The store depends on the existing provider, not account_service;
security may use the store, while account_service already imports security. Do
not introduce a security→account_service→security cycle. The migration receives
a connection rather than importing application authentication. No app.main or
recommendation route change is needed for this recommended shape.

Directly necessary future evidence/support files: new
`backend/tests/test_durable_logout.py`, new
`backend/tests/fixtures/durable_logout_sources.v1.json`, a narrowly scoped
`backend/tests/integration_source_guard.py` transition extension and any specifically
affected old auth callers/tests; new frontend logout/browser/helper tests and
phase configuration/report. Approval must name actual old tests being adapted
before edits. Do not repin old manifests or weaken authentication oracles. No
new SQL, migration module or logout test implementation is created in J-21.

## Migration, provider decision and deployment gate

The conditional SQLite plan adds its own table/index inside a dedicated
BEGIN IMMEDIATE transaction; validate existing shape/constraints before treating
an existing table as ready. DDL/commit failure rolls back and prevents startup
readiness; there is no auth-without-store fallback. Use an idempotent Python-owned
runtime migration consistent with the actual initializer. Existing numbered
SQL001–003 are PostgreSQL deployment assets; do not pretend they migrate this
SQLite runtime or edit them for this prototype feature.

Owners must explicitly approve **either** this actual SQLite prototype migration
target (without silently declaring the final PostgreSQL architecture closed),
**or** defer for an approved genuine PostgreSQL provider/migration design. A PG
choice requires its native schema/connection/locking implementation and tests;
it is not delivered by the SQLite proposal or Compose. No database path may be
silently changed. Back up and review the approved real target only under separate
data authority; J-21 opens no private database.

Before rollout, approve versioned-token/legacy expiry rules, same-file/provider
and secret retention, schema application/verification, and drain/cutover so no
old non-revocation worker continues serving. Retain revocations and v2 verification
during rollback; dropping the table or returning to the old unchecked verifier
can resurrect logged-out tokens. Old parsers also cannot authenticate new v2
tokens. Do not prescribe destructive down-migration or global secret rotation
as routine rollback; any forced invalidation needs separate explicit approval.
TLS, installed service persistence, multi-worker drain and recovery remain
deployment requirements, not certified by a local paper design.

## Focused acceptance gates after explicit approval

1. Freeze time and issue same-owner logins: new v2 bearers differ; immediate
   login after logout works. One token and all its copies reject after logout;
   distinct new session/foreign owner remain valid. Legacy identical values
   share the documented revocation identity. Reject tampering/malformed expiry/
   nonce/signature and preserve ordinary generic authentication errors.
2. Actual authenticated logout204, row digest/owner/verified expiry/first time,
   no raw token in storage/logs/response; duplicate/lost-response retry remains204
   and does not append/extend metadata. Expired/missing/invalid logout401 has no
   fabricated write. Exact expiry-second cleanup never revives a valid token.
3. Independent connections and, for an approved topology, separate processes:
   concurrent logout/idempotency, copied-token use after acknowledged commit,
   retained invalidation after restart with same DB/secret. Barrier tests clearly
   distinguish requests authenticated before commit from later ones.
4. Inject lookup/lock/write/commit/migration/shape failures: fail closed503 or
   failed startup, rollback, no success or dev-identity bypass; bounded waits,
   no event-loop blocking and no credentials in diagnostics. No negative cache.
5. Browser sign-out click/keyboard, pending/double-click,204 cleanup/redirect,
  503/network preservation and retry, lost204 recovery and stale completion
   versus a different new login. Existing registration/profile/preference flows,
   normal recommendation/history/keyed replay, owner protection and quota remain.
6. Record exact source transition and production build. New per-request auth I/O
   changes a shared boundary: review only the necessary approved auth/performance
   delta under the selected provider/baseline. Do not automatically rerun capacity
   studies or relabel J-16 results as measuring this unimplemented authentication.

**Approvals still required:** shared auth/account/API/frontend ownership for the
named files; v2 issuance plus legacy/session/retry semantics; storage owner and
supervisor's explicit prototype/provider/migration target; migration/cutover and
rollback/data authority for the actual deployment. J-21 is a reviewable readiness
specification, not consent to execute any of them. FR-ACC-15 remains Partial until
approved implementation and the relevant evidence actually pass.
