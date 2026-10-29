# Phase 5F-2E-3J-18: coordinated remaining functional-gap closure

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-17 is owner-closed PASS WITH LIMITATIONS. Its full 155-row matrix and original
requirement wording remain the authority. This round implements the expressly
approved corrections; it does not approve whole-FYP acceptance or deployment.

## Ownership and exact scope

The owner separately answered **“Approve this shared scope”** for registration,
profile/preferences and necessary callers/tests, **“Teammate approves these
filters”** for listing-only wardrobe colour/style/availability filters, and
**“Approve the narrow phrase mapping”** for classic outfit. J-18 section 2 already
authorised R production diagnostic logging. `ownership-approval.json` records the
named files and exclusions. No additional ownership consent is inferred.

Durable logout revocation is excluded from the shared approval until a storage
design is agreed under the no-migration constraint. Browser token removal is
still not server invalidation. **FR-ACC-15 remains Partial.** No in-memory
revocation substitute, security/provider/schema change, model run or real-account
database inspection was made.

| Original requirements | Owner / approved production files | Correction |
|---|---|---|
|NFR-13|R: Assistant/Homepage services; new `failure_diagnostics.py`|Safe structured production failure events, preserved responses/rollback/replay.|
|RN-03 related wording; J-15 S07/S15 correction, no status-count increase|R: `backend/app/application/nlp/config/vocabulary.v1.json`|Add exactly the classic outfit alias to the existing classic style.|
|FR-ACC-02/03/04/05/06/07; negative-path evidence FR-ACC-09/11|Shared: `backend/app/api/account_routes.py`, `backend/app/application/account/account_service.py`, `frontend/app/auth/page.tsx`, shared API helper|Required confirmation, server validation, duplicate serialization, success-to-login and actual negative login checks.|
|FR-PP-03/04/05/07/08; retained 01/02/06/09|Shared: account routes/service, `backend/app/domain/value_objects/requests.py`, `frontend/app/profile/page.tsx`, API helper|Controlled four-group choices/weights, validated writes, explicit cancel and failed-save preservation.|
|FR-DW-13|T-approved: wardrobe service/routes, `frontend/app/wardrobe/page.tsx`, shared API helper|Owner listing filters only; non-available rows read-only.|

There are **12 modified existing production files plus one new production helper**.
Two current test modules adapt necessary callers/contracts: `test_workflow.py`
and `test_garment_workflow.py`. Their original copies are retained. Registration
fixtures now supply confirmation and authenticate through login. The workflow
preference example uses a supported style instead of previously accepted prose;
new tests explicitly prove unsupported prose rejection and preservation.
`integration_source_guard.py` follows new exact transitions. No old report,
manifest, archived test/oracle, J-15 collection runner or raw artifact is edited.

The complete production-file inventory is:

| Production path | Type |
|---|---|
|`backend/app/application/recommendation/outfit_assistant_service.py`|Modified|
|`backend/app/application/recommendation/homepage_recommendation_service.py`|Modified|
|`backend/app/application/recommendation/failure_diagnostics.py`|Added|
|`backend/app/application/nlp/config/vocabulary.v1.json`|Modified pre-existing untracked source|
|`backend/app/api/account_routes.py`|Modified|
|`backend/app/application/account/account_service.py`|Modified|
|`backend/app/domain/value_objects/requests.py`|Modified|
|`backend/app/application/wardrobe/wardrobe_service.py`|Modified|
|`backend/app/api/wardrobe_routes.py`|Modified|
|`frontend/app/auth/page.tsx`|Modified|
|`frontend/app/profile/page.tsx`|Modified|
|`frontend/app/wardrobe/page.tsx`|Modified|
|`frontend/lib/api.ts`|Modified|

Some recommendation sources and the guard were already untracked at capture;
“modified” above describes the captured source transition, not a claim that every
file is tracked in HEAD. No previously untracked implementation is discarded.

## Production failure logging

