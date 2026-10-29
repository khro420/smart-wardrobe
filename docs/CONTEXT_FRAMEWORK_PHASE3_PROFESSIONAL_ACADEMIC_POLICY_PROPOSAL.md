# Context Framework Phase 3: professional and academic policy approval proposal

2026-10-25, Asia/Kuala_Lumpur. **Design complete; version 1.0.0; NOT IMPLEMENTED.**
Phase 2 is owner-accepted PASS WITH LIMITATIONS. This review preserves the shared
`general_context_v1` architecture and all accepted Wedding/Date/Dinner behaviour.
No source, policy, default, historical data or old report is changed. No new
situation is activated. **155 requirements remain 144 Verified / 2 Partial /
9 Unverified / 0 Blocked. RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY
ACCEPTED. Whole-FYP acceptance remains NOT READY.**

**Recommendation:** current evidence is sufficient to propose a narrowly disclosed
academic **appearance** binding, subject to role/crosswalk/policy approval. It is
**insufficient for interview inference from style alone**. Interview implementation
needs the separately approved reusable evidence contract below, its shared/T review
scope and policy acceptance. Graduation remains assessment only. Do not enable a
professional policy merely because an event name is understood.

## 1. Inspected implementation and retained evidence

Read the current interpreter/grammar/taxonomy/frame, registry/compiler/resolver,
evaluator/explanations, original declaration parser/policy, style review writer,
snapshot/query adapter, wardrobe API/payload validation, compact mandatory facts,
generic persistence revalidation and frontend types/messages. Also inspected
attribute-head suggestion/confidence projection and retained Phase 2 verification.

All **520 accepted Phase 2 indexed files match**. Read-only capture covers **1,194
starting Git-visible paths**. Sixteen pure parser/capability observations retrieve
no garments and open no database. They are not API/browser tests or fresh execution
of the accepted 1,077/14/10 regression evidence. New review artifacts are under
[context_phase3_policy_design_20261025](../storage/verification/context_phase3_policy_design_20261025/).
No server, model, regression suite or benchmark runs in this review.

| Existing evidence | Actual supported meaning / limit |
|---|---|
|Current singleton owner-reviewed style, category-bound|Reusable observation for an expressly approved style predicate. It does not establish professional appropriateness.|
|Confirmed category and structural role|Owner-reviewed/confirmed classification and outfit membership; a long-sleeve top is not necessarily a shirt, trousers are not necessarily tailored, outerwear is not necessarily a blazer.|
|Exact owner `rec:v1` declarations|Eight occasions including work/campus and two formalities. These are scoped owner decisions, not calibrated predictions. No valid interview/presentation target exists in this namespace.|
|Formality support|Only casual and smart_casual. Formal remains unavailable. A style named formal is not implemented formal-dress-code capability. Business casual is not an approved synonym for smart casual.|
|Fit/material/pattern/colour descriptions|Some fields exist/edit, but the current contextual snapshot has no corresponding trusted per-field attestation contract. Fabric quality, wearer fit, condition and professional readiness cannot be derived from them.|
|AI head values/confidence and generic confirmation|Suggestions retain some confidence/model information; detector confidence or raw head probability is not evidence of field calibration or owner review. Generic garment confirmation does not attest all fields.|

The current resolver only supports reviewed-style predicates; it has no trustworthy
construction-detail or condition observation. The current review payload supports
style review and optional wedding choice only. The registry deliberately admits
exactly three bindings. Adding event words or JSON entries alone cannot implement
the proposed policies safely.

### Actual current interpretation of the seven requested examples

| Input | Current implementation, observed | Proposed semantic handling |
|---|---|---|
|I have a job interview tomorrow.|Supported interpretation; policy unavailable.|Employment interview; time tomorrow; role/code unspecified. Still unavailable until required context supplied.|
|What should I wear to an interview?|UnsupportedRequest.|Neutral interview intent; employment domain and role unresolved. Recognise without requiring Suggest; no automatic job policy.|
|I'm attending an interview at a company.|UnsupportedRequest.|Neutral interview with stated company venue. Company alone does not prove employment domain or candidate role.|
|I have a presentation at university.|UnsupportedRequest.|Academic presentation; university explicit; presenter/attendee unresolved.|
|I'm presenting my project tomorrow.|UnsupportedRequest.|Neutral presentation; presenter follows explicit verb; university remains unknown.|
|Suggest an outfit for my university presentation.|Supported interpretation; policy unavailable.|Academic context; possessive my does not establish presenter role.|
|I'm attending a graduation ceremony.|UnsupportedRequest; ceremony is not currently consumed.|Desired later recognition, with policy unavailable. Graduation wording changes are assessment only, outside recommended implementation scope.|

