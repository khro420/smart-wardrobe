# Phase 5F-2E-3J-3: owner-declared suitability controls

2026-10-22. **PASS WITH LIMITATIONS - ready for owner review and closure.** No activation is included.
Owner and teammate explicitly authorised these scoped wardrobe controls and the minimal API/persistence concurrency protection. No additional activation is authorised. These are approved implementation policies, not occasion rules specified by the original report. RN-13 (report PDF188) motivates condition handling; completed Phase1/2/3 contracts remain authoritative.

## Workflow and evidence

Open a confirmed garment in the existing wardrobe editor. Owner-declared suitability offers exactly Unknown, Allow and Deny for each value below. There is no inference, inheritance or formality hierarchy.

| Field | Supported values | Stored declaration |
|---|---|---|
| Occasion | campus, work, casual_outing, shopping, dinner, party, date, travel | `rec:v1:occasion:<value>:allow` or `:deny` |
| Formality | casual, smart_casual | `rec:v1:formality:<value>:allow` or `:deny` |

Absent evidence is Unknown. Allow is positive, Deny definite failure, conflict Unknown. The existing parser is reused unchanged. A malformed reserved annotation taints its entire identified field; unidentified fields taint both. Choosing Unknown removes only that value's exact valid allow/deny pair. Other valid declarations and malformed annotations remain until explicitly removed. The editor separately exposes conflicts and offers explicit removal of numbered unrecognised annotations. Ordinary tags are edited separately; reserved syntax is not the normal user input mechanism. An invalid tag collection is read-only rather than silently normalised. Corrupt raw JSON can still fail the existing serializer and requires separate explicit repair.

An unchanged save omits custom_tags. Explicit changes preserve unrelated declarations, ordinary tags and style null/empty/string/list semantics. Unrelated garment changes do not invalidate or delete declarations. The UI asks owners to revisit suitability after material garment changes. Owner statements are not independently proven appropriateness, can become stale and have no dedicated review provenance.

The optional approved-name colour guidance lists the existing fourteen NLP names. It preserves any existing primary hex unless the owner edits it. Names/aliases and approved exact anchors are unchanged; no approximate classification is enabled, no palette overrides primary colour, and CV empty-pixel #000000 remains indistinguishable from genuine black without separate provenance.

## Concurrency and API compatibility

Garment reads add transient `tag_edit` metadata: version, quoted revision, parser-derived declarations, raw tag projection, ordinary/reserved indices, malformed evidence and approved colour names. This is not persisted or a new database field. Metadata follows existing snapshot precedence and does not become scoring evidence itself.

**Intentional API compatibility change:** a garment PATCH explicitly replacing `attributes.custom_tags` must supply `If-Match` with the revision from the garment read. Missing precondition returns428; stale or invalid revision returns409. Older external tag-edit clients must adopt this read/conditional-write sequence. The wardrobe client and existing test callers do so. Review/confirmation creation and PATCH requests omitting tags retain their behavior. A conflict rejects the whole combined patch, including name/style changes; the browser retains its draft, reports failure and requires owner reload/review rather than silently retrying.

The content hash binds garment/owner and all current tag representations. `BEGIN IMMEDIATE` covers read, comparison and write. Independent SQLite connections prove one changed write wins and the stale competing replacement fails. This is a content precondition, not a monotonic event revision: same-content writes and an ABA return to identical content are not distinguished. No annotation audit trail or universal protection for future bypassing writers is claimed. SQLite locking is not PostgreSQL verification. Trigger-injected failure rolls back the combined update. Existing tag count/length validation remains; no truncation or historical repair occurs.

## Opt-in evaluator and boundaries

The existing dependency-injected suitability evaluator is tested, not activated. Every member, including outerwear, must Allow each supplied supported condition. Any definite Fail wins; otherwise Unknown yields InsufficientEvidence. All-positive evidence alone passes. Exercise and formal remain PolicyUnavailable. Ordinary tags cannot satisfy these conditions. Combined five-field requests retain category, primary-colour and base-style rules.

Actual API upload/review/confirmation fixtures, persistence reads and strict snapshots were used. Browser tests perform real edits and reloads rather than mocked API success. Historical recommendation, chat and visualisation rows remain unchanged after a successful tag edit. Strict owner/confirmed/available acquisition and stream behavior remain covered by existing regression suites.

Compact execution and deferred scoring defaults are unchanged. Suitability remains opt-in, approximate hex disabled. No recommendation algorithms, live selection, NLP fields, persistence schema, history semantics, saved-outfit validation, CV/VTON algorithms, feature flags or deployment provider changes. No benchmark, model inference or migration was commissioned. This does not close all RN-13 scope: separate approval is needed for evaluator activation and bounded occasion/formality scope; exercise/formal and general-hex evidence remain unavailable. Real models, PostgreSQL, deployment and formal NFR acceptance are outside these tests.

