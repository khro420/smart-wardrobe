# Phase 5F-2D-1: Assistant profiling and optimisation design

Date: 2026-10-18. Design/profiling only; no production algorithm is changed.
The application remains unapproved for final FYP acceptance.

## Authority and preserved behaviour

The original Project I report's NFR-02 (PDF page 180, printed page 169) requires
a recommendation, no-result or unsupported response within five seconds after
valid NLP submission in the baseline environment. It specifies no exemption
for large wardrobes and no median-only acceptance rule. Section 4.10.4
(printed pp.274-277, particularly PDF page 286/printed p.275) requires scoring
valid candidates, selecting exactly one highest-ranked candidate and retaining
the tie sequence total, request, compatibility, preference, stable identifier.
The primary PDF was re-read for these provisions, alongside `FYP_CONTEXT.md`,
the Phase 1-4 contracts and the actual implementation. The report does not
prescribe caching, lightweight constructors, a percentile gate or a speedup.

The current approved live policy remains exact R/C/P weights 7/10, 0, 3/10,
with compatibility Unavailable rather than perfect/neutral evidence.
Suitability is opt-in, approximate hex evidence disabled. None of these are
performance tuning parameters. Strict Phase 1 retrieval, independent gate
verification, snapshot/provenance binding and transactional revalidation must
remain intact. No write transaction may cover enumeration/ranking.

## Historical baseline versus new diagnosis

Phase 5F-1's accepted production-server observations are retained without being
relabeled as new measurements:

| Garments | Candidates | HTTP median / p95 [min,max], seconds | Chromium median [min,max], seconds |
| --- | --- | --- | --- |
| 20 | 198 | .074 / .103 [.064,.116] | .170 [.152,.192] |
| 50 | 2,430 | .539 / .649 [.439,.668] | .537 [.487,.596] |
| 100 | 17,710 | 2.974 / 3.131 [2.853,3.353] | 3.090 [3.010,3.939] |
| 200 | 134,820 | 21.823 / 24.252 [21.109,26.698] | 21.710 [21.565,24.677] |

Those measurements used Next 16.2.9, 20 HTTP/five browser trials, one excluded
warm-up, one sequential client and a production frontend. Next is now patched
to 16.4.2. The present backend-only runs are not new HTTP/browser measurements
and cannot establish a frontend speed change or NFR compliance.

New tooling: `backend/scripts/profile_outfit_assistant.py`. It imports unchanged
production code, creates disposable synthetic SQLite databases, sets data/DB
paths before importing persistence and verifies complete Selected results,
non-replay and the independently calculated candidate count. It records source
hashes, versions, wall time, process CPU time, production stage timers, CPU-clock
cProfile data and separate tracemalloc snapshots. No algorithm monkeypatch is
used. No network, browser, CV/VTON or deployment database is involved.

Wardrobes contain 40% tops, 40% bottoms, 10% dresses and remaining outerwear;
all are user-owned, available and linked to confirmed items/jobs, with current
blue primary colour and vintage style. Counts follow
`(tops*bottoms+dresses)*(1+outerwear)`. All four outfit structures occur. The
request is `Suggest an outfit with vintage style`, admitting every candidate.
There are no saved outfits. The optional preference scenario supplies four
immutable owner-scoped preference snapshots: blue/black colours, vintage/classic
styles, top category group and casual formality, each importance 1/2. No
suitability declarations are fabricated, so formality preference evidence is
Unknown. This is a stress scenario, not a population model of real wardrobes.

Timing excludes fixture creation and service construction; includes real NLP,
ranking, strict selected-garment revalidation and atomic writes. Preference
snapshots are injected rather than read through the account API: their scoring
cost is real, but this is not the full authenticated HTTP path. Every run has
a fresh submission key. Measurements with profiling/tracemalloc are never
accepted as uninstrumented response times.

