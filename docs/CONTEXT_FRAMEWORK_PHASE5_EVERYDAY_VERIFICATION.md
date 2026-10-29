# Context Framework Phase 5: everyday recommendation implementation and verification

2026-10-26, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
Phase 4 is owner-accepted as a completed read-only review. The expressly approved
EC01–EC10 increment now supports ordinary academic attendance, shopping and casual
outings through `general_context_v1`. There is no separate event interpreter,
evaluator or scorer. The existing five context policies and frozen profiles remain.
The manual application was not restarted or activated by this work.

**155 requirements remain 144 Verified / 2 Partial / 9 Unverified / 0 Blocked.**
RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. Whole-FYP
acceptance remains NOT READY. These are bounded prototype appearance heuristics,
not independently validated fashion, safety, comfort or dress-code judgements.

## 1. Explicit approval and exact change scope

The owner answered all three mandatory questions before production editing:

- **“Approve EC01–EC10, evidence reuse and matrix”**: includes the supervisor/shared/T
  evidence decision, academic-class convention, provisional style inference, exact
  declaration scopes, supported optional information, precedence and intentional
  natural/command transition in the general profile.
- **“Backend/API owners approve this exact scope”**: eight proposed backend files,
  the named new tests/fixtures and exactly three existing test/support files.
- **“Frontend owners approve this exact scope”**: four named frontend files and the
  named new browser test/configuration.

[ownership-approval.json](../storage/verification/everyday_context_v1/ownership-approval.json)
records that authority. The unchanged Phase 4 proposed matrix was copied before the
production patch; a separate approved fixture references this authority. The 73
scenario descriptions and their original expectations remain equal. Proposed label
rows retain their authoring metadata; actual execution is recorded separately,
never manufactured by changing a label's NOT RUN field into a pass.

**Ten existing production files change; no production file is added.** The compiler
and resolver, although approved for necessary changes, are reused byte-identically.
No permission beyond the actual named scope is inferred.

