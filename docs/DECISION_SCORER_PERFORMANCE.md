# Phase 5F-2E-3C-3A: decision-scoring performance and activation readiness

Date: 2026-10-20. Scope: isolated experimental optimization and read-only readiness
audit. No live activation, source contract weakening, production migration or historical rewrite.

## Compared implementations and authority

A = current live compatibility-deferred scorer (RecommendationScorer, 0.70/0/0.30).
B = retained cached Phase 3A experimental scorer (request-led 0.60/0.20/0.20).
C = unchanged original Phase 3C-2 decision scorer, midpoint/no-pair policy.
D = separate prepared Phase 3C-2 implementation with the identical approved policy.

A does not measure C. B refuses a session with any unresolved C, including single
dresses. C and D score every mandatory-valid candidate using explicit conventions.
Their different outcomes are intentional: only C/D must match exactly. A is the
same scorer used by the live Assistant, but these measurements invoke the scorer
offline; they do not invoke the live service, SQL, HTTP or browser.

Original report RN-17-21 and sections 4.4.3/4.10.4 require separate scoring,
validity before scoring, the weighted formula and deterministic selection.
The approved fixed 0.60/0.20/0.20 profile, bounds/midpoint and single-dress 1/2
reference are implementation policies, not empirical quality measurements.
See COMPATIBILITY_DECISION_POLICY.md and completed Phase 1-4 contracts.

## Profiling evidence: inherited versus new work

Profile: 100 synthetic garments, 17,710 complete candidate occurrences. Raw
profile.before.v1.json contains A/B/C; profile.attempt.v1.json contains matched
C/D after implementing only the measured correction. Both live in
storage/verification/phase5f2e3c3a. cProfile wall times include profiler overhead;
its cumulative entries overlap and must never be added as independent costs or
compared directly to uninstrumented benchmark seconds.

Initial profiled walls: A 4.040s, B 6.966s, C 9.448s. Initial C's policy.apply
cost 2.549s cumulative INCLUDING 1.379s decision validation. The 0.194s weights
property cost is separate; its 35,420 calls build six fixed weight Fractions per
candidate. This identifies avoidable creation arithmetic, not a reason to remove
validation. Cached raw compatibility aggregation costs 2.660s in C and 2.945s in B;
that work, candidate generation/iteration, score validation and eligibility checks
are inherited. Their different elapsed values also show environmental variability.

| Initial 100-garment C path | Calls | Self seconds | Cumulative seconds |
|---|---:|---:|---:|
| DecisionPolicy.apply | 17,710 | 0.1755 | 2.5490 |
| CompatibilityDecision validation | 17,710 | 0.2295 | 1.3788 |
| Decision adapter validation | 17,710 | 0.0242 | 0.1344 |
| weights property | 35,420 | 0.0479 | 0.1943 |
| ScoreEvidence validation | 58,143 | 0.1954 | 0.6350 |
| ComponentScore validation | 35,433 | 0.0600 | 0.2088 |
| RecommendationScore validation | 17,710 | 0.1138 | 1.1177 |
| Candidate stream next | 17,711 | 0.0967 | 1.3146 |
| Independent gate verify | 17,710 | 0.0759 | 0.3402 |
| Pair-cache pair | 49,700 | 0.1210 | 0.4213 |
| Ranker better | 17,710 | 0.0503 | 0.4324 |
| Fraction constructor | 536,187 | 0.3970 | 0.5020 |

The separate C/D profile has wall 11.979s / 11.091s. Do not compare D's latter
wall with the earlier C 9.448s as if both were matched. In that C/D profile:

