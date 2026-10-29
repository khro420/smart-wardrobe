# Phase 1: confirmed garment data contract

The original Chong Wei Ping Project I report is the design reference: RN-11,
CA-04, FR-DW-11, NFR-08/09/20/24/25; sections 4.4.2, 4.5.2–4.5.3,
4.10.2 and 4.11.3. Phase 1 supplies wardrobe data, not recommendation validity.

## Operations and eligibility

`ConfirmedGarmentQuery.get_confirmed_available_garments(user_id)` returns an
immutable tuple of `ConfirmedGarmentSnapshot` objects. Every returned record
belongs to the supplied authenticated user, has `status='available'`, and has
an existing linked processing item with `review_status='confirmed'`. The owning
processing job must belong to the same user. Temporary processing data never
crosses the interface. These guarantees hold at retrieval time; existing Save
and Try it on paths still perform their current revalidation.

Accepted, pending, rejected, dangling/missing and NULL processing-item links are
excluded. NULL links are not automatically trusted legacy or manual garments.
No existing records are changed or deleted. A future trusted legacy policy
requires coordination with Digital Wardrobe before this query is extended.

The legacy `list_available_garment_ids(user_id)` is unchanged: it filters only
garment ownership and available status. Its IDs can therefore include records
excluded by the new operation. This difference is intentional and approved.

## Snapshot fields and projection

| Fields | Source and treatment |
| --- | --- |
| garment_id, user_id, status, category, name, preferred_media_id | Existing garment columns. Media reference is opaque, never a storage path. Category spelling is preserved. |
| is_favourite, updated_at | Existing columns; retained for the current scaffold ordering. |
| structural_role, layering_index | Exact `GARMENT_STRUCTURE` category lookup. Unrecognized categories produce NULL; no aliases or substring inference. Stored structural metadata is not rewritten. |
| primary_colour, pattern | Nonblank dedicated column first, then existing attribute JSON. Colour aliases `primary_colour` and `primary_color` are read in that order. |
| secondary_colour | Existing column; no inferred secondary colour. |
| style_tags, custom_tags | Dedicated JSON string/list first; absent or JSON-null column uses the attribute value. Text becomes a tuple; whitespace/duplicate tags are removed. A malformed non-null column is flagged, not replaced with fallback data. |
| fit, material | Existing strings stay strings, including empty strings. Lists become tuples preserving every string, NULL element, empty element, duplicate and original order permitted by ReviewItem. Missing/NULL stays None; an empty list becomes (). No first-item selection or concatenation. |
| colour_temperature | Existing warm/cool/neutral value, otherwise NULL. Missing never defaults to neutral. |
| is_dominant | Existing boolean, otherwise NULL. Missing never defaults to false. |
| colour_palette | Existing `color_palette` list, as a tuple of frozen entries. Existing colour text is preserved; coverage must be finite 0–1 or absent/NULL. Malformed entries/coverage invalidate the collection rather than yielding a partial or empty valid palette. No colour naming/classification is performed. |
| invalid_attributes | Immutable tuple naming malformed optional attributes or JSON containers. This is data-quality metadata, not inferred garment information or an eligibility decision. |

For attribute JSON, canonical `attributes_json` keys take precedence over their
`additional_attributes` mirror; the mirror supplies absent keys only. Malformed
optional JSON becomes unavailable and its container is flagged rather than
preventing an otherwise confirmed garment from crossing the boundary.
For collections: missing/NULL is None without a field error, explicitly empty is
(), and invalid is None with the field named in invalid_attributes. An invalid
JSON container is flagged by its container name because its individual fields
cannot be identified. Invalid tag elements invalidate the whole collection;
valid elements are not silently retained as a misleading partial collection.
Blank tag strings are invalid; fit/material empty strings and NULL list elements
remain preserved because the existing ReviewItem accepts them.
Missing optional attributes do not change
confirmation eligibility. Later recommendation-specific eligibility must decide
which fields its rules require (RN-12); this phase does not implement that rule.

Snapshots and nested values contain only immutable primitive values, tuples and
frozen dataclasses. Construction copies all list-valued tags, fit/material,
invalid_attributes and palettes into tuples. Palette dictionaries are converted
to validated frozen entries. Malformed constructor inputs raise ValueError or
TypeError; mutable nested values cannot remain inside a successfully constructed
snapshot, including scalar fields. These protections cover other query adapters
and direct construction, not just the SQLite adapter.
Embeddings and temporary inference/provenance payloads are
not included. Occasion/formality predictions, values and vocabularies are not
introduced. Existing tags are data, not approved suitability rules.

