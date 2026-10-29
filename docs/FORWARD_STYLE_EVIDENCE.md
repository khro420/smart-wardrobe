# Phase 5F-2E-3J-2: forward style evidence and edit preservation

2026-10-22, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS - ready for owner review / Phase3J-2 closure.**
Owner and teammate explicitly authorised this scoped shared wardrobe/frontend
correction in the owner's confirmation reply. Phase3J-1 remains closed; its VIS
code, tests and source transition are unchanged. No subsequent phase is started.

## Before and after semantics

Original RN-11/12/13/15 and the documented Phase1 evidence contract require
truthful current evidence; report section4.10.4 requires documented scoring,
not a new style prediction. Null/empty/omitted distinctions are owner-approved
integration policies, not exact JSON states mandated by the original report.
The closed3I/3J reviews identified the real upstream loss: styles-or-empty in
wardrobe persistence, plus an unconditional frontend CSV-to-list submission.

| Input / operation | Forward behaviour |
|---|---|
| Omitted style during creation | Preserve any existing candidate annotation; if the candidate has no style, persist missing/JSON-null style column. No evidence invented. |
| Explicit attributes.style=null | Canonical null and JSON-null style column; Phase1 snapshot None / Missing. |
| Explicit attributes.style=[] | Deliberate empty assigned-tag set; snapshot () / Known-empty. Not proof that a garment objectively has no fashion style. |
| Nonempty list | Preserve original entries/order in canonical attributes; existing snapshot normalisation remains unchanged. |
| Supported existing string | Remains a string in canonical attributes and a single-entry list in the dedicated column, as before. |
| Omitted style during PATCH | Do not write the authoritative style column or alter the canonical style entry. Preserve the legacy additional_attributes style entry independently. |
| Unchanged wardrobe form | Empty PATCH; no attribute regeneration from displayed blanks. |
| Unrelated wardrobe edit | Only changed fields are submitted; style, fit/material lists, tags, unknown temperature and other unchanged values are not overwritten by display defaults. |
| Explicit Unknown / Empty / Assigned in editor | Sends null / [] / entered list. Blank or comma-only assigned text shows a validation message and sends no clearing PATCH. |
| Review unchanged style | Omits style from the review attributes, retaining the actual candidate value, including absent/null/list/string. |

There is no independent garment-create API. Creation tests use real upload,
review and confirmation with synthetic detector/attribute adapters and genuine
item/job ownership links. Omitted review fields retain candidate evidence;
omission does not erase a real existing annotation. A deliberately style-free
attribute fixture verifies the truly absent creation case.

## Implementation and data boundaries

Only one backend application file changes: wardrobe_service. Creation writes
JSON null rather than substituting []. Updates only write style/custom-tag columns
when their keys are explicitly present. The existing additional_attributes
mirror is also protected on omitted style/tag writes: preserved entries cannot
be lost or regenerated from another historical representation. Malformed legacy
mirror data is retained, not silently repaired into apparently valid evidence.
Normal explicit changes update canonical/dedicated representations together.
The existing update transaction now starts with BEGIN IMMEDIATE before reading
and merging the row, preventing a concurrent style edit from being resurrected
by an unrelated stale PATCH. Independent SQLite connections verify the lock and
subsequent explicit-null preservation. This does not establish PostgreSQL locking. No new field, database provider or migration is introduced.

The wardrobe editor has Preserve current, Unknown, No assigned tags and Assigned
style tags choices, plus the existing free-text tags input. The review form keeps
its existing style vocabulary and adds explicit preservation/unknown/empty
choices. Internal selector values are not new stored style names. Existing API
schemas already accept these payloads; only the TypeScript client type needed
null support and typing for already-returned representation fields. No API route
or server payload schema changes.

The editor's current display follows existing dedicated-column, canonical
attribute and legacy-mirror precedence. Explicit canonical null does not fall
through to stale mirror values. The actual Phase1 mapper remains unchanged.
No category, colour, image or pattern is used to infer style.

Existing malformed additional_attributes JSON is a separate, reproduced upstream
limitation: the unchanged row serializer raises before an edit can proceed.
The negative test expects rejection and verifies no mutation. This phase does not
claim normal UI edits can repair corrupt JSON. Such records require separately
approved data repair; ordinary valid null/list/string records work forward.

## Recommendation interpretation remains unchanged

Snapshot/evidence mapping: null ->Missing, [] ->Known with zero tags, recognised
nonempty tags ->Known with matching values. Malformed and unsupported evidence
keep the existing conservative states. A requested style with no positive base
match is Unknown if evidence is missing, versus Fail for fully known empty/nonmatching
base evidence. Neither can be promoted into mandatory Pass. A different base
member's positive evidence may still satisfy the existing outfit-level minimum.

