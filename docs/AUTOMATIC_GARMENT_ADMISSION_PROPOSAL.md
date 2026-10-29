# Automatic garment admission: source review and proposed change

2026-10-27, Asia/Kuala_Lumpur. **Design complete; ownership/policy approval pending.**
The owner approves automatic recommendation consideration as the product direction.
This explicitly supersedes the earlier requirement to review each saved style for
ordinary contexts. It does not supply teammate/supervisor approvals. No production
patch, private-record read/write, backfill, model run, migration or manual restart
has been performed for this review.

**Recommendation:** implement A, a read-time provisional saved-style policy for exactly
five ordinary contexts, and B, automatic finalisation of structurally complete new
processing batches. Keep actual owner review as optional, distinguish its provenance,
and preserve strict specialist policies. No category-only inference is included.

The existing eight demo records need no Edit, review event or database update under A.
They will be considered from their current saved values when the owner submits a
normal request, subject to current ownership, completed/confirmed processing,
availability, attributes, restrictions and complete outfit structure. Their private
contents were not inspected; this is not a claim that every one has sufficient facts.

## 1. What currently causes the extra work

| Boundary | Inspected implementation | Consequence |
|---|---|---|
|Processing completion|`garment_processing_orchestrator.run_job` always writes `review_required` plus pending candidates.|Successful processing does not create a wardrobe record.|
|Wardrobe creation|`review_service` and `wardrobe_service.confirm_candidates` require accepted items before Save, enforce quota and atomically write garments/confirmed links/completed job.|There are separate Accept and Save actions, independent of contextual style review.|
|Candidate acquisition|`confirmed_garment_query_adapter` joins the owned available garment to a confirmed item and owner-matching job; retrieval validates category/role/media.|Available display alone is not enough. The current SQL does not additionally require `j.status='completed'`; the normal writer establishes it atomically.|
|Context evidence|`ContextEvidenceResolver.resolve` requires the style review to match current singleton style/category unless an applicable clean declaration supplies that condition.|Saved casual/smart-casual alone cannot establish an ordinary occasion. Those garments may already enter the candidate pool, while their contextual condition remains Unknown.|
|Recent one-time confirmation|`owner_style_confirmation` creates the existing owner-review proof only after explicit style selection in Add/Edit.|It removes a second review click, but still requires per-garment human confirmation. That does not meet this new product decision.|
|Current UI|Add exposes review/Accept/Save; contextual explanations and insufficient-evidence messages describe reviewed style.|Those messages and normal upload completion must change alongside the evidence policy. The already implemented outcome-first layout should remain.|

Twenty pure synthetic member-condition probes confirm the current boundary: the five
requested phrases × casual/smart-casual × absent/current review yield **10 Unknown
without review / 10 Pass with review**. These are not outfit, API, browser, model or
private-wardrobe tests. No garments were acquired and no ranking ran.

There is an additional genuine information gap: the local development detector emits
**Unclassified garment**, confidence 0 and style null. The real CV extractor also
deliberately returns style null; its Fashionpedia heads do not supply a canonical style.
Removing review requirements cannot create those missing values. No model/default or
arbitrary confidence threshold is proposed to hide this limitation.

## 2. A: versioned read-time ordinary appearance policy

Proposed registry **context-registry-1.4.0**; grammar/taxonomy remain 1.3.0 because no
new language or situation is needed. Keep eight bindings. Change only campus,
shopping, casual-outing, date and dinner bindings to **appearance-2.0.0** policies;
use distinct CA2/SH2/CO2/DT2/DN2 rule IDs and `saved_style_in` predicates under
`saved_singleton_style_provisional_v1`. Existing binding identifiers remain stable;
policy versions, hashes and rule IDs disclose the new semantics.

