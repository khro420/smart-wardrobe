# Phase 5F-2D-2A: differential equivalence and low-risk optimisation

2026-10-18. This phase implements only the approved low-risk operations.
NFR-02 still refers to a complete response within five seconds after a valid
submission (original report PDF p.180 / printed p.169), not a backend median.
The scoring formula and tie order from section 4.10.4 remain unchanged.
Original Phase 5F-2D-1 measurements remain in
`PHASE_5F_2D_1_PERFORMANCE_DESIGN.md`.

## Test-first evidence

Before editing production modules, 155 application/configuration Python/JSON
files were frozen into `backend/tests/fixtures/performance_reference/app.zip`,
with individual SHA256 hashes. The full reference is extracted/imported in a
separate Python process; copying only the outer rank function would not have
isolated its dependencies. The test-first differential/tie suite passed
**12 tests before the production changes**. An additional preparation-scoping
test and two further fault fixtures were added afterwards; the final suite has
13 tests. No optimisation was needed to make the original oracle pass.

The harness initially caught two fixture issues before any production edit:
incorrect vest/outerwear layer values, and distinct exception identities when
loading a frozen compatibility class alongside live types. These were corrected
in test tooling, not by changing garment mappings or production exceptions.

The final differential matrix has 63 fixtures: all four structures, supported
and empty requests, no/four populated preferences, collective category and
colour conditions, missing/malformed/unrecognized style/colour evidence,
opt-in suitability allow/deny/conflict/malformed declarations, unavailable
default policies, empty/insufficient wardrobes, Jaccard available/unpaired
behaviour, unsupported/duplicate preferences, and 32 fixed-seed generated cases.
Four individual/combined variants are compared against the frozen original.

Each arm records **both mandatory evaluations**, ordered evidence IDs,
candidate snapshots/roles, each scored candidate's complete R/C/P evidence,
exact Fraction numerator/denominator, weights/total/provenance, winner,
diagnostics, request-stream counters and terminal state. Only nondeterministic
context UUIDs/seals are omitted from serialization; real gate construction and
ownership checks remain active. Synthetic recommendation UUIDs are not used as
winner identity: stable garment IDs/roles/orders are compared instead.

Direct differential tests cover all five comparison levels, equal candidates,
incumbent replacement, and profile mismatch. Fault fixtures cover failure before
enumeration, late RuntimeError/KeyboardInterrupt/GeneratorExit, incomplete stop,
forged empty mandatory evaluation and late close failure. No provisional winner
survives those outcomes. Oracle self-tests deliberately alter score, eligibility,
winner and completion records and confirm the comparison detects each change.

An actual temporary SQLite fixture uses strict confirmed query retrieval, real
ranking, atomic Assistant persistence and durable replay. The original and
optimised arms compare persisted score metadata, owner, item snapshots/roles,
provenance and recommendation/item/chat counts. Replaying the same submission
must return the same record inside each arm. No deployment database is opened.

## Production changes and invariant proofs

Only these three production files changed relative to the frozen reference:

- `backend/app/application/recommendation/candidate_ranker.py`: retains the
  exact incumbent key by **object identity** in the session's ranker. Every
  challenger still gets its key calculated, and all context/request/user and
  profile/weight checks still run before comparison. A different incumbent
  triggers recomputation; every winning challenger replaces the retained key.
  Ordering remains negative exact total/R/C/P, then ascending structural key.
- `backend/app/application/recommendation/preference_scorer.py`: once per exact
  immutable NormalizedPreferenceSet identity, prepares category-group membership,
  preferred colour/style frozensets and the exact importance denominator.
  Vocabulary groups are themselves immutable mappings of tuples. The same
  ordered importance sum is reused, without changing numerator arithmetic.
  Candidate evidence, garment selection, coverage, formality states and reason
  strings remain computed per candidate. The existing normalizer already runs
  once/session and is **not** changed. User/type checks precede reuse. Switching
  preference snapshots rebuilds facts; each rank creates a fresh scorer. No
  shared mutable global cache exists. Empty-P components are immutable and
  separately preserve NoPreferences versus NoSupportedPreferences.
- `backend/app/application/recommendation/compatibility_scorer.py`: reuses one
  immutable, validated Unavailable component in deferred mode. Verified-input
  type checking still occurs first; experimental Jaccard logic is unchanged.

