# Eighteen-context Assistant: source analysis and implementation matrix

2026-10-28, Asia/Kuala_Lumpur. **Analysis/proposal complete; approval required before
production implementation.** This is the first deliverable requested in the attached
“Expand Outfit Assistant to 18 Contextual Situations” request. It does not activate
another context or alter the running A1 application.

Recommend all ten proposed situations within the ordinary appearance scopes below.
That would give **18 active situation bindings: 15 ordinary relative-ranking contexts
and three existing specialist contexts**. Nine semantic IDs are new; `travel.journey`
already exists and needs its first active binding. The resulting taxonomy would have
23 recognised IDs, including five still-unavailable IDs. Recognised, admitted and
independently validated are separate counts.

Birthday defaults to **casual**, with a supported explicit style override. Office and
team-meeting smart-casual goals are chosen prototype presentation conventions, not
workplace requirements. All ten objective conventions remain independently unvalidated.
Shared goals can return shared rankings and winners. No diversity bonus is proposed.

## 1. Source findings and work actually performed

Inspected the current compositional interpreter, vocabulary/extractor, immutable
frames, taxonomy, registry/compiler/resolver/evaluator, A1 preparation/scoring/archive
reader, composition, API, persistence checks and frontend explanation boundaries.
The current accepted [A1 source report](A1_CONTEXT_RELEVANCE_RANKING_VERIFICATION.md)
and [activation report](A1_CONTEXT_RELEVANCE_MANUAL_ACTIVATION.md) remain unchanged.

Concrete source constraints:

|Current source|Finding and implication|
|---|---|
|`application/nlp/general_context_interpreter.py`|Requires grammar/taxonomy 1.3.0; recognises literal situation phrases, then composes modifiers and hard garment fields. Multiple event matches normally refuse. The frame list is checked in Python but action-prefix recognition is also a separate regex; editing JSON alone will not add natural sentence forms.|
|`application/nlp/request_field_extractor.py`|Rejects unexplained residual words, negation, alternatives and unrepresentable local colour/category bindings. Preserve this safeguard; making more words globally ignorable would erase meaningful conditions.|
|`application/recommendation/context_policy_registry.py`|Requires registry 1.4.0 and exactly eight named bindings. Ordinary family validation, scopes and some explanation text are duplicated in Python. An extra JSON row is rejected.|
|`application/recommendation/context_evidence_resolver.py`|Reuses saved-style evidence, but declaration-source dispatch couples parent-negative handling to professional policies. New ordinary subcontexts need an explicit ordinary negative-parent path.|
|`application/recommendation/context_relevance_policy.py`|Pins policy/catalogue bytes and five `SCOPES`, enforces maximum five objectives and cross-checks admission scopes. The scorer's `applies()` imports that same closed set.|
|`application/recommendation/context_relevance_verifier.py`|Correctly retains an independent archived revision/target allowlist. Add new revisions; replacing its old targets would corrupt historical meaning.|
|`application/recommendation/decision_score_codec.py`|Relative score decoding checks the currently imported policy version. A new policy revision needs explicit old/new reader dispatch.|
|`application/recommendation/outfit_assistant_service.py`|Replay precedes interpretation. Error/success explanations construct a default evaluator separately; those must use the captured selected bundle after expansion.|
|`domain/value_objects/assistant_execution_context.py`|Execution metadata compares its registry hash with `EvaluatorSpecification.current()` for the default bundle. It must validate the captured approved bundle rather than reject every opt-in winner.|
|`api/recommendation_routes.py` and frontend|Capabilities load the default registry/catalogue; frontend versions and five-goal helper text are allowlisted/hardcoded. They must describe the effective service bundle.|

Backend paths in this table are relative to `backend/app/`. The current taxonomy has
14 IDs and eight bindings. The six recognised unavailable IDs are beach, graduation,
hiking, travel, unspecified interview and unspecified presentation.

A **50-input, in-process current-parser probe** recorded 18 Supported interpretations
and 12 available contextual plans. These are observations, not 18 passing expansion
tests or a coverage percentage. All ten exact new example sentences in the request
currently refuse. Existing “What should I wear to university?” and “What should I wear
for shopping?” already work. “I have a dinner date” refuses as multiple requests;
“I'm going to class at university” also refuses as multiple requests. Family dinner,
having dinner with friends, hanging out and a café date expose other lexical/frame
or scope gaps. Full frames/reasons are retained separately.

Only this new repository report and external review artifacts were written. The probe
imports the interpreter/compiler only: no server, factory, DB, model, browser,
recommendation generation, regression suite or benchmark ran. No runtime process,
private account, garment, preference, image, chat or secret was inspected. No live
health check or stop/start was necessary for this design task.

## 2. Shared proposed admission and objective contract

For all ten new bindings, use the existing supported saved-singleton-style evidence
family. Every selected member, including outerwear, must pass the required conditions.
For an unspecified code, admit current casual or smart-casual styles provisionally.
A supported explicit casual/smart-casual code requires the corresponding style.
Formal/black tie, unsupported roles/venues, specialised conditions, malformed evidence
and missing facts do not become supported through an objective or fallback.