Current exact presenter/candidate phrases can already be partly represented, but
no academic/interview binding is active. Interviewer role is not in the grammar.
Wedding, Date and Dinner controls in the sixteen observations remain available.

## 2. Interpretation contract proposed for approval

Retain the same compositional interpreter and immutable frame. Proposed grammar,
taxonomy and registry minor versions are **1.2.0**, with independently versioned
new bindings and exact bundle hashes. No change to original v1 NLP/vocabulary,
legacy declaration policy or frozen wedding interpreter/configuration.

- Resolve explicit job/employment interview to `professional.job_interview`.
  Bare interview resolves to a new **inactive** `interview.unspecified`; do not
  silently choose employment over admissions/media/other interview meanings.
- Resolve university presentation, or presentation with explicit university venue,
  to `academic.presentation`. Bare presenting/project presentation resolves to a
  new **inactive** `presentation.unspecified` until academic context is established.
  Account ownership/student status does not supply that context.
- Add shared outfit-question and action frames: What should I wear to…, I'm
  presenting…, I'm being interviewed for a job…, I'm conducting a job interview….
  Passive being interviewed establishes candidate; conducting establishes interviewer;
  presenting establishes presenter; in the audience/as an attendee establishes attendee.
  I'm interviewing is role-ambiguous. Have, attend and my alone imply no role.
- Permit explicit company/office for an employment interview, university for an
  academic presentation, or unspecified venue when the event phrase itself establishes
  the domain. Retain the stated term: company is not automatically office/indoors.
  Unsupported venue/environment requirements stay unavailable or unrepresentable.
- Keep dress code separate from requested formality. Formal/black tie are recognised
  unavailable; initially business casual/business formal and specialised uniform terms
  are unsupported, without synonym substitution. Preserve hard colour/category/style
  requirements and existing soft-language limits.
- Tomorrow/today/tonight retain the approved timing-information contract: current
  wardrobe, no forecast, scheduling or future-availability claim. No role or code is
  inferred from timing. Multiple events, conflicting roles/codes, negation and unknown
  meaningful modifiers must not be stripped to obtain a result.

**Necessary overlap rule:** adding interview/presentation aliases would currently
double-match their longer phrases. Resolve contained matches only through an explicit
same-event/refinement relation: job interview refines the contained neutral interview;
university presentation refines contained presentation. Prefer the complete supported
span with its domain evidence. Two independent events still reject. This is a shared
span-resolution change with regression risk, not an event-specific interpreter or
permission to ignore competing events.

No follow-up chat, silent automatic resubmission or completed-request mutation is
proposed. Missing context returns a controlled explanation and a suggested edited
request for a new chat. No candidate, presenter or dress-code convention is assumed
in the recommended first increment. Optional future conventions need separate labels
and approval; they are not hidden defaults here.

## 3. Interview binding: proposed IP01–IP06

Proposed binding **`job_interview_appearance_v1`**, policy
**`job-interview-appearance-1.0.0`**. This is a conditional non-formal appearance
heuristic, not certification of employer requirements or professional suitability.

Required context: explicit employment/job domain, explicit candidate or interviewer
role, and **explicit smart-casual dress code or requested formality**. Both admitted
roles use the same limited appearance predicate; this does not claim all interview
roles have identical real-world requirements. Venue may be unspecified/company/office.

