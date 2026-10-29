# Context Framework Phase 1: generalised context foundations and wedding equivalence

2026-10-24, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
The approved reusable framework is implemented under a separate opt-in profile.
Only the already approved wedding-equivalent suitability binding is active in
that profile. Other taxonomy entries are recognised but unavailable. The frozen
legacy and wedding implementations remain available. This is no deployment or
whole-FYP acceptance, and no additional situation policy is approved here.

**155-requirement baseline remains 144 Verified / 2 Partial / 9 Unverified /
0 Blocked. RN-13 remains Partial. NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.**

## 1. Authority and exact file scope

The owner accepted the architecture review as the proposed design, then expressly
answered “R/shared backend and API owners approve this exact scope” and “Shared
frontend owners approve this exact scope”. [ownership-approval.json](../storage/verification/general_context_phase1/ownership-approval.json)
records the responses and every production path. Scope is section 10A of the
accepted review. Section 10B, new field-review storage, model admission, new
situation policies, migrations, private data and deployment remain excluded.

Exactly **14 existing production files change and nine production files are
added**. The sole existing test/support edit is `integration_source_guard.py`.
No other existing test, frozen label, oracle, report or manifest is edited.

| Owner | Existing production paths, all relative to project root |
|---|---|
|R selection/runtime|`backend/app/application/recommendation/contextual_selection.py`; `backend/app/infrastructure/workflow_runtime.py` (existing paired construction retained, documented for both opt-ins)|
|R engine/metadata|`backend/app/application/recommendation/compact_assistant_scorer.py`; `backend/app/application/recommendation/request_candidate_engine.py`; `backend/app/domain/value_objects/assistant_execution_context.py`|
|R mandatory integration|`backend/app/application/recommendation/compact_mandatory_verifier.py`; `backend/app/application/recommendation/compact_exhaustive_scorer.py`; `backend/app/application/recommendation/scoring_eligibility_gate.py`|
|R/shared service/API|`backend/app/application/recommendation/outfit_assistant_service.py`; `backend/app/api/recommendation_routes.py`|
|Shared frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`|

| New production path | Responsibility |
|---|---|
|`backend/app/domain/value_objects/general_context_request.py`|R: immutable frame, slots, original spans, taxonomy value and five-field adapter|
|`backend/app/application/nlp/general_context_interpreter.py`|R: shared compositional interpretation and semantic configuration validation|
|`backend/app/application/nlp/config/context_grammar.v1.json`|R: versioned frame/role/code/venue/time/goal vocabulary|
|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`|R: shared semantic IDs, phrases, expressed activity/venue and projection; no fashion policy|
|`backend/app/application/recommendation/config/context_policy_registry.v1.json`|R: approved binding, assumptions, evidence contract and declarative W01–W05 references|
|`backend/app/application/recommendation/context_policy_registry.py`|R: strict registry and activation-envelope validation|
|`backend/app/application/recommendation/context_constraint_compiler.py`|R: active binding and required-field compilation|
|`backend/app/application/recommendation/context_evidence_resolver.py`|R: current reviewed-style/declaration read adapter|
|`backend/app/application/recommendation/general_context_evaluator.py`|R: generic evaluation, immutable bundle specification and stored explanation|

New evidence/support consists of the two named backend test modules, separate
general-context labels/source fixtures, one new browser test/configuration and
this phase's helpers/artifacts. [source-transition.json](../storage/verification/general_context_phase1/source-transition.json)
contains every exact before/after/addition hash. The phase patch and original
copies distinguish these changes from the earlier uncommitted working tree.

## 2. Implemented architecture

One compositional interpreter handles shared going/attending/having/meeting/
wanting/command frames against semantic vocabulary. It does not query garments,
import recommendation policies or decide suitability. The taxonomy remains at
the approved configuration path but contains semantic data only; the policy
registry consumes that same validated taxonomy. This preserves the original NLP
dependency rule instead of weakening its existing test.

The immutable frame represents situation, activity, role, venue/environment,
separate dress code and requested formality, hard style/colour/category fields,
soft preference language, goals, temporal literals, companions and unhandled
states. Known, Unspecified, Ambiguous, Conflicting and Unsupported are semantic
states, not scores. Original-text spans are checked against the actual input;
scalar slots reject fabricated multiple values or missing source evidence.

