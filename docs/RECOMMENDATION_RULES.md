# Phase 3A: structural outfit candidates

Phase 4B-A adds a separate [structure-aware reviewed-reference experiment](OUTFIT_COMPATIBILITY_POLICY.md).
Dress signatures contain one actual one_piece member and differ from two-piece
signatures. All structures use the same 0–4 normalization without count bonuses.
The real reference set is empty: no independent compatibility quality is claimed.
Unknown C has explicit experimental zero contribution without asserting a clash;
reviewed zero and unavailable policy remain distinct. All valid candidates stay
in the stream. The new explicit holistic profile/coordinator leaves prior R/P,
Jaccard/deferred profiles, eligibility, exact arithmetic, ranking and defaults
unchanged. No live integration, approximation activation or optimisation occurs.

Phase 4A adds [independent experimental scoring/ranking](RECOMMENDATION_SCORING.md).
It scores only session/request-verified minimum-valid candidates and publishes
one winner only after full stream completion. Structured preferences are read
without account/persistence changes. Profiles must be explicitly selected;
the deferred profile uses 0.70/0/0.30, while experimental shared-style Jaccard
uses 0.50/0.30/0.20 and rejects sessions containing a passing unpaired dress.
No per-candidate weight changes, live wiring, default suitability activation,
approximate hex evidence, history writes or generator optimisations are added.
Compatibility/personalisation validation and end-to-end performance remain
incomplete. The phase-specific historical sections below retain their scopes.

Phase 3B-3A adds explicitly injected [owner-declared suitability infrastructure](OCCASION_FORMALITY_POLICY.md).
The default evaluator still rejects supplied occasion/formality with
PolicyUnavailable. Opt-in SuitabilityRequestEvaluator supports eight occasions
and casual/smart_casual declarations through reserved rec:v1 custom tags;
exercise/formal remain unavailable. Every constituent, including outerwear,
requires allow evidence; deny wins over other garments' unknown evidence,
conflicts/missing/malformed stay unknown. No style-to-occasion/formality inference
or aesthetic claim is introduced. No live/default wiring changes occur.
Backend tag persistence is verified; the existing extraction frontend's rejected
neckline/sleeve_length payload blocks normal acceptance and needs teammate work.
Technical tag entry, stale declarations and absent review provenance remain
limitations. Approximate mandatory colour matching stays disabled.

Phase 3B-2A adds isolated [Oklab experiment infrastructure](COLOUR_CLASSIFICATION.md).
Its 30 prototype swatches are initial unreviewed candidates, not exact anchors
or calibrated evidence. Mandatory colour matching remains Phase 3B-1 aliases
and thirteen exact anchors only. Experimental Recognised/Ambiguous/Unknown
results cannot activate matching. Primary precedence, unknown handling and all
candidate/session interfaces remain unchanged. Empty-pixel CV fallback black
is indistinguishable from genuine black in the existing snapshot; confirmation
does not establish extraction success. Real calibration and validation, occasion/
formality, scoring, ranking and live integration remain incomplete. The previous
200-garment profiling findings are documented separately; no optimisation occurs.

## Authority and exact scope

The original Chong Wei Ping Project I report defines controlled garment
acquisition and eligibility (RN-11–RN-14, CA-03/04, section 4.10.2), mandatory
outfit structure before scoring (RN-15/16, section 4.10.3), separate candidate,
rule and engine responsibilities (section 4.4.3), and shared homepage/NLP
generation principles (section 4.5.2). Exact compositions below are explicitly
user-approved Phase 3A implementation rules, not verbatim report rules.

Phase 3A is independent and not connected to the live recommendation service,
routes, persistence, history, frontend or visualisation. Phase 1 and Phase 2
contracts are unchanged. No preference matching, colour/style/occasion/formality
policy, compatibility scoring, ranking or selection is implemented.

## Structures, categories and stable identities

| Allowed composition | Item roles/order |
| --- | --- |
| Exactly one top + exactly one bottom | upper, lower |
| Top + bottom + exactly one outerwear | upper, lower, outerwear |
| Exactly one dress | one_piece |
| Dress + exactly one outerwear | one_piece, outerwear |

