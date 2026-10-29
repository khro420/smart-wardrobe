# Phase 5F-2D-2D1: fully validated stream progress construction

2026-10-19. **PASS WITH LIMITATIONS; ready for phase closure review.**
The narrowly scoped optimization is retained. No Phase 2D2 work is included.

## Authority and scope

The original Project I PDF was re-read at PDF page 180 / printed page 169
(NFR-02), and PDF pages 286-287 / printed pages 275-276 (section 4.10.4).
RN-15-21 and sections 4.4.3/4.10.4 require normalized scoring, exactly one
highest-ranked valid result and deterministic total/R/C/P/stable-ID ties.
NFR-02 is a complete-response requirement, not a backend median target.
Fresh-constructor optimization is the user's implementation approval, not a
report-defined algorithm. Phase 1 eligibility, Phase 2 NLP, Phase 3 validity,
all scoring arithmetic, weights, preferences and persistence remain unchanged.

There is no persisted `PHASE_5F_2D_2C_PERFORMANCE_DESIGN.md` in this checkout.
The completed 2C review was supplied in the conversation. Existing written
references are `PHASE_5F_2D_1_PERFORMANCE_DESIGN.md` and the completed 2A/2B
verification reports. No nonexistent 2C file is claimed as reviewed.

## Independent reference

Before production edits, all 156 application Python/JSON files were archived
in `backend/tests/fixtures/performance_reference_2b/app.zip`.
Archive SHA256:
`b55ab174454eaa161d9c3d0a63ed59f81e97a6d097669625979fcb74ab14f87f`.
The directory includes per-file `manifest.json`, `environment.json`, and a
README. The original arm validates all archive members and imports the entire
extracted application in a separate process, including transitive dependencies.
The combined arm imports live application code. The pre-2A and completed-2A
archives, existing fixture definitions and historical fingerprints are intact.

## Exact production change and equivalence boundaries

Only normal progress updates in `recommendation_engine.py` and
`request_candidate_session.py` were changed for the experiment. For an exact
base result type, create a fresh result through its normal dataclass constructor.
For subclasses or other result types, preserve generic `dataclasses.replace`.
Terminal completion, interruption, close and error updates retain `replace`.

Structural construction supplies all six fields: Running status, previous
complete, incremented candidate_count, previous reason/exclusions/validity.
Request construction supplies all seven: Running status, previous complete,
incremented examined, increment only the selected passed/failed/unknown counter,
preserve the other counters and reason. Neither old object is mutated. Default
values are not substituted for existing values. Every construction invokes the
existing `__post_init__`; no deferred or bypassed validation is introduced.
Tests guard field names and init semantics so a future schema change requires
review. Subclasses retain their extra fields, InitVar defaults, init=False
recomputation and custom validation through the original generic operation.

The structural update remains outside the iterator exception handler: a normal
progress constructor exception propagates unchanged. The request update remains
inside its existing handler: validation failure records ProcessingFailure and
closes the structural session. Constructor-fault tests exercise both boundaries.
No new global cache or shared mutable state is introduced.

## Differential methodology

`test_stream_progress_equivalence.py` independently runs completed-2B and live
applications on the existing small full-trace matrix plus mixed-evidence cases.
An optional worker channel observes every successfully validated progress object,
including rejected candidates and terminal/error updates. This channel is
separate from the existing ordered mandatory/score events, so their historical
hash format is unchanged. It does not replace or skip original validators.

As in the existing oracle, score transcripts omit random per-session context
nonces and opaque proof seals; persistence comparison omits generated record IDs
and timing samples. Actual ownership, proof binding and replay integrity remain
validated by the production gate/repository and regression tests. No score,
condition, diagnostic, garment identity or progress field is omitted.

The fixtures include all four structures, no/four preferences, mandatory
Pass/Fail/Unknown, missing/malformed/conflicting evidence, ordered diagnostics,
exact Fraction components, tie-breaking, incomplete/early/late/interrupted
streams, close failures and actual persistence/replay. Additional direct tests
cover subclasses, InitVars, init=False fields, mutable-attempt rejection, fresh
per-step snapshots, nonzero counters, diagnostics and interleaved sessions.

## Benchmark methodology

`backend/scripts/benchmark_stream_progress.py` runs each size/preferences cell
in ABBA fresh-worker blocks: reference, trial, trial, reference. Each block has
two excluded warmups and three measured submissions, six samples per arm.
Every measured submission uses a fresh key and completes real NLP, strict
SQLite garment retrieval, exhaustive candidate enumeration, independent gate,
exact scoring/ranking and atomic persistence. No saved outfits are needed.
User preferences are injected fixture snapshots. HTTP, authentication transport,
frontend rendering and browser latency are not measured.

