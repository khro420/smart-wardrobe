# Phase 5F-2E-3J-16: final NFR performance acceptance verification

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-15 is owner-closed PASS WITH LIMITATIONS. All **105 browser observations and
21 direct HTTP comparisons** returned their correct results within the unchanged
applicable deadlines. This is a qualified local prototype evaluation, **not
supervisor-approved formal NFR acceptance**. The release/deployment baseline and
formal maximum-history designation remain unapproved. No production source,
default, model, provider, historical evaluation or capacity choice changed.

One frozen collection attempt completed. There were zero correctness errors,
missing results, response timeouts or deadline exceedances, and zero resource-
blocked attempts. A backend shutdown timeout occurred **after** all measurements
and the history comparison completed; it is retained below and prevents any clean
shutdown/recovery certification. No timing cell was rerun or replaced.

## Original requirement authority

The original Project I report was read at PDF180 (printed169). Its exact
requirement sentences, with PDF line wrapping joined, are:

- **NFR-01:** The system shall display one valid homepage outfit recommendation within three seconds after the homepage has completed loading under the baseline test environment.
- **NFR-02:** The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment.
- **NFR-03:** The system shall return chat-history search results within two seconds under the maximum chat-history workload defined in the system test plan.

All three have Must priority. `original-nfr-page.json` retains the raw page text,
local source path and PDF SHA256
`5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`.
`FINAL_ACCEPTANCE_READINESS_REVIEW.md` and the D7 decisions in
`FUNCTIONAL_SCOPE_SCORING_DECISION_PACKET.md` distinguish earlier readiness
measurements from approved baseline acceptance. Their earlier proposed200 scope
was subsequently superseded by the owner's accepted100 capacity; their historical
measurements and limitations were preserved, not rerun or relabelled.

## Frozen baseline, environment and configuration

`plan.json` was sealed before collection, together with243 execution/source/
policy/configuration/build-metadata files in `frozen-execution.json`. All243
still match. Plan SHA256:
`88a1beb98a852dcd0e4944c50e774b9ae002e64a5e715ded9364aae0fea44554`.
Execution-index SHA256: `836a9a7b02160e76a95a971f8103abe047fa75a2444e50ce43c0de9411d48249`.
No collector correction occurred after freezing.

| Component | Actual tested value |
|---|---|
| CPU/RAM | AMD Ryzen5 7235HS,8 logical processors;19.692GiB total physical RAM |
| OS | Windows11 Home Single Language,10.0.26200/build26200 |
| Disk/storage | WD PC SN5000S SDEPMSJ-512G-1101,512,105,932,800bytes, CIM interfaceSCSI/fixed disk; disposable SQLite/media/hot logs on local C: OS temp |
| Workspace | OneDrive-backed source/build directory; hot measurement database/logs stayed outside it and were copied after process cleanup |
| Backend | Python3.12.10, FastAPI0.146.0, Starlette1.9.0, Uvicorn0.54.0; one worker on127.0.0.1:3101 |
| Database | Actual SQLite3.49.1; journal_mode=delete, page_size4096, provider connections enable foreign keys; disposable new file |
| Frontend | Existing production Next16.4.2 build `K69qSH2Qlp-dAB6ZtNOys`, `next start` on127.0.0.1:3100; normal same-origin proxy |
| Browser | Playwright1.64.1, Chromium156.0.8078.4, headless1280x960 |
| Concurrency/network | One active timed interaction, local loopback; no concurrent test/build/profile/model workload launched by the collector |
| Media | Protected256x256 synthetic PNG thumbnails; image completion included, no real-photo/CV/VTON complexity claim |

`environment.json`, `backend-environment.json`, `browser-environment.json` and
`fixture-runtime.json` retain exact environment details; the latter three are
under `runs/initial/`. Actual backend PID14568 and frontend PID24656 were separate
local child processes. `process-ledger.json` retains launch commands and flags.
These are normal actual application services, not `/_test` route servers.

The five explicit child-process settings were:

```text
SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE=compact_exhaustive
SMART_WARDROBE_ASSISTANT_SCORING_PROFILE=experimental_compatibility_decision_v1
SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED=true
SMART_WARDROBE_ASSISTANT_ENABLED=true
SMART_WARDROBE_HOMEPAGE_ENABLED=true
```

Exact weights remain3/5,1/5,1/5 with the original tie sequence and complete
candidate evaluation. Suitability remains the supported8-occasion/2-formality
owner-declaration policy. Quota100, strict confirmed/available/owner acquisition
and J-14 fail-closed generation remain enforced. No policy/default activation
JSON or persistent service/host environment was changed. Unset scoring remains
deferred and suitability/integrated features retain their existing off defaults.

| Frozen input/config | SHA256 |
|---|---|
| J-10 capacity100 fixture | `54a7982de411102d88149e958d875155ce67b489fd881b4169df4483470a9776` |
| J-10 exact expected results | `34d4cae30091fd2ed5a476e68b1db852a4cd7126bb19a3ed23af9020bc28a84b` |
| Scoring policy | `3af5774382fe8740271f801dfdaec2cdda501543ae397e69559d54c8c8c9b9d9` |
| Suitability policy | `fdd7011ced629493b7c1a5adf6ff9b9ad02569948a7e2bee2fc87895cf70b709` |
| Frontend package lock | `ead9031efae37f2070b55d8f3c14ec3e896b374bd8d2b0a5e5cb513a13599032` |

The complete source/config hashes are in the execution index, including the
existing production build metadata. No new build was necessary for unchanged
application sources. A generated non-default local token secret was passed only
to the disposable backend environment; it is not written into the evidence.

## Workloads, schedule and boundaries

The owner-selected proposed academic capacity remains100 active garments.
The original J-10 balanced100 has17,710 structural candidates; maximum-combination100
has38,148. Exact original IDs, categories, materialized attributes, tags and
preferences were reused with genuine synthetic confirmed-item/job/owner links.
No homogeneous replacement, candidate pruning or deferred scoring was used.

NFR-03 uses **10,000 personal plus10,000 foreign completed chats**,50-row pages.
This is the explicitly owner-proposed test baseline, **not a previously approved
formal maximum or an enforced history quota**. Earlier readiness records report
1,000+3,000 browser and10k+10k API/query measurements. Those support investigating
this bounded maximum, not certifying it. Existing literal escaping, signed cursor
pagination and owner filtering make it technically suitable for this local
proposal. The supervisor/system test plan must still adopt its maximum/topology.

The new coherent synthetic history has one owned recommendation/member snapshot
per chat,5,000 available and5,000 saved results per owner, and repeated timestamps
to exercise stable timestamp/ID ordering. Independent expected rows use Python
substring/casefold and ordering, separately from the application query adapter.
Expected personal matches: empty/many10,000, campus1,000, no-match0, Unicode589,
literal percent527, underscore435 and rare2. No status-filter UI/API exists;
stored available/saved values are verified in returned rows instead.

The predeclared execution order was ten NFR-03 cells, two NFR-01 cells, then nine
NFR-02 cells. Each cell has **five fresh browser observations followed by one
direct authenticated HTTP comparison**. This gives50+10+45 browser and10+2+9 HTTP
observations. NFR-02 includes35 principal and10 separately diagnostic browser
observations; diagnostics do not become successful RN-13 fulfilment.

Authentication uses the real account login API and its JWT in normal browser
sessionStorage; no development identity or test-issued token is used. Public auth
page/login preparation is outside the measured boundary. The UI login form's
automatic Homepage redirect was avoided to prevent an unmeasured recommendation.
There is no ranking warm-up. A fresh browser context starts each cell; subsequent
trials reuse its caches. Every initial observation is retained. Fixture generation
and hashing precede startup, so no claim of cold OS/disk/database caches is made.