The parser supports the stated bounded examples without a mandatory “Suggest”
prefix. Unknown meaningful words, negation, alternatives and multiple/conflicting
contexts reject safely. An unrepresentable request keeps the existing
UnsupportedRequest contract and does not persist a partial frame/result. This
is bounded English interpretation, not unrestricted natural-language coverage.

Tomorrow/tonight/today are retained as timing information. They add no score,
forecast, scheduling, future-availability or unstated dress-code claim. Soft
language and comfort goals are represented but have no new ranking/suitability
semantics: a wedding request requiring them is unavailable, not silently reduced
to a hard colour/style or a generic outfit.

The registry separates semantic recognition from approved policy availability,
required context, evidence, assumptions and provenance. It rejects duplicate or
unknown keys/references, malformed schemas/operators, unresolved projections and
unapproved bindings. Configuration is size/count bounded. No expressions,
dynamic policy classes, imports or arbitrary executable policy are accepted.
Phase 1 deliberately limits activation to the wedding binding. The current
predicate catalogue is reviewed-style equality with all-member aggregation;
this is a reusable foundation, not a claim that every future context predicate
or evidence channel is already implemented.

`EvaluatorSpecification` pins registry, taxonomy and grammar hashes. The DI bridge
preserves this specification instead of discarding constructor configuration.
Primary, independent and public checks construct separate approved evaluators
from the same validated bundle. A mismatched/forged bundle fails closed. Before
persisting an explanation, the service also verifies its registry matches the
bundle used for the selected winner.

## 3. Supported versus unavailable situations

| Interpreted situation | General-profile policy in this increment |
|---|---|
|Wedding, guest or unspecified role, unspecified/casual/smart-casual code|Available within unchanged W01–W05 limits; all garment evidence/gates must still pass|
|Wedding bride/groom/party role, formal/black-tie code|Recognised; unavailable. No guest or casual fallback|
|Job interview, date, beach visit, university presentation, graduation, hiking, dinner, travel|Recognised; unavailable. No new suitability binding or declaration inheritance|
|Explicit venue, soft preference or comfort requirement on a wedding|Represented; unavailable because the binding does not evaluate these conditions|
|Unknown modifiers, negation, alternatives or competing contexts|Controlled UnsupportedRequest; no requirement deletion|
|Ordinary non-context request such as classic outfit|Delegates to the existing interpreter and declared suitability policy|

Beach explicitly records the beach venue without inventing swimming; university
presentation records university without inventing presenter status. Hiking gains
no safety/equipment capability. Recognised date/dinner/travel requests in the
general profile are intentionally unavailable, including command wording; the
legacy and wedding profiles retain their original declared-policy behaviour.
This avoids an alias/wording route around the new profile's activation boundary.

## 4. Evidence, declarations and wedding equivalence

Capability admission occurs before garment overrides. An explicit Allow cannot
enable formal/specialised/inactive capabilities. For each applicable condition
and every outfit member, including outerwear, the resolver applies:

1. Identifiable explicit Deny -> Fail, including Deny with Allow.
2. Malformed/conflicting authoritative evidence -> Unknown; no inference bypass.
3. Clean applicable Allow -> Pass for that exact condition, distinctly recorded.
4. Genuinely absent declarations -> approved current owner-reviewed singleton
   style/category equality may infer Pass.
5. Missing, stale, malformed, mismatched or insufficient review -> Unknown.

Fail precedes Unknown in aggregation; every mandatory condition must pass before
scoring. Occasion Allow never waives a requested formality/code condition.
The existing v1 style review and optional wedding namespace are read through an
adapter; there is no new per-occasion tagging requirement, backfill, confidence
cutoff, model-trust promotion or field-review writer. Explicit Allow and reviewed
inference retain separate bases, rule references, current review and observed
style evidence in immutable stored provenance. The original legacy evaluator's
conflict semantics and original declaration files remain untouched.

All **22 frozen wedding labels** retain status, reason, five-field projection,
effective role assumption and policy availability. The differential artifact
retains both representations. Six combinations of code/outerwear denial cover
all four structures and compare every candidate's eligibility, condition proof,
exact component/total scores and deterministic winner against the frozen wedding
evaluator. Reference ranking agrees too. Independent labelled member tables cover
all 96 code/style/review/decision combinations. Stale/malformed/missing evidence,
formality, Deny and outerwear boundaries remain explicit.