No top/bottom/outerwear alone, dress plus top/bottom, duplicate IDs, competing
slots or multiple outerwear are allowed. Optional layering is only one outerwear
over a complete base. Footwear/accessories and new garment categories are absent.
Outerwear remains a valid recommendation role; VTON's separate lack of outerwear
support is unchanged.

GARMENT_STRUCTURE supplies the existing thirteen exact category mappings:
short_sleeve_top, long_sleeve_top, vest and sling -> top/upper;
shorts, trousers and skirt -> bottom/lower; the four dress categories ->
dress/one_piece; the two outwear categories -> outerwear. Layering indices must
agree with the existing mapping; they do not establish physical compatibility.
No category aliases or substring heuristic is used.

Each OutfitCandidate contains immutable CandidateMember records referencing
actual snapshots. Candidate validity is STRUCTURALLY_VALID only. Members are
ordered by structural slots and numbered from one. The key is the tuple of
(candidate role, garment ID) pairs; candidate_id is SHA-256 of that key's compact
JSON encoding. This identifies a temporary candidate, never a new garment or
persisted recommendation. Input order, names and favourites cannot change it.

## Acquisition and structural eligibility

GarmentRetrievalService receives an injected ConfirmedGarmentQuery and calls
only get_confirmed_available_garments(user_id). It never accesses SQL, saved
outfits or the legacy ID method. Phase 1 remains the confirmation authority:
only owned, available records with linked confirmed processing items are
provided; NULL/accepted/pending/rejected/missing links remain excluded there.

Defensive structural validation excludes invalid snapshot types, blank garment
or media IDs, owner/status mismatch, unsupported categories and inconsistent
role/layer mappings, with immutable diagnostics. Identical duplicate snapshots
are deduplicated; conflicting snapshots for one ID cause a controlled setup
failure. Missing optional colour/style/fit/material and invalid optional-field
metadata do not gate structural eligibility. No private processing data is read
to repeat confirmation management.

## Lazy generation and completion protocol

CandidateGenerator groups by exact structural role, deduplicates records and
sorts each slot by garment ID. It enumerates the four approved composition
products in configuration order and passes each to MandatoryRuleEvaluator's
structure-only check. Canonical role slots and unique IDs avoid permutation
duplicates without retaining a set proportional to all candidate combinations.

RecommendationEngine accepts its query by constructor injection. Both
generate_homepage_candidates(user_id) and generate_nlp_candidates(user_id,
StructuredOutfitRequest()) share the structural path. An NLP request with any
non-null approved field returns PolicyUnavailable before retrieval: Phase 3B
conditions cannot be silently ignored. Raw text is not accepted by this engine.

The return value is a single-use CandidateGenerationSession. The candidates
yielded during consumption are structurally checked but the collection remains
provisional until the iterator is exhausted. Inspect session.result:

| Status | Meaning | complete |
| --- | --- | --- |
| Pending / Running | Stream not yet exhausted | false |
| StructuralCandidates | Exhausted stream with candidates | true |
| NoEligibleGarments | No structurally eligible input | true |
| InsufficientStructure | Eligible input cannot fill a base | true |
| NoStructuralCandidates | Base possible but evaluator yields none | true |
| ProcessingFailure | Acquisition/setup/iteration failed | false |
| Interrupted | Closed early or interrupted | false |
| PolicyUnavailable | Request-dependent Phase 3B rules unavailable | false |

complete certifies structural enumeration, never request/compatibility validity.
Use context management to record early exits:

```python
with engine.generate_homepage_candidates(user_id) as session:
    for candidate in session:
        consume_provisionally(candidate)
    result = session.result
    # Only result.complete with StructuralCandidates permits committing the
    # complete collection. Other statuses require their controlled handling.
```