All ten require a recognised situation. No user role is inferred or required; the
initial role scope is **unspecified only**. An explicit employee, presenter, guest or
other role that is outside that binding remains unavailable. “Colleagues” is a stated
companion relationship, not inferred employment status or a professional standard.
Time is optional metadata under the existing no-forecast/no-future-availability contract.
Explicit supported style/colour/category/formality requirements retain their hard
semantics. No new physical garment attributes or mandatory review actions are needed.

New declaration targets are the exact semantic IDs in section 3, including the
existing `travel.journey` projection. Do **not** add ten values to the frozen `rec:v1`
namespace. Reuse existing broad negative scopes, as expressly proposed below:

|New contexts|Existing exact occasion Deny that also applies|
|---|---|
|Library; academic group study|`campus`|
|Office day; workplace meeting|`work`|
|Birthday gathering|`party`|
|Friend's-house gathering; cinema; café meetup|`casual_outing`|
|City sightseeing; ordinary transit|`travel`|

This inheritance is a **new policy decision requiring approval**. A broad Deny is
conservative and may exclude more than the user intended; its effect must be explained.
A broad Allow does not supply permission for a new child context or invent missing
style. Malformed authoritative declarations still block inference; an identifiable
applicable Deny wins. An applicable requested-formality Deny also wins. Normal saved
facts supply the positive inference. Existing five ordinary exact Allow/Deny meanings
and specialist evidence contracts remain intact.

No new child-specific restriction editor or declaration namespace is proposed.
Consequently new-context restriction controls initially have the broad granularity
above; the UI must not advertise a per-library or per-café override. An exact child
declaration feature would need separate contract/storage/UI authority. No tags are
written automatically and no private record is backfilled.

Reuse the A1 single base-style mean, C conventions, independent P/duplicate mask,
original denominator, exact **T = 3/5 R + 1/5 C + 1/5 P**, deterministic tie key,
best-evidenced coverage and disclosed baseline modes. Explicit supported user style
overrides the soft default and keeps its existing any-base-member hard requirement.
Default goals apply only with unspecified role/code/formality. An otherwise supported
explicit code with no explicit style may use the disclosed legacy baseline after
hard admission. No missing facts, corrupt bundle or technical error authorises fallback.

## 3. Decision-ready ten-situation matrix

The following IDs/binding names are proposals matching the existing dotted semantic
and snake-case binding conventions. Each is its own capability and explanation scope;
all reuse one ordinary predicate family and the shared scorer. A distinct semantic
scope is useful for intent preservation, restrictions and future scoped evaluation,
even where the current admitted styles and ranking are identical. No extra fashion
knowledge is claimed from adding a binding.

Combine **policies**, not distinct stated activities: library/group study and office/
meeting should each reuse their common predicate family, while retaining the activity
and domain boundaries tested below. Keep having/hanging-out paraphrases in existing
contexts, café dates in date, and meal/social compounds as one primary situation with
retained facets. Postpone all specialised subcases in section 10. If separate office
day/meeting intent reporting is not wanted, merging those would give 17 capabilities;
do not claim 18 by counting their synonymous sentences twice. The recommended 18
requires separately demonstrated interpretation, capability scope and explanations
for each of the ten proposed activities, rather than ten newly different formulas.

