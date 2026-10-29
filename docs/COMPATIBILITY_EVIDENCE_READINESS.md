# Phase 5F-2E-1: RN-17 reviewed evidence and coverage readiness

This is offline evidence infrastructure, not activation of compatibility scoring.
RN-17 and original Project I sections 4.4.3 (printed pp.221-222) and 4.10.4
(pp.274-277) require request/compatibility/preference scoring of valid candidates,
consistent normalization/weights and deterministic selection. They do not specify
this review schema, rubric, reference coverage gate or final numeric weights.
These are experimental implementation policies, not original report constants.

All production application files remain the completed-2D1 implementation. Live
Assistant uses compatibility_deferred; suitability is opt-in; approximate hex
mandatory evidence remains disabled. No generation, ranking, persistence,
frontend, CV, wardrobe, saving or visualisation change occurs here.

## Collection contract

Machine-readable schema: datasets/compatibility_reviews.schema.v1.json.
Ready-to-use EMPTY collection: datasets/compatibility_reviews.empty.v1.json.
Its records list intentionally contains no examples, images, reviewers or ratings.
The Python validator additionally enforces semantic conditions JSON Schema cannot
express: canonical snapshot/signature consistency, exact arithmetic, approval,
chronology and cross-partition source isolation. Populated synthetic records exist
only in tests/test_compatibility_evidence_dataset.py and older synthetic fixtures.

Envelope: schema_version=compatibility-evidence-1.0.0, dataset_version, kind
(human_review_collection or explicitly opted-in synthetic_fixture), boolean
validation_locked, records. Schema version describes the contract; dataset
version describes the specific immutable collection release.

Each record contains:

| Field | Meaning |
|---|---|
| example_id | Stable unique actual-outfit example or privacy-preserving ID. |
| partition | reference, development or validation; validation must be locked. |
| review_status | unreviewed or reviewed, separate from approval. |
| approval_status | draft, approved or rejected. |
| independently_reviewed | Auditable declaration, not software proof of independence. |
| lookup_reference | Explicit selection of one approved reference exemplar per signature. Never true for development/validation. |
| source_ids | Stable source/garment/image grouping IDs, retained across aliases. |
| evidence_source | Capture source and permission/provenance description. |
| captured_at | Timezone-aware ISO-8601 capture timestamp. |
| images | image_ref, SHA-256 of actual image bytes, garment_ids depicted. Every outfit garment must have image evidence. |
| garments | Ordered role plus full Phase 1 snapshot, with real or stable pseudonymous IDs. Snapshots are offline captures, not proof of current database confirmation. |
| signature | Exact existing canonical structure-aware signature; null when required evidence is incomplete/unrecognized. |
| reviews | reviewer_id, integer rating 0-4, timezone-aware reviewed_at, all image_refs actually reviewed, dataset_version. |
| adjudication | reviewer_id, accepted/pending/rejected decision, note, reviewed_at; null before adjudication. |
| normalized_value | Exact numerator/denominator of mean rating divided by four; null when unreviewed. |

An unreviewed record is draft, has no ratings/adjudication/value and cannot claim
independent review. Reviewed records can have incomplete signature evidence: a
human may review the image, but the lookup cannot represent it. Such a record
cannot be selected as a lookup reference. Approval requires at least two distinct
reviewer declarations and accepted adjudication; genuine approved data also
requires independently_reviewed=true. Booleans are not accepted as ratings.

The actual structure/roles must be one of top_bottom, top_bottom_outerwear, dress,
dress_outerwear. Existing OutfitCandidate validates category/role mappings,
ownership consistency, available snapshot status, uniqueness and slot order.
The unchanged CompatibilityEvidenceMapper builds the signature from every actual
garment's complete style set, recognized current primary colour and approved
pattern. A dress is one one_piece garment, never two descriptors. Do not fill
missing evidence to make a reference importable. Named aliases/exact anchors
remain the only recognized colour evidence; palette/secondary values never
substitute. Canonical styles are sorted/deduplicated by existing infrastructure.

