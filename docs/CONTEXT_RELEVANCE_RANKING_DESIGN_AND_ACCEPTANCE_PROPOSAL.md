# Evidence-based context relevance: Option A design and acceptance proposal

2026-10-27, Asia/Kuala_Lumpur. **Design complete; production implementation and
policy activation are not authorised.** The owner's direction is Option A, context-sensitive
request matching. Optional context preference profiles are a later possibility, not
a prerequisite or the primary recommendation in this proposal. The previous diagnosis
and its Option C recommendation remain unchanged as historical documents.

**Recommendation:** use a new, explicitly versioned R that measures alignment with an
authorised appearance objective, after all existing mandatory gates. Pursue **A1,
an evidence-backed server-authored objective catalogue**, for automatic use; allow
**A2, an existing explicit style request**, to provide a direct objective without any
per-occasion profile. Defer A3 until suitable data and independent model evidence exist.

There is a real boundary: current saved attributes can measure a specified style
objective, but the five broad event names do not establish which relative style
objective is justified. **No automatic casual-versus-smart-casual mapping for those
five bare names is established by the evidence currently supplied.** This report
does not invent such mappings to manufacture different winners. A1 policy evidence
and ownership approval are a separate release gate, not something a new formula proves.

The mathematical design retains **T = 3/5 R + 1/5 C + 1/5 P**. It removes automatic
maximum R for passing an occasion gate. It also defines a conservative missing-evidence
comparison, exact duplicate-objective handling and full component explanations. These
are substantive, proposed score/selection semantics requiring explicit approval.

## 1. Scope, evidence and actual work performed

The accepted diagnosis established, on an explicit synthetic equivalent of the eight
named garments, 20 passing candidates per request, identical full rankings, four
numeric ties at 4/5 and the Navy Dress/Grey Jacket winner through role/ID tie-breaking.
It also verified preference effects, strict processing joins and immutable replay.
That is retained historical evidence; those runs were **not rerun or pooled here**.

This task inspected the current request scorer, compact facts/kernel, ranker, profile
selection, score codec/display, immutable score/outcome/write contracts, locked writer
and existing source/provenance boundaries. Public dataset descriptions were checked
for the A3 feasibility discussion. No production or existing test file was edited;
no app/model/browser/regression/benchmark was started. No private DB, account, image,
preference or historical response was accessed. Running services were not changed.