Previously the Assistant/Homepage broad exception handlers returned controlled
outcomes without production diagnostic context. They now emit JSON through the
ordinary `app.recommendation.failure` logger. The fixed event schema includes
UTC timestamp, generated diagnostic ID, operation, stage, existing outcome,
static reason/error kind and at most six application-relative source locations.
It works with an ordinary message formatter and also supplies structured extra.

The logger never serializes exception messages, arguments, chains, locals,
custom exception class names, absolute paths, user/account IDs, submission keys,
request text, wardrobe/preferences or credentials. There is no `exc_info` or
`stack_info`. Supported built-in error kinds and fixed operation/stage/outcome
values are allowlisted. Normal success, replay and controlled no-result/unsupported
responses do not emit failure events. A failure already converted by NLP/ranking
to a technical status logs its stage/status; its swallowed original exception is
not reconstructed. This gives a troubleshooting boundary without expanding
production catch sites into NLP/scoring modules.

Existing HTTP/body/status mappings, policy selection, transaction checkpoints,
rollback and same-key recovery are unchanged. A logging handler failure cannot
replace the existing business outcome. Production sink access, retention and
delivery during a sink outage remain deployment responsibilities.

New checks inject credential, secret, private email/request/wardrobe and key
sentinels into actual chained exceptions. They inspect emitted JSON and complete
captured log text, a plain formatter, hostile exception names/string conversion
and a failing log handler. Actual authenticated API calls retain generic503
responses and no writes. Real repository checkpoint failures roll back and allow
same-key success/replay. They also exercise internally controlled NLP/ranking
technical statuses. No test-only observer replaces production logging.

## Registration and account contract

The form now collects **Full name, Email, Password and Confirm password**. Full
name uses the existing `display_name` storage column; no new identity schema is
introduced. Names trim surrounding whitespace, contain 1–100 characters and
exclude control characters. Registration requires matching 12–256-character
passwords at the server as well as the normal browser check.

The prototype email format is explicitly ASCII dot-atom local syntax (1–64
characters) and DNS-style domain labels with a dot, total length at most254.
Whitespace is trimmed and case normalized; invalid dots/labels/spaces are rejected
before insertion. This is syntax validation, not mailbox ownership verification
or support for every international/quoted email syntax. Password hashing precedes
the short `BEGIN IMMEDIATE` duplicate-check/insert transaction. Competing equal
email registrations produce one201 and one409, with one new account.

Registration now returns `Registered`, a success message and the public profile;
it **does not issue an access token**. The UI clears password/confirmation and
shows the login form at `/auth`, retaining email for sign-in. Login then uses the
existing authentication implementation and redirects to Homepage. Wrong password
and unknown email both return the existing general401 message; the frontend now
shows that login message instead of describing it as an expired session.

This deliberately changes old registration callers: they must send
`password_confirmation` and subsequently log in to obtain a bearer token. Current
production has one helper caller, the auth form. Preserved old phase scripts and
frozen J-15 collection remain historical tools for their original source state;
they were not rewritten or silently rerun against this new contract. External
callers need the contract notice before release. Logout revocation stays excluded.

## Controlled preferences and preservation

The normal Profile page now exposes colours, styles, garment categories/groups
and existing supported formality preferences, each with importance0–1 and its own
Save, Clear selection and Cancel controls. Choices come from an authenticated
options route using the existing vocabulary and suitability policy. Importance0
remains ignored by the existing scorer; it does not bypass write validation.
Casual and smart_casual are the existing formality choices; no capability expands.

The write boundary uses the existing `PreferenceNormalizer` to reject unsupported
types, malformed values, unsupported style prose, invalid categories and unavailable
formal preferences. Supported aliases are persisted canonically. Supplied weights
must be finite, non-boolean and within0–1. The scorer and its60/20/20 policy are
unchanged. Actual saved colour/style/category values are read through the normal
preference adapter and affect the existing preference component; historical keyed
results retain their original score metadata and preference snapshot.

