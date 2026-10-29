# Phase 5F-1 verification and performance diagnosis

This is a verification record, not a declaration of FYP completion. The original
Project I report remains authoritative. Requirement-by-requirement findings are
in `PHASE_5F_REQUIREMENTS_AUDIT.md`. No production recommendation, UI, database
schema, saving, CV or VTON algorithms are changed here. New files are verification
fixtures/tests, latency/statistics tooling and these audit documents; existing
Playwright configuration only separates long diagnosis tests from normal tests.

## Environment and measurement method

Windows x64, AMD Ryzen 5 7235HS (4 cores/8 logical processors), 21,144,231,936
bytes physical RAM (~19.69 GiB); Node 24.19.0, npm 11.17.0, Python 3.12. Next
16.2.9 production build, Chromium via installed Playwright 1.64.1; actual FastAPI
Uvicorn localhost TCP server and disposable SQLite. See generated
`storage/verification/phase5f/environment.json` for OS version, git HEAD and time.
Git has existing uncommitted Phase 1–5E changes, so HEAD alone is not a source
identity. Hashes of relevant source/configuration files accompany final evidence.
Resolved workload environment: Python 3.12.10, FastAPI 0.143.3, Uvicorn 0.54.0,
Pillow 13.0.0, NumPy 2.5.4 and python-multipart 0.0.32. The recorded uv commands
resolve their requested packages; use these archived versions when reproducing
later rather than assuming future resolution produces the same environment.

Flags: Homepage/Assistant true, suitability false, development identity false,
test-only secret, AI development, VTOFF off. The isolated server explicitly sets
its temporary data directory before importing application code. No deployment
database is opened. Approximate hex and holistic scoring remain disabled.

Baseline: one sequential client, one backend worker; no concurrent build,
regression or profiler workload during the accepted measurement run. Normal OS,
OneDrive and desktop activity are not controlled. Loopback is not WAN/mobile
latency. Each size has synthetic **pre-confirmed** garments: 40% tops, 40% bottoms,
10% dresses, remaining outerwear; blue primary colour, vintage style, no stored
preferences. All pass the supplied vintage request, deliberately exercising the
full scoring stream. No saved outfits are seeded or needed. Counts:

| Garments | Tops/bottoms/dresses/outerwear | Complete candidates |
| --- | --- | --- |
| 20 | 8 / 8 / 2 / 2 | 198 |
| 50 | 20 / 20 / 5 / 5 | 2,430 |
| 100 | 40 / 40 / 10 / 10 | 17,710 |
| 200 | 80 / 80 / 20 / 20 | 134,820 |

Expected count is `(tops * bottoms + dresses) * (1 + outerwear)`. Every successful
Assistant HTTP trial asserts the persisted scored count equals this independent
formula. Each request uses a new key, so idempotent cache/replay is not timed as
generation. No cap, shortcut, provisional winner or truncation is introduced.

History baseline: 1,000 seeded completed legacy records per size-user (4,000
total), with 100 matching the literal `campus` query and limit 50. Additional
measured successful interactions have vintage text without campus, so matching
count stays 100; total database history grows slightly during the run. Historical
legacy fixture records are search data, not evidence of valid new outfit
generation. This is a proposed experiment workload, not an approved final maximum
history workload for NFR-03. Functional audits also have a separate one-dress user.

For each size/operation: one excluded warm-up, 20 raw HTTP trials and five browser
trials. Conventional median averages the middle two for even n. Empirical p95 is
nearest-rank for n=20 only; this is a noisy descriptive estimate, not a confident
population tail guarantee. Five browser trials report median/range only. Warm-ups
and startup/build/fixture seeding are excluded. Baseline has no cProfile or
per-candidate diagnostic wrappers; existing production stage timers remain intact.

Browser Homepage starts timing after `page.goto(..., waitUntil='load')` completes,
matching the report's post-load wording. Assistant starts at submit click and
includes capability discovery; History starts at search click. Visibility is
Playwright's observable element visibility, not paint instrumentation. Separate
response-to-visible observations include automation/polling overhead and are not
pure React CPU times. Images deliberately reference synthetic missing media, so
these timings do not measure real garment-image downloading or CV/VTON.

## Executed NFR latency observations

Seconds; browser columns are median [min, max], five measured trials per cell.

