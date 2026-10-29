# Context Framework Phase 2: Date and Dinner policy approval package

2026-10-25, Asia/Kuala_Lumpur. **Proposal version 1.0.0; ready for policy review;
NOT IMPLEMENTED OR ACTIVATED.** Phase 1 is owner-closed PASS WITH LIMITATIONS on
its retained 807 backend / 11 general-profile / 10 wedding-profile checks. Its
shared architecture is accepted and will be reused. No production source,
configuration, old evidence, service, database or model changes in this review.
The 155-row baseline remains **144 Verified / 2 Partial / 9 Unverified / 0 Blocked**;
RN-13 remains Partial and NFR-02 OPEN / NOT FORMALLY ACCEPTED.

## 1. Inspected implementation and smallest extension

Inspected the actual working-tree interpreter/frame, taxonomy, registry/loader,
compiler, evidence resolver, evaluator/explanation, original declaration parser
and policy, reviewed-style projection/review binding, frontend messages and
affected Phase 1 assertions. All **438 accepted Phase 1 indexed entries match**.
Fourteen pure parser/capability observations retrieve no garments or generate
outfits. Four of the five requested phrases already parse; all date/dinner
policies remain unavailable. “I'm going out for dinner tonight” currently rejects
the unhandled word “out”. This needs one shared going-out grammar variant.

The existing taxonomy already has `social.date` and `social.meal`. Phase 2 would
bind them to **date** and **dinner**, respectively, through the same
`general_context_v1` interpreter, registry, compiler, resolver, evaluator and
existing scorer. There will be no additional interpreter/service/evaluator/scorer
per situation. No new garment fields, review namespace, model trust or migration
is needed for this proposed appearance-only scope.

## 2. Exact proposed policies

These are proposed prototype **positive appearance heuristics**, not established
facts about all dates, dinners, formality, comfort or fashion quality. Unqualified
requests would receive a disclosed provisional everyday appearance guideline;
the system would not claim their actual dress code is known.

| Binding | Supported meaning | Required / optional context | Explicit assumptions and limits |
|---|---|---|---|
|`date_appearance_v1`, policy `date-appearance-1.0.0`|A personal/social date expressed as an outfit request or first-person situation; excludes calendar-date questions|One date situation; role unspecified. Time and supported hard fields optional. Venue unspecified or explicitly plain restaurant. No companions in this first date binding.|No gender, partner, romantic setting, participant role, venue or dress code inferred. Unspecified code uses only the provisional appearance guideline below. Group dates and specialised venue requirements remain unavailable.|
|`dinner_appearance_v1`, policy `dinner-appearance-1.0.0`|An ordinary dinner/meal, including meeting friends or going out for dinner|One dinner situation; role unspecified. Optional companions=friends, stated time, supported hard fields, and unspecified/plain restaurant venue.|Friends and going out imply no dress code, upscale setting or outdoor environment. No restaurant is assumed when omitted. Business/ceremonial/uniform/staff-role requirements are outside this binding.|

For each member, a clean scoped owner Allow may establish that condition first;
otherwise the following rule applies only to genuinely absent declarations and
current admitted review evidence:

| Rule | Explicit requested code/formality | Approved positive reviewed-style predicate | Mandatory conditions |
|---|---|---|---|
|DT01 / DN01|Both unspecified|Singleton canonical style is **casual OR smart casual**|Exact date/dinner occasion; no invented formality condition|
|DT02 / DN02|Casual|Singleton canonical style is **casual**|Exact occasion AND casual formality/code gate|
|DT03 / DN03|Smart casual|Singleton canonical style is **smart casual**|Exact occasion AND smart_casual formality/code gate|
|DT04 / DN04|Admitted request, but no sufficient applicable evidence|**Unknown**|Missing/stale/unreviewed/malformed/multiple/uncovered styles cannot pass|
|DT05 / DN05|Formal, black tie, unsupported role/venue/activity or additional requirement|**PolicyUnavailable**, before garment selection|Owner Allow cannot enable an unsupported capability|

