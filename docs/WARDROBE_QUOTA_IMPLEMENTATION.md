# Phase 5F-2E-3J-11: 100-garment wardrobe quota implementation and verification

2026-10-23, Asia/Kuala_Lumpur. Owner/teammate-approved implementation of
`WARDROBE_QUOTA_CONTRACT.md`. **PASS WITH LIMITATIONS; ready for owner review.**
J-10 remains owner-closed PASS WITH LIMITATIONS. The accepted capacity remains
100. No capacity experiment was run. NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.

## Authority and implemented semantics

Before editing, the owner explicitly confirmed teammate and owner approval for
the seven application files in the contract, focused quota tests, the narrow
source-guard transition and this report. Accepted-candidate subset selection and
its job-completion notice were separately explicitly approved. The accepted
contract supplies the remaining decisions: count non-archived stored entries,
archives release capacity, pending jobs reserve nothing, whole-batch rejection,
unchanged 100-ID validation and unchanged completed-job retry behaviour.

Usage is the count of authenticated-owner `garments` rows with status NULL or
anything other than exactly `archived`. All categories, unavailable/unverified
entries and non-archived rows with a deleted timestamp count. Pending media,
jobs and processing candidates consume no slots. Outfits/history/recommendations
referencing a garment do not consume additional slots. Retained archive rows can
make lifetime storage exceed 100. Recommendation eligibility remains narrower
than quota usage and its query/policy is unchanged.

For current usage A and a fully validated selected batch of N candidates,
confirmation succeeds only when A+N <=100. In `confirm_candidates`, the count
occurs on the same connection after the existing `BEGIN IMMEDIATE`, owner/job/
accepted-candidate/media validation and before the first garment insertion.
There is no cached counter, reservation, new schema or second count connection.
The existing transaction still commits garments, representations, confirmed
items, optional outfit/members and job completion together. A quota conflict
raises before these writes; later faults use the existing rollback mechanism.

At 99, one accepted garment succeeds and a two-garment batch fails entirely.
At 100, another confirmation fails with HTTP409 `WardrobeQuotaExceeded`,
stage `confirmation`; no selected items become confirmed and the job remains
review_required. A 101-ID request still fails with its existing Pydantic422
validation before the service. Both save modes use the same guard. Ordinary
direct application writer calls are also guarded.

An account already above100 retains all rows and can read/edit/archive through
existing supported paths, but cannot add entries. At101, archiving one reaches
100 and still leaves no free slot; a further successful archive is needed before
adding one. No record was automatically archived, relabelled or removed.

## API and frontend

Authenticated `GET /api/v1/wardrobe/quota` returns:

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

The response has `Cache-Control: private, no-store`; the frontend also requests
`cache: no-store`. Owner identity comes from authentication; count filters or a
client owner override are not accepted. Remaining is clamped to zero, while
actual over-limit usage is disclosed accurately.

Quota conflicts use the existing error envelope with a typed `detail.code`,
stage, explanatory message, the quota fields and `requested`. Upload conflicts
have stage `upload` and requested null because image yield is unknown. At full
capacity, the advisory upload guard executes before durable media storage,
job creation and task dispatch. HTTP multipart parsing/spooling can already
have happened. Successful upload reserves nothing; a later competing
confirmation can consume capacity, so confirmation always recounts.

Wardrobe, upload and review pages show unfiltered capacity separately from the
filtered collection count. They refresh on entry, explicit refresh and return
to a visible tab/window. A successful archive refreshes capacity after commit;
a quota conflict also refreshes it. Sequence checks prevent an older count
request replacing a newer response. Count-fetch failure shows `Capacity
unavailable`, preserving the authoritative server guard. Full/over-limit UI
disables ordinary Add/upload actions and points owners to archive management.

Accepted candidates initially remain selected. Owners can explicitly deselect
individual accepted candidates without changing review evidence. Both save modes
are disabled if selected demand exceeds the last known remaining count, or the
existing dirty-review/name constraints fail. The notice explicitly states:

> Only these selected garments will be saved. This completes the job;
> unselected candidates will not be saved.

A stale-capacity409 preserves selection, candidate review and outfit name,
displays the server message and refreshes quota. An ambiguous failed transport
response triggers a job read, never another confirmation or upload. If the first
write committed, the UI shows the completed job. Existing completed-job retries
still return409; no durable receipt or201 replay was invented. Quota-error
parsing is restricted to the new typed409; unrelated API error handling remains.