No candidate-dependent R or populated P component is cached. No gate, request,
candidate, score or weight validation is bypassed. No Fraction is replaced by
float; timings alone use floats. Candidate generation, mandatory semantics,
eligibility, scoring policy/version, persistence, history, APIs, frontend,
flags, CV/wardrobe/saving/visualisation and experimental activation stay intact.
The source manifest test enforces that other application/config files match
the frozen reference. Private member/cache identity is not a public contract;
all immutable values and diagnostics remain equal.

## Measurement protocol

`backend/scripts/benchmark_assistant_low_risk.py` runs the frozen original,
key-only, prepared-preferences-only, constants-only and combined arms in fresh
subprocesses/databases. Mixed arms load original non-target classes, so effects
are measured independently rather than inferred by subtracting parent timings.

Workloads are the same synthetic 40% top / 40% bottom / 10% dress / remaining
outerwear wardrobes, current blue primary/vintage style and vintage request.
Actual owner-owned/available/confirmed rows are seeded; Phase 1 query, real NLP,
independent gate, scoring and strict atomic selected-snapshot revalidation/write
run in every arm. Four-preference values/importance match Phase 5F-2D-1 and are
injected as the same immutable snapshot; account-query HTTP is not timed.
No saved outfits are required. Every submission key is fresh; replay is not
timed as generation. Candidate count, selected item IDs/roles/order and persisted
score metadata must match across all arms or the benchmark aborts.

Each size/preference/arm uses one excluded warm-up and **three measured trials**.
Raw wall and process CPU samples, medians and ranges are retained. No p95 is
reported for three samples: the maximum would not be a useful tail estimate.
This is a small-sample diagnosis of individual changes, not release latency
acceptance. Five arms at four sizes/two preference workloads run sequentially;
tests, builds and profiles do not run concurrently. Standard Windows/OneDrive
activity, thermal drift and fixed arm order remain limitations. New paired
original/combined measurements use identical environments; historical audit
HTTP/Chromium figures are not substituted as the paired baseline.

Separate cProfile runs occur only after all uninstrumented measurements,
at 200 garments for original/combined with both preference states. Their default
clock cumulative/self timings are instrumented elapsed times, not per-function
CPU measurements or acceptance latency. Process CPU samples come from the
uninstrumented worker. Constructor/key call counts provide allocation-pressure
evidence; they do not measure every allocation or process peak memory.

## Measured latency and independent effects

Seconds; positive percentage is a median latency reduction, calculated as `(original-variant)/original`. These are observations, not statistical confidence or additive causal effects.

| Garments | Prefs | Original median [min,max] | Combined median [min,max] | Latency reduction |
| --- | --- | --- | --- | --- |
| 20 | None | 0.042 [0.042,0.045] | 0.041 [0.038,0.052] | +3.15% |
| 20 | Four | 0.061 [0.060,0.061] | 0.056 [0.055,0.070] | +6.65% |
| 50 | None | 0.312 [0.296,0.316] | 0.293 [0.287,0.340] | +5.93% |
| 50 | Four | 0.485 [0.483,0.508] | 0.489 [0.489,0.492] | -0.83% |
| 100 | None | 2.869 [2.819,2.935] | 2.720 [2.578,2.743] | +5.20% |
| 100 | Four | 4.675 [4.646,4.690] | 4.312 [4.295,4.322] | +7.76% |
| 200 | None | 21.986 [21.908,22.145] | 19.857 [19.287,19.979] | +9.68% |
| 200 | Four | 35.770 [35.612,36.224] | 33.288 [33.061,33.957] | +6.94% |

| Garments | Prefs | Key-only | Prepared-only | Constants-only | Combined |
| --- | --- | --- | --- | --- | --- |
| 20 | None | +0.96% | +11.40% | +7.86% | +3.15% |
| 20 | Four | +8.47% | +8.55% | +3.26% | +6.65% |
| 50 | None | -3.33% | -5.73% | +4.59% | +5.93% |
| 50 | Four | +0.86% | -1.85% | -2.35% | -0.83% |
| 100 | None | -0.50% | -1.23% | -3.84% | +5.20% |
| 100 | Four | +2.27% | -9.02% | +1.16% | +7.76% |
| 200 | None | +4.55% | +1.31% | +6.51% | +9.68% |
| 200 | Four | +0.40% | +1.55% | +1.43% | +6.94% |

All arm medians/ranges in seconds (three measured trials each):