“Casual dinner” is an explicit casual code, whereas “dinner” alone is not.
Dress code and explicitly requested formality remain separate frame slots. Their
existing compatible five-field projection is retained; if both are supplied and
conflict, reject rather than choose one. Casual and smart casual have no hierarchy.
A reviewed classic/vintage/other style outside the positive set stays **Unknown**,
including when the review itself is valid. It is not evidence that the garment is
unsuitable. These limited predicates may therefore produce no result for some
otherwise reasonable wardrobes; richer inference requires separate evidence.

### Stated companions and venue: a distinct approval decision

Propose allowing **friends for dinner only**, and an explicitly stated **plain
restaurant** for date or dinner, as applicability/context information. They supply
no garment evidence, inferred code, extra R term or preference. Preserve their
source spans and show them in the explanation. All other currently recognised
venues (hotel, office, university, indoors/outdoors) remain unavailable for these
bindings. An unrepresented modifier such as “upscale”, “outdoor protection” or a
venue-specific uniform must not be consumed as harmless description. No claim
about compliance with an unknown restaurant dress code is made.

## 3. Declaration crosswalk and reusable evidence predicates

| Context / condition | Sole applicable authoritative source | No inheritance |
|---|---|---|
|Date occasion, every supported paraphrase|`rec:v1:occasion:date:allow` / `deny`|No dinner, party, casual_outing, work or wedding positive/negative remapping|
|Dinner occasion, every supported paraphrase|`rec:v1:occasion:dinner:allow` / `deny`|No date, party, work or wedding remapping|
|Explicit casual formality/code gate|`rec:v1:formality:casual:allow` / `deny`|No smart_casual substitution|
|Explicit smart-casual formality/code gate|`rec:v1:formality:smart_casual:allow` / `deny`|No casual substitution|
|Existing wedding|Existing wedding namespace and W01–W05, unchanged|Date/dinner tags never alter wedding decisions|

No new date/dinner override namespace or per-event review controls are proposed.
Keep original `owner-declarations-1.0.0`, tag grammar/data and legacy evaluator
unchanged. The contextual resolver must inspect the existing parsed atomic
declarations: for it, valid Allow+Deny means **Fail** because Deny wins. Original
legacy evaluation of that conflict remains **Unknown**, which already blocks.

Only explicitly requested formality/code creates a formality condition. An
unrequested formality declaration does not become an occasion declaration or
silently choose a code. For example, smart-casual Deny is not automatically
dinner Deny when no code is requested. Exact occasion Deny always blocks that
occasion regardless of wording or the reviewed style. This scope distinction
is part of the policy approval, not an inferred broad negative crosswalk.

Reusable predicates and decision order, shared by both new bindings:

1. Admit the entire requested capability/facets before garment overrides.
2. Extract valid decisions for the exact field/value above. Identifiable Deny
   gives Fail even alongside Allow or malformed reserved metadata.
3. Otherwise retain the existing conservative malformed-authoritative-collection
   and malformed contextual-namespace barrier: Unknown, no inference or Allow
   bypass. A malformed style review alone prevents inference; a clean independent
   explicit Allow need not assert that style was reviewed.
4. Clean exact Allow gives Pass for that condition only. Record
   `explicit_declaration`, exact target/decision and original policy version.
5. If that declaration is genuinely absent, require a current owner review:
   known canonical singleton style, matching current category/value and valid
   existing review metadata. Evaluate `reviewed_style_in` (or existing equality)
   using the table above; record `attribute_inference`, rule and observed review.
6. Missing, stale, malformed or uncovered positive evidence gives Unknown.
   Aggregate **Fail before Unknown**, with every applicable condition/member
   required to Pass, including outerwear. Existing hard colour/category/style
   contradictions and structural rules still give their existing failures.

No raw AI probability, detector score, material/fit guess or “fashionable” label
becomes suitability evidence. Current reviews can be reused for both situations;
users need not tag every garment for either event. Explicit tags remain optional
owner exceptions. Shared malformed-namespace handling is deliberately conservative;
repair of corrupt historical records is outside this proposal.

## 4. Outcomes and proposed user-facing explanations

