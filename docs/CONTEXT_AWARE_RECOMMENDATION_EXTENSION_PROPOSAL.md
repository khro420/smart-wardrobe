# Context-aware Outfit Assistant: bounded extension proposal

2026-10-24, Asia/Kuala_Lumpur. **PROPOSAL ONLY; awaiting approval.**
This is not a new verification phase, implementation, scope acceptance or
deployment. The J-22 baseline remains 144 Verified / 2 Partial / 9 Unverified
out of 155. RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.
No running service, user data, application source or historical evidence was
changed to prepare this proposal.

## Requested behaviour and inspected limits

The owner chose attribute-based contextual inference, subject to authoritative
explicit declarations, Deny protection, reliable evidence, documented rules,
Unknown for insufficient evidence, mandatory gates before ranking, versioned
policies and independent tests. The owner requested inspection and approval of
a bounded extension before extensive changes.

The current implementation has three separate boundaries:

1. `IntentClassifier` recognises recommendation instructions and "what should
   I wear", but not a standalone situation such as "I'm going to a wedding".
   The extractor rejects unrepresented words/conditions, and vocabulary v1 has
   no wedding occasion. Merely accepting the intent would not supply suitability.
2. `SuitabilityPolicy` supports eight occasions and two formalities using
   owner declarations. Missing/conflicting declarations are Unknown. No
   attribute-to-occasion inference exists. In the existing policy, simultaneous
   Allow and Deny are Unknown, rather than Deny winning; preserve that historical
   behaviour in the existing profile and make the proposed profile's Deny
   precedence explicit.
3. `ConfirmedGarmentSnapshot` carries categories, styles, colour, pattern,
   fit/material and tags, but no field-level review provenance. Confirmation
   proves the owned processing/wardrobe link; it does not prove every automatic
   attribute was inspected. Free-text names, missing model output and development
   fallback values cannot establish contextual suitability.

`CompactExhaustiveScorer`, `CompactMandatoryFacts`, the public evaluator and
`ScoringEligibilityGate` also restrict approved evaluator types. The compact
mandatory facts parse declarations directly. A change only to the high-level
evaluator would be incomplete and could disagree with independent verification.

## Recommended first increment

Add one opt-in **wedding guest suggestion** capability, with natural situation
phrases and conservative attribute rules. Leave other existing occasions on
their current declaration-only behaviour in this increment. This supplies a
working extension boundary that can later support other documented situations;
it does not claim unrestricted natural-language reasoning.

Keep vocabulary v1, declaration policy v1 and their loaders intact. Add a
separate versioned contextual interpreter and policy, selected together through
a new server-only setting, proposed as
`SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE=wedding_guest_v1`.
Its default is `disabled`. Invalid/mismatched configuration fails closed rather
than silently using generic recommendations. A contextual profile additionally
requires the existing Assistant and suitability features to be enabled. The
current running application is not switched to it by this proposal.

Use a versioned immutable contextual request extending the existing request
type, with the actual occasion, explicitly supplied dress code, declared role,
any disclosed role assumption, and interpretation version. Existing requests
retain their original type, fields and serialization. Do not inject inferred
`style=formal` or `formality=formal` into the user's request. Versions and exact
policy hashes must distinguish new behaviour from old bytes.

### Meaning of the wedding example: approval decision

"I'm going to a wedding" alone does not establish the user's role, culture,
venue or dress code. To make this exact input useful, the proposed product
convention is to offer a **provisional guest suggestion**, visibly labelled:

> Wedding guest suggestion; dress code unspecified. Check the invitation.

This convention is an assumption requiring approval, not an extracted fact.
Store `role=unspecified` and `assumed_role=guest` separately. Explicit "as a
guest" needs no role assumption. Explicit bride/groom/bridal-party roles,
uniforms and unsupported dress codes do not use the guest fallback. In the
existing one-request workflow, give a controlled message and invite a new chat
with a supported request; do not add a clarification conversation.

If this convention is rejected, an unspecified-role/dress-code request must
instead produce a specific insufficient-context outcome. It must not silently
receive the provisional guest treatment. Approval of file scope alone does not
approve this convention.

### Proposed interpretation examples

| Input | New-profile interpretation / boundary |
|---|---|
|I'm going to a wedding; Im going to a wedding; I am attending a wedding|Wedding; role/dress code unspecified; disclosed provisional guest convention if approved.|
|Suggest an outfit for a wedding as a guest|Wedding guest; dress code unspecified.|
|I'm attending a wedding as a guest; the dress code is smart casual|Wedding guest; explicit smart_casual dress code.|
|I'm attending a wedding as a guest; the dress code is casual|Wedding guest; explicit casual dress code.|
|I'm going to a formal / black-tie wedding|Context understood, required capability unavailable; no casual fallback.|
|I'm the bride; I'm attending a wedding in a required uniform|Guest policy unavailable; no role/uniform condition discarded.|
|A wedding in hot weather; a traditional ceremony with an unrepresented requirement|Unsupported contextual constraint; no weather/cultural assumption.|
|I'm not going to a wedding; wedding or gym; two separate requests|Unsupported meaning under the bounded grammar; no negation/alternative stripping.|

