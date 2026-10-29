# Phase 5F-2E-3J-8: bounded suitability hot-path diagnosis and correction

**Final: verification complete with limitations; SUPERVISOR SCOPE DECISION REQUIRED. No release/default approval;NFR-02 formally unaccepted.** Initial checkpoints and final measurements are retained below. No activation is authorised. Execution remains compact_exhaustive,scoring compatibility_deferred,suitability default disabled,approximate hex disabled.200 garments remain a proposed capacity,not an approved formal baseline;five seconds is unchanged.

## Authority and diagnostic scope

Original Project I RN-13/RN-17,NFR-02 and sections4.4.3/4.10.4 remain authority for supported request filtering,three-component criteria,exact ranking and response-time requirement. The eight/two owner-declaration suitability policy,colour/Dice proxies,midpoint/no-pair convention and0.60/0.20/0.20 are approved implementation policies,not original numerical fashion requirements. J-7 is owner-closed PASS WITH LIMITATIONS and its release gate did not pass. J-6's exact full-score certificate cache remains intact.

Use byte-frozen J-7 varied200:80tops/80bottoms/20dresses/20outerwear,all13 categories,134,820 structures,three equal supported preferences. Same `Suggest a casual outfit for campus` request. The materialised synthetic distribution is unchanged and is not claimed to represent real user frequencies. Fixture-owner exact reserved Allow tags exist on every member,including outerwear;not independently reviewed human suitability judgments. No private/live DB or model pipeline is used.

## What the matched profiles actually compare

For each deferred/experimental profile:generic request with minimum evaluator;campus/casual with suitability evaluator;generic with suitability evaluator as enablement control;campus/casual with minimum evaluator as capability control. The last correctly returns PolicyUnavailable and enumerates nothing;it is not a comparable successful scoring baseline and its conditions are never stripped or ignored. The generic enabled control distinguishes enabling the evaluator from supplying suitability fields. Full cProfile,CPU/wall,service stages,cache ledgers and function call summaries are retained in profile-before/profile-after and profile-comparison.json. Instrumented elapsed values are not browser/NFR measurements.

Per-garment suitability parsing already occurs at preparation,independently for primary and verifier contexts. Full enabled-profile parser calls including winner/public checks:812deferred/808experimental,cumulative~13ms;state_for likewise812/808,less than1ms. Preparation~60/73ms. Therefore repeated parsing across134,820 candidates was **not** the bottleneck. Primary mandatory reduction and independent verification still cost seconds,but changing or bypassing those is not the correction selected.

The measured scoring loop reconstructs equal request detail objects for hard fields after mandatory Pass. For campus+casual,two new Fraction(1)/Measure details are built for each scored candidate,then compared through existing caches. The score loop alone invoked672,936 Fraction constructors before;269,640 of these are repeated hard-request details. Score-loop Fraction equality calls before were1,345,238deferred/1,827,932experimental. These include other scoring/key work;not all are attributed to suitability. Existing request summary has only1 miss and preference summary85;numeric full-score validation85deferred/11,480experimental. Cache effectiveness did not eliminate temporary input-object construction and equality work.

## The one conditional correction

Only `compact_scoring_facts.py` production source changes. Prepare an immutable request-detail template once per facts session,at most5 entries. Passed non-style fields have the identical existing numeric Measure(1,Available,1,1);style keeps a placeholder whose candidate-specific matched/known base-member fraction is computed every time. With no style,the whole template tuple is reused. With style,a short local copy fills only that position.

This caches **numeric request-match inputs**,not Allow/Deny/Unknown or mandatory Pass conclusions. Each candidate still undergoes the unchanged CompactMandatoryFacts evaluation and separately prepared CompactEligibilityVerifier before facts.score. Both primary/verifier source bytes are unchanged. No candidate is omitted,no winner-only shortcut and no per-garment declaration is inferred. A changed declaration/request/user starts its own immutable facts context and undergoes current checks. The existing authenticated owner,immutable snapshots,request,active preferences,policy/weights and captured evaluator scope remain session-bound. No fact crosses sessions/users. Public winner reconstruction and policy provenance still re-evaluate current captured inputs.

No new LRU/global cache is added. Existing256 certificate bound,19,900pair bound,full key equality,exact validate_total,all weights,request/category/colour/style/suitability semantics and all-member outerwear checks remain unchanged. Reference/deferred rollback,unsupported exercise/formal outcomes,atomic revalidation/commit,replay and history are untouched. An explicit new source transition chains from the unchanged J-6/J-7 digest;earlier fixtures/hashes are not rewritten.