| Rule | Proposed decision |
|---|---|
|IP01: complete admitted context|Require every member's current reviewed smart-casual style **and** the role-specific observed construction detail **and** recorded clean/intact condition observation in section 5, after authoritative negative checks. All must pass.|
|IP02: role/domain/code missing or ambiguous|PolicyUnavailable / required_context_missing (or inactive neutral context). Do not assume candidate or smart casual.|
|IP03: explicit casual code|PolicyUnavailable: globally understood casual is not an approved casual-interview policy in this first increment. This is not a claim that casual interviews are inappropriate.|
|IP04: formal/black tie or specialised requirement|Unavailable, even with owner Allow. Business-casual wording initially remains UnsupportedRequest; no implicit smart-casual rewrite.|
|IP05: inadequate observations|Missing/stale/malformed/uncovered required evidence -> Unknown; InsufficientEvidence if no candidate establishes all mandatory conditions. Reviewed smart casual alone is insufficient.|
|IP06: applicable negative evidence|Applicable Work Deny or explicitly requested formality Deny -> Fail. A recorded needs_attention condition also fails under the proposed negative condition predicate. Deny is never overridden by another Allow/inference.|

No inference about fabric quality, fit on the wearer, gender, actual cleanliness now,
footwear/accessory completeness, employer expectations or a venue dress code. Positive
construction observations are prototype policy inputs, not universal fashion facts.
Absent/false construction features yield Unknown, not a blanket judgement that an
alternative design is unsuitable. The policy requires separately approved additional
evidence; it must not ship enabled with an invented default for that evidence.

Example admitted future input: **“I'm attending a job interview as a candidate;
the dress code is smart casual.”** The shorter original request is understood but
cannot select this policy until role/code are supplied. This limitation is deliberate
and must be visible before describing interview support to users.

## 4. Academic binding: proposed AP01–AP06

Proposed binding **`university_presentation_appearance_v1`**, policy
**`university-presentation-appearance-1.0.0`**. Scope is an ordinary non-specialised
university presentation appearance suggestion, not professional/assessment compliance.

Required context: university academic presentation established, and explicit presenter
or audience-attendee role. Unspecified venue is allowed only when university context
is in the event phrase; explicitly different venues/online/specialist environments
are not silently inherited. Student/project/my do not establish presenter status.

| Rule | Proposed decision |
|---|---|
|AP01: presenter, code unspecified|Permit current reviewed smart-casual style as a **disclosed provisional appearance guideline**. It is not an inferred dress code or requested formality.|
|AP02: audience attendee, code unspecified|Permit current reviewed casual OR smart-casual style with the same limited provisional disclosure. Do not copy wedding guest assumptions.|
|AP03: explicit casual, either role|Require current reviewed casual style for the contextual appearance condition, plus the explicitly requested formality condition. No hierarchy.|
|AP04: explicit smart casual, either role|Require current reviewed smart-casual style, plus the explicitly requested formality condition.|
|AP05: missing role/domain, unsupported code/condition|Required context missing or formal/black-tie capability unavailable -> PolicyUnavailable. Negation/conflicts/unrepresented meaningful terms remain UnsupportedRequest.|
|AP06: evidence/negatives|Applicable Campus Deny or requested formality Deny -> Fail. Otherwise missing/stale/malformed/uncovered current review -> Unknown. No positive Campus inheritance.|

This reuses only the accepted style/category review. It does not establish that
clothing is clean, fits, meets a lecturer's rubric or has professional refinement.
If supervisor/user expectations require those stronger claims, **do not activate this
style-only academic binding**: extend its required evidence explicitly first. The
additional interview observations, if later stored, do not silently change AP rules.

The presenter guideline preferring smart-casual evidence is a proposed normative
prototype rule needing approval, not an empirical finding about all presentations.
An explicit casual request may be supported with matching evidence; unspecified
presenter/casual evidence stays Unknown rather than being declared inappropriate.

## 5. Reusable evidence proposal and minimal review

**Academic:** current reusable singleton style review plus confirmed category suffice
only for section 4's bounded appearance rule. **Interview:** they do not suffice.
Propose two reusable observation groups, not per-situation suitability tags:

| Proposed field group | Exact canonical values / meaning |
|---|---|
|`construction_features`|Three independently reviewed facts: `collared_neckline`, `tailored_cut`, `structured_shape`, each true/false/unknown. These are owner-observed design descriptions; no field is auto-derived from a category/style/model suggestion. Unknown differs from false; false is not an automatic fashion Fail.|
|`condition_observation`|`clean_intact`, `needs_attention`, or `unknown`, explicitly recorded by the owner at a timestamp. clean_intact means “I observed this garment as clean and without visible damage at this review”; it is not an assertion about current/future physical condition, fabric quality, wearer fit or comfort.|