Breaking without closing leaves Running, not success. Context exit or explicit
close marks Interrupted. An iteration exception marks ProcessingFailure and
raises CandidateProcessingError; consumers must discard partial work. A keyboard
interrupt is recorded and re-raised. Setup failures return controlled metadata
without internal exception messages. Sessions are not replayable or thread-safe.
No count limit, silent truncation or invalid fallback is used. Later consumers
must enforce this completion protocol before selection/persistence.

## Growth and benchmark interpretation

Exhaustive candidate count is (T*B+D)*(1+O). Working generation storage is
proportional to the garment index plus one candidate, not the candidate count.
No saved outfits are required. Scoring and random selection are future consumers.

Reproduce from backend/:

```powershell
uv run --no-project --python 3.12 python -B scripts/benchmark_structural_candidates.py --sizes 20 50 100 200 --output runs/structure/benchmark.v1.json
```

The script verifies both traced and uninstrumented passes against the formula,
records full completion, Python/OS/CPU metadata and source hashes, and saves
generated evidence under ignored runs/. Prebuilt synthetic snapshots simulate
the query boundary: this does not benchmark SQLite or confirmation. Retrieval
validation and complete enumeration are timed; fixture construction and policy
loading are excluded. Candidates are not retained. Tracemalloc measures Python
working allocations, not process RSS; its overhead is separately reported and
allocator warmup can produce nonmonotonic peaks.

The report's three-second homepage and five-second NLP targets are eventual
end-to-end requirements, not a Phase 3A threshold. No claim of meeting them is
made by this isolated benchmark. Larger wardrobes/outerwear counts multiply
enumeration costs; operational deadlines and baseline workloads remain to be
agreed. Interruption never permits treating a partial stream as complete.

## Verification and remaining scope

tests/test_structural_candidates.py covers every category, all structures,
duplicate/input-order invariance, an independent subset-combination oracle,
immutable candidates and completion metadata, invalid/missing data, capability
outcomes, exceptions/interruption, and real Phase 1 query integration with zero
saved outfits. Existing Phase 1/2, processing, wardrobe and visualisation tests
remain regressions. No full RN-28 request/compatibility-valid recommendation
claim is made: Phase 3B and Phase 4 are not implemented.

Existing live heuristic, score placeholders and historical/save behavior are
unchanged. The pre-existing ai-services architecture assertion remains separate;
no folder is deleted or restructured. Phase 3B-1 is a separate approved wrapper
documented below; subsequent policies still require fresh approval.

## Executed verification: 2026-10-14

Focused Phase 3A: **48 passed**, 1 existing TestClient deprecation warning, 2.33s.
Final regression selection: **213 passed, 1 failed**, 1 same warning, 18.30s.
The failure is the unchanged test_report_architecture.py:28 ai-services assertion.
git diff --check passed. Exact commands from backend/:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_structural_candidates.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Final exhaustive benchmark evidence is backend/runs/structure/benchmark.v1.json.
All expected counts matched and every stream completed:

| Garments (top/bottom/dress/outerwear) | Candidates | Uninstrumented seconds | Traced seconds | Peak traced bytes |
| --- | ---: | ---: | ---: | ---: |
| 20 (8/8/2/2) | 198 | 0.002485 | 0.019017 | 39,240 |
| 50 (20/20/5/5) | 2,430 | 0.042289 | 0.263888 | 153,752 |
| 100 (40/40/10/10) | 17,710 | 0.311293 | 1.573369 | 7,488 |
| 200 (80/80/20/20) | 134,820 | 2.904661 | 15.978134 | 13,720 |

These are single-run development measurements; the final benchmark overlapped
the regression process and is not an isolated capacity baseline. Earlier 200-item
uninstrumented enumeration was about 2.50s, illustrating timing variability.
Working-memory peaks vary with allocator reuse and are not total process memory.
No arbitrary candidate limit was imposed. At 200 garments, enumeration alone
already leaves little time for the eventual three-second homepage requirement;
larger wardrobes need measured optimization/integration planning. No end-to-end
performance acceptance is claimed.

Not executed: heavyweight segmentation tests, model quality/inference,
PostgreSQL deployment, live browser/frontend tests and production capacity tests.
No relevant frontend/model/schema behavior changed in Phase 3A.

