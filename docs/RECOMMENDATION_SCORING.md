# Phase 4A: independent experimental scoring and top-one ranking

## Authority and integration boundary

Original report RN-15–RN-21 and sections 4.4.3 (printed pp.221–222), 4.10.4
(pp.274–277) define separate RequestMatchScorer, CompatibilityScorer,
PreferenceScorer, RecommendationScorer and CandidateRanker responsibilities.
The formula is S = w_r R + w_c C + w_p P, weights summing to one, with total,
request, compatibility, preference, stable identifier tie-breaking. FR-PP-03/05
motivate supported preference values; section 4.8.2 describes type/value records.
Exact formulas, profiles and preference conventions below are user-approved
Phase 4A implementation policies, not report-specified numerical constants.

This is explicitly invoked infrastructure. No default/live recommendation
selection, frontend, history/recommendation persistence, account APIs, schema,
Phase 1–3 contracts, Digital Wardrobe or CV code is changed. Existing placeholder
live scores remain historical/scaffold behaviour, not replaced by these results.
Approximate hex evidence remains disabled. Suitability remains opt-in. Homepage
random selection does not use this scorer. No new dependencies/models are added.

```python
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.recommendation_scorer import RecommendationScorer

# user_id comes from authenticated application context, not an untrusted payload.
# Inject existing ConfirmedGarmentQuery and the new ActivePreferenceQuery.
engine = RequestCandidateEngine(confirmed_query)
scorer = RecommendationScorer(engine, preference_query)
outcome = scorer.rank(user_id, structured_request, "compatibility_deferred")
# Only outcome.status == "Selected" has a final winner. No writes are performed.
```

To use approved occasion/formality declarations, the caller must separately
construct the engine with evaluator_factory=SuitabilityRequestEvaluator. This
example does not do so. No profile is silently selected or activated by default.

## Read-only preference model

ActivePreferenceQuery.get_active_preferences(user_id) returns immutable raw
PreferenceSnapshot values. SqliteActivePreferenceQuery requires an existing
active account and SELECTs only its is_active=1 rows, ordered by type/id. SQLite
is opened with mode=ro and a read transaction: no database creation or writes. It
does not register/authenticate a user, infer a current identity or write records.
Like Phase 1, trusted application composition supplies the authenticated ID.
SQL remains in the new adapter, outside scoring. Existing APIs/storage remain
permissive; scoring normalization does not claim to fix API-level FR-PP-05.

| Supported type | Required value object | Matching semantics |
|---|---|---|
| colours | {"values":["blue","black"]} | Any alternative recognized current primary occurs |
| styles | {"values":["classic","vintage"]} | Fraction of base garments matching any alternative |
| garment_categories | {"values":[{"kind":"group","value":"top"}]} | Any alternative category/group occurs collectively |
| formality | {"values":["casual","smart_casual"]} | One common preferred value is positively allowed by every constituent |

Values use the completed vocabulary and existing aliases, with trim/case/space
normalization. Groups remain groups; overlapping category preferences do not
double count. style_note only recognizes a whole exact approved style/alias
under {"value":"minimal"}. Longer prose is unsupported, never keyword-mined.
Structured active positive-weight styles overrides a recognized style_note.
No preference inference, dislikes, favourites or historical learning is added.

Missing importance defaults to 1. Zero-weight and inactive records are ignored
before scoring/precedence, with diagnostics. Unknown types and unsupported
style_note prose are retained in storage and diagnosed as unsupported. Formal
formality preferences (including mixed lists containing it) are diagnosed as an
unavailable capability; no partial supported list is silently substituted.
Malformed supported JSON/values, nonfinite/out-of-range importance, foreign
ownership or duplicate active positive-weight supported types produce
InvalidPreferenceData. A malformed structured preference does not silently fall
back to a note. Duplicates are not repaired/deleted. Zero-weight malformed values
are not interpreted because they have no scoring influence.

No local runtime database existed at design inspection. The known frontend
convention is free-text style_note with importance 1; most existing prose notes
therefore cannot directly personalize these scores. Structured preference entry
is possible through existing APIs, not new frontend controls.

## Request-match component R

