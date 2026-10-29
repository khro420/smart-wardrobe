# Phase 5F-2E-3J-4: controlled suitability and RN-13 end-to-end verification

2026-10-22. **PASS WITH LIMITATIONS - ready for owner review and closure.** Verification-only implementation; no general activation. J-3 is owner-closed PASS WITH LIMITATIONS. This phase explicitly enables suitability only in isolated test environments; general deployment defaults remain unchanged. No production application source is modified.

## Runtime inspection and authority

RN-13 (original Project I report, PDF188) requires filtering candidates according to structured extracted conditions. The approved eight-occasion/two-formality owner-declaration policy is a bounded implementation choice, not a report-defined fashion rule. Phase1 strict snapshots, Phase2 meaning safeguards, Phase3 structural/mandatory semantics and Phase4 deferred exact arithmetic are unchanged.

Actual composition: `backend/app/infrastructure/workflow_runtime.py` reads environment at startup and injects `SuitabilityRequestEvaluator` only when its flag equals true after lowercasing. `main.py` invokes composition in ASGI lifespan. No dotenv loader/env_file was found in the inspected backend application: a local .env alone is not evidence of configuration. The invoking verification shell had none of the four relevant variables set; actual deployment/service settings were not inspected.

| Setting | Accepted behaviour / unchanged default | Isolated enabled tests |
|---|---|---|
| SMART_WARDROBE_ASSISTANT_ENABLED | case-insensitive true enables; otherwise disabled, unset false | true |
| SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED | case-insensitive true selects declaration evaluator; otherwise minimum evaluator, unset false | true |
| SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE | exact compact_exhaustive or reference; unset compact_exhaustive; invalid rejects composition even if Assistant disabled | compact_exhaustive |
| SMART_WARDROBE_ASSISTANT_SCORING_PROFILE | exact compatibility_deferred or experimental_compatibility_decision_v1; unset deferred; invalid rejects composition | compatibility_deferred |

Boolean flags are not general truthy parsers: 1 is false; whitespace is not trimmed. Startup captures objects rather than hot-reloading environment per request. Browser server variables are explicitly assigned before app import, on a disposable SQLite database, with development AI and VTOFF disabled. Browser authentication uses actual login/bearer tokens and development identity is false. API fixtures use signed bearer tokens/active accounts, actual upload/review/confirmation, and the real composition function; test-only imported database defaults are redirected to each disposable fixture. No fabricated processing links or saved-outfit prerequisite is used. These are integration tests, not independent CV quality evidence.

Policy remains `owner-declarations-1.0.0`, reserved prefix rec:v1, default_activation false. Existing parser, occasion/formality evaluators, immutable evidence and compact independent mandatory verifier are unmodified.

## Bounded condition results

Each row is exercised through actual authenticated recommendation HTTP under compact/deferred, for Allow, Deny, absent, conflicting allow+deny and malformed relevant evidence.

| Field | Values individually exercised | All Allow | Deny | Missing/conflict/malformed |
|---|---|---|---|---|
| Occasion | campus, work, casual_outing, shopping, dinner, party, date, travel | Selected | NoMatchingCandidates | InsufficientEvidence |
| Formality | casual, smart_casual | Selected | NoMatchingCandidates | InsufficientEvidence |

Allow must apply to every constituent, including outerwear. Eighteen additional integrated cases change upper, lower and outerwear individually across six states, including a simultaneous occasion Deny/formality Unknown. Definite Fail wins; neither recognised blue/vintage nor a maximum matching colour preference rescues it. An annotation for dinner does not imply campus. Missing non-anchor primary hex remains Unknown for mandatory blue, even with declared campus Allow.

Multiple independent dress candidates include two positive, one denied and one missing declaration. Exactly two are scored exhaustively, one winner persists, and neither invalid candidate is selected. No candidate limit, role change, new structure, score convention or invalid fallback is introduced.

| Supported structure | Actual five-field integrated result |
|---|---|
| top + bottom | Both declared, complete two-member selection |
| top + bottom + outerwear | All three declared, outerwear category constraint enforced |
| dress | One genuine dress selected |
| dress + outerwear | Both declared, genuine dress retained |

Successful combined sentence template: `Suggest a casual outfit for campus with vintage style using blue colours with including a top and trousers` (plus outerwear where required), or `... with including a vest dress` (plus outerwear). The existing grammar accepts these function words; the API tests independently assert all five structured fields before submission and check every selected ID and declaration. The browser uses the more natural `Suggest a casual outfit for campus with vintage style using blue colours with a vest dress`. No grammar was extended.

Counterexample retained and explicitly tested: `Suggest a casual outfit for campus with vintage style and blue colours including a vest dress` returns UnsupportedRequest/garment_colour_binding. Existing interpretation requires the explicit `using ... colours with ...` global clause when categories coexist with colours. `blue top and black trousers` also remains unsupported. Exercise/formal requests return PolicyUnavailable, never mapped from style/category/fit/material. Outside-scope weather intent remains UnsupportedRequest. Definite red/classic mismatch remains NoMatchingCandidates even when campus declarations pass.