Evidence is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\context_relevance_design_20261027
```

`independent-proposed-oracle.json` contains 20 hand-authored candidate rows under two
hypothetical, explicitly supplied objectives, plus 21 proposed acceptance cases.
Its status remains **DRAFT / NOT APPROVED / NOT RUN AGAINST AN IMPLEMENTATION**.
A stdlib Fraction document check verifies 40 written point totals, four uncertainty
bound examples and one preference example. This is arithmetic checking of a proposal,
**not a new ranker implementation, passing functional suite or fashion evaluation**.
`context-objective-readiness.json`, `proposed-scope.json` and public source notes retain
the evidence/authority gaps and exact future file boundary.

## 2. Objective: five different concepts

|Concept|Meaning in this proposal|
|---|---|
|Hard eligibility E|Owned, available, confirmed/completed processing; structural completeness; explicit category/colour/style/formality requirements; admitted contextual scope; Deny/malformed/Unknown rules. A non-Pass candidate cannot buy its way into scoring.|
|Relative context relevance R|Degree of alignment with an independently authorised appearance objective for this request. A Pass is permission to consider an outfit, not maximum relative relevance.|
|Compatibility C|Relations between garments under the existing colour/style compatibility decision policy. It does not decide what the situation calls for.|
|Preferences P|The user's independent global taste priorities. No demographic inference, mandatory occasion profile or fabricated preference. Identical semantic tests already paid for in R are suppressed explicitly as described below.|
|Unknown/unsupported evidence|Missing facts or an unjustified objective remain unresolved. They are not casual by default, a neutral fashion judgement or a positive suitability score.|

The result remains one complete outfit satisfying the current gates, or a controlled
no-result outcome. No diversity objective, weather service, movement/comfort proxy,
gender convention, footwear completeness or general aesthetic certification is added.

## 3. What the currently available facts can establish

|Input|Permitted use|What it cannot establish|
|---|---|---|
|Supported saved singleton style|Measure alignment with an authorised canonical style target. Reuse the existing current-source/malformed barriers; unreviewed labels stay provisional.|
|Category/structural role|Existing four structures and explicit hard category requirements. A separately stated composition objective could be designed later.|Comfort, mobility, quality, formality or event suitability merely because something is a dress, trousers, shorts or outerwear.|
|Primary colour|Existing hard colour proof, compatibility and preferences.|A context palette, climate response or cultural/event colour rule without a supplied applicable objective.|
|Exact occasion/formality declarations|Existing scoped authoritative Allow/Deny and admission evidence.|A relative ordering: Allow has no numeric strength and is not a reason to beat an otherwise eligible inferred candidate.|
|Current owner style review|Truthful record that the owner reviewed the saved value.|A utility bonus, universal expertise, continuous physical verification or calibrated model accuracy.|
|Appearance observations|The actual reviewed collar/tailoring/structure/dated condition facts where their accepted contract applies.|Automatic ordinary-context utility, professionalism, fit or comfort. Initial R does not consume these interview-only observations.|
|Explicit user style request|A direct, attributable appearance objective already represented by `request.style`; its existing hard semantics remain.|Permission to drop another hard constraint or silently reinterpret casual formality as casual style.|
|Model/source metadata|Truthful origin and currency of saved information.|Confidence-as-human-review, calibrated contextual relevance or automatically known missing attributes.|

"Known" in the proposed utility arithmetic means **a known match to a recorded
label under the admitted source contract**, not independent truth about a photograph
or fashion judgement. Valid saved/unreviewed and model-reported labels receive the
same utility as equivalent reviewed labels, with different verification disclosures.
Review timestamps and confidence do not earn points. Absent legacy source metadata
retains unknown origin; present malformed/stale metadata cannot supply positive R.

The local development detector can return unclassified/missing-style information.
No ranking design can create those missing facts. No new garment attributes, automatic
review events, source confidence thresholds or CV/VTON changes are part of this scope.

## 4. Relative-objective readiness for each ordinary context

|Context|What its bare request currently establishes|Defensible relative objective now|What would permit A1 automatic grading|
|---|---|---|---|
|Shopping|Ordinary shopping; no code, transport, movement or climate requirement.|No established default. A specified appearance style can be measured.|An applicable authored appearance objective with independent rationale/labels; no "comfortable shorts" or mobility inference from categories.|
|Ordinary campus attendance|Ordinary academic attendance convention; no student role, lab/PE/uniform or institutional code.|No established default. Explicit style is measurable.|An applicable, approved appearance objective for the actual scope. A guideline from one institution cannot be applied to all campus requests without that scope being established.|
|Casual outings|An ordinary activity, possibly stated friends.|No established default. The activity name does not currently assert `style=casual`.|Independent semantic/policy justification before converting an activity name into a soft appearance objective. Friends is not fashion evidence.|
|Date|Social date, possibly tonight; no universal dress code/venue.|No established default. Explicit style is measurable.|An approved appearance objective and its applicability. Do not infer upscale venue, dressy clothing, gendered clothing or a night-weather condition.|
|Dinner|Dining, possibly friends/plain restaurant in supported scopes.|No established default. Explicit style is measurable.|An applicable approved objective; dinner or a plain restaurant does not itself prove a smart-casual or formal preference.|

The current appearance-2.0.0 policies authorise broad positive admission from casual/
smart-casual labels. They do not authorise a graded preference between those styles.
Two contexts with the same justified objective/evidence may correctly retain identical
rankings. Until an objective is justified, this proposal does not call them different
merely because their names differ.

## 5. Proposed mathematical contract

Suggested selected score profile: **`context_relevance_decision_v1`**, with mathematical
policy **`context-relevance-policy-1.0.0`**. The old `experimental_compatibility_decision_v1`
continues to mean its current formula; historical scores are not redefined.

### 5.1 Resolve an objective without changing interpreted facts

Initially support one reusable operator: **base-member canonical style alignment**.
No arbitrary category/colour utility coefficients or new physical facts are needed.

1. Run existing interpretation, capability/code/scope admission and mandatory gates.
2. An existing explicit `request.style` supplies A2's target, if supported. It keeps
   its existing any-base-member hard gate. The new R measures degree of alignment
   beyond that minimum, rather than awarding the minimum again.
3. Otherwise resolve an independently approved A1 catalogue entry for the exact
   supported situation/scope. Initial automatic entries apply only when code/formality
   are unspecified; explicit codes need their own relative-objective applicability.
4. Explicit style takes precedence over a conflicting server style objective. It is
   one objective, not an extra term added to the default. Equivalent objectives are
   deduplicated. Do not turn a soft policy goal into a new hard dress code or fill
   `request.style`/`formality` as though the user stated it.
5. If neither supplies a defensible objective, return the no-objective state below.

The existing supported phrase **“Suggest an outfit for shopping with casual style”**
already supplies explicit style; **“Suggest a casual outfit”** still means the original
formality request. Initial A2 therefore needs no new NLP or preference-profile UI.
Richer soft-goal wording would require a separately named NLP/request-contract increment.

For outfit O, let B(O) contain the one-piece, or the upper and lower. For target t:

```text
m(g,t) = 1  if a current admitted singleton saved style matches t
         0  if that current singleton style is known and does not match t
         Unknown otherwise