| Owner | Changed production path | Change |
|---|---|---|
|R NLP|`backend/app/application/nlp/general_context_interpreter.py`|Bounded ordinary situation matching, contained aliases, protected existing context/venue overlaps and rejection of non-ordinary action frames.|
|R NLP|`backend/app/application/nlp/config/context_grammar.v1.json`|Grammar 1.3.0; explicitly represented campus venue. No unrestricted NLP.|
|R taxonomy|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`|Taxonomy 1.3.0; three appended ordinary situations and approved bounded phrases.|
|R policy|`backend/app/application/recommendation/config/context_policy_registry.v1.json`|Registry 1.3.0; three appended style-set bindings. Existing five binding subtrees compare equal.|
|R validation|`backend/app/application/recommendation/context_policy_registry.py`|Closed eight-binding activation envelope, exact new scopes/evidence/code/style sets and human-readable limits.|
|R explanation|`backend/app/application/recommendation/general_context_evaluator.py`|Version 1.3.0 everyday summaries and scope notes; existing evaluation and old explanation branches retained.|
|Shared frontend|`frontend/lib/api.ts`|Typed 1.3.0 summary and optional scope note; other API contracts preserved.|
|Shared frontend|`frontend/lib/recommendation-messages.ts`|Everyday insufficient-evidence guidance without interview-only requirements.|
|Shared frontend|`frontend/components/OutfitAssistant.tsx`|Supported ordinary examples, scope notes and versioned messages.|
|Shared frontend|`frontend/components/RecommendationResult.tsx`|Stored everyday explanation rendering alongside all older formats. Existing full-name wrapping/actions retained.|

Unchanged approved backend paths are
`backend/app/application/recommendation/context_constraint_compiler.py` and
`backend/app/application/recommendation/context_evidence_resolver.py`. Their existing
generic `legacy_exact_declarations_v1` channel and reviewed-style set predicate
already implement the needed gates. There is no new garment namespace, writer,
review UI, route, snapshot contract, database provider or migration.

The only existing test/support edits are `backend/tests/integration_source_guard.py`,
`backend/tests/test_general_context.py` and
`backend/tests/test_general_context_equivalence.py`: one explicit source transition,
the current registry version and active-capability expectation. Frozen labels and
their old outcomes remain. Six named new files provide the two everyday backend
modules, approved labels/source fixtures and browser test/configuration.

`everyday_context_sources.v1.json`, `source-transition.json`, before copies and
`approved-existing-files.patch` identify the exact ten transitions within the earlier
uncommitted tree. Old source manifests are followed, not repinned. Intermediate
transition bytes are retained; publication uses atomic replacement and is not
performed while source certification reads them.

## 2. Implemented capabilities and exact request outcomes

| New semantic ID | Binding | Existing declaration target |
|---|---|---|
|`everyday.academic_attendance`|`campus_day_appearance_v1`|`campus`|
|`everyday.shopping`|`shopping_appearance_v1`|`shopping`|
|`everyday.casual_outing`|`casual_outing_appearance_v1`|`casual_outing`|

Grammar/taxonomy/registry are 1.3.0. Binding policy versions are respectively
`campus-appearance-1.0.0`, `shopping-appearance-1.0.0` and
`casual_outing-appearance-1.0.0`. Source/bundle hashes distinguish actual bytes.
The current taxonomy contains 14 situations and eight binding definitions; that
does not mean every phrase, role, code or activity for those labels is supported.

| Exact request | Final interpretation / request-policy admission |
|---|---|
|I'm going to class.|Supported → academic attendance → campus binding. No role/code/formality invented.|
|I have university tomorrow.|Supported → same campus binding; tomorrow retained as information only.|
|I'm going shopping.|Supported → shopping binding.|
|I'm going out with friends.|Supported → casual-outing binding; friends retained without garment evidence or score.|
|Suggest an outfit for campus/class/university.|Same ordinary campus binding and Deny scope. Individual aliases are separately checked.|
|Suggest an outfit for shopping/a shopping trip.|Same shopping binding; contained shopping/shopping-trip matches are one event.|
|Suggest an outfit for a casual outing.|Same casual-outing binding and declaration target.|
|Suggest something blue for shopping.|Same binding plus original hard global blue constraint.|
|I'm going shopping; the dress code is casual/smart casual.|Same occasion plus separately mandatory matching code/formality gate.|
|I have a university presentation.|Recognised specialised context; PolicyUnavailable / required_context_missing, with role missing. Ordinary university aliases do not swallow it.|
|I have a job interview.|Recognised employment context; required role/code remain missing.|
|I'm going to a fitness class / university for a chemistry lab.|UnsupportedRequest; specialised modifiers are not removed.|
|I'm presenting at class / conducting shopping.|UnsupportedRequest; those action words cannot be consumed as ordinary attendance/shopping.|
|Formal or black-tie everyday code|Recognised supported phrase forms → PolicyUnavailable / unsupported_dress_code. Allow cannot activate it.|
|Prefer blue / comfort requirement in an ordinary request|Represented soft/goal requirement → unavailable; unknown meaningful modifiers still reject.|

Complete final pure frames/admission observations are retained separately from the
73 actual API scenarios. Natural/command tests compare declaration targets, exact
scores and winners while allowing different original-text spans/companions/time.
They are semantically equivalent clothing requirements, not byte-identical frames.

Recognition/admission still does not guarantee an outfit. Fresh recommendation
requires enough current eligible evidence and a complete structure. The initial
unsupported case cannot be reduced to a generic outfit with its situation discarded.

## 3. EC01–EC10 conformance and evidence precedence

| Rule | Implemented and executed evidence |
|---|---|
|EC01|Only ordinary contexts; disclosed academic-class convention without a student role. Presentation overlap, fitness/lab, multiple contexts and non-ordinary actions are negative controls.|
|EC02|Unspecified code permits current reviewed singleton casual OR smart casual as positive occasion inference. The structured formality/code remains null. UI/provenance disclose the provisional guideline.|
|EC03|Explicit casual uses casual style inference and an independent required casual formality condition; exact formality declarations remain applicable.|
|EC04|Explicit smart casual uses matching smart-casual evidence and separate formality. Formal/black tie remain unavailable; no hierarchy approximation.|
|EC05|Exact campus/shopping/casual_outing Deny first, including conflict/malformed companion evidence; otherwise malformed authoritative evidence blocks, then exact Allow, then inference only for genuine absence. Existing conservative malformed-root barrier retained.|
|EC06|Missing/stale/mismatched/unreviewed/uncovered evidence remains Unknown. Every chosen member must pass, including outerwear. Unknown optional outerwear does not poison an independently valid base-only candidate.|
|EC07|Today/tonight/tomorrow are current-wardrobe information; friends only in the approved ordinary outing scope; university/campus venue only for academic attendance. No weather/future availability/venue code is inferred.|
|EC08|Original hard constraints and P semantics retained. Colour/category/style contradictions block; unrequested formality is not fabricated; soft preferences/comfort are not new ranking semantics.|
|EC09|Natural and command wording in the revised general profile share binding/scope. Frozen original/wedding profiles keep declaration-only commands. All five pre-existing binding JSON objects remain equal.|
|EC10|One existing four-structure eligible result, exact unchanged score/tie rules, stored basis/limits; otherwise controlled no-result. No additional fashion/safety/completeness certification.|

Exact Allow supplies **only its applicable condition**. Occasion Allow does not
waive a requested formality Deny. Unrequested formality does not become an occasion
condition. Clear applicable Allow and attribute inference have different stored
bases (`explicit_declaration` / `attribute_inference`), rules and supporting facts.
Correct classic style is uncovered Unknown, not a universal unsuitable judgement.

There is no automatic garment classification/review promotion. Missing interview-only
collar, tailoring, structured shape or condition observations do not block everyday
appearance. The writer and review controls are unchanged. Users may reuse one truthful
current style review across these contexts instead of filling an event-tag grid.
Generic confirmation and high raw AI confidence do not establish reviewed evidence.

## 4. Independent matrix, ranking and preserved invariants

**73/73 approved scenarios match through actual authenticated recommendation API
calls on disposable databases.** The full labels, HTTP statuses and complete results
are in `backend-final-api-cases/` and `approved-matrix-execution.json`. Expectations
come from the frozen approved review contract, not production evaluator output.
The 10 invariant and eight browser groups are covered by linked checks below;
they are not added as 18 more API passes or an invented test count.

The **338 new backend checks** include 216 independent member truth-table
combinations across the three targets; nine code/context comparisons over all four
structures with both wordings; exact legacy/general transition checks; malformed
barriers and Deny precedence; six span/alias cases; eight rejected registry mutations;
three 100-snapshot preparation cases; five real strict-query exclusions; hard style/
category negatives; actual write rollback/snapshot/replay/logout checks; four
supplemental action negatives and a separate friends/time no-score-bonus check.
These checks overlap the matrix and final total; do not sum them again.

Exact Fraction weights remain **3/5 + 1/5 + 1/5**. No score component or request
term is added. In the independent blue four-garment fixture, all four supported
structures are enumerated; a one-piece alone scores 7/10 and the paired structures
score 4/5. Stable ordering selects `dress-A + outer-A`. Full per-candidate proofs,
weights/totals, compact/reference winner and public reconstruction agree. Forged
condition proofs are rejected. Natural versus command forms retain identical
numerical scores/winners; optional friends/timing adds no bonus.

ConfirmedGarmentQuery SQL, ownership/confirmation/availability checks, retrieval,
candidate stream, structural policy, numerical request/compatibility/preference
calculations and ranking/ties remain byte-identical. Real query negatives exercise
archived, unavailable, unconfirmed, foreign-owner and processing-owner mismatch.
The quota remains **100 non-archived entries**, separate from strict eligible snapshots.

Changing a review after ranking but before the locked writer yields WardrobeChanged
with no partial chat. A real INSERT-abort trigger rolls back chat/recommendation/
items/submission writes; same-key recovery and replay then succeed. Old stored
recommendations retain provenance/scores across profile reselection and new Deny.
Changing key-associated text conflicts. Copied-token rejection after logout remains
covered, as do the unchanged broader durable-auth/account tests.

Actual two-process app.main restart/replay uses a copy of the owned disposable
browser DB and the same child DB/secret/token across stops. The previously successful
campus record, even after a subsequent campus Deny, replays with identical stored
recommendation/proof/score. Both workers stop cleanly. This is restart/immutability
evidence, not installed-service, multi-worker or drain certification.

## 5. Existing-policy compatibility and final supported scope

`preserved-binding-subtrees.json` establishes equality of all five pre-existing
binding objects. Frozen wedding interpreter/request/evidence/policy, original NLP/
vocabulary/declarations, scoring, query, writer/history and durable authentication
retain bytes. Broader regression includes their existing tests without modifying
old oracles or labels. The general profile intentionally gains ordinary inference
where old campus/shopping/casual-outing commands previously needed Allow; tests
separately retain original/wedding-profile declaration-only outcomes.

| Context | Final general-profile scope |
|---|---|
|Ordinary academic attendance, shopping, casual outings|New approved appearance bindings with current evidence and exact existing declaration scopes.|
|Wedding|Existing W01–W05 guest convention/code limits, explicit overrides and reviewed inference preserved.|
|Date/Dinner|DT01–DT05 and DN01–DN05 preserved; friends/plain restaurant only in approved scopes.|
|University presentation|AP01–AP06 preserved: explicit domain/role; Campus Deny veto, no positive parent inheritance.|
|Job interview|IP01–IP06 preserved: explicit employment role/code and additional appearance observations; no Work Allow shortcut.|
|Graduation, hiking, beach, travel|Still inactive in the general profile; recognised forms return controlled unavailable. No regalia/activity/safety/comfort support.|
|Party and ordinary work commands|Existing delegated declaration-only rules; their natural-language examples remain unsupported. No new party/work appearance policy.|
|Standalone “I want something smart casual”, family dinner|Still unsupported. No unapproved paraphrase/suitability expansion.|
|General outfit/colour/style request|Original supported meanings and evidence gates preserved; bare casual outfit is still formality, not automatically style.|

Unknown modifiers, negation, multiple/alternative events, conflicting constraints,
unsupported colours/categories and unavailable codes do not become relaxed generic
requests. Safe failures explain missing context, inactive capability, insufficient
garment evidence, failed requirements or incomplete structure as applicable.

## 6. Executed verification and retained failures

| Check | Actual final result |
|---|---|
|Focused backend regression|**1878 passed, one deliberately deselected archived-source check, in 560.19s**, native exit 0. Includes all 338 new cases plus existing-context, original NLP, core ranking, persistence, quota, account and durable-logout scope.|
|Archived-source guard, separate final invocation|**1 passed in 2439.75s**, native exit 0 on the stable final production manifest. Together these are 1879 distinct passing backend checks across final invocations, not one 1879-pass invocation.|
|General profile, actual Chrome|**21/21 in 149.3s**: four new everyday journeys plus 17 unchanged Phase 1–3/shared/logout definitions.|
|Frozen wedding profile, actual Chrome|**10/10 in 43.9s**, unchanged wedding/shared/logout definitions.|
|TypeScript / scoped ESLint|Final native exit 0, including the corrected new browser locator source.|
|Production build|Native exit 0; separate retained build **J01DzS3LlBe8gYqbWXgwg**. Generated Next tsconfig/next-env/AGENTS changes restored to starting bytes.|
|Process restart/replay|Two ordinary app.main worker processes; copied-token/keyed replay survives clean stop/restart with identical stored result.|
|Integrity|All **1207 starting paths present: 1194 unchanged, exactly 13 approved existing-file advances** (10 production, three test/support). 223 other application paths unchanged; staging empty.|

Actual installed Chrome is **156.0.8078.48**, not bundled Chromium. The two final
browser arms are **31 executions with overlapping definitions**, not 31 distinct
cases. There is no new latest-release/Edge/Firefox or universal accessibility claim.

Browser services use ordinary app.main/Uvicorn and production Next with normal
same-origin proxy at 3100 → 3101, real register/login and fresh disposable SQLite
databases. Synthetic normally reviewed/confirmed uploads and development processing
are disclosed; VTOFF/VTON and development identity are off, child secrets generated
and unpublished. No real photo/account/wardrobe or model output is used.

New journeys verify one style review reused across four natural requests, command
Deny equivalence, missing-review guidance without interview requirements, explicit
formality/Deny, specialised/inactive contexts, complete 100-character names,
Save as outfit, VIS source preparation, history and stored provenance/score equality.
Result bounds fit 360/390/768/1280/1920px; history is also checked at the narrow
state. Native Chrome 200% uses settings zoom 2 and an isolated profile, DPR 2,
physical width 1440, CSS content width 711, CSS zoom 1 and visual scale 1. Keyboard
request submission and reused history search/opening pass. Captures/DOM bounds are
retained; they are not an expert typography/accessibility or fashion study.
An explicit frozen-B02 browser case additionally aborts style-review and garment-
style-save requests, verifies unchanged stored style/review, preserves the failed
style draft, checks Cancel without writing, and then successfully reviews/reuses
the truthful stored style. No wardrobe implementation or contract changes.
Visual inspection reviewed the complete 360px campus result and native-zoom history
viewport. The latter capture shows the top of history, not every result detail;
complete horizontal text/control bounds and native settings are independently
recorded in the browser collector. `visual-review.json` preserves this qualification.

All attempts remain under
[everyday_context_v1](../storage/verification/everyday_context_v1/):

- Initial focused run: **333 passed**. Initial broader run: **1,873 passed and one
  guard deselected**, overlapping intermediate coverage. Supplemental pure probes
  then exposed four non-ordinary action prefixes wrongly admitted as everyday
  contexts. The new everyday-only prefix guard fixes this without changing the
  five old policies. All four before mismatches and after passes remain; five
  supplemental backend cases bring final new coverage to 338.
- Initial browser arm: **19 passed / one failed**. The new generic alert selector
  also matched Next's route announcer. Scoping it to `#main-content` fixes this
  test ambiguity. The original new test, failure trace and source snapshots remain;
  a corrected 20-case arm passed. The explicit B02 review-preservation case was then
  added to directly cover style Cancel/failed-save behaviour; the final 21-case arm
  passes with no retries or extended deadlines. No production change was made for
  that locator failure or additional test.