| Garments | Prefs | Arm | Median | Min | Max | Candidates |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | None | original | 0.042 | 0.042 | 0.045 | 198 |
| 20 | None | key | 0.042 | 0.038 | 0.052 | 198 |
| 20 | None | preferences | 0.037 | 0.036 | 0.039 | 198 |
| 20 | None | constants | 0.039 | 0.038 | 0.040 | 198 |
| 20 | None | combined | 0.041 | 0.038 | 0.052 | 198 |
| 20 | Four | original | 0.061 | 0.060 | 0.061 | 198 |
| 20 | Four | key | 0.055 | 0.054 | 0.057 | 198 |
| 20 | Four | preferences | 0.055 | 0.055 | 0.059 | 198 |
| 20 | Four | constants | 0.059 | 0.055 | 0.060 | 198 |
| 20 | Four | combined | 0.056 | 0.055 | 0.070 | 198 |
| 50 | None | original | 0.312 | 0.296 | 0.316 | 2,430 |
| 50 | None | key | 0.322 | 0.318 | 0.323 | 2,430 |
| 50 | None | preferences | 0.329 | 0.325 | 0.337 | 2,430 |
| 50 | None | constants | 0.297 | 0.289 | 0.315 | 2,430 |
| 50 | None | combined | 0.293 | 0.287 | 0.340 | 2,430 |
| 50 | Four | original | 0.485 | 0.483 | 0.508 | 2,430 |
| 50 | Four | key | 0.481 | 0.464 | 0.535 | 2,430 |
| 50 | Four | preferences | 0.494 | 0.473 | 0.516 | 2,430 |
| 50 | Four | constants | 0.496 | 0.468 | 0.500 | 2,430 |
| 50 | Four | combined | 0.489 | 0.489 | 0.492 | 2,430 |
| 100 | None | original | 2.869 | 2.819 | 2.935 | 17,710 |
| 100 | None | key | 2.883 | 2.776 | 2.923 | 17,710 |
| 100 | None | preferences | 2.905 | 2.757 | 3.390 | 17,710 |
| 100 | None | constants | 2.979 | 2.835 | 3.282 | 17,710 |
| 100 | None | combined | 2.720 | 2.578 | 2.743 | 17,710 |
| 100 | Four | original | 4.675 | 4.646 | 4.690 | 17,710 |
| 100 | Four | key | 4.569 | 4.556 | 4.589 | 17,710 |
| 100 | Four | preferences | 5.097 | 4.617 | 5.337 | 17,710 |
| 100 | Four | constants | 4.621 | 4.618 | 4.772 | 17,710 |
| 100 | Four | combined | 4.312 | 4.295 | 4.322 | 17,710 |
| 200 | None | original | 21.986 | 21.908 | 22.145 | 134,820 |
| 200 | None | key | 20.985 | 20.863 | 21.142 | 134,820 |
| 200 | None | preferences | 21.699 | 21.509 | 22.246 | 134,820 |
| 200 | None | constants | 20.554 | 20.491 | 20.682 | 134,820 |
| 200 | None | combined | 19.857 | 19.287 | 19.979 | 134,820 |
| 200 | Four | original | 35.770 | 35.612 | 36.224 | 134,820 |
| 200 | Four | key | 35.626 | 35.345 | 35.748 | 134,820 |
| 200 | Four | preferences | 35.214 | 35.100 | 35.560 | 134,820 |
| 200 | Four | constants | 35.257 | 35.222 | 35.417 | 134,820 |
| 200 | Four | combined | 33.288 | 33.061 | 33.957 | 134,820 |

At 200 garments, combined throughput-style speedup `(original/combined)-1` is **10.72%** without preferences and **7.46%** with four preferences; median latency reductions are **9.68%** and **6.94%** respectively. CPU medians fall from 21.641 to 19.422 seconds and 35.125 to 32.844 seconds. Individual effects do not add arithmetically.

The 50-garment populated combined median is **0.83% slower**, with overlapping observed ranges: no improvement is claimed there. Prepared-only at 100 populated garments is **9.02% slower** in this sample; its 200-garment result is modestly faster. No uniform per-arm win is claimed. Small sample size, wrapper dispatch in isolated arms and uncontrolled machine variability limit causal attribution. Prepared-only with no preferences has no substantive invariant work to remove, so its apparent gains/losses are control/noise, not attributed to preparation.