## Actual browser journey and history

A new test-only server starts with no seeded garments. Browser setup logs in, uploads a labelled synthetic image, reviews a detected item and confirms it through normal endpoints. The wardrobe editor assigns blue/vintage and Campus Allow/Casual Allow through existing friendly controls. Save includes captured If-Match; reload verifies persisted declarations. A five-field Assistant request produces exactly the confirmed dress, R=1, P contribution0, deferred total7/10, compatibility NULL. Changing Campus to Deny through the editor and reloading causes a fresh independent request to return NoMatchingCandidates with no result card. Replaying the completed submission returns its original ID/items/exact score metadata. Completed-chat GET still returns the historical recommendation. Declaration changes do not rewrite historical snapshots.

API integration also changes current declarations after completion and rebinds test composition to suitability disabled: new requests are PolicyUnavailable while same-key completed retry returns original score/provenance. Environment change alone does not hot reload captured policy. A separate in-flight test rebinds composition during preference acquisition to verify the current captured request and later independent requests use their respective policies; it does not claim an OS-level deployment restart.

Non-successful cases assert zero completed chat/recommendation/item writes. Selected cases assert exactly one chat/recommendation plus the correct member count; current writes use existing atomic persistence. Existing rollback/concurrency/interruption/idempotency/strict eligibility suites remain regression evidence, without altering their oracles. Cross-user and authenticated history/action safety remain covered. Enabled/disabling tests call `?pipeline=integrated` explicitly; no legacy placeholder generation is certified.

## Disabled configuration and release boundaries

Actual composition tests cover enabled+enabled, enabled+disabled, disabled+enabled and case-insensitive TRUE versus non-true 1. Disabled integrated Assistant returns404 IntegrationDisabled; enabled Assistant without suitability returns422 PolicyUnavailable for supported suitability fields. Existing UI capability checks avoid sending disabled requests to legacy. **Unqualified POST still invokes the legacy generator when integration is disabled.** This is a retained release limitation, not RN-13 proof; production routing remains unchanged and requires separate approval.

J-3 conditional tag replacement is preserved: missing revision428, stale/invalid409, correct revision succeeds, unrelated PATCH works without a revision. Existing real concurrent SQLite connections reject stale overwrites and injected trigger failure rolls back combined fields. Ordinary/reserved tags and style null/empty/unchanged semantics remain intact. This is content CAS, not an annotation audit trail or monotonic revision. Owner declarations can be stale and do not independently prove appropriateness.

Additional deployment limitation confirmed by an actual preflight against the disposable backend: main.py's cross-origin CORS allow_headers lists Authorization, Content-Type and X-User-Id, but not If-Match. The verified browser path uses the existing same-origin proxy, so it works without cross-origin preflight. An OPTIONS request for PATCH with Authorization/Content-Type/If-Match from the currently allowed localhost:3000 origin returns400 Disallowed CORS headers (raw result retained). A direct cross-origin browser tag editor therefore requires separately reviewed CORS configuration; no production fix or direct-cross-origin success is claimed here. This does not block the verified same-origin proxy path.

## RN-13 verdict and release recommendation

A: Annotation controls verified in J-3 and exercised again here. B: Bounded8/2 evaluator semantics verified. C: Real integrated compact/deferred Assistant fulfilment verified when explicitly enabled. D: General suitability default remains false; no deployment activation performed. E: exercise/formal unavailable. F: Approved names/aliases/exact anchors supported; arbitrary CV hex is not automatically classified. Primary colour remains authoritative; palette never overrides it. Approximation stays disabled; CV empty-pixel black provenance remains unresolved.

**RN-13 can be described as verified for the tested, explicitly enabled, owner-declared8/2 bounded scope. It is not fully closed against the unrestricted original requirement.** Owner/supervisor must explicitly accept this scope and colour coverage limitation before treating that as final fulfilment. Tests alone cannot supply that acceptance. No human fashion-quality or real extraction-quality claim follows from owner declarations or arithmetic checks.

Recommend a separately approved controlled release configuration with integrated Assistant true, suitability true, compact_exhaustive and compatibility_deferred, after explicit bounded-scope acceptance and actual service environment/restart verification. Keep the general default false until that decision. No additional evaluator algorithm is indicated for the approved8/2 workflow. Wider exercise/formal/hex capability needs separate approved policy/evidence; no style mapping, model, database field or automatic calibration is justified. Experimental scoring activation, Homepage policy, formal NFR acceptance and database/model work remain separate.

## Changed files

| File | Purpose |
|---|---|
| backend/tests/test_suitability_assistant_e2e.py | New authenticated real-composition API matrix, four structures, combined conditions, precedence, history/retry/capture. |
| backend/tests/suitability_integration_server.py | Dedicated disposable enabled-suitability browser launcher; explicit flags, no seeded garment links. |
| frontend/tests/phase5f/suitability-assistant.spec.ts | Actual review/confirmation/edit/reload/Assistant/current-state/history journey and retained JSON evidence. |
| frontend/playwright.suitability.config.ts | Enabled test-server selection and isolated artifacts; separate from normal default-off suite. |
| frontend/playwright.suitability-regression.config.ts | Unchanged default-off browser suite in a fresh isolated build directory. |
| docs/CONTROLLED_SUITABILITY_VERIFICATION.md | This current report. |
| docs/REPORT_TRACEABILITY.md | Append scoped verification status; preserve prior records. |