- Final backend/guard source snapshots precede those **new browser-test-only**
  changes. All production/backend inputs remain exact. The locator diff and appended
  B02 case are explicitly reconciled and verified by final browser, TypeScript/lint.
  The wedding snapshot also lists this unused everyday test file; its actual frozen
  wedding/shared/logout definitions and production sources remain exact. Neither
  reference is falsely presented as identical new-test bytes.
- Initial TypeScript found a missing installed `typescript@5.9.3/lib/lib.dom.d.ts`;
  the next attempt exposed missing `lucide-react@1.18.0/dist/lucide-react.d.ts`.
  Both declaration files were restored from the exact existing offline npm content
  cache with verified SHA512 integrity. No version, lockfile, compiler setting or
  application source was changed; no package/model was downloaded or installed.
  A metadata-based offline npm-pack attempt first returned ENOTCACHED; direct
  verified content-cache access supplied the retained archive bytes. Repair records
  and failed TypeScript logs remain. Final types/lint/build pass.
- Initial evidence finalisation hit a helper assertion that hashed newline-normalised
  text instead of the archived Windows source bytes for the unused wedding browser
  reference. The helper now compares the retained raw-byte hash and separately
  verifies text equivalence. Its initial source/result and identical partial audit
  outputs remain. No production source, test outcome or historical oracle changed.

