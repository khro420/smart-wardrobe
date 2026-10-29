# Context Framework Phase 3: professional and academic implementation verification

2026-10-25, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
The approved academic and bounded interview bindings are implemented through
`general_context_v1`, including the approved reusable appearance review contract.
Graduation remains inactive. No manual service, private database or global default
is changed. **155 requirements remain 144 Verified / 2 Partial / 9 Unverified /
0 Blocked. RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.**
Whole-FYP acceptance remains NOT READY.

## 1. Authority and exact transition

The owner expressly approved the academic semantics, bounded interview/evidence
contract, and **A and B with the named test scope**. [ownership-approval.json](../storage/verification/professional_academic_v1/ownership-approval.json)
retains all three answers and the exact paths. No further ownership consent is inferred.
The policy proposal, its independent labels and prior reports/evaluations retain bytes.

Exactly **18 existing production files change and two production modules are added**:

| Area / owner | Existing files |
|---|---|
|R NLP|`backend/app/application/nlp/general_context_interpreter.py`; `backend/app/application/nlp/config/context_grammar.v1.json`|
|R policy/compilation|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`; `backend/app/application/recommendation/config/context_policy_registry.v1.json`; `backend/app/application/recommendation/context_policy_registry.py`; `backend/app/application/recommendation/context_constraint_compiler.py`|
|R evidence/explanation|`backend/app/application/recommendation/context_evidence_resolver.py`; `backend/app/application/recommendation/general_context_evaluator.py`|
|Shared/T contract/projection|`backend/app/shared_contracts/confirmed_garment_snapshot.py`; `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`|
|Shared/T review/API|`backend/app/domain/value_objects/requests.py`; `backend/app/api/wardrobe_routes.py`; `backend/app/application/wardrobe/wardrobe_service.py`|
|Shared frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`; `frontend/app/wardrobe/page.tsx`|

Added: `backend/app/domain/value_objects/general_context_evidence.py` and
`backend/app/application/wardrobe/attribute_evidence_review.py`. These are the approved
shared observation projection/writer, not new situation-specific evaluators.

Only three existing test/support files advance: `backend/tests/integration_source_guard.py`,
`test_general_context.py` and `test_general_context_equivalence.py`. The latter two
update the explicit bundle version and capability list. G02/G05 remain unavailable
because their role/code context is missing. Seven named new test/fixture/browser files
provide coverage. Old W/DT/DN labels, original tests/oracles/manifests and raw results
are not repinned. Before copies, the phase patch and [source-transition.json](../storage/verification/professional_academic_v1/source-transition.json)
identify this increment within the earlier uncommitted tree. No staging, commit or reset.

## 2. Interpretation and admitted policy scope

Grammar/taxonomy/registry are version 1.2.0; original NLP/vocabulary and frozen wedding
components remain unchanged. The shared parser adds outfit questions, explicit
presenting/being-interviewed/conducting actions and interviewer role. It resolves
contained neutral interview/presentation matches only through approved domain refinement;
two independent events, negation, conflicts and meaningful unknown modifiers still reject.

Bare interviews and presentations retain inactive neutral domains. A stated company
does not establish employment/candidate/office/indoors. Explicit university venue can
establish academic context; presenting establishes presenter, but have/my/attend alone
does not. As an attendee/interviewer is accepted. No fixed Suggest command is required.
Timing is information only, with no forecast or future availability.

| Binding | Actual supported contract |
|---|---|
|`university_presentation_appearance_v1` / policy 1.0.0|Explicit university domain and presenter/attendee role. Unspecified-code presenter uses disclosed provisional smart-casual appearance; attendee permits casual/smart casual. Explicit casual or smart casual requires matching reviewed style. Missing role/domain or formal requirement remains unavailable.|
|`job_interview_appearance_v1` / policy 1.0.0|Explicit employment domain, candidate/interviewer role and explicit smart-casual code/formality. Every member also needs the approved reviewed construction fact and dated clean/intact observation. Smart-casual style alone cannot pass. Unspecified/casual/formal/specialised interview policies remain unavailable or unrepresentable.|

Interview feature table: upper collared neckline; lower tailored cut; one-piece
structured shape; outerwear structured shape OR tailored cut. Missing/false/uncovered
positive features stay Unknown, not a universal fashion judgement. A valid current-bound
needs_attention observation fails the interview condition gate. Every member, including
outerwear, must pass before scoring. Business casual is not silently rewritten to smart
casual. Graduate/guest/regalia/formal graduation capabilities are not introduced.

The seven original desired examples are not all selectable requests: missing role/code
and neutral domain cases return controlled unavailable outcomes. The graduation ceremony
phrase remains unsupported under the frozen scope. Supported positive examples include
“I'm presenting my project at university tomorrow” and “I'm attending a job interview
as a candidate; the dress code is smart casual,” with the required garment evidence.