Wedding, university-presentation and interview binding objects retain their existing
meaning and bytes. Legacy and frozen wedding profiles retain their declaration rules.
The general profile remains separately opt-in; global context default stays disabled.
Fresh ordinary requests in that profile intentionally change. Historical keyed replay
continues returning stored old scores/proofs before current interpretation.

| Rule | Proposed exact meaning |
|---|---|
|SA01: Scope|Only ordinary campus attendance, shopping, casual outings, date and dinner, with their already approved role/venue/companion limits. No new occasion, synonym, inherited professional permission or weather/comfort capability.|
|SA02: Unspecified code|A current supported singleton saved **casual OR smart casual** style may infer the occasion condition without owner review. No dress code/formality is invented.|
|SA03: Explicit supported code|Casual requires matching saved casual; smart casual requires matching saved smart casual. The separately requested formality condition must pass independently through its exact declaration or matching admitted style. No hierarchy approximation.|
|SA04: Precedence|Capability gate first; exact applicable Deny wins, including conflicts/malformed companions. Preserve existing malformed declaration/context-root barriers. Clean exact Allow establishes only its own condition. Otherwise use the admitted current attribute. Malformed review/source evidence cannot supply attribute inference.|
|SA05: Missing/uncovered|Missing, empty, multiple, malformed or unrecognised style is Unknown without applicable positive declarations. A valid uncovered style such as classic is also Unknown, not a universal unsuitable judgement. No style fabricated from category, colour, material, saved preference or raw confidence.|
|SA06: Currency|Use the current canonical saved value and current category/media snapshot. A stale/withdrawn owner review is never presented as current. A valid current saved label may still qualify **as unreviewed** when its separate provenance is absent/valid. Present-but-stale or malformed new source metadata blocks inference rather than becoming absent metadata.|
|SA07: Review withdrawal|Removing a style review removes its human-confirmed basis; it no longer prohibits provisional ordinary use of an otherwise valid saved style. An applicable **Deny** is the optional restriction that excludes a garment. Withdrawal still blocks review-dependent inference for wedding/AP/IP.|
|SA08: Source disclosure|Store `saved_attribute_provisional` separately from current owner-reviewed inference and explicit declaration. Mark source unknown when unknown; model-reported/synthetic evidence remains labelled accordingly. Never create a review timestamp, owner audit or human-verification claim at read time.|
|SA09: All members|Every chosen member, including outerwear, must pass. Unreviewed valid outerwear can now qualify and may change the winner through existing arithmetic; genuinely missing/denied outerwear does not prevent a valid base-only structure.|
|SA10: Ranking/output|Keep exact Fraction 60/20/20, the four structures, enumeration and ties. No source/review/confidence bonus. Show cards/images where available and scores, or an actionable outcome before details.|

Declaration targets stay exactly `campus`, `shopping`, `casual_outing`, `date`, `dinner`.
Formal/black tie remain unavailable even with Allow. Unrequested formality is not
added. AP/IP retain their role/code/evidence requirements; interview construction and
dated-condition observations are not inferred from an unreviewed style.

## 3. Provenance without rewriting legacy garments

Add an immutable `SavedAttributeEvidence` projection to the confirmed snapshot.
It describes the canonical saved style, verification state, actual available origin
information, and value/category/media binding. This requires shared/T contract and
adapter approval. It does not alter numerical style mapping or make an absent source
event an error for legacy saved labels.

| Actual evidence | New ordinary explanation |
|---|---|
|Valid current existing owner review|Owner-confirmed style; retain actual review time/basis.|
|Saved label with no verifiable field-level origin|Saved, unreviewed style; origin unknown; provisional assessment.|
|Actual field-level adapter/model report|Saved adapter/model-reported style, unreviewed; retain real available identifiers; no accuracy/certification claim.|
|Explicit synthetic source metadata|Synthetic saved information; unreviewed/provisional. Without such metadata, do not guess an old record's origin.|
|Missing/ambiguous/corrupt value or required evidence|Unknown; explain the actual missing/inconsistent field.|