|Wave / situation and binding|Distinguishing meaning; admitted optional slots|Goal, rationale and counterexamples|
|---|---|---|
|A: `academic.library_study` / `library_study_appearance_v1`|Studying at a library, not ordinary lecture attendance or library employment. Activity `studying`; venue library/university/campus; companions friends/classmates.|**casual**: a simple ordinary-study appearance convention. A formal library event, staff uniform, laboratory or institutional rule is outside it; no comfort, quietness or study-performance claim.|
|A: `academic.group_study` / `group_study_appearance_v1`|Collaborative academic study/project discussion, not a presentation or work project. Activity `collaborative_study`; university/campus/library; friends/classmates. “Group study” establishes academic study; “project meeting” needs academic context.|**casual**: same appearance goal as ordinary study. Assessed presentations, client work, uniforms and ambiguous project meetings do not inherit it.|
|A: `professional.office_day` / `office_day_appearance_v1`|Ordinary work physically at an office/company. Activity `office_work`; office/company; colleagues. “Work” alone does not establish an office.|**smart casual**: chosen prototype office-presentation goal. Relaxed offices can favour casual; uniforms, PPE, client codes and remote work are not established. This is not employer-code compliance.|
|A: `professional.workplace_meeting` / `workplace_meeting_appearance_v1`|Ordinary workplace/team discussion. Activity `workplace_meeting`; office/company; colleagues. Workplace wording or colleagues establishes the domain; generic “meeting” does not.|**smart casual**: same chosen presentation goal as office day. A team can dress casually. Board/client/formal meetings, interview and academic presentation retain separate unsupported/strict scopes.|
|B: `social.birthday_gathering` / `birthday_gathering_appearance_v1`|Ordinary birthday celebration without a supplied specialised theme/code. Activity `birthday_celebration`; friend's home/restaurant; friends/family.|**casual recommended** over smart casual for the initial ordinary gathering convention. Either can be appropriate. A formal, costume, venue-specific or birthday-dinner event needs its stated meaning preserved. Explicit smart-casual style can override.|
|B: `social.house_gathering` / `house_gathering_appearance_v1`|Ordinary social visit/gathering at a friend's home. Activity `social_house_visit`; friend's home; friends. A visit is treated as ordinary social only under the disclosed convention.|**casual**: a simple social-visit goal. Repairs, caregiving, overnight accommodation, ceremonies or formal home receptions are outside it. Destination alone cannot erase a stated work/activity purpose.|
|B: `leisure.cinema_outing` / `cinema_outing_appearance_v1`|Watching a film/cinema outing. Activity `watching_film`; cinema; friends/family/someone. Watching a movie without a stated venue does not invent a cinema venue.|**casual**: ordinary entertainment appearance convention. Premieres/red carpet, performance work and movie dates are not silently reduced to this binding. No indoor-temperature or comfort claim.|
|B: `social.cafe_meetup` / `cafe_meetup_appearance_v1`|Social coffee/café meeting, without romantic or work meaning. Activity `social_meetup`; café; friends/family/someone. “Someone” remains an unspecified relationship.|**casual**: ordinary social-meetup goal. A café date remains a date; an interview/client meeting at a café does not become a casual meetup. A café does not impose a dress code.|
|C: `leisure.city_sightseeing` / `city_sightseeing_appearance_v1`|Ordinary city sightseeing. Activity `city_sightseeing`; city; friends/family/someone. City wording supplies the bounded setting; unspecified sightseeing needs clarification.|**casual**: ordinary city-visit appearance convention. Beach, hiking, religious-site codes, specialist equipment, weather and physical-exertion needs are excluded. No footwear/mobility/sun-protection assessment.|
|C: **existing** `travel.journey` / new `ordinary_transit_appearance_v1`|Ordinary journey/transit day. Activity remains `travelling`; friends/family/someone; optional train/bus/flight transport facet. No required venue or transport type. Not a sightseeing activity or a specialised expedition.|**casual**: ordinary transit appearance convention. No climate, safety, comfort, airport/operator compliance, luggage or equipment assessment. Specialised motorcycle/expedition travel is excluded.|

No proposed ordinary binding requires new reviewed construction/condition observations.
Weddings/presentations/interviews retain their stricter accepted evidence; office-day
labels do not establish interview readiness. A style goal is a soft preference over
eligible choices, not a new dress code or evidence that the saved label is true.

For each new context the explanation must name its understood activity, stated slots,
default/explicit goal, broad negative scope and prototype/source limits. For example:
“Using the prototype smart-casual appearance goal for an ordinary office day. No
employer dress code was supplied or verified.” Transit must explicitly say its score
does not assess travel comfort, weather or safety. Missing evidence gives the existing
controlled outcome; no qualifying structure and an unavailable code remain distinct.

## 4. Proposed language patterns, modifiers and negative controls

The three positive phrases per row are concrete acceptance candidates, not a closed
list of the only sentences to implement. A bounded reusable grammar combines an
intent/action frame, one semantic activity, licensed venue/companions/time clauses and
existing hard garment-field clauses. Preserve original spans and inspect all residual
text. Recognise cafe/café and straight/curly apostrophe variants with an offset map;
do not apply destructive normalisation that invalidates the stored source spans.

|Context|Concrete positive variants|Negative/clarification controls|
|---|---|---|
|Library|“I'm going to study at the library.”; “What should I wear for a library study session?”; “I will study at the library tomorrow.”|Library laboratory; library staff uniform; library visit with unknown purpose asks for purpose rather than inventing study.|
|Group study|“I have a group project meeting at university.”; “What should I wear to group study on campus?”; “I'm meeting classmates for a study session at the library.”|Project meeting without domain asks workplace/study; a project presentation retains presentation meaning and requires its role/evidence.|
|Office|“I need to go to the office tomorrow.”; “What should I wear for an office workday?”; “I'm working at the office today.”|“Going to work” asks whether ordinary office or specialised work; working from home and construction PPE do not map to office day.|
|Work meeting|“I have a meeting with my colleagues.”; “I'm attending a team meeting at the office.”; “What should I wear for a workplace meeting tomorrow?”|Generic meeting asks domain; team meeting at university remains ambiguous without work/study evidence; formal/client board events refuse.|
|Birthday|“I'm attending a birthday party.”; “What should I wear to a birthday gathering?”; “I have a birthday celebration with friends tonight.”|Black tie/costume; birthday dinner follows the approved compound rule below.|
|House|“I'm visiting my friend's house.”; “What should I wear for a casual gathering at a friend's house?”; “I'm going to a friend's place tonight.”|Repairing a friend's roof; formal home reception; no automatic home-safety assessment.|
|Cinema|“I'm going to watch a movie.”; “What should I wear to the cinema?”; “I'm seeing a film with friends tonight.”|Red carpet/premiere; a movie date retains date plus unsupported additional scope, with controlled refusal/clarification rather than an ordinary cinema result.|
|Café|“I'm meeting someone at a café.”; “What should I wear for a cafe meetup?”; “I'm meeting a friend for coffee at a cafe tomorrow.”|Client/interview purpose is not erased; bare “meeting someone” asks the domain/setting.|
|Sightseeing|“I'm sightseeing around the city.”; “What should I wear for city sightseeing?”; “I'm going sightseeing in the city tomorrow.”|Beach/hiking/snow; a bare sightseeing request asks whether ordinary city sightseeing.|
|Transit|“I'm taking a train for a trip.”; “What should I wear for an ordinary travel day?”; “I'm taking a flight tomorrow.”|Mountaineering expedition; motorcycle safety equipment; “taking a train” alone must not invent a travel purpose.|

