# Phase 5F-2E-3C-1: exact compatibility pair-cache experiment

Date: 2026-10-20. Scope: explicit cached experimental path only. The original
157 application files AND seven Phase 3A additions remain byte-identical. No live
Homepage/Assistant wiring, midpoint/no-pair convention, rule, weights, independent
gate, persistence, frontend, suitability or approximate-hex setting is changed.
The original Phase3A uncached scorer/coordinator are the executable oracle.

## Design and duplicate work

Original rule_based_compatibility_scorer.py evaluates colour/Dice and constructs
pair ScoreEvidence and explanatory strings for every occurrence of a pair. The
same top/bottom pair recurs with every outerwear; top/outerwear recurs for every
bottom, and bottom/outerwear for every top. Per-garment evidence is already cached.

The new CompatibilityPairCache is a lazy OrderedDict LRU with maximum 19,900
unordered pairs. Smaller capacities, including 0, are explicit diagnostic/test
options; larger/bool/negative capacities are rejected. A miss computes exact
original Fraction results and validated immutable evidence. Eviction never drops
candidates, changes weights or substitutes a score. Unknown results are cached too.

Keys are canonical unordered ID tuples. Values are frozen entries containing
validated frozen ScoreEvidence pairs. Diagnostic prefix strings are prepared once
per garment. Original caller ordering of pair labels/reasons is retained: an
opposite-order view is built once if needed and retained as a second immutable
view within the same entry. Ordinary structural generation uses stable role order;
capacity always counts unordered pairs, not views.

The cache pins immutable policy version/hash/achromatic-set identity, binds one
owner, and rejects changed prepared evidence. The existing per-garment mapper also
checks full immutable snapshot equality before lookup, including source/provenance
changes that would not alter numerical pair values. The cached scorer binds the
VerifiedScoringInput context and rejects another gate context. Each rank call
allocates a fresh local scorer/cache; there is no module-global or persistent cache.
One coordinator can run parallel sessions without sharing their caches. Direct
offline evaluate calls explicitly use one scorer lifetime as one offline session;
they do not certify authentication or current eligibility.

Memory is O(G + min(P,19900)) plus the retained winner: existing preparation is
per garment, pairs are capped. A reverse view can add bounded per-entry evidence.
Evicted evidence referenced by the incumbent remains immutable; no pair entry holds
an entire candidate or mutable database object.

## Preserved semantics and architecture

Colour, style Dice, exact pair means, summary/details order, source methods,
missing/empty/malformed/unrecognized reasons, observed/possible counts and policy
hashes are unchanged. Single dresses still yield Unknown and NotApplicable factor
results. The strict experimental complete-session coverage safeguard remains.
No convention approved for a later isolated phase is implemented here.

The cached scorer is a separate twin of the preserved uncached scorer. The cached
coordinator is a separate twin of Phase3A orchestration, using the same gate, R/P,
RecommendationScore validation, ExactScoreReuse and CandidateRanker. Its additional
rank_with_cache_info operation returns only an immutable counter snapshot alongside
the unchanged RankingOutcome. Cache diagnostics are not inserted into policy
results or persisted provenance, so cached/uncached outcome equality is testable.
No candidate is skipped, truncated or published before successful full exhaustion
and close. Late failures preserve unsuccessful completion and partial counts.

Both independent scoring verification and final score validation still run for
every relevant candidate. Reusing already validated immutable pair evidence avoids
reconstructing identical objects; it does not use unchecked constructors or bypass
the validation of newly computed scores.

## New files and modifications

New application modules:
- backend/app/application/recommendation/compatibility_pair_cache.py: bounded LRU, frozen pair evidence/entries/counter snapshots, policy/owner/evidence checks.
- backend/app/application/recommendation/cached_rule_based_compatibility_scorer.py: explicit cached twin, unchanged Phase3A arithmetic and context binding.
- backend/app/application/recommendation/cached_rule_based_recommendation_scorer.py: full-stream cached twin and separate immutable cache-info result.

New tooling/tests/documentation:
- backend/tests/test_compatibility_pair_cache.py: differential full evidence/outcomes, fourteen-colour table, reversed pairs, malformed/missing/zero, source/policy/user/context changes, eviction/full-capacity stress, parallel sessions, actual Phase1 DB cases, late failures and ties.
- backend/scripts/benchmark_compatibility_pair_cache.py: six alternating paired full-pipeline runs, complete output fingerprints, exact pair counters and fresh-process peak-RSS passes.
- backend/tests/fixtures/compatibility_pair_cache_sources.v1.json: separately pinned additions; no frozen archive is rewritten.
- docs/COMPATIBILITY_PAIR_CACHE.md: this design/verification/retention record.

Modified supporting files:
- backend/tests/integration_source_guard.py: recognize only the separately pinned new additions while preserving original 157/seven Phase 3A hash checks and all archive checks.
- docs/RECOMMENDATION_RULES.md: explicit cached-path status and link.
- docs/REPORT_TRACEABILITY.md: correctness/performance evidence and unresolved NFR-02.

