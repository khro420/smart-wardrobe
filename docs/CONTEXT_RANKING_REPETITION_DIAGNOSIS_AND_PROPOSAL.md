# Repeated context recommendations: diagnosis and ranking design proposal

2026-10-27, Asia/Kuala_Lumpur. **Analysis complete; no implementation performed.**

**Confirmed root cause:** the five current ordinary appearance policies share the
same unspecified-code admission predicate. Once a candidate passes, its occasion
receives request-match **1**. There is no graded shopping-versus-class-versus-date
utility in the numerical ranking. Compatibility is context-independent, and saved
preferences are global. Distinct recognised situations therefore need not produce
different scores or winners.

The eight-garment synthetic equivalent reproduces **Navy Dress + Grey Jacket** for
all five requests with **identical full 20-candidate rankings**, not merely the same
top result. All 20 candidates pass. Four outfits tie at **4/5**; the dress/jacket wins
the deterministic role/ID key. This is an intended but limited policy design, not
an arithmetic or candidate-loss defect found in the investigated path. It does not
establish that the winning outfit is independently the most appropriate for each event.

The owner's private database, preferences, photos, account and history were **not
accessed**. Actual private candidate counts/component scores cannot be certified from
the reported winner alone. The finding is reproduced without needing private data.
No production/test source, policy, default or running service was changed.

## 1. Method and retained evidence

Read the compositional interpreter and immutable request, capability compiler/registry,
resolver/evaluator, strict snapshot acquisition, four-structure stream, primary/independent/
public gates, exact request/compatibility/preference calculations, both ranking paths,
preference storage/normalisation/UI, atomic writer, replay and historical presentation.
The production DI bridge selects `CompactAssistantScorer` → `CompactExhaustiveScorer`;
the kernel's old "not selected" module docstring is not the live factory authority.