## File inventory

| File | Purpose |
|---|---|
| backend/app/application/wardrobe/garment_tag_edit.py | New parser-backed edit projection and content revision. |
| backend/app/application/wardrobe/wardrobe_service.py | Read metadata and transaction-bound conditional tag writes. |
| backend/app/api/wardrobe_routes.py | Optional If-Match header forwarded to writer. |
| frontend/components/GarmentSuitabilityFields.tsx | New friendly ten-value controls, conflict/malformed correction and disclosures. |
| frontend/app/wardrobe/page.tsx | Preserve/merge explicit edits, revision submission and colour guidance. |
| frontend/lib/api.ts | Typed edit projection and conditional PATCH header. |
| backend/tests/test_suitability_controls.py | New real lifecycle, all-value, concurrency, rollback, opt-in and history tests. |
| backend/tests/test_suitability_tag_workflow.py | Existing tag PATCH caller supplies revision; assertions preserved. |
| backend/tests/test_o1_wardrobe.py | Existing complete-edit test supplies revision; assertions preserved. |
| frontend/tests/suitability-edit.spec.ts | Twelve real browser lifecycle and concurrent-edit tests. |
| backend/tests/fixtures/suitability_controls_sources.v1.json | Explicit new source transition; historical pins unchanged. |
| backend/tests/integration_source_guard.py | Chain authorised transition and new helper into frozen guards. |
| docs/OWNER_DECLARED_SUITABILITY_CONTROLS.md | This implementation/evidence report. |
| docs/REPORT_TRACEABILITY.md | Appended scoped traceability. |

Verification logs, before hashes, original four application files, generated tsconfig backup, commands and source checks are in `storage/verification/phase5f2e3j3/`. The original tsconfig bytes are restored after generated build includes are checked. Prior phase reports and raw evidence are retained.

## Verification

Focused five-file suite: **177 passed** (83.72s). Additional archival tag-edit test: **1 passed** (4.12s). Full real-browser suite: **54 passed** (8.3m), including all twelve new cases. TypeScript and isolated Next16.4.2 production build passed. ESLint passed with the same two navigation warnings at extract/results:157 and Layout:50.

The initial broad backend run is retained: **1,946 passed, 2 failed** (430.80s). One older full-edit test omitted the newly required revision; only its caller was updated, preserving every assertion. The other is the known ai-services architecture assertion, not weakened here. Initial new-test collection used pytest's reserved parameter name and was corrected; the next run's concurrency fixture attempted an identical-content write, so its expectation was corrected to use genuinely different edits. No production change followed the frozen application patch. Final broad results and integrity verification are appended after completion.


### Final verification and closure

| Verification | Result |
|---|---|
| Five-file focused backend suite |177 passed, 83.72s |
| Additional archival tag-change check |1 passed, 4.12s |
| Final full backend, excluding separate CV geometry environment |1,948 passed, 1 known failure, 269.36s |
| Full browser integration suite |54 passed, 8.3m, including12 new actual save/reload cases |
| TypeScript final explicit check |Exit0 |
| ESLint final explicit check |Exit0, two unchanged navigation warnings |
| Isolated production build |Exit0, Next16.4.2 |
| git diff --check |Exit0 |
| Frozen-source/new-file checks |303 baseline files checked,40 prior fixture files unchanged; authorised transitions match; original tsconfig restored; new-file whitespace clean |

Exact commands are retained in `storage/verification/phase5f2e3j3/commands.txt`; raw logs include initial failures and final outcomes. The final broad run includes all53 new backend tests, historical preservation, Phase1-4 scoring/query/stream regressions and existing action/visualisation/authentication checks. The sole remaining failure is `tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`, whose assertion forbids the retained ai-services directory. Neither directory nor assertion was altered. The corrected older wardrobe test passes with the required header; all original assertions remain. No production edits occurred after the original frozen patch. Initial online UV retries are retained; the final broad command used the same cached pinned environment offline.

Fourteen implementation/test/document deliverables are listed above and hash-indexed in `deliverables.json`; source backups and verification artifacts are additional local evidence. The older O1 test was not in the303-file initial subset; its exact pre-edit backup is retained separately. All previous phase raw results and reports remain. No real CV geometry/GPU quality, production database, PostgreSQL locking, deployed restart or formal latency result is claimed.

**Ready to close J-3 as PASS WITH LIMITATIONS.** The owner workflow, evidence preservation and conditional tag replacement are verified. Separate approval remains necessary for live suitability enablement and RN-13 scope acceptance. No next phase, scoring activation, colour calibration, model change or performance optimisation starts automatically.
