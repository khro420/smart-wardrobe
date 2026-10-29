# Phase 5F-2E-3J-6: exact scoring certificate reuse

2026-10-22. Targeted performance correction only. Final verification and clean sanity results are appended below. Compact/deferred remain production defaults; suitability remains opt-in, reference available, approximation disabled. No default activation, new architecture, model, schema, heuristic or formal NFR test is authorised here.

## Frozen pre-change authority and measured bottleneck

J-5 is owner-closed PASS WITH LIMITATIONS. Its immutable36-trial pre-change reference remains in phase5f2e3j5: experimental200 browser median6.069s/max6.103s, directHTTP5.952s/max6.015s; all six above5s. Deferred200 browser4.631s/max4.658s. The5s NFR-02 target is unchanged and the formal baseline remains unapproved. No previous result is replaced by a faster run.

Before changing production, all existing application/fixture/document sources were hash-recorded; prechange-app.zip and an exact compact_scoring_facts.before.py were captured. The new independent reference fixture copies that exact old file, pinned to its original compact_sources digest. Existing public Fraction oracles and fixed J-5 descriptor datasets remain unchanged.

Actual service cProfile sessions use the same balanced50/100/200 populations, vintage request,one blue-colour preference, both profiles, normal acquisition/persistence and compact execution. Existing kernel stage timers separately capture preparation, enumeration, mandatory, independent verification, scoring/validation, ranking and final reconstruction. cProfile supplies function/call CPU attribution; service timings capture lookup/NLP/ranking/persistence. Windows memory and separate tracemalloc runs capture allocation characteristics. **All profiling/trace timings are instrumented diagnostics, never clean browser/NFR measurements.**

| Size | Candidates | Deferred profiled wall/CPU | Experimental profiled wall/CPU | Experimental pair visits (miss/hit) |
|---|---:|---:|---:|---:|
|50 |2,430 |0.523/0.516s |0.674/0.641s |6,425 (625/5,800) |
|100 |17,710 |3.052/3.016s |3.678/3.562s |49,700 (2,500/47,200) |
|200 |134,820 |20.326/19.969s |27.706/26.703s |390,800 (10,000/380,800) |

At200: preparation0.063/0.062s,deferred/experimental scoring-validation11.393/18.076s,mandatory2.070/2.194s,independent2.279/2.432s,enumeration0.286/0.308s,ranking2.898/2.734s,reconstruction0.0011/0.0021s. Persistence was0.039/0.040s. Inclusive profiler function times must not be added to these stage totals. Experimental score() self time4.145s and cumulative17.745s; validate_total5.805s cumulative over134,820 calls, versus4.674s deferred. Fraction equality consumed3.902s cumulative, not solely compatibility. Pair() consumed1.333s cumulative; pair reuse was already effective,10,000 retained of19,900 maximum,zero evictions. This does not justify expanding pair caches or blaming persistence/UI. Most extra experimental cost is per-candidate exact scoring/certificate work and ordered compatibility handling, with repeated validation of already identical numeric outcomes, not repeated cold rule classification.

## One correction, bounded and semantics preserving

Only production compact_scoring_facts.py changes. Replace the existing256-entry total-only LRU with a256-entry **fully validated immutable CompactScore certificate** LRU. No cache capacity increase or extra unbounded cache. Existing request/preference/decision caches and19,900-pair bound remain. Capacity0 disables reuse,small bounds exercise eviction.

The complete cache key is `(ordered roles,request detail measures,preference detail measures,ordered atomic compatibility key)`. Every measure includes exact value,state,observed and possible counts. Ordered atoms encode exact numerator/denominator or None and retain every genuine relationship/dimension. Roles distinguish structures and ordering. Cache functions are created per immutable owner/garment/request/preference/policy/weights session; no global/user-shared cache. Hash collisions still require full tuple equality; no digest-only score match or float key is used.