| Garments | Homepage after page load | Assistant click → selected display | History search click → results |
| --- | --- | --- | --- |
| 20 | 0.095 [0.092, 0.134] | 0.170 [0.152, 0.192] | 0.109 [0.096, 0.131] |
| 50 | 0.154 [0.144, 0.312] | 0.537 [0.487, 0.596] | 0.112 [0.103, 0.179] |
| 100 | 0.467 [0.445, 0.533] | 3.090 [3.010, 3.939] | 0.115 [0.105, 0.138] |
| 200 | 2.632 [2.583, 2.809] | 21.710 [21.565, 24.677] | 0.112 [0.087, 0.130] |

Real HTTP API seconds; 20 measured trials per cell, median / empirical p95
[min, max]. These are not browser paint times.

| Garments | Homepage | Assistant | History search |
| --- | --- | --- | --- |
| 20 | 0.029 / 0.045 [0.024,0.048] | 0.074 / 0.103 [0.064,0.116] | 0.019 / 0.021 [0.015,0.022] |
| 50 | 0.089 / 0.105 [0.078,0.107] | 0.539 / 0.649 [0.439,0.668] | 0.020 / 0.026 [0.014,0.033] |
| 100 | 0.387 / 0.430 [0.340,0.438] | 2.974 / 3.131 [2.853,3.353] | 0.018 / 0.020 [0.016,0.023] |
| 200 | 2.669 / 3.333 [2.487,3.399] | 21.823 / 24.252 [21.109,26.698] | 0.017 / 0.020 [0.014,0.023] |

Assessment against the actual report:

- **NFR-01: observed browser sample PASS at all four sizes**, maximum observed
  post-load display 2.809s at 200. Only five browser observations per size and
  warm cached production assets: not enough for a robust deployment guarantee.
  HTTP p95 at 200 exceeds 3s; that is a risk indicator, not a replacement for the
  report's post-page-load display measurement or an invented percentile threshold.
- **NFR-02: FAIL at 200**, even the minimum HTTP/browser trial is >21s. The 20,
  50 and 100 garment samples passed the 5s requirement. This reproduces the earlier
  22.531s instrumented concern without a per-candidate profiler: it is not mainly
  instrumentation overhead. About 4.36x speedup is needed from the 21.823s HTTP
  median to 5s, with greater headroom required for variation.
- **NFR-03: observed baseline PASS**, all searches below 2s. **Final acceptance
  unverified** because the approved maximum-history workload has not been supplied.
  The workload is 1,000 personal/3,000 other-user seeded chats, not “200 chats”
  merely because the garment count is 200.

Raw samples: `storage/verification/phase5f/latency.json`. There are 320 HTTP
observations (including authenticated capability baseline) and 60 browser
observations, plus 28 excluded warm-ups. Baseline run passed the exhaustive
correctness assertions in 13.5 minutes (13.6 minutes harness total). A passing
benchmark test means the run completed correctly, **not that all NFRs passed**.
`summarize_phase5f.py` recomputes conventional medians/nearest-rank p95 from raw
samples; no samples are changed. Early exploratory trials concurrent with
regression checks were discarded and a fresh isolated run replaced the artifact.

## Original-report versus implementation limits

Report §4.10.4 calls for R/C/P scoring on valid candidates and the tie order total,
R, C, P, stable identifier. Live Assistant does preserve the arithmetic and tie
order but uses the approved compatibility-deferred profile: weights 0.70/0/0.30,
C NULL/Unavailable, not perfect compatibility. Therefore RN-17 is partial.
`compatibility_references.v1.json` contains zero references and
`activation_approved=false`; independent fashion-quality validation is unavailable.
The Oklab prototype file is explicitly unreviewed and mandatory evidence disabled.
Suitability is all-constituent owner declaration, separately opt-in; exercise and
formal remain PolicyUnavailable. Style/category cannot prove occasion suitability.

The 120-case NLP benchmark is synthetic and frozen separately from development
examples, not independently collected real-user labels. Its arithmetic accuracy
can be reproduced; no independent relevance/compatibility accuracy is claimed.
The requirement audit specifies the minimum additional review protocol proposed
for academic reporting without inventing new report acceptance thresholds.

Reproducible synthetic arithmetic checks are separate from relevance: a supported
vintage-only request with every base garment vintage has R=1, no stored
preferences P=NoPreferences (zero contribution), C unavailable, so S=0.70. With
no supplied fields, R=NotApplicable; a candidate matching an explicit stored red
preference has P=1 and S=0.30, while an unmatched candidate has S=0. A generic
request without preferences gives all candidates S=0 and the stable tie key
selects one; this is not measured aesthetic or personalised relevance. Existing
`test_independent_ranking_calculation_and_generic_ties` executes these exact cases.
The ordinary request "blue top and black trousers" remains conservatively
unsupported because the approved five-field schema cannot retain those bindings.

