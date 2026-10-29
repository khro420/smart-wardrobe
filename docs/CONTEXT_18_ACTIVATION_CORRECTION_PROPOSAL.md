# Eighteen-context activation: reproduced compatibility defect and scoped correction

2026-10-28, Asia/Kuala_Lumpur. **Correction approval pending; no application edit or
manual stop/start performed.** The owner accepted source closure and requested local
activation. Section 10 of the attached activation request says: “Do not modify
application logic unless a reproducible activation defect is discovered and separately
approved.” This is that boundary; it is not approval of a new policy/development phase.

## Reproduced defect

The current 32 production hashes match the accepted implementation and retained final
source copies. Fresh `configure_local_workflow()` selects the expanded interpreter and
compact A1 scorer, but its compatibility probe fails on an original ordinary request:

|Exact text|Retained eight-context interpreter|Accepted expanded interpreter|
|---|---|---|
|`I'm meeting friends for dinner.`|Supported dinner|UnsupportedRequest / context_clarification_required|
|`I'm meeting friends.`|Supported casual outing|UnsupportedRequest / context_clarification_required|

The expanded matcher additionally recognises a generic workplace `meeting`. It does
not refine that contained match into the existing `meeting friends` expression, and
does not carry forward the retained dinner companion relation from the old interpreter.
The original matcher already has a licensed “meeting friends for dinner” refinement;
this is a compatibility regression in the expanded path.

The six exact compound/wording checks in the attached activation request parse as
Supported on the accepted source. Negation and dinner-plus-hiking remain controlled
refusals. These are in-process observations, not private-account requests. The failed
factory probe has native exit 1; the separate diagnostic collector exits 0 after
recording the reproduced failure. Neither is a claim of activation readiness.

## Concrete proposed patch and exact scope

The unapplied candidate is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\context_18_activation_20261028\proposed-compatibility-correction.patch
```

It is syntax-checked only; the candidate has not been executed or written into the
application. Its production change is limited to:

`backend/app/application/nlp/context_expression_matcher.py`

1. Refine a contained bare workplace `meeting` into the already supported longer
   casual-outing expression `meeting friends`.
2. For that exact expression linked to dinner by the licensed `for [a]` bridge,
   retain dinner as the event and friends as the companion. Port the retained
   interpreter's scoped relation rather than discard an arbitrary second occasion.

Unrelated events, work/domain ambiguity, negation, residual meaningful modifiers,
role/code/venue gates, Deny and all numerical scoring remain governed by existing
checks. No grammar/taxonomy/objective default, occasion permission or garment value
is added. The bundle configuration identities remain their accepted versions; the
implementation-source transition is separately pinned and disclosed.

Proposed verification/support edits, also pending approval:

|Existing file|Exact purpose|
|---|---|
|`backend/tests/test_context_expansion_nlp.py`|Add preservation cases for all five original ordinary requests under the expanded bundle, the standalone friends expression, and related negative/domain controls. Preserve the frozen 80-case fixture.|
|`backend/tests/test_context_expansion_integration.py`|Extend the existing complete-outcome loop to the five original ordinary requests as well as the ten new contexts, checking exact stored display/provenance and unchanged garments. Add controls without weakening existing assertions.|
|`backend/tests/integration_source_guard.py`|Chain a new exact correction transition for the matcher/support guard; do not repin the accepted expansion manifest or old historical declarations.|

One new support fixture is proposed:
`backend/tests/fixtures/context_18_activation_correction_sources.v1.json`.
It records exact before/after hashes, preserved approved label hashes and the new
guard transition. The original `context_expansion_sources.v1.json`, all accepted
reports, labels and final source copies remain unchanged historical evidence.

This is **one production file, two existing test modules, the existing source guard
and one new transition fixture**. No other production/test/UI file is proposed.
Task-specific diagnostic/verification documents and external evidence will record
actual results. No private operation, schema/default/model/launcher change, staging,
commit or restart is included in correction approval.

After approval only, run the current approved language/policy/ranking/API/history
checks, the added original-context regressions, actual factory probe, current source
certification and focused disposable browser/API smoke. Retain all failures and source
inputs. Do not ask for or execute the precise manual restart until the correction and
fresh startup gate are satisfactory. Restart approval remains a separate section-4
boundary in the user's request.

## Current activation preparation

Fresh identities match launcher creation records: backend parent **28700**, shim
**86332**, listener **90644 on 8000**; frontend parent **13376**, listener **16888 on
3000**. These are observations for this preparation, not future permanent targets.
The current seventh A1 selection is present; the eighth bundle override is absent.
Public health/auth return 200; protected capabilities/garments return 401 through the
backend and normal same-origin proxy. No private sign-in was attempted.

The established read-only schema/migration/aggregate gate passes with **zero garment
backfill, visualisation backfill, processing recovery and visualisation recovery
targets**. Metadata/data-version observations remain unchanged during that short gate.
This does not guarantee future quiescence; a new user write can arrive afterward.
No migration, recovery, private repair or service operation has been performed.

Fresh disposable verification on the unchanged accepted sources:

- Actual factory/validator: eight-setting composition, final bundle versions and
  18/15/3/5 capability counts are valid, but compatibility readiness is **false** for
  the dinner sentence above. The complete observation exits natively with 1.
- Combined requested API/language smoke: **86 passed / two failed in 30.25s**, native
  exit 1. One failure is the actual dinner regression. The other was an external
  test assumption that a controlled no-result must have `complete=false`; the existing
  contract permits `complete=true` when evaluation completed without an eligible outfit.
  Its assertion now checks non-selection and absence of a recommendation. The original
  external helper remains; no application code or approved oracle was changed.
- Corrected independent negative checks: **4 passed / the known-positive regression
  test deselected in 11.94s**, native exit 0. Covers unavailable/ambiguous/specialist
  language, strict specialist evidence, broad Deny, no broad Allow inheritance, missing
  style, completed-job exclusion and honest incomplete processing. It does not relabel
  the deselected dinner failure as a pass.
- Actual Chrome: **9/9 passed in 1.1m**, native Playwright/harness exits 0, reusing the
  unchanged verified production build **J2J5xgB9_QsntW_s_6zy7**. Existing nine journeys
  cover the ten new contexts and shared controls, but do not submit this exact canonical
  dinner request. These passes therefore do not resolve the compatibility failure.

Browser accounts/data are disposable, development identity is off, processing is an
explicit synthetic fixture and child secrets are unpublished. API fixtures use their
existing controlled test identities. The owned disposable backend stopped with native
exit 0; its production Next process was terminated by its harness (exit 1). Verification
ports 3100/3101 are released. The manual services were not targeted.

All starting scoped source/test/report paths remain unchanged. This proposal is the
sole new repository file; the candidate patch and other artifacts are outside OneDrive.
The source matcher still has its exact accepted hash. Prepared stop/start code has
not been run and no new restart approval has been requested or recorded.

**Disposition: seek explicit approval of this exact compatibility correction.** The
gate's success alone does not make the demonstrated original-request regression a
passing activation result. Existing running manual services remain untouched.
