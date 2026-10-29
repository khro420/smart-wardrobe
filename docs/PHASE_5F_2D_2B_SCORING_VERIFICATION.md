# Phase 5F-2D-2B: scoring preparation and bounded exact reuse

2026-10-19. This phase changes scoring implementation costs, not recommendation
policies. Original report sections 4.4.3 and 4.10.4 / RN-15–RN-21 establish
the five scoring classes, normalized weighted formula and total/R/C/P/stable-ID
tie order. NFR-02 requires a complete response within five seconds after valid
submission in the baseline environment. These benchmarks cannot establish that
HTTP/browser requirement. Compatibility remains deferred (7/10, 0, 3/10),
suitability opt-in and approximate hex matching disabled. No additional fashion
rule, preference type, eligibility exception or vocabulary is introduced.

## Independent reference and incremental process

Before any production scoring edits, all 155 application Python/JSON files from
completed 2A were frozen in `backend/tests/fixtures/performance_reference_2a/`.
SHA256 of its archive:
`e7b0923fd1cadfa14c76664ab2d2d4a3d993f177a342df7359d083cdb619f020`.
Every archive member has a manifest hash. The original arm imports the entire
extracted application in a separate process, including transitive dependencies;
it does not call the optimized functions. Five differential/reference tests
passed before production edits. The older pre-2A archive, 63 fixtures and large
stream fingerprints remain intact. Its source-integrity allowlist now also
permits the explicitly approved 2B scoring files; archived bytes are unchanged.

Existing 2A historical medians at 200 garments remain **19.857 s** without
preferences and **33.288 s** with four types. Contemporary paired measurements
are used for speedups; historical measurements are not substituted for a fresh
control or interpreted as measurements of identical machine conditions.

A passed 18 differential tests before B. Its initial two-trial 200-garment
control/A medians were 14.444/14.350 s (no preferences) and 25.927/25.170 s
(four types). Small 20-garment cases were slightly slower. Separate memory runs
retained 18/180 request style facts at 20/200 garments; 200 garments produced
269,040 hits and 180 misses. B passed 63 tests (one future C test deselected)
before C. Its paired control/B medians were 14.750/14.087 s and 24.313/22.256 s.
Its facts grew from 70 to 700 at 20/200 garments; the larger run had 1,198,980
hits and 700 misses. These are incremental probes, separate from final results.

Before A/B, a fresh 200-garment four-preference cProfile reported cumulative
request scoring 9.146 s, preference scoring 29.656 s, evidence validation
12.597 s and final-score validation 7.721 s. A+B's separate 100-garment profile
before C still showed 123,973 evidence validations (1.181 cumulative seconds),
17,710 final validations (0.979 s), request scoring 1.094 s and preference
scoring 2.814 s. Cumulative times overlap and are instrumented wall timings,
not additive component CPU times or accepted latency measurements.

An initial C diagnostic probe found zero whole-preference-component hits among
134,820 candidates. That pool was removed before final verification: complete
colour/formality reason IDs make these components unique in the four-type
workload. The initial probe files are retained as investigation evidence, not
final implementation measurements. The Windows memory collector initially
needed an explicit HANDLE argument type; its failed runs did not yield memory
results and are not used as accepted evidence.

## Implementation and invariant proof

| File / operation | Safe reusable inputs and unchanged work |
|---|---|
| `request_match_scorer.py` (A) | Exact immutable request identity selects static supplied-field details. Per-garment facts contain requested-style membership, Known flag and original lowercase-state/ID reason. Full snapshot equality is checked on a fact hit. Candidate base membership, counts and ordered reasons are still aggregated. Changing request identity clears these facts. |
| `preference_scorer.py` (B) | Exact immutable authenticated preference snapshot scopes facts by preference index and garment ID. Each hit checks the complete garment snapshot. Facts retain category membership, colour/style match and Known state/reason, or the ordered formality states and source reason. Preference changes clear facts. Style still excludes outerwear; colour/formality include it. Unknown denominator, active weights and normalization are unchanged. |
| `preference_scorer.py` (B) | Reasons are supplied to the evidence constructor directly, replacing construction followed by `dataclasses.replace`. This produces the same validated final object rather than first validating an intermediate object with empty reasons. |
| `exact_score_reuse.py` (C) | Instance-owned typed LRU caches, each capped at 256 entries. Evidence keys contain every constructor argument: name, exact value/None, availability, observed/possible and ordered reasons. Request component keys contain the full validated summary and ordered details. No whole preference-component pool is used. |
| Exact arithmetic (C) | Fraction-constructor inputs, request mean values, preference weights/values/denominator, and total weights/contributions are complete arithmetic keys. Availability and reasons are not numerical operands; they remain in evidence/component keys and outputs. None and actual zero remain distinct evidence. Arithmetic uses the same ordered Fraction operations on misses. |
| `recommendation_scorer.py` (C) | Fresh arithmetic reuse owner per rank. Every candidate still passes the independent gate, all three component scorers, a new `RecommendationScore` constructor with its independent weighted-total validator, `ScoredCandidate`, and deterministic rank comparison. No final score, proof, candidate or provisional winner is cached. |