| Path | Original C calls / cumulative seconds | Prepared D calls / cumulative seconds |
|---|---|---|
| Policy.apply | 17,710 / 3.1798 | 17,710 / 2.4751 |
| Arithmetic factory | repeated within apply | 44 / 0.0032 |
| Fixed weights property | 35,420 / 0.2490 | 1 / <0.001 |
| Fraction constructor | 536,187 / 0.652 | 324,242 / 0.383 |
| Fraction additions | 492,981 / 0.9111 | 358,517 / 0.7171 |
| Fraction divisions | 159,300 / 0.3645 | 106,332 / 0.2611 |
| Fraction multiplication | 53,151 / 0.1181 | 53,151 / 0.1258 |
| math.gcd normalization | 1,115,789 / 0.1703 | 736,388 / 0.1209 |
| Original decision validation | 17,710 / 1.6872 | 17,710 / 1.7762 |
| Original adapter validation | 17,710 / 0.1705 | 17,710 / 0.1764 |
| Original RecommendationScore validation | 17,710 / 1.3991 | 17,710 / 1.4642 |
| Original ScoreEvidence validation | 58,143 / 0.7861 | 58,143 / 0.8076 |
| Independent gate verify | 17,710 / 0.4360 | 17,710 / 0.4443 |
| Pair-cache pair | 49,700 / 0.5239 | 49,700 / 0.5408 |
| Final rank comparisons | 17,710 / 0.5494 | 17,710 / 0.4573 |

Fraction constructions decrease by 211,945 (39.5%) in this profiled workload. Bounds creation
is reused, while original bounds validation recomputes/checks them for EVERY
candidate. Numeric constants do not replace observed raw evidence. Candidate-
specific raw/decision/adapter allocations and score construction remain; no
candidate or diagnostic object is skipped. Metadata serialization of returned
winners occurs outside timing; no per-candidate JSON was present to optimize.
Profiling measures calls and CPU costs, not exact allocation bytes or fashion quality.

## Attempted correction and security/correctness boundaries

One correction is attempted as a separately selected PreparedDecisionRecommendationScorer:
1. Freeze original validated policy name/version/hash and weight tuple once/session.
2. Reuse exact arithmetic facts through a session-owned LRU, maximum 256 entries.

Numeric keys contain the complete ordered atomic value vector: None for an
unresolved value, otherwise the canonical integer numerator/denominator. This
avoids repeated Fraction hashing and preserves exact zeros. The original policy
identity is bound by the containing immutable prepared policy; each rank call
creates a fresh instance. Only immutable numeric facts (M, known count, K, L, U,
midpoint and basis) are retained, never raw evidence, candidates, users, snapshots,
mandatory proofs, diagnostics or decisions. Each result uses the CURRENT raw
ComponentScore and the unchanged original CompatibilityDecision constructor,
DecisionCompatibilityComponent constructor, RecommendationScore validation,
independent eligibility gate and CandidateRanker. No unchecked construction or
validation bypass is introduced. A cache hit with inconsistent raw evidence still
fails original validation. Arithmetic eviction/disabled capacity recomputes exactly.

The existing 19,900-entry pair cache, owner/context/snapshot/rule-policy checks,
full candidate iteration, count/failure guarantees, exact R/P and tie-breaking
are unchanged. There is no global/session-shared cache of user data. Pure numeric
constants are context-independent; they cannot certify eligibility or replace
candidate-specific provenance. The no-pair branch uses the original policy.apply
unchanged. D has exactly the same public output value types and metadata as C,
so the existing explicit versioned codec restores identical rational totals.

D is a separate small coordinator twin because C and its five source/config files
must remain the differential oracle. Future maintenance must update any proposed
implementation intentionally and rerun differential tests; no archive is rewritten.
No speculative new construction fast path, candidate pruning, structure change,
ranking shortcut, metadata suppression or live refactoring was attempted.

## Correctness verification design

