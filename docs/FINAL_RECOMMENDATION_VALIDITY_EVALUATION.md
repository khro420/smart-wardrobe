# Phase 5F-2E-3J-15: final RN-28 validity and RN-30 evaluation records

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-14 is owner-closed PASS WITH LIMITATIONS. Evaluation only: no production source,
policy, route, default, provider, prior test or historical evidence was changed.
The combined evaluation has152 API case records:150 match their frozen J-15
expectations and two supplementary wording expectations fail. Every generated
recommendation passes the independent validity audit. The failures remain failures;
this report does not claim a152/152 clean evaluation-test pass.

## Original authority

The original Project I PDF was re-read directly, not inferred from the roadmap:
`C:/Users/chong/Downloads/RSW_ChongWeiPing_Project1 (1).pdf`, SHA256
`5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`.
Whitespace is normalised below. Raw extracted pages are retained in
`original-requirement-pages.json`.

- **RN-28, Must**, PDF190/printed179: “Every outfit recommendation produced during
  system evaluation shall use only current user-owned, confirmed and available
  garment records supplied through ConfirmedGarmentQuery and shall satisfy all
  applicable recommendation-specific eligibility conditions, mandatory request
  constraints, outfit-structure rules and compatibility rules.”
- **RN-30, Should**, PDF191/printed180: “The evaluation record should contain the
  original request, expected structured fields, actual structured fields,
  processing status, and generated recommendation result for each evaluated
  request.”

The earlier `FINAL_ACCEPTANCE_READINESS_REVIEW.md` identifies the missing combined
population and downstream execution. This report supplies new evidence for those
rows without rewriting that historical review. RN-29 remains the separate dataset
content requirement. RN-28 imposes no additional subjective fashion-accuracy
threshold, human-review sample size or minimum compatibility score.

## Frozen population, inputs and configuration

The original `backend/tests/fixtures/nlp_evaluation.v1.json` remains byte-identical:
SHA256 `ced6418193e866649b635c6671ff2a1387becbd0435eb9eb0dc3a04a439760ba`.
All40 detailed,30 partial,30 unsupported and20 no-feasible cases were executed
through the authenticated Assistant API. Original text, field labels and the
shared no-feasible scenario were preserved.

`backend/tests/fixtures/final_recommendation_evaluation.v1.json` freezes the
120 original cases' downstream wardrobes/expectations plus30 supplements. Its
SHA256 is `ec8e6fcad947216d057686809bbfdc3ba877edead7e8709078ba754425cc390c`.
It was written before application evaluation. It contains synthetic descriptors,
explicit declaration tags, confirmation/ownership states, preferences and
downstream labels, not engine-generated fashion ratings. Case-specific wardrobes
use small varied combinations of supported categories, primary colours, styles
and zero/one/three weighted preferences. They are functional coverage fixtures,
not an empirical wardrobe distribution or capacity experiment.

Two later controls, S31/S32, were separately frozen before their own execution in
`final_recommendation_controls.v1.json`, SHA256
`afd1e907e05522c9df8e443c0ea08888b61964c940ef3a90baad56b26dca7559`.
Its hash is retained in `frozen-controls.json`;
all initial dataset/fixture/vocabulary/policy hashes remain in the unchanged
`frozen-inputs.json`. The controls reuse the original P25 request and retain the
original failed supplements. They do not replace labels or tune application rules.

Every API case uses the actual app.main HTTP boundary, signed authenticated
account, normal composition and real disposable SQLite repositories. The shared
release fixture binds only disposable database paths; it does not substitute
NLP, the recommendation query, evaluator, scorer or persistence implementation.
Synthetic wardrobe rows/media are deliberately materialised test inputs with
explicit linked processing-item/job evidence. They are not real CV predictions
or independently reviewed owner fashion annotations. Actual register/password/
token code runs; development-header identity is disabled for evaluated requests.