No unresolved correctness discrepancy remains in these tested comparisons.
Representation differences are intentional: the general frame retains original
spans and separate dress-code/formality slots; assumptions are compiled from the
approved binding. For wedding score compatibility only, the approved code is
projected to the existing formality gate/score field, without asserting that the
user separately stated formality. Temporal wedding phrasing gains the explicitly
approved timing-information treatment; the frozen wedding profile does not.
Generic provenance/version identifiers are new and disclosed, never presented
as byte-identical wedding-profile metadata.

## 5. Engine, persistence and protected boundaries

Exact Fraction arithmetic and 3/5 + 1/5 + 1/5 weights remain unchanged. There is
no extra R term or contextual bonus. The four structures, candidate stream,
completion/count checks, compatibility conventions and deterministic tie order
are preserved. Reviewed attributes are hard-gate evidence, never extra preference
evidence. Saved preference normalisation/snapshots are unchanged.

ConfirmedGarmentQuery ownership/availability/confirmed joins, snapshot projection,
100 non-archived garment quota, atomic writer and history reader are unchanged.
Disposable API tests verify current-review changes between ranking and commit
produce WardrobeChanged with no partial chat. Old wedding results and new general
results replay with their stored provenance/scores across profile/composition
reselection. Fresh results respect Deny; replay does not reinterpret old results.
Owner/auth boundaries, durable logout, normal shared flows and existing atomic
failure tests pass. No new API route or authentication inventory expansion occurs.
Homepage remains the existing random no-chat selection, outside context scoring.

[protected-boundaries.json](../storage/verification/general_context_phase1/protected-boundaries.json)
checks 36 source/configuration boundaries against their retained bytes, including
the frozen wedding interpreter/request/evidence/evaluator/policy, original NLP,
numerical facts/streams/scorers, declarations, query, persistence and durable auth.

## 6. Bounded work and verification results

Context compilation and member evidence resolution occur outside ordinary
candidate enumeration. The 100-snapshot/two-condition call-count test observes
400 primary/independent member resolutions plus four winning-member public/gate
resolutions, and five separate request compilations. No resolver/configuration
work is performed per candidate in the ordinary hot loop. Audit reconstruction
is a separate test path. There is no remote call, model inference or database
read in that loop. No speculative cache optimisation or changed-path timing
collector was needed. Functional test durations below are not latency acceptance.

| Check | Actual final result |
|---|---|
|Focused backend regression|**807 passed in 327.04s**, native exit 0; includes **177 new framework cases** and unchanged wedding, original NLP/dependency, compact/reference, source guards, routing, preferences, quota, persistence, shared account and durable logout checks|
|General profile, actual Chrome|**11/11 passed in 44.7s**: three new context flows plus five durable-logout and three shared integration cases|
|Preserved wedding profile, actual Chrome|**10/10 passed in 41.8s**: two unchanged wedding cases plus the same eight shared/logout cases|
|TypeScript/scoped lint|Native exit 0 on the four approved frontend files and new browser/configuration sources|
|Production build|Native exit 0; separate retained build **1wtksGvsPfvlNdE_FEehP**; generated tsconfig/next-env/AGENTS bytes restored|
|Source/staging/whitespace|Exact transition and 36 protected paths pass; git diff --check/new-source whitespace/Python AST pass; staging empty|

Chrome is the actual installed product **156.0.8078.48**, not bundled Chromium.
The two final browser arms are **21 executions with overlapping test definitions**,
not 21 independent cases. They use real register/login, ordinary app.main/Uvicorn,
production Next and its normal same-origin proxy, with separate disposable
databases and process-only configuration. Synthetic reviewed/confirmed uploads
are used; development processing is disclosed, VTOFF/VTON are off, development
identity is off and generated child secrets are not published. No private photo,
account or database is inspected. This is not real-model verification.

New context explanations fit at 360/390/768/1280/1920px in Chrome, with full valid
100-character garment names. Keyboard request/search/open, Save as outfit and
VIS source preparation pass. Native 200% uses an isolated actual Chrome profile:
zoom 2, DPR 2, physical width 1440, CSS content width 711, CSS zoom 1 and visual
scale 1. Result/history text and controls fit. Stored scores/provenance remain
equal. No new Firefox/Edge or universal accessibility certification is claimed;
the retained J-20/J-21 evidence and limitations remain unchanged.