The current snapshot has no generic style-origin field. A garment-level label such
as `source=YOLO segmentation` does **not** prove that YOLO produced its style. Preserve
that distinction. No probabilities are promoted to calibrated confidence.

For future automatic additions/corrections, server-owned
`saved_attribute_sources_v1` JSON records the actual contributor and saved-value
binding. Use storage/processing timestamps labelled as such, never `reviewed_at`.
Both JSON representations remain consistent. Reserve this namespace against client
injection and strip forged adapter owner/source audits before recording actual source.
Legacy rows receive **no backfill**; A synthesises only a read-time explanation.

Proposed explanation version **general-context-explanation-1.4.0** applies to the five
changed bindings. Preserve rendering of all old versions. Example: “Uses your saved
casual style for a provisional ordinary-shopping appearance suggestion. This style
has not been owner-reviewed; its original source is not recorded.” A correct uncovered
style must not be relabelled merely to obtain a recommendation.

## 4. B: safe automatic finalisation for new uploads

Normal Add explicitly requests **automatic_structural_v1** on the existing authenticated
POST `/processing/jobs` through a typed `admission_mode` query parameter. Requests
omitting it retain the old **manual_review_v1** protocol. This versions the submission
contract without changing global defaults, adding a route or migrating the database.
Server-generated `automatic_garment_admission_v1` item metadata records the requested
mode and finalisation outcome; clients cannot manufacture it.
The upload response must acknowledge its selected version. An older backend that
omits it cannot be presented as supporting automatic saving; show controlled legacy/
unavailable guidance. Automatic mode saves garments, not an implicitly named outfit.

The existing confirmation endpoint receives an optional matching mode for controlled
retry/correction completion. Legacy payloads keep their accepted-item requirement.
No GET performs finalisation or writes data. No background resubmission loop is added.
Automatic retries must identify the same complete batch and return stable saved IDs;
they cannot change the original item selection or silently create a partial save.

| Rule | Proposed finalisation contract |
|---|---|
|AF01: Minimum|Processing returned a nonempty complete batch without failure; every item has a supported canonical category/structural role, valid owned preferred representation and owner/job association. Validate finite/range-correct metadata, not an invented fashion-confidence cutoff.|
|AF02: Optional attributes|Style/colour/material may be genuinely unavailable. This does not prohibit storing a structurally valid garment; requested contextual/hard constraints still need their actual facts before selection.|
|AF03: Atomic batch|In one writer transaction lock/recheck the job and all candidates, recount non-archived quota, create all garments/representations, mark links confirmed and job completed. No partial automatic batch. No intermediate false human `accepted` event.|
|AF04: Incomplete/failed|No automatic save for unclassified/unsupported categories, failed/no detections, invalid/foreign media or malformed required data. Preserve an honest incomplete/error state with correction guidance. If any item is incomplete, retain the batch/drafts; do not silently save only a subset.|
|AF05: Quota/cancel/race|Quota remains 100; uploads reserve no spaces. A full/racing batch is blocked atomically. A committed cancellation wins. Do not archive/delete/replace other garments or mark interrupted processing successful.|
|AF06: Idempotence|A retry/lost response for the same successfully automatic-finalised job returns its same owned saved IDs, with no duplicate or second quota charge. Failed writes roll back. No startup/backfill changes to old jobs.|
|AF07: Correction|If a category is genuinely missing, one explicit **Save corrections** in the incomplete flow can finish the automatic job once valid. This is correction of missing information, not mandatory per-item style attestation. A retry after resolving quota uses the versioned existing POST action.|
|AF08: Truthful state|`confirmed` means successfully finalised storage/processing linkage; it does not mean every attribute was human-reviewed. Preserve adapter review-needed hints as unverified-data information under the new mode. Do not turn them into owner-review proof or block all ordinary use just because the legacy adapter sets that hint.|