Raw evidence is local under ignored `storage/verification/phase5f2d1/`.
The initial diagnostic script revision is archived there with its recorded
hash. A subsequent diagnostics-only revision corrects logged response keys
(`id`, `garment_role`) and adds baseline-only mode; initial null logging fields
are not used as identity/equivalence evidence. Initial smaller-size timing
overlapped PDF inspection; clean baseline-only trials are recorded separately.
Normal Windows/OneDrive activity is uncontrolled. CPU-clock profiles on this
host have quantised readings: small zero/sub-tick entries do not prove free work.

New resolved environment: Python 3.12.10, FastAPI 0.143.5, Pillow 13.0.0,
NumPy 2.5.4 and python-multipart 0.0.32, Windows 11 build 26200, eight logical
processors. FastAPI differs from the earlier audit's 0.143.3; historical HTTP
figures are retained as historical, not a matched before/after experiment.

Clean uninstrumented service baseline (five no-preference trials, three
populated-preference trials, plus one excluded warm-up per cell):

| Garments | Preferences | Candidates | Wall median [min,max], seconds | CPU median, seconds | Empirical p95, seconds |
| --- | --- | --- | --- | --- | --- |
| 20 | None | 198 | .038 [.037,.043] | .031 | .043 |
| 20 | Four types | 198 | .059 [.057,.060] | .047 | .060 |
| 50 | None | 2,430 | .298 [.288,.311] | .297 | .311 |
| 50 | Four types | 2,430 | .668 [.663,.700] | .672 | .700 |
| 100 | None | 17,710 | 2.886 [2.828,3.232] | 2.875 | 3.232 |
| 100 | Four types | 17,710 | 4.738 [4.727,4.923] | 4.703 | 4.923 |
| 200 | None | 134,820 | 22.671 [22.625,23.411] | 22.063 | 23.411 |
| 200 | Four types | 134,820 | 38.890 [38.340,39.919] | 36.000 | 39.919 |

20/50/100 use the later baseline-only run; 200 uses the original sequential
uninstrumented trials after PDF inspection had finished. p95 at n=3 or n=5
equals the sample maximum; do not interpret it as a precise population estimate.
The earlier exploratory 100-garment preference runs took 5.018-5.497s, while
the clean repeat took 4.727-4.923s: environmental/run variability matters, and
neither service-only sample proves browser compliance. No runs are discarded
from raw evidence; the exploratory and clean series are explicitly separate.

CPU-clock instrumented runs (not latency acceptance):

| Garments | Preferences | Total calls | Wall seconds | Process CPU seconds |
| --- | --- | --- | --- | --- |
| 20 | None | 144,760 | .247 | .234 |
| 50 | None | 1,623,145 | 4.207 | 3.859 |
| 100 | None | 11,701,080 | 26.019 | 24.469 |
| 200 | None | 88,921,300 | 182.825 | 178.172 |
| 200 | Four types | 146,512,058 | 307.509 | 301.688 |

Selected **cumulative CPU seconds** by size in the no-preference profiles:

| Work | 20 | 50 | 100 | 200 |
| --- | --- | --- | --- | --- |
| Candidate generation/construction | <clock tick | .359 | 2.547 | 16.578 |
| Both mandatory checks | .016 | .469 | 2.516 | 21.922 |
| Request-match scoring | .047 | .766 | 5.234 | 34.938 |
| Empty-preference scoring | .016 | .109 | .844 | 5.453 |
| Deferred compatibility | <clock tick | .125 | .594 | 5.609 |
| Candidate comparison | .031 | .328 | 2.219 | 18.531 |
| Mapper lookups/equality | <clock tick | .172 | .625 | 6.172 |

Call counts scale as N request/preference/comparison calls, 2N mandatory
evaluations and N+1 generator resumes. Actual colour classifier calls are
58/145/290/580, versus mapper lookups 1,434/18,540/138,130/1,064,460: caches
already work. Scoring's mapper only needs base garments in this scenario,
which explains fewer than 3G actual colour classifications across three caches.

A separate unranked request-stream probe drains exactly the expected candidates
then times only the terminal `next` and subsequent `close`. Terminal calls
took approximately 23.2/24.9/23.4/34.3 microseconds at 20/50/100/200; close took
0.5-1.4 microseconds. All ended MatchingCandidates with complete accounting.
These are single microdiagnostic observations, exclude ranking outcome creation
and persistence, and do not test every failure path. They show no large terminal
cleanup cost in this fixture; the repeated progress updates remain hot-loop work.