Both 200-garment combined service medians still exceed five seconds by a wide margin. No NFR-02 compliance or new HTTP/browser latency result is claimed.

## Separate profiling and object counts

Instrumented elapsed self totals (not service latency or CPU measurements):

| 200-garment workload | Original calls | Combined calls | Original self seconds | Combined self seconds |
| --- | --- | --- | --- | --- |
| No preferences | 89,097,417 | 80,739,211 | 55.891 | 50.649 |
| Four preference types | 146,688,148 | 136,839,282 | 95.929 | 88.726 |

Selected call counts:

| Work | Original, no prefs | Combined, no prefs | Original, four prefs | Combined, four prefs |
| --- | --- | --- | --- | --- |
| Incumbent/challenger key construction | 269,639 | 134,820 | 269,639 | 134,820 |
| ScoreEvidence construction/validation | 539,280 | 269,643 | 1,483,020 | 1,348,203 |
| ComponentScore construction/validation | 404,460 | 134,823 | 404,460 | 269,643 |
| Final RecommendationScore validation | 134,820 | 134,820 | 134,820 | 134,820 |
| Mandatory evaluation including independent gate | 269,640 | 269,640 | 269,640 | 269,640 |

Constants are constructed and validated once per scorer, then reused as
immutable values; the unchanged per-candidate RecommendationScore validator
still checks components, weights and exact total. The extra three constant
objects are one unavailable-C and two distinct empty-P states. These counts
measure constructor pressure, not all heap allocations or peak memory.

No-preference rank comparison cumulative time changes from 5.574 to 3.682s;
empty preference scoring from 1.858 to .164s. Populated preference scoring
changes from 43.200 to 40.096s and comparison from 5.604 to 3.678s. These parent
times include children and cannot be added to an independent time budget.
Request-match scoring remains about 12s and final score validation about 10s
under instrumentation; populated preference evidence/reason construction and
exact arithmetic remain substantial. The `_prepare` getter is called once per
candidate (134,820 calls / .116s cumulative here), but builds facts only for
the first encounter of that immutable preference snapshot. Normalization is
still once per rank, not a removed per-candidate operation.

The separate stream-fingerprint mode hashes canonical ordered mandatory and
scored-candidate records incrementally. It does not retain all candidate
records. Fingerprint runs are instrumented correctness checks, excluded from
latency tables and the profiles above.

## Verification commands

From `backend` (VTOFF off for regressions):

```powershell
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_assistant_performance_equivalence.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_assistant_performance_equivalence.py tests/test_candidate_ranking.py tests/test_recommendation_scoring.py tests/test_preference_modelling.py -q --tb=short
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with pillow --with numpy --with python-multipart python -B scripts/benchmark_assistant_low_risk.py --output ../storage/verification/phase5f2d2a/benchmark
```

Large-stream worker calls, after benchmark fixture generation (no warm-up;
these are correctness instrumentation, not new latency samples):

```powershell
foreach ($preferenceCase in 0,1) {
  foreach ($variant in 'original','combined') {
    uv run --no-project --python 3.12 --with pytest --with fastapi --with pillow --with numpy --with python-multipart python -B tests/performance_worker.py --variant $variant --fixtures "../storage/verification/phase5f2d2a/benchmark/size-200-prefs-$preferenceCase-input.json" --output "../storage/verification/phase5f2d2a/benchmark/digest-prefs-$preferenceCase-$variant.json" --digest
  }
}
```

Compare parsed outputs excluding `timings`; assert identical winners,
persisted score metadata and transcripts, scored_count 134820 and transcript
event count 404460. The executed Python orchestration used those worker
arguments and performs these assertions, recording `stream-digests.json`.
Both no-preference and populated-preference transcripts **matched**, with
404,460 events each: two mandatory evaluations and one complete scored record
per candidate. SHA256 values are respectively
`7338a94fddf5c8c66cfafb3f9732e00114e90e062a75e1f1098b9d61f61a14c5`
and `302fa15c0bd06c36445a5d8bf07fb2ea0b1a43db56905a863adf0ba4cfacb574`.
Canonicalization includes immutable candidate snapshots, exact scores and
evidence/diagnostics; nondeterministic context IDs/seals are excluded as in the
small-fixture oracle. No candidates were retained en masse for this check.