## Files and ownership

Only these seven approved application files changed in J-11:

| File | Change |
|---|---|
| `backend/app/application/wardrobe/wardrobe_service.py` | Central100 policy/count projection, advisory admission and authoritative transaction-bound confirmation guard. Teammate-owned. |
| `backend/app/api/wardrobe_routes.py` | Authenticated non-cacheable quota GET. Teammate-owned. |
| `backend/app/api/garment_processing_routes.py` | Advisory upload admission before media/job creation. Teammate-owned. |
| `frontend/app/wardrobe/page.tsx` | Independent capacity status/full Add state and committed archive refresh. Teammate-owned. |
| `frontend/app/extract/page.tsx` | Capacity/full upload controls, management link and error refresh. Teammate-owned. |
| `frontend/app/extract/results/page.tsx` | Capacity-aware explicit subset selection, completion notice and failed-response reconciliation. Teammate-owned. |
| `frontend/lib/api.ts` | Quota type/GET/text formatter and typed quota-message parsing. Shared. |

Supporting changes: new `backend/tests/test_wardrobe_quota.py`, disposable
`backend/tests/frontend_quota_server.py`,
`frontend/tests/phase5f/wardrobe-quota.spec.ts`,
`frontend/playwright.wardrobe-quota.config.ts`,
`backend/tests/fixtures/wardrobe_quota_sources.v1.json`, the explicitly approved
`backend/tests/integration_source_guard.py` extension, this report and
`storage/verification/phase5f2e3j11/` artifacts. The browser test uses the existing
phase5f isolation convention so a normal suite cannot accidentally run its
special fixture against another server. Test-only fixture mutation endpoints
exist solely in the disposable loopback server, never in application sources.

All prior manifests and frozen reference archives remain unchanged. The new
manifest records explicit before/after hashes for exactly the seven approved
application paths. The source guard follows the original transition chain,
checks every new hash and keeps all historical assertions. The phase patch is
relative to the captured starting workspace, which already contained earlier
uncommitted work; it does not attribute all current Git changes to J-11.

No provider/port, migration, request schema, authentication, recommendation
algorithm/query/scorer, model, visualisation implementation or release flag/
default changed. Compact/deferred remain defaults; suitability remains opt-in
and approximate hex remains disabled. Earlier Digital Wardrobe style/tag and
saved-outfit validation corrections remain intact.

## Concurrency and rollback evidence

SQLite's existing `BEGIN IMMEDIATE` serializes writers to the same database file
before quota counting. Two jobs do not rely on a shared in-process mutex or job
lock. Tests coordinate a barrier before HTTP confirmation; the actual service
opens independent SQLite connections and counts after acquiring its write lock.

`concurrency-final.jsonl` retains both request/response pairs and final counts:

| Starting usage | Competing batches | Result | Final usage |
|---:|---|---|---:|
|99|Two different jobs, one garment each|201 and typed409|100|
|98|Two different jobs, two garments each|201 and typed409; no losing partial batch|100|

Additional tests cover concurrent same-job201/409 and subsequent changed-batch/
mode retry without another write; an archive/confirmation race with either
valid commit order; rollback after a second-garment failure, after outfit-member
insertion failure and at job completion; and successful retry after removing
each injected fault. Existing blocked-archive dependency behaviour releases no
slot, while committed archive releases one and leaves its historical row.

This evidence uses real SQLite connections/transactions in one test process,
not an OS multi-worker deployment test. A PostgreSQL implementation would need
its own account-level serialization/locking and database-specific tests;
SQLite's count-after-BEGIN-IMMEDIATE guarantee is not transferred to it.

## Executed verification

Exact commands and logs are retained in
`storage/verification/phase5f2e3j11/commands.txt`. No timing run or inference was
used; detectors and VTOFF in tests are explicitly synthetic/development fixtures.