Proposed review definitions: collared_neckline means the owner can identify a collar
at the neckline; tailored_cut means the owner identifies deliberate shaping through
construction such as darts/panels/defined waist shaping; structured_shape means the
owner identifies construction intended to hold a defined outline rather than only
drape. These latter two are **owner judgements**, not calibrated measurements or
quality claims. Uncertain owners select unknown. A review guide with lawful labelled
examples and shared/T agreement on these definitions is a prerequisite for B; until
that is accepted, do not claim the additional fields are independently reliable.

IP01's proposed per-role appearance predicate:

| Structural role | Additional positive fact required, beside reviewed smart-casual style and clean_intact observation |
|---|---|
|Upper|collared_neckline=true|
|Lower|tailored_cut=true|
|One-piece|structured_shape=true|
|Outerwear|structured_shape=true OR tailored_cut=true|

This is a small, deliberately restricted **positive heuristic catalogue**, not an
exhaustive professional dress taxonomy. It excludes alternatives by Unknown. There
is no shorts/skirts/dresses/gender/colour stereotype and no category-only tailored
or collar inference. Policy applicability and factual review remain separate.

Proposed evidence contract **`owner_appearance_observations_v1`**, separate JSON
namespace **`appearance_evidence_v1`**; do not alter or duplicate the existing v1 style
source. Retain canonical values, source=owner_review, review timestamp, value/dependency
binding, evidence revision and per-field semantic state. Bind observations to current
category and source-media identity; relevant field/category/media changes invalidate
their dependencies. Keep v1 style/category staleness checks independently authoritative.
Malformed collections, contradictory mirror values or forged provenance are Unknown.

Condition is a **dated owner observation**, valid only as recorded evidence until
withdrawn/changed; no arbitrary numeric expiry is chosen and no guarantee of physical
freshness is made. Show the date and require the user to check current condition before
wearing. **This point-in-time contract needs explicit owner/supervisor acceptance.**
If genuinely current physical-condition assurance is required, a fresh session/request
confirmation contract must be separately designed; do not quietly treat stored review
as continuous verification or introduce a hidden time threshold.

Offer the few fields only when reviewing garments needed for enabled interview rules,
with the image, current values and individual confirmation. Reuse unchanged reviews
across contexts; no mandatory occasion grid or re-review for each event. Show AI output
as suggestions only; high raw confidence cannot mark a field owner-reviewed. No
automatic backfill or model admission. Batch review and at-upload controls are outside
the recommended first scope; ordinary wardrobe editing is enough for this proposal.

The JSON approach proposes no SQL migration/provider change. It still requires shared/T
storage/contract/UI approval, reserved-namespace protection, authenticated revision-bound
writes, rollback and current snapshot projection. No real database is opened here.

### Reusable predicate contract

Keep old equality/set predicates unchanged. The proposed additional allowlist is
`reviewed_observation_equals(field, canonical_value)`, `all(children)` and
`any(children)`, with only the named construction/condition fields and strict
boolean/enumeration types. Compile the explicit role branch once per request;
do not add one evaluator per role. Negative-scope lookup is separately compiled
from the approved crosswalk and reduced before positive predicates. No model
confidence, free text, Python expression or arbitrary callable is a predicate.
Propose depth <=3, fan-out <=4 and <=16 atomic predicates per context condition;
validate these bounds, references, source contracts and complete required facts
at startup. The existing reviewed-style reader supplies style without duplication.
Missing/untrusted atoms remain Unknown; `any` may pass only on a genuinely admitted
positive atom, and `all` needs every required atom. No malformed declaration is
hidden inside an OR. These are proposed implementation limits, not measured results.

Academic-only approval means a fourth binding, with interview still inactive;
approval of B plus its verified evidence contract permits the fifth binding.
The loader must enforce the exact approved bundle, not accept an arbitrary number
of policies or enable an interview binding while its evidence adapter is missing.

## 6. Exact declaration crosswalk and decision order