Proposed reusable frames add “I need to go…”, “I will…”, “I'm studying/working/
visiting/watching/taking…”, “I'm having…” and bounded “I have…” forms. This is a finite
grammar expansion, not unrestricted language understanding or a free-text synonym
fallback. Merely mentioning an activity in a question about buying/deleting items,
explaining definitions or changing instructions is not recommendation intent.

Classify language into A, an existing-context expression; B, a new capability;
C, clarification required; and D, unsupported. Reuse existing `UnsupportedRequest`
with a specific clarification reason/message for C; do not introduce a conversation
state machine or automatic second confirmation. The owner may submit a fresh complete
request. Ordinary unambiguous requests need no additional interaction.

Existing-context additions are A: family dinner, having dinner with friends, hanging
out with friends, and repeated same-context venue wording such as “class at university”.
The two university/shopping outfit questions already work and are preservation controls.
“Suggest a casual outfit” retains its current formality meaning. Unsupported soft
comfort/avoidance language, negation, contradictory codes, unknown activities and
unrelated multiple occasions remain controlled refusals.

## 5. Composition that preserves meaning

Do not add a general first-keyword-wins or longest-event-wins rule. Longest lexical
matches may remove contained synonyms for the **same licensed expression**; they may
not erase an independent occasion or specialised condition.

Recommend an additive bounded `facets: ContextSlot` in `GeneralContext`, under frame
version **general-context-1.1.0**. It carries at most two allowlisted, span-backed
values; it is not a free-form metadata channel or an extra scoring field. Initial
values are `meal:dinner`, `celebration:birthday` and `transport:train|bus|flight`.
At most one celebration/meal relation and one mutually exclusive transport value may
be present, with only explicitly licensed combinations. Old frames remain readable.

|Expression|Retained meaning and proposed policy action|
|---|---|
|Dinner date|Primary `social.date`, facet `meal:dinner`; compile both existing date and dinner gates, including both exact Deny scopes. One smart-casual objective; explicit style overrides once.|
|Birthday dinner|Primary `social.meal`, facet `celebration:birthday`; compile dinner plus birthday-gathering gates, with dinner and party negative scopes. The explicit meal is primary under this named product rule; use its smart-casual default, rather than silently replacing it with birthday's casual default. Explain both meanings and this choice.|
|Café date|Primary `social.date`, venue café; approve a bounded extension of date's venue scope. It remains a date and uses the date goal. It is not the ordinary café-meetup binding.|
|Class at university; university group project meeting|University is a licensed venue/domain qualifier, not a second ordinary-campus event. A project presentation is not removed as a qualifier.|
|Train for a trip; flight tomorrow|Primary `travel.journey` and explicit transport facet; transport supplies no garment utility, comfort or safety permission.|

Compound plans intersect at most **two** admitted bindings; Fail wins, then Unknown,
then Pass. Existing hard fields are evaluated once. A clean Allow for date cannot
waive the dinner requirement; shared numeric predicates may be prepared once while
their distinct declaration checks/proof are retained. One primary appearance objective
prevents double payment. Reject unlisted compounds, conflicting domains and unrelated
sequences; do not create a compound situation ID for each phrase or inflate the count.

The existing scalar `activity` remains the primary activity; retained facets and
their compiled secondary bindings appear in request JSON, admission explanation and
stored provenance. The new proof reader must validate that the secondary plan matches
the actual request/facets and bundle, not merely accept a claimed secondary ID.
The new frame and proof definitions require shared contract approval.

## 6. Maintainable bundle, versioning and isolation

Recommend a small **immutable context bundle** joining the selected grammar, taxonomy,
registry and objective catalogue. `general_context_v1` remains the public feature
profile; its default bundle remains the accepted eight-context implementation.
A proposed server-only `SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE` defaults to
`legacy_8_v1`. Only an explicit opt-in `context_18_v1`, with the existing general/A1/
suitability selections, exposes the expanded release. Unknown combinations fail.
No current environment, launcher or service is changed by this proposal.

The bundle descriptor has allowlisted resource names, versions and hashes; it cannot
load arbitrary paths, executable expressions or user-supplied rules. Load/validate
once before preparation/enumeration. Validate unique IDs, exact projections, registry
coverage, predicate/operator types, role/venue/companion compatibility, facet rules,
objective applicability and full explanation metadata. Keep 64 KiB per configuration
file, at most 32 taxonomy/binding entries, at most 15 relative objectives, bounded
trees/phrases/frames and the existing 500-character request limit. A manifest digest
does not replace semantic validation or source-ownership approval.