## Confirmed integration/data issues

1. **High: normal onboarding blocked.**
   `frontend/app/extract/results/page.tsx:55` always includes neckline and
   sleeve_length keys, even for lower-body garments where values are null.
   `backend/app/domain/value_objects/requests.py` ReviewItem permits only fit,
   style, material, custom_tags, color_temperature and is_dominant in attributes.
   Existing tests reproduce 422 review → 409 confirmation and success after
   removing the two unsupported keys. The teammate has not corrected the source.
   The normal upload → review → confirmation → recommendation browser journey is
   **BLOCKED**. Development-mode processing and pre-confirmed fixtures cannot prove
   successful production CV/onboarding.

   Minimum teammate correction: omit both unsupported keys from the attributes
   payload. Existing descriptive custom tags can remain; do not expand the backend
   schema/processing model without separate agreement. Regression: exercise the
   actual browser accept submission for upper and lower categories (including null
   values), require review 200, then confirmation 201, then strict-query inclusion;
   retain negative API tests for genuinely unsupported attributes.

2. **High: recommendation-source action eligibility gap.**
   `recommendation_service.py:validated_recommendation_items/_items` checks user
   and available status but not strict processing confirmation/job owner.
   `outfit_identifier_validator.py:45` accepts accepted processing rows, unlinked
   records and confirmed rows from a foreign processing job. Diagnostic
   `test_phase5f_audit.py` reproduces acceptance despite the Phase 1 query excluding
   the record. Only media resolution is stubbed for that source test; no VTON
   generation is performed. Saving uses actual SQLite. Passing these diagnostic
   tests means the gap was reproduced, NOT that the behaviour is safe.

   Coordinate strict revalidation in the recommendation-source save/prepare
   transaction, preserving unrelated outfit-source behaviour. Do not hold a
   transaction across VTON. Also reconcile save's mutation to `status='saved'`
   with report §4.8.2's unchanged Recommendation semantics. No fix is applied.

3. **Medium: full historical diagnostics are not shown.** History API restores
   request, interpretation, scores, score metadata and provenance; executed tests
   compare them and ensure no NLP/ranking rerun. CompletedChatView displays the
   request, interpretation and garments; RecommendationResult only adds the
   compatibility-deferred notice. It does not display full scores/policy provenance.
   This is a gap against the Phase 5F requested walkthrough, not proof that the
   original FR-CH-13 explicitly required a technical provenance panel. Read-only
   historical save/visualise actions also remain intentionally withheld pending
   strict-action coordination.

4. **Low: context-specific error wording.** `recommendation-messages.ts` maps every
   InvalidInput to an outfit-request instruction, including history InvalidInput
   (for example a cursor rejected after secret rotation). Backend preserves 422
   and detail, but frontend wording is misleading. A later targeted fix should
   retain context/backend detail and reset invalid pagination safely.

5. **Existing architecture assertion:** `test_report_architecture.py:28` asserts
   `ai-services` does not exist. The existing directory is present. This assertion
   is separate from candidate architecture and no folder/test is removed to turn
   the suite green.

6. **Medium data-quality coordination: cleared style loses missing state.** An
   actual wardrobe PATCH with `attributes.style=null` is written by
   `wardrobe_service.py:_write_representation` as `style_tags=[]` through
   `json.dumps(styles or [])`. Phase 1 faithfully projects the known empty list;
   the request evaluator therefore returns definite NoMatchingCandidates for a
   vintage request, rather than InsufficientEvidence for missing style. The snapshot
   cannot reconstruct the lost upstream distinction. The browser diagnostic first
   exposed this expectation mismatch; it now records the actual behavior and uses
   a cleared primary colour to exercise genuine Unknown/InsufficientEvidence.
   No teammate code is changed. Agree whether clearing style means unknown or
   intentionally no tags before modifying normalization or eligibility semantics.

   Separately, CV's empty-pixel black fallback remains indistinguishable from real
   black primary colour. Confirmation alone does not prove successful extraction;
   this requires cross-module provenance/data-quality work, not a Recommendation
   inference or a new unapproved prediction.

## Security, persistence and API compatibility