Typed keys prevent a cached valid Fraction from admitting an invalid equal-valued
integer/bool/float to the evidence factory. Failed constructor calls are never
cached. Previously constructed immutable values are returned only for identical
complete factory inputs. Eviction causes recomputation, not a candidate cut.
The actual value-object validators, structural generator, eligibility gate,
policy configuration, ranker, persistence and frontend are unchanged.

Each rank creates fresh request/preference scorers and cache owners. Preference
queries/normalization still occur once per rank. No cache is global or reused
across live users/sessions. Garment facts grow O(G × supported preference
types); bounded pools grow independently of candidate count. Cached values do
not hold outfit candidates. Enumeration/ranking still exhaust the stream;
interruption, incomplete result, forged evaluation and late close failures
discard the provisional winner. Selection/persistence revalidation, transaction,
idempotency and historical metadata behavior are unchanged.

## Reproduction

Run from `backend`, with `$env:SMART_WARDROBE_VTOFF_ENABLED='off'`.
All runs use Python 3.12 and the same uv dependency environment in both arms.

```powershell
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_scoring_hot_path_equivalence.py tests/test_assistant_performance_equivalence.py tests/test_recommendation_scoring.py tests/test_preference_modelling.py tests/test_candidate_ranking.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B scripts/benchmark_scoring_hot_path.py --output ../storage/verification/phase5f2d2b/benchmark --repeats 3 --diagnostics
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

The benchmark uses fresh disposable SQLite databases with strict confirmed
processing records, actual NLP, exhaustive generation, independent mandatory
gate, ranking and atomic Assistant persistence. Each size has 40% tops, 40%
bottoms, 10% dresses and the remainder outerwear. All garments have synthetic
blue/vintage evidence; four-type preferences are colour, style, category and
formality, with missing formality declarations deliberately preserved.
Expected counts are `(T*B + D)*(1+O)`: 198, 2,430, 17,710 and 134,820.
No saved outfits are required. Submission keys are fresh; durable replay is
tested separately. Candidate count, winner and policy/score metadata must match
the reference or the benchmark aborts.

The five arms are unchanged 2A; A only; B only; A+B with C disabled; and A+B+C.
C's independent incremental effect is the comparison of A+B against A+B+C,
holding prepared evidence constant. A-only/B-only use frozen opposite scorers.
Uncached factory bindings preserve the same operations when C is disabled.
Those final individual arms include the uncached C call plumbing; its small
dispatch/setup cost is not subtracted. The earlier clean A/B incremental probes
above were measured before that plumbing was added. C's A+B/combined comparison
holds the plumbing constant and isolates enabled reuse.
Each cell uses three measured uninstrumented trials after one excluded warmup;
no tests/builds/profiles run concurrently. Cache/memory runs are separate, one
per cell. Four 200-garment CPU profiles run afterwards, outside latency trials.
All samples, hashes, environment versions, cache diagnostics and profile tables
are retained under ignored `storage/verification/phase5f2d2b/`.

Memory diagnostics report actual Windows process peak working set, logical
cache sizes/hits/misses and a deduplicated `sys.getsizeof` graph estimate. The
graph estimate excludes opaque C LRU internals/native allocations and is not
total retained heap; the real process peak and explicit entry caps complement
it. The shared mapper is counted once across scorer estimates. No statistically
reliable p95 is inferred from three trials.

## Phase file inventory

These are this phase's changes, not a list of pre-existing uncommitted work:

- Modified `backend/app/application/recommendation/request_match_scorer.py`:
  prepared request/style facts, bounded exact evidence/component/mean reuse.
- Modified `backend/app/application/recommendation/preference_scorer.py`:
  snapshot-scoped garment facts, direct final evidence construction, exact
  numerical reuse; whole candidate-specific preference components stay uncached.
- Modified `backend/app/application/recommendation/recommendation_scorer.py`:
  session-owned exact weighted calculation, retaining every final validator.
- Created `backend/app/application/recommendation/exact_score_reuse.py`:
  typed bounded validated factories and pure exact arithmetic caches.
- Created `backend/tests/fixtures/performance_reference_2a/app.zip`,
  `manifest.json`, `README.md`: executable completed-2A source and integrity/
  provenance documentation, frozen before production changes.
- Modified `backend/tests/performance_worker.py`: optional independent reference,
  isolated A/B/prepared arms and separate cache/Windows memory instrumentation.
- Modified `backend/tests/test_assistant_performance_equivalence.py`: extend
  only the old reference's allowed scoring-file differences; retain all original
  fixture definitions, tie tests and archived bytes.
- Created `backend/tests/test_scoring_hot_path_equivalence.py`: independent 2A
  transcript/metadata oracle, extended partial/weighted cases, 60-garment
  fingerprints, cache admission/eviction/type/immutability/isolation checks and
  mandatory/final-validator invocation counts.
- Created `backend/scripts/benchmark_scoring_hot_path.py`: paired five-arm
  repeated service benchmark, separate memory passes and CPU profiles.
- Created `backend/scripts/verify_scoring_fingerprints.py`: full 200-garment
  independent-reference comparison and preservation of both historical hashes.
- Created this document and updated `docs/REPORT_TRACEABILITY.md`: evidence,
  limitations, requirement mapping and exact reproduction commands.

No frontend, schema, dependency manifest, query contract, mandatory evaluator,
structural generator, persistence, saving/visualisation or CV file is changed.
The 256-entry bound is a memory-management choice, not a candidate limit,
fashion threshold or claim of an optimal cache capacity.

## Final results

Three measured trials per cell, one excluded warmup. Ranges are observed
minimum?maximum, in seconds. 120 measured trials across 40 cells; 40 excluded
warmups and 40 separate cache/memory runs. CPU profiles are separate. Preference
rows in this benchmark are injected immutable fixtures rather than a production
preference SQL query. Authentication, transport and browser rendering are not
included in the latency measurement.

### Combined latency

| Garments | Preference types | Candidates | Completed 2A median [range] | Combined median [range] | Reduction | Speedup |
|---:|---:|---:|---|---|---:|---:|
| 20 | 0 | 198 | 0.035272 [0.033988 - 0.036765] | 0.044785 [0.044292 - 0.051522] | -26.97% | 0.788x |
| 20 | 4 | 198 | 0.067143 [0.066362 - 0.069381] | 0.046104 [0.044414 - 0.048083] | 31.33% | 1.456x |
| 50 | 0 | 2,430 | 0.306023 [0.273765 - 0.341001] | 0.257253 [0.254539 - 0.270169] | 15.94% | 1.190x |
| 50 | 4 | 2,430 | 0.463805 [0.459215 - 0.522614] | 0.384122 [0.375292 - 0.420771] | 17.18% | 1.207x |
| 100 | 0 | 17,710 | 1.975239 [1.935115 - 2.179136] | 1.706822 [1.624256 - 2.006201] | 13.59% | 1.157x |
| 100 | 4 | 17,710 | 3.138040 [3.114507 - 3.211083] | 2.443902 [2.427013 - 2.445405] | 22.12% | 1.284x |
| 200 | 0 | 134,820 | 14.164723 [14.030588 - 14.643030] | 12.478719 [12.415406 - 13.209403] | 11.90% | 1.135x |
| 200 | 4 | 134,820 | 24.025244 [23.963159 - 24.091200] | 18.720859 [18.567105 - 19.978560] | 22.08% | 1.283x |

### Independent and incremental effects

A and B compare individually against the completed-2A column above. C is
isolated by comparing prepared A+B with combined A+B+C, without changing A/B.

| Garments | Preference types | A only median [range] | B only median [range] | A+B median [range] | C reduction from A+B |
|---:|---:|---|---|---|---:|
| 20 | 0 | 0.038577 [0.036238 - 0.039132] | 0.038540 [0.037197 - 0.039106] | 0.039984 [0.039289 - 0.043542] | -12.01% |
| 20 | 4 | 0.060353 [0.059969 - 0.065769] | 0.050351 [0.049107 - 0.051596] | 0.048776 [0.048303 - 0.050355] | 5.48% |
| 50 | 0 | 0.279986 [0.276804 - 0.306447] | 0.300464 [0.297883 - 0.327758] | 0.293226 [0.283925 - 0.321080] | 12.27% |
| 50 | 4 | 0.480947 [0.444501 - 0.481217] | 0.449217 [0.427391 - 0.463100] | 0.446884 [0.405147 - 0.538741] | 14.04% |
| 100 | 0 | 1.868379 [1.855607 - 1.943966] | 1.913964 [1.879981 - 1.951493] | 1.860253 [1.854742 - 1.892786] | 8.25% |
| 100 | 4 | 3.185968 [3.116267 - 3.344090] | 2.923562 [2.873023 - 3.081848] | 3.103941 [2.947531 - 3.463839] | 21.26% |
| 200 | 0 | 14.018129 [13.864350 - 14.197051] | 14.893824 [14.332849 - 15.268313] | 13.857045 [13.854013 - 14.362630] | 9.95% |
| 200 | 4 | 24.141454 [23.874651 - 24.927715] | 22.396681 [22.134179 - 22.701854] | 21.676575 [21.640980 - 22.514734] | 13.64% |

The combined 20-garment/no-preference case is slower (about 9.5 ms absolute).
A alone is also slower at 50/100/200 garments with four preference types; B's
200-garment/no-preference control is slower. These observations are retained,
not excluded or interpreted as uniform improvements. Three samples and fixed
arm order do not establish statistical significance or isolate background load,
thermal/frequency effects or setup costs. Historical 19.857/33.288-second 2A
medians are preserved but are not the denominators for these speedups.

### Cache and memory observations

H/M means observed hits/misses in a separate single-session run; parentheses
contain retained entry count. Peak memory is actual Windows peak working set,
shown as reference/combined MiB. These diagnostic runs are not latency samples.

| Garments | Pref types | Peak MiB 2A/combined | Request facts H/M (entries) | Preference facts H/M (entries) | Request evidence pool H/M (entries) | Request component pool H/M (entries) | Weighted total H/M (entries) | Preference arithmetic H/M (entries) |
|---:|---:|---|---|---|---|---|---|---|
| 20 | 0 | 26.47/26.88 | 372/18 (18) | 0/0 (0) | 328/68 (68) | 132/66 (66) | 197/1 (1) | 0/0 (0) |
| 20 | 4 | 26.60/27.00 | 372/18 (18) | 1,566/70 (70) | 328/68 (68) | 132/66 (66) | 196/2 (2) | 196/2 (2) |
| 50 | 0 | 27.10/27.09 | 4,785/45 (45) | 0/0 (0) | 4,053/807 (256) | 1,625/805 (256) | 2,429/1 (1) | 0/0 (0) |
| 50 | 4 | 27.04/27.38 | 4,785/45 (45) | 20,820/175 (175) | 4,053/807 (256) | 1,625/805 (256) | 2,428/2 (2) | 2,428/2 (2) |
| 100 | 0 | 26.95/27.09 | 35,220/90 (90) | 0/0 (0) | 32,208/3,212 (256) | 14,500/3,210 (256) | 17,709/1 (1) | 0/0 (0) |
| 100 | 4 | 26.98/28.26 | 35,220/90 (90) | 155,590/350 (350) | 32,208/3,212 (256) | 14,500/3,210 (256) | 17,708/2 (2) | 17,708/2 (2) |
| 200 | 0 | 27.49/28.36 | 269,040/180 (180) | 0/0 (0) | 256,818/12,822 (256) | 122,000/12,820 (256) | 134,819/1 (1) | 0/0 (0) |
| 200 | 4 | 28.29/29.12 | 269,040/180 (180) | 1,198,980/700 (700) | 256,818/12,822 (256) | 122,000/12,820 (256) | 134,818/2 (2) | 134,818/2 (2) |

Every individual arm's memory/cache counters, including all remaining pools,
are recorded in `benchmark/results.json` and per-cell `*-diagnostics.json`.
Request/preference garment facts scale with G; exact pools stay at or below
256 entries even while the number of candidates rises from 198 to 134,820.
The final score constructor and mandatory gate are not cached.

### Separate profiling and remaining hotspots

Environment recorded by the benchmark: Python 3.12.10, FastAPI 0.146.0,
Pillow 13.0.0, NumPy 2.5.4 and python-multipart 0.0.32 on Windows. Both arms
use the same resolved environment. This is not a claim that dependencies or
machine conditions match the historical 2A run.

| Preferences | Arm | Total profiled calls | Evidence validations | Component validations | Final-score validations | Mandatory evaluations | Request score cumulative s | Preference score cumulative s |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | original | 80,739,280 | 269,643 | 134,823 | 134,820 | 269,640 | 8.756 | 0.120 |
| 0 | combined | 65,984,108 | 12,825 | 12,823 | 134,820 | 269,640 | 3.702 | 0.121 |
| 4 | original | 138,832,655 | 1,348,203 | 269,643 | 134,820 | 269,640 | 8.877 | 28.682 |
| 4 | combined | 86,639,923 | 295,305 | 147,643 | 134,820 | 269,640 | 3.744 | 14.212 |

Final-score validation remains 134,820 calls; mandatory evaluation remains
269,640 calls in every 200-garment arm. In the populated case, request scoring
falls from 8.877 to 3.744 cumulative instrumented seconds and preference scoring
from 28.682 to 14.212. Final-score validation still costs about 8.009 cumulative
seconds and mandatory evaluation 6.402 in the combined profile. These overlap
other call stacks and must not be added to latency or labelled direct CPU costs.
Raw function tables also retain Fraction operations and structural/session
object construction costs. Those validators and generation algorithms were not
optimized here.

The service medians remain 12.479/18.721 seconds at 200 garments. No NFR-02 pass
is claimed. Recommended next step is a separately approved profiling/design
review of remaining exact validation, mandatory evaluation and object-construction
costs, with an agreed fresh end-to-end HTTP/browser workload. Any future reuse
must retain independent verification and complete enumeration. Pruning, altered
completeness, validation shortcuts and Phase 5F-2D-2C are not implemented.

## Remaining boundaries

No claim of final FYP acceptance or NFR-02 compliance is made. Compatibility is
still incomplete; reviewed holistic reference data remain unavailable. The
normal review payload's `neckline`/`sleeve_length` 422 followed by confirmation
409 and recommendation-source save/visualisation eligibility inconsistencies
remain separately owned coordination items. No teammate code was modified.
This phase does not authorize pruning, early termination, altered candidate
semantics, validation shortcuts or Phase 5F-2D-2C work.

## Final differential and regression verification

**Status: PASS WITH LIMITATIONS; ready for Phase 5F-2D-2B closure review.**
This is not final application/FYP acceptance. No functional regression was
detected. The small no-preference 20-garment timing regression and five-second
performance gap remain documented limitations, not concealed successes.

The final oracle keeps all 63 old fixtures and adds five mixed positive/
unrecognized-style and unequal-weight cases. Both 60-garment cases compare
4,074 scored candidates / 12,222 ordered events, including persisted metadata.
Final 200-garment verification executes both the full independent reference and
combined app for each preference workload: **134,820 candidates and 404,460
ordered mandatory/score events per arm**, with equal outcomes and metadata.
Both preserved historical fingerprints match exactly:

| Preference types | SHA256 |
|---:|---|
| 0 | `7338a94fddf5c8c66cfafb3f9732e00114e90e062a75e1f1098b9d61f61a14c5` |
| 4 | `302fa15c0bd06c36445a5d8bf07fb2ea0b1a43db56905a863adf0ba4cfacb574` |

The oracle compares full evidence values, states, coverage, ordered reasons,
Fraction numerator/denominator, weights, total, candidate roles/order, selected
identity, session counters and terminal status. Existing tie-level tests,
invalid-owner/preference/snapshot isolation, interruptions, forged mandatory
results, late exceptions/close errors, actual atomic persistence and replay
remain covered. Only nondeterministic context UUID/seal data are omitted from
serialization; live proof/user/context checks still execute. Source integrity
confirms only the three approved existing application files differ from 2A and
the only additional application source is `exact_score_reuse.py`. Final measured
recommendation source hashes still match the current worktree source bytes.

Additional exact commands (backend working directory unless noted):

```powershell
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_scoring_hot_path_equivalence.py tests/test_assistant_performance_equivalence.py -q --tb=short
uv run --no-project --python 3.12 --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B scripts/verify_scoring_fingerprints.py --fixtures-dir ../storage/verification/phase5f2d2b/benchmark --output ../storage/verification/phase5f2d2b/fingerprints
```

Frontend working directory, after timing/profiling completed:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-verification/phase5f2d2b'
npm run build
Remove-Item Env:SMART_WARDROBE_BUILD_DIR
npm run test:browser
```