Additional local raw artifacts, original hashes, tsconfig backup, commands, logs and exact request/response JSON are in `storage/verification/phase5f2e3j4/`. No production source or historical source manifest is changed. Generated tsconfig additions are checked and original bytes restored after final verification.

## Retained attempts and verification

Initial API harness failures were test setup: imported repository default pointed at process test storage and active authenticated fixture owner was absent. These were corrected only in test setup; no eligibility/account requirement was relaxed. The first combined wording was rejected as garment_colour_binding; both that failure and a permanent actual-outcome test remain. Initial browser locator used Styles instead of the existing full label Styles (comma-separated); only the locator changed. The browser retry passed. Initial standard browser startup hit EBUSY on its historical build directory and was interrupted before tests; its log remains. A fresh isolated directory is used rather than deleting unrelated caches or weakening timeouts. Initial lint found two unused copied test constants; they were removed. Every initial/final log is retained, not retroactively called a pass.

Focused seven-file backend suite:269 passed,128.03s. Dedicated enabled browser retry:1 passed,45.9s. Production build Next16.4.2 and initial explicit TypeScript checks passed; final moved-path collector/lint and broad/default-off browser results follow. Build is verification only, not deployment or performance acceptance. No formal NFR benchmark is run.


### Backend completion

The full backend run completed: **2,036 passed,1 known failure**,451.25s. The sole failure is `tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`, asserting ai-services must not exist. Neither folder nor assertion is changed. Separate CV geometry is excluded because it requires its own torch/CV environment. Existing frozen-source, Phase1-4, persistence, stream-completion/failure, strict query, If-Match, concurrency, saved-outfit visualisation and historical action regressions passed. An additional in-flight capture test added after broad collection passed separately (1 pass,4.27s); the broad count is not inflated to include it.

The focused run retained94 actual HTTP request/response records:21 Selected (including replay),20 NoMatchingCandidates,43 InsufficientEvidence,5 PolicyUnavailable,3 UnsupportedRequest,2 IntegrationDisabled. These counts describe the prescribed matrix and extra calls, not a fashion-accuracy rate. All50 value/state combinations passed. All four structures passed with independent selected-member expectations. Three member positions across six states passed with maximum matching preference unable to override mandatory failure. Actual five-field scores were7/10 without preferences and1 when a fully matching colour preference contributed3/10; all are exact deferred rules, not new scoring.

Prior evidence checks: J-2 index37 artifacts and J-3 index26 artifacts match. J-1 has no equivalent evidence-index file in that location; it is not falsely reported as hash-certified by that index. No J-1 artifact was modified. Previous initial/slow/failing/performance evidence remains untouched. Formal NFR and overall FYP acceptance remain open.


### Final verification and closure

| Check | Actual result |
|---|---|
| Focused seven-file backend suite |269 passed,128.03s |
| Additional in-flight capture |1 passed,4.27s; separate from broad collection |
| Broad backend, separate CV geometry excluded |2,036 passed,1 unchanged architecture failure,451.25s |
| Normal suitability-disabled browser suite, isolated directory |54 passed,7.7m |
| Final enabled browser journey, permanent path + JSON artifact |1 passed,1.2m (test body16.0s) |
| TypeScript final explicit check |Exit0 |
| ESLint final explicit check |Exit0; only two existing navigation warnings |
| Isolated production build |Exit0,Next16.4.2 |
| git diff --check |Exit0 |
| Source integrity |371 pre-existing files checked; only appended traceability changed after restoring tsconfig;41 prior fixture files unchanged |

The final browser JSON is copied into `storage/verification/phase5f2e3j4/browser-actual-flow.json`; it records the persisted reviewed declaration, real selected recommendation, fresh Deny outcome and historical replay. API trials are in `verified-trials.jsonl` with an aggregate `trial-summary.json`. Exact commands are in commands.txt. Earlier retry/startup failures remain retained. No formal performance interpretation is made from test durations or diagnostic timings.

No new production application regression was reproduced. Direct cross-origin If-Match CORS remains a documented deployment limitation requiring separate approval; verified same-origin flow passes. The known ai-services assertion remains unresolved. No raw model results, human fashion ratings or deployment/database equivalence is fabricated. Previous closed reports/fixtures and J-2/J-3 indexed raw evidence are unchanged.

**J-4 is ready to close as PASS WITH LIMITATIONS.** Bounded enabled8/2 fulfilment and integration are verified. General suitability remains disabled by default; owner/supervisor scope acceptance and a separately approved release flag/restart decision are still required. RN-13 remains incomplete outside that bounded scope. No RN-17 scoring activation, approximate hex, formal NFR run or next phase begins.
