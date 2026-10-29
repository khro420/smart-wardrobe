# Controlled Assistant decision-profile integration

Phase 5F-2E-3C-3B. This is an explicitly selected experiment, not default-on or
general production activation. Existing rule values are implementation policies,
not independently validated fashion judgements.

## Selection and execution

`SMART_WARDROBE_ASSISTANT_ENABLED=true` is still required for the integrated
Assistant. New server-only `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE` accepts:

| Value | Behaviour |
|---|---|
| Unset / `compatibility_deferred` | Existing default, exact `.70R + 0C + .30P`. |
| `experimental_compatibility_decision_v1` | Prepared decision scorer, exact `.60R + .20C_decision + .20P`. |
| Anything else, including empty string | `ProfileUnavailable` for new submissions, no fallback. |

Selection version is `assistant-scoring-selection-1.0.0`; its canonical hash is
stored with each new result. Request bodies cannot select profiles (extra body
fields are rejected by the existing integrated endpoint); an arbitrary query
parameter does not override server configuration. Homepage selection is unchanged.

The Assistant first resolves authenticated-user submission idempotency. Existing
successful submissions replay their stored profile even after the server setting
changes or becomes invalid. New submissions resolve the allowlist, interpret NLP,
capture preferences, retrieve eligible garments through Phase 1, enumerate the
complete Phase 3 stream, apply mandatory evaluation and the independent scoring
gate, then score/rank with the selected policy. No candidate collection is added.
The original exact arithmetic, tie order, completion checks, pair cache and
256-entry prepared arithmetic cache remain unchanged. A selected score must pass
profile, weights, decision hash, raw rule hash and exact codec checks before writing.

Enumeration/ranking happens outside the write transaction. The existing repository
owns atomic idempotency resolution, strict transaction-bound garment/snapshot
revalidation and recommendation/chat/item/metadata writes. No schema migration,
historical rewrite or new saving/visualisation algorithm is required.

## Stored evidence and read-only presentation

The existing writer stores raw compatibility in the nullable SQL scalar, and the
exact full score/decision in authoritative JSON. A conventional midpoint never
becomes a fabricated raw value. NULL and measured zero remain different. Stored
JSON retains bounds, known/possible comparisons, structure, basis, exact fractions,
policy/version/hash, weights and weighted total. Provenance additionally records
the selection hash and `prepared-decision-1.0.0` implementation identity.

`scoring_display` version `assistant-scoring-display-1.0.0` is an additive, typed,
read-only projection on current Assistant and completed History responses. It is
derived from the saved metadata, never by rerunning ranking or current wardrobe
evidence. The same frontend component renders both:

| Basis | Display heading |
|---|---|
| Computed | Rule-based compatibility |
| PartiallyConventional | Partially estimated compatibility contribution |
| FullyConventional | Default compatibility contribution due to unavailable evidence |
| NoPairReference | Default contribution for a single-piece outfit |

Details show raw Unknown/Not applicable/actual value, coverage and applicable
bounds. Bounds are explicitly not confidence intervals. The UI distinguishes
conventions from measured rules and says these are not independent fashion ratings.
Deferred records retain their truthful compatibility-not-measured explanation.
Legacy records without identifiable metadata receive an unavailable explanation;
homepage responses without this projection retain their existing presentation.
Malformed or contradictory stored decision/scalar/profile data yields unavailable
details, not a recomputed score. The existing codec currently recognizes the
pinned v1 policy; future version support must retain old decoders or explicitly
show unavailable details. This phase does not implement policy-version migration.

## Synthetic worked examples

These are unit-test descriptors, not reviewed garment examples or quality evidence.
For generic requests with no stored preferences, R=P=0:

| Synthetic outfit evidence | Raw compatibility | Decision | Total |
|---|---|---|---|
| Blue/vintage top and blue/vintage bottom | 1 | 1, Computed | 1/5 |
| Blue/classic top and red/sporty bottom | 0 | 0, Computed | 0 |
| Recognized shared blue; styles missing | Unknown | 3/4, PartiallyConventional | 3/20 |
| Both colour and style unavailable | Unknown | 1/2, FullyConventional | 1/10 |
| Single dress | NotApplicable | 1/2, NoPairReference | 1/10 |

For a vintage single-dress request with a matching stored blue preference,
R=P=1, raw C=NotApplicable, C_decision=1/2, so S=3/5+1/10+1/5=9/10.
No per-candidate weight renormalization is introduced. Conventional contributions
can affect mixed-evidence ranking; that is disclosed policy, not proof of quality.

## Requirement and scope boundaries