## Differential protocol

Original and cached executions use identical snapshots/requests/preferences. Every
component field, exact Fraction, rule state/reason/coverage and candidate ordering
is compared. Full ranking equality includes score details, candidate snapshots,
request/evaluation, user, status, complete flag, score counts and diagnostics; only
independently generated gate context nonces are excluded from cross-run equality.
The gate itself still verifies that context per execution.

Eviction tests use capacities0/1/2/default with varied numerical outcomes; full
capacity stress visits20,100 unique pure pairs, stores19,900 and recomputes after
eviction. This stress is not presented as generating invalid wardrobe outfits.
Actual test-database cases cover strict confirmation, ownership, availability,
missing linkage and processing-job ownership. The normal live pipelines are untouched.

## Benchmark protocol

Six matched pairs per workload, alternating uncached/cached then cached/uncached.
All timings are complete backend generation/mandatory/gate/scoring/ranking runs
using synthetic eligible snapshots, no optional request fields and no preferences.
A result fingerprint (status, complete flag, score count, diagnostics, winner
key and full score/evidence) must match on every arm. Full snapshot/request/user
equality is covered separately by the differential suite. Normal workloads contain dresses
and retain the original InsufficientEvidence result; the no-dress heavy workload
can select. Counts always include the entire accepted candidate stream.

For T tops,B bottoms,D dresses,O outerwear:
N=(T*B+D)*(1+O); pair visits=T*B+3*T*B*O+D*O;
unique relevant pairs=T*B+(T+B+D)*O.
Unique counts are analytically derived for these exhaustive workloads, confirmed
by cache misses when no eviction occurs. The production cache does not retain an
unbounded all-time seen-pairs set merely to collect this statistic.

Memory is measured in separate fresh Python processes running the complete same
pipeline. Windows GetProcessMemoryInfo reports peak working-set RSS, including
interpreter/imports/input; it is not incremental tracemalloc memory. Startup/input
peaks are recorded separately. Prior Phase3A tracemalloc values are not directly
comparable. Timing arms run sequentially without concurrent regression tests;
independent host scheduling/power variability remains. No microbenchmark is called
an end-to-end result. First pairs are retained, not silently discarded as warmup.
Six observations do not establish p95 or statistical significance.

Host: AMD Ryzen5 7235HS,4 cores/8 logical processors,21,144,231,936 bytes physical
memory reported by Windows. Python/platform/hash-seed/GC/config hashes are recorded
in the raw report. No production dependency or environment default is changed.
NFR-02 is the report's complete HTTP response target, not these backend timings.

## Commands