**Proposed applicability, NOT current accepted declaration semantics:**

| Existing declaration | Employment interview | University presentation |
|---|---|---|
|Work Deny|Negative veto for either admitted role, wherever an admitted job interview occurs.|No automatic applicability from an academic event.|
|Work Allow|May be reported as broad work permission, but supplies **no interview Pass** and waives no evidence/constraint.|No inherited permission.|
|Campus Deny|No applicability merely from a job interview; the initial interview binding does not admit a university venue.|Negative veto for either academic role, including lexical university-presentation wording.|
|Campus Allow|No inherited interview permission.|Supplies **no presentation Pass**; required style/role/code rules remain.|
|Explicitly requested casual/smart_casual formality Deny|Veto for that requested condition, when the context capability is admitted.|Same.|
|Exact requested formality Allow|Explicit positive for that formality condition only. Does not replace the separate interview/academic appearance predicate.|Same.|
|Unrequested formality, Date/Dinner/Wedding choices|No automatic scope/positive transfer.|Same.|
|`rec:v1:occasion:interview:…` or `…:presentation:…`|Currently malformed; remains malformed. No silently extended v1 grammar or reinterpretation.|Same.|

The Work/Campus **negative** crosswalk is an explicit policy choice to respect a broad
restriction on a narrower admitted context. It is not inferred from string similarity.
If shared owners/supervisor do not accept that interpretation, leave the affected
binding unavailable until the intended scope is resolved. Do not ignore Deny or make
users add a new tag to regain the restriction. No new per-event override writer or
direct interview/presentation Allow namespace is proposed in the first increment.

After request-level capability admission, for every member:

1. Inspect all applicable negative scopes; any identifiable valid Deny -> Fail,
   including coexisting Allow or malformed companion metadata.
2. Otherwise malformed/conflicting authoritative declaration collections block
   inference as Unknown, retaining the accepted conservative malformed barrier.
3. A clean requested-formality Allow may pass that exact condition, distinctly
   `explicit_declaration`. Parent Allows are recorded, not promoted to child facts.
4. The new contextual condition requires its reviewed predicates; inferred positives
   are `attribute_inference`. Missing/uncovered facts -> Unknown; IP negative condition
   observation -> Fail. Any scoped explicit positive cannot erase another condition.
5. Fail precedes Unknown; every member including outerwear must pass all mandatory
   conditions before scoring. Capability unavailability cannot be cured by a tag.

AP unspecified-code guidelines do **not** manufacture a requested formality condition.
Consequently an unrequested formality declaration is not silently made a veto, just
as in the accepted Date/Dinner contract. An owner seeking a broad Campus restriction
uses the applicable Campus Deny. This precise distinction needs approval, not a
post-hoc change to the original declaration evaluator's conflict semantics.

## 7. Explanations and controlled outcomes

Retain current top-level HTTP/outcome meanings; add typed summary fields/reasons,
not new success states or a new chat flow. A missing role/code is PolicyUnavailable;
admitted policy with unresolved garment evidence is InsufficientEvidence; mandatory
contradictions give NoMatchingCandidates. Known unsupported codes remain unavailable;
unrepresentable modifiers remain UnsupportedRequest. List missing context separately
from missing garment observations. No generic-outfit fallback.

Proposed examples:

- **Missing interview context:** “I understood a job interview, but your role and
  dress code are unspecified. This prototype does not choose them for you. Start a
  new chat with your role and any stated dress code.”
- **Insufficient interview evidence:** “Reviewed smart-casual style alone does not
  establish this interview appearance rule. Some garments need construction or dated
  condition observations. Correct existing style labels need not be changed.”
- **Interview selection:** “For the candidate role and smart-casual code you stated,
  this is a provisional appearance suggestion based on the listed reviewed style,
  construction details and condition observations dated [actual dates]. Confirm the
  employer's requirements and current condition/fit; shoes/accessories are not assessed.”
- **Academic presenter, no code:** “You said you are presenting at university. With
  no dress code supplied, this provisional suggestion uses reviewed smart-casual
  appearance. It does not establish a course requirement or infer your dress code.”