The actual build command saved/restored any prior environment variable value;
the abbreviated reproduction block assumes none. The production build used a
fresh isolated nested directory; no unrelated cache or directory was deleted.
Generated `tsconfig.json`, `next-env.d.ts` and frontend `AGENTS.md` were restored
byte-for-byte from pre-run backups and equality checked. Frontend source and
configuration bytes are unchanged by this phase. Functional/fingerprint runs
may overlap each other; none overlapped accepted latency runs or profiles.

| Verification | Actual result |
|---|---|
| Initial independent completed-2A tests before production edits | 5 passed, 5.00 s |
| A differential stage | 18 passed, one existing warning, 12.03 s |
| B differential/scoring/preference stage | 63 passed, one future C test deselected, one existing warning, 11.77 s |
| C-focused scoring/ranking/preference suite | 89 passed, one existing warning, 20.46 s; before the final extra fixture assertions |
| Final focused old/new oracle suites | **24 passed**, one existing warning, **27.82 s** |
| Full relevant backend regression command above | **663 passed, 1 failed**, one warning, **63.07 s** |
| Full 200-garment fingerprint command | Exit 0; all four complete streams, winners and persisted metadata match independent reference and historical anchors |
| `npx tsc --noEmit` | Exit 0 |
| `npm run lint` | Exit 0; zero errors, two existing navigation warnings |
| Isolated `npm run build` | Exit 0, Next 16.4.2/Turbopack; 13/13 static pages generated; compilation 11.8 s, TypeScript 7.1 s |
| `npm run test:browser` | **17 passed (1.1 minutes)** |
| `git diff --check` (repository root) | Exit 0; existing `frontend/app/history/page.tsx` LF→CRLF warning only |
| Additional source checks | All phase Python text parses; no trailing whitespace in phase text files; source hashes and generated-frontend restoration verified |

The sole backend failure is unchanged:
`backend/tests/test_report_architecture.py:28`,
`ReportArchitectureTests.test_single_backend_and_canonical_ml_locations`,
asserting that `ai-services` must not exist. The pre-existing folder still
exists; neither it nor the assertion was changed to satisfy the test. This is
separate from scoring correctness. The Starlette/httpx deprecation warning is
also pre-existing. The two frontend warnings concern existing relative
`window.location.assign` calls at `app/extract/results/page.tsx:151` and
`components/Layout.tsx:50`; no teammate-owned UI code was altered.

`tests/test_segmentation_geometry.py` was not executed: this unchanged CV module
needs the previously unavailable heavy CV dependencies, and installing them is
outside this phase. Phase 1–5 regression coverage includes eligibility,
structure, mandatory evaluation, scoring, ranking, transactions/concurrency,
rollback, durable replay, Homepage, Assistant, completed history, authentication,
cross-user access and feature flags. The 17 browser checks cover enabled/
disabled and controlled-failure behavior plus real login/Homepage/Assistant/
history/archival interactions. They are functional tests, not a new agreed
200-garment HTTP/browser NFR-02 performance evaluation.