R(O,t) = sum(m(g,t) for g in B(O)) / |B(O)|     when every required m is known
```

A matching dress yields 1; two matching base members yield 1; one matching base
member out of two yields 1/2. Adding outerwear never directly changes R. Selected
outerwear still has to pass every mandatory contextual requirement, and remains
included in existing C and applicable P calculations. There is no R no-pair midpoint.

This is a **goal-alignment fraction**, not a probability of appropriateness. A value
of 1 means full alignment with the specified recorded-style objective, not perfect
fashion, comfort or venue compliance.

For a later independently approved multi-objective policy, the general form would be
`R = Σ(a_j q_j) / Σ(a_j)`, with fixed positive rational weights, unique semantic tests
and no missing-term renormalisation. **The initial scope does not activate that broader
operator/weight language.** Start with one style objective and weight 1.

### 5.2 Hard requirements do not earn artificial bonuses

Category, colour and formality requirements retain their current hard meanings. Passing
them does not add constant 1 terms to this new R. Passing occasion does not add one
either. Explicit style is different: its current hard gate requires at least one base
match; measuring one-of-two versus two-of-two matches supplies genuine additional
degree information from the user's stated objective.

An authorised soft default can have R=0 while the outfit remains hard-eligible. There
is **no hidden minimum R threshold**: a point-score winner can still be selected if
every known candidate has R=0, but the explanation must say the appearance objective
was not matched. That is different from having no objective or missing evidence.

### 5.3 C, P and duplicate semantic tests

Keep the current compatibility decision contribution C, including its declared
midpoint conventions and single-piece reference. Do not call a conventional C value
measured certainty. Do not put pairwise colour/style compatibility into R as well.

Retain the existing global preference groups, exact weights and Unknown rules, with
one explicit **new-profile-only** deduplication rule. Canonicalise a semantic test by
its attribute, target set, selected-member scope and aggregation. If a P test is exactly
the test already used for R—for example the same casual-style/base-mean predicate—
suppress that duplicate P term. A conflicting/different preference is not automatically
the same test. More complex equivalence must be specified, not guessed from text.

For positive active group weights b_k and suppression mask d_k:

```text
P_independent = Σ(b_k d_k p_k) / Σ(b_k)
d_k = 0 for an exactly duplicated R test, otherwise 1
```

Unknown p_k supplies no positive value under the existing preference convention.
The original positive-weight denominator is retained: do not silently increase other
groups' influence when a duplicate is suppressed. With no preferences P remains
NoPreferences/0. If all active tests are suppressed, mark P NotApplicable with an
explicit duplicate-suppression reason and numeric contribution 0; do not claim the
user has no taste or the evidence is missing. Raw preferences stay in the snapshot.

This **changes P treatment as well as R** and requires explicit approval under the
new profile. It is not described as unchanged legacy preference semantics. The outer
weights remain 3/5, 1/5, 1/5, with no redistribution of an unused contribution.

R's absolute target match and C's garment-to-garment relation can use the same style
labels for different questions. They can be correlated; no statistical independence
is claimed. The rule forbids paying twice for an identical semantic test, not all
reuse of an input. Reviewed-source quality and Allow do not become extra bonuses.

### 5.4 Unknown facts: logical bounds, not fabricated scores

An applicable clean Allow can admit a garment whose style is missing. It supplies
permission, not the missing style needed for R. Invalid source metadata or ambiguous
style also cannot create a positive match. Do not silently discard such admitted
candidates and then claim another outfit is the best contextual match.

For n base members, k known matches, z known non-matches and u unknowns:

```text
R_low  = k/n
R_high = (k+u)/n
R is a point only when R_low = R_high