For each candidate, enumeration, strict snapshot acquisition,primary mandatory evaluation,independent mandatory verification,R/P fact construction,all pair lookups,ordered atom construction and decision-certificate equality checks still occur. On a new complete key, the original exact Fraction weighted sum and unchanged validate_total run and produce the same CompactScore. Only an identical full key reuses that already validated immutable result. Every valid candidate still receives its exact score and participates in total/R/C/P/stable-role-ID ranking; no pruning,preselection,rounding,partial-stream publication or deferred fallback. Public winner reconstruction independently rebuilds original request/preference/compatibility evidence and metadata as before; candidates sharing numeric certificates do not share garment-ID provenance.

For keys k1=k2 in one immutable session: request detail tuples imply equal R/state/coverage; preference detail tuples plus fixed importance imply equal P/state/coverage; ordered atoms and roles imply equal rawC,L,U,midpoint,basis,pairs; fixed exact weights imply equal S. Thus the full immutable score is equal. Candidate identity is absent from the numeric certificate and remains in the unchanged structural/ranking/reconstruction paths. Public every-candidate audit equality verifies diagnostic reason/ID reconstruction, not just winner numbers.

An initial draft closure captured self, forming a reference cycle and delaying release of session snapshots. Separate allocation profiling exposed that retention; the draft and its raw results remain retained. The final closure captures only immutable values and cache functions, not its owning facts object. A weak-reference test requires immediate release without cyclic garbage collection, even while the numeric result is retained. Initial in-progress broad/focused runs were interrupted for this correction and are not reported as complete passes. This is a draft implementation correction within the same measured optimisation, not a policy change. The original before hash/reference remains unchanged; the first draft's source/manifest are separately retained.

## Differential and error verification

The new test loads the exact old facts implementation, then executes the unchanged kernel with old/corrected implementations over every candidate and compares both with existing public Fraction reference records. It covers the unchanged9+1 J-5 frozen cases,all four structures,ties,multiple styles/preferences,generic requests,known/unknown/empty evidence and NoPairReference. A separate5-state suitability matrix plus changed primary/style snapshots checks every mandatory outcome and full score/provenance. Bounded randomized4352-candidate cases at capacities0/1/256 compare every numeric certificate,all pair-visit counts,cache eviction and limits. Existing independent J-5 arithmetic/API tests run against corrected actual-confirmed wardrobes as well; frozen expectations are not edited to hide mismatches.

Late-stream failures,provisional-winner exceptions,source changes before persistence,atomic recommendation/chat/item rollback,concurrent submissions,idempotency,history,save/VIS,If-Match and style/null semantics remain required unchanged regressions. The kernel enumeration,independent verifier,scalar validators,ranker,public models,query,persistence and frontend application code are byte-identical to pre-phase sources. The source guard chains a new explicit before/after transition; no old manifest/archive is rewritten or assertion relaxed. The known ai-services architecture assertion remains separate.

## Verification boundaries

Profiling,cProfile,allocation and concurrent functional-test observations are labelled instrumented; their elapsed times are not acceptance values. Only the later production-Next/direct-HTTP36-call collector runs after these workloads finish and resource qualification passes. It reuses J-5 populations,requests/preferences,timeouts,collection boundary and gate,with a fresh label/output path. It additionally requires each size/profile's post-change fingerprint to equal the retained J-5 fingerprint. All slow/failed/first calls remain. No96-trial matrix or formal NFR population is automatically rerun.


## Completed final semantic checks

Final focused suite610 passed (187.99s). The standalone artifact-producing differential suite29 passed (8.94s). It records30 before/after/public-reference scenarios over88 complete candidate records:60 Pass,10 Fail,18 Unknown,including all four structures. All full-record SHA256 triplets agree; full records retain exact Fraction strings and diagnostic/provenance content. Three additional4,352-candidate numerical runs (capacities0/1/256) compare every score and12,544 pair visits per run and exercise eviction without exceeding bounds. The existing independent J-5 arithmetic/real-confirmation tests also pass in the focused suite. A new weak-reference assertion proves that retaining a returned score does not retain its owning session facts.