C/D equality covers every score/evidence/decision field, bounds, states, reasons,
coverage, ordered candidate identity, counts, completion, winner and metadata JSON.
Only separately generated gate context nonces differ across independent runs.
Tests calculate L/U/midpoint independently from atomic outputs, stress 301
synthetic rational vectors beyond a two-entry arithmetic cache and force pair
cache eviction at 0/1/2/default capacities. Synthetic arithmetic stress is not
claimed as garment evidence. Tests cover all four structures, measured zero,
missing/empty/malformed/unsupported attributes, mixed dresses, mandatory Unknown
and Fail, ties, changed snapshots/policies, parallel sessions, late failure and
interruption. Every candidate is observed to call all three original safeguards.
Nonzero R/P and exact serialization/replay are compared too.

Five disposable SQLite/history cases verify measured, zero, partial, entirely
unknown and no-pair metadata through the unchanged real writer and completed-
history reader. NULL raw compatibility stays NULL, measured zero stays zero and
exact decision/bounds/basis/coverage/policy are separately restored. Deployment
DBs and existing historical rows are not touched. Injection tests reproduce the
live service's signature and profile guards without enabling any live service.

## Stronger benchmark protocol

Six matched four-arm runs per workload, alternating ABCD/DCBA three times each.
All five requested workloads are retained: 20,50,100,200 ordinary and 200 heavy.
C/D outputs MUST match within every run, and all policy-specific records must
repeat identically; A/B outcomes are not forced to equal C/D. GC collection occurs
outside timing, normal GC stays enabled, and first runs are not discarded. Each
arm has a separate fresh-process complete-pass peak working-set RSS measurement.
The wall clock covers query-interface acquisition, generation, mandatory rules,
independent verification, scoring and ranking, excluding database/HTTP/browser.
Candidate counts and analytical pair counts are asserted; no truncation is allowed.

Synthetic primary colours/styles are recognized in this performance dataset;
ordinary workloads contain unlayered dresses, while the heavy workload does not.
All performance runs use a generic structured request and no preferences.
This measures that fixed case, not every request distribution, photograph or
production workload. High-entropy arithmetic vectors can miss more often; cache
benefit is not universal. Cache capacity remains bounded independently of wardrobe.
Raw reports record all arms, timings, fingerprints, diagnostics, winner scores,
cache statistics, source hashes, interpreter/OS and GC settings.

Host: Windows 11 build 26200, AMD Ryzen 5 7235HS (4 cores/8 logical CPUs), Python
3.12.10. No regression tests, profiler or PDF extraction run concurrently with
this final timing experiment. Read-only code/documentation work occurs while it
runs; host background processes, thermal state and power are not independently
controlled. Six samples do not establish p95 or statistical significance.
Prior phase timings use different runs and are NOT mixed into paired statistics.

## Read-only activation audit: minimum future integration

| Existing boundary | Confirmed current behavior | Minimum proposed future change (NOT implemented) |
|---|---|---|
| OutfitAssistantService.recommend, lines 62-71 | Calls rank(user,request,"compatibility_deferred"); then strictly checks profile name, Unavailable C and weights 7/10,0,3/10. | Introduce a versioned, allowlisted server-side scoring-policy selection with old default. A signature adapter alone fails the existing profile guard. Explicitly validate the selected decision tag/hash/weights and retain all stream guarantees. |
| WorkflowRuntime, lines 54-63 | Assistant enablement and suitability are separate default-false flags; service uses default RecommendationScorer. | Proposed SMART_WARDROBE_ASSISTANT_DECISION_SCORING_ENABLED=false setting, explicit allowlisted scorer factory/profile wiring, invalid selections fail closed; no client-selected weights. This setting is not added here. Homepage/random selection remains untouched. |
| RecommendationRepositoryAdapter, lines 72-82 | SQL compatibility_score uses raw summary.value; score_json already serializes decision fields and exact Fractions. | No demonstrated schema migration needed. Add explicit decision-aware validation/projection at the application/read boundary and policy/implementation provenance; preserve SQL NULL and every historical payload. |
| decision_score_codec | Explicit tag/profile/hash check and exact replay already work. | Deliberately dispatch known versions for current and historical consumers, reject malformed new-policy payloads, retain legacy fallback without inferring midpoint from old NULL rows. |
| ChatHistoryQuery, lines 94-120 | Restores generic metadata through the existing repository on one read snapshot, without rescoring. | Optional versioned score-view projection; never rerun ranking or overwrite original rows. Historical display must use stored policy identity, independently of current flag. |
| frontend/lib/api.ts, lines 108-112 | IntegratedRecommendation has nullable compatibility_score and score_metadata?:unknown; no typed decision view. | Add a validated/discriminated DTO: raw state/value, basis, contribution, optional bounds, known/possible, structure and policy version. Preserve legacy/unknown-version states. |
| RecommendationResult.tsx, line 71 | Only deferred profile gets a message saying compatibility was not measured; no decision-basis display exists. | Approved shared display for Assistant/history: measured narrow-rule score versus midpoint/fully conventional/no-pair references; explicitly label bounds as possible-value bounds, not confidence. Never show reference .5 as measured fashion accuracy. |
| API/capabilities | Current booleans expose Assistant/Homepage availability, not scoring policy; existing controlled 422/409/503 mappings. | Deliberate backwards-compatible capability/policy disclosure if needed; keep existing controlled failures, retries, idempotency, strict revalidation and authentication. No new success on incomplete streams. |