From `frontend`: `npm run test:browser`. Its generated isolated-build changes
to tsconfig were restored to the exact pre-phase file. No frontend source edit.
From repository root: `git diff --check`.

Results:

- Before production edits: 12 differential/tie tests passed (one existing
  Starlette/httpx deprecation warning).
- Initial post-edit focused run: 77 passed in 10.47s.
- Final expanded differential suite after the digest-mode and unknown-C fixture:
  **13 passed**, one warning, 8.17s.
- Broad backend run: **651 passed, one failed**, one warning, 42.86s; this run
  preceded the extra preparation-scoping test, which subsequently passed in
  the final differential suite. The failure is the unchanged
  `test_report_architecture.py:28` assertion that `ai-services` must not exist.
  No folder/assertion was altered. Geometry/CV dependency-heavy tests were
  explicitly excluded; all collected NLP, candidate/mandatory, scoring/ranking,
  suitability, Assistant, persistence, Homepage, history and auth tests ran.
- Browser: **17 passed (1.7m)**, covering controlled/disabled integration,
  real backend login/Homepage/Assistant/history/archival and cross-user access.
  No new browser failure. These are functional regressions, not NFR timings.

Raw test logs, input fixtures, per-arm output/metadata, source/dependency hashes
and profiles are retained under ignored `storage/verification/phase5f2d2a/`.
The two-trial 20-garment smoke run verified tooling only and is excluded from
the reported comparison series.

## Remaining boundaries

No Phase 5F-2D-2B work is implemented: no prepared mandatory evaluators, shared
gate evidence, exact-total memoization, lightweight score constructors,
winner-only diagnostics, mutable progress counters, candidate-member reuse,
pruning, early exit or candidate limits. Those require separate review.

Recommended next investigation, if approved, is bounded exact component/total
reuse while retaining full score validation and independent mandatory proof.
Populated preference evidence construction also remains a hotspot; do not assume
normalization or actual colour classification is repeatedly uncached.

The existing dependency findings, normal review 422/409 blocker and strict
recommendation-source saving/visualisation inconsistencies remain separately
documented and untouched. Experimental holistic compatibility and approximate
hex matching stay disabled; suitability stays opt-in. No final FYP acceptance
or NFR-02 compliance is claimed from this backend-only phase.

## Complete source/document change list

Modified existing files:

1. `backend/app/application/recommendation/candidate_ranker.py`: incumbent key.
2. `backend/app/application/recommendation/preference_scorer.py`: scoped facts and empty components.
3. `backend/app/application/recommendation/compatibility_scorer.py`: deferred constant.
4. `docs/PHASE_5F_2D_1_PERFORMANCE_DESIGN.md`: follow-up link; original baseline retained.

Created:

5. `backend/tests/test_assistant_performance_equivalence.py`: differential, tie, oracle-sensitivity, reference integrity and scoping tests.
6. `backend/tests/performance_worker.py`: isolated frozen/live/mixed-arm runner, full traces, actual persistence, timing and bounded-memory transcript mode.
7. `backend/tests/fixtures/performance_reference/app.zip`: complete pre-edit Python/JSON app reference.
8. `backend/tests/fixtures/performance_reference/manifest.json`: 155 source/configuration hashes.
9. `backend/tests/fixtures/performance_reference/README.md`: capture and maintenance rules.
10. `backend/scripts/benchmark_assistant_low_risk.py`: sequential individual/combined full-service timings and separate profiles.
11. `docs/PHASE_5F_2D_2A_PERFORMANCE_VERIFICATION.md`: this report.

Pre-existing uncommitted changes are not attributed to this phase. Generated
raw artifacts/logs/fixtures/profiles are grouped under ignored storage, not
additional application changes. Frontend tsconfig is byte-restored.

## Closure assessment

**PASS WITH LIMITATIONS: Phase 5F-2D-2A is ready for review/closure.** Test-first
and final differential checks pass, including large complete-stream fingerprints
and persisted metadata. No eligibility, scoring, ranking or failure-semantic
regression was found. Large-workload combined latency improved, while individual
small-sample effects include neutral/slower cells and are not presented as
universal speedups. `git diff --check` passes. The known architecture assertion
remains failing; heavy CV tests were excluded.

NFR-02 remains unmet at 200 garments, independent end-to-end acceptance is not
claimed, and Phase 5F-2D-2B has not started. Its next proposed exact-arithmetic/
component work needs separate approval and equivalent correctness safeguards.