## Phase 3B-1: approved minimum request constraints

This extension follows RN-12–RN-16 and sections 4.10.2–4.10.4, with the user's
explicitly approved minimum policies. The report does not prescribe the exact
colour anchors or style minimum. Completed Phase 1/2/3A classes and interfaces
are unchanged. RequestCandidateEngine receives a query or a Phase 3A engine by
constructor injection and uses Phase 3A's structurally validated stream. It is
not connected to the live recommendation service, persistence or frontend.

### Mandatory conditions and evidence

Every supplied category/group must occur somewhere in the complete candidate.
Group membership uses Phase 2's unchanged versioned mapping; a single specific
garment can satisfy overlapping broad and specific constraints. A top/trousers
request does not require every garment to be both categories.

Every supplied global colour needs recognized positive evidence from at least
one current primary colour. Current primary data is authoritative; secondary
colours and old palettes are never consulted to override it. No per-garment
colour binding is invented. Phase 2's unsupported bindings stay unsupported.

Requested style requires positive evidence on at least one base garment (upper,
lower or one_piece), never outerwear alone. Other constituent styles can differ
or be unknown. Matching a minimum does not establish whole-outfit aesthetic
compatibility. The mapper recognizes Phase 2's approved canonical styles and
aliases only; arbitrary custom tags are not suitability evidence.

Missing tags and malformed style_tags are unknown. Explicit empty tuples are
known empty/nonmatching. Unrecognized tags remain unknown; recognized matching
tags can provide positive evidence even alongside other unrecognized tags.
An invalid_attributes flag for style_tags invalidates that collection, so it
cannot provide positive evidence. All-known nonmatching styles fail; known
nonmatching plus missing/unrecognized evidence is Unknown, not proven failure.

Individual conditions are Pass, Fail or Unknown. Any Fail rejects the candidate,
even if another condition is Unknown. Otherwise any Unknown excludes it as
insufficient evidence. Only all-Pass candidates are emitted. Category membership
is definite because Phase 3A has already enforced supported consistent roles.

For colour, any recognized matching primary proves presence. If absent, an
unknown constituent primary means Unknown; absence across all recognized primary
colours means Fail. Blank/missing, invalid hex, unknown names and valid but
unmapped hex values are not positive evidence. Snapshot structural eligibility
is never changed by these annotations.

### Exact hex anchors; approximation deferred

The exact thirteen anchors in config/request_policy.v1.json reproduce the W3C
CSS Color 4 named-colour definitions:
https://www.w3.org/TR/css-color-4/#named-colors . These are standard reference
values, not calibrated ranges for garment photographs or a claim of colour
classification accuracy. The configuration and independent expected-value tests
verify exact names/hex values; no RGB distance/HSV/Oklab thresholds are used.

| Anchor | Approved canonical name |
| --- | --- |
| #000000 | black |
| #ffffff | white |
| #808080 | grey |
| #000080 | navy |
| #0000ff | blue |
| #ff0000 | red |
| #008000 | green |
| #ffff00 | yellow |
| #ffa500 | orange |
| #ffc0cb | pink |
| #800080 | purple |
| #a52a2a | brown |
| #f5f5dc | beige |

Named aliases come from the existing NLP vocabulary (gray->grey, navy blue->navy).
Names are whitespace/case-normalized. #RGB is expanded to #RRGGBB and case is
normalized. Unsupported alpha hex and malformed hex remain malformed evidence.
Cream is supported as named text only: no arbitrary cream anchor is introduced.
#00007f does not match navy's #000080, and CSS lime #00ff00 is not silently
mapped to the approved green name. Approximate hex classification/calibration
is explicitly deferred to Phase 3B-2. Real CV K-means outputs will frequently
remain unknown; this is a coverage limitation, not a negative colour finding.

### Capability and completion protocol

Supplying occasion or formality returns PolicyUnavailable before retrieval.
These are supported NLP fields with downstream matching deferred to Phase 3B-3;
they are never silently omitted, mapped from style or described as no wardrobe
match. Other noncanonical request values also produce PolicyUnavailable.