Final production browser four-way UI/history/profile suite28 passed (56.4s); final real-confirmed experimental+suitability journey1 passed (1.1m,38.7s test body). Earlier draft browser1 pass and interrupted draft-focused/broad logs remain retained, not substituted for final results. TypeScript,lint and isolated production build passed; lint has only the two unchanged navigation warnings. The final broad result and isolated profiling/clean latency remain separately recorded below.


## Final diagnostic and regression results

Final broad backend: **2,094 passed,1 unchanged ai-services architecture failure**,404.05s. Separate CV geometry remains excluded for its model environment. Final focused610 passes and artifact differential29 passes are complete. Four-way production browser28 and actual-confirmed experimental+suitability browser1 pass. No new application regression was reproduced. Initial draft interrupted runs remain retained,not complete passes.

Final cProfile200 experimental:19.779s elapsed/19.188s CPU versus pre-change27.706s/26.703s. Scoring/validation stage10.693s versus18.076s; independent134,820 verification calls remain. All390,800 pair visits remain,10,000 misses/380,800 hits/no evictions. validate_total executes4 times instead of134,820 for this homogeneous population:4 complete distinct structured numeric keys versus reuse on134,816 candidates. The same original validation code runs on every new key. This is an exact immutable-input certificate reuse,not omission of a candidate or mandatory verification. In a highly diverse workload,misses can be numerous; the LRU then evicts safely and reuse may be less beneficial. No latency improvement for arbitrary evidence distributions is inferred.

Allocation diagnostics (separate tracemalloc,not clean speed measurements): at50 Python traced peak1,088,495 ->1,099,983bytes; at200 3,455,267 ->3,456,531bytes (+1,264bytes). Retained current bytes at200 334,685 ->335,582. Initial draft retention3,317,695bytes is preserved and was removed by the no-self-capture closure. Windows post-request working set at20068,308,992 ->69,062,656bytes; process-lifetime peaks74,526,720 ->74,260,480bytes,not per-request peaks. These single observations demonstrate bounded tested memory,not a statistical memory guarantee. Tracemalloc elapsed actually increased38.729 ->48.813s at200; observer overhead and conditions differ and this result is not hidden or presented as a speedup. Clean browser/HTTP results are the required performance evidence,not profiler/trace elapsed times.

Inlined R/P fact-building and opaque LRU-hit overhead are grouped inside score() self/stage time; the profiler does not independently isolate every inline expression. Callback,exact-total,decision,pair,enumeration,mandatory,verification,reconstruction,persistence and cache counts are separately retained as far as practical. Inclusive callgraph times are not summed. Original J-5 HTTP/browser boundaries remain the pre-change transport baseline. No claim is made that all additional experimental cost is cold compatibility rule calculation.

## Current resource blocker and stage status

After all test/build/profile processes ended,a host sample at18:46:12+08:00 reported70% CPU,5.68GiB free physical RAM. A separate three-second process delta identified RobloxPlayerBeta14.39% machine CPU/2.51GiB RAM and ctfmon7.10% CPU,plus desktop activity. Observation windows differ; values are not added to the OS snapshot. No clean timed submissions were started. Owner workload relief was requested; applications are not terminated automatically. host-before-sanity.json is retained.

**Functional/differential correction verification PASS; clean post-change performance PENDING.** Therefore no before/after50/100/200 browser/HTTP medians or percentage speedup are fabricated. The new collector is prepared to run the same36 trials with a fresh J-6 output and exact J-5 fingerprint checks. All previous J-5 slow results remain unchanged. NFR-02 remains OPEN/NOT FORMALLY ACCEPTED;5s is unchanged.

**Current activation recommendation: DEFER until the controlled post-change sanity completes. J-6 is not yet ready for closure at this checkpoint.** The minimum next action is resource relief,recheck CPU/RAM/competing processes,and run only the prepared collector after qualification. Passing semantic suites need not be repeated without a new source change/failure. If experimental200 remains above5s,report it and seek separate direction; no second speculative optimisation/default switch is authorised. Even a successful sanity requires a separate activation decision and approved formal baseline before NFR acceptance. Suitability remains default-off,approximate hex disabled,reference/deferred rollback available. No additional phase begins.