Both arms use Python 3.12.10 and identical dependencies, recorded in full in
raw results (FastAPI 0.146.0, httpx 0.28.1, Pillow 13.0.0, numpy 2.5.4,
python-multipart 0.0.32). Workloads use 40% tops/40% bottoms/10% dresses/rest
outerwear. Counts are independently calculated as (T*B+D)*(1+O). Fixtures,
source hashes, individual wall/CPU/stage samples and all ranges are retained.
All eight input files were verified byte-identical to the completed-2B benchmark
inputs; no easier workload was substituted.
No build, profile or unrelated tests ran concurrently with latency measurements.

Windows 11, AMD Ryzen 5 7235HS, eight logical processors, Balanced power plan.
Pre-run snapshots record CPU load and available memory in
`storage/verification/phase5f2d2d1/`. These are host observations, not CPU
affinity, fixed-frequency or thermal controls. Other user/OS activity cannot be
excluded. Paired runs and ranges reduce but do not eliminate host variation.
Progress tracing, RSS diagnostics and cProfile are separate later runs; their
times must not be compared with uninstrumented latency samples.

## Fresh uninstrumented measurements

Seconds, median [min, max], six measured samples per arm. Positive percentage
means faster; negative means slower. All counts and winner/score metadata matched.

| Garments | Preferences | Candidates | Completed 2B reference | Direct construction | Speedup |
| --- | --- | --- | --- | --- | --- |
| 20 | none | 198 | 0.049460 [0.045482, 0.051246] | 0.053364 [0.047637, 0.072082] | -7.89% |
| 20 | four | 198 | 0.074085 [0.070547, 0.079585] | 0.074589 [0.058832, 0.104679] | -0.68% |
| 50 | none | 2,430 | 0.350303 [0.346328, 0.396308] | 0.350099 [0.304674, 0.403386] | +0.06% |
| 50 | four | 2,430 | 0.551432 [0.498536, 0.602193] | 0.554520 [0.485973, 0.615981] | -0.56% |
| 100 | none | 17,710 | 2.453775 [2.329167, 2.725571] | 2.323934 [2.225643, 2.438450] | +5.29% |
| 100 | four | 17,710 | 3.425177 [3.361023, 3.679593] | 3.390496 [3.216106, 3.610800] | +1.01% |
| 200 | none | 134,820 | 17.713201 [17.173845, 18.262351] | 17.039334 [16.823895, 17.737971] | +3.80% |
| 200 | four | 134,820 | 28.618305 [26.274190, 37.491279] | 25.831849 [25.685674, 29.005543] | +9.74% |

At 200, reference AB block medians (first/last) were 17.700/18.211 s without
preferences and 28.489/28.985 s with four; trial middle block medians were
17.169/16.910 and 25.832/25.738. Both trial blocks outperform both controls
in each large workload. Aggregate CPU medians also decrease: 16.758 -> 15.875 s
and 26.398 -> 24.094 s. Ranges overlap and the four-preference reference has a
37.491 s outlier. Six samples are not evidence of a precise universal speedup
or a p95; host variation contributes uncertainty. The improvement is credible
for retaining this narrow change, not a guarantee that all of the observed
wall-time difference is caused by constructor dispatch alone.

The slower cells are 20/no preferences (+3.904 ms), 20/four (+0.504 ms), and
50/four (+3.088 ms). They are explicitly retained rather than hidden. These
small absolute differences and overlapping ranges do not amount to a
disproportionate application regression relative to the consistent large-cell
benefit. The 50/no-preference result is effectively unchanged. No arbitrary
performance or candidate-count threshold was introduced.

## Progress and memory observations

All eight paired diagnostic streams match, including every validated result
and every structural/request yield. At 200 the progress hash is
`3abbb50819c84238f0a0deac4b438b564241c45b890d645c82610f19e189261f`
with 539,284 events per arm: 269,644 result constructions and 269,640 yields.
The no/four-preference progress hashes are equal because preference scoring
must not change candidate progress. Smaller event counts are 796 / 9,724 /
70,844 at 20 / 50 / 100 garments. No progress snapshot is pooled or skipped.

Separate fresh-process Windows peak working sets (MiB; not allocation totals):

| Garments | Preferences | Reference | Trial | Change |
| --- | --- | --- | --- | --- |
| 20 | none | 27.078 | 26.977 | -0.101 |
| 20 | four | 27.406 | 27.137 | -0.269 |
| 50 | none | 27.918 | 27.777 | -0.141 |
| 50 | four | 28.133 | 28.168 | +0.035 |
| 100 | none | 28.059 | 28.242 | +0.184 |
| 100 | four | 28.910 | 28.961 | +0.051 |
| 200 | none | 29.398 | 29.277 | -0.121 |
| 200 | four | 29.469 | 29.680 | +0.211 |