Original report §§4.4.3/4.10.4 and RN-17–21 establish weighted scoring and ranking;
the selected decision convention, weights and UI terminology are separately
approved implementation policies. RN-15/16, NFR-24/25 and Phase 1 strict eligibility
remain authoritative. FR-OA and FR-CH completed-interaction/read-only semantics,
NFR-06/07 atomicity/idempotency and NFR-08/09 authentication/ownership are preserved.

The original PDF §3.3.5 (PDF p179 / printed p168) delegates the baseline deployment
environment and workload to the system test plan. NFR-02 appears on PDF p180 /
printed p169 and requires a recommendation, no-result or unsupported-request
response within five seconds after valid submission under that baseline. It does
not itself establish a numeric wardrobe maximum. This phase reports 20/50/100/200
as requested representative local workloads and 300,763 candidates as stress;
neither is silently declared the final approved deployment baseline. A slower
representative workload remains a performance gap, not a passed NFR.

No NLP, R/P meaning, structural generation, mandatory rules, homepage logic,
database schema, persistence writer, save/VIS paths, permissions, CV/VTON/VTOFF,
pattern scoring or unrelated performance optimization is changed. Suitability
remains opt-in, approximate hexadecimal matching remains disabled. The previously
reproduced review 422/409 issue and strict action inconsistencies were addressed
under their earlier separately approved integration phase; this phase preserves
those files and reruns their regressions, without claiming real AI quality testing.

## Verification methodology

`tests/assistant_decision_server.py` is a disposable, loopback-only test server,
never a production entry point. It seeds synthetic confirmed/available garments,
real users and one blue-colour preference per performance user. No real deployment
database is accessed. Four-category counts and independently calculated candidate
counts are exposed by the test fixture. The ordinary API/browser tests use real
password login/JWT and the actual runtime composition. Development AI fixtures
and synthetic protected-media references are not real CV/VTON evaluation.

Production Next/Chromium tests use isolated build output
`.next-integration-run/decision-production`. Each profile is run in a separate
fresh test-server process. Performance tests retain three repetitions per workload
and layer, without excluding warm-up or slow successful requests:

- Service: actual Assistant method, including lookup, NLP, retrieval, complete
  scoring, transaction commit and display projection, timed in a test-only endpoint.
- HTTP: real authenticated endpoint elapsed time; test-only middleware also records
  server processing including dependencies/serialization, before network body delivery.
- Browser: submission click through visible result, plus click-to-response latency
  and server header timing. Login/page preparation is outside submission latency.

Each successful result must report exactly the independent candidate count. Errors
and timeouts are recorded; the tool completes remaining trials then fails its final
error assertion rather than substituting no-result or truncating. A read-only
test-fixture lookup waits for a disconnected request's backend commit before the
next trial, avoiding accidental overlapping enumeration. Resume mode retains all
old samples, including errors, and restarts only the disposable server for missing
trials. The first original failed browser sample includes page preparation in its
error timer; it is retained unchanged and not presented as successful submission
completion. Later error timers start at submission. Observed maximum is the reported tail; three samples do not support a
reliable p95 estimate. Local HTTP is a test transport, not deployment HTTPS proof.

Actual measured results and exact verification commands follow below.

## Phase file inventory

Paths are relative to repository root; earlier uncommitted phase changes are not
attributed to this phase.

| File | Change / purpose |
|---|---|
| `backend/app/application/recommendation/assistant_scoring_selection.py` | New allowlisted server profile selection, scorer dispatch and selected-score validation. |
| `backend/app/application/recommendation/scoring_display.py` | New immutable typed projection of authoritative stored evidence and legacy fallback. |
| `backend/app/application/recommendation/outfit_assistant_service.py` | Optional profile configuration, dispatch, provenance, validation and display projection; old default constructor preserved. |
| `backend/app/infrastructure/workflow_runtime.py` | Server environment binding only; existing Assistant enablement/default preserved. |
| `backend/app/application/chat_history/chat_history_service.py` | Read-only projection on restored recommendation. |
| `frontend/lib/api.ts` | Additive typed display contract. |
| `frontend/components/CompatibilityExplanation.tsx` | New shared truthful display for computed/conventional/legacy evidence. |
| `frontend/components/RecommendationResult.tsx` | Reuse shared explanation for Assistant and History. |
| `backend/tests/test_assistant_decision_integration.py` | Real service/SQLite/API, four structures, metadata, constraints, concurrency, rollback, save/VIS tests. |
| `backend/tests/test_outfit_assistant.py` | Explicitly isolate the existing default-profile composition test from external experimental environment settings. |
| `backend/tests/assistant_decision_server.py` | New disposable real-server functional/performance fixture and test-only timing. |
| `backend/tests/integration_source_guard.py` | Recognize exactly the separately authorized integration replacements/additions while retaining old pins. |
| `backend/tests/fixtures/assistant_decision_integration_sources.v1.json` | New before/after hashes for three replacements and hashes for two new modules. |
| `backend/scripts/summarize_assistant_decision_integration.py` | Reproducible latency summaries and original/archive integrity verification. |
| `frontend/playwright.decision.config.ts` | New isolated production-browser verification configuration. |
| `frontend/tests/phase5f/decision.spec.ts` | New real API/History browser cases, UI evidence screenshots and repeated three-layer benchmarks. |
| `frontend/tests/recommendation.spec.ts` | Archive an actually selected garment in the existing regression; do not assume one hardcoded dress wins both scoring policies. |
| `docs/ASSISTANT_DECISION_INTEGRATION.md` | Contract, inventory, evidence, commands and acceptance limitations. |
| `docs/REPORT_TRACEABILITY.md` | Append this phase's requirement evidence and limitations. |

