# Phase 4B-A: experimental whole-outfit reference infrastructure

## Requirements, approval and boundaries

The original report, sections 4.4.3 (printed pp.221–222) and 4.10.4
(pp.274–277), defines separate scoring responsibilities, normalized R/C/P,
S=w_r R+w_c C+w_p P, and total/R/C/P/stable-ID tie-breaking. RN-15–RN-21
requires mandatory validity before scoring and exactly one highest-ranked valid
candidate. The report does not specify reference signatures, individual ratings,
colour/pattern clash tables, thresholds or these exact weights. The policies
below are approved experimental implementation decisions, not report rules.

No live/default integration, frontend, persistence/history, CV/Digital Wardrobe,
Phase 1–4A source/contract changes or candidate-generation optimisations occur.
Request-match, preferences, exact arithmetic, eligibility and ranking are reused.
The existing Jaccard and compatibility-deferred profiles remain unchanged.
Approximate hex matching stays disabled and suitability stays opt-in.

## Structure-aware signatures

A complete descriptor contains a sorted canonical style SET, recognized current
primary colour and recognized pattern. Styles must have complete Known nonempty
evidence; unrecognized extra tags are not silently discarded. Colour uses only
Phase 3B-1 aliases/exact anchors. Existing corrected primary precedence applies;
secondary/palette information never substitutes for it. Pattern matching is
case/whitespace normalized exact matching of existing extraction-review options,
without invented aliases such as solid -> plain. New pattern values are rejected.

| structure | Actual ordered signature roles |
|---|---|
| top_bottom | upper, lower |
| top_bottom_outerwear | upper, lower, outerwear |
| dress | one_piece |
| dress_outerwear | one_piece, outerwear |

The signature includes structure AND actual roles/descriptors. A dress appears
exactly once. It is neither duplicated nor equated to two separate garments.
Different structures can have different independently reviewed values even if
their descriptors coincide. Within a structure, garment IDs, input order and
equivalent canonical aliases do not change the signature. Multiple style tags
remain a full set. Outerwear absence is a supported structure, not missing data.

No garment-count bonus, pair-count denominator, self-pair, automatic perfect or
neutral score exists. Fit/material/physical layering, pattern harmony and Oklab
similarity are not inferred as aesthetic criteria. Structural roles only locate
the actual garments; structural validity itself earns no compatibility score.

## Versioned reviewed references

config/compatibility_references.v1.json is the production-format experimental
policy. It is available as infrastructure, has activation_approved false and
an EMPTY references list. No actual reviewed outfit ratings exist here.

Each reference contains:

- reference_id and a complete structure-aware signature;
- individual reviewer_id/rating records, integer grades 0–4;
- adjudication reviewer_id, decision and explanatory note;
- source_ids for auditable outfit/garment/image source groups;
- approval_status: draft, approved or rejected;
- independently_reviewed declaration;
- normalized_value with exact numerator/denominator.

Rubric: 0 very poorly coordinated, 1 weak, 2 mixed/ordinary, 3 coordinated,
4 strongly coordinated. It is experimental and subjective. For m accepted
individual ratings, q=sum(ratings)/(4*m). The declared normalized value must
equal that exact rational. At least two distinct reviewer declarations and
accepted adjudication are required for approved entries. Only approved entries
can provide numeric evidence. Complete draft/rejected records are retained but
not scored. Duplicate IDs/signatures, inconsistent values, invalid roles,
unknown attributes, noninteger/out-of-range ratings and missing provenance fail
configuration validation. There is no arbitrary first-match conflict resolution.

Approved real entries require independently_reviewed true. Software validates
the declaration, not the honesty/independence of its authors; external audit is
essential. All policy records, descriptors, ratings and lookup collections are
immutable. Configuration version and SHA-256 content hash accompany results.

The sole populated reference file is tests/fixtures/
compatibility_references.synthetic.v1.json. Its kind is synthetic_fixture;
reviewer/source identifiers are explicitly synthetic and independently_reviewed
is false. Both policy loading and experimental ranking require explicit fixture
opt-in. These records are not real approvals and cannot claim human validation.

## Unknown, zero and availability

| Evidence | Result |
|---|---|
| Approved reference with rating 0 | Available, exact value 0 |
| Complete evidence, no approved reference | Unknown, null value, missing_approved_reference reason |
| Missing/malformed/unrecognized required attribute | Unknown, null value, individual reasons and descriptor coverage |
| Policy marked unavailable | Unavailable, null value, policy_unavailable reason |
| Single dress | Same holistic lookup rules as every structure; no NotApplicable C |