EvaluatedCandidate wraps an unchanged structurally valid OutfitCandidate plus
immutable condition/evidence identifiers. Its validity label is
APPROVED_MINIMUM_REQUEST_CONDITIONS, not aesthetic or full integrated validity.
No scores/ranking/preferences are computed. Unknown evidence is not scored.

RequestCandidateSession.result records examined/passed/failed/unknown counts and
completion. MatchingCandidates requires an exhausted structural source and at
least one passing candidate. With no pass, any otherwise unresolved candidate
gives InsufficientEvidence; only definite failures give NoMatchingCandidates.
NoEligibleGarments, InsufficientStructure and NoStructuralCandidates retain
Phase 3A distinctions. Pending/Running, PolicyUnavailable, Interrupted and
ProcessingFailure never certify a completed candidate stream.

Consumers must treat emitted candidates as provisional until result.complete;
context management/explicit close marks early exit Interrupted. Source/evaluator
failures raise RequestProcessingError without exception detail and require
discarding partial output. Keyboard interrupts are recorded/re-raised. No silent
truncation or invalid fallback is permitted. Existing Phase 3A sessions remain
unchanged; no historical data is rewritten.

### Cache, safe optimization and performance

Each request session owns a fresh evidence mapper cache keyed by garment ID.
Each participating garment is classified at most once. Conflicting snapshots
for one ID cause failure rather than stale cached evidence. The default engine
creates a new evaluator per session; callers injecting a factory must likewise
return a fresh evaluator/cache rather than sharing one across sessions.

The only optimization is proof-based category-failure short-circuiting before
evidence classification. It skips request work for already rejected candidates,
not structural enumeration. The reference mode evaluates all conditions.
Accepted candidate order/sets and aggregate counts are tested and benchmarked
for equality. Rejected-candidate condition detail may be shorter in optimized
mode; no passing candidate or unresolved outcome is lost. No candidate budget
or approximation is introduced.

The previously measured 200-garment structural enumeration cost (~2.9s) remains
a performance risk before filtering/scoring/persistence. New benchmarks compare
exhaustive/reference and optimized request modes with identical stream hashes.
Synthetic timings include evidence/policy initialization, retrieval and complete
generation/filtering, but not SQL, frontend or ranking. Traced allocations are
measured in separate passes and do not represent RSS. No end-to-end target or
performance improvement is claimed without measurements.

### Tests and deferred work

tests/test_request_candidates.py covers collective/overlapping constraints,
global colours and exact aliases/anchors, primary precedence, base-style
evidence, missing/empty/malformed/nonmatching states, failure precedence,
capabilities, deterministic/exhaustive equivalence, per-session caching,
immutable outputs, interruption/errors and real Phase 1/2/3A integration.

Phase 3B-1 establishes only approved minimum conditions. Approximation is
Phase 3B-2; occasion/formality is Phase 3B-3. Fully integrated recommendation
validity and Phase 4 scoring/ranking are incomplete. Live recommendation and
frontend behavior is unchanged; no migration/AI model or teammate change occurs.

### Executed verification (2026-10-15)