Evidence is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\context_ranking_diagnosis_20261027
```

- `pure-diagnosis.json`: complete five frames, policies, 100 audited candidate decisions/
  scores, independent arithmetic agreement, compact/reference winner agreement and
  controlled preference/constraint experiments.
- `full-ranking.md` and `five-request-comparison.json`: readable complete ranking and
  exact interpretation comparison. Fractions remain numerator/denominator pairs in JSON.
- `api-final-cases/`: actual authenticated disposable API responses, candidate audits,
  preference change, immutable old-key replay/history and completed-job control.
- `proposed-acceptance.json`: ten future groups plus compatibility guards, explicitly
  **DRAFT / NOT APPROVED / NOT RUN**. No new policy has been frozen or activated.
- Starting hashes/status, native attempts, helper originals and final integrity index.

The pure diagnosis passes with native exit 0. Its 100 candidate scores independently
match a separate exact arithmetic oracle; five compact/reference winner scores agree.
**Two disposable API checks pass in 9.87s**, native exit 0. These include multiple
requests/assertions; they are not a new full regression or model/fashion evaluation.
No new browser, benchmark or application server was launched.

## 2. Synthetic wardrobe and what it represents

These are **author-assigned fixture facts**, not observations of the private garments.
Names come from the request; category/colour/style are explicit disposable equivalents
also used by the accepted prior contract checks. Every row is owned, available,
confirmed and linked to an owned completed job in the disposable API fixture. No
human style review, appearance observation, occasion override or preference is present.
Legacy source provenance is absent/unknown rather than fabricated as human review.

|Stable pure ID|Name|Category|Colour|Saved style|
|---|---|---|---|---|
|G01|Blue T-shirt|short_sleeve_top|blue|casual|
|G02|White Shirt|long_sleeve_top|white|smart casual|
|G03|Black Trousers|trousers|black|smart casual|
|G04|Blue Jeans|trousers|blue|casual|
|G05|Beige Shorts|shorts|beige|casual|
|G06|Navy Dress|vest_dress|navy|smart casual|
|G07|Grey Jacket|long_sleeve_outwear|grey|smart casual|
|G08|Green Sweatshirt|long_sleeve_top|green|casual|

There are three uppers, three lowers, one one-piece and one outerwear item:
`(3 × 3 + 1) × (1 + 1) = 20` candidates. The structures contribute **9 upper+lower,
9 upper+lower+outerwear, 1 one-piece, 1 one-piece+outerwear**. No top/bottom alternative
was discarded to make the dress win.

The pure fixture uses stable G IDs for reproducible complete order. Disposable APIs
use genuine generated IDs; these can change the order of equally scored two-piece
candidates. The dress/jacket wins the maximum numeric tie in either construction
because the `one_piece` role sorts before `upper`.

## 3. The five interpreted requests

All five are Supported and admitted under registry **context-registry-1.4.0**.
Each has `style=null`, `colours=null`, `garment_categories=null`, `formality=null`,
unspecified dress code and role, and no venue/environment requirement. Class does
not invent a student role. A date tonight does not add future/weather evidence.

|Request|Situation → occasion projection|Effective binding / policy|Other retained meaning|
|---|---|---|---|
|I'm going shopping.|`everyday.shopping` → shopping|`shopping_appearance_v1` / shopping-appearance-2.0.0|Activity shopping|
|I'm going to class.|`everyday.academic_attendance` → campus|`campus_day_appearance_v1` / campus-appearance-2.0.0|Activity academic_attendance; disclosed ordinary-class convention|
|I'm going out with friends.|`everyday.casual_outing` → casual_outing|`casual_outing_appearance_v1` / casual_outing-appearance-2.0.0|Activity casual_outing; stated friends|
|I'm going on a date tonight.|`social.date` → date|`date_appearance_v1` / date-appearance-2.0.0|Activity socialising; tonight retained|
|I'm meeting friends for dinner.|`social.meal` → dinner|`dinner_appearance_v1` / dinner-appearance-2.0.0|Activity dining; stated friends|

All five unspecified-code predicates are `saved_style_in {casual, smart casual}`.
The exact declaration target still differs: shopping/campus/casual_outing/date/dinner.
Optional-context admission differs too; for example friends is admitted only in its
approved scopes. Thus the policies are not universally interchangeable. For these
five exact requests and clean fixture evidence, their clothing decisions coincide.

For **each** request: **8 confirmed/available snapshots → 20 structural candidates →
20 mandatory Pass → 20 scored; 0 Fail, 0 Unknown, 0 exclusions**. The winner and
entire order below are identical. Raw frames/spans, supporting rule IDs and occasion
proof values remain different; semantic metadata is not falsely called byte-identical.

## 4. Where context affects the algorithm

|Stage|Actual current effect|
|---|---|
|Interpretation|Constructs distinct situation/activity/occasion slots, timing and companions; rejects unsupported or conflicting meaning.|
|Capability and mandatory eligibility|Chooses the binding, supported role/code/scope and exact declaration target. Every selected member must pass. Applicable Deny wins, malformed authoritative evidence blocks, then clean applicable Allow or admitted saved-style inference.|
|Request score R|A passed occasion contributes a fixed **1**, not an event-specific affinity. For these requests it is the sole scoring field, so every admitted candidate has R=1.|
|Compatibility C|Uses primary-colour relations and saved style overlap between garments. No situation, friends or tonight input.|
|Preference P|Uses one captured global user preference snapshot. Current scoring does not choose a preference profile by occasion.|
|Final ranking|Context can change the winner by changing which candidates survive. It does not directly differentiate the scores of a candidate admitted by all five current requests.|
|Persistence/history|A fresh key ranks and atomically saves its exact request, component metadata, selected members, preferences and provenance. A successful old key replays before interpretation; historical display does not rerank.|

`RequestMatchScorer` and `CompactScoringFacts` agree: the active request fields are
category, colour, style, occasion and formality. Non-style fields receive **1 only
after mandatory verification**. Explicit style is graded by the proportion of base
members matching it; outerwear is excluded from that style proportion. The active
field values are averaged. Multiple constraints inside a field do not create arbitrary
new occasion terms. Timing and companions are not scoring fields.

Therefore these context-only requests reserve the same **3/5** contribution for every
passing outfit. They are numerically distinguished only by C and P. The 60% component
does not measure how much *better for shopping* an admitted outfit is than another.
Explicit colour/category/formality mostly change admission; an explicit style can
also provide graded R after its any-base-member hard gate passes.

A genuinely generic request with no occasion or other scoring fields has raw R
NotApplicable and numeric contribution **0**, not 1. The same fixture then selects
the same dress/jacket at **1/5**, with no preferences. There is no renormalisation of
the unused 60% or 20% weights.

## 5. Full exact ranking, shared by all five requests

Here **R=1** and **P contribution=0 for every row**. P's raw state is NoPreferences,
not evidence that the owner dislikes these outfits. C is the *decision contribution*;
the one-piece's 1/2 is the documented no-pair reference, not measured pair quality.
The weighted terms are `3/5`, `C/5`, `0`, summing to the exact total.

|Rank|Synthetic outfit|C|Weighted C/5|Total|
|---|---|---|---|---|
|1|Navy Dress + Grey Jacket|1|1/5|4/5|
|2|Blue T-shirt + Blue Jeans|1|1/5|4/5|
|3|White Shirt + Black Trousers|1|1/5|4/5|
|4|White Shirt + Black Trousers + Grey Jacket|1|1/5|4/5|
|5|Blue T-shirt + Black Trousers + Grey Jacket|2/3|2/15|11/15|
|6|Blue T-shirt + Blue Jeans + Grey Jacket|2/3|2/15|11/15|
|7|White Shirt + Blue Jeans + Grey Jacket|2/3|2/15|11/15|
|8|White Shirt + Beige Shorts + Grey Jacket|2/3|2/15|11/15|
|9|Green Sweatshirt + Black Trousers + Grey Jacket|2/3|2/15|11/15|
|10|Navy Dress|1/2 reference|1/10|7/10|
|11|Blue T-shirt + Black Trousers|1/2|1/10|7/10|
|12|Blue T-shirt + Beige Shorts|1/2|1/10|7/10|
|13|Blue T-shirt + Beige Shorts + Grey Jacket|1/2|1/10|7/10|
|14|White Shirt + Blue Jeans|1/2|1/10|7/10|
|15|White Shirt + Beige Shorts|1/2|1/10|7/10|
|16|Green Sweatshirt + Black Trousers|1/2|1/10|7/10|
|17|Green Sweatshirt + Blue Jeans|1/2|1/10|7/10|
|18|Green Sweatshirt + Blue Jeans + Grey Jacket|1/2|1/10|7/10|
|19|Green Sweatshirt + Beige Shorts|1/2|1/10|7/10|
|20|Green Sweatshirt + Beige Shorts + Grey Jacket|1/2|1/10|7/10|

The raw colour atom is 1 for identical or achromatic colours, otherwise 0. Grey is
achromatic, so navy+grey has colour atom **1**. Both singleton styles are smart casual,
so their Sørensen–Dice style overlap is **1**. C=(1+1)/2=1 and T=3/5+1/5=4/5.
The jacket's improvement over the dress alone comes from computed pair compatibility
versus the single-piece reference, not date/dinner suitability, warmth or comfort.

Adding outerwear is not universally rewarded: Blue T-shirt + Blue Jeans scores 4/5,
but adding the smart-casual jacket reduces its style agreement and total to 11/15.
There is no blanket jacket bonus.

Both ranking paths compare **total, then R, then C, then P descending**, then the
lexicographically smallest actual tuple of `(role, garment_id)`. The top four have
identical numeric comparison keys `(4/5,1,1,0)`. `one_piece` precedes `upper`, choosing
the dress/jacket. Among the White Shirt/Black Trousers pair and its jacket extension,
the shorter equal-prefix key precedes the longer one. None of these tie rules asserts
contextual or aesthetic superiority.

The disposable API check uses five fresh keys and records five distinct completed
chats, identical score metadata and identical numeric candidate ledgers, with different
context requests. This rules out accidental old-key replay as the cause in the replica.

## 6. Eligibility controls and private-data limits

|Executed disposable control|Result and interpretation|
|---|---|
|Shopping Deny on the dress only|18 Pass, 2 Fail; shopping selects Blue T-shirt + Blue Jeans. Dinner retains 20 Pass and the dress/jacket. This is meaningful context **filtering**, with no new numerical context score.|
|Unknown jacket style|10 base-only candidates Pass; 10 candidates containing it are Unknown. No implicit outerwear permission; an otherwise valid base remains selectable.|
|Hard trousers request plus soft dress preference|12 Pass, 8 Fail; no dress structure survives. Preferences do not override mandatory category requirements.|
|Explicit casual-style shopping request|16 Pass, 4 Fail. R varies between 1 and 3/4 on passing base-style combinations, unlike the context-only requests.|
|Actual disposable linked dress job changed from completed to failed|Strict query returns 7 snapshots, then 18 structural/Pass candidates. A valid top/bottom alternative is selected. No job repair or admission weakening.|

The strict query requires garment owner/available status, an existing processing item
marked confirmed, a matching job owner and **completed job status**. The retrieval layer
also checks category, role/layer consistency and identity/media references. Missing
optional appearance observations do not block ordinary appearance policies.

These controls show that alternative structures are valid under the intended synthetic
equivalent. They do not establish the actual private wardrobe's join/status/style/tag
state. The repeated observed winner alone cannot distinguish identical real candidate
sets from different sets sharing the same top candidate. No private read is necessary
to establish the design limitation; any later record-specific audit needs separate
permission with named minimal fields/queries. No photo, credential or historical chat
content is needed for a basic eligibility audit, and no repair is authorised here.

## 7. Personalisation: current capability and measured effects

|Current positive preference group|Meaning and limits|
|---|---|
|Garment categories|Binary 1 if **any member** has a preferred category/group, else 0. It is not a hard inclusion or exclusion, and does not rank every category individually.|
|Styles|Matching proportion of base members; outerwear excluded. Supported saved labels are used, with Unknown/Partial states where evidence is missing.|
|Colours|Binary match in any selected member, including outerwear. This can reward one preferred colour without requiring the entire outfit to have it.|
|Formality|Uses exact declaration semantics across all members. Smart-casual style alone does not prove this global formality preference. Missing declarations can leave the component Unknown.|

The model has **no typed negative/disliked-category preference or hard category avoid
list**. Unsupported "avoid dresses" prose is not inferred into an exclusion. An
unselected positive category is merely not rewarded. Current hard positive category/
style/colour request constraints and applicable garment Deny are distinct mechanisms.
There is no demographic inference or learned preference in this diagnosis.

Within P, the supported positive group values are averaged by their importance:
`P = Σ(w_group × numeric_group_value) / Σ(w_group)`. Unknown contributes no positive
value; its weight is not silently removed from the denominator. If all are unknown,
the raw summary remains Unknown. No preferences yields raw NoPreferences and numeric 0.
Importance 0 ignores that group. A lone positive group's 0.1 versus 1 importance
cancels in this normalisation; relative importance matters when multiple groups exist.
This internal normalisation does not change the outer 20% weight.

|Explicit synthetic experiment; not inferred owner preferences|Winning outfit|Exact total|
|---|---|---|
|No preferences|Navy Dress + Grey Jacket|4/5|
|Prefer casual style, importance 1|Blue T-shirt + Blue Jeans|1|
|Same lone style group, importance 0.1|Blue T-shirt + Blue Jeans|1|
|Style importance 0|Navy Dress + Grey Jacket|4/5|
|Prefer trousers|Blue T-shirt + Blue Jeans|1|
|Prefer green|Green Sweatshirt + Black Trousers + Grey Jacket|14/15|
|Prefer smart-casual formality, no formality declarations|Navy Dress + Grey Jacket|4/5; P remains Unknown|
|Casual style importance 0.8; dress category 0.2|Blue T-shirt + Blue Jeans|24/25|
|Casual style importance 0.2; dress category 0.8|Navy Dress + Grey Jacket|24/25|

With only dress/jacket available, a soft top-category preference still selects them
at 4/5 with no category reward. That confirms it is not a hard exclusion. Actual
owner preferences are unknown because they were not inspected; the empty baseline
does not assert that the real profile is empty or adequately expresses the owner's tastes.

The API check changes a disposable saved style preference to casual and observes the
winner change to Blue T-shirt + Blue Jeans at 1. The old key and history retain the
original dress/jacket score/provenance exactly. Fresh New Chat can reflect updated
preferences; historical records must not.

## 8. Design comparison: how context could meaningfully affect ranking

Saved style/category facts tell us what is recorded. They do **not** by themselves
establish that casual is universally better for shopping or smart casual for dinner.
Recognised labels need an independently approved objective, user intent or validated
policy to turn those facts into a graded contextual preference. Assigning arbitrary
occasion multipliers would conceal this missing contract.

|Design|Benefit|Required evidence/decisions|Compatibility risks and limitations|
|---|---|---|---|
|A. Context-sensitive R inside 60%|The request component could distinguish how well an admitted outfit fits an explicitly defined contextual objective.|Define a versioned utility and evidence for each relevant objective; for example an explicit saved user intent, not a guessed universal dress rule. Independently label its bounds/Unknown semantics. A candidate must still pass all existing gates.|Replacing occasion's constant 1 changes R semantics and often the effective influence of C/P despite unchanged 60/20/20. Avoid double counting the same intent in R and P. Requires compact/reference/public formula, metadata and replay-version review. Current labels contain no justified universal relative utility.|
|B. Separate suitability contribution or tier|Can make a validated contextual ordering clear, possibly prioritising it before other scores.|An approved, evidence-backed ordinal/cardinal policy and rules for missing facts. A tier needs a meaningful ordering; Pass/Unknown/Fail alone is not a ranking preference.|A fourth weight changes 60/20/20. A tier before total changes the ranking objective even if the displayed formula stays unchanged. Do not let a tier waive Deny, promote Unknown or imply unestablished safety/comfort. Largest acceptance/explanation risk.|
|C. Optional user-configured context preference profiles|The recognised situation selects the user's explicit style/colour/category/formality priorities. Supported saved facts already serve the existing P math; different or shared winners have an understandable cause.|Explicit account-owned configuration and a versioned selector, with bounded five-context scope, no invented defaults and stored selection provenance. Reuse global profile types; no per-garment event grid.|This is context-conditioned personalisation, not universal suitability validation. Missing configuration can legitimately preserve the current same result. The outer P budget remains 20%; explicit hard requests and gates still dominate admission.|
|D. Optional diversity|May reduce repetition for users who explicitly want novelty among already eligible options.|A separately approved deterministic history/seed contract, scope/window and replay rules; preferably an explicit alternative-view action.|Does not establish context suitability and cannot fix this root cause. Penalising a recent winner changes ranking; randomness breaks reproducibility without stored state. Not requested for implementation.|

**Recommended first design: C**, with an explicit versioned selection contract and
truthful explanations. It grounds a distinction in what the user actually wants,
rather than asserting new fashion/comfort knowledge. If the desired product instead
requires system-supplied occasion utility in the **60% request component**, choose A
only after approving its evidential basis, numerical/Unknown contract and labels.
Retaining the numbers 60/20/20 is not evidence that a new R formula is unchanged.

No design should force five winners. Equivalent profiles/evidence may return the same
outfit, and a strong global preference may legitimately win across several situations.
Without a new objective or evidence, identical rankings are the honest result.

## 9. Concrete proposed contract and files for recommended C

**Proposal only; not approved or implemented.** Suggested contract names:
`context-preferences-1.0.0` for bounded account JSON and
`context-preference-selection-1.0.0` for immutable ranking-time selection proof.
A separate server-only `context_profiles_v1` preference mode would be default-off;
the current `global_v1` selection stays the default. Keep the existing compatibility
policy, numerical R/C/P formula and 60/20/20 weights; disclose the new input-selection
semantics in provenance instead of silently changing the old global path.

- Initially map only the five approved ordinary semantic IDs. No new NLP, activity,
  specialist policy, garment field or style review is needed.
- A context chooses **inherit_global** or a **custom** profile made from the existing
  four supported positive groups. An absent profile inherits global explicitly.
  A deliberately empty custom profile means no active preferences for that context;
  it must not silently resurrect global values. Weight 0 keeps its existing meaning.
- Validate bounded keys/version/values/weights and owner. Malformed/foreign/unknown
  versions fail safely, rather than silently choosing a permissive profile.
- Capture the raw and selected immutable preference snapshot, semantic ID, selection
  mode/version/hash and normalised values at ranking time. Explain the owner-selected
  basis beside the still-provisional saved-style appearance basis. One snapshot/read
  per request; prepare facts before enumeration.
- Reuse existing preference JSON storage/endpoint where feasible; no migration or
  old-row backfill. Old clients/global rows and old history remain readable. No
  automatic category exclusions or new negative-preference semantics are bundled.

The concrete **proposed existing-file review scope**, subject to final design approval:

|Owners|Paths and reason|
|---|---|
|Shared account/API/T|`backend/app/domain/value_objects/requests.py`; `backend/app/application/account/account_service.py`: bounded versioned preference payload/validation/options through existing authenticated account actions.|
|Shared composition/R|`backend/app/infrastructure/workflow_runtime.py`; `backend/app/application/recommendation/outfit_assistant_service.py`; `assistant_execution_selection.py` in the same recommendation directory: explicitly select the opt-in preference strategy and persist its immutable provenance.|
|R scoring/integration|`backend/app/application/recommendation/compact_assistant_scorer.py`; `compact_exhaustive_scorer.py`; `aggregated_decision_scorer.py` in the same directory: pass/select the same prepared preference snapshot in compact and reference paths; preserve arithmetic/gates.|
|Shared frontend|`frontend/lib/api.ts`; `frontend/app/profile/page.tsx`; `frontend/components/RecommendationResult.tsx`: optional account-owned context profiles, Save/Cancel/error handling, selected-profile explanation and old-history rendering.|

Proposed new modules are
`backend/app/application/recommendation/context_preference_selector.py` and
`backend/app/domain/value_objects/context_preference_selection.py`; proposed bounded
configuration is `backend/app/application/recommendation/config/context_preference_profiles.v1.json`.
That configuration may enumerate allowed IDs/contracts, **not invent preference values**.
These filenames define a reviewable proposed boundary, not permission to edit them.

Current `PreferenceScorer`, `PreferenceNormalizer`, active-preference SELECT adapter,
strict garment query, central writer and history can be reused if their existing
contracts suffice. Any concrete need to change them must be named/justified before
editing. Do not infer a broad writer/storage authorisation from primitive reuse.

Choosing A instead additionally requires a separately named utility configuration/
resolver and explicit changes to `request_match_scorer.py`, `compact_scoring_facts.py`,
their independent/public verification and versioned score/provenance interpretation.
Choosing B additionally affects `candidate_ranker.py`, compact `numeric_key` comparison,
score/persistence codecs and displayed ranking meaning. Neither is a config-only alias.

R/supervisor/evidence owners must approve intent/evidence/Unknown semantics and labels;
shared account/API/storage owners must approve the preference writer/payload contract;
frontend owners must approve UI/history changes. Existing frozen manifests/labels need
an exact named transition, retained originals and separately authored acceptance data.
No such production authorisation is inferred from this diagnosis request.

## 10. Focused acceptance plan and limits

The ten groups in `proposed-acceptance.json` cover the requested future criteria:
distinct explicitly supported context intent can change winners; equivalent intent
can share a winner; genuine graded R is tested **only if A is chosen** (C intentionally
leaves R unchanged); preference edits; hard constraints; Deny; Unknown; deterministic
ties; exact metadata/history; bounded 100-garment work. Add old-profile/no-custom-profile,
malformed/foreign/version, custom-empty, optional UI and W/AP/IP compatibility controls.
Future filenames can be `test_context_preference_selection.py`,
`test_context_preference_ranking.py` and `context-preference-ranking.spec.ts`, with
separate approved fixtures/source transition and exact existing-test adaptations named
before any edit. These test names/groups are proposals, not executed checks.

For a meaningful labelled contrast, an explicitly configured synthetic owner may
prefer casual for shopping and smart casual for dinner. That is an owner-intent
fixture, not evidence that those are universal event requirements. A second fixture
must intentionally use equal profiles and accept a shared winner. Independent expected
fractions must be authored before patching; do not ask the new scorer for its oracle.

Performance acceptance uses retained 100-garment populations and the unchanged search
bound `(upper × lower + one_piece) × (1 + outerwear)`. Compile/select only the active
context profile; do not evaluate all contexts per candidate. Keep per-member facts and
bounded caches prepared before enumeration, with no candidate-loop DB/config/model/
network work. Add changed-path measurements only for an identified concern. No new
capacity population or formal NFR acceptance is established by this read-only review.

Retained diagnostic attempts: the first pure helper's extra controls replaced flat
request fields without updating their immutable frames, correctly yielding unavailable
controls. It now parses supported complete phrases; originals remain. The first API
attempt recorded one pass/one failure because it compared whole audits, including the
deliberately different occasion proof values. The final check compares the full candidate
identities/decisions/exact scores while separately asserting all five distinct occasion
projections. No production assertion/policy was weakened; both attempts and disposable
databases remain. Cached dependencies were used offline; a small probe environment
materialised cached packages, with no network download or repository dependency change.

**Disposition: diagnosis/design complete; stop before implementation.** The current
system provides bounded contextual admission, not differentiated ordinary contextual
utility ranking. No production source, existing test/oracle, policy, model, private
record, default or service was changed. Whole-FYP acceptance remains NOT READY;
the original 155 rows remain 144 Verified / 2 Partial / 9 Unverified / 0 Blocked,
RN-13 remains Partial and NFR-02 OPEN / NOT FORMALLY ACCEPTED. Await owner review of
the design; do not begin another phase or activate a new preference/scoring policy.
