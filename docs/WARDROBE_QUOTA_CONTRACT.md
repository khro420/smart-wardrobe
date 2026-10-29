# 100-garment wardrobe quota contract and implementation readiness review

2026-10-23, Asia/Kuala_Lumpur. **Documentation-only proposal; NOT IMPLEMENTED.**
J-10 is owner-closed PASS WITH LIMITATIONS. The owner accepts100 garments as the
proposed maximum for the academic prototype. No further capacity reduction or
J-9/J-10 experiment is proposed. Digital Wardrobe implementation still requires
teammate approval. This review changes only this new document; no application,
database, test, model, policy/default or retained evidence is changed or executed.

**Recommendation:** limit each user's **active stored garment entries** to100,
enforced atomically when reviewed candidates become wardrobe garments. Successfully
archived entries release capacity while their rows/history remain. This lifecycle
definition is proposed for owner/teammate agreement; accepting100 as a proposed
capacity did not independently settle archive counting or authorize code changes.
NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. Capacity evidence does not enable
experimental scoring or general suitability; compact/deferred remain defaults.

## 1. Actual implementation inspected

| Workflow | Current implementation and source | Consequence for a quota |
|---|---|---|
| Upload | `backend/app/api/garment_processing_routes.py:11` validates/stores media, creates a job, schedules a background task. `upload_validator.py` delegates to protected media; JPEG/PNG, byte and image checks apply. | No total garment count or reservation exists. One photo can produce several candidates; images/jobs cannot be equated to garments. |
| Processing | `backend/app/application/garment_processing/processing_job_service.py:9` creates queued jobs. `garment_processing_orchestrator.py:21` claims queued work, runs AI outside short write transactions, stores pending candidates and moves to review_required. Cancel/failure/restart have controlled states. | Pending jobs/candidates are separate records, not wardrobe entries. No quota currently constrains them. |
| Review | `review_service.py:15` uses BEGIN IMMEDIATE, owner/job checks and accepted/rejected decisions with attribute/media validation. | Acceptance is review evidence, not garment insertion or reserved capacity. |
| Confirmation | `review_service.py:11` delegates through ConfirmedGarmentWriter to `wardrobe_service.py:105`. BEGIN IMMEDIATE precedes owner/job state and accepted-item checks; all garments/representations, confirmed statuses, optional outfit/items and completed job commit together. | This is the authoritative shared insertion boundary. No current count check. A selected subset completes the entire job; remaining candidates cannot later be confirmed through that completed job. |
| Repeat confirmation | Completed/non-review_required jobs return409; each garment processing_item_id is UNIQUE. `test_garment_workflow.py:245` expects201+409 for competing same-job confirmations. | Existing behaviour prevents duplicate saves but is **not** replay of the original successful response. Do not describe it as receipt-based idempotency. |
| Listing | `wardrobe_service.py:85` returns all matching owner/status=available rows, with filters and no total cap. `wardrobe_routes.py:13` exposes the list. | Filtered list length is not authoritative quota usage. Never truncate the list to100 to simulate enforcement. |
| Archive/delete | `wardrobe_routes.py:34` DELETE calls `wardrobe_service.py:228`: BEGIN IMMEDIATE, dependency validation, status=archived, deleted_at/updated_at timestamps. Available outfits or queued/processing visualisations block it. | DELETE is a soft archive, not physical row/media deletion. Only a successful committed archive can release a slot. No restore or ordinary hard-delete route was found. |
| Outfits/actions | `wardrobe_service.py:296` creates outfits from existing garment references. Recommendation saves similarly reference existing garments. | Creating/saving an outfit creates no additional garment entries and consumes no garment slots. |
| Recommendation eligibility | `confirmed_garment_query_adapter.py:123` requires available owner garments linked to confirmed items and owner-matching processing jobs; downstream mandatory conditions further restrict candidates. | Eligibility is narrower than stored wardrobe usage. Its query/policy must remain unchanged. |
| Frontend | `frontend/app/extract/page.tsx:15` checks file type/size, not count. `extract/results/page.tsx:153` sends **all accepted IDs** although the button says selected. `wardrobe/page.tsx:215` always offers Add from image; shown counts are filtered. | New count feedback needs a separate owner-scoped server projection and explicit confirmation selection if offered. Existing count labels are not a quota. |