T_low  = 3/5 R_low  + 1/5 C + 1/5 P_independent
T_high = 3/5 R_high + 1/5 C + 1/5 P_independent
```

An unknown member has not earned R=1: its upper bound only describes an unresolved
possibility. No midpoint, confidence multiplier or random imputation is used for R.
These are logical missingness bounds over recorded-label utility, **not statistical
confidence intervals** and not uncertainty calibration for CV errors. C still follows
its separately approved decision convention.

Proposed selection rule:

- Among candidates with point R, compare exact `(T,R,C,P)` descending, then actual
  `(role,garment_id)` key ascending, as today.
- For each non-point candidate form the same **optimistic comparison key** using
  `(T_high,R_high,C,P)` and its actual garment key. This key is only a blocker bound.
- Select the best point candidate only if its exact comparison key wins against
  every non-point candidate's optimistic key. Equality is resolved by the same
  role/ID ordering; an unresolved candidate that could win the tie blocks selection.
- If no point candidate exists, or an unresolved candidate could outrank it, return
  `InsufficientEvidence` with reason **`relative_ranking_evidence_unknown`** and a
  ranking-stage explanation. Do not persist an unknown candidate as a scored winner.

All-known inputs therefore retain the exact deterministic tie rule. Mixed missing
inputs introduce a **versioned withholding rule**, not a silent change to the old
comparator. No artificial diversity or recency penalty is included.

### 5.5 No defensible objective

If no A1 objective or explicit A2 style objective exists, the new profile returns
`PolicyUnavailable` with reason **`context_ranking_objective_unavailable`**. Do not
invent R=1, set R=0 and present the resulting total as contextual suitability, or
silently return a generic result under the original context label.

The existing appearance/compatibility profile remains separately available and stays
the current default until new activation is approved. A user-visible fallback choice
would need an explicit request/key/UI contract; it is not silently added here. A
supported explicit style can resolve an objective in a fresh interaction. This is
occasional request clarification, not mandatory per-garment review or occasion profiles.

Unsupported contexts/codes retain their existing refusal before this ranking stage.
No-objective is distinct from a missing garment style, a failed hard requirement, an
empty wardrobe, a known R=0 mismatch, malformed policy, or a technical failure.

## 6. A1, A2 and A3 feasibility

|Dimension|A1: authored evidence-backed catalogue|A2: owner/user-provided objective|A3: calibrated model/data approach|
|---|---|---|---|
|Available data|Saved labels exist; justified relative mappings for the five bare contexts have not been supplied.|Existing explicit style is directly attributable and already parsed.|No calibrated five-context utility model/evaluation is established in the inspected ranking contracts.|
|CV dependence|Can use current saved labels provisionally; real label accuracy remains a separate limitation.|Same; no new model required to interpret a known style goal.|Needs reliable inputs or an independently evaluated image model as well as contextual target data; upstream error and context error must be separated.|
|Complexity|Moderate engineering plus genuine policy/evidence work.|Low extra input mechanism initially, sharing the proposed score/Unknown/version infrastructure.|High: dataset rights/provenance, annotation, leakage control, training/calibration, deployment and drift evaluation.|
|Automatic usefulness|No recurring profile setup once a justified context entry is activated.|Requires an explicit style when the context has no justified default; no stored per-occasion setup.|Potentially automatic, only if trained/evaluated on the relevant context objective and wardrobe scope.|
|User input|No new garment reviews or mandatory personal profiles; app owners supply the policy.|An optional supported style phrase, or an applicable authoritative objective supplied for a specific scenario.|Could avoid goal entry, but missing scene/role/code facts cannot responsibly be invented.|
|Explanation|Goal source, applicability, matching saved facts and exact fraction.|User's own target, base-member matches and existing constraints.|Requires calibrated output interpretation, coverage/abstention and faithful explanations; model confidence alone is insufficient.|
|Independent validation|Separate objective justification and held-out context comparisons; synthetic fraction checks validate only mechanics.|Validate parsing/intent and arithmetic; do not claim matching a user target is independent fashion approval.|Context-labelled held-out data, garment/source-disjoint splits, annotation reliability, calibration/abstention and baselines.|
|Main risk|Disguising an arbitrary style preference as a fashion fact.|Useful intent matching may still not satisfy fully automatic bare-context ranking.|Learning compatibility/popularity or synthetic rule labels and calling that validated contextual suitability.|

The [Fashionpedia publisher's description](https://github.com/cvdfoundation/fashionpedia)
describes clothing categories, parts, attributes and segmentation annotations.
**Design inference:** those annotations do not by themselves validate a relative
shopping-versus-dinner utility for this app.

The [Polyvore dataset author's description](https://github.com/xthan/polyvore-dataset)
documents fill-in-the-blank and compatibility prediction tasks and notes unavailable
original image URLs. **Design inference:** compatibility labels are not evidence that
an outfit is relatively better for these five situations; reproducible input access
also needs assessment. This is a limited primary-source check, not an exhaustive
dataset survey or a licensing determination. No data or models were downloaded.

**Practical recommendation:** pursue A1's evidence pack and the bounded Option A
mechanism; use A2's existing explicit style as a transparent bootstrap when necessary.
Do not introduce A3 solely because the FYP includes AI, and do not relabel the existing
compatibility model/task as contextual suitability. Option C remains optional later.

## 7. Independent synthetic examples and expected outcomes

Use the same author-assigned G01–G08 fixture as the retained diagnosis: three uppers,
three lowers, one navy smart-casual dress and one grey smart-casual jacket; the other
saved styles/colours are fully listed in that earlier report. These are disposable
facts, not observations or preferences inferred from the private wardrobe.

The examples below **supply their appearance objective explicitly as part of the
scenario's authority**. They do not establish production mappings "shopping means
casual" or "dinner means smart casual". Those mappings remain unapproved A1 hypotheses.
The supplied objective is what justifies the mathematical distinction.

|Case|Independent expected calculation/outcome|
|---|---|
|Different justified goals|With an authorised casual appearance objective, Blue T-shirt + Blue Jeans has R=1,C=1,P=0,T=4/5; dress/jacket has R=0,C=1,T=1/5. With an authorised smart-casual objective the values reverse; dress/jacket wins the smart numeric tie by the preserved key.|
|Equivalent date/dinner objectives|If both independently specify the same smart-casual goal, the same full scores and dress/jacket winner are legitimate.|
|No authorised objective|The five bare event names alone do not create different R values. Under the new profile, no-objective refusal is expected until justified; the legacy profile is not redefined.|
|Partial alignment|Blue T-shirt + Black Trousers has R=1/2 under either singleton-style goal and C=1/2, so T=2/5. With Grey Jacket, C=2/3 and T=13/30.|
|Independent preferences|Under a casual goal plus a global green-colour preference, Green Sweatshirt + Blue Jeans has R=1,C=1/2,P=1,T=9/10 and can beat Blue T-shirt + Blue Jeans at 4/5. Colours are independent of this R predicate.|
|Hard constraint|Under a smart goal, a hard trousers requirement excludes both dress structures even with a dress-category preference. White Shirt + Black Trousers wins at 4/5.|
|Deny|A matching outfit containing a member with exact applicable Deny is excluded before R/C/P, even if its hypothetical utility is 1.|
|Unknown before admission|A missing-style dress without applicable Allow stays mandatory Unknown; no new R can rescue it.|
|Unknown after Allow; resolvable|Allow admits a style-missing dress. Dress/jacket has R in [0,1], existing C=3/4, P=0, T in [3/20,3/4]. Known White Shirt + Black Trousers at 4/5 provably wins. No positive R was invented for the dress.|
|Unknown that can change the winner|Add an independent dress-category preference: that unresolved dress/jacket has T in [7/20,19/20], which could beat the known 4/5 outfit. Withhold relative selection rather than quietly dropping it.|
|Unreviewed/model origin|Equivalent admitted labels get the same target-match arithmetic, with truthful provisional origin. No fabricated review/time or confidence bonus. Invalid/stale source cannot supply positive R.|
|Exact duplicate preference|Casual goal plus exactly equivalent global casual-style/base-mean preference suppresses the duplicate P contribution. Blue T-shirt + Blue Jeans stays 4/5 rather than being paid twice to reach 1.|

The external oracle contains **all 20 candidate rows under both hypothetical goals**,
not just selected examples. For explicit A2 style requests, apply the existing hard
style gate as well: the retained diagnosis established 16 Pass for an explicit casual
style. Do not score all 20 as hard-eligible merely because the soft-goal table has 20 rows.
Expected arithmetic is authored independently before any future scorer patch.

## 8. Evidence needed to activate A1

An objective entry needs a named policy/evidence owner, exact context/role/code/venue
applicability, the intended appearance objective, admitted facts and source rules,
scope limitations, independent comparison labels and a revision/hash. Record whether
its basis is a normative product goal, applicable external requirement or empirical
relative-judgement evidence. An owner's approval makes a product convention explicit;
it does not convert that convention into independent fashion science.

Proposed review process, not performed here:

1. Write scenario definitions before labelling outfits. Do not assume absent venue,
   code, role, activity or demographic facts. If the broad event is underdetermined,
   keep its automatic objective unavailable.
2. Have the policy owner and an independent reviewer assess whether a relative target
   is justified by admitted facts, and supply reasons/counterexamples. Reviewers must
   be allowed to answer "no justified ordering". Do not expose computed ranks as the
   ground truth they are asked to endorse.
3. Separate development examples from held-out garments/scenarios and report ties,
   disagreement, missing-evidence cases and source errors. Agree the evaluation
   population and acceptance criteria with the supervisor before execution; no
   universal fashion-accuracy target is invented here.
4. Activate only entries whose scoped rationale and independent labels are accepted.
   Disagreement or scope mismatch is a reason to withhold that objective, not average
   unsupported judgements into a confident utility.

The eight named synthetic garments are sufficient for arithmetic and invariants,
not independent validation of event appropriateness. A3 additionally needs lawful
context-labelled data, protected held-out calibration/evaluation, deployment inputs,
abstention criteria and comparison with this transparent rule baseline. A small set
of labels generated from the rules cannot validate a model as discovering those rules.

## 9. Proposed versions, activation and stored proof

|Contract|Proposed identity / boundary|
|---|---|
|Selected score profile|`context_relevance_decision_v1`; outer weights remain 3/5,1/5,1/5.|
|Math/selection policy|`context-relevance-policy-1.0.0`; exact style alignment, duplicate suppression and missing-evidence decision rule.|
|A1 catalogue|`context-relevance-objectives-1.0.0`; separate immutable revisions/hashes. No justified entries are supplied as active defaults by this report.|
|Evidence/plan proof|`context-relevance-evidence-1.0.0`; objective authority, selected members/source currency, matches/non-matches/Unknowns, bounds and snapshot identity.|
|Explanation|`context-relevance-explanation-1.0.0`; separate from the current admission explanation.|
|Display|`assistant-scoring-display-2.0.0`; exact R/C/P values, raw states, numeric contributions, weights and total, with suppression/convention notes.|
|Capabilities|`context-ranking-capabilities-1.0.0`; distinguish supported admission from available relative objectives and per-wardrobe evidence.|

A proposed process-only `SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE` would default
to disabled. Selecting the new mode requires the general context profile and existing
experimental decision C/P baseline; invalid combinations fail, not silently switch
to the deferred 70/0/30 profile. An explicit profile resolver applies new R only to
the five ordinary situations; wedding/AP/IP and generic requests retain their current
profile/path, and inactive situations retain their current refusals. Record the
actual selected profile per result. This is a proposal, not a setting changed here.

Grammar/taxonomy 1.3.0 and admission registry 1.4.0/appearance-2.0.0 retain their meanings.
Do not put new graded relevance into the same versioned admission explanation or
silently change historical totals under `experimental_compatibility_decision_v1`.

Successful results retain exact point R, existing C decision, independent P and the
complete immutable objective/source/preference proof. Unknown competitors contribute
a bound certificate (counts/max blocking key or bound), **not a persisted positive R**.
No-objective/uncertain ranking returns a controlled outcome with a separate
`ranking_summary`; it must not falsely mark the existing admission capability unavailable.

Exact JSON fractions are authoritative; SQL REAL fields remain projections. The new
display API should project numerator/denominator as decimal **strings**, so a browser
does not round large exact integers through JavaScript Number. Render the stored
fractions/weighted terms; any optional decimal is labelled approximate. Older numeric
ratio formats remain supported by their original versioned reader. Null/Unknown is
not a measured zero, and a raw missing C is not its midpoint decision contribution.

Bound the new catalogue to five semantic IDs, one style operator/target per plan and
64 KiB of configuration, consistent with bounded configuration loading. The result
proof needs only winning members and at most one strongest unresolved blocker, plus
counts/digests, not the full candidate list. Exact display/proof size limits must be
checked against existing valid fractional preference weights before being approved;
never truncate or convert an overlong fraction to an unlabelled float.

Old-key
lookup still occurs before interpretation/selection and returns the original score.
New historical decoders must validate stored/archived allowlisted policy revisions,
not reinterpret a record with the currently active catalogue. No executable JSON,
unapproved operators, arbitrary paths or unbounded expressions are accepted.

The winner is optimal under the captured ranking-time facts and numerical conventions.
The existing locked writer revalidates selected garment snapshots; this proposal does
not claim all competitors or preferences are frozen until commit, or expand that
transaction guarantee silently. Objective/profile revisions are captured like the
ranking-time preference snapshot. A changed selected snapshot still rejects/rolls back.

## 10. Exact proposed source and ownership scope

**Not permission to edit.** The proposed minimum is **20 existing production files
(16 backend, four frontend), six new production files**, plus named new verification
files. `proposed-scope.json` retains each exact path. No production file is added now.

|Owner / area|Existing proposed paths and responsibility|
|---|---|
|R selection/integration|`backend/app/application/recommendation/assistant_scoring_selection.py`; `assistant_execution_selection.py`; `compact_assistant_scorer.py`; `outfit_assistant_service.py` in that directory: new profile dispatch, scoped goal resolution, controlled rank-stage outcomes and stored provenance.|
|R exact scoring|`backend/app/application/recommendation/request_match_scorer.py`; `compact_scoring_facts.py`; `compact_exhaustive_scorer.py`; `aggregated_decision_scorer.py`; `preference_scorer.py` in that directory: public/compact/reference R, independent verification, unknown-bound selection, exact duplicate mask. Keep legacy formulas and weights unchanged.|
|Shared score/API display|`backend/app/application/recommendation/decision_score_codec.py`; `scoring_display.py`; `backend/app/api/recommendation_routes.py`: explicit new-profile codec/capabilities/display dispatch, preserving old formats.|
|Shared R/T immutable write contracts|`backend/app/domain/value_objects/ranking_outcome.py`; `recommendation_persistence.py` in that directory; `backend/app/infrastructure/persistence/recommendation_repository_adapter.py`: typed ranking evidence/proof validation and stored revision-aware reading. Preserve transaction, owner/key checks, selected-snapshot validation and existing insert/replay behaviour. No schema/data migration.|
|Shared composition|`backend/app/infrastructure/workflow_runtime.py`: default-off server selection and compatibility validation.|
|Shared frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`: typed rank-stage states, objectives, source disclosures and full component breakdown/history rendering. No redesign before approval.|