- **NFR-01:** native document load event to one complete visible result with every
  protected thumbnail loaded (`complete` and positive naturalWidth). Navigation-to-
  result is also retained. Signed post-load differences are retained before any
  zero clamp; no observation in this run completed before load.
- **NFR-02:** captured form submit before the normal React handler to the correct
  visible terminal state. Selected results additionally require loaded thumbnails.
  Capability lookup, NLP, exhaustive ranking, commit, proxy/network and UI are
  included. The ordinary component creates durable fresh submission keys.
- **NFR-03:** initial empty page starts at navigation timeOrigin. Search starts at
  captured form submit. A later page starts at Load more click and finishes only
  when the expected100 cumulative rows are rendered. Earlier page/search setup
  for a later-page case is excluded and disclosed; all underlying ASGI calls are
  retained. Chat-detail opening is outside search timing.
- **HTTP:** direct authenticated backend request through full JSON consumption,
  explicitly separate from browser/proxy completion. It does not substitute for
  a browser result or establish a Homepage post-load boundary.

The per-observation gate is correct outcome **and** elapsed<=3/5/2seconds as
applicable. No median/p95 substitution, slow-sample exclusion or deadline change
was made. Normal app/proxy/service timeouts were unchanged; the test's30s terminal
wait does not turn a result above its original deadline into a pass.

## NFR-01 results: observed local pass

All10 browser and two HTTP results were correct. Homepage retained random valid
selection; no deterministic Assistant winner expectation was imposed. Current
garment ownership/confirmation/availability and valid roles/order were checked
against the persisted database. No Homepage chat was created. All images were
loaded synthetic protected thumbnails, not loading indicators or missing media.

| NFR | Cell | Browser observations, all five in order | Median | Maximum | HTTP comparison | Deadline | Exceeded |
|---|---|---|---:|---:|---:|---:|---:|
|NFR01|balanced-100|0.456200, 0.408300, 0.405100, 0.350300, 0.424900|0.408300|0.456200|0.336444|3|0|
|NFR01|maximum-100|0.851900, 2.286100, 0.716900, 0.814200, 0.752700|0.814200|2.286100|0.633362|3|0|

Navigation-to-visible seconds, outside the stated post-load stopwatch but retained:

| Workload | All five browser observations in order |
|---|---|
|balanced-100|0.524900, 0.451200, 0.442900, 0.389600, 0.462000|
|maximum-100|0.949900, 2.329300, 0.759400, 0.866400, 0.800200|

The2.286100s second maximum-combination browser observation is retained in full;
it was not replaced by the faster surrounding values. The strict browser maximum
is2.2860999999642373s, leaving approximately0.714s observed post-load headroom.
This small local sample does not establish a universal3s guarantee.

## NFR-02 results: observed local pass for principal outcomes

All35 principal browser and seven direct HTTP observations met5s with the correct
outcome. Both generic and Campus+Casual Allow cases use the intended experimental
profile and suitability evaluator. Full17,710/38,148 candidate counts, exact
J-10 score metadata and deterministic member IDs match for all24 selected
Assistant submissions. Raw component/provenance conventions remain unchanged.

| NFR | Cell | Browser observations, all five in order | Median | Maximum | HTTP comparison | Deadline | Exceeded |
|---|---|---|---:|---:|---:|---:|---:|
|NFR02|balanced-100-generic|1.056400, 1.056100, 1.158700, 1.376700, 0.991500|1.056400|1.376700|1.199177|5|0|
|NFR02|balanced-100-allow|1.805200, 1.627400, 1.626100, 1.649600, 1.744500|1.649600|1.805200|1.729966|5|0|
|NFR02|maximum-100-generic|2.590600, 1.708100, 1.932500, 3.132100, 2.446100|2.446100|3.132100|2.616590|5|0|
|NFR02|maximum-100-allow|2.537300, 3.076600, 3.471000, 3.346500, 3.324700|3.324700|3.471000|3.308095|5|0|
|NFR02|empty|0.057600, 0.058100, 0.057700, 0.059100, 0.057000|0.057700|0.059100|0.039222|5|0|
|NFR02|no_match|0.071600, 0.057400, 0.057000, 0.057100, 0.059100|0.057400|0.071600|0.032492|5|0|
|NFR02|unsupported|0.038900, 0.026900, 0.028400, 0.027300, 0.028900|0.028400|0.038900|0.007878|5|0|
|NFR02|unavailable (diagnostic)|0.040600, 0.040900, 0.042500, 0.041100, 0.040300|0.040900|0.042500|0.014633|5|0|
|NFR02|insufficient (diagnostic)|0.058500, 0.057800, 0.059000, 0.072500, 0.059200|0.059000|0.072500|0.031946|5|0|