|Selection|Frozen value|
|---|---|
|Execution|`compact_exhaustive`|
|Scoring|`experimental_compatibility_decision_v1`, exact3/5 R +1/5 C +1/5 P|
|Assistant / suitability / Homepage|Enabled explicitly in evaluation composition and isolated browser child processes|
|Suitability|All eight approved occasions and casual/smart_casual; exercise/formal unavailable|
|Quota|Existing100 non-archived stored entries; unchanged writer and archive semantics|
|Routing / provider|J-14 fail-closed integrated routing; SQLite|
|Colour|Approved names/exact anchors; approximate hex disabled|

Read-only observers capture the actual interpreter result and actual ranking-time
ConfirmedGarmentQuery return values without changing them. Two supplements use
explicit test-only fault hooks at persistence boundaries. No ordinary client
selects profiles/evaluators; no global defaults or installed service settings
are activated. Prior RN-27 retained accuracy artifacts remain separate and are
not overwritten or reclassified by this combined evaluation.

## Complete evaluation results

Every case's original text, expected/actual intent and fields, expected/actual
terminal status, HTTP response, recommendation ID or explicit terminal result,
IDs/roles, exact score/provenance, raw wardrobe proof, actual query observations,
quota, SQL counts and persisted snapshots are retained in `initial-cases/<ID>.json`.
The directory name denotes the retained collection, not an incomplete sample.
`case-ledger.csv` gives the full field comparison; `case-ledger.md` lists all152
case statuses. `independent-audits.jsonl` stores every final independent audit.

|Population|Cases executed|Result|
|---|---:|---|
|Original detailed|40|All intent/fields and J-15 expected outcomes match.|
|Original partial|30|All intent/fields and J-15 expected outcomes match.|
|Original unsupported|30|All UnsupportedRequest; no recommendation/chat generated.|
|Original no-feasible|20|All intent/fields match;18 NoEligibleGarments,2 PolicyUnavailable.|
|Supplementary plus separate controls|32|30 match; S07/S15 retain wording-label mismatches.|
|Total|152|150 matching case records;2 mismatches;71 API recommendations generated.|

**Original no-feasible qualification:** N05 (exercise) and N06 (formal) reach
the actual downstream policy check and return PolicyUnavailable before retrieval.
The original dataset's shared scenario says NoEligibleGarments for all20. That
old shared label is preserved, and these two differences are recorded explicitly.
J-15's separately frozen operational expectations anticipated the existing policy
precedence; the report does not claim20 NoEligibleGarments results, garment-query
execution for those two cases, or fulfilment of exercise/formal. All20 requests
were submitted downstream; none remains merely NotEvaluated. The other18 actually
reach the empty acquisition path. Supported NLP intent is preserved in all20.

|Actual API processing outcome|Count|
|---|---:|
|Selected|71|
|UnsupportedRequest|32|
|NoEligibleGarments|23|
|PolicyUnavailable|11|
|NoMatchingCandidates|6|
|InsufficientEvidence|5|
|InsufficientStructure|1|
|WardrobeChanged|1|
|PersistenceFailure|1|
|InvalidInput|1|

S20's empty body text is rejected by Pydantic422 before NLP invocation. Its
InvalidInput is a normalised HTTP validation outcome, with raw validation detail
and null actual structured fields retained; it is not an invented NLP prediction.
The32 UnsupportedRequest outcomes comprise the original30 plus the two wording
mismatches below. No supported-but-empty wardrobe is relabelled unsupported.

### Retained mismatches and added controls

S07 and S15 both freeze “Suggest a classic outfit” as Supported/style=classic.
The implemented phrase vocabulary recognises “classic look”/“classic style”,
and this text actually returns UnsupportedRequest, reason unrecognized_condition,
with no structured request or recommendation. Their intended NoMatchingCandidates
and InsufficientEvidence outcomes are not reached. Both evaluation assertions
remain failed in the logs and final ledger. This is a new supplementary label/
bounded-grammar mismatch, not evidence that an outfit violated RN-28. It does not
justify silently changing a production rule, widening language scope or claiming
unseen-language accuracy. Owner review should retain this limitation.

S31/S32 use the exact unchanged P25 text, “Recommend a classic look.” They keep
the corresponding known-vintage or missing-style wardrobes. They produce the
intended NoMatchingCandidates and InsufficientEvidence outcomes, respectively.
These separately frozen controls establish downstream style exclusion/unknown
coverage without replacing S07/S15 or the original120 labels. No application
defect requiring a production correction was established; this phase changed
no production source.