- New recommendation write uses `BEGIN IMMEDIATE`, user/operation/key uniqueness,
  fingerprint, strict transaction-bound selected-snapshot comparison, item/display
  snapshot/metadata insertion, and final commit. Any BaseException rolls back.
  Actual independent SQLite connections test same-key retries, differing payloads,
  lock contention, stage rollback and changed garment evidence. Ranking is outside
  the transaction. Preference snapshot is captured at ranking read, not refreshed
  at commit; this is explicit provenance, not an atomic preference edit guarantee.
- Historical items survive archival and are never silently regenerated. Protected
  media is owner/status checked; foreign/unavailable historical media is suppressed.
  Existing tests cover archived/missing/foreign records and actual media ownership.
- History SQL uses read-only SQLite and coherent owner-bound joins. Cursor HMAC
  binds user/search and pagination anchor; invalid/tampered/cross-search/cross-user
  cursors reject. Default cursor signing uses TOKEN_SECRET. Production must set
  environment=production and a strong private secret; the code rejects the known
  development default only in that mode. Secret rotation invalidates existing
  tokens and cursors. No separate cursor expiry/secret policy is implemented.
- Phase 5E's explicit `?pipeline=integrated` guard returns 404 IntegrationDisabled
  and never calls the placeholder. Capability discovery is authenticated/read-only.
  **Unqualified** POST intentionally keeps the prior default-off legacy fallback
  for backward compatibility. This is not a global removal of unsafe legacy
  selection; new UI always selects integrated mode. Earlier Phase 5C unqualified
  disabled behaviour is retained; the additive guard is the deliberate contract
  extension. Tests exercise both paths.
- Legacy history without snapshots/structured metadata has explicit unavailable
  details; saved legacy Assistant rows remain searchable; Homepage has no chat.
  Legacy recommendation-list routes retain their existing semantics and can omit
  unavailable live item joins; use the completed-history reader for historical
  restoration. Existing saving/outfit-source visualisation behaviour is unchanged.
- Local implementation is SQLite despite `postgresql_repository.py` naming.
  PostgreSQL migrations/docs are not evidence of deployment execution. Audits must
  precede new constraints; no old records are repaired/deleted automatically.
  PostgreSQL needs real transaction/locking/FK/migration/concurrent retry tests;
  do not transfer SQLite's global writer-lock assumptions to PostgreSQL.

## Performance diagnosis and optimisation opportunities (not implemented)

The final separate real-HTTP 200-garment diagnostic measured Homepage 3.115s:
lookup 0.0010s, retrieval/setup 0.0098s, enumeration/reservoir selection 3.0218s,
persistence 0.0237s, residual 0.0585s. Assistant was 23.305s: lookup 0.0031s,
NLP 0.0118s, ranking 23.2633s, persistence 0.0180s, residual 0.0084s.
The residual includes authentication, dependency injection, serialization,
transport and untimed orchestration; it is not pure HTTP CPU overhead. Values
are single diagnostic trials, not additions to the repeated acceptance sample.
An earlier stage diagnostic measured Assistant 22.751s (22.721s ranking) and
Homepage 3.084s; the final artifact is the re-execution above, which also includes
the Chromium performance probe.

Chromium's submit-to-visible diagnostic took 22.853s wall time while cumulative
TaskDuration increased 0.245s, ScriptDuration 0.0165s, LayoutDuration 0.0083s and
RecalcStyleDuration 0.0019s. These overlapping browser counters include application
and automation work, not React-only attribution; do not sum them. They substantiate
that frontend CPU/layout is not responsible for the >21-second wait. This single
diagnostic is separate from the five repeated browser observations.

Direct authentication microdiagnosis: median valid-token verification ~3.46
microseconds per call (10 batches of 10,000); password verification median ~65ms
across five trials. Password verification is login-time work, not performed for
each authenticated recommendation. The authenticated capability HTTP baseline
medians are ~4.9–5.7ms, including transport/ASGI/DI, not just token HMAC.

Separate cProfile plus existing benchmark timers identify Python per-candidate
work, not CV inference, SQL retrieval, frontend rendering or NLP, as the bottleneck.
The final diagnostic executed all 134,820 candidates in 61.49s under profiling
(versus 21.82s repeated unprofiled HTTP median). Instrumentation materially slows
this run: **never report the profiled time as NFR acceptance**. It recorded about
92.7 million calls. Cumulative timings overlap; do not sum parent/child entries.
The final re-execution and full source hashes are retained with the profile.