`ReviewRequest.items` and `ConfirmRequest.item_ids` remain1..100 distinct entries
per request (`backend/app/domain/value_objects/requests.py:44,54`). Their100-ID
batch restriction is independent of total wardrobe capacity. The current app
still has **no enforced per-user garment quota**.

## 2. Proposed quota definition v1

Let A be the number of persisted `garments` rows owned by the authenticated user
whose status is not `archived`. Unknown/null non-archived status values count
conservatively rather than creating an exclusion loophole. Let N be the number of
distinct validated accepted candidates being inserted by this confirmation.

**Admit a new confirmation only when A+N <=100.** Remaining capacity is
`max(0,100-A)`. Over-limit means A>100. The count uses the owner ID from
authentication, never a client-provided count, category, eligibility result or
filtered wardrobe response. All categories and source ages have equal cost1.

Illustrative read query, not executed by this review:

```sql
SELECT COUNT(*) FROM garments
WHERE user_id = ? AND (status IS NULL OR status <> 'archived');
```

| Record/state | Consumes an active slot? | Proposed interpretation |
|---|---|---|
| Confirmed available garment row | Yes, once per garment ID | A linked processing item is not a second slot. |
| Active row with missing attributes, unsupported category, unconfirmed/NULL/dangling/foreign processing linkage, or unusable media | Yes | Do not derive usage from the strict recommendation query or silently certify these records. Later correction must not produce an uncounted active entry. |
| Temporarily unavailable/quarantined or other non-archived stored row | Yes | Availability changes cannot free/reacquire a slot outside the guard. Such extra status-edit workflows are not currently exposed. |
| Pending upload/media, queued/processing/review_required job | No | No reservation. Many jobs may compete for the same remaining slots; successful upload does not promise successful confirmation. |
| Pending/accepted/rejected processing candidate without a garment row | No | Count only the actual new entries at confirmation. A stray confirmed item without a garment is an integrity issue, not an extra usable entry. |
| Failed/cancelled/interrupted processing job or zero detections | No | No reservation to refund. Keep current failure/recovery semantics and media retention. |
| Archived garment row | No | Status archived is the quota discriminator. Normal archive sets deleted_at too; inconsistent timestamps are audited, not fabricated or rewritten. |
| deleted_at set while status remains non-archived | Yes | A timestamp alone must not bypass the guard or disagree with available-status queries. |
| Physically deleted row | No row to count | No new hard-delete/cleanup route is authorized. Existing history/media retention must not be weakened to free space. |
| Outfit/membership, saved recommendation, history or visualisation referencing an existing garment | No additional slot | Archiving an outfit alone does not free its constituent garments. |
| Future unarchive, import, standalone manual garment creation or owner transfer | Would consume a destination slot | Not current supported routes. Any later addition must use the same guard and transaction policy; owner transfers need agreed lock ordering. |

This means **at most100 non-archived stored wardrobe entries**, not100 lifetime
database rows. Archives, job/candidate records and media can make total retained
storage exceed100. Disk/media retention and pending-job resource limits are
different policies; no new limits/reservations or cleanup are proposed here.
For a compliant account, recommendation-eligible garments E satisfy E<=A<=100;
the converse does not hold. Missing evidence must not be changed to make E=A.

A literal limit of100 rows including archives would not release capacity after
the existing DELETE/archive action and would require a different retention/UX
decision. This contract recommends the active-entry definition explicitly; it
does not silently promise a limit on all retained historical rows.

## 3. Enforcement boundaries and atomic confirmation

1. **Authoritative:** add the count/guard to the common WardrobeWriter /
   `confirm_candidates` path, on its existing transaction connection. Every
   HTTP confirmation and ordinary application insertion must reach it. Route-
   only checks, a frontend check, a cached count or an in-process mutex are
   insufficient. The application currently has one production garment INSERT
   site here; processing creates candidates, not garments.
2. Retain authentication,1..100/distinct ID validation, owner/job readiness,
   accepted membership, embedding and preferred-media checks. Count A and N
   **inside BEGIN IMMEDIATE, before the first garment insert**, after identifying
   the valid complete selection. No quota helper opens a second connection,
   commits the caller's transaction or reads a strict-query eligibility subset.
3. If A+N>100, reject the **whole batch** with409; insert zero garments, zero
   outfit/items, change no selected-item confirmation status and do not complete
   the job. Keep it review_required so the owner can archive something or choose
   fewer candidates. No first-N saving, silent dropping or partial outfit.