Actual disposable database/history checks prove all four evidence bases survive
persistence; they do not establish presentation readiness. Existing generic JSON
can carry the distinction, but its public typing/presentation cannot explain it
accurately today. The current component does not display numeric compatibility,
so this audit does not allege an existing numerical mislabelling bug; it identifies
the missing explanation/contract needed for future new-policy results. A narrow read-model/DTO plus shared renderer is the contract
change required BEFORE showing decision values. Existing scalar NULL alone cannot
identify the basis. No historical recommendation/chat mutation or save/visualisation
change is needed or approved for this optimization. Existing submission retries
resolve stored recommendations before fresh ranking; after a future setting change,
old keys must still replay their original profile/metadata rather than reranking
or upgrading a historical result. New scoring selection applies only to new
submissions. Keep this separate from saving/visualisation revalidation.

Recommended next stage is a separately approved default-off Assistant integration
and decision-aware current/history display, with unit/API/browser tests for both
settings and all evidence bases, replay/version checks, owner isolation and late
failures. Do not approve general deployment merely because wiring works. Performance
and academic policy usefulness remain separate activation gates. Homepages should
continue their independently approved random selection, not this weighted scorer.

## NFR-02: preserved requirement and measurement layers

Original PDF page 180 (printed p.169) was re-read: a valid NLP submission must
return one recommendation, no-result or unsupported response within five seconds
under the baseline test environment. It defines no wardrobe-size exemption and
no median-only success criterion. This row does not quantify hardware or a maximum
wardrobe size. Section 4.11.4 (PDF p.302, printed p.291) also retains the targets
for verification against the final implementation/test environment; it does not
provide an exemption or a numerical wardrobe/hardware definition. The repository's established test plan covers 20/50/100/200 garments;
this phase retains 200 ordinary and the separate 200-heavy stress distribution.
Do not retroactively redefine baseline size or call 200 exempt to obtain a pass.
Final acceptance hardware/workload must be stated with the supervisor/user, and
any approved amendment documented as an amendment rather than a compliant result.

These experiments are offline backend scorer runtime. HTTP latency must also
include authentication, NLP, SQL acquisition/revalidation/writes and serialization;
browser latency adds network and rendering. No new HTTP/browser measurement or
live-policy acceptance claim is made. Existing old HTTP/browser measurements are
historical evidence from their own environments, not derived from these times.
After optimization the remaining gap will be reported from the measured D values.

