# Owner-confirmed style admission and visible recommendation outcomes

2026-10-27, Asia/Kuala_Lumpur. **Investigation complete; design proposed for approval.**
No production change, private garment transition or manual-service restart was made.

**Recommendation:** treat an explicit style selection in the ordinary Add/Edit
workflow as the single owner-confirmation action. Record that action server-side and
reuse the existing admitted style-review evidence. Do not make every saved style
trusted, introduce a category-only suitability shortcut, or change the scorer.
Separately, make the outcome visible before the contextual explanation.

## 1. Root cause

Two independent problems explain the reported experience.

**The evidence contract loses an important distinction during normal addition.**
`frontend/app/extract/results/page.tsx` distinguishes preserving an existing suggestion
from explicitly choosing a style: `styleChoice="__keep"` omits `attributes.style`,
whereas choosing casual sends it. However, the API/service stores the resulting value
without retaining a field-specific owner-confirmation event. `review_status=accepted`
means the candidate was accepted; it does not identify which fields were checked.

`backend/app/application/garment_processing/review_service.py:15` merges attributes
and saves the decision. `wardrobe_service.py:171` confirms accepted candidates under
the quota/ownership checks, but line 208 explicitly removes the contextual namespace.
That is an intentional defence against automatic processing fabricating owner review.
It also means an explicitly chosen style has no admitted confirmation after saving.

The wardrobe editor has the same gap. It distinguishes preserving a style from
assigning values, but `wardrobe_service.py:259` invalidates the existing style review
whenever category or style is supplied. It does not replace that review with an
attestation to the newly selected value. Even an explicit same-value style PATCH
does not establish review.

`context_evidence_resolver.py:28` correctly requires a Known review, a Known singleton
canonical style, matching category and matching values. Without these, it returns
Unknown / `insufficient_reviewed_attributes`. All selected members must pass; colour,
category, saved preferences and compatibility scores do not supply that evidence.
The missing step is trustworthy write-time provenance, not another ranking algorithm.

**The outcome is visually subordinate to the explanation.**
`OutfitAssistant.tsx:32` sets the no-result message. Lines 72–83 render the full context
summary before the alert at line 84. Long capability guidance also precedes the
request. There is no initial-outcome focus/scroll treatment. At narrow widths this
puts the actionable message below the viewport, leaving explanation text that can
look like a completed recommendation.

## 2. Independent disposable reproduction