Tests use persisted snapshots with a vintage lower garment: an unknown upper
garment gives R=1/2 with Partial diagnostics, an empty upper gives R=1/2 with
Available diagnostics, and two vintage bases give R=1. Existing colour/style
compatibility arithmetic is unchanged: with recognised coordinating colours,
unknown or empty style-pair evidence keeps the existing 3/4 decision convention;
two matching observed vintage styles give1. These are synthetic arithmetic checks,
not independent fashion-quality evaluation or a new default policy.

Compact/deferred remain defaults. Exact weights, mandatory gates, NLP, candidate
generation, eligibility, homepage behaviour, saved-outfit VIS, suitability opt-in,
disabled approximate hex and legacy routing remain unchanged.

## Historical limitations and preservation

No existing rows are bulk rewritten. An old [] may be deliberate or the result
of the former loss; original intent cannot be recovered from that value alone.
Opening/saving an unchanged form preserves it. The owner may explicitly review
and choose Unknown or actual tags using these controls; that is a new owner edit,
not retrospective proof or automatic reclassification.

Lifecycle tests retain raw snapshots of recommendation, item, historical display,
score metadata, chat, visualisation and visualisation-item rows while editing
current style evidence. They verify byte/value equality after successful edits,
foreign-owner rejection and injected transactional failure. Existing VIS jobs'
normal restart/cancellation lifecycle is not altered by this phase. Tests do not
restart the app midway and mistake its recovery behaviour for an edit mutation.

## File inventory

| File | Purpose |
|---|---|
| backend/app/application/wardrobe/wardrobe_service.py | Forward representation writes and omission preservation across canonical/dedicated/mirror evidence. |
| frontend/app/wardrobe/page.tsx | Partial payloads, explicit style actions, blank validation and current evidence display. |
| frontend/app/extract/results/page.tsx | Preserve unchanged review styles; explicit unknown/empty choices without vocabulary changes. |
| frontend/lib/api.ts | Null-capable existing attribute update type and types for existing returned representation fields. |
| backend/tests/test_forward_style_semantics.py | Persisted creation/update/state, mapper/scorer, rollback/ownership and historical preservation coverage. |
| frontend/tests/style-edit.spec.ts | Actual API-backed review/confirm and wardrobe edit/save/reload tests. |
| backend/tests/integration_source_guard.py | Chain this phase's exact one-backend-file transition, preserving old archives. |
| backend/tests/fixtures/forward_style_sources.v1.json | Separate backend and frontend before/after hashes for this authorisation. |
| docs/FORWARD_STYLE_EVIDENCE.md | This contract, implementation and verification report. |
| docs/REPORT_TRACEABILITY.md | Append scoped evidence/limitations without changing closed reviews. |

Raw logs, original source backups, authorisation record, commands and integrity
artifacts are under storage/verification/phase5f2e3j2. Initial failures and
interrupted trials are retained; final results will be recorded below.

## Verification status

Final checks are complete; exact results and retained attempts are recorded below.
No formal NFR benchmark, production database inventory,
model inference or scoring/suitability activation is part of this work.

## Retained development and verification attempts

No earlier results were overwritten. Initial test-fixture mistakes are explicit:

- style-initial.log:36 passes/1 failure; the archival test's service writer used
  the original configured DB path instead of the disposable fixture DB.
- focused.log:12 failures/27 passes/152 setup errors; an attempted test-only
  repository factory accepted no arguments, but the history reader supplies one.
  That factory patch was removed; no application persistence path was weakened.
- diagnosis.log:the same setup error isolated with stop-on-first-error.
- focused-final.log:190 passes/1 failure; archival fixture supplied empty policy
  provenance, correctly rejected by the existing value object.
- history-targeted.log:1 failure; an unnecessary nested application lifespan
  invoked existing interrupted-VIS recovery. The test now uses the same lifespan
  and catches its injected write exception directly; VIS recovery is unchanged.
- focused-complete.log:191 passes before the final legacy-mirror/atomic additions.
- focused-mirror.log:193 passes/1 failure; reproduced the pre-existing malformed
  JSON edit blocker. The final test verifies rejection/preservation rather than
  pretending this phase implements a general malformed-row repair.
- focused-verified.log and backend-final.log were interrupted when superseded by
  the final atomic read/merge/write correction. Incomplete runs are not passes.
- backend.log:1,891 passes/one known architecture failure on the earlier patch,
  before the final mirror and lock additions. The final broad run is separate.
- browser-focused.log:7 setup failures from reading processing items before the
  asynchronous job became review-ready; fixed by polling its actual status.
- browser-focused-retry.log:interrupted after exact-label selector timeouts;
  accessible combobox roles are used now, without extending test limits.
