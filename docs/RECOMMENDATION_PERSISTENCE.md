# Phase 5A: independent recommendation persistence foundations

Authority: original report FR-HR-01–12, FR-OA-01–12, FR-CH-01–07/13–16,
sections 4.8.2 and 4.10.4–4.10.5. Submission keys, exact-score JSON and display
snapshots are approved implementation choices, not report-defined schemas.

## Boundary

RecommendationRepository and SqliteRecommendationRepository are independent,
explicitly invoked infrastructure. No route, frontend, live selection, scorer,
save-as-outfit or visualisation code is wired to them. Callers must finish the
approved mandatory evaluation and complete selection/ranking before constructing
RecommendationWrite. This writer verifies structure, ownership and fresh strict
garment evidence; it does not certify that a trusted caller actually completed
the upstream request/ranking stream. It is not a public browser input contract.

## Schema and migration

Existing SQLite initialization runs first, unchanged. A separate narrowly scoped
hook invokes recommendation_migrations.migrate_recommendations. Migration v1
uses BEGIN IMMEDIATE, audits historical user/chat/item ownership, missing
references, duplicate non-null chats and invalid/duplicate item orders. Any
conflict aborts the recommendation migration without repairing historical rows.
Earlier initializer operations retain their existing commit behaviour; this is
not an all-or-nothing migration of the entire application schema.

Additions: recommendation_metadata (policy provenance and exact score metadata),
recommendation_item_snapshots (display-only snapshots), recommendation_submissions
(scoped key/fingerprint/result), recommendation_migrations (version marker), unique
indexes on non-null recommendation chat IDs and recommendation item ordering.
New child tables have foreign keys. Submission insert/update triggers enforce
same-owner recommendation/chat/items and the operation's chat association.

SQLite cannot add foreign keys to old tables without rebuilding them. Existing
tables are not rebuilt; legacy writes/parent updates are not comprehensively
constrained by these additions. New writer checks plus new-table FKs establish
the foundation's write invariants. Arbitrary SQL modifying old parents can still
invalidate history; reads remain user-scoped and actions retain their legacy
checks. The migration audits once before installing constraints, not at every
subsequent startup. It does not pretend to sanitize later out-of-band corruption.

No deployment database was available for inspection. Tests use fresh and
representative populated temporary databases, not actual user deployment data.

## SQLite transaction guarantees

The adapter opens its own connection with foreign_keys=ON and a ten-second lock
timeout, then BEGIN IMMEDIATE before idempotency resolution. Strict revalidation
uses SqliteConfirmedGarmentQuery with that same connection. Injected connections
are never committed, rolled back or closed by the query adapter; default callers
retain their original behaviour and both public methods are preserved.

Every selected ConfirmedGarmentSnapshot must exactly equal the current strict
projection: identity, ownership, availability, category, role, media, attributes,
updated_at and diagnostics. This deliberately conservative comparison can reject
even display/favourite changes. It never ignores missing or malformed attributes.
NULL/missing/accepted/pending/rejected processing links and foreign processing
jobs remain excluded. Changes committed before lock acquisition are detected;
other SQLite writers cannot commit changes between revalidation and commit.

Chat (Assistant only), recommendation, ordered items, snapshots, metadata and
submission are inserted in the same transaction. All BaseException failures roll
back. Enumeration/ranking never runs inside this writer. No VTON work runs here.
Changes after commit remain possible and are shown through current eligibility.
Preference updates during ranking are not revalidated: this input carries the
selected garment snapshots and actual scores, not a preference-revision token.

## Idempotency and score provenance

Scope is (authenticated user, operation, submission key), with nonblank keys up
to 200 characters. SHA-256 fingerprint v1 covers canonical sorted JSON of the
operation, complete request_json object and original request text. JSON object
key order is irrelevant; array order and text whitespace remain significant.
Callers must include the complete submitted request, not omit meaningful fields.
Candidate, policy and generated scores are deliberately excluded: retrying a
submission recovers the committed result even if generation/policy subsequently
changes. A changed request under the same key raises PersistenceConflict.