New patterns must account for every meaningful token, preserve original text
and reject conflicting or unrepresented conditions. Existing explicit colour,
style and category requests remain mandatory. Existing non-wedding inputs
delegate to the original interpreter/evaluator, with their accepted outcomes
unchanged. This increment requires no LLM, cloud wardrobe transfer, image
analysis, model installation or download.

## Evidence and proposed rules

Users should not have to annotate every garment for every occasion. For this
increment, review **style attributes once**, then reuse them in contextual rules.
Automatic style evidence is not admitted until an approved model/provenance
contract independently establishes its reliability; current model handoff gaps
do not meet that condition.

Add a small optional wardrobe control to acknowledge the currently displayed
canonical style values as reviewed. Bind the server-written acknowledgement to
those exact values and the current garment category, with schema version and
review time. An edit of either invalidates the acknowledgement until reviewed
again. Old records are unreviewed, not automatically backfilled. Null, empty,
malformed, conflicting or unrecognised styles cannot be certified as positive
evidence. This records an owner's description, not independent fashion accuracy.

Use a namespaced object in the existing garment attributes JSON, proposed as
`contextual_suitability_v1`, and an additive immutable snapshot evidence field.
No new SQL table/provider or database schema migration is proposed. Shared
storage/contract approval is still required for the new stored representation.
Only the dedicated authenticated owner action writes the acknowledgement;
automatic processing output and generic attribute updates cannot manufacture it.
Do not alter CV extraction, review raw results or existing custom tags.

Optional wedding Allow/Deny controls use this new versioned representation,
not a new reserved tag inserted into v1 custom tags (which the old parser would
correctly consider malformed). They are overrides, not prerequisites. Existing
supported occasion/formality declarations remain intact and authoritative for
their exact field/value; no inheritance from work/dinner/party to wedding.

The following are **proposed heuristics for approval**, not measured fashion
rules or universal wedding requirements. They intentionally cover a narrow
part of the available wardrobe evidence:

| Rule | Required evidence when no applicable declaration exists | Result |
|---|---|---|
|W01: wedding guest, dress code unspecified|Each member has current reviewed style evidence exactly identifying smart casual, and belongs to a valid existing structural composition.|Provisional Pass, with the unspecified-code warning.|
|W02: wedding guest, explicit smart casual|Each member has current reviewed style evidence exactly identifying smart casual, and valid structure.|Pass for this proposed dress-code rule.|
|W03: wedding guest, explicit casual|Each member has current reviewed style evidence exactly identifying casual, and valid structure.|Pass for this proposed dress-code rule.|
|W04: evidence outside these positive rules|Missing/stale/empty/malformed/ambiguous evidence, multiple potentially conflicting styles, or another style without an approved rule.|Unknown; no invented negative fashion judgement.|
|W05: required formal/black-tie/other unsupported code|No implemented policy for the actual requirement.|PolicyUnavailable; no generic/casual substitution.|

"Exactly identifying" means the reviewed canonical style set is the singleton
specified by the rule. Category supplies structure only: a dress or long sleeve
alone does not prove suitability. Classic is not automatically smart casual;
colour, fit/material prose, names and unverified confidence do not prove it.
Do not add white/black colour bans, gender/body assumptions, a formality hierarchy,
or climate/cultural rules. Shoes, accessories, garment condition and invitation
details are outside the current garment contract, so these suggestions cannot
certify a complete dress code or guarantee suitability for every wedding.

### Declaration precedence and candidate safety

For each relevant occasion/dress-code condition in the new profile:

1. An identifiable, valid explicit Deny is Fail, including alongside an Allow.
   Attribute inference cannot rescue it.
2. Otherwise malformed/conflicting authoritative evidence is Unknown and blocks
   inference. A corrupt collection cannot be treated as absence.
3. A clean explicit Allow is authoritative for that exact condition. It does
   not waive a different condition or unsupported request capability.
4. Only genuinely absent declarations may use the admitted attribute rules.
   Unknown for lack of a declaration is distinguishable from Unknown caused by
   malformed evidence. Do not collapse those cases before deciding fallback.

Apply this to every member, including outerwear. Aggregate Fail before Unknown;
only all-Pass candidates enter the existing scoring/ranking pipeline. Explicit
requested colours/styles/categories, ownership/current availability, confirmation,
structure, existing compatibility handling and exact candidate enumeration remain.
Do not convert currently scored compatibility atoms into new hard constraints.
Keep the exact 60/20/20 weights and tie order; no suitability confidence bonus or
extra scoring component. The proposed occasion is a mandatory condition, not
permission to increase scores for missing evidence.

## Integration and review scope

Proposed existing-file scope, subject to shared approval:

| Owner | Existing paths / purpose |
|---|---|
|R NLP/domain|`backend/app/domain/value_objects/structured_outfit_request.py` only if needed for a compatible extension point; prefer a new subclass module and unchanged base serialization. Existing v1 classifier/extractor/vocabulary files remain intact.|
|R startup/integration|`backend/app/infrastructure/workflow_runtime.py`: select the paired opt-in interpreter/evaluator; keep Homepage wiring unchanged.|
|R mandatory validation|`backend/app/application/recommendation/compact_mandatory_verifier.py`, `compact_exhaustive_scorer.py`, `scoring_eligibility_gate.py`: explicitly admit and independently verify the new evaluator, not arbitrary injected evaluators.|
|R Assistant explanation|`backend/app/application/recommendation/outfit_assistant_service.py`: store new interpretation/rule versions, hashes, assumptions and winning-member evidence in existing provenance JSON. Preserve atomic writes/keyed replay.|
|T/shared snapshot|`backend/app/shared_contracts/confirmed_garment_snapshot.py`, `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`: additive immutable reviewed-evidence projection; retain all query eligibility predicates.|
|T/shared wardrobe/API|`backend/app/domain/value_objects/requests.py`, `backend/app/api/wardrobe_routes.py`, `backend/app/application/wardrobe/wardrobe_service.py`: authenticated, concurrency-protected review/override writes, stale-evidence invalidation and reserved-metadata protection. No quota/archive/confirmation-eligibility change.|
|Shared frontend|`frontend/app/wardrobe/page.tsx`, `frontend/lib/api.ts`: style-review/optional wedding override controls and typed payloads. `frontend/components/RecommendationResult.tsx`, `frontend/components/OutfitAssistant.tsx`, `frontend/lib/recommendation-messages.ts`: contextual explanation and specific controlled outcomes. Retain J-20 wrapping and actions.|
|R test support|`backend/tests/integration_source_guard.py`: exact approved transitions where required; no old manifest/hash repinning.|

New modules would hold the contextual interpreter/grammar, request context,
policy/configuration, declaration/evidence resolver, evaluator, immutable snapshot
evidence type and independent test oracle. Proposed versions are
`contextual-nlp-1.0.0` and `wedding-guest-suitability-1.0.0`; freeze the actual
grammar, rule IDs, schemas and hashes before verification. New configuration
must not expand v1's supported sets through an indirect default loader change.
No existing scoring arithmetic, preference scorer, enumeration algorithm,
Homepage selector, auth/logout, database provider or CV/VTON file is in scope.

Independent validation means a separately implemented test oracle with manually
labelled garment/request fixtures, not just calling the production resolver
twice. Runtime primary compact facts, separately constructed verification facts,
public reconstruction and scoring gate must agree on all mandatory conditions.
Keep unsupported evaluator injection fail-closed. The new resolver must be
request-local; no global mutable inference cache or cross-account evidence.

Add immutable inference provenance to new successful results: actual/assumed
context, rule version/hash, declaration versus inference per member/condition,
reviewed values and evidence version. Display the basis and limitations on the
result/history card. Existing stored chats and keyed results replay their stored
payloads without reinterpretation, rescoring or retrospective certification.
Inspect the existing repository's snapshot/revalidation contract before coding;
if it cannot preserve the additional evidence atomically through its current
generic JSON fields, return with the exact additional persistence-file scope
for approval. Do not bypass revalidation or silently add a migration.

## Required verification after approval

- Freeze new labels separately: the wedding examples above, paraphrases,
  apostrophe variants, unsupported roles/codes, conflicting constraints and
  unknown meaningful words. Existing J-15 labels/failures remain unchanged.
- Independently label declarations versus attributes: Deny over inferred Pass,
  Deny plus Allow, malformed collections, absent declarations, conflicting/stale
  review, unsupported values, owner isolation, invalidation races and all-member
  outerwear coverage. Explicit Allow cannot bypass another failed condition.
- Verify primary/independent/public/reference mandatory agreement and exact
  existing score arithmetic/tie order for accepted candidates. Old profile and
  delegated non-wedding requests retain accepted behaviour and serialization.
- Verify actual API/UI examples with disposable data: a successful contextual
  result, specific Unknown/no-result, unsupported dress code, optional override,
  one request/one result, save eligibility, immutable history and keyed replay.
  No real-account writes, model inference or service-mode switch without authority.
- Record the exact source transition and focused regressions. Do not rerun a
  capacity study or full performance matrix. Review any necessary changed-path
  performance delta separately; unchanged J-16 figures are not new measurements.

## Approval requested before implementation

Approve or amend these three concrete decisions together:

1. The opt-in wedding-only first increment, including the disclosed provisional
   guest convention for an unspecified role/dress code and rules W01-W05.
2. Shared/T permission for the named snapshot, wardrobe/API, stored JSON evidence
   and frontend scope: reusable attribute review plus optional occasion overrides,
   with no schema migration, inferred backfill or real-account edits.
3. R permission for new versioned NLP/suitability modules, the named mandatory
   integration and provenance/UI paths, new independent tests and exact source
   transitions. Existing defaults/profiles/evidence remain intact.

If a rule or assumption is not accepted, revise this proposal before writing
application code. This proposal makes no claim that the extension is implemented
or that RN-13, model evidence, final architecture or formal acceptance is closed.