4. Otherwise keep the existing insertion/representation/optional outfit/job
   completion transaction. Any later fault rolls everything back, including the
   effective quota usage. Recount on the next attempt; no separately maintained
   counter or schema migration is needed for this SQLite proposal.
5. **Advisory early upload check:** when A>=100, reject a new wardrobe-image upload
   before durable private media storage, job creation and background dispatch.
   Authentication still runs; HTTP multipart parsing/spooling may already have
   occurred, so this is not a promise to reject before receiving file bytes.
   If A=99, an image may be accepted even if it later yields several candidates.
   No slot is reserved and a race may fill the wardrobe meanwhile; confirmation
   remains authoritative. A second late upload gate after media storage is not
   needed to claim safety and could create avoidable orphan media.
6. Review, reading, ordinary edits, pending-job cancellation and existing-record
   outfit/recommendation actions remain available at quota. Old pending jobs can
   be reviewed at100; they cannot add garments until there is capacity. Keep
   upload image validation and processing/AI algorithms unchanged.

**Exact boundary cases:** 99+1 succeeds at100;99+2 fails at99;100+1 fails at100.
At0, a valid100-ID batch may succeed. A101-ID request is still a Pydantic422
batch-validation error, not the new409 total-quota error. Both save modes follow
the same guard. Future non-HTTP writers must share it; privileged direct SQL,
fixtures or maintenance scripts are outside an ordinary API guarantee and must
not be advertised as protected unless they adopt equivalent enforcement.
An aggregate per-user limit is not achieved by simply adding a per-row CHECK.

### Concurrent requests, retries and recovery

- Different jobs competing at A=99: only one N=1 confirmation may commit;
  the other must re-read100 and fail409. N=2 cannot partially win the single slot.
- Same job/duplicate click/lost response: preserve current at-most-once writes.
  Once completed, a repeated confirmation returns existing409; do not count its
  submitted IDs as new demand or overwrite the saved outfit. GET job followed by
  the wardrobe lets the UI reconcile the existing completed state. No automatic
  re-upload or replacement job after an ambiguous network response.
- This minimum proposal does **not** promise201 replay of the original response.
  Current persistence has no durable confirmation receipt binding ordered IDs,
  save mode/name and returned outfit ID. Do not guess an original outcome by
  searching current outfits or infer replay identity from mutable rows. Stronger
  replay would require separately approved persisted receipt/schema semantics.
  Existing recommendation submission-key replay is independent and unchanged.
- A failed quota check leaves no receipt/job completion; the same valid job can
  be retried after space is freed. A failed insert/commit rolls back; retry must
  revalidate job state, ownership, candidate IDs and A on a fresh transaction.
- Existing archive already uses BEGIN IMMEDIATE and dependency checks. Release
  a slot only after its commit. If confirmation wins the write lock first it may
  fail for full capacity; an archive-first ordering may allow it. Both outcomes
  are valid. Do not merge archive+replacement into a new atomic endpoint or
  automatically archive dependent garments. The safe minimal workflow is an
  explicit archive, then confirmation; replacement can still lose a race.

## 4. Proposed HTTP and frontend contract

Add authenticated **GET `/api/v1/wardrobe/quota`**, separate from the existing
list response. Return a private, non-cacheable snapshot (not a reservation):

```json
{
  "policy_version": "wardrobe-active-entries-1.0.0",
  "scope": "non_archived_garment_entries",
  "limit": 100,
  "used": 99,
  "remaining": 1,
  "over_limit": false,
  "pending_reserved": 0
}
```

All numbers derive from the same owner count; use `Cache-Control: private,
no-store`. Do not accept an owner ID override or count filters. Pending_reserved
is always0 for this no-reservation policy, not a newly allocated resource.

Proposed quota-conflict409 using the existing FastAPI error envelope:

```json
{
  "detail": {
    "code": "WardrobeQuotaExceeded",
    "stage": "confirmation",
    "message": "You have 99 of 100 active garments and selected 2. Archive at least 1 garment or select fewer candidates.",
    "limit": 100,
    "used": 99,
    "remaining": 1,
    "requested": 2,
    "over_limit": false
  }
}
```

For early upload use stage=`upload`, requested=`null` (photo yield is unknown),
and message `Your wardrobe is full (100/100). Archive a garment before adding
another image.` At A>100 report the actual usage and how many removals are needed
for the intended batch. Keep401/404 ownership protection,422 validation and409
job/dependency errors distinct; never call lock contention a quota conflict.
These are **proposed new responses**, not current API behaviour.

