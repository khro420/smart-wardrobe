# Phase 5F-2E-3J-1: saved-outfit visualisation eligibility

2026-10-22, Asia/Kuala_Lumpur. Implementation and verification report.
Status: **PASS WITH LIMITATIONS - ready for owner review / Phase3J-1 closure**.
No later phase or activation is authorised.

## Authority and implemented scope

Original Project I FR-VIS-04 (PDF176 / printed165) requires current source
resolution and rejection of missing, duplicate, unowned, deleted, unavailable,
unconfirmed or otherwise unsupported garments. The PDF was re-read directly;
SHA256 5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669.
The owner approved the narrow shared VIS correction in the Phase3J closure.
Closed `FUNCTIONAL_SCOPE_SCORING_DECISION_PACKET.md` and
`FINAL_ACCEPTANCE_READINESS_REVIEW.md` are retained historical reviews.

Only two production files change. No query contract, persistence adapter,
wardrobe writer, frontend, model, schema, routing, scoring or default changes.
Compact/deferred remain defaults; suitability stays opt-in and approximate
hex matching disabled. Outerwear remains unsupported by VTON.

## Before and after

Previously saved-outfit resolution checked current ownership/availability but
could accept NULL links or accepted processing items, and did not prove the
processing-job owner. Only recommendation sources were re-resolved at claim.

Saved-outfit resolution now calls the injected transaction-bound Phase1 query
once on the caller's connection. Every stored member must be returned by that
strict query. No member is dropped. A complete unique 1..N ordering and supported
role are required. Existing wardrobe roles top/bottom/dress and existing saved
recommendation roles upper/lower/one_piece/garment/accessory are permitted;
category-based VTON mode validation remains authoritative for supported classes.
These labels do not predict garment roles or impose recommendation compositions.
Multiple tops remain supported; outerwear cannot be hidden behind a generic role.
The recommendation branch keeps its existing strict_items and role rules.

Queued saved outfits now use the same pre-inference source resolution and exact
ordered tuple comparison as recommendations: garment ID, preferred media ID,
category, role and order, including count. Replaced/missing members, reordering,
category/role/media changes or loss of strict eligibility fail before inference.
The job still uses its stored configuration, not current runtime defaults.

## Confirmation proof and disposable inventory

Accepted proof is an available owned garment linked to an existing confirmed
processing item whose existing job has the same owner. No job-status or age rule
is added. The genuine upload/review/confirm operation provides this proof;
manual assembly of existing garments does not independently confirm them.
No standalone garment attestation/create route was found in the inspected APIs.
Older linked records remain eligible if the same proof remains valid.

Before production editing, a read-only inventory joined the existing disposable
API-created records. `inventory.json` contains four memberships in two outfits:
one image-upload outfit and one manually assembled outfit referencing the same
two genuinely confirmed garments. All four have independently query-verifiable
confirmed-item/job-owner relationships. The read-only inventory test passed
before edits. Additional tests inventory a deliberately unlinked disposable
member and verify it remains absent from strict query results.

This is NOT an inventory of the deployment database or a natural population
sample. Synthetic detector images are used to exercise the actual review and
confirmation API; no valid confirmation links are fabricated by SQL. Negative
cases deliberately corrupt disposable records. Missing-garment/job and duplicate
cases explicitly bypass test-DB integrity protections to simulate legacy damage;
application foreign-key enforcement and schemas are unchanged.

NULL/dangling/missing links, accepted/pending/rejected items and foreign job
ownership fail closed for new visualisations. Existing records, saved outfits
and historical recommendation data remain untouched. Remediation requires the
owning developer/user to perform genuine supported review/confirmation, or a
separately approved auditable legacy/manual trust workflow. Do not create fake
links, mass-backfill statuses or rewrite historical records. Reprocessing into a
new genuinely confirmed garment and an explicit owner edit of the outfit is a
possible supported replacement workflow; it does not attest the original record.
A linked accepted legacy garment may conflict with the existing unique processing
link during confirmation, so do not promise a blind confirm retry repairs it.
Any in-place legacy repair/attestation needs the owning developer's separate plan.

## Transactions and inference safety

Preparation uses a read transaction. Creation independently re-resolves inside
its existing BEGIN IMMEDIATE transaction, before request/items insertion.
Invalid sources insert nothing; an injected failure on the second item rolls
back the request and first item together.

GPU waiting still occurs before the claim transaction. Claim, strict resolution
and frozen/current comparison run under the short SQLite write transaction.
Failure rolls the claim back; the existing failure handler marks the queued job
failed/unprocessable without invoking the adapter. The source snapshot remains
stored for traceability. Successful claim commits before reading images and
calling inference. Tests use independent SQLite writer connections to prove
competing source writes are blocked during create/claim, and possible during GPU
waiting and inference. A committed source change during GPU waiting is caught.

This guarantees validation at the committed pre-inference claim boundary; it
does not lock the wardrobe for the entire subsequent model run. No transaction
is held across GPU waiting or generation. PostgreSQL locking, deployed workers
and real GPU/model quality are not certified by these SQLite/fake-adapter tests.

## File inventory

| File | Purpose |
|---|---|
| `backend/app/application/visualisation/outfit_identifier_validator.py` | Strict saved-outfit eligibility via injected transaction query; ordered membership and supported roles. |
| `backend/app/application/visualisation/outfit_visualisation_service.py` | Extend existing queued snapshot comparison to saved-outfit sources. |
| `backend/tests/test_saved_outfit_visualisation_eligibility.py` | Actual API-confirmed fixture, inventory, invalid sources, stale snapshots, rollback, concurrency and fake-inference safety. |
| `backend/tests/integration_source_guard.py` | Chain the explicitly approved two-file hash transition without modifying historical pins. |
| `backend/tests/fixtures/saved_outfit_visualisation_sources.v1.json` | Exact before/after hashes for only the two authorised production files. |
| `docs/SAVED_OUTFIT_VISUALISATION_ELIGIBILITY.md` | This policy, verification and limitations report. |
| `docs/REPORT_TRACEABILITY.md` | Append current FR-VIS-04 evidence without revising earlier evidence. |