## Confirmed repeated work in code

| Path and entry point | Actual behaviour | Consequence |
| --- | --- | --- |
| `candidate_generator.py:27` | Creates CandidateMember objects and an OutfitCandidate for each valid product; `MandatoryRuleEvaluator` checks structure before OutfitCandidate checks it again. | Constructor/validation traffic grows with the exhaustive stream. Snapshot safety is intentional; do not delete checks casually. |
| `recommendation_engine.py:32` | Replaces immutable structural progress result per candidate. | O(N) short-lived result objects, despite streaming. |
| `request_candidate_session.py:29` | Evaluates mandatory conditions, replaces progress result, checks state repeatedly and emits an EvaluatedCandidate only for Pass. | Complete accounting and failure propagation are part of the contract. |
| `request_constraint_evaluator.py:13,22` | `evaluate` calls `supports` each time; builds condition/evaluation objects and performs cached mapper lookups. | Request support is invariant for an immutable request, but callers still need validation. |
| `scoring_eligibility_gate.py:36` | Independently recomputes evaluation and compares full condition/evidence IDs before sealing input. | Exactly two mandatory evaluations per accepted candidate are intentional anti-forgery protection. |
| `garment_evidence_mapper.py:20` | Already caches actual colour/style classification by garment ID; cache hits compare the stored full snapshot. | Repeated calls are mostly lookup/equality, not repeated colour normalization. Different same-ID snapshots must still fail. |
| `recommendation_scorer.py:20` | Normalizes preferences once, creates a fresh scoring mapper, computes exact weighted total, then constructs RecommendationScore. | No per-candidate preference normalization; another independent mapper/cache exists by design. |
| `request_match_scorer.py:11` | Builds base/evidence/reason lists and new exact evidence/components on every accepted candidate. | A style-only request's R and diagnostics do not depend on optional outerwear; repeated base combinations recur. |
| `preference_scorer.py:17` | Rebuilds allowed category sets, preference set intersections, coverage/reasons, weighted denominator, fractions and detail replacements per candidate. | With no preferences this is a constant empty result; populated preferences are substantially more work. Suitability parsing already caches garments. |
| `compatibility_scorer.py:17` | In deferred mode constructs the same unavailable component for every candidate. | Safe potential reuse, but no new compatibility evidence. |
| `recommendation_score.py:54` | Revalidates weights and recomputes exact weighted total already computed in rank. | Repeated fraction operations and constructor checks; removing the public validation is not approved. |
| `candidate_ranker.py:7,13` | Constructs candidate and incumbent keys each comparison, negating four fractions and reconstructing candidate role/ID tuples; checks session/profile equality. | Incumbent key is invariant while incumbent stays the same. Checks must survive cross-session/mismatched-profile cases. |

Paths above are relative to `backend/app/application/recommendation/`, except
value object `backend/app/domain/value_objects/recommendation_score.py`.
Candidate IDs are lazy SHA256 properties; the hot comparator uses candidate
keys, not hashing every outfit. NLP, DB commits, frontend rendering and auth are
not established as the dominant computation by these measurements.

The earlier Phase 5F-1 wall-clock profile recorded 92,684,839 calls. Its
instrumented 61.49s service duration must not be compared directly with the
21.82s uninstrumented HTTP median. Its cumulative rows overlap: request scoring
11.62s; final score validation 10.03s; mandatory evaluation 8.24s; candidate
generation 6.18s; comparison 5.38s; mapper calls 2.54s. The new CPU-clock profile
is an independent diagnostic, not a correction factor for that older profile.

## Proposed optimisation stages, not approved implementation

The fresh no-preference **200-garment CPU-clock profile** records 88,921,300
calls, 182.825s wall and 178.172s measured process CPU. Its sum of profiled self
times is 166.609s; clock granularity and profiler accounting/overhead prevent
using that as an exact decomposition of process CPU. No per-candidate timing
wrappers from the old benchmark are installed, explaining part of the call-count
difference from the old 92.7-million-call diagnostic. Ranked cumulative hotspots:

| Work | Calls | Self CPU seconds | Cumulative CPU seconds |
| --- | --- | --- | --- |
| Final RecommendationScore validation | 134,820 | 2.297 | 35.516 |
| RequestMatchScorer.score | 134,820 | 4.641 | 34.938 |
| RequestConstraintEvaluator.evaluate (both checks) | 269,640 | 5.188 | 21.922 |
| ScoreEvidence validation | 539,280 | 4.203 | 18.781 |
| CandidateRanker.better | 134,820 | 1.016 | 18.531 |
| ScoringEligibilityGate.verify | 134,820 | 1.672 | 17.422 |
| CandidateGenerator.enumerate | 134,821 resumes | 1.438 | 16.578 |
| CandidateRanker.key | 269,639 | 2.688 | 12.234 |
| dataclasses.replace (all callers) | 269,642 | 3.297 | 12.078 |
| GarmentEvidenceMapper.classify (mostly hits) | 1,064,460 | 2.750 | 6.172 |
| Deferred CompatibilityScorer.score | 134,820 | .609 | 5.609 |
| Empty PreferenceScorer.score | 134,820 | .906 | 5.453 |

These rows overlap and must not be summed. Fraction functions alone account
for **35.563s of exclusive self CPU** across their operations, spread through
scoring, validation and comparison, not an additional independent 35.563s on
top of those callers. `Fraction.__new__` runs 1,887,485 times and
`_from_coprime_ints` 3,370,499 times. Normalization remains one call/session.

Object construction is substantial even though candidates are not retained:
the 200-garment run constructs 397,620 candidate members, 134,820 outfit
candidates, 539,280 ScoreEvidence objects, 404,460 ComponentScore objects and
134,820 final RecommendationScore objects. There are also both stream progress
objects, evaluation/proof wrappers, reason tuples and arithmetic temporaries.
Constructor calls are allocation-pressure evidence, not a count of every heap
allocation or live-memory requirement. `tracemalloc` runs at 20 and 50 garments
with populated preferences peaked at **233,023** and **220,316** traced bytes
respectively; surviving snapshots include vocabulary and small tuple/object
allocations. Lower peak at 50 reflects allocator/caching differences, not proof
that memory decreases with wardrobe size. Transient/freed objects are absent
from end-of-run snapshots. No 200-garment traced peak or process-RSS peak is
claimed. CPU profiles record constructor counts at that size instead.

With four preference types, **PreferenceScorer.score becomes the largest
individual scorer**: 134,820 calls, 13.984s self / 124.031s cumulative CPU.
ScoreEvidence validation rises to 1,483,020 calls (13.016s self / 58.531s
cumulative). Mapper lookups rise to 1,731,300 (10.531s cumulative), while actual
colour classification remains only 600 calls. Suitability parsing has 397,620
cache lookups (2.703s cumulative) and only 200 evidence constructions. Preference
normalization still runs once. Thus populated preference set operations,
evidence/reason construction, exact weighted aggregation and validation deserve
separate attention; repeated normalization or uncached colour inference is not
the explanation. These CPU costs include profiling overhead and overlap.

1. **Session constants and incumbent key.** Reuse immutable Unavailable C and
   empty-preference P (preserving NoPreferences versus NoSupportedPreferences),
   cache the incumbent comparison key, and precompute normalized preference
   category/value sets and importance denominator. Keep user/context/profile
   checks on every comparison and no per-candidate weight changes. Lowest risk;
   likely modest benefit, not a credible standalone five-second solution.
   A comparison variant may compare positive exact (total,R,C,P) tuples in
   descending order and stable garment keys ascending only on equality, avoiding
   repeated Fraction negation. It must retain the current public key semantics
   where exposed, session/profile validation and every tie-break stage; choose
   between variants using differential tests and measured allocation/runtime.