Ignored build/type declarations, Playwright traces/screenshots, logs and JSON
measurement artifacts remain local verification output. Next's automatic isolated
type include edits are removed from `tsconfig.json` after verification; no permanent
compiler configuration change is needed.

## Verification commands and functional results

From `backend`, VTOFF explicitly off, Python 3.12.10:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
# Run each command with the profile set to compatibility_deferred, then
# experimental_compatibility_decision_v1 (new integration tests also parameterize both).
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_assistant_decision_integration.py -q --tb=short
```

| Verification | Actual result |
|---|---|
| Initial existing Assistant/History/prepared tests | 206 passed, 22.57s. |
| Final new focused tests, default environment | 41 passed, 20.22s. |
| Final new focused tests, experimental environment | 41 passed, 16.28s. |
| Broad default backend collection | 1,522 passed, one known architecture failure, 193.25s. |
| Broad experimental backend collection | 1,529 passed, same known architecture failure, 232.25s. |
| Existing browser default suite | 35 passed, 4.0 minutes. |
| Existing browser experimental suite, final isolated run | 35 passed, 2.7 minutes. |
| Revised archival test under default profile | One passed, 28.8s including server startup. |
| New production-browser functional tests | Eight passed per profile (38.2s default, 27.1s experimental). |
| Invalid server profile, real production browser | One passed, 18.2s. API 422/ProfileUnavailable; no result/fallback. |
| TypeScript | `npx tsc --noEmit`, exit 0. |
| ESLint | `npm run lint`, exit 0, two pre-existing navigation warnings in extract/results and Layout. |
| Production build | `npm run build`, exit 0, Next 16.4.2, static generation 13/13. |

The broad collections ran while integration tests were being expanded (32 then
39 new cases collected); the final 41-case focused file subsequently passed under
both environments. Counts overlap and must not be added as unique tests. Existing
FastAPI/Starlette TestClient emits one httpx deprecation warning. The geometry test
is explicitly excluded because this verification environment does not provision
its cv2/torch model stack. No real GPU/CV/VTON-quality or deployment PostgreSQL
verification is claimed.

The remaining architecture failure is
`tests/test_report_architecture.py:28`, asserting `ai-services` does not exist.
That existing folder/assertion was not deleted or rewritten. It is independent of
this Assistant integration, so the broad suite is not reported as fully green.

Initial new test failures were fixture errors (wrong metadata table/checkpoint
names, History query pointing at the wrong disposable DB) and were corrected.
The first experimental legacy browser run exposed a fixed-dress winner assumption:
the experimental scorer legitimately chose a two-piece outfit. The test now
archives an actual selected constituent; both profiles pass. A subsequent rerun
had one ENOENT trace teardown error because concurrent Playwright configurations
shared `test-results`; separate output directories and an isolated full rerun
resolved it. The new default-browser error test also scoped `role=alert` to main
content to exclude Next's route announcer. None required application workarounds.

From `frontend`:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/decision-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3201'
npm run build
# Both valid profiles, separately, using the value set in the backend command above:
npx playwright test --config playwright.integration.config.ts
# Final isolated experimental rerun:
npx playwright test --config playwright.integration.config.ts --output .next-integration-run/legacy-decision-results
# Revised default archival assertion:
npx playwright test --config playwright.integration.config.ts --grep 'Real backend login, Homepage' --output .next-integration-run/legacy-default-results
# New production-browser functional tests, each valid profile separately:
npx playwright test --config playwright.decision.config.ts --grep 'real Assistant|real controlled'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='invalid-test-profile'
npx playwright test --config playwright.decision.config.ts --grep 'real unavailable'
# Measurements: run separately for compatibility_deferred and experimental_compatibility_decision_v1.
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
$env:SMART_WARDROBE_DECISION_BENCHMARK='true'
npx playwright test --config playwright.decision.config.ts --grep 'repeated real service'
# If a run stops early, retain its evidence and resume only missing trials:
$env:SMART_WARDROBE_DECISION_BENCHMARK_RESUME='true'
npx playwright test --config playwright.decision.config.ts --grep 'repeated real service'
```