One generic ordinary predicate-family validator replaces the repeated new-context
Python branches. Existing specialist validators remain closed and unchanged. The
selected bundle supplies scopes, enabled binding IDs and relative-enabled flags to
the existing compiler and objective resolver; it cannot introduce a scorer/operator.
Future compatible entries should require reviewed configuration/labels and a release
manifest, not changes to kernel arithmetic or a handler for every sentence. A new
operator, physical requirement or semantic field still needs code and approval.

|Contract|Proposed final release treatment|
|---|---|
|Grammar/taxonomy|New `context-grammar-2.0.0` / `situation-taxonomy-2.0.0` in new v2 files; retain original 1.3.0 files. New grammar schema covers reusable expressions/qualifiers/facets.|
|Frame|Additive `general-context-1.1.0`; old 1.0.0 accepted by its original reader.|
|Registry|New `context-registry-2.0.0`; 18 bindings. Old registry 1.4.0 retains its exact bytes/reader.|
|Admission policies|One new `ordinary-saved-style-appearance-1.0.0` family for ten bindings, with distinct binding/rule IDs. Existing five predicates keep their meaning. Date/dinner scope additions use new 2.1.0 policy revisions; W/AP/IP objects remain equal to their accepted originals.|
|A1 profile and numerical operator|Keep `context_relevance_decision_v1` and base-member style mean; no R/C/P/tie/coverage/fallback formula change.|
|Policy/catalogue|New `context-relevance-policy-1.1.0` / `context-relevance-objectives-1.1.0`, recording expanded bound/scopes; retain original 1.0.0 files/revisions.|
|Proof/explanation|New `context-relevance-evidence-1.1.0`, `context-relevance-explanation-1.1.0` and `general-context-explanation-2.0.0`, with bundle/facet/binding provenance. Keep old readers.|
|Capabilities/display|New `context-ranking-capabilities-1.1.0`; additive display-2.1.0 for bundle/facet/restriction metadata, with existing exact component semantics and old display-2.0.0 reader retained.|

Wave A/B checkpoints use explicitly prerelease version/hash identities, such as
`2.0.0-wave-a.1` and `2.0.0-wave-b.1`, with their own approved activated subsets.
Final IDs above describe the full release, not meanings to reuse for incomplete
catalogues. Retain checkpoint hashes and immutable before/after transitions. A/B
checkpoints are engineering evidence, not authority for live activation.

Historical proof validation dispatches by stored approved revision **and hashes**,
with archived target/scope definitions independent of the active bundle. Old-key replay
still precedes current NLP/selection; old records are not reparsed or reranked. Exact
fraction strings, 4,096-digit integer and 256-KiB proof/score limits remain. Measure
bounded new metadata under those limits; fail controllably on overflow, never truncate,
float-convert or use baseline to hide a contract failure. No schema migration is needed
for the existing immutable JSON storage, but its validation boundary needs approval.

## 7. Exact proposed source and ownership boundary

**Proposed, not permission to edit:** 20 existing backend and four existing frontend
production files, plus eight new production files. Exact paths/reasons and starting
hashes are retained in `proposed-scope.json` and `starting-hashes.json`. Backend
recommendation paths below are under `backend/app/application/recommendation/`.