2. **Prepared evidence and mandatory request facts.** Independently prepare
   request membership tests inside each approved evaluator; preserve the fresh
   verifier and compare complete evaluations. Reuse immutable per-garment
   recognized evidence and match facts. On cache hit, an identity fast path is
   safe only for the identical immutable snapshot; a different same-ID object
   must still undergo existing equality/conflict checking. Preserve every
   mandatory condition, evidence-ID order and three-state outcome. Do not share
   untrusted injected evidence into the independent gate.
3. **Exact arithmetic/component reuse.** Cache exact bounded aggregate values
   and weighted totals keyed by immutable request/profile/preferences and exact
   component contributions. Use Fraction values, never float conversion.
   Both rank and final validation may call the same exact calculation helper;
   validation must still compare the supplied total. Style-only R may reuse a
   component for the same base garment identities because outerwear is excluded
   by current semantics; preference/colour/suitability keys must include all
   relevant members and diagnostic IDs. Bound caches using eviction, not
   candidate truncation; benchmark hit rate and peak memory. Broad full-outfit
   caches have little benefit when every outfit is unique.
4. **Constructor/stream overhead, only after further approval.** Reuse immutable
   CandidateMember objects for fixed garment/role/order (outerwear needs distinct
   order-2 and order-3 members). Investigate validated session facts for invariant
   weights/structure. Keep existing public immutable constructors and checks.
   Winner-only diagnostic construction, private fast constructors or mutable
   internal progress counters are higher-risk alternatives, not automatically
   authorised changes: malformed input detection, every intermediate observable
   result, close semantics and late exceptions must remain identical. Do not
   bypass the eligibility seal or suppress arithmetic validation for speed.

No candidate pruning is recommended for the initial implementation stages.
The all-vintage baseline accepts every candidate, so invalid-candidate pruning
cannot help it. Even category pruning must preserve structural candidate set,
individual mandatory evidence, counters and late-failure observations under
the user's strict equivalence requirement; merely retaining the final winner
is insufficient. Avoid early exit when a perfect score is found: later errors
and stable-identifier ties still matter.

## Future affected files

No file in this table is modified during this review.

| Proposed stage | Files under backend | Required invariant |
| --- | --- | --- |
| Constants/comparison | `app/application/recommendation/recommendation_scorer.py`, `candidate_ranker.py`, `compatibility_scorer.py`, `preference_scorer.py` | Exact same components, full tie order, context/profile checks |
| Prepared evaluation | `request_constraint_evaluator.py`, `garment_evidence_mapper.py`, `scoring_eligibility_gate.py`, possibly new `prepared_request_evidence.py` in the same application directory | Independent verification, same Pass/Fail/Unknown and condition IDs |
| Exact aggregate reuse | `request_match_scorer.py`, `preference_scorer.py`, `recommendation_scorer.py`, potentially new `exact_score_calculation.py`; `app/domain/value_objects/recommendation_score.py` only if separately approved | Exact Fraction components/totals and validation failures unchanged |
| Optional later construction work | `candidate_generator.py`, `recommendation_engine.py`, `request_candidate_session.py` | Identical candidate order/count/identities and observable completion/error behaviour |
| Equivalence verification | new `tests/test_assistant_performance_equivalence.py`, frozen test-only reference runner/fixtures; existing candidate/request/scoring/ranking/Assistant/persistence tests retained | Compare every candidate and result, not just selected ID |
| Benchmarking | `scripts/profile_outfit_assistant.py`; separate benchmark-only HTTP/browser harness/config rather than production frontend files | Fresh keys, identical data, pinned environment, no timing instrumentation in acceptance |

Application-directory file names in abbreviated rows resolve under
`backend/app/application/recommendation/`. No database, persistence, API,
frontend, flag, CV, review, saving or visualisation change is proposed.

## Differential correctness protocol

Freeze the pre-optimisation source hashes and a test-only reference version of
the current pipeline. Run original and proposed implementations against
identical immutable inputs, preference rows and fault schedules in separate
fresh sessions. For small and medium fixtures retain full per-candidate
records; for large fixtures compare streams lockstep to avoid materialisation.
Archive the entire relevant transitive application/configuration baseline,
including uncommitted source, rather than relying on Git HEAD or copying only
the outer rank method. Prefer isolated subprocess imports so the reference
cannot accidentally call newly optimised lower-level helpers. Schedule injected
faults by semantic stage and candidate ordinal/key, not the number of cache
lookups (which an optimisation is intended to change).