These are single instrumented process observations and include Python, imports,
SQLite and evidence caches. They do not establish a statistically significant
memory improvement. Result allocation sizes and result construction counts are
unchanged; the experiment removes generic copying overhead rather than result
objects. Exact allocated-byte or lifetime-allocation reductions are not claimed.

## Changed files

| File | Purpose |
| --- | --- |
| `backend/app/application/recommendation/recommendation_engine.py` | Exact-type, fresh fully validated structural progress construction only. |
| `backend/app/application/recommendation/request_candidate_session.py` | Exact-type, fresh fully validated request progress construction only. |
| `backend/tests/performance_worker.py` | Optional independent progress construction/yield tracing and bounded digest channel; historical score transcript unchanged. |
| `backend/tests/test_stream_progress_equivalence.py` | Independent completed-2B full traces, field/init guards, fallback, validation failures and session isolation. |
| `backend/tests/test_assistant_performance_equivalence.py` | Permit only the two newly approved production files in the historical source-integrity allowlist. Frozen bytes/fixtures unchanged. |
| `backend/tests/test_scoring_hot_path_equivalence.py` | Same narrow allowlist extension for completed-2A checks. |
| `backend/tests/fixtures/performance_reference_2b/app.zip` | Independently executable, unchanged completed-2B application. |
| `backend/tests/fixtures/performance_reference_2b/manifest.json` | Every archived application's source hash. |
| `backend/tests/fixtures/performance_reference_2b/environment.json` | Freeze environment, archive hash and source count. |
| `backend/tests/fixtures/performance_reference_2b/README.md` | Reference provenance and independent execution instructions. |
| `backend/scripts/benchmark_stream_progress.py` | Fresh ABBA measurements, separate progress/RSS diagnostics and profiles. |
| `backend/scripts/verify_scoring_fingerprints.py` | Optional reference directory and progress digest; existing default/anchors preserved. |
| `docs/PHASE_5F_2D_2D1_PROGRESS_VERIFICATION.md` | This scoped verification report. |
| `docs/REPORT_TRACEABILITY.md` | Requirement preservation and performance evidence entry. |

Generated local measurement files are under the ignored
`storage/verification/phase5f2d2d1/` directory: host snapshots, benchmark inputs,
all block samples, diagnostics, profiles, fingerprints and browser-file backups.
They are measurement artifacts, not application/policy changes. A final artifact
manifest enumerates their paths and hashes. Pre-existing worktree changes are
not part of this phase and were not reset.

## Verification and acceptance

Retain the two-file optimization: equivalent full-stream behaviour has passed
focused independent comparisons, with a credible large-wardrobe improvement and
no disproportionate small-workload regression. No semantics, validation or
candidate completeness was traded for speed. Overall closure status: **PASS WITH LIMITATIONS; ready for user review and
closure of Phase 5F-2D-2D1 only**. The known architecture assertion and the
remaining end-to-end latency gap are not new regressions.

Separate profiles confirm 269,642 -> 2 `dataclasses.replace` calls at 200;
the remaining two are terminal updates. In both arms, structural-result and
request-result `__post_init__` each execute 134,822 times, final-score validation
134,820 times, and mandatory evaluation 269,640 times. Every normal progress
result remains a new validated object. Generic copy calls decrease by 269,640;
this is a dispatch/allocation-opportunity observation, not a measured total
allocated-byte saving. The original result classes and their validators are
byte-identical to the frozen reference.

Profiles are diagnostic, not latency evidence. No-preference total profiled
self time was 45.939 -> 43.527 s; four-preference was 65.277 -> 65.496 s
(slightly slower under profiling). Profiling overhead and host conditions mean
these totals must not substitute for the uninstrumented ABBA comparison.

Remaining trial-profile cumulative hotspots at 200/four preferences include
preference scoring 21.689 s, final-score validation 11.698 s, mandatory evaluation
9.909 s across both producer and independent verifier, request scoring 5.734 s,
and rank comparison 3.868 s. Gate verification includes 7.553 s, overlapping
mandatory evaluation. Cumulative times overlap and cannot be added. Structural
construction and exact Fraction arithmetic also remain. None of these other
paths was optimized in this phase. No score-validation arithmetic shortcut,
base-outfit intermediate, mandatory cache, member reuse or pruning was added.

### Full historical fingerprints

All four instrumented runs passed against the independently executed completed-2B
reference. Each retained 134,820 scored candidates, 404,460 ordered mandatory/score
events, 539,284 progress events, exact winners and persisted scoring metadata.
The preserved mandatory/score SHA256 anchors remain:

- No preferences: `7338a94fddf5c8c66cfafb3f9732e00114e90e062a75e1f1098b9d61f61a14c5`.
- Four preferences: `302fa15c0bd06c36445a5d8bf07fb2ea0b1a43db56905a863adf0ba4cfacb574`.

`fingerprints/results.json` retains the four summaries and separate per-arm
outputs retain progress hashes. No candidate or event sampling was used.
Reference hashes and all 156 production source hashes were rechecked: only the
two approved production files differ. The pre-2A and completed-2A archive hashes
also match their existing recorded values.

### Exact commands and results

From `backend`, with `$env:SMART_WARDROBE_VTOFF_ENABLED='off'`:

```powershell
# Before production edits: 10 passed, 1 warning, 8.51 s.
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_stream_progress_equivalence.py -q --tb=short

# Initial post-change focused run: 196 passed, 1 warning, 40.62 s.
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_stream_progress_equivalence.py tests/test_scoring_hot_path_equivalence.py tests/test_assistant_performance_equivalence.py tests/test_structural_candidates.py tests/test_request_candidates.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_outfit_assistant.py -q --tb=short

# All eight fresh ABBA cells: exit 0. No concurrent tests/builds/profiles.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/benchmark_stream_progress.py --output ../storage/verification/phase5f2d2d1/benchmark --measure-only

# Separate progress/RSS diagnostics and four CPU profiles: exit 0.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/benchmark_stream_progress.py --output ../storage/verification/phase5f2d2d1/benchmark --diagnostics-only

# Broad Phase 1-5 and existing backend regressions: 675 passed, 1 failed,
# 1 warning, 97.48 s. See known failure below.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short

# Final focused run, including additional fallback/session tests:
# 200 passed, 1 warning, 47.96 s.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_stream_progress_equivalence.py tests/test_scoring_hot_path_equivalence.py tests/test_assistant_performance_equivalence.py tests/test_structural_candidates.py tests/test_request_candidates.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_outfit_assistant.py -q --tb=short

# Instrumented exhaustive historical anchors plus progress snapshots: exit 0.
# All four complete streams matched the independent reference and old hashes.
uv run --no-project --python 3.12 --with pytest --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B scripts/verify_scoring_fingerprints.py --reference tests/fixtures/performance_reference_2b --fixtures-dir ../storage/verification/phase5f2d2d1/benchmark --output ../storage/verification/phase5f2d2d1/fingerprints --progress-digest
```

The broad-suite sole failure is pre-existing:
`tests/test_report_architecture.py:28`,
`ReportArchitectureTests.test_single_backend_and_canonical_ml_locations`,
which asserts that existing `ai-services` must be absent. Neither directories
nor assertions were removed/restructured to force a pass. There are no new
backend failures. Two final extra fallback tests were added after the broad
run and passed in the final focused run; broad and focused counts overlap and
must not be added as unique tests. The warning is the existing Starlette/httpx
TestClient deprecation.

`test_segmentation_geometry.py` was not executed: unchanged CV-only tests need
the unavailable cv2/torch dependency environment. No CV dependencies were
installed or CV algorithms changed. Frontend TypeScript/lint/production-build checks were
not repeated for this backend-only edit; shared workflows are checked with the
existing browser suite. No deployment database or production FYP acceptance
run is claimed.

From `frontend`, `npm run test:browser` runs the existing browser suite, with
`tsconfig.json`, `next-env.d.ts` and `AGENTS.md` backed up and restored in a
PowerShell `finally` block because Next may regenerate them. **17 passed (2.4 min)**. Byte-for-byte restoration of all three files was verified. Real backend login, Homepage, Assistant, history, archival and controlled/disabled flows passed; some controlled UI cases use the existing API mocks. Fast Refresh/NO_COLOR development warnings did not fail tests. No frontend source was changed.

From repository root, `git diff --check` returned exit 0. Git emitted the existing
LF-to-CRLF notice for `frontend/app/history/page.tsx`; this is not a whitespace
failure or a phase modification.

### Remaining boundaries and closure

Large-wardrobe latency remains above the report's eventual complete-response
target. This phase does not establish NFR-02 compliance or final FYP acceptance.
Compatibility remains deferred with weights (7/10, 0, 3/10), approximate hex
mandatory evidence disabled and suitability opt-in. Strict eligibility,
mandatory validation, independent verification, exact arithmetic, stream
completion/failure, persistence/idempotency and all API policies are unchanged.

The existing review payload neckline/sleeve_length 422 then confirmation 409
blocker, and weaker legacy recommendation-source saving/visualisation eligibility,
remain separate teammate-coordination items. No teammate module, frontend
workflow, schema, historical record or feature-flag default was edited.
No Phase 2D2 optimization or other follow-on work is authorized by this report.
