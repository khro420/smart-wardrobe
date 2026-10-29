# Phase 5F-2D-2D2: exact score-validation arithmetic experiment

2026-10-19. **Arithmetic optimization NOT retained: application-level benefit
was insufficiently consistent.** Production is restored to completed 2D1.
**PASS WITH LIMITATIONS: ready to close as a measured non-beneficial
optimization investigation.** This is not acceptance of a deployed optimization.
No Phase 2D3 work is included.

## Authority and preserved boundaries

The original Project I report, RN-15-21 / sections 4.4.3 and 4.10.4, specifies
the normalized weighted formula, one highest-ranked valid result and deterministic
total/R/C/P/stable-ID tie order. NFR-02 (PDF page 180, printed page 169) concerns
a complete response within five seconds after valid NLP submission in the
baseline environment. Backend timing medians cannot establish that requirement.
Exact integer validation is a separately approved implementation technique,
not a report-prescribed algorithm or permission to weaken input validation.

Written references are `FYP_CONTEXT.md`, `RECOMMENDATION_SCORING.md` and completed
`PHASE_5F_2D_2D1_PROGRESS_VERIFICATION.md`. As recorded in 2D1, the completed 2C
design review exists in the conversation; no persisted 2C report exists here.
All Phase 1-5 contracts, progress results, feature flags and teammate algorithms
are preserved. Compatibility stays deferred, suitability opt-in, approximate
hex mandatory evidence disabled. No scoring weights or component values change.

## Frozen independent reference

Before production edits, all 156 completed-2D1 application Python/JSON files
were frozen under `backend/tests/fixtures/performance_reference_2d1/`.
Archive SHA256:
`ce649a736850e9dac3f844a079e1c32e1e27e77de83af21a25a012aadd4cf059`.
`manifest.json` records every source hash; `environment.json` records Python and
all installed distributions. The full extracted app is imported in a separate
process, not a live helper aliased into a reference class. Older reference
archives, fixture definitions and historical fingerprints are retained.

## Repeated arithmetic and the prototype

The producer's session-owned `ExactScoreReuse.weighted` caches exact weighted
calculation using full weights/contribution keys. It remains unchanged.
`RecommendationScore.__post_init__` independently recomputes the same weighted
total for every score. No producer cache, proof flag or memoized validator result
is consulted by this experiment. Every constructor and mandatory eligibility
gate remains active.

The existing 200/four-preference profile contains 404,474 Fraction multiplications
and 808,942 additions. The independent three-term weighted check contributes
404,460 multiplications and 404,460 additions (three each per 134,820 candidates).
Weight normalization still separately requires summing three weights, and range,
component type, availability representation and provenance handling remain.
The entire validator cost is not removable. Caller-attributed baseline data is
retained in `storage/verification/phase5f2d2d2/baseline-arithmetic-profile.json`.
Fresh profiles are collected separately from latency measurements.

Only `backend/app/domain/value_objects/recommendation_score.py` was changed in
the production experiment. The original initial component/total checks and
weight type/range/sum checks stay ahead of total verification. Provenance remains
after it. Weight normalization to tuple and all public Fraction fields remain.

For each term, write weight a/b and contribution c/d, with positive integer
denominators. Its exact product is A/B = (a*c)/(b*d). Start N=0, D=1 and update
in the existing three-term order:

```
N_next = N*B + A*D
D_next = D*B
```

After all terms, N/D is exactly the independent weighted sum, without requiring
intermediate Fraction construction or normalization. For supplied total t/u,
equality is the integer identity `t*D == N*u`. Python integers do not overflow.
No floating-point conversion, tolerance, approximate comparison, component
reweighting or producer-cache lookup is involved. Large products can increase
temporary integer sizes; performance on huge denominators is not assumed free.

The prototype fast path is restricted to exact built-in Fraction values with
exact integer numerators/positive denominators, plain list/tuple weights and
plain ComponentScore/ScoreEvidence objects using the original contribution
descriptor. Every contribution is read, including zero-weight components.
None retains the existing contribution property's Fraction(0) behavior.
Unknown/subclass cases return to the original expression, preserving operator,
property and exception semantics. Fallback does not rescue an invalid total or
turn unsupported arithmetic into a valid score. The mismatch error remains
before missing-provenance errors.