## Collection template and review procedure

Start by copying the empty JSON collection under an isolated data directory.
Use this record blueprint; angle-bracket placeholders are NOT collected evidence
and must be replaced. The validator rejects unresolved/invalid fields.

```text
example_id: <stable actual outfit ID>
partition: reference | development | validation
review_status: unreviewed
approval_status: draft
independently_reviewed: false
lookup_reference: false
source_ids: [<stable source group IDs>]
evidence_source: <how/where captured and authorization>
captured_at: <actual ISO timestamp with timezone>
images: [{image_ref: <protected review artifact reference>,
          sha256: <actual file hash>, garment_ids: [<depicted stable IDs>]}]
garments: [{role: <actual role>, snapshot: <captured Phase 1 snapshot>}, ...]
signature: <canonical signature from existing mapper, or null>
reviews: []
adjudication: null
normalized_value: null
```

Collect all four structures, multiple styles, corrected primary colours, pattern
variation and incomplete evidence. Record image capture/lighting limitations.
Do not put private photographs, credentials or public bearer URLs into Git.
Image references can be protected opaque IDs with hashes; this tool does not
download images, authenticate media access or prove image contents. Collectors
must independently verify the image bytes, permissions and correspondence.

Have reviewers independently inspect the actual full outfits, blinded to system
scores and each other's judgments. Rubric: 0 very poorly coordinated, 1 weak,
2 mixed/ordinary, 3 coordinated, 4 strongly coordinated. Preserve disagreements;
do not rewrite individual ratings after adjudication. Common scale does not prove
cross-structure validity: reviewers must assess dresses and layered outfits using
the same rubric without a garment-count bonus or penalty. Review realistic
different garments sharing metadata to test whether signature-level reuse is
defensible. Select an explicit representative only after reviewing this evidence;
the importer never silently averages conflicting examples or chooses the first.

Freeze reference/development collections, rubric, policy hash and weights before
locked validation. Assign splits by garment/image/source GROUP, not outfit ID.
Validation must use different garments and image sources; identical signatures
are allowed so generalization to new actual garments can be measured. Include
previously unseen signatures separately. Do not import validation ratings into
the lookup used for that evaluation. No minimum sample size or new quality
threshold is claimed as an original report requirement.

## Validation and isolated import

From backend:

```powershell
uv run --no-project --python 3.12 python -B scripts/compatibility_evidence_dataset.py ../docs/datasets/compatibility_reviews.empty.v1.json --output ../storage/verification/phase5f2e1/empty-import.json
```

Outputs are NEW isolated JSON bundles containing the unchanged original collection
(timestamps/images/reviewer provenance), dataset hash, derived compatible lookup
policy, policy hash and descriptive quality diagnostics. Import never writes to
production configuration. Existing output files, input paths, backend/app,
backend/tests and frontend trees are protected. Use a new output name for reruns.
The existing CompatibilityReferencePolicy validates the derived policy again.
An offline consumer can load bundle["policy"] explicitly; the bundle is not a
drop-in live configuration or evidence of activation approval.

Duplicate JSON keys, malformed values, unsupported fields, roles, canonical
attributes and inconsistent signatures are rejected. Snapshots sharing a stable
garment ID must agree. Image hashes, garment IDs and stable source groups must not
cross partitions. Source aliases dishonestly omitted by a collector cannot be
detected; partition locking is a recorded protocol, not access control. Real and
synthetic collections cannot be merged through this contract. Explicit synthetic
opt-in still cannot claim independent human review.