Even zeroing incremental decision-construction overhead cannot eliminate inherited
complete enumeration, candidate/result allocation, raw pair aggregation, exact
score validation, independent verification and ranking cost. They occur for every
mandatory-valid candidate. An academically defensible next action is an approved
architecture review of exact aggregation/reuse or exact best-candidate search with
proof of equal eligibility, coverage/count/diagnostics and failure semantics;
changes to exhaustive/count contracts require explicit approval. Measure again
on the declared acceptance environment before activation. Do not truncate, return
fabricated no-result, remove independent checks or publish a provisional winner.

## Files and commands

Created:
- backend/app/application/recommendation/prepared_decision_policy.py: frozen prepared
  policy constants and bounded exact arithmetic facts; original validators retained.
- backend/app/application/recommendation/prepared_decision_scorer.py: explicit twin.
- backend/tests/test_prepared_decision_performance.py: differential, independent
  arithmetic, validation counts, isolation/failure and persistence/history audit.
- backend/tests/fixtures/prepared_decision_sources.v1.json: separate new source pins.
- backend/scripts/profile_decision_performance.py: complete cProfile call/cost export.
- backend/scripts/benchmark_prepared_decision.py: stronger four-arm benchmark.
- docs/DECISION_SCORER_PERFORMANCE.md: this design, measurements/readiness audit.

Modified only supporting files:
- backend/tests/integration_source_guard.py: recognize separately pinned additions.
- docs/RECOMMENDATION_RULES.md: experimental optimization status/link.
- docs/REPORT_TRACEABILITY.md: requirement/performance/integration evidence.

Commands from backend, PowerShell:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 python -B -u scripts/profile_decision_performance.py --size 100 --arms A B C --output ../storage/verification/phase5f2e3c3a/profile.before.v1.json
uv run --no-project --python 3.12 python -B -u scripts/profile_decision_performance.py --size 100 --arms C D --output ../storage/verification/phase5f2e3c3a/profile.attempt.v1.json
uv run --no-project --python 3.12 python -B -u scripts/benchmark_prepared_decision.py --sizes 20 50 100 200 --heavy --pairs 6 --memory --output ../storage/verification/phase5f2e3c3a/paired.v1.json
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_prepared_decision_performance.py tests/test_compatibility_decision.py tests/test_compatibility_pair_cache.py tests/test_rule_based_compatibility.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

Use new storage filenames when reproducing; tools refuse existing/source outputs.
Run git diff --check from repository root. Profiling output and benchmarks are
ignored local verification artifacts; summary results are retained here.

Final results and retain/revert decision follow after the experiment completes.


## Completed paired measurements and retention

Raw completed report: storage/verification/phase5f2e3c3a/paired.v1.json.
All 120 timing arms (six four-arm rounds per workload) and 20 fresh-process memory
passes completed. C/D full-result records and pair-cache counters match in every
round; each arm repeats its own fingerprint across timing and memory passes.
All recorded source/config hashes match the final measured files.

| Garments | Complete candidates | A median seconds | B median seconds | C median seconds | D median seconds | Median paired C-to-D improvement |
|---|---:|---:|---:|---:|---:|---:|
| 20 | 198 | 0.023477 | 0.038880 | 0.059649 | 0.050116 | 7.398% |
| 50 | 2,430 | 0.230427 | 0.409549 | 0.585491 | 0.464470 | 21.048% |
| 100 | 17,710 | 1.167858 | 2.121709 | 3.021256 | 2.737445 | 8.988% |
| 200 | 134,820 | 9.068567 | 16.118048 | 22.974575 | 20.660803 | 9.527% |
| 200 heavy | 300,763 | 20.000739 | 35.817285 | 51.851930 | 46.656652 | 10.587% |

Paired improvement is median(100*(C_i-D_i)/C_i), not the ratio of medians.
Only C/D implement identical policy semantics. Different A/B scores, status and
winners are expected and are recorded rather than treated as equivalence failures.