## Independent RN-28 audit

`backend/tests/final_evaluation_auditor.py` imports only standard-library modules.
It reads approved declarative vocabulary/policy files, but imports no application
scorer, candidate generator, ranker, mandatory gate or interpreter. It independently:

1. Reconstructs owner/status/confirmed-item/job-owner eligibility from raw SQL
   proof and compares it with actual strict-query observations. Missing identity,
   media references and unsupported structure cannot introduce candidates.
2. Enumerates the four supported structures, checks every applicable category,
   global primary colour, base style and all-member occasion/formality condition,
   with Fail-before-Unknown aggregation and no guessed declarations.
3. Calculates exact Fraction request/preference contributions, real pair colour/
   Dice atoms, unknown midpoint/no-pair conventions and60/20/20 totals for every
   valid candidate. It compares complete scored counts and the minimum exact
   total/R/C/P/stable-ID ordering with the one returned winner.
4. Checks public scores, raw versus decision compatibility, provenance/policy
   hashes, SQL ownership/items, persisted request fields, score metadata, receipt
   and immutable display snapshots against the evaluated result and source rows.

All71 API recommendations pass all applicable checks. There is no missing,
foreign, archived, unavailable or unconfirmed selected garment; mandatory
conditions are Pass, not Unknown or Deny. The mandatory compatibility rules in
this accepted profile are the configured structural/eligibility rules. Colour/
style coordination values are documented scoring proxies, not an additional
hard aesthetic cutoff. A low known atom, midpoint or single-dress1/2 does not
constitute evidence of fashion quality or a reason to invent another rejection.

|Independently verified winning structure|Count|
|---|---:|
|Top + bottom|55|
|Top + bottom + outerwear|8|
|Dress|6|
|Dress + outerwear|2|

Compatibility bases are62 Computed,6 NoPairReference,2 PartiallyConventional and
1 FullyConventional. All exact totals and deterministic ties agree. Null raw
evidence remains null; numerical decision contributions do not manufacture a
measured compatibility value. Auditor mutation checks reject foreign/archived/
unconfirmed/missing members, bad job ownership/query origin, mandatory Deny,
wrong score/weight/provenance/snapshot/receipt, extra writes and a wrong stable-ID
tie winner. They also retain S07/S15 as audit failures.

## Negative, ownership, quota and transaction coverage

S01-S04 cover empty, fully archived, unavailable/accepted/pending/rejected,
NULL/dangling/foreign-job links and foreign-only wardrobes. S05/S06/S31 cover
definite category/colour/style nonmatches. S08-S11/S25 cover Deny, Unknown,
conflicting/malformed declarations and Fail precedence. S12/S13 preserve
exercise/formal PolicyUnavailable. S14/S32 preserve uncalibrated hex/missing
style Unknown. S16 excludes a missing media reference; S21 exposes incomplete
structure; S22 confirms an outerwear-only style cannot satisfy base style.

S17 archives the selected synthetic garment after ranking but before transaction
revalidation; the real repository returns WardrobeChanged409 and writes no
generation rows. S18 raises after metadata insertion, before commit; the real
transaction returns PersistenceFailure503 and rolls back all six generation
tables. These are disclosed fault-injection correctness cases, not ordinary
service failures hidden from the report. S19 has100 active entries, with99
unavailable/unlinked rows and one eligible confirmed dress. Usage stays100,
eligibility stays one, and recommendation succeeds without consuming a slot.
S23/S24/S26-S30 exercise unknown/no-pair, supported structures and stable ties.

## Normal production-browser regression

One unchanged J-14 activated-journey browser test passed against actual app.main,
normal account/login, same-origin proxy and the retained production Next build
`K69qSH2Qlp-dAB6ZtNOys`. The J-15 supervisor runs only the experimental/suitability
stage; it does not add deferred-profile results to this frozen evaluation.
No new frontend source/configuration or build was needed.