## Differential and regression evidence so far

538 focused tests pass,74.19s. New matrix:all10values x6evidence states(Allow/Deny/absent/malformed/conflict/mixed Deny+Unknown) xsingle/five-field requests x2profiles=240cases. All four structures,missing/empty/known/multiple style evidence and known/missing colours participate. Candidate conditions,masks/reasons,complete scores and final winners match frozen J-7 and unchanged public Fraction oracle,including reversed input order. Fresh sessions after declaration changes and unsupported exercise/formal are checked. Existing integration tests cover in-flight configuration capture,cross-user eligibility,atomic writes,same-key historical replay,complete-stream failures and bounded caches.

Full varied200 comparison across scoped4cases:539,280structural examinations,462,252mandatory-valid exact score comparisons;all scores,winners and complete cache ledgers match. Suitability deferred/experimental and generic experimental score134,820 each;style scores57,792. Primary/independent remain unchanged and execute on every applicable candidate. Full outputs in full-equivalence.json.

## Bounded transport plan and retained resource history

Frozen collection-plan.json:four200-garment cells(suitability deferred/experimental,style experimental,generic experimental),one HTTP plus3browser submissions per cell=16per arm. Four corrected terminal browser checks after correction bring total planned transport submissions to36,not a new architecture matrix. First requests included,existing timeouts/proxy/preflight unchanged,no warm-up. Login/page setup outside submission boundary;visible card/message completion does not certify real protected thumbnail loading.

Initial unchanged-code before attempt was resource_blocked,zero submissions. CPU60-67%;process delta Roblox27.99%,OneDrive.Sync.Service17.84%,ctfmon6.12% machine CPU. Owner reported workloads paused. A fresh snapshot then showed20%CPU with residual OneDrive/Discord work;bounded preflight was used unchanged. Fresh `j8-before-retry` passed13/14/17% CPU and completed16/16 correct requests. Both attempts are retained.

To avoid flipping production files after the conditional correction,a disposable J8 server uses the byte-exact J-7 numeric-facts module for the before arm,with its SHA asserted. All surrounding actual authenticated integrated application/query/persistence/frontend code is current and unchanged. After arm uses the actual corrected production facts. This test-only frozen injection is not a production engine/profile selector or modified oracle. All16 before requests persisted successfully and stable fingerprints are retained for after comparisons.

Formal baseline still needs owner/supervisor approval of200capacity,bounded suitability scope,final scoring profile,real DB/deployment environment,representative evidence distribution,concurrency and terminal/browser/image completion boundary. The runnable DB here is SQLite,not proof of PostgreSQL. No formal NFR-02 acceptance or deployment claim follows from this collection. No additional optimisation is authorised if this one fails to provide adequate deadline margin.

## Profile and allocation results (instrumented,not clean latency)

| Arm/profile/request/evaluator | Outcome | Wall / CPU s | Preparation | Mandatory | Independent | Scoring/validation | Ranking | Persistence |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| before / deferred / generic / disabled | Selected | 12.197 / 11.984 | 0.046 | 0.671 | 1.256 | 6.991 | 1.799 | 0.048 |
| before / deferred / suitability / enabled | Selected | 18.746 / 18.375 | 0.060 | 3.033 | 2.775 | 9.655 | 1.691 | 0.058 |
| before / deferred / generic / enabled | Selected | 12.500 / 12.266 | 0.057 | 0.680 | 1.284 | 7.178 | 1.848 | 0.046 |
| before / deferred / suitability / disabled | PolicyUnavailable | 0.006 / 0.016 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| before / experimental / generic / disabled | Selected | 19.399 / 19.016 | 0.064 | 0.750 | 1.395 | 13.526 | 1.774 | 0.045 |
| before / experimental / suitability / enabled | Selected | 28.444 / 27.406 | 0.073 | 3.500 | 3.202 | 17.833 | 1.663 | 0.054 |
| before / experimental / generic / enabled | Selected | 20.522 / 19.766 | 0.072 | 0.788 | 1.472 | 14.315 | 1.879 | 0.047 |
| before / experimental / suitability / disabled | PolicyUnavailable | 0.026 / 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| after / deferred / generic / disabled | Selected | 9.609 / 9.422 | 0.033 | 0.532 | 0.975 | 5.507 | 1.423 | 0.042 |
| after / deferred / suitability / enabled | Selected | 13.651 / 13.234 | 0.045 | 2.511 | 2.253 | 6.242 | 1.372 | 0.037 |
| after / deferred / generic / enabled | Selected | 10.316 / 9.844 | 0.033 | 0.569 | 1.055 | 5.908 | 1.564 | 0.035 |
| after / deferred / suitability / disabled | PolicyUnavailable | 0.006 / 0.016 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| after / experimental / generic / disabled | Selected | 15.355 / 14.516 | 0.045 | 0.597 | 1.106 | 10.701 | 1.413 | 0.036 |
| after / experimental / suitability / enabled | Selected | 19.242 / 18.672 | 0.055 | 2.604 | 2.361 | 11.439 | 1.219 | 0.035 |
| after / experimental / generic / enabled | Selected | 14.903 / 14.641 | 0.041 | 0.585 | 1.065 | 10.402 | 1.365 | 0.035 |
| after / experimental / suitability / disabled | PolicyUnavailable | 0.006 / 0.016 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