|Owners / area|Existing paths proposed for change|
|---|---|
|NLP/shared frame|`backend/app/application/nlp/general_context_interpreter.py`; `backend/app/domain/value_objects/general_context_request.py`: selected bounded grammar/composition and span-backed facets.|
|R/context admission|`contextual_selection.py`, `context_policy_registry.py`, `context_constraint_compiler.py`, `context_evidence_resolver.py`, `general_context_evaluator.py`: selected bundle, reusable ordinary family, negative scopes and compound checks/explanations.|
|R/A1 selection and archival verification|`context_relevance_policy.py`, `context_relevance_scorer.py`, `context_relevance_verifier.py`: selected scope/catalogue and versioned bundle/compound proof validation, keeping exact arithmetic.|
|R/compact/reference integration|`compact_exhaustive_scorer.py`, `compact_assistant_scorer.py`, `aggregated_decision_scorer.py`: pass the same prepared immutable bundle through both paths; no per-candidate loading.|
|Shared integration/score projection|`outfit_assistant_service.py`, `decision_score_codec.py`, `scoring_display.py`: explanation uses selected evaluator, controlled clarification and archived/versioned decoding.|
|Shared immutable execution metadata|`backend/app/domain/value_objects/assistant_execution_context.py`: verify the captured approved evaluator bundle/request identity rather than the default bundle's hash; preserve winner/user/snapshot checks.|
|Shared API/composition/storage|`backend/app/api/recommendation_routes.py`; `backend/app/infrastructure/workflow_runtime.py`; `backend/app/infrastructure/persistence/recommendation_repository_adapter.py`: effective capabilities, opt-in bundle and request/facet/proof consistency. Existing routes, locks, inserts, owner/key checks and selected-snapshot validation remain.|
|Shared frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`: typed metadata, capability-driven examples, clarification/limits and old/new history rendering.|

New production paths proposed:

```text
backend/app/application/recommendation/context_bundle.py
backend/app/application/nlp/context_expression_matcher.py
backend/app/application/recommendation/config/context_expansion_bundle.v1.json
backend/app/application/nlp/config/context_grammar.v2.json
backend/app/application/recommendation/config/situation_taxonomy.v2.json
backend/app/application/recommendation/config/context_policy_registry.v2.json
backend/app/application/recommendation/config/context_relevance_policy.v2.json
backend/app/application/recommendation/config/context_relevance_objectives.v2.json
```

`context_bundle.py` validates/captures approved immutable resources. The expression
matcher implements finite reusable expression/qualifier composition, not event-specific
interpreters or unrestricted inference. The six new JSON resources retain all accepted
v1 files. No account preferences UI, central garment writer, strict query, scoring
formula modules, CandidateRanker, CV/VTOFF/VTON, authentication, schema or provider
change is proposed. The existing generic compact mandatory tables can consume the
aggregate per-member Pass/Fail/Unknown result; tests must prove both compound gates
were included. Any need to edit those additional modules must first be named/justified.

New verification paths, not created in the repository yet:

```text
backend/tests/test_context_expansion_nlp.py
backend/tests/test_context_expansion_policy.py
backend/tests/test_context_expansion_integration.py
backend/tests/test_context_expansion_equivalence.py
backend/tests/test_context_expansion_history.py
backend/tests/fixtures/context_expansion_nlp_labels.v1.json
backend/tests/fixtures/context_expansion_labels.v1.json
backend/tests/fixtures/context_expansion_sources.v1.json
frontend/tests/phase5f/context-expansion.spec.ts
frontend/playwright.context-expansion.config.ts
```

The sole proposed existing test/support adaptation is
`backend/tests/integration_source_guard.py`, chaining exact approved transitions and
new files. No existing frozen test/oracle is authorised for editing. Default-off old
tests should keep their original expectations; new opt-in tests own new behavior.
Retain old manifests, source copies, checkpoint patches and all failed attempts.

## 8. Acceptance candidate, independent review and honest freeze

`proposed-acceptance-matrix.json` contains **80 concrete NLP cases and 112 prospective
end-to-end/control cases, 192 review candidates total**. The NLP set includes three
positive forms and two non-selection controls per new context, plus 30 cross-context
cases. The end-to-end set includes ten checks per new context and 12 shared controls.
They are proposed cases, **not tests executed or passing results**; a case may produce
several assertions when implemented. They were authored from the proposed contract,
not copied from a future parser/scorer's output.

No independent reviewer has reviewed or approved them in this task. Bytes/hashes are
retained as a review candidate; **formal acceptance freeze is pending**. Calling this
an independently reviewed frozen oracle now would invent evidence. After an actual
reviewer/owner accepts or revises expectations, retain both versions and freeze the
approved JSON before any production edit. If an independent reviewer is unavailable,
the owner must explicitly choose an author-labelled prototype contract and retain
independent validation OPEN. Do not claim the requirement was independently met.

|Group|Concrete required assertions|
|---|---|
|Interpretation|Semantic ID, activity, every stated modifier/hard field, original spans, absent versus unknown relationship, exact compound/facet plan; cafe/café/apostrophe variants; no discarded residual words.|
|Capability|Own binding/family, version/hash, negative-parent scope and objective; code/role/venue/soft-goal rejection; no study/work or date/meetup substitution.|
|Mandatory evidence|Applicable Deny, malformed authoritative container, absent/stale/forged source, missing/multiple/uncovered style and selected outerwear; no broad Allow-to-child permission.|
|Ranking|All four candidate structures; compact/reference/public decisions and exact R/C/P/T/tie/proof agreement; independent preferences, duplicate masks/denominator, known R=0 and same-goal shared winners.|
|Normal workflow|Automatic Add with valid data, zero mandatory review/confirm/tagging POSTs, actual normal request through capabilities and result UI, correct correction/no-save state for genuine processing gaps.|
|Controlled outcomes|Unavailable policy, clarification, no eligible garments, structural shortage, failed requirement, insufficient evidence, certified versus coverage-limited relative winner and disclosed baseline remain distinct. Technical/configuration failure cannot turn into fallback.|
|Storage/security|Strict owner/available/confirmed/completed joins; changed selected snapshots; insert-abort rollback; same-key recovery; immutable old/new history after bundle/preference changes; saved outfits; copied bearer denied after logout; atomic 99-plus-two/concurrent-last-slot quota.|
|Browser|New contexts through ordinary UI; full exact components/objective/provisional limits; compound meaning; no-result/retry; old history; keyboard focus and history behavior; long names, 360/390/768/1280/1920px and native 200% zoom.|
|Bounded work|Existing retained 100-garment population; one strict acquisition, one preference snapshot, one selected bundle/objective preparation; no candidate-loop DB/config/NLP/network/model work.|

The numerical oracle can reuse the retained independently authored eight-garment
labels, without copying actual private records. Under a casual goal the blue casual
pair has R=1,C=1,P=0,T=4/5; under a smart-casual goal the smart dress/jacket has the
same components, with its existing numeric tie disclosed. Under a stipulated matching
goal an independent green preference can produce R=1,C=1/2,P=1,T=9/10. Per-candidate
all-four-structure checks must include the one-piece C=1/2 convention, partial R=1/2,
and exact duplicate suppression; source/review status adds no bonus. Expected fractions
must be written before the implementation is run. Existing A1 missing-evidence and
fallback labels remain separate, unchanged controls.

New negative-parent semantics mean a broad Allow with missing style does not create
a new-child hard-Pass pool. Therefore a proposed zero-point fallback test must first
establish a genuinely hard-Pass request under an authorised contract; it cannot add
invented child permission just to reach the branch. Existing old-context A1 controls
can cover that mode where their clean exact Allow already applies.

The visible review-candidate phrases are not a blind held-out evaluation. Ask a
reviewer to author and seal additional paraphrases/scenarios separately, outside
parser-development examples, before evaluation. Label their classification and slots
before revealing outputs. Do not relabel a failure to make a phrase counted as covered.

## 9. Proposed implementation waves and checkpoints

|Wave|Authorised scope to freeze first; proposed work|Required checkpoint|
|---|---|---|
|A: academic/workplace|LS/GS/OW/WM semantics, parent negatives, four objectives, grammar frames and bundle/archival contracts. Add reusable infrastructure and the first four bindings; keep remaining proposed bindings disabled.|12 active binding definitions in the opt-in checkpoint, nine relative contexts. Focused NLP/admission/ranking/storage positives and negatives; old eight remain equal except separately approved later scope extensions. Default legacy bundle unchanged.|
|B: social/leisure|BG/HG/CM/CF scopes, casual birthday decision, family-dinner and café-date scope changes, two explicit meal/social composition rules.|16 active bindings, 13 relative. Compound gates/proof and date-preservation controls; normal Add/request/browser subset; full component and clarification display. No arbitrary multi-event precedence.|
|C: city/transit and language consolidation|SS/TD scopes, existing travel ID activation, transport facets, broader bounded action/wording families across all contexts.|18 active bindings, 15 relative; 23 recognised taxonomy IDs. Held-back paraphrase candidate execution and specialist negatives; all selected bundle readers and explanations consistent.|
|D: cross-context verification|No extra production paths. Source certification, full approved matrix, selected old regression, production browser, exact replay/archive and 100-garment preparation/enumeration checks.|Final source/build/test identities match; all failures retained; precise counts/native codes and exclusions; source implementation acceptance separate from later manual activation.|

Freeze the wave's source transitions and independent mechanics labels before editing.
Any production changes needed outside section 7 require a named amendment first.
After explicit approval of all named waves/files/contracts, proceed through stable
checkpoints without repeatedly asking for approval of routine implementation steps.
A failed checkpoint is corrected within authorised scope with failures retained;
it is not accepted by changing a historical oracle or enabling an unfinished bundle.
No wave is automatically activated in the owner's running application. Later manual
activation needs its own current-identity/startup gate and exact stop/start approval.

Use the retained population and bound
`(upper × lower + one_piece) × (1 + outerwear)`. Context parsing/bundle selection and
at most two compound admission preparations are outside enumeration; per-member
facts are O(N), shared caches stay bounded, and winner/blocker/fallback tracking has
constant additional selection state. Score only the selected context goal; do not
evaluate 18 policies for each candidate. Existing 100 non-archived-garment quota and
four structures remain. Record changed-path timing on identical retained inputs if
the new parser/preparation work warrants it; this is not formal NFR-02 acceptance.

## 10. Specialist/future situations to postpone

|Situation|Specific remaining evidence/scope required|
|---|---|
|Graduation graduate/guest|Roles, institutional/ceremonial code, gown interaction and appropriate garment evidence/independent labels. It is already recognised but unavailable; ordinary appearance goals do not establish these facts.|
|Gym/exercise|Activity type, motion/coverage requirements, functional garments, footwear/equipment and applicable policy/evaluation. A sporty style label is not functional exercise evidence.|
|Hiking|Terrain, duration, weather/exposure, footwear/equipment and relevant physical garment properties. Existing structural categories/saved styles cannot certify protection or safety.|
|Beach/swimming|Distinguish promenade/social visit from swimming, sun/water exposure and necessary garments/equipment. Do not treat a beach modifier as city sightseeing.|
|Formal workplace event|Supported formal-code evidence, event/role applicability, necessary categories and independent policy labels. Current formal/black-tie capability remains unavailable.|
|Laboratory/uniform classes|Actual institutional rules, activity/PPE/uniform identity, physical requirements and suitable evidence. Ordinary class/library defaults cannot verify compliance.|
|Outdoor sports|Sport and activity-specific conditions, equipment, footwear and validated policy/evidence. No generic casual/sporty shortcut.|
|Specialised travel/weather|Journey type, stated conditions, lawful weather input if later authorised, functional garment/equipment evidence and explicit evaluation boundaries. Time/transport alone supplies none of these.|

Do not propose an automatic implementation date for these. A separate phase is useful
only after its input facts, source authority, category/equipment scope and acceptance
rubric are defined. No external dress-code research or model download occurred here;
the proposed ordinary conventions make no external compliance claims.

## 11. FYP evaluation beyond case counts

Measure semantic situations (target 18) separately from recognised-but-unavailable
IDs (five), phrase count, admitted scopes, evidence coverage and appropriateness.
Compare the accepted eight-context bundle with the opt-in expansion on the same
lawful disposable/consented garments and requests. Preserve the old bundle for an
actual baseline comparison; prior test totals are not a newly executed baseline.

Propose 20 independently authored held-out requests per new context: 12 supported
paraphrases, four meaningful unsupported modifiers and four ambiguity/contradiction
cases, **200 new-context requests**. Add eight preservation/rejection cases per
existing context, **64 baseline-context requests**. These 264 proposed requests are
separate from the visible 192 mechanics/control candidates. They need independent
authorship/review and an agreed rubric before testing; no such results exist now.
Report exact semantic-and-slot agreement, false admission, false refusal,
clarification/rejection correctness and per-context confusion counts. Do not call
recognition alone end-to-end success.

On separately labelled fixed wardrobes, compare full decisions/rankings for equal
versus different objectives, preferences and missing facts. Numerical correctness
measures the authorised convention, not fashion truth. For user-perceived relevance,
propose six to eight consenting users, each trying six counterbalanced old/new
scenario pairs using lawful held-out or voluntarily supplied inputs. That is 36–48
paired tasks, clustered by user, not independent population-level fashion samples.
Record perceived relevance, effort, explanation/soft-default understanding,
fallback/coverage comprehension and reasons. No participants are recruited here.

For independent appropriateness, propose two reviewers judging six held-out
comparisons per new context: 60 scenarios/120 initial ratings. Blind left/right,
allow tie/no-justified-order/insufficient-information, include casual-office and
dressed-up-birthday counterexamples, and separate identical winners. Record reviewer
experience/conflicts; do not automatically call them experts. Agree sampling/rubric
and reporting thresholds with the supervisor before collecting ratings. Report
disagreement rather than converting every judgement into ground truth.

Latency/resource work requires a separate reproducible harness, repeated measurements,
warm/cold conditions and environment specification; focused enumeration checks are
functional safeguards. Independent fashion/model accuracy, human evaluation and
formal NFR acceptance remain **OPEN**. No invented percentage or universal threshold.

If implemented and verified, the expansion would demonstrate bounded compositional
intent/modifier handling, correct ambiguity/refusal, shared evidence-policy reuse,
automatic objective selection, exact context-conditioned ranking, scoped provenance
and history across revisions, and preparation independent of candidate count. It
would not establish larger wardrobe capacity, universal NLP, real-model correctness,
comfort/safety or universally better fashion recommendations.

## 12. Decisions needed before source work

All new approvals are pending; earlier A1 approvals cover that increment, not this one.

|Decision|Exact reviewable approval required|
|---|---|
|E01 semantics/policy/objectives|Owner/R/supervisor/evidence approval of all ten section-3 IDs/scopes/targets, birthday=casual, ordinary admission family and negative-parent semantics, explicit exclusions, and unvalidated normative status. Approve the named date/dinner/family/compound extensions separately within this decision.|
|E02 NLP/contracts/backend|Actual relevant shared NLP/API/storage/composition/integration owners approve sections 4–7: span-backed facets, licensed two-binding composition, default-off bundle, versions/archive/history contract and exact 20 existing backend/eight new production paths and named test/source-guard scope.|
|E03 frontend|Actual shared frontend owners approve the four named production files, capability-driven examples, clarification/compound/restriction/source/fallback explanations and new browser scope. No broad redesign/account profile UI.|
|E04 acceptance and waves|Accept/revise the 192 candidate expectations; record actual independent review or explicitly accept author-labelled prototype mechanics with independent review OPEN; freeze final approved bytes before edits. State all A–D waves or an exact subset. Human sampling/recruitment remains a separate later approval.|

This report is a concrete proposed boundary, not a production edit authorisation.
If the owner combines approvals in one answer, record which actual shared owners
approved which scope. Do not invent teammate/supervisor/reviewer sign-off. No private
inspection, restart, migration, deployment or Git staging/commit is included.

## 13. Evidence and disposition

Review evidence is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\context_18_expansion_review_20261028
```