Score only gate-verified passing candidates. Compute a mean over supplied FIELD
types, not individual colour/category tokens. Category, global colour, occasion
and formality contribute 1 only after their mandatory evidence passes. Style
contributes positively matching base garments / number of base garments.
Outerwear is excluded from this style denominator as in the completed minimum
style rule. Unknown style has no positive contribution; detailed reasons retain
missing/malformed/unrecognized states. Supported positive tags remain evidence
even when other style tags are unrecognized, consistent with Phase 3B-1.

No optional fields means NotApplicable, value null, numerical contribution 0.
Unknown mandatory evidence never receives a score. Unsupported occasion or
formality does not become a scored default. Suitability binary scores mean
owner-declared minimum evidence, not measured appropriateness or confidence.
Global colour presence is not a colour prominence/harmony measure. Only current
primary aliases/exact anchors qualify; stale palettes and approximate hex do not.

## Experimental compatibility C and fairness

compatibility_deferred uses C=Unavailable (null value, contribution 0).
three_component_experimental uses shared-style annotation Jaccard per garment
pair, including optional outerwear: |A intersect B| / |A union B|. A pair needs
two complete Known nonempty canonical style sets. Otherwise its state is Unknown.
Average supported pair contributions over ALL pairs; unknown pairs stay in the
denominator with no positive evidence. All unknown pairs yield Unknown/null.
Partial and complete evidence coverage remain distinct. Different styles are
not hard violations; the measure is shared annotations, not objective fashion
compatibility. No colour harmony, pattern, physical-fit or layering score exists.

A single dress without outerwear has no pair. The three-component profile
rejects the ENTIRE affected ranking session with ProfileUnavailable and no
winner, even if an earlier two-piece candidate was provisionally best. It does
not score the dress as 0 or 1, silently skip it, switch weights or return a
partial success. The caller can explicitly rerun the entire session using
compatibility_deferred. This also conservatively rejects singleton-only sessions.
No candidate truncation is used to avoid an unsupported structure.

Full compatibility scoring remains incomplete: multi-structure comparability,
reviewed aesthetic criteria, annotation coverage and independent ranking quality
need further work. The deferred profile does not complete RN-17's intended
three-component capability. Shared-style Jaccard is an experimental heuristic.

## Preference component P and diagnostics

For supported positive-weight records t: P = sum(a_t p_t) / sum(a_t). Preferred
values are alternatives, not mandatory conditions. Colour/category matches are
binary presence, style is base-garment coverage, and formality needs one common
positively declared level across all constituents. Different allowed formality
values do not form a hierarchy. Explicit denial of every preferred common level
is known nonmatching; incomplete/conflicting declarations remain unknown.

Unknown candidate attributes have zero positive numerical contribution but their
importance remains in the denominator; no evidence-only renormalization occurs.
NoPreferences/NoSupportedPreferences/Unknown/null are distinct from Available/0
(confirmed nonmatch). Mixed evidence is Partial, with diagnostic detail and
coverage. No preference can admit a candidate failing a mandatory condition.

ScoreEvidence, ComponentScore, RecommendationScore, VerifiedScoringInput,
ScoredCandidate, RankingOutcome and preference structures are immutable; caller
collections are normalized to tuples. Numerical values are Fraction, bounded
0–1. Null availability contributes zero without asserting a true quality score.
Scores are evidence measures, not probabilities. Metadata is not written into
historical records.

## Profiles and exact ranking

| Explicit profile | R / C / P weights | Status |
|---|---|---|
| compatibility_deferred | 0.70 / 0.00 / 0.30 | Interim experimental option |
| three_component_experimental | 0.50 / 0.30 / 0.20 | Shared-style experiment; rejects unpaired candidates |

scoring_policy.v1.json is versioned phase4a-1.0.0, with default_activation false.
Weights are parsed using decimal text then Fraction, preventing 0.1+0.2-style
validation errors. Finite, nonnegative weights must sum EXACTLY to one. Booleans,
NaN, infinity, negatives and wrong sums fail. Disabled compatibility requires
zero compatibility weight. No per-candidate renormalization occurs. All outputs
record profile name, version and the actual immutable weight tuple. Change the
policy version with semantic changes; do not compare different-profile totals.