| State | Controlled result / explanation |
|---|---|
|All gates pass|One Selected result: understood event, actual rule/version, applicable scoped declarations or reviewed values, stated facets/time and any provisional assumption|
|Unspecified code, inferred result|“No dress code was supplied. This suggestion uses a limited casual/smart-casual appearance guideline; check your plans and any venue requirements.”|
|Explicit Allow supports a member|“Your explicit date/dinner suitability choice supports this condition.” Do not claim an inferred style predicate passed.|
|No admitted garment evidence|InsufficientEvidence: “Current garment evidence does not establish a suitable complete outfit for this policy.” Identify missing/stale review versus uncovered style where established; do not ask users to change a correct style label.|
|Definite applicable Deny / hard requirement failure|NoMatchingCandidates when no alternative complete candidate passes. Never relax a Deny to manufacture a result.|
|Known unsupported formal/code/venue|PolicyUnavailable with the understood condition; no smart-casual or generic-outfit fallback|
|Unrepresentable code/modifier, negation, conflict or compound situations|UnsupportedRequest, preserving current interpretation boundaries; no constraint deletion|
|No eligible garments / incomplete structure / concurrent edit|Existing NoEligibleGarments / InsufficientStructure / WardrobeChanged, with unchanged atomicity|

“Dinner date” names both contexts and remains unsupported until composition is
separately scoped; it must not be mapped to whichever target avoids a Deny.
Equivalent wording uses the same declaration target, but exact keyed-text replay
still requires unchanged submission text. Missing/unspoken situations cannot be
inferred from the user's actual plans.

The existing generic result still contains wedding-specific invitation wording.
Use binding-supplied safe notes for new date/dinner explanations and preserve old
1.0.0 history rendering. New explanation metadata may use additive version 1.1.0;
the frontend must read both versions. Store the actual scoped declarations,
reviewed evidence, rule/policy/bundle hashes and explicit versus inferred basis.
No historical result is rewritten or re-explained under the new policy.

## 5. Independent acceptance package and bounded work

[JSON matrix](../storage/verification/context_phase2_policy_proposal_20261025/proposed-acceptance-matrix.json)
and [CSV](../storage/verification/context_phase2_policy_proposal_20261025/proposed-acceptance-matrix.csv)
contain **58 author-labelled proposed cases, none executed**. Labels are based
on this proposed contract, not on future implementation output or independent
fashion judgement. Freeze the approved version before implementation.

| Case group | Proposed coverage |
|---|---|
|N01–N12|All five requested phrases; equivalent commands; unspecified/casual/smart-casual; actual spans/time, no fabricated role/venue; proposed restaurant/friends treatment|
|U01–U06|Formal/black tie even with Allow; unsupported venue/group-date/soft-ranking conditions|
|E01–E21|Exact Deny across wording, explicit Allow, Allow+Deny, malformed metadata, scope separation, separate formality, missing/stale/uncovered review and absent declarations|
|G01–G10|Archived/unavailable/foreign/unconfirmed rows, missing structure, outerwear, every structure and mandatory colour/category constraints|
|H01–H06|Negation, dinner-date composition, conflicting codes, calendar-date question, weather and unknown dress code|
|P01–P03|Immutable old/new keyed replay, ranking/commit evidence changes and exact-key conflicts|

For the one-dress/no-preference fixtures, independently labelled R=1, C=1/2,
P=0 gives total **7/10**. The four-blue/casual-garment fixture has exactly four
candidates; the paired structures score **4/5**, and stable role/ID ordering
selects dress-A + outer-A. Future tests must assert complete per-candidate
eligibility/counts/scores and public/independent agreement, not just a plausible
winner. Expand reviewed-style/decision/staleness truth tables independently.
Retain all frozen wedding labels and rerun wedding/legacy compatibility checks.

Compilation remains once per evaluator/request, with request-level admission
for companions/venue. Prepare only active date OR dinner predicates in O(N*K),
K<=2 occasion/formality conditions. At 100 eligible snapshots, primary plus
independent preparation has at most 400 resolutions; public winner/gate add at
most 12 for three members, with explanation work only for the selected result.
No NLP, config, database or model call belongs inside enumeration. Candidate
counts and exact scoring are unchanged for the same eligible population; enabling
new contexts intentionally changes eligibility from Phase 1's unavailable state.
Use call-count assertions and retained inputs; no capacity reduction/full NFR
matrix, and no speculative optimisation or latency guarantee.