Existing uv no-project, Starlette/httpx deprecation, Playwright colour and Git
line-ending warnings remain. Native child codes determine results. Phase 3's
original manifest-read failure and separate successful guard remain unchanged;
this phase does not relabel it. Current manifests stayed stable during final
certification. No old assertion was weakened or failed evaluation erased.

## 7. Bounded work, source continuity and operational limits

For each new binding, the 100-snapshot/two-condition fixture observes **400
primary/independent resolutions plus four winner/public resolutions, five request
compilations**. No resolution/config work occurs between candidate callbacks.
This one-piece population enumerates 100 candidates; it is a call-path test, not
a new worst-mix capacity benchmark. The unchanged four-structure enumeration and
retained capacity evidence remain authoritative. No candidate-space expansion,
per-candidate NLP/DB/model/network/file reads or cross-owner mutable cache is added.

No concrete timing concern required a comparison. Test durations are functional
execution durations under concurrent local verification activity, not latency/NFR
acceptance. There is no full J-16 rerun, new capacity population, lower quota,
speculative optimisation or claim that NFR-02 has become accepted.

All 848 Phase 3 indexed entries reconcile: **835 retain hashes and exactly 13 live
approved source/test references advance**, with their originals and index preserved.
All 16 Phase 4 review deliverables retain bytes, including the unexecuted proposed
matrix. Raw historical reports/labels/manifests/archived sources are not rewritten.
New phase snapshots, exact manifest revisions, patch, before copies, integrity and
deliverables index distinguish Phase 5 from the existing uncommitted workspace.