## 7. Retained attempts, source continuity and operational limits

All attempts remain under [general_context_phase1](../storage/verification/general_context_phase1/).
The first targeted run had 15 failures/156 passes: 14 new tests wrongly treated
occasion Allow as satisfying the separate code condition, and one reused a parser
cache across changed same-ID snapshots. Correcting those new test fixtures gave
171 passes. No old oracle or production suitability rule was changed for them.

The first regression command named a nonexistent test filename and executed no
tests. The corrected 801-case invocation retained 800 passes and the real new
NLP-layer dependency failure. Production was corrected to separate semantic
taxonomy loading from policy binding; the existing isolation assertion was not
weakened. The focused correction passed 219 cases. Scalar/venue/taxonomy guards
expanded the framework tests; an 806-case regression then passed. Final review
added the selected-versus-explained bundle guard and its fault test; the final
807-case run and verified browser arms cover those final bytes. Intermediate
passes overlap; none is added to the final total.

Initial and final browser arms all retain their logs, test/config copies and
reports. The final arms additionally pin the actual executed production/test
source hashes. Earlier successes are not counted again. Existing uv no-project,
Starlette/httpx and Playwright colour warnings remain; native child return codes
determine results. No retries, extended deadlines or weakened conditions turn
failures into passes.

All **1,170 starting paths** remain: **1,155 unchanged, exactly 15 approved
existing-file advances** (14 production and the guard). All 346 entries in the
accepted wedding index reconcile: **335 retain their original hashes; 11 live
source/guard references advance through the new approved transition**. Their
original bytes and old index are retained. No old raw output, archived source,
report, label or manifest is repinned. New source-transition revisions within
this increment are retained separately, rather than deleting earlier attempts.

Owned verification backends stop normally with exit 0; owned frontends/browsers
stop and ports 3100/3101 are released. Synthetic databases remain at ledger paths.
The user's manual services/data/configuration are not restarted or changed by
these launchers. This does not resolve J-16's historical larger-run shutdown
timeout or certify multi-worker/service-manager/in-flight/forced-stop recovery.

## 8. Activation, remaining approvals and disposition

The new process-only opt-in is:

```powershell
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
```

It requires the existing Assistant and suitability flags enabled. The intended
compact/exact demonstration also keeps execution_engine=compact_exhaustive,
scoring_profile=experimental_compatibility_decision_v1 and the existing Homepage
flag. `disabled` remains the default; `wedding_guest_v1` retains its old path.
This report does not restart the manual application or activate either profile
globally. Keep the existing DB/media/secret when the owner separately restarts
their manual services; this increment adds no migration.

No further section-10A ownership approval is outstanding for this executed scope.
**Date/dinner is ready for a separate policy-design/approval review, not automatic
implementation.** Before activation, approve exact declaration crosswalks and
Deny scope, role/code/venue assumptions, predicates/evidence and separate labels.
Current style evidence can be reused where a bounded appearance rule is approved;
it does not prove safety, comfort, weather protection or independent fashion
appropriateness. Extra fields/model-derived admission still need the separate
shared/T evidence/storage scope. No additional per-event evaluator/scorer is
recommended.

The unchanged 155-row baseline is linked by hash in requirement-baseline.json.
RN-13 and FR-VIS-01 remain Partial; FR-DW-03/04/06/07, FR-VIS-09 and NFR-01/02/03/11
remain Unverified. Bounded suitability/VTON scope decisions, lawful real-model
evidence transfer, final SQLite/PostgreSQL architecture, formal NFR baseline/history
maximum, HTTPS/deployment/data/cutover and canonical ai-services reconciliation
remain open. The new prototype framework closes none of those decisions.

**PASS WITH LIMITATIONS.** The approved Phase 1 foundations and bounded wedding
equivalence are implemented and verified. Whole-FYP acceptance remains NOT READY;
NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. No additional situation policy,
model/provider/migration/default change, private-data operation, deployment,
full performance/capacity benchmark or next policy increment begins. Wait for
owner review.