## 6. Exact future implementation boundary and approvals

This is a proposed scope, **not production-edit authority**. Preserve the shared
architecture, existing profile name and global default. Append bindings and
extend existing allowlisted operators/adapters; do not add per-event pipelines.

| Owner | Existing production files proposed to change | Exact purpose |
|---|---|---|
|R NLP/config|`backend/app/application/nlp/general_context_interpreter.py`; `backend/app/application/nlp/config/context_grammar.v1.json`|Versioned shared going-out frame, preserving all modifiers/spans; no separate dinner parser|
|R taxonomy/policy|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`; `backend/app/application/recommendation/config/context_policy_registry.v1.json`|Only date/dinner projection crosswalks; append approved bindings/rules. Proposed taxonomy/grammar/registry minor versions 1.1.0; wedding rule values unchanged|
|R registry/compiler|`backend/app/application/recommendation/context_policy_registry.py`; `backend/app/application/recommendation/context_constraint_compiler.py`|Validate the three approved bindings; allowlisted style-set predicate and per-binding facet admission/assumptions. No guest assumption leakage into date/dinner|
|R evidence/evaluation|`backend/app/application/recommendation/context_evidence_resolver.py`; `backend/app/application/recommendation/general_context_evaluator.py`|Exact legacy date/dinner declaration channel, shared style predicate, proof and safe binding-specific explanation notes|
|Shared frontend/API|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`|Additive explanation types/notes for success and no-result; remove wedding-specific wording only for new bindings, preserve stored history/long names/keyboard/zoom|

**Twelve existing production files; no new production/policy file proposed.**
The shared registry holds the two new versioned policy bindings. General frame,
snapshot/query/review writers, original vocabulary and declaration policy,
frozen wedding components, numerical/compact scorers, candidate stream, runtime
profile selection, API routes, account/auth, provider/migrations, Homepage and
CV/VTON files need no change for this proposed scope.

Proposed necessary verification/support scope: extend
`backend/tests/integration_source_guard.py` with a new exact transition fixture;
add `backend/tests/test_date_dinner_context.py`,
`backend/tests/test_date_dinner_equivalence.py`,
`backend/tests/fixtures/date_dinner_context_labels.v1.json`,
`backend/tests/fixtures/date_dinner_context_sources.v1.json`,
`frontend/tests/phase5f/date-dinner-context.spec.ts` and
`frontend/playwright.date-dinner-context.config.ts`.

Two existing backend test modules also require explicit approval for narrowly
named current-contract adaptations: `test_general_context.py` has G03/G08/G22/G23
date/dinner inactive expectations; `test_general_context_equivalence.py` has the
recognised-unavailable loop and wedding-only capabilities assertion. Preserve
the Phase 1 label fixture and original test copies unchanged in retained evidence;
new version-specific assertions must explicitly record these intentional four
inactive-to-available transitions, with new independent labels. Do not silently
edit frozen labels, weaken Deny/unsupported assertions or relabel Phase 1 results.
The existing Phase 1 browser tests can be reused without alteration.

Required decisions before production changes:

1. **Policy owner/R/supervisor:** approve DT01–DT05 and DN01–DN05, the provisional
   appearance guideline, exact declaration crosswalk, positive-only inference,
   conservative malformed barrier and independent acceptance labels.
2. **Context semantics:** approve friends for dinner/plain restaurant treatment
   and its limits. Alternative: keep all explicit venues unavailable; this would
   change N10/N11 expected outcomes and must be recorded before implementation.
3. **R/shared frontend owners:** approve the exact twelve-file production scope,
   three existing test/support files and named new verification files. T-owned
   garment/query/review/storage files are read-only and require no new edits in
   this scope. Any additional field/source admission or unexpected caller change
   must return for named approval first.

No policy is activated by this package. Interviews, presentations, graduations,
beach activities, hiking, travel, formal clothing and specialised capabilities
remain unavailable. Real attribute/model evidence, bounded RN-13 scope, VTON,
final database architecture, formal NFR acceptance, TLS/deployment and canonical
ai-services decisions remain open. Prior evidence and requirement counts do not
advance. **Proposal ready for approval with the stated limitations; implementation
and execution verification await the user's concrete policy/scope approval.**