The build variables above are scoped to the build/test process; they are not
written to deployment configuration. The original existing-browser configuration
sets its own development build path and backend port. New verification uses a
production server and distinct ports 3200/3201. No unrelated directory deletion
was used to resolve Windows cache/build issues.

Reproduce summaries from `backend` after collecting both profiles:

```powershell
uv run --no-project --python 3.12 python -B scripts/summarize_assistant_decision_integration.py
```

Raw logs, measurements and screenshots are local artifacts under
`storage/verification/phase5f2e3c3b/`. JSON retains every timing and error record;
screenshots cover all seven evidence/structure examples for both profiles.

The initial stress browser trial failed with a production proxy socket reset and
HTTP 500, not a valid recommendation/no-result response. The installed Next 16.4.2
`node_modules/next/dist/server/lib/router-utils/proxy-request.js:37` uses
`proxyTimeout || 30000` by default; no proxy timeout configuration was changed.
Direct backend stress requests can succeed while the browser path resets around
30 seconds. This is an unresolved end-to-end performance/transport blocker, not
an environment artifact to discard. The initial measurement driver stopped after
its first JSON parse error; its original JSON/log are retained, and revised tooling
records the remaining trials and eventual backend completion separately.

## Actual local integrated measurements

Seconds; three retained trials per cell. Tail = observed maximum, not p95.
Successful completions only in median/max columns; every failed trial is counted explicitly.
Backend column is middleware processing for the real HTTP trials. Browser
times include submit-to-visible completion; all layers use fresh submission keys.

### compatibility_deferred

| Garments | Candidates | Service median / max | HTTP median / max | Backend median / max | Browser median / max | Errors service/HTTP/browser |
|---|---|---|---|---|---|---|
| 20 | 198 | 0.089 / 0.105 | 0.086 / 0.099 | 0.080 / 0.094 | 0.220 / 0.286 | 0/0/0 |
| 50 | 2,430 | 0.539 / 0.594 | 0.516 / 0.550 | 0.511 / 0.544 | 0.676 / 0.695 | 0/0/0 |
| 100 | 17,710 | 3.799 / 4.051 | 3.654 / 4.073 | 3.649 / 4.067 | 4.373 / 4.554 | 0/0/0 |
| 200 | 134,820 | 26.723 / 28.706 | 21.069 / 21.622 | 21.064 / 21.615 | 22.387 / 22.668 | 0/0/0 |
| stress | 300,763 | 47.185 / 47.815 | 53.083 / 56.198 | 53.079 / 56.190 | No completed response | 0/0/3 |

### experimental_compatibility_decision_v1

| Garments | Candidates | Service median / max | HTTP median / max | Backend median / max | Browser median / max | Errors service/HTTP/browser |
|---|---|---|---|---|---|---|
| 20 | 198 | 0.122 / 0.389 | 0.127 / 0.133 | 0.119 / 0.126 | 0.250 / 0.387 | 0/0/0 |
| 50 | 2,430 | 0.936 / 0.973 | 0.916 / 0.932 | 0.911 / 0.924 | 1.246 / 1.643 | 0/0/0 |
| 100 | 17,710 | 6.799 / 8.012 | 6.887 / 7.201 | 6.881 / 7.193 | 7.298 / 7.685 | 0/0/0 |
| 200 | 134,820 | 42.408 / 43.350 | 41.827 / 44.780 | 41.823 / 44.777 | No completed response | 0/0/3 |
| stress | 300,763 | 91.247 / 91.934 | 89.236 / 92.468 | 89.231 / 92.463 | No completed response | 0/0/3 |

All 90 scheduled trials are retained: 81 successful completions, 9 errors.
Every successful result has the expected full candidate count. Errors remain failures,
even where read-only inspection subsequently confirms backend commit after proxy reset.
No no-result substitute, candidate truncation or timing sample exclusion occurred.
NFR-02 remains unmet for representative workloads exceeding five seconds; these
local synthetic measurements do not approve a final deployment baseline or human fashion quality.

Integrity: 154/157 original application files byte-identical; exactly three separately
authorized integration replacements. All 22 pre-phase fixture/manifests/archive
entries in the phase snapshot remain byte-identical; old reference pins were not rewritten.

