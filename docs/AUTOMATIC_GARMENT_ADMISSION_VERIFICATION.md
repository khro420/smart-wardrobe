# Automatic garment admission: implementation and verification

2026-10-27, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; implementation complete.**
Normal Add now requests automatic saving of a complete, valid processing batch.
Ordinary campus, shopping, casual-outing, date and dinner requests can use supported
saved styles without a separate owner review. Actual evidence and provisional limits
are retained. Automatically considered does not mean suitable for every context.

The manual backend was **not restarted**. The owner's account, eight demo garments,
database, photos and secret were not inspected or modified. Activation and actual
private-wardrobe results remain separate from this source/disposable-data verification.

The original **155 requirements remain 144 Verified / 2 Partial / 9 Unverified /
0 Blocked**. RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.
Whole-FYP acceptance remains NOT READY. These are approved prototype appearance
heuristics, not independent fashion, model, safety or professional validation.

## 1. Authority and exact scope

After reviewing [the proposal](AUTOMATIC_GARMENT_ADMISSION_PROPOSAL.md), the owner
answered all three required questions:

- **Approve SA01–SA10 and the proposed acceptance contract.** This includes the
  supervisor/R/evidence decision, five ordinary contexts, saved singleton styles,
  truthful provisional evidence, stale/withdrawn-review semantics and exclusions.
- **Confirm the named backend/shared/T approvals.** This includes AF01–AF08,
  processing, central writer, acquisition, storage/contract and named test changes.
- **Confirm the named frontend approvals.** This includes normal automatic Add,
  optional correction/review/restrictions, visible outcomes and the named browser scope.

Approval answers, exact starting copies and the unchanged 59-scenario/eight-browser-group
contract were retained before production editing. The original proposed labels keep
their original NOT RUN authoring metadata; the approved wrapper and actual results
are separate. No historical failure or label was rewritten as a pass.

Exactly **20 existing production files change and two production modules are added**:

| Approved area | Existing paths relative to project root |
|---|---|
|Snapshot/acquisition|`backend/app/shared_contracts/confirmed_garment_snapshot.py`; `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`|
|Context policy/evidence|`backend/app/application/recommendation/config/context_policy_registry.v1.json`; `context_policy_registry.py`, `context_evidence_resolver.py`, `general_context_evaluator.py` in the same recommendation directory|
|Processing/API/contracts|`backend/app/api/garment_processing_routes.py`; `backend/app/domain/value_objects/requests.py`; `backend/app/application/ports/confirmed_garment_writer.py`; `garment_processing_orchestrator.py`, `processing_job_service.py`, `review_service.py` under `backend/app/application/garment_processing/`|
|Central wardrobe writer|`backend/app/application/wardrobe/wardrobe_service.py`|
|Frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`; `frontend/app/wardrobe/page.tsx`; `frontend/app/extract/page.tsx`; `frontend/app/extract/results/page.tsx`|

New modules are `backend/app/domain/value_objects/saved_attribute_evidence.py` and
`backend/app/application/garment_processing/automatic_garment_finalization.py`.
The first provides immutable source projection; the second provides pure readiness
checks. Neither is another scorer, transaction owner or model adapter.

Eight existing backend test/support files and the three expressly named browser
files advance. The approved `test_general_context_equivalence.py` needs no edit.
New coverage uses the three named backend modules, two fixtures and new browser
test/configuration. All original copies remain outside OneDrive.

`automatic_admission_sources.v1.json` pins all 20 exact before/after hashes and both
new-module hashes. The guard follows this transition without repinning old manifests.
All **434 starting scoped paths remain: 403 unchanged and exactly 31 approved advances**
(20 production, eight backend test/support, three browser files). The proposal and
approved contract retain bytes. Staging is empty; scoped `git diff --check` passes.

## 2. Root cause and new evidence policy

Previously, processing created pending candidates, Accept and Save created wardrobe
records, and ordinary contextual inference additionally required a current human
style review. The recent Add/Edit confirmation supplied that review only after an
explicit human style choice. Those were separate boundaries, so removing one click
did not make unreviewed saved styles usable or automatically store new uploads.

Registry **context-registry-1.4.0** intentionally changes only the five ordinary
appearance policies to **appearance-2.0.0**, with CA2/SH2/CO2/DT2/DN2 rule IDs and
`saved_singleton_style_provisional_v1`. Grammar/taxonomy remain 1.3.0; eight binding
definitions remain. Wedding, university-presentation and job-interview binding
objects compare equal to their accepted originals. Their stricter evidence remains.

For each selected member, including selected outerwear:

1. Capability/code admission still precedes garment overrides. Formal/black tie,
   inactive contexts and unsupported conditions do not become available through Allow.
2. An identifiable applicable Deny wins. Otherwise malformed authoritative
   declarations/context containers block; a clean applicable Allow supplies only
   its condition. A separate requested formality Deny cannot be waived.
3. For absent declarations, a supported current singleton saved casual or smart-casual
   style may supply ordinary positive evidence. Explicit supported codes require
   the matching style; unspecified code creates no formality field or inferred code.
4. Missing, empty, multiple, unrecognised or uncovered styles remain Unknown.
   Category alone supplies no style or positive contextual fallback.
5. Present malformed/stale new source metadata blocks inference. A malformed owner
   review also blocks. A valid saved label with absent, stale or withdrawn human
   review can be used provisionally without rehabilitating that review.

New `saved_attribute_sources_v1` JSON binds the value digest, category, media and
owner, with an actual source/contributor and recording time. Sources distinguish
owner-supplied values, adapter output, reported model information, synthetic fixtures
and unknown origin. Future automatic adapter output cannot create owner confirmation,
contextual review, appearance observations or authoritative `rec:` declarations.
An origin claim is not calibrated model accuracy or human verification.

Existing records lacking source JSON remain **Absent / unknown origin**. Read-time
admission uses their saved facts without a backfill, owner audit or fabricated review
time. Genuine current human review still has its distinct basis. New explanations
are version 1.4.0 and retain source state, observed styles, actual review and per-condition
basis; `saved_attribute_provisional` is visibly different from reviewed inference.
Source/storage timestamps are explicitly not owner-review timestamps.

## 3. Automatic Add and central persistence

Normal frontend Add explicitly requests `automatic_structural_v1` on the existing
upload endpoint. Omitted API mode remains `manual_review_v1`, preserving legacy
Accept/Confirm and save-as-outfit callers. Existing endpoints carry the optional
versioned mode; no route or database schema is added.

Processing creates server-bound batch/item records, preserves actual source facts
and invokes the existing central writer. Its locked transaction validates the full
batch, owner/job/items, supported category/structure, owned usable image, processing
metadata, embedding contract and quota. Structural role/layer comes from the existing
category map. Style may genuinely be missing at storage time; it is not invented.

Only the full valid batch is materialised: garments, mirrored attributes, confirmed
item links and completed job commit together. No false human review is created.
Repeated finalisation returns the same IDs without consuming more quota. A client
cannot downgrade an automatic job to partial legacy confirmation. Cancellation,
foreign media, incomplete items, quota conflicts and write faults cannot create a
partially saved batch. Recoverable failures expose correction/retry; GET remains read-only.

An incomplete supported category can be corrected with one **Save corrections**;
the writer then retries the complete batch without another Accept/Confirm action.
Quota failure explains the 100 non-archived-entry limit. Successful completion shows
saved garments and an Open wardrobe action. The prepared-to-saved refresh follows
the separate writer transaction briefly, then retains Retry if finalisation needs help.

Acquisition now additionally requires the linked job to be **completed**, alongside
existing owner, available, confirmed-item and processing-owner checks. Merely displaying
an available garment is not permission to admit a failed/unconfirmed/foreign record.

The local fallback still produces unclassified/missing-style information. Such an
upload can correctly require a genuine category correction or lack evidence for an
ordinary suggestion. No models, defaults, confidence threshold or category-only policy
were added to manufacture success.

## 4. Results, existing garments and preserved protections

Disposable replicas bearing the eight requested demo names use existing saved casual/
smart-casual labels without Edit or review for shopping, class, friends, date and
dinner. Their garment records remain equal before and after those requests. This is
verification of the read-time contract, not inspection of the owner's actual records.
After later activation, existing valid records can use that policy without mass editing;
their actual saved facts and complete eligible structures still determine the outcome.

Results show complete garment cards/images and the stored exact ranking fraction,
for example **7/10** or **4/5**, before context details. The fraction comes from saved
score metadata, not recomputation, and is labelled as a ranking score. Unsupported
old metadata is not guessed. No-result and technical-retry outcomes remain explicit.
Optional review, correction, restrictions and withdrawal remain available.

The four structures, exact Fraction 60/20/20 arithmetic, request/compatibility/preference
semantics, deterministic ties and numerical scorers are unchanged. Independent checks
enumerate all four candidates and agree with reference/public verification: the
one-piece scores 7/10; paired structures score 4/5; `dress-A + outer-A` wins the stable
four-garment fixture. Source/review status creates no bonus or request term.

Actual disposable checks cover strict eligibility, changed snapshots at the locked
writer, INSERT-abort rollback, same-key recovery, immutable history/replay, saved
outfits, preserved preferences and copied-bearer denial after logout. The 99-entry/two-item
batch and two competing jobs for one remaining space verify atomic quota admission.
These are functional boundary tests, not a new capacity benchmark.

Existing-label adaptations are explicit: Date/Dinner E16/E17 and Everyday
CA03/SH03/CO03/N17 gain provisional saved-style admission. G07/N18 can select valid
unreviewed outerwear, with asserted members and exact 4/5 score. Truly missing-style
outerwear remains a separate Unknown control. Frozen label files retain their old
policy expectations; named current-version overlays and original test copies disclose
the transition. No old wedding/professional/interview policy oracle was weakened.

## 5. Executed verification

| Check | Actual evidence |
|---|---|
|Broader backend regression|**2,285 passed / one archived-source check deselected in 369.44s**, native exit 0. Existing processing, style, W/general/Date/Dinner/everyday/AP/IP, query, quota, compact ranking and durable-logout scope.|
|Final focused backend|**604 passed in 58.86s**, native exit 0: 603 new checks plus the source-transition check. Includes the approved 59 scenarios and eight later defensive checks. This overlaps the broader invocation.|
|Final source certification|**1 passed in 6.34s**, native exit 0 after final frontend changes. Checks all 20 transitions, both additions and independent starting-hash continuity against retained accepted manifests.|
|Explicit final N18 assertion|**1 passed / 81 deselected in 8.72s**, native exit 0. Strengthens the already passing named transition with selected-member/basis/exact-score assertions; not an extra distinct scenario.|
|Approved matrix|**59/59** scenarios match through disposable APIs; complete observations and unchanged labels retained separately. Not 59 additional passes to add to pytest totals.|
|Actual Chrome / production Next|**33/33 passed in 2.8m**, native exit 0: eight new journeys plus 25 existing definitions, with only the three approved existing browser files adapted.|
|Final TypeScript / scoped ESLint|Native exit 0. One existing internal `window.location.assign` navigation warning remains; no lint errors.|
|Production build|Native exit 0, Next 16.4.2 webpack; final retained build **RSaXDpBomxBO68YWyceCb**. All seven executed frontend production inputs match final sources.|
|Integrity|434 starting paths present, 403 unchanged, exactly 31 approved existing advances; proposal/contract/frozen labels preserved; empty staging and scoped whitespace check pass.|

There is no claimed clean combined backend invocation or pooled sum of overlapping
runs. The expensive full historical-archive check was explicitly excluded, not
reported as freshly passed. Its retained earlier evidence remains historical.
The final guard verifies exact current transitions and original accepted starting
hashes without recursively rerunning every historical audit for every path.

The new condition oracle covers **480 independent combinations**, plus 35 origin/
currency cases, strict specialist negatives and exact four-structure comparisons.
Five unreviewed-style 100-snapshot/two-condition checks observe 400 primary/independent
resolutions plus four winner/public resolutions and five compilations, outside candidate
enumeration. No per-candidate evidence/config work is introduced. Durations are
functional execution times, not latency acceptance; no full NFR benchmark ran.

Browser execution uses actual installed **Chrome 156.0.8078.48**, ordinary app.main/
Uvicorn, production Next and the normal same-origin proxy on owned 3100/3101. Accounts,
DBs, tokens and images are disposable. The processing port supplies explicitly
synthetic fixtures; a reported-model example is a provenance simulation, not model
inference. Development identity is off, child secrets unpublished, and VTOFF/VTON
off only in that disposable runtime. No private-account login or real model was used.

Browser checks cover zero review/confirm POSTs in normal successful Add, the eight
legacy replicas, missing style/category, one correction Save, Deny/code limits,
optional owner confirmation/withdrawal, Cancel/failed-save preservation, exact score
display, history/save/logout, technical retry, keyboard and long names. Bounds pass
at 360/390/768/1280/1920px. Native 200% uses Chrome settings zoom 2, DPR 2, CSS width
711, CSS zoom 1 and visual scale 1. The result heading is explicitly measured below
the fixed header. Inspected narrow-result/no-result and native captures are retained;
this is not a universal accessibility, usability or fashion validation claim.

## 6. Retained attempts, evidence and operational limits

Evidence is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\automatic_admission_implementation_20261027
```