## Composition and compatibility

The infrastructure composition root `configure_local_workflow()` injects the
query into `application/ports/recommendation_runtime.py`. Recommendation depends
on that protocol boundary for acquisition, not the concrete SQLite adapter.
Existing recommendation/preferences SQL remains outside this acquisition change.

Snapshots are ordered by favourites descending, updated time descending and ID
ascending, matching the former acquisition query. The existing four-item limit,
selection heuristic, `_role_for()`, persistence and response shapes are retained.
Snapshot structure is not substituted for persisted recommendation roles.
Known heuristic role defects remain deferred; old recommendations are untouched.

The report identifies upper-body, lower-body, outerwear and one-piece role
concepts (section 4.8.2, printed p.256). Exact role strings and outerwear
combinations remain a later coordinated decision. VTON still rejects outerwear.

Users with only unlinked or nonconfirmed records now receive the existing 422
no-garments response when creating a recommendation. Wardrobe browsing/editing,
manual outfit construction, historical recommendations, saving and visualisation
retain their existing behavior. The capacity script's NULL-linked fixtures do
not qualify for the new query; its wardrobe capacity workflow is unchanged.

## Verification and remaining coordination

`tests/test_confirmed_garment_snapshot.py` covers strict status/provenance,
ownership, legacy-ID compatibility, nullable/malformed optional data, immutable
nesting, all 13 structural mappings, ordering, and injected acquisition.
Existing workflow, wardrobe, recommendation-boundary, garment-processing and
VTON contract tests provide regressions. Model quality is not evaluated here.

Remaining decisions: trusted legacy-record confirmation, category aliases,
controlled colour/style vocabularies, occasion/formality rules, outfit structures
and compatibility criteria. No migration or CV/VTOFF/VTON/processing algorithm
change is part of Phase 1. Successful contract tests do not establish RN-27 NLP
accuracy, RN-28 complete outfit validity, ranking quality or performance targets.

### Verification on 2026-10-14

Executed with an isolated Python 3.12 environment containing pytest, FastAPI,
HTTPX, Pillow, python-multipart and NumPy, using the development AI test runtime
and `SMART_WARDROBE_VTOFF_ENABLED=off` to avoid absent model assets:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -m pytest tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Result: **74 passed, 1 failed**, with a Starlette TestClient deprecation warning.
The existing `test_single_backend_and_canonical_ml_locations` fails because it
asserts that `ai-services/` does not exist; that directory exists in this checkout.
Its later datasets/runs directory assertions were not reached. No project folders
or old tests were changed to hide this failure. `git diff --check` passed.

The initial minimal-environment smoke run failed because optional VTOFF imported
NumPy while assets were absent; disabling model VTOFF for development regression
tests resolved that setup issue. An intermediate new malformed-JSON fixture
interfered with later startup backfill; the fixture was corrected before the
final run. No application processing algorithm was changed for either issue.

Not executed: segmentation geometry tests requiring the heavy CV stack,
real-model inference/quality benchmarks, PostgreSQL deployment verification,
capacity scripts, frontend lint/build and browser tests. Phase 1 makes no
frontend, database-schema or AI algorithm changes.

### Correction verification on 2026-10-14

After projection/immutability corrections, the focused contract suite passed
**68 tests** in 7.47 seconds. The same 11-file regression selection above passed
**114 tests**, with **1 pre-existing architecture failure**, in 14.02 seconds.
Both runs reported the same Starlette TestClient deprecation warning. The
architecture failure remains the ai-services directory assertion; no folder or
architecture-test change was made. The earlier 74/1 result is the original
Phase 1 run, not the corrected-suite result.

Exact corrected commands, from backend/:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_confirmed_garment_snapshot.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Additional coverage checks accepted fit/material strings, lists, NULL/empty
elements and duplicates; collection missing/empty/invalid distinctions; malformed
JSON fallback behavior; all mutable constructor collection inputs and nested
palette dictionaries; rejection of invalid nested/scalar mutable values; and
post-construction mutation attempts. Existing eligibility, ordering, injection,
selection and history/save integration tests continue to pass. No Phase 2
behavior was added. The previously listed unexecuted checks remain unexecuted.