Saving `{values:[]}` explicitly deactivates active rows only for that owner/type;
it retains their original payload. It never stores active empty evidence. Each
group saves independently, so there is no implied all-groups transaction. Clear
selection changes the draft until Save; it can also remove unsupported historical
choices without automatically rewriting storage. Earlier style notes remain visible
and unchanged. Structured styles retain their existing precedence over recognised
whole-style notes; arbitrary prose does not become inferred preference evidence.

Final review also reproduced a response race in the old upsert projection: a
second SQLite connection could clear the preference after commit but before
`list_preferences` re-read it, causing StopIteration/500 for a successful save.
The response now projects its own written row under the transaction lock and
returns that acknowledgement after commit. A real independent-connection test
clears immediately after commit; the save still returns200 with its committed
values and the later clear remains effective. This changes no scorer semantics
and does not undo a competing update. The failing pre-correction test
and subsequent complete regression remain preserved.

Cancel restores the last saved values without a write. Failed network saves keep
the draft visible and leave stored values unchanged. Backend trigger-injected
profile/preference failures independently verify transaction rollback; browser
network-abort checks verify the UI preservation behavior. Separate owner tokens
see/update their own profile/preferences only. Unrelated settings and earlier
recommendations are preserved.

## Wardrobe listing filters and NLP correction

Listing adds `colour`, `style` and `availability`. Colour is an exact
case-insensitive stored primary-colour label; style is an exact case-insensitive
stored style label. An authoritative empty style list stays empty rather than
being promoted from a conflicting attribute mirror. No approximate hex matching,
colour inference, new extraction or suitability evidence is introduced.

Default `available` listing remains unchanged. `archived` selects archived rows;
`unavailable` selects other/null non-archived statuses; `all` shows all stored
owner rows. Non-available cards are read-only, with disabled outfit selection,
favourite/edit/archive actions. No restore/recovery workflow is invented. Query,
category, favourite and sort remain composable; SQL values remain parameterized.
The manual-outfit source still loads the ordinary available list. Quota remains
an independent unfiltered100-active-entry projection. API and browser checks
verify filtered results do not alter rows/counts or recommendation eligibility.

The vocabulary change is exactly one additional alias, **classic outfit**, under
the existing classic style. The v1 schema version remains1.0.0; the new source
hash transition identifies this approved revision, so version text alone must not
be treated as identical vocabulary bytes. New actual HTTP/browser corrections
select a confirmed classic dress. Existing negation, weather and unrelated intent
boundaries remain UnsupportedRequest. J-15 S07/S15 failed responses and labels
remain unchanged; these new passes do not relabel J-15 as152/152.

## Outstanding dependencies and minimum final verification scope

`dependency-evidence-presence.json` checks the same nine named teammate bundles
and their two local path alternatives. Missing local files remain missing
evidence, not proof that teammate tests never ran. Request transfer/inspection
of existing lawful raw inputs/outputs, model/config/weight hashes, known failures
and source journeys before proposing fresh model tests. No messages were sent
to teammates and no new model/dataset acquisition or inference was run.

| Dependency / classification | Owner and minimum action |
|---|---|
|Segmentation/CV, VTOFF and real VTON raw bundles: evidence unavailable here|T transfers existing segmentation, held-out, standardisation/smoke and reconstruction evidence; inspect only missing authorised coverage after transfer.|
|VTON scope: capability/scope decision|T/supervisor accepts existing11 top/bottom/dress classes and sequential journeys, or separately designs missing support. Outerwear remains wholly unavailable for VIS.|
|SQLite versus PostgreSQL/pgvector: architecture decision/conditional implementation|Supervisor accepts documented SQLite prototype deviation or separately approves genuine shared adapter, schema mapping, migration and locking work. Compose/DDL is not a live app adapter.|
|RN-13: original capability Partial|Supervisor accepts bounded8 occasions/2 formalities/named-anchor colour scope or separately approves missing policies/evidence. Exercise/formal/general hex remain unfulfilled.|
|FR-ACC-15: actual functional gap, excluded|Shared auth/storage owner agrees durable session invalidation design; no schema migration or token redesign was authorised here.|
|Formal NFR-01/02/03: acceptance decisions|Adopt precise baseline/history maximum/image/resource scope and decide whether retained J-16 observations suffice. NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.|
|Deployment/data/operations: missing proof|Deployment/T owners approve actual launcher, source packaging, secret/DB retention, TLS, real quota/status inventory and recovery; preserve unusual/over-limit rows. CORS PUT/If-Match and installed/multi-worker drain remain separate.|
|NFR-16/17/18/19 and canonical architecture: evidence/layout gaps|Reuse existing evidence if available; otherwise focused360–1920 viewport, keyboard,200% zoom and actual three-browser checks; reconcile ai-services ownership/layout without deleting it or weakening the known assertion.|