`generic` is “Suggest an outfit”; `allow` is “Suggest a casual outfit for campus.”
Empty wardrobe returns NoEligibleGarments; a known blue-only garment with a red
mandatory request returns NoMatchingCandidates; weather returns UnsupportedRequest.
The two diagnostics are exercise -> PolicyUnavailable and undeclared Campus/Casual
-> InsufficientEvidence. Their prompt terminal handling meets5s, but unavailable
capability and missing evidence are not positive suitability fulfilment or NLP
unsupported intent. No terminal/diagnostic case creates a recommendation/chat.

The browser maximum is3.471s, observed headroom1.529s. These bounded cases do not
cover all possible100-garment evidence distributions or concurrent deployments.

## NFR-03 results: observed local pass at the proposed maximum

All50 browser and ten HTTP observations met2s. The initial real history page,
empty next page, common-query first/next pages, no-match, Unicode, literal percent,
literal underscore, many and few matches all return the independently expected
totals, row fields/statuses and ordered IDs. Later-page DOM contains exactly the
correct100 cumulative rows; the corresponding HTTP page contains the next50.
All results belong to the authenticated history owner, with no foreign IDs.

| NFR | Cell | Browser observations, all five in order | Median | Maximum | HTTP comparison | Deadline | Exceeded |
|---|---|---|---:|---:|---:|---:|---:|
|NFR03|empty_first|0.399400, 0.218000, 0.224400, 0.215600, 0.208600|0.218000|0.399400|0.149498|2|0|
|NFR03|empty_next|0.169700, 0.189600, 0.161900, 0.188400, 0.280900|0.188400|0.280900|0.113807|2|0|
|NFR03|common_first|0.089700, 0.079900, 0.078200, 0.089900, 0.091000|0.089700|0.091000|0.070178|2|0|
|NFR03|common_next|0.112100, 0.096600, 0.128500, 0.110800, 0.129600|0.112100|0.129600|0.086199|2|0|
|NFR03|no_match|0.086500, 0.074900, 0.097800, 0.089100, 0.094900|0.089100|0.097800|0.072974|2|0|
|NFR03|unicode|0.094100, 0.096300, 0.094300, 0.090900, 0.092800|0.094100|0.096300|0.084595|2|0|
|NFR03|percent|0.094000, 0.094900, 0.096800, 0.110000, 0.093400|0.094900|0.110000|0.090186|2|0|
|NFR03|underscore|0.105800, 0.109400, 0.093000, 0.108500, 0.095000|0.105800|0.109400|0.072096|2|0|
|NFR03|many|0.125800, 0.110000, 0.127300, 0.141200, 0.128400|0.127300|0.141200|0.112060|2|0|
|NFR03|few|0.093400, 0.090800, 0.091900, 0.090600, 0.092300|0.091900|0.093400|0.067782|2|0|

The browser maximum is0.39939999997615816s on the first initial page. The first
observation is included, not silently warmed away. All20,000 seeded chats,
recommendations, items and snapshots remain unchanged across collection, verified
by row counts and full sorted-row hashes for each of the four tables. Search did
not rewrite history. This is no claim for an unbounded history size or search-plus-
detail timing, and formal maximum-workload adoption remains outstanding.

## Resources, observation cost and every operational failure