Frontend requirements, pending teammate/shared approval:

- Show `Active garments: 99 / 100 — 1 space left` independently of search,
  category/favourite filters and pagination. Explain that non-archived unavailable
  or unverified entries count, pending jobs do not reserve space and archives
  release it. Do not use `garments.length` as this indicator.
- Load/refresh quota on wardrobe/upload/review entry, return-to-tab, successful
  confirmation/archive, and any quota conflict. Update an accessible live status;
  keep refresh UI lightweight and avoid new recommendation calls.
- At zero remaining, disable the ordinary Add image action with an explanation
  and wardrobe link; retain read/edit/dependency-preview/archive controls. Direct
  navigation/API calls remain protected by the backend. If the count cannot be
  loaded, display `Capacity unavailable` and allow a refresh; do not invent0/100.
  The final confirmation guard remains authoritative for stale or missing UI data.
- Show candidate selection demand versus remaining before confirmation. The
  current results page sends all accepted IDs. **Propose explicit save-selection
  checkboxes among already accepted candidates**, without changing their review
  evidence or auto-rejecting candidates. Disable both save modes when selected
  demand exceeds the latest remaining value or when existing dirty-review/name
  requirements are unmet. Do not silently trim a batch to fit.
- Preserve the existing job-finalisation rule and disclose it before a subset
  save: `Only these selected garments will be saved. This completes the job;
  unselected candidates will not be saved.` No automatic continuation or partial
  confirmation is introduced. If this small selection UI is not approved, keep
  all-accepted saving and provide a capacity warning/archive-and-retry path;
  do not pretend a selection control already exists.
- On409 keep edits, accepted decisions, selection, name and job reference. Show
  the server message/count and offer smaller selection or open wardrobe; fetch
  fresh capacity after returning. Reconcile completed jobs on lost responses
  rather than creating duplicates. Archive dependency failures retain their
  existing explanation and release no slot.
- `frontend/lib/api.ts` currently understands string detail/Pydantic arrays,
  not the proposed nested detail.message/code. Add a narrowly typed quota/error
  branch preserving all existing authentication/recommendation/error handling.
  Do not accidentally replace a quota message with the current generic fallback.

## 5. SQLite concurrency and future PostgreSQL