## Differential methodology

`tests/score_validation_worker.py` independently imports either the frozen or
live value objects. Synthetic cases cover the three configured profile weight
tuples, single-component weights, exact/mismatching totals, zero/boundary values,
large/shared/coprime denominators, all seven evidence availability states,
malformed components/weights/totals, negative inputs and provenance precedence.
Accepted Fraction subclasses record operator calls. Component/evidence/container
subclasses record property/iterator calls, including zero-weight and alternative
legacy int/bool/exact-float contributions. Unsupported Decimal/object arithmetic
retains its original exception. Exact values, full evidence/provenance, errors
and call order are compared, not merely successful booleans.

The final oracle contains **932 identical cases** in reference/trial/restored
arms. It also supplies a deliberately wrong producer-cached total: both the
original and prototype independently reject it and accept the correct total.

Very large rational integers are serialized as decimal strings in the test
oracle to avoid altering pytest's global integer parsing limit. The trusted
synthetic subprocess permits its own large-integer serialization; no application
input or runtime setting changes.

`tests/test_score_validation_equivalence.py` also runs complete Assistant/scorer
traces on the existing full matrix plus mixed evidence: all four structures,
preferences, missing/unknown/malformed evidence, ordered diagnostics, exact
components, tie-breaking, incomplete/interrupted/late-failure streams and actual
SQLite persistence/replay. Progress traces remain separate from preserved score
fingerprints. Existing random context nonces/seals and generated record IDs are
excluded from stable comparisons; ownership/proof/replay checks remain active.
No score, diagnostic, garment identity or progress field is omitted.

### Incremental corrections and exploratory data

The initial three new tests passed against unchanged production (4.96 s).
After the arithmetic edit, the arithmetic/score/ranking selection passed 43
tests (11.57 s). An expanded selection initially had six test-harness failures:
one JSON integer-digit-limit failure and five NameErrors from an allowlist line
incorrectly inserted into a ranker test. Those harness errors were corrected;
81 tests then passed (31.87 s). They were not application regressions.

A subsequent subclass review added a custom container metaclass equality trace.
It exposed an extra callback from `type(weights) not in (tuple, list)`. The
exploratory benchmark was stopped rather than continuing with a semantic
difference. The guard was changed to identity comparisons. The counterexample
then passed with 43 arithmetic/scoring/ranking tests (6.46 s).

`benchmark/` contains the interrupted first-source experiment. It is retained
for transparency but is incomplete and is not used for the acceptance decision.
The corrected source is measured afresh in `benchmark-final/`. No favorable
cells from the interrupted run are substituted into the final run. Initial
isolated constructor microbenchmarks are also exploratory: sequential execution
and substantial host variation prevent treating them as application speedups.
Their separate tracemalloc runs measure temporary traced peaks, not total
allocation traffic or application memory usage.

## Benchmark method

The existing reusable `scripts/benchmark_stream_progress.py` accepts an explicit
reference directory (its old default remains completed 2B). For this phase it
uses completed 2D1, identical 20/50/100/200 fixtures and no/four preferences.
ABBA fresh-worker blocks each have two excluded warmups and three measured
submissions: six samples per arm. No tests, builds or profiles run concurrently
with latency measurement. Every timed interaction completes real NLP, strict
SQLite retrieval, exhaustive generation, the independent gate, exact ranking
and atomic persistence with a fresh submission key. This is service timing,
not browser/HTTP latency. Counts follow (T*B+D)*(1+O), not truncation.

Both arms use Python 3.12.10 and identical pinned primary dependencies:
FastAPI 0.146.0, httpx 0.28.1, Pillow 13.0.0, numpy 2.5.4 and
python-multipart 0.0.32. Complete environment, source/fixture hashes, every trial,
CPU/stage times and ranges are retained in raw results. CPU/memory/power-plan
snapshots are separate host observations, not fixed frequency/thermal controls.
Separate profiles and memory observations must not substitute for latency trials.

## Corrected-source paired application results