The smallest final verification round is the approved deployment/scope delta:
obtain existing model evidence and the SQLite/RN-13/VTON/NFR decisions first;
verify affected account/profile/filter/logging paths alongside ordinary
recommendation/history/owner/quota behavior; perform the missing compatibility/
accessibility/TLS and bounded lifecycle checks only for the chosen release
topology. Durable logout needs its separate approved implementation/design.
Reuse unchanged score/capacity/NFR evidence. Do not start another recommendation
architecture, capacity reduction, full performance matrix or J-19 automatically.

## Final verification, traceability and disposition

| Check | Actual result |
|---|---|
|Focused backend regressions|**521 passed in110.52s**, native child exit0: new closure/logging tests, two adapted callers, confirmation/quota, owner isolation, styles, startup, J-14 routing, preferences/ranking, atomic history/replay, Homepage/Assistant and compact frozen-source checks.|
|New targeted coverage within that521|44 functional-closure cases and30 logging cases; earlier25 logging,43 closure and520 regression passes overlap, not additional distinct coverage.|
|Additional original source-set/reference guards|**4 passed in311.98s** across completed2A/2B/2D1 and Assistant frozen transitive sources; original ZIPs/manifests unchanged. Final direct transition audit and the final521-test compact guard verify the final bytes after the UI/type and preference-acknowledgement corrections.|
|Final production browser|**3 passed in17.3s**, actual app.main/Uvicorn, production Next and real register/login; registration/profile, filters and normal Assistant/history journeys.|
|Production build|Final build passed: `o2aRZKY_67KAiMV7I1qqh`. Separate initial/final directories preserve both builds. The final process ledger records the actual build ID.|
|TypeScript / scoped ESLint|Passed on final auth/profile/wardrobe/helper and new browser/config sources. Production build also completed its TypeScript step.|
|Integrity|All2,830 starting paths present: **2,815 unchanged, exactly15 approved existing-file changes** (12 production, two caller tests, one guard). All42 accepted J-17 indexed deliverables and all226 final frozen source/build entries unchanged. One production helper added, with exact addition hash.|
|Whitespace / syntax|`git diff --check`, explicit added-file whitespace checks and Python AST checks passed. Next-generated tsconfig/next-env were retained as generated copies and restored to their captured original bytes.|

The two new backend modules inject actual service/repository/API failures and
exercise the shared workflow. The four extra source guards test the newly extended
transition mechanism, not another performance study. No NFR timing collector or
new capacity population ran. Account writes/listing are outside J-16's timed
generation boundaries; success-path scoring/enumeration and policies remain
byte-identical, and failure logging only executes on failure. The one approved
phrase alias does not justify repeating J-16's completed matrix. Its original
measurements remain qualified historical evidence, not newly measured guarantees.

All new attempts remain in the J-18 evidence directory. Initial logging tests
had three fixture expectations wrong: persistence used unsupported private prose
before the intended checkpoint, and the checkpoint is named `item`, not `items`.
They were corrected in the new tests; the initial3-failed/20-passed log remains.
The corrected25-case run passed, then technical-status coverage expanded the
module to30 cases. The first closure run imported `release` without registering
its `lifecycle` fixture:40 setup errors and34 passes across that invocation;
importing the existing fixture resolved the setup errors. The43-case run then
passed and all were included in the initial520 regressions. No production/original
oracle was changed to resolve these test setup issues.