The new entry point extends the existing `ConfirmedGarmentWriter` port and central
wardrobe writer. Share its locked validation/materialisation logic; do not add a
second SQL writer or recommendation pipeline. The processing orchestrator calls that
port after publishing its prepared batch. All state is rechecked under the write lock.

Proposed acquisition strengthening: keep the existing owner/available/confirmed joins
and additionally require **processing job status completed**. This excludes a forged
confirmed link attached to a failed/non-completed job, across profiles. It is a named
shared/T query change, not permission to relax the confirmed-item boundary. Normal
old manual saves already commit that completed state atomically.

The current local unclassified fallback cannot take the successful automatic path.
It needs an accurate category correction or a working appropriately scoped processing
source. Neither A nor B supplies a missing style or proves model quality. No model,
CV adapter, confidence threshold or inference-mode change is in this plan.

## 5. Category-only alternative and real product limits

Category proves the represented structural role, not casual style, professional
appearance, climate protection or event compliance. A category-only heuristic would
be a separate new applicability policy, not merely evidence admission. I recommend
**excluding it from A+B**. Missing style stays a distinct genuine-information outcome,
and available exact declarations still apply within their existing scope.

If style-free ordinary recommendations are required, first approve an explicit
category set, unspecified-code-only scope, declaration interaction and wording such
as “basic category combination; style appropriateness not established”, with separate
labels. No category-only rule or style-generating model is approved by this proposal.
Thus A+B removes redundant confirmation; it does not promise every upload can produce
every requested outfit from currently absent attributes.

## 6. Exact proposed production scope and owners

**20 existing production files and two new modules are proposed; none is edited.**
Paths are relative to project root. A and B are one coherent product increment with
separate evidence and processing ownership decisions.