Commands below run from `backend`, with `SMART_WARDROBE_VTOFF_ENABLED=off`
for tests. The focused suite passed **39 tests** (2.06s). The combined backend
regression suite passed **252 tests**, failed **1 test** (20.02s), and reported
one Starlette TestClient deprecation warning. The existing failure is
`test_report_architecture.py:28`, whose assertion requires the existing
`ai-services` directory to be absent. No directory was deleted or restructured.

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_request_candidates.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/benchmark_request_candidates.py --sizes 20 50 100 --output runs/request_constraints/benchmark.v1.json
uv run --no-project --python 3.12 python -B scripts/benchmark_request_candidates.py --sizes 200 --output runs/request_constraints/benchmark.200.v1.json
```

| Garments | Examined | Accepted | Failed | Unknown | Reference seconds | Optimized seconds | Reference / optimized peak traced bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 198 | 97 | 38 | 63 | 0.0123 | 0.0101 | 97,855 / 89,143 |
| 50 | 2,430 | 1,154 | 430 | 846 | 0.1278 | 0.1539 | 45,495 / 43,687 |
| 100 | 17,710 | 8,570 | 2,510 | 6,630 | 1.0390 | 1.0673 | 66,935 / 63,279 |
| 200 | 134,820 | 65,533 | 18,020 | 51,267 | 10.3453 | 8.9174 | 118,055 / 102,239 |

All runs completed exhaustively, with identical accepted-stream hashes and
aggregate counts between modes. Measurements are single synthetic runs, not
statistical capacity estimates; the 200-garment run initially overlapped the
regression run. Pruning is not a guaranteed speed improvement. Its observed
8.9s at 200 garments already exceeds the report's eventual 3s/5s end-to-end
targets before SQL or scoring, so performance readiness remains unresolved.
End-to-end/live UI behavior was not benchmarked because this module is not
integrated. `git diff --check` was also run from the repository root.


## Phase 5F-2E-3A: explicit experimental rule-based scoring

The approved colour/style rule-based scorer is independent and disabled by default.
It does not change structural generation, mandatory rules, Homepage or Assistant.
Unknown C blocks only its experimental whole-session path after full enumeration;
single dresses remain in the normal live flow. Pattern scoring and approximate
hex remain disabled. See [RULE_BASED_COMPATIBILITY.md](RULE_BASED_COMPATIBILITY.md)
for exact formulas, evidence states, tests, synthetic coverage and remaining RN17 gaps.


## Phase 5F-2E-3C-1: exact experimental pair cache

A separate opt-in cached twin preserves the unchanged Phase 3A colour/style
rules, exact Fraction scores, diagnostics and whole-session coverage safeguard.
Its session-local LRU holds at most 19,900 unordered pairs, rejects owner/policy/
snapshot/context conflicts and recomputes exactly after eviction. It does not
change live Homepage/Assistant behavior, mandatory validation or any ranking rule.
The uncached scorer and all frozen reference archives remain the oracle.
See [COMPATIBILITY_PAIR_CACHE.md](COMPATIBILITY_PAIR_CACHE.md) for file inventory,
differential checks, six-pair benchmarks, bounded-memory tradeoff and retention.
Single dresses still yield Unknown; no midpoint or no-pair convention is enabled.


## Phase 5F-2E-3C-2: explicit experimental compatibility decisions

A separately selected DecisionRecommendationScorer uses unchanged atomic rules
and the retained pair cache. It preserves raw evidence separately from exact
possible-value bounds and midpoint decisions. Single dresses have raw pairwise
NotApplicable and an explicitly conventional 1/2 no-pair contribution. It scores
every mandatory-valid candidate with exact 0.60R + 0.20C_decision + 0.20P and the
unchanged deterministic ranker, after independent mandatory verification.

No live registration, default, schema or persistence change is made. The old
uncached and cached Phase 3A scorers retain their original coverage refusal.
See [COMPATIBILITY_DECISION_POLICY.md](COMPATIBILITY_DECISION_POLICY.md) for the
versioned adapter, exact replay, synthetic examples, performance regressions and
academic/activation limitations. Unknown mandatory evidence never gains a pass.


## Phase 5F-2E-3C-3A: isolated prepared decision-scoring experiment

An explicit prepared twin reuses only numeric bounds facts and fixed policy
constants. The original Phase 3C-2 value objects, validators, codec and coordinator
remain the differential oracle. Atomic rules, all evidence/diagnostics, exact
60/20/20 decisions, independent gate and ranker are unchanged. The 256-entry
session-local arithmetic cache stores no candidate or raw user data; the retained
19,900-pair cache and complete-stream guarantees are preserved.

No live registration, feature flag, frontend, persistence or historical record is
changed. See [DECISION_SCORER_PERFORMANCE.md](DECISION_SCORER_PERFORMANCE.md) for
profiling, six-run comparisons, correctness checks, retain/revert decision,
integration blockers and the unresolved five-second requirement.