| Check | Result |
|---|---|
|Initial focused quota tests|21 passed; initial concurrency ledger retained.|
|Shared backend regressions|375 passed, including initial quota cases, normal garment/review workflow, archives, style, suitability controls, saved-outfit eligibility, recommendation/history/save and source guards.|
|Final quota/workflow/VTON/source-guard run|35 passed, including25 quota cases with the added direct-writer, partial rollback and archive-race checks. Runs overlap; totals are not added as distinct tests.|
|Initial quota browser checks|5 passed on actual API/disposable SQLite.|
|Existing browser regressions|54 passed, including actual login/Homepage/Assistant/history/save/archive and style/suitability-control flows; `browser-regressions.log`.|
|Final quota browser checks|6 passed against the isolated production build and actual backend; includes the lost-response case and final test location/configuration; `browser-quota-final.log`.|
|Isolated production build|Passed; `build.log`. This was a functional build check, not latency collection.|
|Final TypeScript|`npx tsc --noEmit --incremental false` passed using restored original configuration; `types-final.log`.|
|Final lint|Passed, zero errors and two existing navigation warnings; `lint-verified.log`.|
|Source guard/integrity|Frozen-source guard passed in both backend regression runs.785 pre-existing hashes checked:776 unchanged,8 approved source/helper changes,1 explicitly recorded ignored compiler-cache change; `integrity.json`.|
|Whitespace|`git diff --check` passed; explicit whitespace validation also covers new untracked source/test/report files.|

The quota tests cover99/100/101, both save modes, valid100-ID and invalid101-ID/
empty/duplicate requests, different/same-job concurrency, direct writer calls,
rollback/retry, archive and dependency failures, above-limit preservation,
unavailable/archived/deleted-timestamp rows, owner isolation, authentication,
private/no-store response and full upload admission before media/job dispatch.
Frontend checks cover unfiltered usage, archive refresh, full/over-limit states,
subset membership/job finalization, stale-capacity errors preserving selection/
name, unavailable-count recovery and lost successful-response reconciliation.

Initial lint exposed three new effect warnings treated as errors; the effects
were corrected. The subsequent lint run passed with only the two existing
internal-navigation warnings. No policy/test oracle was weakened. Tooling-only
corrections (unsupported local Python text-write option and an integrity-script
ancestor path) are recorded in commands; no failed source hash was repinned.
The existing browser run also logged a protected-media proxy ECONNRESET; all54
tests passed. That log is retained without treating the warning as a new test
failure or suppressing it. Next-generated `tsconfig.json` and `next-env.d.ts`
were restored to byte-identical starting hashes after verification. The ignored
`tsconfig.tsbuildinfo` cache was regenerated and is explicitly separated from
application changes in the integrity result.

## Remaining limitations and release boundary

- No private/deployment database was inventoried or modified. Before deployment,
  perform the separately approved read-only account/status inventory from the
  contract. Existing above-limit accounts must be preserved and resolved through
  agreed management/support workflows. Non-visible unusual statuses may require
  teammate support; this change adds no status transition or restoration route.
- Pending uploads reserve no slots and have no new job/media storage quota.
  Many in-progress jobs can compete; upload admission is advisory. Privileged
  direct SQL and later import/restore/owner-transfer writers require equivalent
  guards; this is an ordinary application/API guarantee.
- The existing SQLite provider, bounded lock waits and infrastructure-error
  behaviour remain unchanged. Lock/commit failures are not mislabeled as quota
  conflicts. The optional shared provider/port503 translation was outside the
  seven approved application files and was not added; no new controlled503 or
  receipt-based retry guarantee is claimed. Commit-failure/OS restart fault
  injection and actual PostgreSQL/multi-process deployment certification were
  not performed in this phase.
- Archive dependencies, confirmed evidence, historical retention and completed
  job409 retries remain as before. Subset confirmation intentionally completes
  the job; discarded selection is not a resumable later confirmation workflow.
- No capacity benchmark, scoring/suitability activation, default change, database
  provider switch or historical rewrite occurred. NFR-02 is formally unaccepted;
  J-10 capacity evidence remains under its original conditions and limitations.

## Final recommendation

**PASS WITH LIMITATIONS.** The approved100-active-entry quota, advisory upload
admission, private capacity endpoint and subset-confirmation UI are implemented
and verified. Different-job concurrency cannot overfill the tested shared SQLite
file, quota/write failures are atomic, and shared regressions pass. This is
implementation readiness for owner review, not a deployment/inventory or final
FYP acceptance decision. All old source manifests, frozen reference archives,
captured prior reports and J-6/J-7/J-8/J-9/J-10 artifacts retain their hashes.
Exact changes, before copies, commands, raw concurrency responses, logs and
deliverable hashes are retained in `storage/verification/phase5f2e3j11/`.

NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. No next phase starts. Wait for owner
review.