Representative cumulative hotspots from the final complete profile:

| Function / work | Calls | Profile cumulative time | Meaning |
| --- | --- | --- | --- |
| RecommendationScorer.rank | 1 | 61.44s | Includes generation, mandatory gate, scoring, ranking and wrappers. |
| RequestMatchScorer.score | 134,820 | 11.62s | Repeated exact component construction/coverage evidence. |
| RecommendationScore.__post_init__ | 134,820 | 10.03s | Rechecks weights, fractions, normalized bounds and weighted total. |
| RequestConstraintEvaluator.evaluate | 269,640 | 8.24s | Exactly two evaluations per candidate: session plus independent gate. This second check is intentional, not removable merely for speed. |
| CandidateGenerator.enumerate | 134,821 next steps | 6.18s | Structural checks and immutable candidate/member construction. |
| CandidateRanker.better | 134,820 | 5.38s | Exact comparison plus session/profile safety. Key creation 269,639 times takes 3.72s, overlapping this row. |
| GarmentEvidenceMapper.classify | 1,064,460 | 2.54s | Existing session caches already prevent repeated actual colour classification, but lookup/equality work remains. |
| isinstance | 18.6 million | 5.03s | Distributed validation overhead, included in parent rows. |

Existing stage wrappers also measured construction ~6.44s, mandatory evaluation
including recheck ~8.81s, request scorer ~11.90s, unavailable compatibility overhead
~2.07s, empty-preference overhead ~2.02s, strict locked revalidation ~0.015s and
readback/commit remainder ~0.023s. These instrumented values overlap other profile
rows and must not be added as independent end-to-end components. Frontend
response-to-visible observations were generally ~6–54ms in Assistant/Homepage
samples; these include automation polling, not pure render profiling. They cannot
explain a >21-second Assistant computation.

Prioritised proposals, all requiring separate implementation approval:

1. Cache genuinely constant immutable unavailable-compatibility/no-preference
   components per session; preserve state diagnostics and exact zero contribution.
   Cache the current best comparison key while keeping the documented tie order
   and session/profile checks. Individually modest: the entire C/P overhead is
   only about 7% of this profile; even eliminating it gives an optimistic ~1.08x
   bound, not the needed ~4.36x. Caching half of key construction is only a few
   percent of total profile cost. These are prioritisation estimates, not measured
   optimisation results.
2. Prototype exact aggregate scoring/validated session facts to reduce repeated
   fraction/evidence-object construction. Score every valid candidate, preserve
   independent mandatory verification and immutable externally visible contracts,
   and construct full winner diagnostics without losing evidence. Moving or
   memoizing checks needs equivalence and failure-injection proof; do not simply
   delete safety checks or switch to inexact float ranking. Request-scoring and
   final score validation are substantial profile shares, so broader loop work is
   likely needed to approach 5s. No reliable speedup estimate exists before a
   separately approved prototype.
3. Consider exact safe structural/category pruning for selective requests only.
   A dress-only constraint in this workload admits 20*(1+20)=420 combinations,
   versus 134,820 total: a theoretical 321x reduction in evaluated combinations,
   NOT a measured latency speedup. The all-vintage broad baseline admits all
   candidates, so this cannot solve the measured worst case. Preserve Fail/Unknown
   precedence, diagnostic meanings, deterministic ordering and full-stream failure
   guarantees. Do not prune garments independently for a global colour condition.
4. Keep per-garment evidence caches separate for the independent verifier. A same
   immutable snapshot identity fast path may reduce equality checks; total mapper
   time is only ~4% here, so it cannot solve the target alone. No need to optimise
   database/authentication/NLP first given the measured millisecond costs.

Do not replace exhaustion with early top-one return, silently truncate, randomise
Assistant ties or add threads as an assumed CPU speedup. A process/vectorised
approach would require new complexity, exact-score/failure-order validation and
benchmarking; no such redesign or dependency is approved here.

## Dependency audit (2026-10-18)

Actual `npm audit --json`: 14 affected package entries, 1 moderate/12 high/1
critical. Production dependency-tree audit `npm audit --omit=dev --json`: six
entries, 1 moderate/4 high/1 critical. These counts include propagated findings,
not 14 independent exploitable defects. Raw advisories/fix metadata are retained
in the ignored verification directory. No broad upgrade or audit fix was run.