Proposed new production paths:

```text
backend/app/application/recommendation/context_relevance_policy.py
backend/app/application/recommendation/context_relevance_scorer.py
backend/app/application/recommendation/context_relevance_verifier.py
backend/app/domain/value_objects/context_relevance.py
backend/app/application/recommendation/config/context_relevance_policy.v1.json
backend/app/application/recommendation/config/context_relevance_objectives.v1.json
```

These are reusable ranking policy/measurement/verification contracts, not event-specific
interpreters or separate scorers per occasion. Existing mandatory interpreter/evaluator/
resolver/registry, strict query, four structures, automatic Add, quota, garment fields/
review/central writer, account preference UI, auth/logout and CV/VTOFF/VTON remain
outside this proposed initial change. `CandidateRanker`'s point tie rule and the old
compatibility policy can be reused. New request wording, physical attributes, account
context profiles or additional operators require separately named scope/authority.

R/supervisor/evidence owners must approve the mathematical objective, objective basis,
Unknown withholding rule, duplicate-P change, labels and actual A1 applicability.
Shared API/contract/storage owners must approve proof/codecs/history boundaries;
frontend owners must approve typed explanations/component display. Approval of the
product direction alone is not approval of these concrete semantics or shared files.

## 11. Transparency and current UI limitation