It retains the request, 556 starting scoped hashes/status, source summary, all 50
current-parser observations, proposed context/scope/192-case JSON, source-probe helpers
and final delivery hashes. The first observation helper referenced `NLPOutcome.request`
instead of its actual `structured_request` field and stopped with native exit 1.
That helper remains; correcting the accessor produced native exit 0 and the complete
50-observation artifact. No production input/assertion changed for that correction.
The artifact-authoring helper completed with native exit 0; that is document generation,
not an executed acceptance suite. Closing scope review also found the existing
execution-metadata default-bundle equality; its exact file is included in the final
20-backend scope. The earlier 19-file draft is retained separately, not a source edit.
Final integrity checks certify all 556 starting scoped paths unchanged, the sole new
repository report, empty staging and report whitespace; they do not certify a future
expanded application or its full historical archive.

**First deliverable complete; stop before implementation.** Recommended target is
18 scoped capabilities, using nine new IDs and activating one existing unavailable
ID, with one shared ranking mechanism. Formal independent acceptance freeze and
new source/policy ownership approvals are pending. No running service was accessed
or restarted, no private record was read or changed, and no new source policy/default
was activated. The original 155-row baseline remains **144 Verified / 2 Partial /
9 Unverified / 0 Blocked**; RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY
ACCEPTED; whole-FYP acceptance remains NOT READY.