The browser generates one Assistant recommendation and one random valid Homepage
recommendation. Both are separately audited in `browser-audit.json`. Assistant
R=C=P=1 and total1 agree with the independent oracle; persisted references and
metadata agree. Homepage is checked for valid owner/confirmed/available membership,
structure and display snapshots, not deterministic Assistant ranking. It creates
no chat. The normal journey also covers declaration Deny/Unknown/conflict,
unavailable values, save/VIS preparation, foreign-owner actions and quota/archiving.

This regression's independent source check uses a stopped-service, read-only
transaction-bound strict-query snapshot after the journey, with fixture attributes/
availability and Allow declarations restored. That qualification is retained;
the primary152 API records separately capture actual ranking-time query returns.
Browser lifecycle/flags and raw rows are retained. Its two generated outputs
bring the audited acceptance population to **73/73 valid recommendations**:
71 API +1 browser Assistant +1 browser Homepage. Focused regression-suite outputs
are separate test evidence, not additional corpus rows or undisclosed accuracy
samples. All owned browser/backend processes were stopped.

## Verification, integrity and acceptance recommendation

- First collection:126 passes and the retained S07 failure; it stopped at that
  failure. Remaining-case/control collection:24 passes and the retained S15
  failure. Together these are152 distinct executed cases, not152 passes. No
  original case was rerun to replace a slow/failed observation.
- Focused backend/API/source-guard and auditor regressions: **629 passed in102.93s**,
  with one existing Starlette/httpx deprecation warning. These are distinct from
  the evaluated case expectations, not a way of hiding the two failures.
- Production browser: **one test passed**, with both generated results audited.
  It reused unchanged frontend code/config/build. TypeScript/lint were not rerun
  because no frontend file changed; their J-14 evidence is preserved, not claimed
  as newly executed. No NFR, capacity, profiling or model-inference run occurred.
- The special evaluation collector now requires its explicit evidence-output
  environment variable, preventing an ordinary regression run from silently
  repeating the whole population. A guard check skips one selected case when
  that variable is absent; this does not skip or relabel any of the152 completed
  records or waive the two failures when evaluation is explicitly invoked.
- Source/evidence inventory: all1,938 captured starting files and all69 J-14
  indexed deliverables remain unchanged. Original dataset, policies, manifests,
  source guards and frozen J-10 through J-14 evidence retain their bytes. No
  source-hash transition or historical rewrite was needed. `git diff --check`
  and explicit new-file whitespace checks passed.

New files are limited to the two frozen fixture JSONs, the standalone auditor,
its mutation tests, the explicit API evaluation collector, this report and
`storage/verification/phase5f2e3j15/` scripts/records. Exact commands, all failures,
raw cases, final audits, hashes and complete ledgers are retained there.

|Requirement|Acceptance recommendation|
|---|---|
|RN-28|PASS WITH LIMITATIONS for the frozen bounded synthetic configuration: every generated acceptance-population recommendation passes the independent applicable validity checks. This closes the combined-output audit gap for this population, subject to owner review, without certifying real CV evidence, arbitrary fashion judgments or deployment.|
|RN-30 (Should)|Fulfilled for all152 evaluated API requests: original request, expected/actual fields, processing status and complete generated or explicit terminal result are recorded, including failures and policy-unavailable cases. The two browser outputs have separate full regression/audit records.|

**Overall: PASS WITH LIMITATIONS.** Original120 NLP labels are preserved and
matched; all20 no-feasible requests now have actual downstream outcomes. Keep
both supplementary wording failures and N05/N06's original-scenario differences
visible in any report or presentation. No independently collected user corpus,
real CV colour/style accuracy, human outfit-quality ratings or model-backed VTON
quality is established. A human quality pilot is optional evidence for stronger
claims, not an invented RN-28 threshold.

Bounded suitability (8/2), non-anchor colour/fallback-black provenance, annotation
freshness, default-off deployment, real quota inventory/recovery, SQLite versus
the report's PostgreSQL commitment, real model artifacts and service deployment
remain external acceptance limitations. None of NFR-01/02/03 is formally accepted
by this phase; NFR-02 remains OPEN. No J-16 or further implementation starts.
Wait for owner review.