| Package | Severity | Present in production tree? | Practical interpretation / proposed remediation |
| --- | --- | --- | --- |
| next 16.2.9 | Critical | Yes | Windows App Router server falls in affected range; approval-gated upgrade to a currently patched compatible 16.x release (audit proposes 16.4.2), align eslint-config-next, rebuild/retest. No exploit executed. |
| sharp | High | Yes | Next image/native decoder dependency; update through compatible Next/sharp resolution; image attack surfaces need specific review, not an assumption all advisory paths are exercised. |
| postcss | High | Yes | Build/server dependency tree; source-map/CSS parsing advisories. Patch compatible resolved versions; user CSS uploads are not an app feature, reducing some attack paths but not removing dependency risk. |
| source-map-js | High | Yes | Malformed source-map DoS; compatible transitive patch, verify reachable build/runtime consumers. |
| nanoid | High | Yes | Invalid-size generator DoS; app interaction UUIDs use crypto.randomUUID, not nanoid. Patch dependency; do not claim this application passes attacker-controlled sizes without evidence. |
| baseline-browser-mapping | Moderate | Yes | Input-induced process termination; primarily tooling use despite production-tree inclusion. Patch resolved data/tooling dependency; production-tree presence alone is not request reachability. |
| brace-expansion | High | No | Glob expansion DoS; patch compatible transitive versions and rerun lint/tooling. |
| braces | High | No | Glob recursion exhaustion; review newer compatible lint dependency chain. |
| browserslist | High | No | Query/custom-stat memory or crash issues; patch tooling dependencies, avoid untrusted config/stats. |
| js-yaml | High | No | YAML CPU exhaustion; patch compatible resolved version, review CI input trust. |
| micromatch | High, propagated | No | Dependency on vulnerable braces; fix chain through tooling update. |
| fast-glob | High, propagated | No | Vulnerable glob chain; fix aligned lint tooling. |
| @next/eslint-plugin-next | High, propagated | No | Affected lint chain; align with patched Next generation. |
| eslint-config-next | High, propagated | No | Audit suggests a major downgrade to 14.2.35 for some glob findings; **do not blindly apply that downgrade** to a Next 16 app. Choose/test a compatible maintained toolchain separately. |