- browser-style-final.log:4 actual wardrobe flows passed/3 review-test failures.
  All three confirmations returned201, but Chromium discarded response bodies
  after navigation. Final tests read persisted garments by processing-item ID
  using the authenticated API after reload; no navigation timing is suppressed.

These are retained implementation/test-development observations, not hidden
application successes or final acceptance evidence. All raw traces/logs remain.

## Current functional verification

Final focused backend command: **195 passed**,165.86s, one existing
Starlette/httpx deprecation warning. It includes current snapshot/scoring,
review/confirm/tag lifecycle and closed3J-1 saved-source regressions. Final
TypeScript exit0; lint exit0 with the two existing navigation warnings
(extract/results:157 and Layout:50); isolated production build exit0 on
Next16.4.2. Final broad/browser/integrity results are recorded below.

Examples of intentional forward behaviour changes: newly missing styles remain
Unknown rather than becoming known-empty. A style-only request can therefore
correctly yield InsufficientEvidence instead of NoMatchingCandidates when no
base garment provides a match. An existing legacy [] is left as recorded.
Partial/Available score diagnostics remain truthful; no scoring formula or
mandatory threshold changes. No missing evidence is converted to a positive match.

## Final backend, frontend and integrity results

| Check | Exact result |
|---|---|
| Final focused five-file backend suite | **195 passed**,165.86s; focused-final-atomic.log. |
| Final broad `tests --ignore=tests/test_segmentation_geometry.py -q --tb=short` | **1,895 passed,1 known failure**,408.57s; backend-atomic-final.log; pytest exit1. |
| TypeScript `npx tsc --noEmit` | Exit0; types-final.log. |
| `npm run lint` | Exit0,two existing navigation warnings; lint-final.log. |
| `npm run build` with isolated forward-style-final-production directory | Exit0; build-final.log. |
| Entire integration browser suite | **42 passed**,7.8m; browser-all.log. |
| Restarted final-code style/action browser suite | **10 passed**,3.2m; browser-final-actions.log; exit0. |
| Frozen-source integrity | All39 earlier fixture/archive files unchanged; separate one-backend/three-frontend hash transition. |

The only backend failure is unchanged
`tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`,
line28, asserting that ai-services must not exist. Neither directory nor assertion
was changed. The dedicated CV geometry suite remains excluded from this general
test environment; no real CV/VTOFF/VTON model, deployed service, production data,
PostgreSQL migration/locking or formal NFR measurement was tested.

The42-case browser server began before the final backend BEGIN IMMEDIATE addition.
Its final frontend preservation/review checks pass; the195 focused and full broad
backend runs exercise the final lock. A fresh server restart repeats the10
specifically affected style/action cases against the final application source,
without claiming the earlier42 ran code that had not yet been loaded. Initial
and intermediate builds/tests, failures and interruptions remain separate.

Exact commands, environment and raw logs are in
`storage/verification/phase5f2e3j2/commands.txt`. Test suite durations are verification
runtime, not clean latency measurements or NFR acceptance evidence. Production
flags, defaults, timeouts and scoring selections are unchanged.

## Final integrity and closure assessment

Final restarted-server tests passed all10 affected cases against the completed
application patch. No production code changed after the final lock correction.
The final frontend TypeScript/lint/build checks passed; verified Next-generated
tsconfig include additions were removed by restoring the exact captured bytes.
No package/lock, AGENTS, VIS or completed Phase1-4 scoring/query/NLP source changed.
`git diff --check` passed; raw line-ending warnings are retained.

**300 pre-existing files checked; all39 historical fixture/archive files unchanged.**
Only the one backend writer, three frontend application/type files, test source
guard and appended traceability changed among captured files. New files are the
two focused test files, separate transition manifest and this report. Exact main
file hashes are in deliverables.json; integrity.json records the comparison.
Existing closed3H/I/J/J-1 reports and both3J-1 VIS application files are unchanged.
Verification logs, backups and artifacts are indexed separately in this phase's
storage folder; no earlier phase evidence was overwritten.

**Phase3J-2 is ready for owner closure as PASS WITH LIMITATIONS.** Forward omission,
null, empty and assigned style semantics are stable across actual persisted
review/confirm/edit flows and recommendation consumption. Exact matching/scoring
rules, strict eligibility, historical snapshots and defaults remain intact.
No new application regression was reproduced. The known architecture assertion,
excluded CV geometry/model coverage and real deployment/PostgreSQL acceptance
remain separate. Existing ambiguous [] and malformed legacy data are not repaired.

This is a sufficiently tested forward-write foundation for separately approved
RN-13 controls and later RN-17 activation work. It is not authorisation to begin
those tasks, enable suitability, activate scoring, calibrate colour matching or
run formal NFR tests. Existing style records still need owner review where their
original meaning is uncertain; genuine fashion-quality/provenance limitations
remain. Overall final FYP acceptance remains open. Wait for owner review.