Evidence is retained outside OneDrive at:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\style_admission_20261027
```

The probe ran ordinary `app.main` on an owned temporary backend at port 3181, using
a new database, generated secret, development processing and VTOFF/VTON off. It used
real registration/login and processing-review-confirmation APIs for eight synthetic
garments corresponding to the stated categories/styles. It performed no model inference.
Styles were explicitly supplied through the ordinary review API, with no contextual
review or occasion declarations. This exercises a stronger case than merely storing
unreviewed demo metadata: an explicit normal-workflow style selection is still lost
as evidence.

| Observation | Actual result |
|---|---|
|Shopping after normal addition with explicit styles|HTTP 200, `InsufficientEvidence`, `context_reason=required_attribute_unknown`, no recommendation; completed history total 0|
|Class after the same addition|Same controlled result and history total 0|
|Shopping after an explicit casual style correction|Still `InsufficientEvidence`; history total 0|
|Candidate diagnostics in those three cases|20 complete candidates examined, 20 Unknown, 0 passing, 0 numerically scored|
|Positive control: separate style review on casual top and jeans|Shopping returns HTTP 201 / Selected with two members; history total 1|
|Same successful key replay|HTTP 200 / Selected, same stored recommendation, history total remains 1|

Final disposable counts are one chat, one recommendation and one submission: only
the positive control persisted. A controlled HTTP 200 is transport success, not
proof that an outfit was selected. The service returns before `persist_assistant`
when ranking is not Selected. No cards or numeric score are appropriate when no
candidate passes the mandatory evidence gate; displaying zero would be misleading.

Four fresh browser observations used installed Chrome 156.0.8078.48: shopping and
class at 1280×720 and 390×844. The current running frontend served its unchanged
page/assets; an isolated browser redirected **all API traffic** to the disposable
backend. No real account token/profile or private API request was used. This is a
targeted rendering reproduction, not another production-proxy or comprehensive
browser certification.

| Browser geometry immediately after completion | Shopping alert | Class alert |
|---|---:|---:|
|1280×720|top 634, bottom 708: in viewport|top 634, bottom 708: in viewport|
|390×844|top 898, bottom 1052: below viewport|top 918, bottom 1072: below viewport|

All four contained the expected insufficient-evidence alert, became visibly readable
after scrolling and captured no page errors. Visual inspection of the narrow shopping
screenshot confirms the reported impression: the initial view shows interpretation
and guideline text while the outcome lies below it. **No missing-response-field or
omitted-alert defect was reproduced. A result-discoverability defect was reproduced.**
The user's exact viewport, browser state and historical response were not inspected.

This does **not** certify what every earlier request in the private account persisted.
Its database, logs containing private activity, session storage and responses were
not accessed for this investigation. The current source and disposable results
establish the failure mechanism and persistence behaviour for the reproduced inputs.
The private historical result remains unverified; a context summary alone is not
evidence of a persisted recommendation. Failed requests are not completed-history rows.

Probe and owned backend both exited 0; the temporary worker stopped normally.
Application-source hashes before/after match. The manual services were not stopped
or reconfigured. Files `observations.json`, `run-result.json`, source hashes, four
viewport screenshots and the small probe scripts/logs retain the observations.
These are diagnostic observations, not a new regression-test total or fashion study.

## 3. Evidence classification

| Source | Current distinguishability | Proposed treatment |
|---|---|---|
|Existing explicit contextual style review|Dedicated v1 review, exact values/category/time, currency checks|Keep admitted and reusable; no repeat action needed|
|Style explicitly chosen during Add/Edit|The new request reveals an explicit value; historical stored value alone does not reliably prove the event|New versioned owner-confirmation contract records the action at write time; admit only that current field value|
|Reviewed/verified extraction|Extraction can retain model identity and raw head confidence, but no accepted style-specific calibrated admission channel is present|If the owner confirms the suggestion, use owner confirmation. Automatic model admission needs its own evidence contract and approval|
|Unverified model suggestion|Saved value and some model metadata; acceptance alone does not certify this field|Remain untrusted for required contextual inference until explicitly confirmed|
|Synthetic demo metadata|The importer labelled synthetic origin and deliberately did not create owner-review attestations|Remain synthetic/unreviewed; no automatic transition based on the email, garment name, sample style or successful insertion|
|Missing, empty, multiple, malformed or unmapped style|Existing mapper states and singleton requirement|Remain Unknown for these appearance predicates; do not invent casual or select one of several styles|

The attribute adapter's embedding/model metadata and Fashionpedia head probabilities
are not calibrated contextual-style evidence. Current output includes suggestions
for other visual fields; neither detector confidence nor a saved style label proves
style accuracy. No threshold or new model trust channel is proposed.

The historical normal-confirmation event is insufficient for safe bulk inference:
clients can preserve suggestions, omit style, round-trip values or import synthetic
data. The current storage does not preserve the distinction needed for retroactive
admission. A small forward-write contract is necessary.

## 4. Options and recommended minimum

| Option | Benefit | Cost/limitation | Decision proposed |
|---|---|---|---|
|A. Reuse explicit owner-confirmed style at normal Add/Edit|One ordinary attribute confirmation, immediately reusable across applicable rules; no per-event review grid|Needs a typed intent, server-owned provenance, revisions and transactional transfer|**Recommend**|
|B. Everyday category/colour-only fallback|Could select more combinations without a style confirmation|Category establishes composition and colour supports existing constraints; neither proves the approved occasion appearance predicate. Calling such a combination shopping/class-suitable would introduce a new policy|Do not include in this correction|
|C. Keep separate contextual review for every new garment|Preserves today's distinction without write-contract work|Duplicates an explicit normal-workflow selection and reproduces the UAT friction|Keep only as an optional legacy review/withdrawal path, not a required second step|

A category-based alternative could only be separately approved as an ordinary
**basic wardrobe combination** with explicitly weaker claims, constraints and labels.
It must not silently satisfy an occasion requirement or bypass an applicable Deny.
No concrete evidence here justifies changing EC/DT/DN style rules into universal
category/colour permission. The recommended correction needs no fallback policy.

### A1. Confirm once in the ordinary workflow

- Add/Edit presents the image, final category and style. Selecting one supported
  style and pressing the ordinary Accept/Save action confirms that value. Selecting
  the same value as an untrusted suggestion also counts when deliberately chosen.
- A short field-level notice explains that the saved selection is used as the
  user's style confirmation for recommendations. No additional contextual page,
  checkbox per occasion or second save is required.
- Preserve-current, omitted, Unknown, empty and multiple-style states retain their
  meanings. Merely accepting the candidate or clicking Save without confirming the
  style must not promote a suggestion. An unknown style need not prevent storing
  a legitimate garment; it can still prevent a context that requires it.
- Existing optional contextual review remains available to review old data or
  withdraw review. Do not remove the only way to withdraw admitted evidence.

### A2. Versioned request and server-owned proof

Propose an optional top-level `style_confirmation` object on `ReviewItem` and
`GarmentUpdate`, with contract `owner-style-confirmation-1.0.0`, the explicitly
confirmed canonical style and an expected content revision. Reject unknown keys
and a value that does not match the final saved singleton style. Old payloads
without this object retain their current behaviour; **payload presence of
`attributes.style` alone is not enough to retrospectively change old clients.**

The client supplies intent and its last-seen revision, never authoritative reviewer,
time, provenance or admission state. The server derives those from the authenticated
owner, current candidate/garment and validated final values. The revision covers
identity, owner/job, category, style representations and selected media/dependencies;
it must not be replaced by the tag-only If-Match revision. Existing tag revision
checks still run when reserved declarations change.

Create one small shared writer helper, `owner_style_confirmation.py`, used by
candidate review and wardrobe editing. Store a versioned, **server-reserved** pending
event in the candidate's existing JSON (`owner_style_confirmation_v1`). Strip that
namespace from automatic processing outputs; forbid it in general client attribute
dictionaries. An authenticated confirmation action alone can create it.

The pending event binds owner, job/item, canonical value, category, selected media,
source event and server timestamp. Review/confirmation remain separate state
transitions. An accepted candidate with this event is **not** a garment until the
existing confirmed writer passes quota, ownership, representation and job-state
checks. Rejection/cancellation cannot produce an eligible garment.

### A3. Reuse the existing canonical admitted evidence

At final candidate confirmation, validate the pending event against the locked
current item and create the existing `contextual_suitability_v1.style_review`:
`source=owner_review`, singleton styles, category and server review time. Keep the
current unconditional removal of arbitrary incoming contextual/appearance evidence;
reconstruct only the authorised style proof after validation. Do not copy an
arbitrary incoming namespace into the garment. Update both existing JSON mirrors
in the same garment transaction.

For ordinary garment correction, update the style and its new proof in the same
transaction. Preserve applicable Deny/Allow overrides and malformed-evidence
barriers. A malformed authoritative container needs explicit repair, not silent
replacement by a convenient clean review object.

The new event namespace records how the confirmation happened (candidate acceptance
or garment edit), its contract version and reference/digest of the resulting review.
It is an audit record, **not a second style source or alternative eligibility gate**.
Existing v1 style review remains the sole canonical positive field proof consumed
by the resolver. Never restore a withdrawn/stale review from the audit event.
Current wardrobe presentation may report the event only when it matches the live
review. An optional old-style separate review can supersede it without ambiguity.

This deliberately avoids changes to the general evidence resolver, immutable
snapshot contract, rule registry, mandatory engine or scorer. The existing resolver
already admits a current owner review. Persisted recommendation explanations already
capture that immutable review, its category/style/time and inference basis. The new
entry-action audit need not become an additional scoring or snapshot dimension.

### A4. Currency, corrections and withdrawal

- An actual category/style/source-media dependency change invalidates the pending
  or admitted proof. A newly explicit confirmation of the final values can replace
  it atomically in that same Save; there is no second contextual review afterward.
- Omitted/unrelated edits preserve a current proof. Unknown, empty, multiple or
  unsupported style cannot produce a singleton positive proof.
- Stale revisions return a controlled conflict without saving half an edit. Failed
  writes preserve the prior style, proof, declarations and draft.
- Explicit withdrawal removes the canonical style proof and prevents automatic
  re-admission by an unrelated save. A later deliberate style confirmation can
  create fresh evidence.
- Save/review never overrides an applicable Deny, enables an unsupported code,
  certifies an interview's construction/condition observations or invents formality.

### A5. Context/profile compatibility

This changes how a truthful owner-style proof is obtained, not W/DT/DN/AP/IP/EC
predicates or declaration scopes. Shopping, class, outings and Date/Dinner become
usable immediately when normal Add/Edit has supplied the required proof. Wedding
and presentation can reuse the same proof under their existing style/role/code
limits. Interview still requires all its additional appearance evidence.

New records with the proof will naturally behave like records manually reviewed
through the existing button, including in the frozen wedding profile. That is the
intentional input-contract expansion requiring approval; it is not a claim that
unreviewed new/old records are identical. Old records, old payloads, frozen policy
files and historical results remain unchanged. No new global feature flag/default,
context profile or policy bundle is needed for this explicitly versioned write action.

## 5. Independent UI correction

Propose a compact outcome region immediately after the original request and before
assumptions/limitations. Collapse the long capabilities/examples after submission,
and place extended explanation in a labelled disclosure. On explicit submission
completion, announce/focus the outcome heading or scroll it into view without
discarding the request or moving focus during history loading.

For the reproduced result, use a clear heading **“No outfit generated”** and explain
that the current records lack the confirmed style evidence needed to establish a
complete outfit. Link to ordinary Wardrobe Edit and explain that selecting and saving
a supported style confirms it once. Do not imply that every garment is unsuitable or
that changing a correct uncovered style to casual is the solution.

Render technical failures, missing context, inactive policy, insufficient structure,
Unknown evidence and explicit requirement failure distinctly. Keep safe mappings
and retry behaviour. Every terminal non-success must show a visible message even
without a recognised explanation version. A success shows the complete existing
result cards and exact scores; no fake zero or placeholder outfit is added.

The minimum patch does not invent per-garment missing-field diagnosis: the current
no-result response supplies an aggregate outcome, not a reviewed per-member repair
plan. Specific member diagnostics would be separately scoped API work. The current
outcome placement can be fixed independently of evidence admission.

## 6. Exact proposed files, ownership and migration

All paths are relative to `smart-wardrobe`. **Proposed scope only; not edited here.**

| Owner | Existing production path | Intended change |
|---|---|---|
|Shared/T API contracts|`backend/app/domain/value_objects/requests.py`|Optional strict versioned style-confirmation payload on review/edit; protect reserved metadata|
|Shared/T processing|`backend/app/application/garment_processing/review_service.py`|Validate explicit intent/revision; write/invalidate server-owned pending event under existing transaction|
|Shared/T processing projection|`backend/app/application/garment_processing/processing_job_service.py`|Expose additive candidate confirmation revision/state; no changed queue or recovery semantics|
|Shared/T processing boundary|`backend/app/application/garment_processing/garment_processing_orchestrator.py`|Strip only the new server-reserved event from automatic attribute output; no detector, extraction, standardisation or model change|
|Shared/T wardrobe persistence|`backend/app/application/wardrobe/wardrobe_service.py`|Validated confirmation transfer, same-transaction edit/admission, mirror protection, audit presentation and withdrawal handling; preserve quota and existing declarations|
|Shared frontend/API|`frontend/lib/api.ts`|Additive request/projection types and transport for normal review/edit|
|Shared/T upload UI|`frontend/app/extract/results/page.tsx`|Explicit normal style selection emits confirmation intent and revision; clear suggestion/confirmation wording|
|Shared/T wardrobe UI|`frontend/app/wardrobe/page.tsx`|Ordinary style correction confirms once, current-evidence status and optional legacy review/withdrawal|
|R/shared frontend|`frontend/components/OutfitAssistant.tsx`|Outcome-first presentation, concise submitted state and completion announcement/focus|
|R/shared frontend|`frontend/lib/recommendation-messages.ts`|Actionable safe no-result wording aligned with the approved new workflow|

One proposed new production module:
`backend/app/application/wardrobe/owner_style_confirmation.py` (Shared/T, reviewed
with R for the existing evidence contract).

No new endpoint is necessary: existing authenticated route handlers already forward
validated request dictionaries to these services. No API route, security, CV adapter,
query SQL, shared snapshot, context/evidence evaluator, numerical scorer, Homepage,
history writer or provider change is proposed. `contextual_review.py` and the frozen
v1 evidence parser can remain unchanged. If a concrete patch needs another file,
name and justify it before widening this scope.

Existing verification/support edit: only `backend/tests/integration_source_guard.py`
for the exact new transition. Proposed new files:

- `backend/tests/test_owner_style_confirmation.py`
- `backend/tests/test_owner_style_recommendation_integration.py`
- `backend/tests/fixtures/owner_style_admission_labels.v1.json`
- `backend/tests/fixtures/owner_style_admission_sources.v1.json`
- `frontend/tests/phase5f/owner-style-admission.spec.ts`
- `frontend/playwright.owner-style-admission.config.ts`

Retain old payload behaviour so existing unreviewed fixtures/negative oracles need
not be rewritten to pass. Freeze new expectations before implementation. Any necessary
existing-test adaptation must be explicitly named rather than changing old labels.
Record only scoped source originals/transitions, concise results and relevant failures;
keep disposable DBs/media/browser evidence outside OneDrive.

**No SQL schema migration or private-data backfill is required:** candidate and
garment JSON already exist. That does not authorise private JSON writes. Old data
has no trustworthy event and remains as-is. Old binaries ignore the optional audit;
the canonical review is already understood, but an old editor may invalidate it under
its prior semantics. Historical recommendations retain stored proof/score/replay.

Shared/T approval is needed for normal garment confirmation/storage/provenance;
shared frontend approval for Add/Edit and outcome presentation; R approval for the
equivalence and no-result contract. These decisions are required by the user's
explicit request to present a design before modifying production, not a newly inferred
permission gate. Prior Phase 5 approvals do not cover these new write semantics.

## 7. Private demo garments

No transition is performed by this review. The eight actual demo garments remain
synthetic with their saved styles and no fabricated user-review event. The earlier
import was data setup; it was not eight human observations or verified model outputs.

After approval and implementation, the owner can select a truthful style in ordinary
Edit and save once, including the same displayed value, to create fresh confirmation.
That confirms the illustrated sample's descriptive label; it does not turn it into a
real garment or model result. Withdrawal remains available. Existing names, synthetic
origin, category, declarations and historical records are not silently rewritten.

If an assisted transition is desired later, propose a separate opt-in action showing
each sample/image/value, exact selected IDs and revisions. Record new confirmation
times and synthetic origin, preserve previous namespace values and support withdrawal
only if revisions still match. Never restore an old snapshot over subsequent user
edits. A batch-review UI/script is outside this minimum scope and needs separate
permission; no automatic bulk-review, backfill or occasion Allow tags are proposed.

## 8. Focused acceptance plan after approval

| Case group | Required acceptance |
|---|---|
|Normal Add, explicit casual/smart-casual selection|Accept then confirm creates current owner-style evidence exactly once; no contextual-review endpoint call|
|Normal Edit, new or same explicit value|One Save atomically updates/attests the final value; stale revision rejects without partial edit|
|Preserve/omit old suggestion|No admission solely from candidate acceptance, generic confirmation or old payloads|
|Synthetic/model/forged metadata|Old unreviewed samples remain Unknown; automatic pipeline/client metadata cannot manufacture the reserved event or reviewer|
|Missing/empty/multiple/unknown style|No guessed singleton or arbitrary confidence threshold; storing a valid garment remains distinct from satisfying context|
|Currency and withdrawal|Style/category/media changes invalidate dependent proof; unrelated edits preserve it; withdrawal cannot be undone by unrelated saving|
|Deny and malformed source|Identifiable Deny still vetoes, malformed authoritative containers do not gain inference; existing overrides preserved|
|Ordinary contexts|Shopping/campus/outings and approved Date/Dinner use immediate proof; each requested formality remains independently mandatory|
|Structures/strict eligibility|Trustworthy top+bottom and one-piece cases; optional unknown outerwear doesn't poison base-only result; unconfirmed/archived/unavailable/foreign members excluded|
|Existing contexts|Fresh proof gives the same W/DT/DN/AP/IP/EC decisions as equivalent existing manual-review proof; no extra interview permission or role/code assumption|
|Score equivalence|Same members, structured request, compatibility and preferences produce identical exact R/C/P/total/ties across both confirmation paths|
|Persistence/history|Failed correction/confirmation rolls back; rank-to-commit change rejects; old stored records replay without reinterpretation; same-key response remains exact|
|Browser: normal workflow|Disposable account uploads a synthetic image, selects category/style in normal review, accepts/confirms, submits shopping/class, sees complete cards and score without visiting Contextual recommendations|
|Browser: controlled outcomes|Unreviewed samples, missing context, Deny, unsupported code, technical error and unknown explanation version show an obvious outcome before details at desktop/narrow widths and native zoom; keyboard/focus/retry remain usable|
|Bounded work|No provenance lookup or model/config/DB work in candidate enumeration; reuse 100-snapshot preparation assertions; no speculative cache, full NFR matrix or new capacity claim|

Use independent labels for supported and rejected entry actions, negative provenance
cases, equivalent old/new evidence and UI outcomes. Test actual authenticated APIs
and disposable normal browser upload/review/confirm flows; a direct SQL proof insert
is not acceptance of the new user workflow. The diagnostic positive control above
used today's separate review and does **not** count as this future acceptance test.

**Decisions requested:** approve Option A's versioned one-action confirmation and
existing-proof reuse (including stated profile effects), and approve the exact shared/T/R
files plus the independent outcome-first UI correction and tests. Exclude category-only
fallback, automatic model admission, private demo transition and service restart.

The original 155-requirement baseline remains 144 Verified / 2 Partial / 9 Unverified.
RN-13 and formal NFR acceptance do not advance. No production patch starts from this
proposal alone.