| Owner / part | Existing paths | Exact purpose |
|---|---|---|
|Shared/T contract, A|`backend/app/shared_contracts/confirmed_garment_snapshot.py`; `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`|Immutable source projection, currency/equality, and explicit completed-job predicate. No pending/foreign admission.|
|R policy, A|`backend/app/application/recommendation/config/context_policy_registry.v1.json`; `backend/app/application/recommendation/context_policy_registry.py`|Strict 1.4 envelope; five version-2 bindings; three strict binding subtrees equal.|
|R evidence/explanation, A|`backend/app/application/recommendation/context_evidence_resolver.py`; `backend/app/application/recommendation/general_context_evaluator.py`|Saved-style predicate and truthful 1.4 proof/summary; existing mandatory integration and spec hashes retained.|
|Shared/T processing, B|`backend/app/api/garment_processing_routes.py`; `backend/app/domain/value_objects/requests.py`; `backend/app/application/ports/confirmed_garment_writer.py`|Versioned existing upload/confirm payloads and explicit automatic writer port. Same authoritative auth; no new route.|
|Shared/T workflow, B|`backend/app/application/garment_processing/garment_processing_orchestrator.py`; `backend/app/application/garment_processing/processing_job_service.py`; `backend/app/application/garment_processing/review_service.py`; `backend/app/application/wardrobe/wardrobe_service.py`|Automatic finalisation, optional correction/retry, read-only saved-ID/status projection, reserved source metadata and atomic central writes.|
|Shared frontend/R, A|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`; `frontend/app/wardrobe/page.tsx`|Typed provenance/modes, source-appropriate explanation and optional review/corrections. Preserve outcome-first layout, scores, old history formats, wrapping and keyboard.|
|Shared frontend/T, B|`frontend/app/extract/page.tsx`; `frontend/app/extract/results/page.tsx`|Normal Add explicitly requests automatic mode; successful completion displays saved garments/Wardrobe action without Accept/Confirm. Honest incomplete/capacity states and optional correction.|

New modules:

- `backend/app/domain/value_objects/saved_attribute_evidence.py`: immutable bounded
  source/value binding and conservative projection; no database writer or model trust.
- `backend/app/application/garment_processing/automatic_garment_finalization.py`:
  reusable automatic-readiness/provenance assessment used by the existing central writer;
  no independent transaction owner, event scorer or AI adapter.

Excluded: original NLP/grammar/taxonomy; original declarations/parser; frozen wedding
classes; owner-style confirmation helper; appearance review contract; scoring arithmetic,
compact loops/gates, request/preference/compatibility calculations; recommendation
writer/history; auth/logout; workflow default selection/provider/migrations; Homepage;
CV/VTOFF/VTON code/assets. No private data or manual-service operation is authorised.
Any concrete need for another existing production/test file must be named before editing.

## 7. Versioned acceptance and existing-test transitions

The external `proposed-acceptance-matrix.json` has **59 proposed scenarios and eight
browser groups**, independently authored from SA/AF rules. They are **unapproved and
NOT RUN**, not a promised pytest count or fashion-validation dataset. Twenty current
pure observations are recorded separately.

Historical fixtures remain byte-identical. New current-contract labels explicitly
record these proposed transitions:

| Old fixture IDs | New 1.4 expectation |
|---|---|
|Date/Dinner E16, E17|InsufficientEvidence → Selected for valid current saved casual. E17 uses unreviewed current value; its stale review is not rehabilitated.|
|Everyday CA03, SH03, CO03, N17|Same intentional change for valid current saved style without current owner review.|
|Date/Dinner G07; Everyday N18|Unreviewed valid outerwear can qualify. Candidate decisions, deterministic winner and score can change through the existing algorithm.|

Other labelled outcomes must remain unless a separately named semantic difference is
found and approved. Explicit code mismatch, classic/uncovered style, malformed data,
Deny, unavailable scope, wedding/AP/IP and immutable old replay retain their limits.

Existing backend test/support edits proposed before patching:

- `backend/tests/integration_source_guard.py`: exact new transitions/additions,
  including shared snapshot/query/processing paths; no old manifest repinning.
- `backend/tests/test_general_context.py`: current registry/capability expectations only.
- `backend/tests/test_general_context_equivalence.py`: current ordinary explanation
  version/provenance expectations where needed; keep wedding meaning/oracles.
- `backend/tests/test_date_dinner_context.py`: the named E16/E17/G07 transition overlay,
  `test_independent_social_member_truth_table`, and strict new registry expectations.
- `backend/tests/test_date_dinner_equivalence.py`: its unreviewed-outerwear branch in
  `test_all_structures_independent_expected_arithmetic_and_reference`; separately retain
  a truly missing-style outerwear case and exact score/reference/public assertions.
- `backend/tests/test_everyday_context.py`: named CA03/SH03/CO03/N17/N18 transition overlay.
- `backend/tests/test_everyday_context_equivalence.py`: current member oracle, closed
  1.4 envelope and new source basis; preserve old-profile declaration-only assertions.
- `backend/tests/test_owner_style_confirmation.py`: only `test_existing_source_transition`
  to follow the newly approved transition. All actual owner-action tests stay intact.
- `backend/tests/test_owner_style_recommendation_integration.py`: make the optional
  **unknown** outerwear fixture genuinely missing-style, and separately assert valid
  unreviewed outerwear admission. Preserve explicit owner proof/withdrawal tests.

Existing browser edits proposed: only
`frontend/tests/phase5f/date-dinner-context.spec.ts`, `everyday-context.spec.ts` and
`owner-style-admission.spec.ts`. Replace obsolete “missing review alone prevents an
ordinary result” expectations with versioned saved-style outcomes; retain truly missing
style negatives. Where the old owner-action journey needs legacy Accept/Confirm,
explicitly request the legacy submission protocol in its test helper and label that
compatibility arm. The new normal-path tests must use automatic mode without interception
that fabricates processing success. Preserve originals and all failed attempts.

New files proposed:

- `backend/tests/test_saved_style_admission.py`
- `backend/tests/test_automatic_garment_finalization.py`
- `backend/tests/test_automatic_admission_integration.py`
- `backend/tests/fixtures/automatic_admission_labels.v1.json`
- `backend/tests/fixtures/automatic_admission_sources.v1.json`
- `frontend/tests/phase5f/automatic-admission.spec.ts`
- `frontend/playwright.automatic-admission.config.ts`

Verification after approval must cover:

1. All five ordinary phrases with saved unreviewed casual/smart casual; independent
   Pass/Fail/Unknown tables, exact code gates, Deny/malformed precedence and true source.
2. Newly automatic additions, complete top+bottom and one-piece, all four structures,
   known/unknown outerwear and exact independent Fraction scores/ties/reference/public proof.
3. Eight named synthetic demo replicas on a disposable account, without any Edit or
   review call. Their values are fixture-authored, not claimed copies of private rows.
4. Absent/malformed/multiple styles; stale owner review versus stale new source binding;
   corrections, withdrawal, unchanged clean Allow semantics and no false human audit.
5. Real disposable SQL joins: foreign/archived/unavailable/unconfirmed/non-completed-job
   exclusion; processing failure/incomplete category, media faults and cancellation.
6. Actual quota races, INSERT rollback, completed-job idempotence/lost response, atomic
   recommendation persistence, commit-time snapshot change, old/new keyed replay and logout.
7. Strict W/AP/IP and unchanged old-profile policy output; old labels/results retained.
8. Actual product/version Chrome Add → automatic Wardrobe → Assistant without per-item
   confirmation; optional corrections, visible source/outcome, history/save, keyboard,
   representative narrow widths, long names and native zoom. Synthetic processing
   adapters are isolated test fixtures, never presented as real CV/model verification.
9. Existing 100-snapshot preparation/call bounds, with provenance projected/prepared
   outside enumeration. No full benchmark, lower quota or speculative cache.

## 8. Required decisions, sequence and limits

Before production edits:

1. Owner/supervisor/R and evidence owners approve **SA01–SA10**, five changed policies,
   provisional unreviewed-style admission, explicit-code semantics, stale/withdrawn-review
   treatment, truthful provenance and the exclusion of category-only fallback. Product
   direction is accepted; these exact contracts are proposed for sign-off.
2. Relevant shared/T/R backend/API/storage owners approve **AF01–AF08**, the completed-job
   query check, six A backend files, seven B backend files, two new modules, existing
   namespaces/port/payload semantics and the exact backend test scope above.
3. Shared frontend owners approve the seven named frontend production files, three
   existing browser adaptations and new browser scope. Review/freeze the independent
   proposed labels before patching. No teammate/supervisor consent is inferred.

Then pin approved labels/source originals; implement A/B together; run focused
disposable verification and source integrity; report exact results/limitations. Any
manual restart or actual private-data evaluation is a separate later decision.

Evidence is outside OneDrive:
`C:\Users\chong\AppData\Local\SmartWardrobe\reviews\automatic_admission_review_20261027`.
Source snapshots, proposed labels and current pure observations are retained there.
No current account, garment, chat, DB, secret or photo was opened. The current manual
listeners were only observed, not stopped/restarted. Earlier activation/implementation
reports remain historical evidence, not repinned for this proposed new policy.

RN-13 remains Partial. The original **155 requirements remain 144 Verified / 2 Partial /
9 Unverified / 0 Blocked**; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. This planned
provisional appearance contract does not establish independent fashion quality, real
model accuracy, formal/exercise capability or whole-FYP acceptance.

**Automatically considered** means a current valid wardrobe garment can enter the
candidate pool without a separate human-review action. **Contextually suitable** means
every required condition of the selected, explicitly versioned policy passes for every
chosen member. Only complete passing candidates are scored and persisted.

**Disposition:** source review and concrete plan complete; A+B await the named approvals.
No production implementation or further activation begins from this proposal alone.