**SQLite now:** the current provider named `postgresql_repository.py` is sqlite3,
with foreign keys enabled and context-managed commit/rollback. The authoritative
count must occur after BEGIN IMMEDIATE on that connection, so competing writers
to the **same database file** cannot slip an insert between count and commit.
This coordinates threads/processes; a Python lock or frontend button does not.
Archive already uses the same writer transaction. Keep it short: no upload/AI,
GPU wait, model inference or external network work inside it. SQLITE_BUSY/lock
acquisition failures must fail closed with no partial state; propose a controlled
retryable503 mapped by the shared adapter/API boundary after rollback. Keep
existing bounded driver waits unless separately approved; never retry only the
failed INSERT or turn infrastructure failures into `WardrobeQuotaExceeded`.
SQLite documents a single simultaneous writer and BEGIN IMMEDIATE's early write
transaction semantics in its [transaction reference](https://www.sqlite.org/lang_transaction.html).

**PostgreSQL if later implemented:** BEGIN IMMEDIATE is not portable, and
COUNT-then-INSERT alone can race. With an actual provider at READ COMMITTED,
every quota-changing writer must first lock the same existing authenticated
account row using SELECT FOR UPDATE, then execute the count as a **subsequent
statement after acquiring that lock**, revalidate and insert within the same
transaction. Locking only a job or existing garment rows cannot protect two
different jobs or future rows; an aggregate count is not a lockable account row.
Use consistent account-before-job/member lock ordering across confirm/archive/
future restore/import/transfer. Plain row locks plus a stale repeatable-read
snapshot are not this design; alternative SERIALIZABLE execution needs bounded
whole-transaction retry on serialization failure. See PostgreSQL's
[row locking](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS)
and [isolation documentation](https://www.postgresql.org/docs/18/transaction-iso.html).
No PostgreSQL adapter, schema mapping, locking or migration is certified here.
Its eventual owner/provider decision remains separate from this SQLite proposal.

No new schema/counter table is required for count-based SQLite enforcement.
Database-wide protection against privileged writers, a durable confirmation
receipt, or a PostgreSQL adapter would be separately scoped work, not silently
added to this quota implementation.

## 6. Proposed tests (NOT RUN in this review)

| Case | Required result |
|---|---|
| A=99,N=1; A=98,N=2 |201; exactly100 active rows, complete selected membership and optional outfit. |
| A=100,N=1 via direct confirm API and writer |409quota conflict; no new rows/status change. A job accepted before the account became full must not bypass it. |
| A=99,N=2 and larger batches crossing100 |Whole batch409; no partial garment, outfit or membership; job remains review_required, candidates accepted. Cover both save modes. |
| A=0,N=100;101 IDs;empty/duplicate IDs |100valid IDs allowed if normal validation passes;101/empty/duplicates remain422 at HTTP boundary. Preserve the separate batch contract. |
| Two different jobs, A=99,N=1 each |Two independent connections/processes race;201+409,final100. At98 with N=2 each,201+409,final100. Coordinate the barrier before lock acquisition, not inside both write transactions. |
| Same-job concurrent/serial repeats, changed IDs/mode/name, lost response |One insertion/outfit only; existing completed-job409 on later calls; owner GET reconciliation works, no quota double charging or guessed201 replay. |
| Inject fault after first/last garment, representation, outfit item, status update and commit |All writes roll back; A unchanged, job/candidates retryable; repeat after removing the injected fault succeeds once. |
| Pending/accepted/rejected/failed/cancelled jobs at99/100 |No usage charge/reservation/refund. Full-upload precheck creates no media/job/task; a pre-existing pending job can still be reviewed/cancelled. One image yielding several candidates must use selected N. |
| Successful archive at100 then N=1; archive dependency failure |Archive commit ->99,confirm ->100. Blocked archive remains100; no forced removal, inference cancellation or altered history. |
| Archive vs confirmation race |Only transaction-order-consistent outcomes; final<=100 for compliant accounts. No early optimistic capacity release. A replacement may require a user retry. |
| Multiple outfits/history/recommendations reference one garment |Count once; saving another outfit at100 remains allowed. Outfit archive alone does not free the garment. Old immutable snapshots/availability notices remain unchanged. |
| Archived rows, deleted_at-only row, unavailable/unverified/unsupported-category rows |Archived status excluded; deleted_at alone/non-archived states count. E may be less than A without increasing capacity. No NULL-link trust or eligibility-policy change. |
| Foreign owner/job/item/media, unauthenticated quota request |Existing401/404/validation protection; no foreign counts or writes. A second user's entries do not consume the first user's slots. |
| Client-supplied count/status or filtered listing, two tabs |Cannot manipulate usage or bypass the writer; quota indicator independent of filters. Stale UI gets409 and preserves review. PATCH cannot create a slot by an unsupported status field. |
| Busy/commit failure/restart |No false quota conflict, no success before commit, no slot drift; bounded controlled retryable failure. Test through actual independent DB connections, not only mocks. |
| Seeded pre-existing A=101 |No automatic deletion/truncation. Report used101,remaining0,over_limit=true; block additions. Reads/valid edits/archives remain available. Releasing one slot gets100, still no room for N=1 until a second is released. |
| Frontend selection/errors |Accessible counts/full/loading states, nested409 message, both save modes, explicit subset-finalisation notice, no automatic candidate dropping/re-upload. Preserve existing review/style/null/If-Match controls. |

Reuse `test_garment_workflow.py`'s real duplicate-confirm and injected-outfit-fault
patterns, `test_o1_wardrobe.py` archive dependencies and owner isolation, and
historical/recommendation-action regressions. Add focused quota tests rather than
rerunning capacity matrices. Real PostgreSQL concurrency tests are required only
if that provider is separately implemented; SQLite tests cannot stand in for them.

## 7. Exact proposed file and approval boundary

Ownership below follows the user's Digital Wardrobe ownership statement and the
workflow handoff, not an inferred Git author. **No file below is authorized for
implementation by this planning request.**

| File | Proposed touch / approval needed |
|---|---|
| `backend/app/application/wardrobe/wardrobe_service.py` | **Teammate-owned; required.** One central policy/count projection and transaction-bound confirmation guard. Retain archive checks/semantics; no new archive operation required. |
| `backend/app/api/wardrobe_routes.py` | **Teammate-owned; required.** Owner-authenticated quota GET; existing garment list response unchanged. |
| `backend/app/api/garment_processing_routes.py` | **Teammate-owned processing boundary; required for proposed early admission.** Upload precheck before durable media/job dispatch; confirmation still delegates to the guarded writer. |
| `frontend/app/wardrobe/page.tsx` | **Teammate-owned; required.** Unfiltered capacity indicator, full-state Add feedback and refresh after committed archive. |
| `frontend/app/extract/page.tsx` | **Teammate-owned; required.** Capacity preflight/full-state display while retaining image validation. |
| `frontend/app/extract/results/page.tsx` | **Teammate-owned; required.** Quota demand/error display and refresh; explicitly approve the proposed accepted-candidate save-selection controls/subset notice. |
| `frontend/lib/api.ts` | **Shared frontend contract; teammate+owner approval.** Typed quota GET and nested quota-error parsing without regressing other API callers. |
| New `backend/tests/test_wardrobe_quota.py`, `frontend/tests/wardrobe-quota.spec.ts` | **Teammate/shared testing approval.** The boundary/concurrency/UI matrix above; disposable fixtures, no production data. Existing `test_garment_workflow.py` and `test_o1_wardrobe.py` should be reused unchanged where possible; edits need explicit test ownership approval. |
| `backend/tests/integration_source_guard.py` and a new `backend/tests/fixtures/wardrobe_quota_sources.v1.json` | **Shared integration-owner approval if frozen paths change.** Add a narrowly scoped before/after transition for approved files; preserve every old manifest/reference archive and assertions. No broad hash repinning. |
| `backend/app/infrastructure/persistence/postgresql_repository.py` and `backend/app/application/ports/workflow_runtime.py` | **Shared provider/port; conditional explicit approval.** Only if needed for a neutral transient-storage failure/controlled503 mapping. Keep quota logic in the wardrobe service, not a concrete adapter import; no schema migration/provider rewrite implied. Route handling for that mapping must be agreed with API owners. |

Inspected but **no production edit expected** in the minimal proposal:
`review_service.py`, `processing_job_service.py`, `garment_processing_orchestrator.py`,
`upload_validator.py`, `confirmed_garment_writer.py`, `requests.py`,
`confirmed_garment_query_adapter.py`, `confirmed_garment_snapshot.py`, protected
media, recommendation algorithms/selectors/actions, visualisation, CV/VTON and
composition flags. Existing100-ID schema validation stays intact. A new policy
module/configuration file is not required; if the teammate prefers one, add its
exact path/scope to approval before implementation. No schema, migration, package,
model, processing payload or authentication changes are authorized here.

## 8. Readiness and release gates

**Contract/design ready for owner and teammate review; implementation not yet
authorized.** Obtain explicit agreement on active-vs-lifetime counting, archives
releasing capacity, no pending reservations, whole-batch rejection, current409
retry semantics, response/selection UX and the exact file boundary above. This
does not reopen the accepted100 proposal or request another capacity experiment.

Before eventual activation, perform a separately approved **read-only account
inventory** of actual non-archived counts, over-limit users, unusual statuses,
archive timestamps and active unverified rows. No private/deployment database was
opened for this review. Preserve any existing account above100; block additions,
provide honest counts and let owners resolve capacity through the normal approved
archive workflow. Do not mass-archive, rewrite provenance, invent confirmation
links or alter history. Until over-limit accounts are resolved, a new-write guard
does not retroactively prove A<=100 for every existing account; those populations
are outside J-10's tested capacity and must not be silently certified or pruned.
Unusual non-visible status rows cannot necessarily be archived through today's
available-only endpoint. If inventory finds them, the teammate must agree an
explicit recovery/support workflow before rollout; neither invent an availability
transition nor hide their quota consumption from affected owners.

After teammate approval, implement only the narrow guard/API/UI contract, run the
focused tests and relevant shared regressions, document exact source transitions
and review the concrete result before deployment. PostgreSQL commitment,
experimental/default suitability activation, formal NFR-02 baseline and final FYP
acceptance remain separate decisions. No tests, benchmarks, migrations, inference,
quota implementation or runtime/default activation are performed in this review.

**Scope verification:** existing application, tests, packages, prior reports and
J-6/J-7/J-8/J-9/J-10 evidence are checked by before/after hashes for this review.
Only this new document is created; a repository diff/whitespace check is performed.
J-10 remains owner-closed; no new implementation phase starts. Wait for owner and
teammate review.