| Garments | C range seconds | D range seconds | Individual paired improvements %, rounds 1-6 | D faster |
|---|---:|---:|---|---:|
| 20 | 0.050135-0.066308 | 0.045892-0.064089 | 3.347, 6.766, 15.479, 8.030, 23.334, 4.462 | 6/6 |
| 50 | 0.454698-0.725437 | 0.415421-0.608449 | 1.336, 21.643, 32.166, 20.453, 8.638, 22.817 | 6/6 |
| 100 | 2.961057-3.184555 | 2.679409-2.813447 | 4.985, 7.576, 15.411, 9.491, 15.667, 8.485 | 6/6 |
| 200 | 22.759378-23.684956 | 20.603168-21.187973 | 7.953, 12.991, 8.021, 9.659, 9.394, 11.922 | 6/6 |
| 200 heavy | 50.781112-53.703159 | 46.317429-48.897085 | 6.946, 5.002, 11.301, 11.780, 13.262, 9.873 | 6/6 |

The preliminary two-pair tool smoke at 20 garments is preserved separately in
smoke.v1.json: D was slower than C by approximately 6.65ms/7.8% and 13.94ms/20.3%.
It is not hidden or mixed into the final six-pair statistics. The final six-pair
20-garment experiment improved in every pair, including its first run. This shows
no consistent unacceptable small-case regression in the stronger final experiment,
not a universal performance guarantee. Host variability remains a limitation.

| Garments | A peak RSS bytes | B peak RSS bytes | C peak RSS bytes | D peak RSS bytes |
|---|---:|---:|---:|---:|
| 20 | 25,870,336 | 26,124,288 | 26,189,824 | 26,722,304 |
| 50 | 25,919,488 | 26,742,784 | 27,062,272 | 27,582,464 |
| 100 | 26,234,880 | 28,631,040 | 29,261,824 | 29,585,408 |
| 200 | 26,349,568 | 37,163,008 | 37,371,904 | 37,109,760 |
| 200 heavy | 26,402,816 | 41,050,112 | 41,336,832 | 41,517,056 |

These are separate single-process peak observations, including imports/input and
returned-score serialization, not repeated memory distributions. The lower D peak
at ordinary 200 garments is process variation, not proof that an additional cache
saves memory. Arithmetic entries are strictly capped at 256 and pair entries at
19,900; no memory is retained proportional to all generated candidate records.

| Garments | Pair visits | Unique pairs / misses | Hits | Hit rate | Evictions |
|---|---:|---:|---:|---:|---:|
| 20 | 452 | 100 | 352 | 77.876% | 0 |
| 50 | 6,425 | 625 | 5,800 | 90.272% | 0 |
| 100 | 49,700 | 2,500 | 47,200 | 94.970% | 0 |
| 200 | 390,800 | 10,000 | 380,800 | 97.441% | 0 |
| 200 heavy | 893,311 | 13,333 | 879,978 | 98.507% | 0 |

B/C/D pair-cache counters are identical at each workload. Size/high-water equal
unique-pair counts. Saturation/eviction correctness is separately tested. The new
arithmetic cache is not inserted into outcome diagnostics (which must match C).
At profiled 100 garments, its factory executes 44 times for 17,700 paired decisions;
this implies 17,656 arithmetic hits with maxsize 256 and no eviction in that run.
The directly observed profiler count is 44 factory calls; the hit count is derived,
not a returned benchmark counter. A 301-vector test forces arithmetic eviction
and verifies exact recomputation against the original policy.

| Garments | C minus B medians seconds | D minus B medians seconds | Median paired D-over-B overhead |
|---|---:|---:|---:|
| 20 | 0.020770 | 0.011236 | 29.826% |
| 50 | 0.175942 | 0.054921 | 21.038% |
| 100 | 0.899547 | 0.615737 | 28.431% |
| 200 | 6.856527 | 4.542755 | 28.951% |
| 200 heavy | 16.034645 | 10.839367 | 30.749% |