For full enabled200 cases,all134,820 candidates remain structural/mandatory-valid/scored. Independent verification calls134,820 per case,unchanged. Numeric validate_total calls85deferred/11,480experimental,unchanged. The exact primary/verifier source bytes are unchanged. Disabled campus/casual rows return PolicyUnavailable before acquisition;zero stage columns here mean not executed,not successful zero-cost fulfilment.

Score-loop Fraction constructor counts672,936->403,296 in each suitability profile,exactly269,640 fewer. Fraction equality calls1,345,238->806,130deferred and1,827,932->1,311,614experimental. Request summary misses1,preference summary85,and full-score cache ledger remain unchanged. Raw compatibility pair visits390,800,hits380,800,misses10,000,evictions0;full-score hits123,340/misses11,480/evictions11,224,capacity256. Deferred hits134,735/misses85/no evictions. No approximate arithmetic or eligibility shortcut caused these changes.

Before/after stage wall reductions cannot all be attributed to the patch:unchanged mandatory/independent stages also timed faster,showing resource/frequency/profiler variation. Call counts,byte comparisons and exact differential records establish the redundant work removed. cProfile elapsed is not a speed acceptance result;inclusive function times must not be summed.

| Allocation arm/profile | Traced current bytes | Traced peak bytes | Instrumented wall s |
|---|---:|---:|---:|
| frozen / deferred | 696811 | 1024002 | 31.403 |
| frozen / experimental | 815370 | 4395005 | 66.390 |
| corrected / deferred | 348498 | 613761 | 42.215 |
| corrected / experimental | 389849 | 3891348 | 59.354 |

Single-process sequential tracemalloc observations include cold/warm effects and are not a statistical memory or speed guarantee. Windows working-set/lifetime peak values and each bounded-cache ledger are retained in allocation.json. The correction adds only a fixed tuple of at most5 numeric details and a style position,no additional LRU or candidate collection. Existing immediate-release tests pass.

Broad backend regression:2,361passed,1unchanged failure in test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations,352.25s. The separate geometry suite remains excluded for its CV/torch environment. No test assertion or directory was weakened/deleted. TypeScript and scoped ESLint final checks exit0. No production frontend change or new build was needed;the identical J-6 production build is reused.

## Final bounded transport evidence

The corrected initial collector was also resource_blocked,zero submissions. A retained3-second process delta showed OneDrive.Sync.Service20.44%,OneDrive15.95%,Explorer7.55% machine CPU. After the owner requested a recheck,CPU13%,free RAM7.67GiB were observed,with residual OneDrive activity11% in a separate window. No applications were terminated. Fresh label `j8-after-retry` then passed unchanged preflight at19/20/11% CPU and completed20requests. Both zero-submission failures remain alongside successful runs;no label/output was reused.