It contains approvals, before/final sources, exact source-transition revisions,
patch, labels, complete 59-case responses, native logs, browser traces/captures,
disposable databases/builds, integrity and delivery index. The adjacent
`automatic_admission_review_20261027` retains the original read-only review.

All attempts remain:

- Initial focused runs passed 535 new checks and then 60 matrix/legacy-replica checks;
  they overlap final coverage. Two broader runs were deliberately interrupted while
  redundant historical hash-chain work was running. Only their recorded owned pytest
  workers were stopped. Their nonzero native codes/logs remain; no final pass count
  is assigned. The approved source test now compares every starting hash independently
  and validates all final hashes without repeated recursive archive execution.
- Browser attempt 1: one pass/one failure, 31 unexecuted. A new legacy setup read its
  asynchronously queued job too early; ordinary bounded polling fixes that fixture.
- Attempt 2: two passes/one failure, 30 unexecuted. This exposed the genuine results
  refresh race between prepared and saved state. The writer had saved correctly;
  the page now follows that transition.
- Attempts 3 and 4: four passes/one failure each, 28 unexecuted. The new optional-review
  test first preserved an unchanged value rather than explicitly choosing it, then
  used an exact dropdown label including option text. Correct explicit selection and
  a role-based selector test the real owner-confirmation action; no policy was relaxed.