Differences of medians describe remaining incremental work; they are not additive
profiler costs or isolated causal estimates. Ordinary B sessions numerically score
N-D single dresses and refuse selection after complete enumeration, whereas C/D
score N and select. In the heavy case all three score 300,763 and select. Their
profile metadata still differs. No new HTTP/browser timing is inferred.

Retention decision: RETAIN both prepared constants and bounded arithmetic reuse
as one isolated correction. They were measured together, not claimed as separate
independent speedups. Correctness/isolation/metadata tests and all 30 matched C/D
comparisons agree; every final pair improves, memory remains bounded, and the
six-run small cases show no consistent material regression. The preliminary smoke
regressions and high-entropy-cache limitation remain disclosed. No other speculative
optimization was implemented or retained. The old C remains available unchanged.

Measured NFR-02 gap: ordinary D median 20.661s is 4.13 times the entire 5s budget
and exceeds it by 15.661s BEFORE HTTP/SQL/browser overhead. Heavy D median 46.657s
is 9.33 times the budget (41.657s over), explicitly a separate stress distribution.
Even A's ordinary 200 median 9.069s already exceeds the full budget. D at 100 is
2.737s, which leaves only a potential budget for other stages, not a compliant
full-response result. Real requests/preferences and deployment concurrency may
cost more. Performance acceptance remains blocked; do not redefine workload to
pass or claim the old 32.051s-to-current-20.661s difference as a paired speedup.

Readiness recommendation: PASS WITH LIMITATIONS for this isolated correction;
NOT ready for live activation or final NFR-02/FYP acceptance. Request a separately
approved performance architecture review and/or tightly scoped default-off
Assistant policy-selection plus decision-aware current/history DTO/display stage,
with activation gated on explicit performance and policy-quality review. No
production activation has been performed or scheduled automatically.


## Final verification and scope closure

- Focused final command: 733 passed, one existing TestClient deprecation warning,
  17.47s, exit 0. This includes 147 new tests plus 586 preserved decision/cache/
  raw-rule tests. Earlier development runs passed 137 and then 729 tests as the
  readiness and nonzero R/P cases were added; no application failure was hidden.
- Broad final command: 1,490 passed, 1 failed, one existing warning, 93.60s, exit 1.
  Sole failure is tests/test_report_architecture.py:28,
  ReportArchitectureTests.test_single_backend_and_canonical_ml_locations:
  assertFalse((ROOT / "ai-services").exists()). It is pre-existing; neither the
  folder nor the assertion was deleted or weakened.
- The warning is the existing FastAPI/Starlette httpx TestClient deprecation.
- tests/test_segmentation_geometry.py was explicitly excluded (cv2/torch not
  provisioned in this regression environment). Frontend/browser, deployed
  PostgreSQL, GPU/model quality and new live HTTP latency were not tested.
- Source integrity: all 177 pre-phase entries match SHA256, consisting of the
  original 157 application files, seven Phase 3A additions, three retained pair-
  cache files, five original Phase 3C-2 additions, and five frozen app archives.
  Original manifests and archives remain unchanged. The two prepared application
  additions have their own separate pins. All 176 benchmark source/config hashes
  match the measured files; no source change occurred during the final benchmark.
- git diff --check passed, exit 0. Existing LF/CRLF notices concern untouched
  recommendation_service.py and frontend/app/history/page.tsx. A separate scan
  of all ten phase files, including new/untracked files, found no trailing spaces.
- No live service selection, feature flag/default, persistence/schema, frontend,
  saving/visualisation, historical record, NLP, mandatory rule, R/P, suitability,
  approximate-hex, CV, VTOFF or VTON algorithm was modified. Existing database
  initialization/migration tests run only in disposable test databases; no
  deployment migration or data audit is claimed.

The prepared experiment is ready for review/closure as PASS WITH LIMITATIONS.
The retention decision does not authorize the proposed flag or integration changes.
Wait for user review before any further activation or architecture implementation.