From backend, PowerShell:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_compatibility_pair_cache.py tests/test_rule_based_compatibility.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -u scripts/benchmark_compatibility_pair_cache.py --sizes 20 50 100 200 --heavy --pairs 6 --memory --output ../storage/verification/phase5f2e3c1/paired.v1.json
```

Use a new output filename when reproducing; source/existing outputs are protected.
The raw report has complete=false until all workloads and memory checks complete.
Run git diff --check at repository root. Results and retention decision are recorded below.


## Measured results and retention decision

Raw completed report: [paired.v1.json](../storage/verification/phase5f2e3c1/paired.v1.json).
This is a local ignored verification artifact; the tables below retain the results
in source documentation. All 30 matched pairs (60 timing arms), plus ten separate
memory arms, completed with matching result fingerprints. These are backend
full-pipeline measurements, excluding database I/O, HTTP, browser and live models.

| Garments (T/B/D/O) | Candidates | Pair visits | Unique pairs / misses | Hits | Hit rate | Evictions |
|---|---:|---:|---:|---:|---:|---:|
| 20 (8/8/2/2) | 198 | 452 | 100 | 352 | 77.876% | 0 |
| 50 (20/20/5/5) | 2,430 | 6,425 | 625 | 5,800 | 90.272% | 0 |
| 100 (40/40/10/10) | 17,710 | 49,700 | 2,500 | 47,200 | 94.970% | 0 |
| 200 (80/80/20/20) | 134,820 | 390,800 | 10,000 | 380,800 | 97.441% | 0 |
| 200 heavy (67/67/0/66) | 300,763 | 893,311 | 13,333 | 879,978 | 98.507% | 0 |

Each row's final cache size/high-water equals its unique-pair count. No benchmark
exceeds capacity; separate saturation/eviction differential tests cover that case.
All candidates are examined. Normal workloads numerically score N-D candidates
and end InsufficientEvidence because the D single dresses remain Unknown; the
heavy workload scores all 300,763 and ends Selected. Neither path hides dresses.

| Garments | Uncached median seconds (range) | Cached median seconds (range) | Median paired time reduction | Ratio of medians | Faster cached pairs |
|---|---:|---:|---:|---:|---:|
| 20 | 0.048885 (0.040200-0.053526) | 0.045429 (0.034739-0.050728) | 9.512% | 1.076x | 4/6 |
| 50 | 0.474748 (0.448071-0.523660) | 0.391721 (0.383321-0.471329) | 14.092% | 1.212x | 6/6 |
| 100 | 3.363811 (3.289038-3.932860) | 2.921600 (2.782804-2.995973) | 14.415% | 1.151x | 6/6 |
| 200 | 26.872682 (24.942653-29.229881) | 21.307416 (20.328485-22.523165) | 21.322% | 1.261x | 6/6 |
| 200 heavy | 59.079457 (56.977393-64.313454) | 46.502323 (45.737647-51.804399) | 19.755% | 1.270x | 6/6 |

Paired reduction is median(100*(uncached_i-cached_i)/uncached_i), not a
percentage derived from the ratio of medians. At 20 garments, two cached runs
were slower: +0.905 ms (1.84%) and +4.803 ms (10.46%). The four other pairs
improved; the median improved and no consistent small-case regression was observed.
These few milliseconds and six samples do not establish a universal guarantee.
All larger cases improved in every matched pair. Host background activity and
power/thermal conditions were not independently controlled; interleaving limits
but does not eliminate their effects.

| Garments | Uncached peak RSS bytes | Cached peak RSS bytes | Difference bytes |
|---|---:|---:|---:|
| 20 | 26,206,208 | 26,009,600 | -196,608 |
| 50 | 25,792,512 | 26,607,616 | 815,104 |
| 100 | 26,501,120 | 28,860,416 | 2,359,296 |
| 200 | 26,308,608 | 36,851,712 | 10,543,104 |
| 200 heavy | 26,333,184 | 40,656,896 | 14,323,712 |

RSS is one independent process measurement per arm/workload, not a repeated
memory distribution. The negative small-case difference reflects process-level
variation and is not evidence that adding a cache saves memory. Entry count is
strictly capped even beyond these sizes; byte use also depends on evidence and
identifier lengths, so 40.7 MB is not a universal memory ceiling.

Decision: RETAIN the explicitly selected experimental cached path. Differential
checks and benchmark fingerprints preserve behavior; owner/context/policy/source
checks and parallel tests preserve isolation. Bounded entries trade additional
memory for consistent medium/large-workload benefit, with no consistent material
small-workload regression in this experiment. Live/default behavior is unchanged.

## Verification and unresolved work

Focused and broad test results are recorded below. Baseline
hash checks passed: original 157 application files unchanged; seven Phase 3A
additions unchanged; all 169 pre-phase entries (164 application files plus five
frozen app.zip archives) unchanged. The three additions have a separate manifest.
All six benchmark source/config hashes match the measured files. No reference
archive or old manifest was rewritten.

Remaining cost still includes complete enumeration, mandatory checks, independent
verification, candidate and score validation, exact R/P and weighted arithmetic,
per-candidate compatibility aggregation/provenance and ranking. Repeated pair
calculation is reduced; these other stages were deliberately not optimized.
The 200-garment median remains 21.3 or 46.5 seconds in this experiment. NFR-02 is
not achieved or certified by these backend-only results. The original experimental
Unknown/dress coverage refusal remains unchanged and is not a final policy.
Phase 3C-2 midpoint/no-pair conventions, different weights, production activation,
pattern, suitability defaults and approximate hex evidence are not implemented.


### Automated verification results

Commands are the exact pinned uv invocations in the Commands section above, run
from backend with VTOFF disabled only in that test-process environment.

- Focused: 491 passed, one existing TestClient deprecation warning, 12.64s; exit 0.
  This comprises 255 new cache tests and 236 existing Phase 3A tests.
- Broad: 1,248 passed, one failed, one existing warning, 111.94s; exit 1.
  The sole failure is tests/test_report_architecture.py:28,
  ReportArchitectureTests.test_single_backend_and_canonical_ml_locations:
  assertFalse((ROOT / "ai-services").exists()). This is the documented pre-existing
  assertion; no folder or test was changed to satisfy it.
- tests/test_segmentation_geometry.py was explicitly excluded because its cv2/
  torch environment was not provisioned for this recommendation regression run.
  VTOFF/VTON model execution, frontend/browser, production DB and HTTP acceptance
  tests were not run in this isolated experimental scorer phase.
- git diff --check passed (exit 0). Git emitted existing LF-to-CRLF notices for
  recommendation_service.py and frontend/app/history/page.tsx; neither was edited
  in this phase. A separate trailing-whitespace scan of all ten phase files passed,
  including new/untracked files that git diff alone does not inspect.
- Hash checks: zero mismatches across the original 157, all 169 pre-phase entries,
  the seven Phase 3A additions, three new pinned application modules and six
  benchmark source/config hashes.

Status: PASS WITH LIMITATIONS; ready for user review/closure of 3C-1. The retained
cache is explicit experimental infrastructure only. Phase 3C-2 is not started;
its conditionally approved conventions require a separately isolated delivery.