Descriptor coverage (recognized fields / 3 per garment) is diagnostic, never a
compatibility rating. Complete evidence can still have unknown reference coverage.
The scorer does not partially match signatures or interpolate from another
structure. Unknown contributes numerical zero ONLY under this explicit experiment;
it is not proven incompatibility. Zero ratings do not create a new hard rejection.
Unknown candidates are retained, may win through R/P, and do not reject sessions.
No per-candidate weight renormalization or silent profile switch occurs.

## Explicit scoring architecture

The existing five-class roles remain: HolisticRecommendationScorer specializes
RecommendationScorer; HolisticCompatibilityScorer specializes CompatibilityScorer;
Phase 4A RequestMatchScorer, PreferenceScorer and CandidateRanker are reused.
Separate experimental orchestration preserves closed Phase 4A profile/constructor
contracts and defaults. Completion/error behaviour is tested against the existing
pipeline. This intentional small orchestration duplication avoids refactoring the
approved pipeline; future shared orchestration needs separate review.

```python
engine = RequestCandidateEngine(confirmed_query)
scorer = HolisticRecommendationScorer(engine, active_preference_query)
outcome = scorer.rank(authenticated_user_id, structured_request, "holistic_experimental")
```

No live wiring calls this class. To support occasion/formality requests, callers
must separately inject SuitabilityRequestEvaluator into the candidate engine.
The experiment never changes that default. The new scoring_policy.v2.json
contains the explicit phase4ba-1.0.0 holistic_experimental profile, with exact
weights 0.50/0.30/0.20 and default_activation false. Phase 4A profile v1 is unchanged.
The profile is not selected automatically by the old coordinator.

The Phase 4A gate verifies fresh request/session context, ownership and exact
mandatory-condition coverage. R/P computations and immutable score objects are
unchanged. One provisional winner is retained; only complete exhaustion with
consistent counts and safe close publishes Selected. Late failures, incomplete
StopIteration and interrupts discard it. Coverage diagnostics on incomplete
outcomes are partial counts, not complete coverage rates. No recommendation or
chat-history record is written.

Garment evidence is cached once per session; conflicting snapshots fail. Candidate
signatures contain at most three actual descriptors. Reference lookup is a hash
lookup. Candidates are never materialized or truncated. Only reference records,
wardrobe evidence caches, fixed structure counters and one best candidate are
retained. Existing 200-garment latency risk remains; no new performance claim or
unrelated optimisation is made.

## Synthetic worked calculations (not review evidence)

The unit-test fixture supplies the following illustrative ratings for identical
vintage/blue/plain descriptors across structures. Their differences demonstrate
separate review lookup, not a garment-count or aesthetic rule.

| Structure | Synthetic ratings | C | S with no request fields/preferences |
|---|---|---|---|
| Top + bottom | 3,3 | 6/8 = 3/4 | .30*(3/4) = .225 |
| Top + bottom + outerwear | 2,3 | 5/8 | .1875 |
| Single dress | 2,2 | 4/8 = 1/2 | .15 |
| Dress + outerwear | 3,4 | 7/8 | .2625 |
| Test-only reviewed-zero dress | 0,0 | 0, Available | 0 |
| Unreviewed/incomplete outfit | None | null, Unknown | 0 contribution |

R is NotApplicable and P is NoPreferences in the generic example. No perfect
defaults or per-candidate weight changes are used. The single dress is neither
excluded nor assigned a pair baseline.

Weight sensitivity is tested with temporary synthetic-only profile files:
a reviewed blue dress C=1/2, P=0 competes with an unreviewed red dress C=null,
P=1 for a red preference. Under .50/.30/.20, their totals are .15 and .20.
Under a test-only .40/.50/.10 profile they are .25 and .10. The winner changes;
every candidate in each run uses the SAME weights. Extra trial weights are not
added to the production profile configuration.

## Reproducible evaluation tooling

From backend:

```powershell
uv run --no-project --python 3.12 python -B scripts/evaluate_compatibility.py --output runs/compatibility/reference_audit.v1.json
```

Without cases this audits actual reference availability, not candidate accuracy.
With --cases PATH, --profiles-file PATH and --profiles NAME [NAME ...], it runs
one fresh streaming session per case/profile. --partition validation additionally
requires --confirm-locked-validation. --allow-synthetic-fixtures is test-only
acknowledgement. Outputs cannot overwrite inputs. Reports include reference,
profile and dataset versions/hashes, exact component/total values, deterministic
winner IDs, winner changes across profiles and per-structure examined/reviewed/
unknown/unavailable/incomplete counts. Reviewed-zero counts as reviewed coverage.
Incomplete streams have no complete coverage fraction.