## File inventory

| File | Purpose |
|---|---|
| backend/app/application/recommendation/compact_scoring_facts.py | Only production change: replace total-only bounded LRU with validated full numeric certificate LRU; avoid session reference cycle. |
| backend/scripts/profile_three_component.py | Reproducible instrumented actual-service cProfile/allocation driver; refuses existing output directories. |
| backend/tests/fixtures/score_certificate_reference/compact_scoring_facts.py | Byte-exact frozen pre-change implementation. |
| backend/tests/fixtures/score_certificate_sources.v1.json | New strict before/after source transition; original baselines untouched. |
| backend/tests/integration_source_guard.py | Chain the authorised transition while retaining every old archive/hash assertion. |
| backend/tests/test_score_certificate_reuse.py | Before/after/reference every-candidate checks,bounds,eviction,changed evidence,suitability and immediate session release. |
| frontend/tests/phase5f/score-certificate-performance.spec.ts | Same36-call collector with fresh evidence path and J-5 semantic fingerprint assertions. |
| frontend/playwright.score-certificate.config.ts | Isolated production build/server paths; existing functional browser suite reused. |
| docs/THREE_COMPONENT_PERFORMANCE_CORRECTION.md | This implementation,diagnostic and pending-performance report. |
| docs/REPORT_TRACEABILITY.md | Appended scoped current status. |

Raw profiles,full candidate equivalence records,SHA triplets,source backups/diff,initial draft/interrupted logs,resource samples,commands and integrity indexes are additionally retained in storage/verification/phase5f2e3j6. Historical J-5 raw data and all prior fixture/oracle files are unchanged. The original tsconfig is restored after checking generated include changes. No frontend application,persistence,query,scoring policy,independent verifier,NLP,CV/VTON,DB schema/provider,Homepage,legacy route or live default is changed. No production deployment or real-model acceptance is claimed.

Resource recheck18:50:18+08:00:59% CPU,5.66GiB free RAM; Roblox18.16% machine CPU and ctfmon7.75% in the separate3-second delta,with active AutoClicker. Owner pause confirmation has not arrived at this checkpoint. No clean trial is started or invented. All semantic/source/regression results are preserved; only resource-qualified post-change transport evidence remains outstanding.


## Owner-requested load recheck and first transport attempt: RESOURCE BLOCKED

At20:06 the owner asked to recheck. Available RAM was9.83-9.84GiB; CPU23%,26%,16%. Chrome PID13784 used14.45% machine CPU in the first separate delta,then0% in a follow-up and total CPU16%. The existing authorised collector was started with new label j6-initial and no changed gate/timeouts/source. It retained44 preflight observations:CPU17-76%,RAM8.84-8.99GiB,zero timed submissions. It correctly ended resource_blocked with one failed collector test,not an application latency failure. No new medians/maxima/speedups exist.

A process delta during preflight found OneDrive24.61% machine CPU and OneDrive.Sync.Service13.80%,now the dominant background work; Roblox was only1.76%. Owner was asked to pause syncing again. No process was terminated. Raw host-owner-recheck timestamped sample,preflight-competing-processes.json,performance-sanity-j6-initial.json,performance-initial.log,resource-blocked-initial-summary.json and browser trace are retained. Earlier Roblox/ctfmon resource observations and all completed semantic tests remain. The retry must use a fresh label/artifact directory after resource relief; no earlier file is overwritten. J-6 remains pending clean performance and no default is activated.


## Final resource-qualified retry and closure assessment (supersedes pending checkpoints)

Owner confirmed OneDrive syncing paused again. Fresh label `j6-quiet-retry` preserved the first blocked attempt. Existing preflight passed after 11 observations; qualifying final CPU samples were [11, 20, 16]. Preflight CPU ranged 11-63%, free RAM 8.95-8.99 GiB. Timed before/after observations ranged 1-54% CPU and 8.69-9.05 GiB free RAM. One CPU observation was unavailable (null); it is retained, not fabricated or treated as zero. These snapshots are not continuous process isolation. No test/build/profile work ran concurrently.