| Arm / case | Profile | Layer | All seconds | Median | Maximum | Service seconds |
|---|---|---|---|---:|---:|---|
| before / suitability | deferred | http | 4.807 | 4.807 | 4.807 | 4.799 |
| before / suitability | deferred | browser | 4.762, 4.667, 4.607 | 4.667 | 4.762 | 4.631, 4.555, 4.533 |
| before / suitability | experimental | http | 6.546 | 6.546 | 6.546 | 6.540 |
| before / suitability | experimental | browser | 6.826, 6.884, 6.556 | 6.826 | 6.884 | 6.746, 6.781, 6.483 |
| before / style | experimental | http | 2.893 | 2.893 | 2.893 | 2.888 |
| before / style | experimental | browser | 3.060, 3.269, 2.984 | 3.060 | 3.269 | 2.979, 3.201, 2.899 |
| before / generic | experimental | http | 4.687 | 4.687 | 4.687 | 4.681 |
| before / generic | experimental | browser | 4.990, 4.843, 4.782 | 4.843 | 4.990 | 4.895, 4.755, 4.711 |
| after / suitability | deferred | http | 5.865 | 5.865 | 5.865 | 5.854 |
| after / suitability | deferred | browser | 6.316, 6.800, 5.892 | 6.316 | 6.800 | 6.189, 6.716, 5.797 |
| after / suitability | experimental | http | 8.988 | 8.988 | 8.988 | 8.979 |
| after / suitability | experimental | browser | 7.350, 6.304, 6.629 | 6.629 | 7.350 | 7.261, 6.223, 6.535 |
| after / style | experimental | http | 3.037 | 3.037 | 3.037 | 3.031 |
| after / style | experimental | browser | 3.020, 3.083, 3.037 | 3.037 | 3.083 | 2.950, 3.019, 2.949 |
| after / generic | experimental | http | 4.766 | 4.766 | 4.766 | 4.760 |
| after / generic | experimental | browser | 4.678, 4.744, 4.754 | 4.744 | 4.754 | 4.601, 4.678, 4.676 |
| after / no_result | deferred | browser | 0.095 | 0.095 | 0.095 | 0.021 |
| after / no_result | experimental | browser | 0.106 | 0.106 | 0.106 | 0.050 |
| after / unsupported | deferred | browser | 0.078 | 0.078 | 0.078 | 0.002 |
| after / unsupported | experimental | browser | 0.067 | 0.067 | 0.067 | 0.001 |

**Before:**1collector passed2.9m,16/16correct HTTP201 submissions,zero errors;4experimental suitability observations above5s. **Corrected:**1collector passed3.1m,16/16correct HTTP201 recommendations plus4correct terminal browser outcomes;zero errors,8suitability observations above5s. All repeated/cross-arm winner,exact-score and semantic-provenance fingerprints match. Fresh keys and32distinct recommendations/chats were retained across the two disposable runs. Terminal checks create no recommendation/chat IDs.

Before preflight8samples:CPU4-33%,RAM9.14-9.19GiB;timed snapshots9-39%,RAM8.97-9.19GiB. Corrected preflight3samples:CPU11-20%,RAM7.12-7.13GiB;timed snapshots3-57%,RAM6.91-7.12GiB. These are preflight-qualified sequential collections,not continuous isolation or randomised interleaved experiments. Memory/background conditions differ. No tests,builds,profilers or allocation runs overlap either collection. Sampled current CPU load alone cannot establish equal effective per-core frequency or thermal conditions.

The correction demonstrably removes redundant work and preserves exact semantics,**but these transport observations do not demonstrate reliable end-to-end improvement**. Deferred suitability browser median4.667->6.316s is slower;experimental6.826->6.629s has a small median reduction but maximum6.884->7.350s is worse,and HTTP6.546->8.988s is slower. Do not report a universal speedup or dismiss the slower rows as proven environment-only effects. No causal performance regression or precise machine cause is established by these sequential samples. The post-collection Balanced power-plan/nominal3201MHz/battery snapshot is retained,but no comparable before/effective-frequency/thermal series exists;it cannot explain away results.

Style/generic controls:experimental browser medians3.060->3.037s and4.843->4.744s,maxima3.269->3.083s and4.990->4.754s. These controls show no observed slowdown in these small samples;they do not certify arbitrary wardrobes or exclude request-specific performance risk. Original J-7 style5.208s and suitability6.344/6.686deferred,9.169/9.865experimental remain unchanged and cannot be retroactively passed by later observations.

## Corrected terminal browser timing

Exact same existing app alert is selected while excluding Next route announcer. The corrected qualified run measured NoEligibleGarments:0.095sdeferred/0.106sexperimental;UnsupportedRequest:0.078sdeferred/0.067sexperimental. Correct API outcomes/statuses(200/422),visible application message and no persisted recommendation/chat are checked. These are one observation per profile/outcome,not formal deadline acceptance. The failed J-7 0.08-0.12s locator attempts are not reused as successful timings;J-7 blocked retry and separate functional proof remain retained. No production frontend logic changed.