The predeclared gate waits for actual backend, production Next and browser/public
auth-route readiness, then10s settling and up to120s for three consecutive samples
with CPU<=20% and freeRAM>=4GiB. An early read-only check saw roughly66–72% CPU;
the owner was asked to pause OneDrive/heavy workloads. **The same initial attempt
qualified automatically** at15.8203125%,19.23076923076923%,19.23076923076923%,
before the readiness reply was processed. No blocked attempt or retry is invented.
All65 preflight samples, including one initial undefined CPU delta, are retained.

Preflight ranged15.77–100% CPU and4.425–6.258GiB freeRAM. During active collection,
122 one-second samples ranged **47.88–100% CPU** and **5.477–6.026GiB freeRAM**.
Runtime CPU clearly rose above the idle qualification threshold. Samples include
browser/backend/observer and background work; their causes were not isolated.
**Continuous idle/background isolation was not established.** Resource disturbance
does not erase the timings, and the completed cells were not repeated for quieter
numbers. One-second aggregate observations can miss shorter peaks; no concurrent-
user or low-contention deployment guarantee follows from them.

Native counter microchecks before collection measured median0.058ms/read
(maximum0.516ms); they exclude file/thread cost. A separate synthetic ASGI payload
diagnostic measured0.743ms median observed call/1.788ms maximum. It was not an
application recommendation and did not replace the real app in the collection.
Browser requestAnimationFrame observation cost is retained per trial (accumulated
0–8.700ms). No observer cost was subtracted from any measured duration.

The transparent ASGI wrapper forwards the untouched `app.main:app`, including its
normal lifespan/composition, and records full bodies/results plus duration/CPU
after forwarding. It adds no ranking/profile/evaluator route or application
replacement. The ledger contains244 history GETs (including declared setup and
chat-count checks),54 Assistant POSTs and12 Homepage POSTs. Generation records
join to browser/HTTP results by submission key. Their observed ASGI durations
span0.324–3.411s and processCPU0.297–3.234s. Assistant responses retain application
lookup/NLP/ranking/persistence timing. History ASGI maximum is0.232s across all
retained GETs; repeated GETs have no unique per-trial identifier, so no fabricated
one-to-one history service-time mapping is claimed. Browser time controls NFR-03.

**Retained failures/warnings:** initial new-test TypeScript checks reported
TS2352 for a Window cast; the new test gained a typed global declaration before
the plan was frozen. Final TypeScript/scoped ESLint pass. The focused backend run
retains one existing Starlette/httpx deprecation warning. The successful browser
run retains ordinary console/colour warnings and a backend Windows asynchronous
socket callback `ConnectionResetError: WinError10054`; all126 response/DOM checks
still completed correctly, with no observed affected terminal result.

After the browser returned exit0 and the history before/after comparison passed,
the supervisor requested normal shutdown. Backend14568 logged “Shutting down”
but did not finish within the30s wait; `launch-initial.log` retains TimeoutExpired.
It has no “Application shutdown complete”/exit0 proof. This interrupted the
launcher's final archive/Next cleanup, not the completed timing population.
The exact command lines/parent IDs were recorded before explicitly terminating
only owned backend14568 and frontend24656. Their launch children exited and both
ports were released. No unrelated process was stopped.

`recover_completed_attempt.py` copied21 original hot evidence files byte-for-byte
after cleanup, checked history equality and the completed126-row collector state,
and recorded `completed-attempt-recovery.json`. The frozen launcher was not
edited; the shutdown cause was not diagnosed or optimised in this performance
phase. All raw results are retained; no successful clean-shutdown/recovery claim
is made. No browser failure trace is present because the configured
retain-on-failure trace policy saw a successful collector; the external cleanup
failure remains in supervisor/backend logs.

## Correctness, persistence, regressions and integrity