Case JSON: schema_version 1.0.0, version, kind (held_out_review_dataset or explicitly
synthetic_fixture), validation_locked true, cases. Each case has case_id,
partition (development/validation), source_ids, user_id, wardrobe (serialized
ConfirmedGarmentSnapshot records), request and optional PreferenceSnapshot list.
These are offline captured evaluation inputs, NOT proof of current production
confirmation. Runtime ranking still uses the real Phase 1 query. Suitability is
explicitly selected in this offline tool to exercise supported test requests.

Duplicate case IDs, cross-partition source overlap and validation sources shared
with reference data are rejected. Use source_ids containing garment/image group
IDs, not merely unrelated outfit aliases. These checks cannot detect unreported
aliases or dishonest provenance. Validation locking is a procedural declaration,
not access control. Tool evaluation reports independent_validation_complete false
and fashion_accuracy null; arithmetic/coverage is not reviewed fashion accuracy.

## Independent review, held-out validation and future activation

Collect balanced examples of all four structures, with complete reviewed style,
named primary and pattern evidence. Have independent reviewers rate actual outfit
examples using the common rubric, blinded to scores, preferences and expected
winners. Preserve individual ratings/disagreements, source groups and adjudication.
Assess whether identical metadata genuinely supports shared ratings; review
structure-specific bias rather than enforcing equal averages across structures.

Freeze reference/configuration hashes before holdout evaluation. Holdout garments
and source images must not occur in reference/development groups. Report seen
signatures with new garments separately from unseen signatures. Compare deferred,
historical Jaccard (applicable subset) and holistic methods, reporting coverage per
structure, reviewer agreement, ranking agreement and top-choice agreement. A
separate reviewed-label analysis is required for quality metrics; no such labels
exist here. Weight fitting/refinement must use development data, with final weights
frozen before independent validation. No accuracy or coverage threshold is invented
from RN-27 or the report.

Future session-level coverage policy proposal (NOT implemented): agree coverage
requirements overall and per represented structure, then evaluate complete-stream
coverage. Below that requirement, do not publish a normal holistic recommendation;
rerun the ENTIRE session using an explicitly authorized deferred profile, retaining
all valid structures. Do not switch individual weights. Rerun freshness, latency,
outcome semantics and permission for automatic fallback need separate approval.
This is an interim coverage safeguard, not a final substitute for reviewed data.

Current actual evidence: ZERO approved real references, ZERO independently
validated outfit examples, coverage/accuracy unmeasured. Required before normal
activation: collected and audited reviews, held-out validation, cross-structure
coverage/fairness evidence, agreed weight/coverage policies, explicit integration
approval and response-time verification. Empty reference data currently permits
only an explicitly experimental R/P/stable-ID ranking with Unknown C.

The existing frontend review neckline/sleeve_length payload causes 422 and then
409 confirmation; it remains a teammate coordination blocker and is unchanged.
Technical suitability tag UX, stale declarations and absent review provenance
remain prior-phase limitations. No frontend controls or colour calibration occur.

## Executed verification (2026-10-17)

Commands from backend (the test runtime uses isolated storage/development AI):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_holistic_compatibility.py tests/test_holistic_ranking.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/evaluate_compatibility.py --output runs/compatibility/reference_audit.v1.json
```

Focused: **48 passed**, one Starlette TestClient deprecation warning, 2.69s.
Combined regression selection: **478 passed, 1 failed**, same warning, 28.68s.
Remaining failure is the existing test_report_architecture.py:28 assertion that
ai-services must be absent. No folder deletion/restructure or assertion removal
was performed. Reference audit exited successfully: 0 approved real references,
0 evaluated cases, independent validation false, accuracy/coverage unmeasured.

Tests cover every structure, no dress duplication, equivalent signatures,
multiple styles, primary precedence, malformed/missing attributes, actual zero
versus unknown, approval validation, immutable records, per-structure coverage,
mixed-reference ranking, synthetic weight sensitivity, deterministic winners,
partition leakage guards, preserved old profiles, strict Phase 1 query integration,
no persistence/history writes and complete-stream failure guarantees.

`git diff --check` passed at repository root. A separate new-file whitespace
check covered all 13 new source/test/config/document files. Before/after SHA-256
comparison of 53 existing recommendation, shared-contract, value-object, wiring,
main and review-page files found no changes. Prior working-tree edits are not
new Phase 4B-A source changes. Only the two traceability/rules docs were updated.
The generated audit JSON is an additional runtime artifact, not review data.

No browser E2E, PostgreSQL deployment test, independent outfit validation or
performance benchmark was executed. Compatibility quality and activation remain
incomplete. Infrastructure verification: PASS WITH LIMITATIONS pending review.