- **Academic attendee, no code:** same disclosure, using the casual/smart-casual guideline.
- **Broad restriction:** “No complete outfit passed the applicable Work/Campus
  restrictions and this context's evidence rules.” Identify the actual applicable
  scope in stored proof; never suggest overriding a Deny to obtain a result.

Persist actual role source spans, explicit versus assumed values (assumptions empty
for roles), supplied code versus provisional guideline, policy/bundle hashes, exact
negative scopes considered and each member's reviewed observations/basis. A formality
Allow must not make an inferred occasion appear explicitly approved. Display the
actual new observations; a generic “inferred from style” label would be incomplete
for interview rules. Old 1.0.0/1.1.0 and wedding explanations must still render exactly
within their accepted contracts; history/replay never recomputes old explanations.

## 8. Graduation feasibility: separate assessment only

Graduation is already a recognised inactive taxonomy entry, but the ceremony phrase
and graduating verb need separately approved interpretation coverage. No graduation
lexicon/binding activation is included in the recommended Phase 3 implementation.

Guest, graduate and official roles differ; attending does not establish guest, while
graduating would establish graduate if its grammar were approved. Invitation rules,
regalia, under-gown constraints, school requirements, venue/weather and footwear are
not available from current reviewed style/category or the proposed construction facts.
Neither Campus Allow, wedding guest heuristics, academic presenter rules nor interview
rules establish those requirements. Campus negative scope for graduation also remains
unresolved rather than automatically copied from presentation.

A later **explicit non-formal guest** appearance binding may reuse these primitives
after its own role/code/scope/predicate approval. Graduate/official/regalia or formal
completion cannot be claimed from this proposal. **Graduation remains unavailable;
no implementation readiness is implied.**

## 9. Independent proposed verification matrix

[Complete 81-case JSON](../storage/verification/context_phase3_policy_design_20261025/proposed-acceptance-matrix.json)
and [CSV](../storage/verification/context_phase3_policy_design_20261025/proposed-acceptance-matrix.csv)
are separately author-labelled **PROPOSED / NOT EXECUTED / PENDING APPROVAL**. They
are not relabelled Phase 1/2 results or an NLP/fashion accuracy rate. Outcomes assume
the exact recommended rules and future approved implementation; graduation rows are
assessment targets only, outside that implementation increment.

| Group | Proposed coverage |
|---|---|
|N01–N16|All seven desired inputs, natural commands/questions, neutral domain/role ambiguity, explicit role grammar, university context, timing and company information. N07 is graduation assessment only.|
|I01–I15|Interview additional evidence, style-only insufficiency, feature false/missing, dated condition, staleness/mirror conflicts, untrusted AI, code/role admission and formal/specialised limitations.|
|A01–A10|Presenter/attendee provisional rules, exact explicit casual/smart-casual, missing/stale review, no formality hierarchy or outdoor requirement deletion.|
|D01–D16|Exact negative crosswalk, Work/Campus Allow non-inheritance, Deny across paraphrases, requested versus unrequested formality, malformed reserved tags and scope isolation.|
|G01–G12|Strict owner/confirmed/available eligibility, missing structure, all four structures, outerwear, complete candidate/score proof, hard colour/category and conflicting/negated requests.|
|P01–P08|Old/new immutable replay, rank-to-commit evidence mutation, exact keyed text, visible explanations, narrow/zoom/keyboard/save/source regression, bounded 100-snapshot preparation and authenticated revision/rollback evidence.|
|R01–R04|Graduation guest/graduate/formal/scope failures; assessment only.|

Fixtures use synthetic owned/available/confirmed blue garments and no preferences.
For a single admitted dress: R=1, C=1/2, P=0 -> exact **7/10**. Four fully evidenced
top-A/bottom-A/dress-A/outer-A garments give four candidates, singleton 7/10 and
paired 4/5; stable role/ID ordering selects dress-A+outer-A. Check every candidate's
conditions/scores and primary/independent/public agreement, not just the final outfit.
Reference/compact comparisons must preserve existing arithmetic and tie rules.

Expand these labels into independently reduced truth tables and metamorphic checks:
an unrelated attribute or temporal/venue detail adds no score; missing evidence cannot
improve admission; changing a phrase cannot evade the same negative scope. Freeze
new labels before implementation. Preserve and rerun the relevant frozen W/DT/DN
oracles and existing source-transition tests, without editing historical labels.