All owned browser backends log Application shutdown complete / Finished server
process with native exit 0; owned frontends/browsers stop and ports 3100/3101 are
released. Disposable DBs/profiles remain at ledger paths. No manual or unrelated
process was stopped/restarted. These ordinary stops do not diagnose or erase the
earlier large-run shutdown issue or certify mixed workers, drain, forced termination,
installed-service or deployment recovery.

## 8. Activation, requirement status and disposition

The existing **process-only** opt-in remains:

```powershell
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
```

It requires Assistant and suitability enabled. The intended compact demonstration
also selects `compact_exhaustive` and `experimental_compatibility_decision_v1`;
Homepage remains separately enabled/random. Context default remains `disabled`.
This phase does not change host/User/Machine environment variables, the manual
application DB/media/secret, running processes or deployed settings. No migration
is introduced. Activating/restarting the manual app is a separate owner action.

The [unchanged requirement authority](../storage/verification/everyday_context_v1/requirement-baseline.json)
pins all original 155 rows. **144 Verified / 2 Partial / 9 Unverified / 0 Blocked**
remains the traceability baseline. RN-13 and FR-VIS-01 are Partial; FR-DW-03/04/06/07,
FR-VIS-09 and NFR-01/02/03/11 remain Unverified. Broader formal/exercise/general-colour
capability, original fixed-dataset NLP accuracy and real fashion appropriateness
are not certified by this approved synthetic-rule implementation.

Remaining decisions include lawful real CV/segmentation/attribute/VTOFF/VTON evidence,
bounded RN-13/VTON supported scope, final SQLite/PostgreSQL architecture, formal
NFR baseline/history maximum/images/resources/statistics, actual TLS/deployment/data/
retention/cutover/recovery, and canonical ai-services layout/assertion reconciliation.
No teammate execution is disproved by missing local evidence and no shared acceptance
is inferred. **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.**

**PASS WITH LIMITATIONS.** The approved three-context increment is implemented and
verified for the documented local appearance contract. Whole-FYP acceptance remains
NOT READY. No graduation, travel, party, work, family-dinner, specialised activity,
standalone soft-preference policy, model admission, private-data operation, migration,
default activation, manual-service restart, staging/commit/reset, deployment, full
benchmark or next increment begins. **Wait for owner review.**