CandidateRanker compares descending S, R, C, P, then ascending existing
candidate.key (role, garment-ID tuples). Exact fractions, not rounded displays,
determine ties. A zero component weight does not remove that component from the
report-prescribed tie sequence when its measure exists; the deferred profile
explicitly disables C, including its tie contribution. Individual zero-weight
preferences never enter P. Different scoring contexts/profiles cannot be compared.

## Verified context, streaming and failures

RecommendationScorer creates a fresh session through its injected engine.
ScoringEligibilityGate binds request equality, user ownership and a fresh
unconsumed RequestCandidateSession. It accepts only approved evaluator types and
independently recomputes mandatory conditions with a fresh approved evaluator.
The emitted evaluation must match exactly, including requested condition coverage
and evidence. Empty forged Pass coverage, foreign candidates, bare structural
candidates, stale sessions and mismatched requests are rejected before scoring.
The verifier cannot certify a malicious Phase 1 adapter; confirmation/availability
remain that contract's responsibility. Internal DI is trusted, not an external
authentication or cryptographic boundary. A per-gate nonce prevents cross-session
comparison, but does not affect candidate ordering or numerical reproducibility.

The scorer holds only one provisional best and count, plus bounded per-garment
evidence caches. It never collects all candidates. It publishes Selected only
after successful full exhaustion, accepted-count consistency and safe close.
An exception, incomplete stop, close failure or interruption discards the best.
Outcome states distinguish original no-result/structural/capability outcomes,
ProfileUnavailable, InvalidPreferenceData, InvalidScoringInput, ProcessingFailure
and Interrupted. Failure outcomes cannot carry a winner or claim completion.

Revalidation adds work; this is not a performance optimisation. Existing
200-garment enumeration/filtering risk remains and scoring adds cost. No new
end-to-end latency claim is made. No recommendations or chat history are written.

## Worked exact calculations

Request: campus, casual clothes, vintage style, global blue, top and trousers.
Every garment below allows campus and casual through the opt-in declaration
policy. A is blue vintage top + black classic trousers. B is blue vintage top +
grey vintage/classic trousers. Preferences: black importance .6 and classic .4.

| Component | A | B |
|---|---|---|
| R | (1+1+1/2+1+1)/5 = 9/10 | 1 |
| C shared-style | 0 | 1/2 |
| P | .6(1)+.4(1/2) = 4/5 | .6(0)+.4(1/2) = 1/5 |
| S three-component | .5(.9)+.3(0)+.2(.8) = .61 | .5(1)+.3(.5)+.2(.2) = .69 |
| S deferred | .7(.9)+.3(.8) = .87 | .7(1)+.3(.2) = .76 |

Unit tests assert these fractions and both winning candidates. These are worked
policy examples, not empirical validation or weight fitting.

## Existing integration blocker

The extraction frontend sends neckline/sleeve_length even when null. Backend
ReviewItem rejects them with 422; confirmation of the unaccepted item then
returns 409. Phase 3B-3A API tests reproduce this. Teammates must reconcile the
payload/allowlist under separate approval. No fix is included here. Manual
technical suitability tags, stale declarations and absent review provenance
also remain limitations. No friendly annotation/preference UI is added.

## Executed verification (2026-10-15)

Run from backend, using the existing isolated test runtime:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Final focused result: **65 passed**, one Starlette TestClient deprecation warning,
2.77s. Final combined regression selection: **430 passed, 1 failed**, same
warning, 20.83s. Remaining failure is the existing
test_report_architecture.py:28 assertion that the existing ai-services folder
must be absent. No folder deletion/restructure or assertion removal occurred.

Tests cover actual preference create/update/read projection, owner/inactive
filtering, read-only missing-database handling, normalization and weights,
fractions, missing vs nonmatch, all ranking tie stages, profile/context mismatch,
singleton fairness, failures after a provisional winner, incomplete/close-error
streams, no history/recommendation writes and Phase 1–3 regressions. The actual
query integration verifies NULL processing links still cannot enter scoring.

`git diff --check` passed from the repository root. A separate whitespace check
also covered all 19 newly created Phase 4A files, because normal git diff does
not include untracked additions. Earlier phase working-tree changes were not
edited as part of this phase. Browser E2E, PostgreSQL deployment execution,
independent preference/compatibility quality evaluation and new performance
benchmarks were not run. No end-to-end response-time or final RN-28 result is
claimed. Infrastructure status: PASS WITH LIMITATIONS, pending owner review.