The Windows RCE advisory explicitly covers Windows filesystems without Cache
Components, matching the inspected local configuration; it states no known
workaround. Patch before public deployment. See the
[Next Windows advisory](https://github.com/advisories/GHSA-p293-qw3h-jr36).
The separate image and next/og critical advisories require their specific feature
paths; no next/og route is present, and exploitability is not established by this
audit. See [image advisory](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4) and
[next/og advisory](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j).

## Phase 5F-2 remediation order (proposal, not implemented)

1. **P0:** approve a narrowly scoped Next/runtime and aligned lint dependency
   security update, then repeat type/lint/build/browser and dependency checks.
2. **P1 / teammate:** correct review payload and run real onboarding browser
   regression with supported review fields; CV quality remains its own evaluation.
3. **P1 / teammate coordination:** reconcile recommendation-source strict save/
   visualisation eligibility and immutable historical recommendation semantics;
   verify concurrent changes without a long VTON transaction.
4. **P1 / Recommendation:** approve performance changes only after profiling;
   preserve exhaustive candidate sets, independent mandatory gate and exact winner
   arithmetic. Equivalence and interrupted-stream tests are mandatory for any
   later optimisation. Remeasure all four sizes, new keys and repeated trials.
5. **P2 / scope agreement:** decide the minimum supported live suitability/colour/
   compatibility scope for academic acceptance, collect reviewed quality evidence,
   and explicitly reconcile RN-17 partial compatibility with the report.
6. **P2:** decide user-facing historical score/provenance display and revalidated
   historical actions; correct context-specific history errors. Requires UI approval.
7. **Release gate:** approve maximum history/baseline deployment workload, execute
   PostgreSQL migration/concurrency if deployment uses it, test more browsers/
   devices, and rerun final end-to-end/NFR/security audit.

No final FYP completion, colour activation, scoring policy change or Phase 5F-2
fix is authorised by this document. Wait for the user's review.

## Verification commands, results and exceptions

From `frontend`:

```powershell
.\node_modules\.bin\tsc.cmd --noEmit --pretty false
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-phase5f-build'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3101'
npm run build
.\node_modules\.bin\playwright.cmd test --config playwright.phase5f.config.ts
.\node_modules\.bin\playwright.cmd test --config playwright.phase5f.config.ts --grep 'real browser review|single-request HTTP'
npm run test:browser
```

The initial Phase 5F configuration invocation discovered only the latency test
(the other audit files were added subsequently). It passed one complete
measurement run in 13.6 minutes; current isolated reproduction can select just
that run with `--grep 'repeated real HTTP'`. The separate functional/stage command
passed **2/2 in 50.2s**, including actual browser accept-payload 422 and API confirm
409, concurrent same-key persistence, stored scores/provenance, no regeneration
on history open, cursor pagination/invalid-cursor and cross-user checks.
Normal browser regressions passed **17/17 in 1.4 minutes**.

Initial production build passed (13 static pages plus dynamic detail route).
Final build uses `.next-phase5f-final` with the same explicit backend URL to avoid
reusing a test server's generated directory. TypeScript, lint and final production
build results are recorded after completion below. No frontend application source
changed during diagnosis. An earlier lint run overlapped Playwright cleanup of
`test-results` and failed ENOENT while traversing that directory; final checks run
sequentially after browser shutdown. This is a tooling race, not a clean initial
lint result or an application regression.

From `backend`:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_phase5f_audit.py tests/test_suitability_tag_workflow.py tests/test_frontend_recommendation_boundary.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/evaluate_nlp.py --output ../storage/verification/phase5f/nlp-evaluation.json
uv run --no-project --python 3.12 python -B scripts/evaluate_compatibility.py --output ../storage/verification/phase5f/compatibility-audit.json
uv run --no-project --python 3.12 python -B scripts/summarize_phase5f.py ../storage/verification/phase5f/latency.json
uv run --no-project --python 3.12 --with fastapi python -B scripts/profile_phase5f_auth.py
uv run --no-project --python 3.12 --with pillow --with numpy --with fastapi --with python-multipart python -B -m cProfile -o ../storage/verification/phase5f/assistant.prof 'C:/Users/chong/OneDrive/Desktop/Smart Wardrobe/smart-wardrobe/backend/scripts/benchmark_outfit_assistant.py' --sizes 200 --output ../storage/verification/phase5f/profile-stages.json
```

- Final selected backend suite: **639 passed, 1 failed**, **49.98s**; one existing
  Starlette/httpx deprecation warning. Sole failure is the existing ai-services
  assertion at `test_report_architecture.py:28`. Read-only folder inspection shows
  empty skeleton directories there, not an active second Recommendation backend.
  No directory/assertion was removed to satisfy the test.
- Focused audit/review/capability tests: **20 passed**, **9.03s**, same warning.
  This includes six new diagnostic cases: three existing action-eligibility gaps,
  legacy/explicit guard compatibility and two late-failure/interruption paths.
- An initial whole-suite collection without the ignore failed for missing cv2;
  a second ephemeral OpenCV-enabled environment then lacked torch. Heavy
  `test_segmentation_geometry.py` was explicitly not executed. No CV quality,
  real GPU/VTON, WAN/mobile, soak/load concurrency, deployment-data or PostgreSQL
  recommendation migration/transaction acceptance is claimed.
- NLP evaluation: intent **120/120**, five fields **450/450**, supplied fields
  **130/130**, combined **120/120**, per-field P/R/F1 all 1.0. RN-27 >=80% is met
  **only on this author-labelled synthetic fixed dataset**; dataset hash is
  `ced6418193e866649b635c6671ff2a1387becbd0435eb9eb0dc3a04a439760ba`.
  No independent human-labelled request evaluation was available to run.
- Compatibility audit: **0 approved references, 0 reviewed evaluation cases**;
  independent validation false. No invented fashion-accuracy result.
- Final diagnostic profile completes **134,820 scored candidates in 61.491s under
  cProfile**, with stage artifact and source hashes. An earlier cProfile invocation
  using a relative script path completed scoring but failed metadata serialization
  in the pre-existing benchmark's relative_to call. Reinvoking with the absolute
  script path succeeded; no production or benchmark algorithm was modified.
- Statistics tooling validates all 28 size/flow records and expected measured
  sample counts; refuses incomplete/duplicate workload records before certifying
  a full-run summary. Raw timing observations are not altered.

From `frontend`, read-only audits:

```powershell
npm audit --json
npm audit --omit=dev --json
```

Both intentionally report vulnerable dependencies; no audit fix/upgrade is run.
From repository root: `git diff --check`. Generated raw/profile/audit evidence is
under ignored `storage/verification/phase5f`; browser traces/results remain ignored.

## Changed files for Phase 5F-1

- `backend/tests/phase5f_server.py`: disposable multi-size/authenticated workload,
  explicit database path and test-only flags, separate functional-audit user.
- `backend/tests/test_phase5f_audit.py`: diagnostic source/save gaps, deliberate
  disabled-mode contract and late candidate failure/interruption via actual ASGI
  route, interpreter, strict retrieval, scorer and SQLite repository. ASGI tests
  use TestClient; separate browser tests use real localhost TCP.
- `backend/scripts/summarize_phase5f.py`: complete-run validation and raw-sample
  descriptive statistics; no samples/labels fabricated.
- `backend/scripts/profile_phase5f_auth.py`: isolated token/password microdiagnosis.
- `frontend/playwright.phase5f.config.ts`: isolated production server harness.
- `frontend/tests/phase5f/latency.spec.ts`: repeated actual HTTP/browser measurements.
- `frontend/tests/phase5f/integrity.spec.ts`: actual review blocker and integrity flow.
- `frontend/tests/phase5f/stages.spec.ts`: separate HTTP-stage/residual diagnosis.
- `frontend/playwright.config.ts`: excludes long Phase 5F diagnostics from the normal
  17-test regression command; no UI or selection change.
- `frontend/.gitignore`: ignores isolated Phase 5F build artifacts.
- `docs/PHASE_5F_REQUIREMENTS_AUDIT.md`: all 57 requested individual requirements,
  source pages, evidence, classifications and responsibility boundaries.
- `docs/PHASE_5F_VERIFICATION.md`: methodology, measurements, diagnosis, defects,
  dependency review, commands and remediation plan.
- `docs/REPORT_TRACEABILITY.md`: links the audit and records unresolved acceptance.

Pre-existing uncommitted Phase 1–5E files are not attributed to this phase.
Build-generated tsconfig includes are restored after checks; application source,
production feature defaults, completed contracts, historical data and teammate
algorithms remain unchanged.

## Final verification and readiness

Final frontend type check and lint pass with no reported errors/warnings. Final
production build (`SMART_WARDROBE_BUILD_DIR=.next-phase5f-final npm run build`,
PowerShell environment assignment as above) passes: all 13 static pages and the
completed-chat dynamic route. `git diff --check` passes; Git's LF/CRLF notices
are not whitespace-check failures. Build-generated tsconfig includes have been
removed without altering the existing source configuration.

Additional final commands:

```powershell
# frontend
.\node_modules\.bin\playwright.cmd test --config playwright.phase5f.config.ts --grep 'single-request HTTP'
.\node_modules\.bin\playwright.cmd test --config playwright.phase5f.config.ts --grep 'real browser review'
# backend, same dependency arguments as the focused command above
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_phase5f_audit.py -q --tb=short
```

Final stage/Chromium diagnostic: **1 passed in 1.2 minutes** (50.2s test body).
Expanded final integrity browser case: **1 passed in 8.5s** (1.9s test body), now
also confirming no eligible Homepage/Assistant result after archival, retained
historical items and real Unknown colour evidence. The earlier incorrect test
expectation that Wardrobe's null style remains missing failed; investigation
identified the existing null→[] normalization described above, not a production
change. The test now records that gap and exercises Unknown using a truly missing
primary colour. Final backend audit-file run: **6 passed in 3.92s**, including a
properly signed token with past expiry, not only a malformed token.

Statistical transparency: the initial collector summary used the upper middle
observation for even sample counts. The final collector and statistics tool use
the conventional mean of the middle two. Reported medians were recomputed from
all unchanged raw observations; collection intervals, candidate processing,
labels and sample counts were not adjusted. Tail estimates/observed ranges are
unchanged. Final source hashes identify current reproduction code.

The application is **not ready for full final FYP acceptance**: a tested Must
response-time target fails at 200, normal garment onboarding is blocked, strict
recommendation-source actions require teammate reconciliation, live compatibility
remains incomplete and independent quality evidence is absent. Critical dependency
exposure must be resolved before public deployment. The <=100-garment observations
support a limited demonstration of approved features using pre-confirmed data,
not full system, deployment, CV or fashion-quality acceptance. No completion
percentage or unmeasured optimisation speedup is invented.

Phase 5F-1 diagnosis is ready for user review with these findings retained.
**Phase 5F-2 fixes have not started.**