For **each structural candidate**, compare ordered role/ID key, complete
snapshot contents, structure validity, all mandatory conditions/evidence IDs,
Pass/Fail/Unknown, whether it reaches scoring, R/C/P values as numerator and
denominator, availability/coverage/reasons, exact total/weights/provenance and
comparison key. Compare the final selected garment key, complete/status/reason,
examined/passed/failed/unknown/scored counts and close outcome. Random context
UUIDs and persisted recommendation IDs cannot be compared literally; require
their ownership/binding invariants and compare stable garment keys instead.

Test matrix:

- All four compositions; each exact category-to-role mapping; mixed structures,
  optional outerwear, duplicate/conflicting IDs, reversed/permuted input order.
- Zero/one/multiple supported preferences, arbitrary exact decimal importance,
  inactive/unsupported rows, malformed supported JSON, ownership mismatch,
  zero importance and duplicate types; all supported preference types.
- Every approved request field alone/combined; collective overlapping category
  constraints; named aliases and exact hex only; style positive, mixed, missing,
  intentionally empty, unrecognized and malformed annotations; opt-in suitability
  allow/deny/conflict/missing, with default PolicyUnavailable preserved.
- No optional request fields; no preferences; unavailable C versus reviewed zero
  in experimental test-only policies; preserve existing Jaccard single-dress
  ProfileUnavailable behaviour rather than activating a different policy.
- Ties at total/R/C/P and stable-key stages, mathematically equal fractions with
  different construction histories, cache eviction, same-ID equal versus changed
  snapshots, attempted mutation and scoring-context/profile substitution.
- Fail before first candidate, after a passing candidate and after the apparent
  best/final candidate; RuntimeError, KeyboardInterrupt, GeneratorExit and close
  failure at structural/session/gate/scoring/ranking stages. No partial winner
  may be returned or persisted. Compare constructor validation errors too.
- Fixed reproducible random seeds (record seed and serialized fixture hash),
  hundreds of small combinatorial cases and 20/50/100/200 garment streaming
  cases. Include varied evidence and nontrivial preference values, not only the
  homogeneous performance fixture. Independently enumerate small expected sets.
- Existing Phase 1-4, Assistant, Homepage, history, auth/cross-user, flags and
  persistence rollback/revalidation/idempotency regressions. No persistence
  refactor is needed; verify unchanged writes and failures through their tests.

Do not weaken equality to numerical totals alone: Unknown versus zero,
diagnostic order, rejected candidates and stream completion are contract data.

## Proposed performance acceptance protocol

1. Freeze original/optimised source and fixture hashes, dependency versions,
   Python/Node/Next/Chromium, hardware/OS, flags and SQLite settings. Use patched
   Next 16.4.2 production builds for **both** comparison arms. Do not compare a
   development frontend with the historical production build.
2. Use identical disposable fixture clones and one server worker/sequential
   client. Include 20/50/100/200 with the existing role mix, plus skewed role
   mixes, selective/no-result/unsupported requests and populated preferences.
   Restart or restore databases consistently to avoid history growth differences.
   Every timed successful request has a new submission key; replay is separate.
3. One excluded warm-up per arm/cell; then at least 30 measured HTTP trials and
   30 actual browser submit-to-visible-outcome trials. This is a proposed test
   protocol, not an extra threshold invented by the report. Use alternating
   baseline/optimised blocks to reduce thermal/order bias. No profiler,
   tracemalloc, concurrent build or regression suite in timed runs.
4. Record raw times, median, nearest-rank empirical p95, min/max, counts, complete
   outcome, exact winner and stage times; explain p95 uncertainty at this sample
   size. Report cold startup separately and clearly define warm baseline scope.
   Browser timing starts at submit action and ends at visible selected/no-result/
   unsupported outcome; includes capability/API/render delay and never ends at
   a loading/provisional response. HTTP ends after complete body consumption.