The current UI exposes an overall ranking fraction and C details, but not a complete
separate R/P breakdown. That limitation was confirmed by source inspection. No UI
code has been changed in this task. The eventual result should show:

- Objective and authority: user-stated style or a named approved appearance convention;
  distinguish this from a dress code the user did not supply.
- Per-base supporting saved labels and source/verification status. Explain the fraction
  as target alignment, not a probability that the outfit is appropriate.
- R, C raw state and decision contribution, P raw state/contribution, exact outer
  weights, weighted terms and T. Single-piece C reference and suppressed duplicate
  preference terms must be visible rather than hidden as null-to-zero conversions.
- Why this outfit outranked alternatives: actual relevance/compatibility/preference
  difference or an exact numeric tie settled deterministically, not invented fashion prose.
- For unresolved ranking, distinguish missing objective from missing garment facts,
  mandatory Deny/failure, no structure and technical error. Never ask the user to
  relabel a correct style or review every garment just to obtain a score.

For example: “Recorded casual styles match the authorised casual appearance goal in
both base garments: R=1. Pair compatibility contribution C=1. No independent preferences
were supplied: P contribution=0. Total=4/5. These saved labels are unreviewed; this is
provisional appearance alignment, not comfort or venue-compliance verification.”

Old results retain their old R meaning and stored profile. New display readers must
label those semantics honestly and tolerate unavailable/unknown older formats without
recomputing them. No multi-turn clarification, draft preview or interface redesign is
implicitly added to this scope.