Verification artifacts are under `storage/verification/phase5f2e3j1/`, including
before hashes, original two source backups, read-only inventory, PDF extraction,
exact commands, raw initial/final test logs and integrity results. Browser
artifacts use the distinct ignored `.next-integration-run/saved-outfit-eligibility-artifacts`
location. All earlier evidence and frozen archives are preserved.

## Verification

All planned applicable checks have completed. Exact full commands are recorded in
`storage/verification/phase5f2e3j1/commands.txt`.

Initial focused run: 88 passed / 2 failed, retained as `focused-initial.log`.
Both failures were test setup attempting a referenced garment deletion with
foreign keys enabled. Explicit disposable-corruption setup corrected those tests;
no production code was changed in response. Final focused run: **97 passed**,
33.06s, one existing Starlette/httpx deprecation warning. Pre-edit inventory:
**1 passed**, 1.97s. Focused tests use real SQLite and protected media plus actual
review/confirmation; inference-specific tests explicitly use a fake adapter.

## Remaining boundaries

No real CV/VTOFF/VTON inference was run; development detector/output fixtures
establish contract behaviour only. Outerwear/model acceptance and deployment
validation remain separate. No deployment data audit, migration or data repair
was performed. Unproven records remain stored but cannot start a new VIS job.
The known ai-services architecture assertion remains separate.

No RN-13 controls, RN-17 activation, DB-provider work or performance benchmark
was started. Formal NFR acceptance and final FYP acceptance remain open.

### Retained first broad run and source-integrity correction

The first broad suite reported **1,853 passed / 2 failed**, 194.96s. One failure
was the known ai-services architecture assertion. The other was the compact
archive test calling `integrated_digest` directly: the initial new transition
was only chained through `approved`. The test helper now chains the same exact
two-file transition for both entry points. No archive, old manifest, assertion
or production code was changed to resolve it. Targeted frozen-reference test:
**1 passed**, 1.99s. The full rerun is retained separately as `backend-final.log`.

Existing browser regression command: **35 passed**, 2.3m. This includes real
backend authentication, upload/review/confirmation, save/history/source actions
and UI controlled outcomes; some UI-state tests deliberately mock transport.
It is not real GPU/model evidence or an NFR timing run. Browser-generated
isolated-build include entries in tsconfig were semantically checked and the
captured original bytes restored. No frontend source/configuration change remains.

### Final verification results

| Check / command suffix (backend prefix is pinned in commands.txt) | Result |
|---|---|
| Pre-edit read-only inventory test | 1 passed, 1.97s. |
| `tests/test_saved_outfit_visualisation_eligibility.py tests/test_recommendation_actions.py tests/test_historical_recommendation_actions.py tests/test_workflow.py tests/test_vton_contracts.py -q --tb=short` | **97 passed**, 33.06s. |
| `tests/test_compact_exhaustive.py::test_frozen_reference_and_current_sources_remain_intact -q --tb=short` | 1 passed, 1.99s after helper correction. |
| `tests --ignore=tests/test_segmentation_geometry.py -q --tb=short` | **1,854 passed, 1 known failure**, 149.03s; pytest exit 1. |
| `npx playwright test --config playwright.integration.config.ts --output .next-integration-run/saved-outfit-eligibility-artifacts` (frontend) | **35 passed**, 2.3m; exit 0. |
| `git diff --check` (repository root) | **Exit 0**; existing line-ending warnings retained. |

The sole remaining failure is
`tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`,
line28, asserting the existing ai-services directory must not exist. The folder
and assertion are unchanged. The new transition passes frozen reference/current
source checks. Initial focused and broad failures remain in their original logs.
No new application regression was reproduced.

The dedicated CV geometry suite is excluded because it requires its separate
CV/torch environment; no CV code changed. TypeScript, ESLint and production build
were not repeated: no frontend/package change is part of this backend correction;
the existing applicable browser regressions were run. No actual GPU inference,
deployment restart, production data inventory or PostgreSQL verification occurred.

Integrity: **295 pre-existing files checked** against the pre-phase snapshot.
Only the two authorised production files, the test guard and appended traceability
changed among those files. **All 38 pre-existing fixture/archive files** are
byte-identical. Captured frontend app/components/package/lock/AGENTS/tsconfig,
all other app modules and the closed Phase3H/I/J reports are unchanged. New files
are the focused tests, two-file transition manifest and this report. New-file
whitespace checks passed as well. Exact evidence is `integrity.json`,
`application.diff`, `before.json` and `deliverables.json` in the phase folder.

### Closure assessment and FR-VIS-04

**Ready for owner closure as PASS WITH LIMITATIONS.** FR-VIS-04's identified
saved-outfit eligibility and queued-snapshot gap is functionally corrected and
verified for the existing supported VTON contract. Both source types now require
current trusted confirmation, complete validated membership and pre-inference
snapshot consistency. Valid manual assembly and old linked proof are retained;
unproven records are not silently trusted, repaired or deleted. Existing
recommendation-source and historical-action regressions pass.

This does not independently accept real model quality, deployment/database
semantics or unsupported outerwear visualisation, nor certify final FYP/NFR
acceptance. Teammate coordination remains necessary for any unproven legacy/manual
record remediation or alternative confirmation evidence. No RN-13 development,
scoring activation, colour calibration, PostgreSQL work or NFR run begins.
Wait for owner review.