5. Proposed operational pass criterion: **every measured valid submission in
   the agreed baseline workload completes within five seconds with correct
   semantics**. A median/p95 below five with a slower observed request is not a
   pass. This finite sample is evidence, not a universal latency guarantee.
   Seek agreement on wardrobe upper bound, expected preference workload,
   baseline hardware and single-client versus concurrent load before final FYP
   acceptance. Do not silently reduce the 200-garment test to obtain a pass.
6. Separately run CPU/allocation profiles to attribute gains and check cache
   memory growth. Report uninstrumented speedup with ranges, not a subtraction
   of overlapping cumulative profiler rows. Run correctness before performance;
   a faster result with altered evidence or an incomplete stream fails.

Reproduction commands and measured new results are recorded below. No speedup
has been measured because no optimised implementation exists.

## Feasibility and decisions

The new 200-garment uninstrumented service-only baseline has five no-preference
trials: median **22.671s**, range **22.625-23.411s**. Three populated-preference
trials have median **38.890s**, range **38.340-39.919s**. Their empirical nearest
rank p95 equals the maximum at these small sample counts; this is not a stable
tail estimate. Median CPU is 22.063s and 36.000s respectively. All trials score
134,820 candidates and commit complete results. Ranking alone takes about
22.647s/38.867s at the median-wall trial; individual stage medians are reported
separately in raw data. NLP, lookup and persistence do not explain these totals.

Just reaching five seconds needs about **4.53x** service speedup for the
no-preference median, **4.68x** for its slowest observed run, and **7.78x/7.98x**
for the populated-preference median/maximum. End-to-end HTTP/browser overhead
still needs room. At 100 garments the exploratory populated-preference
workload also exceeds five seconds, so the problem is not restricted to the
200-garment empty-preference case.

Expected benefit assessment, not measured speedups:

| Proposal | Evidence-based opportunity | Benefit/risk/complexity |
| --- | --- | --- |
| Reuse empty P/deferred C | One constant pair reconstructed for all 134,820 candidates | Low-risk, small. Older profile assigns only about 7% to both scorers; deleting their entire cost would cap benefit near 1.08x, before reuse overhead. |
| Retain best key | 269,639 key calls for 134,820 comparisons | Low/medium complexity. Roughly half of key builds could disappear on this tie-heavy workload, not half of comparison cost. Older profile gives only a few percent end-to-end ceiling. |
| Prepare request/preference facts | 269,642 support checks and repeated set/denominator work; normalization itself runs once | Medium complexity; supports is cheap, populated preference loops merit more attention. Do not promise a large win from normalization caching. |
| Reuse exact R/aggregate arithmetic | Same base repeats with up to 20 optional outerwear choices; baseline exact score vector is constant despite distinct evidence IDs | Higher potential within R/arithmetic subwork, moderate correctness/memory risk. At 200 there are 6,420 bases versus 134,820 candidates, at most 21 uses per base; this is not a 21x pipeline speedup. |
| Constructor/progress reduction | Large numbers of short-lived immutable members/evidence/results | Potentially material but highest proof burden; reject any shortcut that changes validation/failure timing or observable contracts. |
| Selective pruning | No rejected candidates in the baseline | No benefit for this bottleneck; conflicts with exact diagnostics/completion unless stronger proofs exist. Defer. |

Even eliminating the old request-scoring cumulative cost alone (about 19% of
that instrumented run) gives an optimistic Amdahl ceiling near 1.23x, not 4.5x.
Overlapping parent/child costs cannot be added to invent a speedup. Achieving
five seconds with exhaustive Python evaluation is **plausible but unproven**;
simple caches are insufficient evidence. If measured small stages still fall
short, propose a separately reviewed internal exact-scoring representation,
not a hidden limit, weaker request policy, early winner or float shortcut.

Approval requested for the next phase, with separate review checkpoints:

1. Implement the differential harness first, then only stage 1 constants/key
   reuse and preference-invariant preparation; benchmark before broadening scope.