## 12. Acceptance, independent evaluation and performance plan

All 21 AR cases in the external oracle are **proposed, unapproved and not run against
a new implementation**. They cover distinct/same objectives, absent objective, partial
alignment, preference effects, hard constraints/Deny, unknown before/after Allow,
unknown blockers, stale/untrusted sources, equal reviewed/unreviewed arithmetic,
duplicate suppression, explicit-intent precedence, code applicability, all structures,
known zero relevance, ties, specialist isolation, replay and bounded work.

New proposed backend modules are `test_context_relevance_math.py`,
`test_context_relevance_ranking.py`, `test_context_relevance_equivalence.py` and
`test_context_relevance_integration.py`, with `context_relevance_labels.v1.json` and
`context_relevance_sources.v1.json`. Proposed browser files are
`frontend/tests/phase5f/context-relevance.spec.ts` and
`frontend/playwright.context-relevance.config.ts`. The sole proposed existing support
edit is an exact transition in `backend/tests/integration_source_guard.py`.
Default-off isolation should preserve old oracles; any additional existing test edit
must be named and justified before patching, with its original retained.

After approval only:

1. Freeze independent mathematical labels and the separate A1 justification/evaluation
   contract. Do not derive expected rankings from the implementation being evaluated.
2. Compare every candidate decision, R evidence/bounds, duplicate mask, C/P values,
   exact total and tie key across compact, reference and public reconstruction.
   Include mixed unknown candidates that can/cannot outrank the known winner.