The read-only post-collection audit confirms36 distinct recommendations:12 random
Homepage and24 exact experimental Assistant results, with24 distinct new completed
Assistant chats,36 metadata records and36 submission receipts. Item role/order,
display snapshots, score/provenance persistence and authenticated owner/confirmed
item/job/available proof are checked for every selected member. Total database
counts are20,036 recommendations and20,024 chats. There are no additional
generation writes from the30 terminal/diagnostic submissions. All11 quota
before/after projections match; both100-garment workloads remain exactly100.
Wardrobe, media, processing and preference tables match their initial full rows.

`persisted-state-audit.json` retains identifiers, keyed service observations and
proofs. `trials.json` retains full browser/API results, exact scores, keys,
browser clocks and invariant projections. `timing-ledger.csv` and `timings.md`
retain every value, with full precision in JSON/CSV; displayed rounding never
determines acceptance. No prior historical evaluation was rewritten.

| Verification | Result |
|---|---|
| Focused backend regressions |221 passed in69.38s; startup/release/suitability, Homepage/history/persistence, quota, fail-closed routing and frozen-source guard |
| Final fixture validation |1 passed in4.25s after the final snapshot-output addition; overlaps the focused run, not221+1 distinct tests |
| Production browser collector |1 test passed in3.1m, executing all105 browser and21 direct HTTP observations with zero correctness errors |
| Final TypeScript |`npx tsc --noEmit --incremental false` passed |
| Scoped ESLint |New browser test/config passed |
| Read-only persisted state/history audit |Passed; no extra generation writes, retained20k histories unchanged |
| Source/evidence integrity |All2,135 starting files,196 accepted J-15 indexed deliverables and243 frozen execution files unchanged |
| Whitespace/new-source syntax |`git diff --check`, explicit new-source whitespace and Python AST checks passed |

The preserved focused regressions exercise submission-key replay, rollback,
quota concurrency, fail-closed disabled routing and historical actions; this
phase does not claim a new multi-process or PostgreSQL test. No broad rerun,
capacity reduction/experiment, optimisation or model inference was needed.

New files are the focused fixture test, isolated browser test/configuration,
this report and the `phase5f2e3j16/` preparation/collector/observer/audit artifacts.
All existing application sources, original tests/guards/manifests/reference
archives and earlier reports/raw evidence remain byte-identical. The prior
working tree already contains uncommitted phases; cumulative Git changes are
not attributed to J-16. J-15 S07/S15 and N05/N06 qualifications remain intact.

## Requirement-by-requirement recommendation and closure

| Requirement | Observed local result | Formal acceptance recommendation |
|---|---|---|
| NFR-01 |PASS:10/10 browser results within3s; maximum2.286100s, loaded synthetic images and valid current membership |Insufficient evidence for formal baseline/deployment acceptance; approve actual image/network/hardware/resource scope first |
| NFR-02 |PASS:35/35 principal browser results within5s; maximum3.471s;12 separate diagnostic comparisons also correct/timely including HTTP |Remain OPEN / NOT FORMALLY ACCEPTED pending approved baseline; observed diagnostics do not fulfil unavailable features |
| NFR-03 |PASS:50/50 browser results within2s; maximum0.399400s; correct owner-isolated pages at proposed10k+10k |Insufficient formal-maximum approval; accept/test-plan designation remains an owner/supervisor decision |

All19 principal HTTP comparisons also meet the corresponding numerical bounds;
they are supporting transport measurements. Both diagnostic cells' five browser
and one HTTP observations are reported separately. These small bounded samples
do not prove universal deadlines, cold-storage performance, concurrent-user load,
real-photo rendering, production deployment or PostgreSQL equivalence.

**Final phase recommendation: PASS WITH LIMITATIONS.** The requested qualified
local verification is complete with every frozen observation retained and no
observed deadline failure. Formal NFR-01/02/03 approval remains unresolved,
runtime isolation was imperfect, and backend shutdown required owned-process
cleanup. This phase neither approves a deployment nor certifies service recovery.
Actual real-account quota inventory/support, provider commitment and CV/VTON
evidence remain separate release dependencies.

No defaults, algorithms, capacity choice, historical data or provider changed.
**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** No automatic remeasurement,
optimisation or J-17 starts. Wait for owner review.