2. If equivalent, review stage 2 independent prepared evidence/request facts
   and stage 3 bounded exact arithmetic/component caching. Choose cache budgets
   as memory controls, with eviction preserving all candidates/results.
3. Keep stage 4 constructor/progress changes and all pruning deferred until an
   exact proposal demonstrates preserved defensive checks and stream behaviour.
4. Agree the final acceptance environment/workload and every-observed-request
   five-second criterion, including populated preferences. Thirty trials per
   HTTP/browser cell is a proposed reproducibility protocol, not a report quote.

No approval is assumed from this document. Phase 5F-2D-2 has not started.
Remaining dependency findings stay in `PHASE_5F_2A_SECURITY_REMEDIATION.md`;
review 422/409 and recommendation-source saving/visualisation gaps remain
separate teammate coordination, with no changes in this phase.

## Executed commands and verification

From `backend`, sequentially (logs redirected into ignored storage):

```powershell
uv run --no-project --python 3.12 --with pillow --with numpy --with fastapi --with python-multipart python -B scripts/profile_outfit_assistant.py --output ../storage/verification/phase5f2d1
uv run --no-project --python 3.12 --with pillow --with numpy --with fastapi --with python-multipart python -B scripts/profile_outfit_assistant.py --output ../storage/verification/phase5f2d1/clean-baseline --sizes 20 50 100 --baseline-only
uv run --no-project --python 3.12 --with pillow --with numpy --with fastapi --with python-multipart python -B scripts/profile_outfit_assistant.py --output ../storage/verification/phase5f2d1/finalization --finalization-only
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_structural_candidates.py tests/test_request_candidates.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_preference_modelling.py tests/test_outfit_assistant.py -q --tb=short
```

All three diagnostic commands exited 0. The main profile covered every size
and both 200-garment preference scenarios, without truncation or partial success.
Its executed script revision/hash is archived alongside results. The final
tooling revision has the additional diagnostic modes and corrected output-key
logging; application algorithms are identical throughout. For future paired
benchmarks pin the resolved versions listed above in both arms; unversioned
`uv --with` commands alone do not freeze future dependency resolution.

Focused regressions: **187 passed, one Starlette/httpx TestClient deprecation
warning, 11.46 seconds**, exit 0. Tests cover structural generation, request
evaluation, exact scoring, ranking, preferences and Assistant integration.
No production algorithm change required a new optimisation test yet: the
differential suite above is proposed for the implementation stage, not claimed
as already implemented. The full backend/CV/browser/security suites were not
rerun in this design-only phase; earlier results and known architecture failure
remain documented in the Phase 5F-2A record. No fresh HTTP/browser latency run
or speedup comparison was performed.

From repository root: `git diff --check` passes, exit 0. Application Python
source hashes match before/after both complete diagnostic runs and the final
stream probe. The profiling tool creates no production records or migrations;
its SQLite databases are temporary and removed by TemporaryDirectory lifecycle.

Files created in this phase:

- `backend/scripts/profile_outfit_assistant.py`: reusable isolated diagnosis,
  uninstrumented repeats, CPU profiles, allocation and terminal-stream probes.
- `docs/PHASE_5F_2D_1_PERFORMANCE_DESIGN.md`: measured evidence, limits,
  affected-file plan, differential tests, benchmark protocol and approval gates.

No existing production file was modified. Raw diagnostic artifacts and logs
are under ignored storage, including source hashes and profiler function data.
**Design review is ready; NFR-02 remains unmet at 200 garments.** No
implementation speedup, application acceptance or Phase 5F-2D-2 approval is
claimed.

## Follow-up: Phase 5F-2D-2A

The user subsequently approved differential testing and the low-risk key,
preference-invariant and immutable constant-component changes only. Their
implementation, fresh paired original/individual/combined measurements and
verification are recorded in `PHASE_5F_2D_2A_PERFORMANCE_VERIFICATION.md`.
The original measurements and design decisions above remain historical evidence;
they have not been overwritten with optimised results. Phase 5F-2D-2B and
NFR-02 acceptance remain separate gates.