## 10. Exact proposed file/ownership boundary

**Future scope only. No listed production or test file is edited in this review.**
Approve A and B separately; academic A can proceed without B only if its weaker
appearance claim is explicitly accepted. Interview activation requires both A and B.

### A. Shared bindings and interpretation (12 existing production files)

| Owner | Exact paths | Necessary proposed changes |
|---|---|---|
|R NLP|`backend/app/application/nlp/general_context_interpreter.py`; `backend/app/application/nlp/config/context_grammar.v1.json`|Shared question/action frames, explicit role grammar/interviewer, strict span overlap and domain refinement.|
|R taxonomy/registry|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`; `backend/app/application/recommendation/config/context_policy_registry.v1.json`; `backend/app/application/recommendation/context_policy_registry.py`|Versioned inactive neutral concepts and two new approved bindings, negative scope maps and bounded compound evidence predicates. Preserve W/DT/DN subtrees.|
|R compilation/evidence|`backend/app/application/recommendation/context_constraint_compiler.py`; `backend/app/application/recommendation/context_evidence_resolver.py`; `backend/app/application/recommendation/general_context_evaluator.py`|Role/code/domain/facet admission; exact parent-negative/field-positive separation; reusable all/any reviewed-fact evaluation, complete stored proof and safe missing-context summary.|
|Shared frontend/R|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`|Typed additional proof, role/code/evidence guidance, binding-specific provisional disclosures and old-format preservation.|

Use the existing frame, evaluator specification/DI, mandatory preparations, score
projection and generic repository. No new interpreter/evaluator/scorer class, profile
name, service, route, execution-engine or numerical source change is proposed.
Inactive neutral concepts authorise no outfit rules. No graduation changes in A.

### B. Reusable appearance observations (6 further existing files, 2 new modules)

| Owner | Exact paths | Necessary proposed changes |
|---|---|---|
|Shared/T domain/query|New `backend/app/domain/value_objects/general_context_evidence.py`; existing `backend/app/shared_contracts/confirmed_garment_snapshot.py`; `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`|Strict immutable per-field observations and projection; SQL ownership/confirmed/status predicates unchanged.|
|Shared/T review/API|New `backend/app/application/wardrobe/attribute_evidence_review.py`; existing `backend/app/domain/value_objects/requests.py`; `backend/app/api/wardrobe_routes.py`; `backend/app/application/wardrobe/wardrobe_service.py`|Versioned optional appearance payload on existing authenticated contextual-review route, dedicated namespace/projection, revision checks, validation, dependency invalidation and atomic mirror writes. Old style/wedding payloads keep their path.|
|Shared/T frontend|Existing `frontend/app/wardrobe/page.tsx` and A's `frontend/lib/api.ts`|Few reusable image/value review controls, source/date display and clear-withdraw semantics. No mandatory per-event matrix.|

Preserve old `contextual_garment_evidence.py`, `contextual_review.py`, original
declaration parser/policy, query interface and automatic processing. New namespace
must remain inaccessible to generic attribute PATCH/processing promotion. Do not
loosen the current manual-attribute allowlist to let callers write trusted metadata.
Use a strict review action, with server-owned source/timestamp/revision metadata.

The writer currently compares complete current snapshots under its write lock; added
evidence must participate in that comparison and stored selected-result proof. New
projection must default Missing for absent namespace, retain old fields/semantics and
not reinterpret old histories. Prove this through actual disposable DB tests. No writer/
history edit is currently proposed; return for named approval if a concrete patch
shows one is required. No SQL migration, provider/auth/model/config edit is proposed.

### Necessary test/support scope after approval

- Existing `backend/tests/integration_source_guard.py`: exact next transition only;
  do not repin earlier manifests.
- Existing `backend/tests/test_general_context.py`: update the explicit Phase 2
  registry-version assertion for the approved new bundle. G02/G05 still lack roles
  and remain unavailable; do not relabel them as positive just because bindings exist.
- Existing `backend/tests/test_general_context_equivalence.py`: extend the exact
  capabilities assertion to the approved active subset (academic only versus both).
  Keep missing-context/unavailable loops and frozen wedding differentials intact.