Seconds, median [min, max]; six measured samples per arm. Positive speedup
means faster, negative means slower. These are the complete fresh corrected-source
results; the interrupted experiment is excluded from this table.

| Garments | Preferences | Candidates | Completed 2D1 | Integer prototype | Speedup |
| --- | --- | --- | --- | --- | --- |
| 20 | none | 198 | 0.050566 [0.040862, 0.075093] | 0.040026 [0.038056, 0.061577] | +20.84% |
| 20 | four | 198 | 0.050561 [0.044938, 0.059888] | 0.046570 [0.044157, 0.053609] | +7.89% |
| 50 | none | 2,430 | 0.288599 [0.254844, 0.417433] | 0.277656 [0.258501, 0.298192] | +3.79% |
| 50 | four | 2,430 | 0.413861 [0.399664, 0.437538] | 0.416419 [0.382374, 0.442888] | -0.62% |
| 100 | none | 17,710 | 2.236408 [2.155562, 2.337904] | 2.239262 [2.157387, 2.379974] | -0.13% |
| 100 | four | 17,710 | 3.579475 [3.399274, 3.670633] | 3.503185 [3.368670, 3.725938] | +2.13% |
| 200 | none | 134,820 | 17.350508 [16.995539, 17.571575] | 17.484992 [16.313062, 18.876316] | -0.78% |
| 200 | four | 134,820 | 26.630909 [25.785786, 32.357320] | 26.053347 [25.427703, 26.563360] | +2.17% |

All complete counts, selected outfits and persisted score metadata matched.
No-preference CPU medians at 100/200 were 2.1953/16.2266 s versus
2.1797/16.3672 s; four-preference CPU medians at 100/200 were 3.3125/24.7578 s
versus 3.1953/24.2266 s. The small 20-garment CPU medians were unchanged at
0.046875 s in both arms, despite lower wall medians. The 20-garment wall gains
must not be presented as a precise causal arithmetic speedup; ranges and service
I/O/host variation are substantial at that scale.

Slower final cells are 50/four (+2.558 ms), 100/none (+2.854 ms), and
200/none (+134.485 ms). There is no demonstrated disproportionate small-wardrobe
regression. However, correctness alone is insufficient: the modest populated-
preference gains, essentially unchanged/slightly slower no-preference workloads,
and overlapping ranges do not establish a sufficiently consistent benefit for
retaining the additional type guards and integer path. This is a conservative
engineering acceptance decision, not a newly invented mandatory numeric threshold
or a claim that integer arithmetic can never help.

### Retention decision and independently reproducible prototype

**Restore the original production validator.** Its bytes and all other 155 app
Python/JSON files match completed 2D1. The previous approved progress optimization
is retained intact. Historical fixtures/fingerprints and older archives are
unchanged. The temporary arithmetic allowlist additions in the three older
source-integrity tests were removed again.

The corrected prototype is archived separately under
`backend/tests/fixtures/performance_trial_2d2/`, with per-file manifest and
an explicit NOT-retained status. Archive SHA256:
`73660f4ac7bc26cfebbe55ee054474089e87121a97899aae309b01e36d852a35`.
Its 156-file manifest differs from completed 2D1 in exactly
`app/domain/value_objects/recommendation_score.py`. It is test evidence, not a
live policy or an approved alternative default.

New tests now compare **three** separately imported arms: completed-2D1 archive,
corrected-trial archive, and restored live app. Both benchmark/fingerprint tools
accept `--candidate-reference` to execute the archived trial rather than silently
measuring restored live code as if it were optimized. Different archive identities
are checked. Without this option, their historical live-arm behavior is unchanged.

### Memory and allocation observations

Separate fresh-process diagnostics (MiB, reference/trial peak working set):

| Garments | Preferences | Reference | Trial | Change |
| --- | --- | --- | --- | --- |
| 20 | none | 27.102 | 27.176 | +0.074 |
| 20 | four | 27.355 | 27.363 | +0.008 |
| 50 | none | 28.023 | 28.070 | +0.047 |
| 50 | four | 28.062 | 28.449 | +0.387 |
| 100 | none | 27.875 | 27.906 | +0.031 |
| 100 | four | 29.254 | 28.973 | -0.281 |
| 200 | none | 29.348 | 28.977 | -0.371 |
| 200 | four | 29.539 | 29.641 | +0.102 |