Browser `initial` retained two successful journeys and a registration locator
timeout: its exact Password label ignored existing help text. `locator-corrected`
then retained two successes and a strict locator error because Next's route
announcer also has role alert. Narrowing the new test to its actual message
paragraph resolved that ambiguity. `scoped-locator` passed all three journeys.
Final review added Clear selection for historical unsupported draft choices and
an accurate TypeScript union for the clear response; `verified` exercised all
three journeys again, including clear/save, against the separate final build and
a fresh disposable database. The reproduced preference response race then justified
its narrow account-service correction, a new44th closure case and the final521-test
backend run. `final` passes all three browser journeys again on that final backend
state and unchanged final frontend build. Earlier passes are not added to its
three passes.
The first two traces and all partial logs remain; no timeout/deadline was extended
to convert a failed test into a pass.

Retained warnings include the existing Starlette/httpx deprecation, Playwright
NO_COLOR/FORCE_COLOR warning and uv's no-project warning. PowerShell redirection
records the latter as NativeCommandError and can report a nonzero shell status
despite completed passing child work; raw logs retain both. The final check
driver records actual child return codes separately, and browser ledgers record
exit0 for successful Playwright and normal backend shutdown. No warning is
presented as an application failure or silently removed.

All five browser-attempt backends log complete normal shutdown/exit0; all owned
frontends stop and ports3100/3101 are free afterward. No unrelated process was
stopped. This supplies additional small functional-cycle evidence; **it does not
diagnose or erase J-16's larger-run shutdown timeout**, establish in-flight drain,
forced-termination recovery, multi-worker capacity or an installed service.
Synthetic temporary databases remain at each ledger's paths for audit. No real
account, photo, deployed setting or historical evaluation was used or changed.

`recommendation_failure_logging_sources.v1.json` pins exactly two service
replacements and the new helper. `functional_closure_sources.v1.json` pins exactly
the ten approved shared/vocabulary replacements. The prior source-transition
chain is followed, not repinned. `phase-existing-files.patch` and before copies
identify J-18 within the earlier uncommitted workspace. No commit/reset/staging
or packaging approval is inferred. All old source manifests, scoring/suitability
policies, fixed labels, failed evaluations and earlier raw reports retain bytes.

`requirement-matrix.json` and its CSV preserve all155 original sentences/pages
and show each J-17 status alongside the new status. **15 rows advance**: nine
Partial and six Unverified become Verified. The counts are traceability statuses
for bounded local functionality, not a universal accuracy/FYP acceptance rate.

| Family | Total | Verified | Partial | Unverified | Blocked |
|---|---:|---:|---:|---:|---:|
|RN|30|29|1|0|0|
|FR-HR|12|12|0|0|0|
|FR-OA|12|12|0|0|0|
|FR-CH|16|16|0|0|0|
|FR-DW|20|16|0|4|0|
|FR-VIS|16|14|1|1|0|
|FR-ACC|15|14|1|0|0|
|FR-PP|9|9|0|0|0|
|NFR|25|17|0|8|0|
|**All original requirements**|**155**|**139**|**3**|**13**|**0**|

Still Partial: **RN-13, FR-VIS-01 and FR-ACC-15**. Still Unverified:
FR-DW-03/04/06/07, FR-VIS-09 and NFR-01/02/03/11/16/17/18/19. The RN/Homepage/
Assistant/chat70-row ownership slice remains69 Verified/1 Partial; logging is
in the shared NFR slice. No RN-13 scope acceptance or real-model proof is invented.

**PASS WITH LIMITATIONS.** The authorised functional corrections are implemented
and verified. The explicitly configured recommendation workflow remains READY
WITH LIMITATIONS; **whole-FYP acceptance remains NOT READY** pending the named
functional/scope, model-evidence, formal NFR and deployment decisions. Global
feature flags/defaults,100-garment quota, confirmed query eligibility, archive
semantics, provider/schema, CV/VTON and historical data remain unchanged.
**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** J-18 is complete for owner review;
no deployment, automatic remeasurement or J-19 begins. Wait for review.