## 3. Evidence, declarations and UI

`appearance_evidence_v1` stores only the approved owner observations, current category/
source-media binding, server timestamp and schema/source metadata. Construction facts
are strict true/false/unknown; condition is clean_intact/needs_attention/unknown. The
immutable snapshot defaults Missing, rejects malformed/mismatched mirrors and participates
in complete locked snapshot revalidation. No SQL migration, model-derived admission,
automatic backfill or new per-event tag matrix is added.

The existing authenticated review route accepts a strict separate appearance action.
It keeps old style/wedding payloads, enforces owner/revision/transaction boundaries,
and preserves unrelated values. Generic PATCH cannot write the namespace; confirmation
strips untrusted processing metadata. Category changes invalidate dependent appearance
observations; source changes make them stale. Style staleness remains independent.
The UI shows definitions/date, optional controls, Cancel and Withdraw. Failed saves
preserve drafts. Withdraw removes only appearance observations, not style/wedding evidence.

[Appearance review guide](APPEARANCE_OBSERVATION_REVIEW_GUIDE.md) provides eight synthetic
text vignettes. Contract/type/state behaviour and the actual review controls are verified;
there is **no visual review study, independent professional/fashion validation or AI
calibration claim**. Tailoring/structure remain owner design judgements. Condition is a
dated observation, not continuous physical verification: the UI requires checking current
condition/fit before wearing. Footwear/accessory completeness is not established.

Work Deny vetoes admitted employment interviews; Campus Deny vetoes admitted university
presentations. Broad Work/Campus Allows supply no child-situation Pass. Exact requested
formality Allow is distinguishable from inferred contextual evidence and cannot waive
another condition. Applicable valid Deny wins even alongside Allow/malformed metadata;
otherwise malformed authoritative collections block inference. Old declaration conflict
semantics remain untouched. Unknown `rec:v1` interview/presentation targets remain malformed.
Unrequested formality and unrelated Date/Dinner/Wedding scopes are not silently inherited.

New 1.2.0 result/history proof shows role/spans, supplied code versus provisional note,
negative scope, supporting declarations, exact rule/bundle and actual additional observations
with dates. It does not label all interview evidence merely as reviewed style. Missing
context and missing garment facts have separate explanations. Old formats still render.

## 4. Preserved engine and executed evidence

Exact Fraction 60/20/20 arithmetic, compatibility, preference handling, four structures,
complete enumeration, stable ranking, quota 100, strict eligibility SQL, atomic writer,
history/replay, durable auth and Homepage selection remain unchanged. Three existing
binding JSON subtrees compare equal. Newly generated general-profile proofs have the new
bundle hashes; stored old proofs are never reinterpreted or claimed byte-identical to new ones.

| Check | Final actual result |
|---|---|
|Backend regression|**1540 passed / one manifest-read failure in 696.12s**, native exit 1; includes **464 new cases** plus the prior 1,077-case scope with approved metadata/capability adaptations. The failed guard is separately rechecked below; no single 1,541-pass run is claimed.|
|Final archived-source guard|**1 passed in 759.74s**, native exit 0, against stable final sources/manifest. Together the runs cover **1,541 distinct passing checks**; the earlier failure remains retained.|
|Approved matrix|**76/76 in-scope scenarios**: 74 recommendation API scenarios, one review API scenario and one explicitly identified pure 100-snapshot preparation scenario. Five graduation assessment rows remain unimplemented, not relabelled as passes.|
|Other new backend coverage|360 independent interview/academic truth-table cases; every-candidate four-structure exact score/reference/public comparisons; rejected registry mutations; stale/model-source boundaries; real owner/revision/strict payload/trigger rollback checks. All overlap the 464 total.|
|Independent per-role feature probes|12/12 pure one-hot observations match the approved upper/lower/one-piece/outerwear feature table, including the outerwear OR. These are separate pure observations, not extra API or pytest cases.|
|General profile / actual Chrome|**17/17 in 58.8s**: three new professional/academic journeys plus unchanged Date/Dinner/general/shared/logout definitions.|
|Frozen wedding profile / actual Chrome|**10/10 in 21.2s**, unchanged definitions. These 27 executions have overlapping cases, not 27 distinct new tests.|
|Restart/replay|Actual two app.main processes, copied disposable browser DB, same child secret and copied bearer: authenticated 200 replay, exact score/proof preservation after restart, clean stops.|
|Frontend checks|Final TypeScript/scoped ESLint/production build exit 0. Separate retained build **bCl9UUWj_U4RpIXT1P6lX**; generated Next files retained as copies and original bytes restored.|
|Integrity|All **1,195 starting paths remain: 1,174 unchanged, exactly 21 approved changes**; two approved production additions. 33 protected sources and 388 other application paths exact. Staging empty.|