These single diagnostic samples include Python/import/SQLite/cache costs and do
not establish a memory saving. The prototype removes intermediate Fraction
arithmetic allocations but adds a helper call, type guards and temporary
iteration/generator/integer work. No new persistent cache exists. Denominator
products can grow larger than reduced Fraction intermediates, especially with
large shared denominators. Correctness tests cover that case; faster performance
for arbitrary huge rational inputs is not claimed. Exploratory constructor
tracemalloc peaks differed by tens of bytes, not a demonstrated application
memory improvement. Retained traced deltas were 32 bytes (loop instrumentation),
not an accumulated score-object cache. Exact total allocated-byte savings were
not measured and are not claimed.

All eight ordered progress digests matched. At 200, each arm retains 539,284
progress construction/yield events with hash
`3abbb50819c84238f0a0deac4b438b564241c45b890d645c82610f19e189261f`.
Counts and full completion are checked before diagnostic output is accepted.

## Changed-file inventory

Final retained changes:

| File(s) | Purpose |
| --- | --- |
| `backend/tests/score_validation_worker.py` | Synthetic exact/malformed/subclass/provenance oracle, independent producer-cache corruption check, exploratory constructor/memory measurements. |
| `backend/tests/test_score_validation_equivalence.py` | Three-arm numeric/full-Assistant comparisons and source/archive integrity; restored production and archived prototype are both covered. |
| `backend/scripts/benchmark_stream_progress.py` | Optional independent reference and archived trial selection, distinct-archive checks, score-source hash and diagnostic/profile provenance. Old defaults remain. |
| `backend/scripts/verify_scoring_fingerprints.py` | Optional archived trial selection for complete historical anchors; prevents comparing the restored live original as the trial. Old defaults remain. |
| `backend/tests/fixtures/performance_reference_2d1/app.zip` | Complete unchanged 2D1 application. |
| `backend/tests/fixtures/performance_reference_2d1/manifest.json` | Every reference source hash. |
| `backend/tests/fixtures/performance_reference_2d1/environment.json` | Freeze environment/archive identity. |
| `backend/tests/fixtures/performance_reference_2d1/README.md` | Reference provenance and reproduction. |
| `backend/tests/fixtures/performance_trial_2d2/app.zip` | Corrected experimental full app, NOT retained in production. |
| `backend/tests/fixtures/performance_trial_2d2/manifest.json` | Every trial source hash; exactly one application file differs. |
| `backend/tests/fixtures/performance_trial_2d2/environment.json` | Environment, archive identity and explicit non-retained status. |
| `backend/tests/fixtures/performance_trial_2d2/README.md` | Experimental-only status and reproduction. |
| `docs/PHASE_5F_2D_2D2_SCORE_VALIDATION_VERIFICATION.md` | This measured experiment and acceptance decision. |
| `docs/REPORT_TRACEABILITY.md` | Requirements preservation and non-retention result. |

Temporarily edited and restored: `backend/app/domain/value_objects/recommendation_score.py`
(byte-identical restoration), and the arithmetic-file allowlist entries in
`test_assistant_performance_equivalence.py`, `test_scoring_hot_path_equivalence.py`,
`test_stream_progress_equivalence.py` (removed after restoration). No such
allowlist exception remains necessary for production. No other app source was
changed. Existing unrelated dirty worktree changes were not reset.

Generated ignored artifacts are under `storage/verification/phase5f2d2d2/`:
interrupted and final benchmark inputs/raw trials, profiles, diagnostics, host
snapshots, numeric oracle outputs, fingerprints and browser-file backups. A final
`artifact_manifest.json` enumerates all generated paths and hashes.

## Verification results

Broad backend command returned **680 passed, 1 known failure, 1 warning, 94.68 s**.
The failure remains `tests/test_report_architecture.py:28`,
`ReportArchitectureTests.test_single_backend_and_canonical_ml_locations`, which
asserts that the existing `ai-services` directory must be absent. Neither the
folders nor the assertion were changed. There are no new backend regressions.
The warning is the existing Starlette/httpx TestClient deprecation.