- New `backend/tests/test_professional_academic_context.py`,
  `backend/tests/test_professional_academic_equivalence.py`,
  `backend/tests/fixtures/professional_academic_labels.v1.json`,
  `backend/tests/fixtures/professional_academic_sources.v1.json`,
  `frontend/tests/phase5f/professional-academic-context.spec.ts`,
  `frontend/playwright.professional-academic-context.config.ts`.
- If B is approved: new `backend/tests/test_attribute_evidence_review.py` for the
  shared contract/write path. Reuse existing browser definitions unchanged where
  their requests still lack role/code. Name any other old caller/test adaptation
  before editing; none is implicitly authorised here.

No edits to runtime/profile defaults, Assistant persistence service, Homepage, auth,
quota, account, extraction review, models or deployment assets are proposed. At-upload
or batch review would require additional named files and approval, outside B.

## 11. Performance, integration and requirements

Compile only active request predicates outside enumeration. Prepare per-member
atomic facts once in each independent preparation; reduce them to the existing
mandatory occasion condition plus explicitly requested formality (K<=2). Roles,
observations and scope vetoes add no R terms, new score bonuses or P changes.

With N<=100 and bounded predicate atoms A, preparation is O(N*K*A), not O(candidates*A).
There are at most 400 top-level primary/independent member-condition resolutions
for two conditions, but their internal work is greater than the current style-only
resolver. Account separately for public winner verification and explanation; do not
claim unchanged CPU/time merely from a similar call count. No per-candidate NLP,
JSON/config load, database/model call, full explanation or owner-global eligibility
cache. No quota reduction or new capacity population is warranted by this design.

Risks needing focused checks: alias overlap/domain deletion; role assumptions;
negative scope bypass; tuple/boolean malformed handling; field staleness/mirror
conflicts; new snapshot equality/commit races; untouched old binding reduction;
explicit code versus provisional score projection; longer UI explanations at narrow
width/native zoom; configuration count/schema/activation failure and proof completeness.
Use static/call-count assertions first, then only a justified changed-path timing
delta on retained inputs if required. No full J-16 NFR matrix or performance promise.

RN-13 is strengthened only for approved complete context/evidence contracts. Event
recognition alone closes no requirement. RN-17 arithmetic, RN-28 output validity,
RN-27 original labels/80% criterion and immutable histories remain separate unchanged
obligations. Author-labelled rules do not establish independent professional/fashion
quality. Real-model evidence, bounded suitability/VTON scope, final SQLite/PostgreSQL,
formal NFR baseline/history maximum, HTTPS/deployment/data/cutover and canonical
ai-services reconciliation remain open. Counts do not advance in this design review.

## 12. Concrete approval decisions and implementation recommendation

1. **R/policy owner/supervisor:** approve AP01–AP06, explicit role/domain semantics,
   disclosed presenter/attendee provisional appearance conventions and the exact
   negative-only Work/Campus crosswalk. If the academic appearance claim is too weak,
   require additional evidence rather than presenting it as professional validation.
2. **R/shared/T/supervisor:** approve IP01–IP06 only together with the two reusable
   observation groups, role-specific predicate table and explicitly dated condition
   contract. Otherwise keep interview unavailable. No style-only interview fallback.
3. **Named shared owners:** approve A's exact production/test paths; additionally B's
   contract/query/storage/API/wardrobe paths and new evidence tests if interview is
   selected. Approve role/code/domain/alias semantics, versioned bundles and labels.
   There is no private-data write/migration, default activation or deployment authority.

**Recommended sequence:** approve/review the academic binding and crosswalk first;
implement it only after approval. In parallel or later, approve and verify the small
shared appearance-review contract before enabling interview inference. Each step uses
the same framework. Do not ship an interview binding with absent facts treated as
true, broaden professional claims to save review effort, or automatically include
graduation. This is a dependency order, not authorisation for either implementation.

**Disposition: policy design ready for approval, with an unresolved interview evidence
decision.** Current evidence supports a conditional academic appearance increment;
professional/interview inference needs the proposed approved additions. No policy,
production source, private account/database, model, migration, global default or
deployment changes in this review. Wait for the user's concrete design/scope approval.