- Attempt 5: 21 passes/one failure, 11 unexecuted. An unchanged general browser test
  exposed a missing named region around the collapsible situation details. The
  approved Assistant file restores that region while preserving the disclosure.
  Visual review also found a success heading covered by the fixed header at 200%;
  submission scrolling now leaves header space, with a new measured assertion.
- Attempt 6 is the final 33-pass run. No retries or extended deadlines converted
  these failures into passes. Intermediate builds/sources/traces remain separately
  identified. Small editing/probe helper failures are retained; the accidentally
  rerun old-policy pure probe failed its old assertion before writing its artifact.
  No original pure observation, oracle or historical result was rewritten.

Final certification follows all production changes. The final explicit N18 test
addition changes only that approved assertion; its separate pass and final source
snapshot reconcile it with the broader run. All final production inputs match the
executed final build/browser source records. Existing uv, Starlette/httpx, Playwright
colour and Git line-ending warnings remain; native child exit codes determine checks.

Owned disposable backends shut down with exit 0. Owned production Next processes
are terminated by the harness with exit 1, not claimed as graceful recovery.
Ports 3100/3101 are free. The unchanged manual listeners remain **88624 on 3000**
and **8528 on 8000**, with their existing creation identities. No manual service
was stopped or restarted. No migration, backfill, private-data edit, secret rotation,
model download, global configuration change, commit or deployment occurred.

## 7. Use and disposition

This source increment does not activate itself in the already-running Python
process. After a separately authorised manual activation, normal Add uses the new
automatic protocol; existing valid saved styles are admitted at read time without
requiring eight manual edits. Actual missing facts, restrictions, specialist evidence
and incomplete structures can still prevent a result. An older backend that does
not acknowledge automatic mode is identified by the refreshed frontend and retains
the legacy workflow rather than pretending automatic saving occurred.

Context default remains disabled. The existing process-only general profile and
Assistant/suitability/compact/decision flags remain the activation mechanism;
Homepage retains its separate workflow. No launcher or AI-mode change is included.

**PASS WITH LIMITATIONS.** Approved automatic admission and provisional ordinary
saved-style semantics are implemented and verified. Private demo outcomes and manual
activation remain pending their own scope. RN-13/FR-VIS-01 remain Partial; the nine
Unverified requirements and NFR-02 OPEN status remain. Real model/VTON evidence,
formal NFR baselines, deployment/HTTPS, architecture and data/recovery acceptance
are not resolved. No further policy increment, private-data operation or restart begins.