Quality diagnostics report exact reviewer-pair agreement, mean absolute ordinal
rating difference, within-signature rating range, reviewed counts per structure
and held-out compatibility pair-order agreement where covered reviewed examples
exist. Pair ties must agree as ties. These descriptive statistics are not
chance-corrected reliability, full R/C/P ranking quality or proof of fair rubric
interpretation. Weight sensitivity still requires separately captured request/
preference ranking sessions with the existing evaluate_compatibility.py tool;
it is not fabricated from isolated outfit ratings. No actual records means null
quality metrics, not zero accuracy or perfect agreement.

## Exhaustive coverage probes

```powershell
uv run --no-project --python 3.12 python -B scripts/audit_compatibility_coverage.py ../docs/datasets/compatibility_reviews.empty.v1.json --sizes 20 50 100 200 --measure-memory --output ../storage/verification/phase5f2e1/coverage.json
```

Uniform and varied synthetic metadata at each size exercise the existing
structural generator. Uniform gives four distinct complete signatures when all
structures are present. Varied cycles approved styles, colours and patterns.
These snapshots have no actual images or human reviews and are explicitly marked
synthetic_probe. They are not imported into the human-review collection.

An additional outerwear-heavy 200-garment probe (67 tops,67 bottoms,0 dresses,
66 outerwear) has 300,763 combinations. The familiar 80/80/20/20 composition has
134,820; that count is not an upper bound. No candidate truncation is used.

Optional --wardrobes PATH accepts an actual captured offline workload file:
version, kind=captured_offline_wardrobes, wardrobes=[{session_id,snapshots:[...]}].
Capture through the genuine Phase 1 contract, preserve stable IDs, and record
the independent review split separately. Do not relabel synthetic captures as
real. Captured snapshots still cannot prove current production eligibility.

Reports include input hashes, complete-stream counts, unique complete signatures,
covered candidates/signatures, reviewed zero, missing references, incomplete
evidence, unavailable policy, per-structure coverage, seen signatures with
different actual garments, unseen signatures and hypothetical session eligibility.
No compatibility score or recommendation is produced. Missing references are
unknown, never numeric zero. Absent structures have null coverage, not 100%.
Unique signatures exclude incomplete evidence, whose candidates remain in the
total coverage denominator. The hypothetical gate requires positive candidate
count and every candidate covered; it is measured, NOT installed in any engine.

Timing: one uninstrumented structural baseline and one full signature/lookup pass
per workload; optional separate tracemalloc pass. The time delta includes all
signature construction, lookup, unique-key accounting and diagnostics; it is not
an isolated nanosecond dictionary benchmark or optimized-production causal result.
Memory is Python traced incremental allocations, not RSS, and excludes input
fixture/policy construction. Candidate objects are streamed. Audit unique-key
sets grow with signature diversity; this collection cost is not required by the
live scorer, which only retains a winner, garment cache and counters. No speedup
or five-second NFR-02 compliance is claimed.

## Current evidence and next decision

No real reviewed reference images/ratings or captured real workload were supplied
for this stage. The initial approved configuration and new collection are empty.
Human reviewer agreement, ranking quality, real coverage and cross-structure
rubric validity remain unmeasured. Synthetic probes with zero references have
zero coverage and a strict gate permits no session. This does not estimate the
gate's probability after genuine references are collected.

Exact lookup may be feasible for a bounded curated demonstration with repeated
metadata, but cannot presently support normal wardrobe coverage. Reference
diversity and metadata sufficiency must be measured first. A reviewed generalizable
rule/hybrid policy is likely needed for broad unseen-signature coverage, but no
rule, approximation, automatic fallback, coverage gate or scoring profile is
implemented or activated here. Unknown candidates are never silently discarded.
Next decision: obtain real reference/held-out collections and representative
wardrobes, assess actual reuse/coverage and signature consistency, then separately
approve either a bounded reference-only activation plan or a reviewed hybrid
design. RN-17 remains partial, not accepted as completed by empty tooling.

The review 422/409 blocker, strict recommendation-source save/visualisation gaps,
style-null semantics and CV empty-pixel black ambiguity remain coordination work.
Existing tags/confirmation do not prove suitability or extraction success.