**Collector: 1 passed (3.9m), 36/36 HTTP 201, zero errors/timeouts, zero responses above five seconds.** Every retained J-5 semantic fingerprint matched. Candidate counts remain 2,430 / 17,710 / 134,820. Every request has a fresh submission key; no recommendation warm-up, timeout extension, truncation or policy change was used.

| Garments | Profile | Layer | All seconds | Median | Maximum | J-5 median | Median change |
|---|---|---|---|---:|---:|---:|---:|
| 50 | deferred | http | 0.094, 0.099, 0.087 | 0.094 | 0.099 | 0.146 | -35.3% |
| 50 | deferred | browser | 0.217, 0.163, 0.173 | 0.173 | 0.217 | 0.292 | -40.9% |
| 50 | experimental | http | 0.128, 0.116, 0.119 | 0.119 | 0.128 | 0.190 | -37.2% |
| 50 | experimental | browser | 0.203, 0.208, 0.224 | 0.208 | 0.224 | 0.254 | -18.1% |
| 100 | deferred | http | 0.563, 0.471, 0.455 | 0.471 | 0.563 | 0.623 | -24.4% |
| 100 | deferred | browser | 0.527, 0.582, 0.515 | 0.527 | 0.582 | 0.721 | -26.9% |
| 100 | experimental | http | 0.654, 0.680, 0.683 | 0.680 | 0.683 | 0.836 | -18.7% |
| 100 | experimental | browser | 0.787, 0.795, 0.729 | 0.787 | 0.795 | 0.950 | -17.1% |
| 200 | deferred | http | 3.185, 3.177, 3.242 | 3.185 | 3.242 | 4.549 | -30.0% |
| 200 | deferred | browser | 3.281, 3.363, 3.371 | 3.363 | 3.371 | 4.631 | -27.4% |
| 200 | experimental | http | 4.641, 4.812, 4.621 | 4.641 | 4.812 | 5.952 | -22.0% |
| 200 | experimental | browser | 4.710, 4.844, 4.964 | 4.844 | 4.964 | 6.069 | -20.2% |

These are matched workload/profile comparisons with retained J-5 transport observations, not simultaneous randomized machine-isolated experiments. Resource conditions differ; percentages describe observed changes, not a universal causal speedup. Instrumented stage/call counts and exact differential tests independently support the correction mechanism. Homogeneous evidence yields unusually strong certificate reuse; diverse evidence churn and concurrent users remain unverified. The experimental 200-garment browser maximum 4.964s leaves only about 36ms below five seconds. No claim of reliable deadline headroom or general scalability is made.

Exact final command (frontend; both execution/scoring selection variables unset):
```powershell
$env:SMART_WARDROBE_SCORING_SANITY='true'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='j6-quiet-retry'
npx playwright test --config playwright.score-certificate.config.ts --grep 'scoring acceptance browser and HTTP sanity' --output .next-integration-run/score-certificate-sanity-j6-quiet-retry-artifacts
```

Raw trials, resources, exact fingerprints and job CPU/memory/stage diagnostics are in `performance-sanity-j6-quiet-retry.json`; full log is `performance-quiet-retry.log`. `summarize-performance.py` reproducibly creates `performance-quiet-summary.json`. All previous slow J-5 trials, initial blocked J-6 collector, draft diagnostics and interrupted test runs remain retained.

**Phase J-6 is ready for owner review/closure as PASS WITH LIMITATIONS.** Exact semantics and regression verification are complete and the authorised transport comparison now completes. Technical evidence supports a separate bounded activation review; it does not authorise activation. Compact execution and compatibility_deferred remain defaults; suitability stays opt-in and approximate hex disabled. No second optimisation or later phase begins.

**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** Five seconds is unchanged. This homogeneous synthetic 36-call sanity is not the unapproved diverse formal baseline, real protected-image loading acceptance, deployment/concurrent load verification or independently reviewed fashion-quality evaluation. Earlier above-five-second results remain valid historical observations. Owner review is required before any scoring-default change.