## Stopping decision and acceptance boundary

**Recommendation: SUPERVISOR SCOPE DECISION REQUIRED.** The one authorised correction has an exact semantic proof and reduced measured redundant operations,but corrected200-garment suitability HTTP/browser requests still exceed5s with no defensible measured margin. J-8 does not establish the scoring-default release gate or enable global suitability. No second correction,larger cache,pruning,approximate score,timeout increase,workload reduction or J-9 is started. This is a stopping/escalation decision,not a claim that200is mathematically impossible or that measured failures may be relabelled as stress.

**NFR-02 stays OPEN / NOT FORMALLY ACCEPTED.** Original5s unchanged,200capacity not yet approved formal baseline. Owner/supervisor must decide200capacity,supported8-occasion/2-formality scope versus report commitments,final three-component profile,database/deployment target,actual/synthetic distribution acceptance,concurrency,and terminal/browser completion including protected images. Only after those explicit decisions can a formal plan be frozen. SQLite here does not certify PostgreSQL locking or deployed workers;synthetic media does not certify real image-loading/GPU quality. A passing terminal check or generic median does not certify suitability performance.

Minimum next action is the owner/supervisor release/acceptance scope decision using these results. Further engineering work would need a separately bounded approval and a reason it can close the chosen acceptance gap;another similar optimisation phase is not automatically recommended. Retain compatibility_deferred,compact_exhaustive,suitability disabled,approximate hex disabled and reference rollback. The J-6 full-score certificate optimisation remains present. J-8 source correction is submitted for review with mixed/insufficient transport benefit,not described as an accepted deployment speedup.

## Final verification and file inventory

Focused538passed(74.19s);broad2,361passed plus the unchanged ai-services assertion(352.25s);full-size462,252exact scores across539,280structural examinations;before16and corrected20actual requests all correct;TypeScript/scoped ESLint exit0;git diff --check exit0. No new functional regression was reproduced. Transport timings are mixed/slower as disclosed;do not conflate functional correctness with performance readiness.

| Created/modified file | Purpose |
|---|---|
| backend/app/application/recommendation/compact_scoring_facts.py | Only production change:immutable per-session request numeric-detail template. |
| backend/scripts/profile_suitability_hot_path.py | New actual-service matched diagnostic/cProfile driver. |
| backend/tests/fixtures/invariant_request_reference/compact_scoring_facts.py | New byte-frozen J-7 facts;SHA612bf357... verified,not modified oracle. |
| backend/tests/fixtures/invariant_request_sources.v1.json | New narrow before/after transition;all previous manifests untouched. |
| backend/tests/integration_source_guard.py | Chain the exact authorised transition without weakening old source checks. |
| backend/tests/test_invariant_request_details.py | New240-case matrix plus policy-unavailable/fresh-declaration tests. |
| backend/tests/suitability_hot_path_server.py | New disposable baseline-only frozen-facts injection;actual corrected facts otherwise. |
| frontend/tests/phase5f/suitability-hot-path.spec.ts | New bounded paired collector,cross-arm fingerprint proof and corrected terminal locator. |
| frontend/playwright.suitability-hot-path.config.ts | New production-browser fixture configuration;J-6 build reused. |
| docs/SUITABILITY_HOT_PATH_DIAGNOSIS.md | This diagnosis,correction,measurement and stopping report. |
| docs/REPORT_TRACEABILITY.md | Append-only J-8 traceability. |

All11deliverables are hash-indexed in deliverables.json;additional raw scripts,profiles,JSON,logs,backups,diffs and resource samples are indexed in storage/verification/phase5f2e3j8/evidence-index.json. Exact commands are in commands.txt. Browser artifacts are separately retained under frontend/.next-integration-run/suitability-hot-path-{before,before-retry,after,after-retry}-artifacts. Existing frontend app/build inputs,eligibility/verifier,public scoring rules,style/null/If-Match,saved-outfit validation,Homepage,legacy routes,CV/VTON,DB provider/schema and historical records are unchanged. No real deployment restart or formal NFR trial is claimed.

**J-8 is complete for owner review with the stated limitations;release readiness is not achieved.** Wait for owner review before any further phase or default change.