### Workload interpretation and release decision

| Workload | Eligible vest / trousers / vest_dress / long_sleeve_outwear | Active preferences |
|---|---|---|
| 20 | 8 / 8 / 2 / 2 | 1 colour preference, blue |
| 50 | 20 / 20 / 5 / 5 | 1 colour preference, blue |
| 100 | 40 / 40 / 10 / 10 | 1 colour preference, blue |
| 200 | 80 / 80 / 20 / 20 | 1 colour preference, blue |
| Stress, 200 garments | 67 / 67 / 0 / 66 | 1 colour preference, blue |

Every garment is synthetic blue/vintage. The supplied vintage-style request
admits the entire complete structural set. No saved outfits are required or
seeded. This homogeneous evidence workload is not a worst-case diversity study.
Profiles ran sequentially, not as alternating statistically paired trials. These
real-persistence, one-preference workloads are not directly interchangeable with
previous zero-preference, in-memory scorer benchmarks. No causal speedup claim
is made from comparing those different experiments.

The default profile's 100-garment browser median/max was 4.373/4.554 seconds;
its 200-garment median/max was 22.387/22.668 seconds. The experimental profile's
100-garment median/max was 7.298/7.685 seconds; all three 200-garment browser
trials failed around the 30-second proxy timeout. Both profiles failed all three
stress browser trials. The performance Playwright test therefore FAILS for each
profile (one failed test case per completed profile measurement run), correctly
retaining the nine real transport errors. The default initial run stopped at its
first stress error; the resumed run retained that error and completed the two
remaining trials. No failed sample was rerun and substituted as a success.

Eight resumed/new proxy-error trials were subsequently confirmed to commit their
full candidate counts (default stress trials 1/2; experimental 200 and stress
trials 0/1/2). The first original default stress error's server was torn down when
the initial driver failed, so its eventual commit is not claimed. A committed
record after client failure supports persistence robustness, not NFR compliance.
The original five-second target is unchanged. NFR-02 is UNMET on the failing
representative workloads; the stress case is reported separately. Proxy errors
are unresolved operational failures, not a reason to report backend-only timing
as browser success.

Functional integration status: PASS WITH LIMITATIONS. All functional assertions
pass after the documented fixture/test-output fixes. Exact metadata, mandatory
gates, all four structures, historical immutability, idempotency, rollback and
existing action workflows were verified. The broad backend suite still has its
one known independent architecture failure; the performance measurement tests
have the real proxy failures above.

Activation readiness: NOT READY for general deployment, default-on activation,
or final FYP acceptance. The path is available only for explicitly selected,
controlled experimentation. No deployment configuration was enabled. Required
next acceptance work is a separately approved performance/transport resolution
and NFR retest against an explicitly agreed baseline, plus independent human
compatibility-quality/decision-convention validation using held-out examples and
weight sensitivity. This phase collected no new independently reviewed outfit
ratings and makes no general fashion-accuracy claim. Deployment HTTPS,
PostgreSQL, real models/GPU quality and additional browser engines were not
validated here. The existing development-AI tests prove integration only.

The compiled application sources did not change after the successful production
build. Final TypeScript/ESLint checks include the later measurement-tool changes.
The original tsconfig.json bytes were restored using the pre-phase SHA256 match;
no permanent isolated-build compiler include change remains. All 22 old fixture,
manifest and frozen-archive entries in the phase snapshot remain byte-identical.
The original 157-file reference remains intact: 154 current files are identical,
and three integration replacements have explicit before/after authorization pins.
Seven rule-based additions, three pair-cache additions, five original decision
additions and two prepared additions retain their old independent hashes.

Do not activate the experimental default, change timeouts, optimize further,
change suitability/hex policy, or begin another phase without user review.

Final checks: TypeScript exit 0; ESLint exit 0 with the same two existing warnings;
git diff --check exit 0 (only existing LF/CRLF notices). A separate scan of all 19
phase files, including untracked additions, found no trailing whitespace. All five
new application pins match. Broad environment B preserves unit tests that
explicitly construct the deferred default; the new parameterized and real-runtime
integration cases separately exercise explicit experimental selection.

The original report was also rechecked directly: RN-15?17 on PDF p188,
RN-18?23 on p189, deterministic ranking on p233, persistence/ownership on
pp267/269, weighted scoring on p285, and NFR baseline wording on pp179/180.
The saved extract is original-report-check.txt in the verification directory.
No conflicting new eligibility/scoring interpretation was introduced. Outstanding
quality and performance limitations remain limitations against final acceptance.