3. Disposable APIs must cover strict joins, all four structures, quota, automatic Add,
   forged/malformed proof/bundle/version rejection, rank-to-commit change, rollback,
   keyed replay and history across catalogue/preference/profile changes. Preserve
   W/AP/IP, inactive contexts, old numerical profiles and durable logout.
4. Actual production-browser checks should cover visible success/no-objective/unknown/
   failed/technical outcomes, full R/C/P explanation, old history, keyboard, narrow
   names and native zoom, plus optional failure/Cancel behaviour where touched.
5. Use retained 100-garment populations for preparation/call-count bounds. Keep selected
   objective preparation O(N); one-style goal aggregation is constant work per candidate.
   A streaming best point candidate plus strongest unresolved optimistic blocker needs
   constant additional selection state, not a stored/sorted list of every candidate.
6. Preserve the search bound `(upper × lower + one_piece) × (1 + outerwear)` and existing
   bounded caches. No candidate-loop NLP/config/DB/network/model calls, five-context
   scoring per garment, new capacity population or speculative global cache. A focused
   changed-path timing comparison may be justified by the new per-candidate work;
   it is not a full NFR benchmark or latency acceptance.

Synthetic rule conformance, objective-policy validation, upstream label accuracy and
normal-user understanding are separate evaluation claims. A1's held-out comparison
evidence must justify event utility; 40 correct fractions cannot substitute for it.

## 13. Compatibility risks and decision

The largest risk is not arithmetic: it is assigning an unjustified objective to a
broad context and displaying it as established suitability. Other material risks are
implicit formality from a style goal, correlated/double-paid tests, dropping Unknown
competitors, insufficient provenance/version dispatch, and old history decoded with
a new catalogue. Exact weights alone do not prevent these changes in meaning.

R=0 under a known soft objective is not universal unsuitability. R Unknown is not a
zero-quality observation. R=1 is not perfect fashion. The proposed uncertainty rule
proves only a winner under captured recorded facts and approved numerical conventions;
it does not certify true CV labels or independent real-world appropriateness.

**Decision-ready recommendation:** approve an Option A mechanism only together with
its explicit score/Unknown/dedup/version contract, and require an accepted A1 evidence
pack before automatic mappings are activated. A2 can use an already supported explicit
style without setting up occasion profiles. Do not activate arbitrary five-way mappings
or claim a calibrated contextual model merely to make the FYP demonstration varied.

This approach materially improves the FYP objective **when an authorised contextual
objective actually produces graded, independently justified comparisons**. A formula
change, a new label or an A2-only demonstration does not by itself fulfil the desired
automatic behaviour for the five bare requests. The missing A1 evidence is a real
remaining dependency, stated explicitly instead of fabricated as completed work.

**Disposition: detailed design/acceptance proposal complete; stop before implementation.**
No production/default/service/model/private-data operation occurred. The existing
155-requirement baseline remains 144 Verified / 2 Partial / 9 Unverified / 0 Blocked;
RN-13 remains Partial, NFR-02 OPEN / NOT FORMALLY ACCEPTED and whole-FYP acceptance
NOT READY. No new phase, ranking policy activation or interface change begins here.