Concurrent identical calls serialize through SQLite's write lock. One commits;
others return its stored result. A different key intentionally creates another
interaction, even with identical text. The operation namespace distinguishes
Homepage and Assistant keys. A successful commit followed by a lost response is
recoverable by replay. Busy timeout/I/O errors propagate; no partial success is
returned. No permanent running/submission reservation is inserted on failure.

Homepage writes have NULL chat and all score columns NULL. Assistant requires
actual immutable RecommendationScore; unavailable component values stay NULL.
Exact fractions, availability, evidence, weights and profile/version are stored
as JSON in addition to the legacy REAL score columns. Provenance is a required
nonempty application-supplied object. No default profile or suitability policy
is activated. Approximate colour classification remains disabled.

## Historical reads

The new get(user_id,id) uses a LEFT chat join, so Homepage records are readable.
It retains every recorded ID, role and order. New records restore captured name,
category and media identity, with current strict eligibility separately exposed.
Media identifiers are withheld for unavailable/inaccessible references; protected
media authorization remains necessary. No current foreign garment attributes are
read into the response. Legacy items without snapshots return NULL display fields
and snapshot_available=false rather than inventing original historical values.
Replay retains result identity and saved content; availability diagnostics can
change. Reads never invoke generation or ranking. No searchable chat API exists
in this phase. Existing live readers deliberately remain unchanged.

## PostgreSQL deployment

003_recommendation_foundations.sql supplies corresponding additive deployment
DDL with audit, unique indexes, foreign keys and submission ownership trigger.
It has not been executed against PostgreSQL in this phase. PostgreSQL is not the
runtime adapter: documentation/DDL do not claim a working PostgreSQL writer.

A future PostgreSQL adapter must reserve/serialize the scoped idempotency key
before lookup (e.g. transactional advisory lock plus unique constraint), lock
selected garment AND linked processing-item/job rows before rereading evidence,
then compare and insert all records in one transaction. READ COMMITTED plus
unlocked sequential checks is insufficient. Use consistent row lock ordering,
coordinate parent updates, and handle deadlocks/serialization retries without
duplicate commits. Do not assume SQLite's database-wide writer lock exists in
PostgreSQL. Migration table locks and conflict audits require a deployment window.

## Deferred teammate coordination

No changes to existing save or visualisation paths are approved. Saving currently
checks ownership/availability but not full strict processing confirmation;
recommendation-source visualisation accepts some accepted/unlinked garments.
Minimum later reconciliation: strict current Phase 1-equivalent revalidation
within the source-resolution/save transaction, preserving unrelated outfit-source
behaviour. Never hold such transactions across VTON processing.

Saving currently changes recommendation.status to saved, whereas report 4.8.2
describes an independent outfit without changing Recommendation. Proposed later
reconciliation: retain Recommendation and record saved-outfit association outside
its status; requires separate API/frontend/Digital Wardrobe agreement.

The frontend review neckline/sleeve_length 422 followed by confirmation 409
remains unchanged. Future Homepage/Assistant orchestration and full history APIs
are outside Phase 5A. Existing ai-services architecture assertion remains separate.

## Executed verification (2026-10-18)

From backend, exact commands:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_recommendation_persistence.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_recommendation_persistence.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Final focused: 46 passed in 6.93s. Final combined: 524 passed, 1 failed,
1 Starlette TestClient deprecation warning in 32.49s. Only failure:
test_report_architecture.py:28 expects the existing ai-services directory to be
absent. No folders/assertions were removed or restructured. No new regression
failure was observed. Earlier runs before test expansion are superseded.

Tests use independent SQLite connections for duplicate/conflicting submissions
and garment write-lock contention, rollback injection at each write stage,
second-item rollback, strict transaction-bound eligibility, actual score metadata,
historical restoration, legacy missing-snapshot reads, inactive/foreign owners,
attribute-change detection, repeated migrations and seven conflict audit cases.

From repository root, git diff --check passed. Separate trailing-whitespace
inspection covered all seven new files because normal git diff excludes untracked
files. PostgreSQL execution, deployment-data audit, browser E2E, real VTON/CV
inference and end-to-end performance measurements were not performed. No Phase 5B
activation or response-time claim is made. Phase 5A: PASS WITH LIMITATIONS,
ready for owner review; not automatically closed.