The broad suite covers the completed Phase 1-5 contracts, old and new differential
suites, exact arithmetic/score/ranking, strict eligibility, structural/request
streams, Assistant, Homepage, chat history and persistence. Unchanged CV-only
`test_segmentation_geometry.py` was excluded because its cv2/torch environment is
not installed; no CV dependencies or algorithms were changed.

### Independent profile evidence

Separate cProfile runs at 200 garments:

| Preferences | Check | Original | Corrected trial |
| --- | --- | --- | --- |
| none | Fraction multiplications | 404,463 | 3 |
| none | Fraction additions | 808,927 | 404,467 |
| four | Fraction multiplications | 404,474 | 14 |
| four | Fraction additions | 808,942 | 404,482 |
| either | Final-score validator calls | 134,820 | 134,820 |
| either | New independent integer check calls | 0 | 134,820 |

Exactly 404,460 multiplications and additions disappear in each workload; the
remaining Fraction arithmetic includes unchanged weight normalization and
producer calculations. Public score fields remain Fraction values. The integer
helper is invoked afresh for every candidate, not once per profile/session.
Its cumulative profiled cost is 3.625 s without preferences / 3.547 s with four.
Final-validator cumulative times were 10.748 -> 9.940 s and 10.613 -> 10.125 s.
The original full-validator cost is clearly not eliminated.

Prototype normal-path guards create five temporary generator objects (two type
scans plus three integer-field scans) instead of the original one weighted-sum
generator, in addition to three integer-part tuples and integer intermediates.
These are static normal-path allocation observations, not a measured aggregate
allocated-byte count. Component contribution reads, including None-to-Fraction(0),
remain. The added defensive overhead consumes much of the arithmetic saving.

Profile totals are not application latency measurements: total self time was
42.640 -> 41.012 s without preferences and 59.087 -> 59.136 s with four (slightly
slower under profiling). Profiling overhead and host variation prevent using
these numbers instead of the uninstrumented ABBA table. Cumulative times overlap
and cannot be added.

### Complete-stream anchors and final status

All four full-stream fingerprint runs returned exit 0. Each arm retained 134,820
scored candidates and 404,460 ordered score/mandatory events, plus 539,284
progress events. Exact winners and persisted scoring metadata matched.
Preserved score-event SHA256 anchors:

- No preferences: `7338a94fddf5c8c66cfafb3f9732e00114e90e062a75e1f1098b9d61f61a14c5`.
- Four preferences: `302fa15c0bd06c36445a5d8bf07fb2ea0b1a43db56905a863adf0ba4cfacb574`.

The comparison explicitly used the distinct original and corrected-trial archives,
not two copies of restored live code. The old pre-2A, 2A, 2B and new 2D1 archive
hashes were rechecked. All eight final workload inputs are byte-identical to the
completed-2D1 benchmark inputs. All 156 live app sources match completed 2D1.

Browser regressions: **17 passed (2.4 min)**. The three Next-regenerated files were
restored byte-for-byte. `git diff --check`: **exit 0**; only the existing
LF-to-CRLF notice for `frontend/app/history/page.tsx` was emitted. A separate
whitespace check covers the phase's new untracked text files as well.





## Exact commands and reproduction

From `backend`, with `$env:SMART_WARDROBE_VTOFF_ENABLED='off'`:

```powershell
# Before production edits: 3 passed, 4.96 s.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_score_validation_equivalence.py -q --tb=short

# Initial arithmetic/score/ranking: 43 passed, 1 warning, 11.57 s.
# Corrected identity-guard version: 43 passed, 1 warning, 6.46 s.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_score_validation_equivalence.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py -q --tb=short

# Expanded differential/scoring selection, after harness correction:
# 81 passed, 1 warning, 31.87 s.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_score_validation_equivalence.py tests/test_stream_progress_equivalence.py tests/test_assistant_performance_equivalence.py tests/test_scoring_hot_path_equivalence.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py -q --tb=short

# Corrected-source latency run, executed while trial was still the live app:
# exit 0; all eight ABBA cells, no concurrent tests/builds/profiles.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/benchmark_stream_progress.py --reference tests/fixtures/performance_reference_2d1 --output ../storage/verification/phase5f2d2d2/benchmark-final --measure-only

# After restoring production, independent archived diagnostics/profiles: exit 0.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/benchmark_stream_progress.py --reference tests/fixtures/performance_reference_2d1 --candidate-reference tests/fixtures/performance_trial_2d2 --output ../storage/verification/phase5f2d2d2/benchmark-final --diagnostics-only

# Final restored-live backend regressions: 680 passed, 1 known failed,
# 1 warning, 94.68 s. Includes independent original/trial/restored comparisons.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short

# Full historical event/progress fingerprints, two DIFFERENT archived apps:
# exit 0; all four complete streams matched the preserved hashes.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/verify_scoring_fingerprints.py --reference tests/fixtures/performance_reference_2d1 --candidate-reference tests/fixtures/performance_trial_2d2 --fixtures-dir ../storage/verification/phase5f2d2d2/benchmark-final --output ../storage/verification/phase5f2d2d2/fingerprints --progress-digest
```

**Reproducing latency now:** add
`--candidate-reference tests/fixtures/performance_trial_2d2` to the latency command,
and choose a new output directory. Without that option, restored live code is
intentionally original, so it cannot stand in for the archived arithmetic trial.
Both arms still use the same worker/interpreter/dependency environment and
validated input files. Hashes in the output identify the actual sources.

Persistent numeric-oracle outputs were also generated with:

```powershell
uv run --no-project --python 3.12 python -B tests/score_validation_worker.py --reference tests/fixtures/performance_reference_2d1 --output ../storage/verification/phase5f2d2d2/numeric-reference.json
uv run --no-project --python 3.12 python -B tests/score_validation_worker.py --reference tests/fixtures/performance_trial_2d2 --output ../storage/verification/phase5f2d2d2/numeric-trial.json
uv run --no-project --python 3.12 python -B tests/score_validation_worker.py --output ../storage/verification/phase5f2d2d2/numeric-restored.json
```

All 932 records are identical across those three files. Focused/broad test counts
overlap and must not be summed as unique tests. The intentionally failing new
metaclass counterexample and initial harness failures are recorded above; neither
remains a failure in the final suite.

Browser tests use `npm run test:browser` from `frontend`, with `tsconfig.json`,
`next-env.d.ts` and `AGENTS.md` backed up/restored in `finally` because Next may
regenerate them. They exercise restored live behavior; archived trial integration
is covered separately by complete backend traces. No frontend source is edited. **17 passed (2.4 min)**. All three potentially regenerated files were verified byte-identical to their backups. Real backend login/Homepage/Assistant/history/archival and existing controlled/disabled UI cases passed; some controlled cases use existing API mocks. Fast Refresh and NO_COLOR warnings did not fail tests.
TypeScript/lint/production build were not repeated for this non-retained backend
experiment; no final FYP deployment/acceptance run is claimed.

## Remaining bottlenecks and closure boundary

The measured experiment does not establish NFR-02 compliance. Production retains
the completed-2D1 validator and its costs. Existing large candidate counts,
preference aggregation, independent mandatory verification, candidate/result
construction, weight/range checks and ranking still dominate the full pipeline.
None was changed here. Reducing Fraction operation counts alone did not establish
a robust overall gain under the fixed workloads.

No base-outfit scoring intermediates, mandatory cache, candidate-member reuse,
pruning, candidate caps or alternate approximate arithmetic were implemented.
Compatibility remains deferred, suitability opt-in and approximate hex matching
disabled. No live API, frontend, persistence, chat history, schema, CV, wardrobe,
saving or visualisation behavior changed. The review payload 422/confirmation 409
issue and strict legacy save/visualisation inconsistencies remain separately
owned coordination items. Final FYP acceptance remains unapproved.

**Ready for closure review as PASS WITH LIMITATIONS, with the optimization
not retained.** No new regression remains. The one known architecture assertion
and excluded CV-only dependency tests are recorded above. The end-to-end latency
problem remains open. Further implementation requires separate user approval.
