# Phase 3B-2A: Oklab colour classification infrastructure

## Authority and boundaries

The original report is primary: RN-12/13/15 cover mandatory filtering, RN-23
prohibits fabricated attributes, and RN-28 concerns complete validity. Sections
4.10.2–4.10.4 separate mandatory validity from scoring. The report does not define
Oklab, swatches, thresholds or a classifier release precision requirement.
RN-27's 80% NLP target must not be reused as a colour-classifier threshold.

**Approximate mandatory matching remains disabled.** The classifier is isolated:
existing ColourClassifier, evidence mapper, candidate evaluator and Phase 1–3B-1
interfaces are unchanged. No live service, frontend, persistence, CV, scoring,
ranking, occasion/formality policy, migration or AI dependency is changed.

## Formulas, candidate configuration and outcomes

`application/recommendation/oklab.py` converts encoded sRGB channel c in [0,1]
to linear c/12.92 for c <= 0.04045, otherwise ((c+0.055)/1.055)^2. It applies
Ottosson's 2021 RGB-to-LMS matrix, LMS cube roots, then the LMS-to-Oklab matrix.
Distance is Euclidean on native L/a/b coordinates, including lightness. It is
not a probability or recommendation score. Sources/reference vectors:
[Ottosson's specification](https://bottosson.github.io/posts/oklab/) and
[W3C conversion guidance](https://www.w3.org/TR/css-color-4/#color-conversion-code).

Hex inputs accept #RGB/#RRGGBB, case differences and surrounding whitespace;
alpha and malformed values are rejected. Decoded CV RGB is provisionally treated
as sRGB; profile assumptions require CV developer agreement. Colour distance
cannot prove English naming or correct illumination/extraction errors.

`config/colour_prototypes.v1.json` contains 30 INITIAL UNREVIEWED CANDIDATES over
exactly the fourteen approved NLP colours. Twelve seeds come from the existing
AIR-05 audit; variants, navy and cream are proposals. Every prototype carries
provenance and remains unreviewed. Multiple prototypes are candidate within-class
variants, not approved boundaries. Their inclusion creates no mandatory anchor.

Class distance is the minimum over its prototypes. The closest two entries are
distinct classes, sorted by distance then class name. Alphabetical tie ordering
is diagnostic only. Missing threshold configuration always yields Unknown for
valid hex, even an exact prototype input. With explicit experimental thresholds:

| Outcome | Rule |
|---|---|
| Missing / Malformed | Missing input / invalid supported hex |
| Unknown | No calibration, or closest distance > maximum |
| Ambiguous | Distance qualifies but second-class gap < minimum, or exactly tied |
| Recognised | Distance <= maximum and gap >= minimum, without exact tie; experiment only |

ColourClassification is frozen, including nested class-distance tuples. It
contains status, optional recognised colour, method, reason, configuration
version/hash and diagnostic distances. ColourPrototype is also frozen. Prototype
ordering is canonicalized for hashing; data or threshold changes alter hashes.

Threshold JSON requires schema_version "1.0.0", version, status
"experimental_unapproved", mandatory_evidence_enabled false, prototype_hash,
max_distance and min_margin. Both thresholds must be explicit finite nonnegative
numbers. No acceptance values are supplied by default. Invalid configuration
fails rather than inventing defaults. A Recognised experimental result has no
AttributeEvidence adapter or release activation route.

Existing named aliases and thirteen exact anchors remain unchanged. An
experimental recognition of #182A46 as navy cannot satisfy mandatory matching;
the existing classifier still returns Unrecognized. #F5F5DC remains the existing
beige anchor. Cream gains no exact anchor. Only current snapshot primary colour
is consulted, never old secondary/palette information.

## Dataset schema and reproducible tools

Dataset JSON requires schema_version "1.0.0", a nonblank version,
validation_locked true and samples. Each sample provides:

- sample_id, source_group, hex and provenance;
- partition: development, calibration or validation;
- reference_kind: canonical, ambiguous or unknown;
- label: an approved colour for canonical references, null otherwise;
- reviewer_ids and independently_reviewed (boolean).

True independent review requires at least two distinct declared reviewers;
software cannot verify their independence. Related garment/image variants must
share source_group. Duplicate sample IDs are rejected. Normalized duplicate hex
or source groups cannot cross partitions. Within-partition duplicate hex and
unique group counts are reported. Import canonicalizes order without assigning
new partitions or silently changing labels. Outputs cannot overwrite inputs.

Locked validation is a procedural declaration, not filesystem access control.
Freeze its manifest/hash externally before tuning. Calibration cannot select
validation; evaluation requires explicit --confirm-locked-validation. Reports
record dataset, partition and configuration versions/hashes. Changing a manifest
is detectable by hash, but cannot be prevented by this offline tool.

Run from backend; paths below are examples for future real data, not existing
datasets or executed real-data evaluation:

```powershell
uv run --no-project --python 3.12 python -B scripts/evaluate_colour_classifier.py --help
uv run --no-project --python 3.12 python -B scripts/evaluate_colour_classifier.py import --dataset PATH_TO_REVIEWED_SAMPLES.json --output runs/colour_classification/imported.json
uv run --no-project --python 3.12 python -B scripts/evaluate_colour_classifier.py calibrate --dataset runs/colour_classification/imported.json --partition calibration --thresholds PATH_TO_EXPERIMENTAL_THRESHOLDS.json --output runs/colour_classification/calibration-report.json
uv run --no-project --python 3.12 python -B scripts/evaluate_colour_classifier.py evaluate --dataset runs/colour_classification/imported.json --partition validation --thresholds PATH_TO_FROZEN_THRESHOLDS.json --confirm-locked-validation --output runs/colour_classification/validation-report.json
```

calibrate assesses a supplied experiment, not automatic threshold fitting or
release selection. Retain experiment hashes; refine only with development and
calibration data. Agree a precision requirement, compare distance/margin settings
with grouped calibration, freeze a configuration, then evaluate untouched data.
No experiment or holdout result automatically activates mandatory evidence.

Metrics: recognised precision, canonical recall, coverage, abstention,
ambiguity/unknown rates, per-colour support/precision/recall/F1, confusion counts,
false recognition on uncertain references, review counts and missing reviewed
colours. Undefined denominators are null, not invented accuracy. Recognising an
ambiguous/unknown reference counts as an incorrect positive. Reports always
declare release_validation_complete false and mandatory_evidence_enabled false.

Review standardised swatches without predictions/prototype labels, using two
reviewers and adjudication. Record garment-context/extraction-fidelity judgments
separately. Include navy/blue, white/cream/beige, brown/orange, black/navy and
grey/muted-colour boundaries and uncertain/out-of-vocabulary examples.

## Evidence and limitations

Collection target: 30 independent examples per colour, with 20 for development/
calibration and 10 locked validation, plus uncertain examples. This is a pilot
target, not available data or guaranteed generalisation.

Existing scripts/attribute_ground_truth.json contains 39 single-reviewer audit
labels: white 9, black 10, pink 5, blue 6, grey 2, green 2, purple 3, beige 1,
orange 1. No navy, cream, brown, red or yellow examples are present. Its vocabulary
has twelve colours; its schema is not the new reviewed/partitioned schema.
Referenced storage/verification/attributes/label-manifest.json and
storage/verification/embeddings/samples.json are absent in this workspace.
The old forced-nearest OpenCV Lab audit must not become independent ground truth.

No real calibration/holdout evaluation has been executed. No reference images,
reviewed labels, threshold values or achieved accuracy have been fabricated.
Tests use explicitly synthetic samples/thresholds in temporary directories.
Calibration and release validation remain incomplete.

ColorAnalyzer returns (#000000,1.0,(0,0,0)) for empty pixels. The current snapshot
cannot distinguish that fallback from genuine black. Confirmation does not prove
successful extraction. Existing exact black matching is preserved. Coordinate
provenance and colour-space interpretation with CV/Digital Wardrobe; no algorithm
or database field is changed in this phase.

## Separate performance investigation

Previous read-only cProfile: 134,820 candidates, 65,533 passed, 18,020 failed,
51,267 unknown. Instrumented total ~17.45s is not comparable to the uninstrumented
8.92s baseline. Overlapping cumulative costs: request evaluation ~7.79s;
269,642 dataclass replacements ~4.21s; candidate validation ~2.31s;
structural checks ~1.44s; evidence-cache access ~1.04s; support checks ~0.71s.
Accepted-key digest overhead was not profiled.

Evidence classification is cached per garment. No generator/evaluator/session
optimisation occurs here. Future approved work should use repeated alternating
uninstrumented runs without concurrent load, separate digest/SQL/scoring costs,
and prove accepted order/hashes, counts, failures and interruption equivalence.
The 200-garment response-time risk remains unresolved.

## Executed verification (2026-10-15)

From backend, with VTOFF disabled for tests:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_colour_classification.py tests/test_request_candidates.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/evaluate_colour_classifier.py --help
```

Focused: **86 passed**, one Starlette TestClient deprecation warning, 3.06s.
Of these, 47 are new infrastructure tests and 39 are Phase 3B-1 regressions.
Combined: **299 passed, 1 failed**, the same warning, 19.49s. The existing failure
is test_report_architecture.py:28, requiring the existing ai-services directory
to be absent. No folder deletion or restructuring was performed. CLI help exited
successfully; CLI import/calibration/holdout guards and deterministic metrics were
also tested using temporary synthetic fixtures, not real evaluation samples.

`git diff --check` was run from the repository root and passed. The working tree
also contains earlier phase changes; those existing source modifications are
not new Phase 3B-2A work. No performance benchmark was rerun or optimisation
implemented. Real garment calibration and release validation were not executed
because the reviewed datasets and approved acceptance criteria are absent.