Actual installed Chrome is **156.0.8078.48**, not bundled Chromium. Production Next and
ordinary app.main/Uvicorn use the normal proxy, real register/login and disposable
synthetic databases; development identity off, development processing disclosed,
VTOFF/VTON off, child secrets unpublished. There is no private photo/account/database
inspection, real inference or new latest-release/three-browser certification.

New result/history explanations retain full 100-character names and fit tested
360/390/768/1280/1920 widths. Native Chrome zoom is settings=2, DPR=2, physical width=1440,
CSS width=711, CSS zoom=1 and visual scale=1. Keyboard request/history, saved-outfit and
VIS source preparation remain usable. Screenshots/DOM metrics remain; this is no universal
accessibility or subjective typography claim.

The broad backend run records starting frontend hashes separately from the final two
UI-only corrections. All executed backend production/test bytes remain exact. The new
phase manifest was rewritten while the archived guard read it, causing a transient empty
JSON read: this was an orchestration error, not an application or archived-source defect.
The helper now replaces manifests atomically. The failed guard is rerun alone against
stable final sources/manifest; final TypeScript/lint/build/browser and terminal transition
audit cover the UI patch. This does not turn the initial invocation into a 1,541-pass run.

Each new binding's 100-snapshot/two-condition counter check observes 400 primary/independent
resolutions plus four winning-member gate resolutions and five compilations, outside
ordinary candidate enumeration. Compound nodes are bounded/validated; no per-candidate
NLP, database/config/model call. Internal predicate work is greater than style-only rules;
no unchanged-time guarantee is inferred. No full NFR matrix/capacity study or new capacity
population is run. Functional durations are not formal NFR acceptance.

## 5. Attempts, evidence continuity and limitations

All attempts are retained under [professional_academic_v1](../storage/verification/professional_academic_v1/).
The initial 464-case run had six failures/458 passes because the new shared role grammar
missed the article an. Correcting the parser, without changing labels, gave 464 passes.
The first general browser arm retained 15 passes/two failures: the old missing-context
journey expected the truthful “understood/no generic substitution” explanation, and a
new exact-label locator could not find the condition control's aggregate accessible name.
The final UI wording preserves that truthful explanation and identifies missing context;
the new condition selector has an explicit accessible name. New alert selection is scoped
to the application's paragraph rather than Next's route announcer. No deadline, retry,
eligibility or oracle is weakened. Earlier counts overlap and are not pooled.

Final source transitions, raw outputs, labels and exact execution snapshots remain.
All 520 Phase 2 indexed entries reconcile: 505 unchanged,
15 approved live references advance with their original bytes retained.
All 12 Phase 3 design deliverables remain exact. Existing uv no-project, Starlette/httpx,
Playwright colour and Git line-ending warnings are retained; native child codes determine
checks. The broad-suite canonical ai-services issue is not erased or claimed resolved.
An initial pure role-feature helper imported a pytest-dependent fixture from plain Python
and stopped before observations; its original source remains. Self-contained synthetic
snapshot construction resolved that helper dependency without changing production rules.

Owned backends log normal shutdown/exit 0, owned frontends/browsers stop and ports 3100/3101
are released. Disposable DBs remain at ledger paths. No unrelated/manual process is stopped.
These ordinary functional stops do not diagnose J-16's larger-run timeout or certify
multi-worker, in-flight drain, forced termination or installed-service recovery.

## 6. Disposition and remaining work

The process-only opt-in remains `SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE=general_context_v1`,
with Assistant/suitability enabled and the existing compact/exact demonstration flags.
Default remains disabled. This phase does not restart the manual application, migrate
private data, alter stored accounts or enable deployment settings.

[requirement-baseline.json](../storage/verification/professional_academic_v1/requirement-baseline.json)
pins all 155 original rows with no status advances. RN-13/FR-VIS-01 remain Partial;
FR-DW-03/04/06/07, FR-VIS-09 and NFR-01/02/03/11 remain Unverified. Bounded RN-13/VTON
scope, real-model evidence, final SQLite/PostgreSQL architecture, formal NFR baseline/
history maximum, TLS/deployment/data/cutover and canonical ai-services decisions remain.
Other contexts/specialised/formal/comfort/weather capabilities need their own approved rules
and evidence. Graduation is not activated by primitive reuse.

**PASS WITH LIMITATIONS.** The approved A+B implementation and local verification are
complete for owner review. Whole-FYP acceptance remains NOT READY; NFR-02 remains OPEN /
NOT FORMALLY ACCEPTED. No next policy increment, model run, default change, private-data
operation, deployment or full benchmark starts. Wait for owner review.
