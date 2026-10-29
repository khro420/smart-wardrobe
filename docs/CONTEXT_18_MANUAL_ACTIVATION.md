# Eighteen-context Assistant: local activation and owner UAT

2026-10-28, Asia/Kuala_Lumpur. **ACTIVATED; ready for owner manual testing.**

The owner accepted [Waves A–D](CONTEXT_18_EXPANSION_IMPLEMENTATION_AND_VERIFICATION.md)
as PASS WITH LIMITATIONS and requested activation using the existing manual application.
The source-compatible correction described below was separately approved and verified.
The owner then answered **“Approve this exact 18-context restart.”** The approved
operation completed once, successfully. The manual services now run with
`context_18_v1`. **Do not start another copy.**

Section 4 of the owner's attached activation request expressly required approval of
the exact operation before either service stopped. The correction and restart have
separate retained approval records. No private account was signed into and no private
wardrobe, preference, chat or image contents were inspected.

## 1. Current identities and readiness

Before restart, fresh inspection verified actual GetProcessTimes creation identities, launcher records,
port ownership and listener ancestry, including the backend's intermediate Python shim.
These were the approved operation's starting identities, not permanent stop targets.

|Role|PID|Creation UTC|Creation FILETIME|
|---|---|---|---|
|Backend launch parent, uv.exe|28700|2026-10-27 15:33:32.2848050|134375888122848050|
|Backend Python shim|86332|2026-10-27 15:33:35.9346990|134375888159346993|
|Backend listener, 127.0.0.1:8000|90644|2026-10-27 15:33:35.9632300|134375888159632303|
|Frontend launch parent, node.exe|13376|2026-10-27 15:33:32.5939900|134375888125939903|
|Frontend listener, ::1:3000|16888|2026-10-27 15:33:33.0600270|134375888130600272|

Only launch parents **28700 and 13376** were stopped, through the existing checked
helper and dedicated consoles. Both stopped with ordinary Ctrl+C and native exit 0.
Fresh replacement identities are:

|Role|PID|Creation UTC|Creation FILETIME|
|---|---|---|---|
|Backend launch parent, uv.exe|26852|2026-10-27 20:11:23.6044130|134376054836044130|
|Backend Python shim|2480|2026-10-27 20:11:26.7587850|134376054867587854|
|Backend listener, 127.0.0.1:8000|7688|2026-10-27 20:11:26.7928560|134376054867928563|
|Frontend launch parent, node.exe|14416|2026-10-27 20:11:23.9128360|134376054839128368|
|Frontend listener, ::1:3000|24392|2026-10-27 20:11:24.5108740|134376054845108749|

New creation identities match updated launcher records; bounded ancestry binds the
listeners to their parents. These observations are not future permanent stop targets.

Backend health **http://127.0.0.1:8000/health** and sign-in
**http://localhost:3000/auth** return HTTP 200. Protected garments/capabilities return
401 through both backend and normal same-origin frontend proxy. Authentication is
required; no private login or bearer fabrication is used for verification.
Website **http://localhost:3000** and `/assistant` also return HTTP 200.

The old process had the seven accepted A1 feature selections; the eighth bundle
override was absent. The fresh backend and frontend children now have all eight
selections, including `context_18_v1`. Public API version alone was not used as
an implementation currency check.

The read-only startup gate passes: required schema objects, columns, indexes,
triggers and migration metadata match current startup requirements constructed
only in memory. **All four aggregate target counts are zero**:

|Startup effect|Targets|
|---|---|
|Legacy garment backfill|0|
|Legacy visualisation backfill|0|
|Queued/processing garment recovery|0|
|Queued/processing visualisation recovery|0|

The private connection uses `mode=ro`, `query_only=ON`, immediate busy failure and
a short consistent read transaction. No sidecar is present. Same-connection
data-version and DB/media-directory/secret-file size/mtime stay equal during each
observed gate. This is schema/aggregate/metadata evidence, not inspection of private
contents or a guarantee against a subsequent in-flight save. Finish uploads, saves
and other manual writes before the approved operation. Any nonzero target or schema
requirement aborts; no repair, migration, backfill or recovery is authorised.

## 2. Preserved configuration and actual factory

The approved start supplied these eight **process-only** selections, confirmed on
both new listener processes:

|Variable|Value|
|---|---|
|`SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE`|`general_context_v1`|
|`SMART_WARDROBE_ASSISTANT_ENABLED`|`true`|
|`SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED`|`true`|
|`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`|`compact_exhaustive`|
|`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`|`experimental_compatibility_decision_v1`|
|`SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE`|`context_relevance_decision_v1`|
|`SMART_WARDROBE_HOMEPAGE_ENABLED`|`true`|
|**New:** `SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE`|**`context_18_v1`**|

The baseline score setting deliberately remains: relative, fallback, generic and
specialist dispatch keep their distinct accepted meanings. The actual
`configure_local_workflow()` / execution factory constructs `OutfitAssistantService`
and `CompactAssistantScorer`, implementation `compact-context-relevance-1.0.0`.
The immutable bundle validator and capability compiler establish:

|Boundary|Verified disposable factory selection|
|---|---|
|Bundle|`context_18_v1` / `context-expansion-bundle-1.0.0`|
|Registry|`context-registry-2.0.0`|
|Grammar / taxonomy|`context-grammar-2.0.0` / `situation-taxonomy-2.0.0`|
|Relative policy / objectives|`context-relevance-policy-1.1.0` / `context-relevance-objectives-1.1.0`|
|Capability|18 active bindings: 15 ordinary relative contexts and three original strict specialists|
|Recognised taxonomy|23 IDs, including five unavailable situations|
|Display|`assistant-scoring-display-2.1.0`, with retained old readers|

All fifteen ordinary canonical requests and six exact compound phrases resolve in
the probe. Specialist binding objects equal their accepted originals; a generic
request has no contextual requirement. This uses disposable paths/random secret and
no database request. Fresh disposable APIs and Chrome execute the real app/factory,
ranker, proxy and exact display. These are operational readiness checks, not private
authenticated capability observations or independent fashion evaluation.

After restart, the actual factory/immutable-validator probe was repeated with the
same eight selections verified on the new children: native exit 0, 18/15/3/5 counts
and all required versions pass. Live protected capability access remains 401 without
authentication. Accepted sources, fresh process selection, actual factory execution
and authenticated disposable app execution provide bounded activation evidence;
the owner's normal authenticated capabilities/result view remains a manual observation.

Existing retained paths are:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024
  data\smart_wardrobe.db
  data\media
  token-secret.txt
```

Selective process inspection records only an explicit allowlist. Nonfeature data,
AI/model/device, security and proxy selections are preserved separately for backend
and frontend; absent overrides remain absent. Development identity stays off in the
manual backend. The secret is neither opened nor copied into evidence; the existing
launcher reuses it internally. No global environment or launcher/settings file changes.
Frontend remains the existing Next development/webpack process and retained
`.next-integration-run/manual-j22-dev-20261024` cache, proxied to 127.0.0.1:8000.

## 3. Separately approved compatibility correction

Readiness reproduced two regressions in the accepted expanded matcher:
**“I'm meeting friends for dinner.”** and **“I'm meeting friends.”** were supported by
the legacy interpreter but incorrectly returned clarification under the expanded
bundle. Generic workplace `meeting` shadowed the friends expression; the dinner
companion refinement was missing. This was an actual source defect, not a private
wardrobe finding or permission to change ranking policy.

The owner answered **“Approve this exact compatibility correction”** to the precise
[correction proposal](CONTEXT_18_ACTIVATION_CORRECTION_PROPOSAL.md), under section 10
of the attached request. The exact reviewed patch changes only
`backend/app/application/nlp/context_expression_matcher.py`: contained friends meaning
refines generic meeting, and the licensed friends-for-dinner relation retains the meal.
Current matcher SHA256 is
`02f5d4c928ff5c4b5176867469343aa2312b861c262cd698e9dd30d3c5e6a264`.

Verification changes are exactly `backend/tests/test_context_expansion_nlp.py`,
`backend/tests/test_context_expansion_integration.py`,
`backend/tests/integration_source_guard.py`, plus new
`backend/tests/fixtures/context_18_activation_correction_sources.v1.json`.
The new descendant manifest certifies exact before/after copies; the original
expansion manifest, eighty frozen language labels, policy resources, source contracts
and historical reports retain bytes. The original integration loop now checks the
five old requests alongside the ten new requests with its exact existing assertions.
New controls retain generic-workplace, unrelated-event, negative, venue and code gates.

Of the original **32 accepted production sources, 31 remain byte-identical and one
has this explicitly approved correction**. All current hashes match the prepared
source confirmation. No formula, objective, frozen oracle, admission rule, database
schema, frontend production source or model changed. The new manual backend starts
from these exact corrected sources.

## 4. Exact approved stop/start operation

The owner approved the exact prepared operation. The guarded script performed the
following **once**:

1. Recheck current launcher records, all five creation identities/ancestry, allowlisted
   selections, unchanged launcher/settings files, current 32 production inputs and
   correction/source-guard/label hashes. Repeat the read-only startup gate.
2. Run existing `stop.ps1` → creation-time-checked `stop.py`, sending ordinary Ctrl+C
   only to dedicated frontend parent **13376** and backend parent **28700**. Their
   listeners are **16888** and **90644**, with backend shim **86332**. No force kill.
3. Confirm 3000/8000 are free; repeat the startup gate; run existing `start.ps1` once
   with all eight selections and preserved nonfeature child configuration.
4. Verify new parent/listener identities and ancestry, all eight child selections,
   public health/auth/root/proxy, served exact-display markers, current source hashes,
   root generated-file bytes and another read-only aggregate gate. Repeat focused
   write smoke only on disposable data. Leave manual services running.

Any changed identity, occupied port, nonzero gate, failed clean stop or failed start
aborts without forced termination, repair or silent retry. Expected runtime effects
are log append, `last-stop.json` / `processes.json` updates, normal existing startup
validation transactions and Next development cache/type metadata. No cache deletion,
secret rotation, global default change or extra app instance is included.

Both immediately-before-stop and immediately-before-start gates passed with all four
counts zero. `stop.ps1` and `start.ps1` each returned native exit 0; health readiness
passed. No forced manual termination or retry occurred. The post-start gate also
passes with all counts zero. Startup still executes its existing validation/recovery
statements; no migration, backfill/recovery target change or record repair was applied.

Observed effects include log append, launcher process/stop-record updates, normal
existing startup schema-validation transactions and Next development cache activity.
DB/media-directory/secret size/mtime remain equal across the observed restart;
`tsconfig.json`, `next-env.d.ts` and `AGENTS.md` retain before bytes. This is bounded
metadata continuity, not a private-row audit. All 32 current production inputs and
seven launcher/settings hashes still match; nonfeature AI/security/proxy/path
selections are preserved. The guarded script records completed health readiness and
refuses another attempted operation. Do not reuse it for a future restart.

Served frontend JavaScript contains `assistant-scoring-display-2.1.0`, the retained
2.0.0 reader, full R/C/P and context ranking labels, `baseline_disclosed_v1`, expanded
capability/context-explanation markers and strict-specialist wording. Exact rendering
was exercised in disposable Chrome, not in the private account.

## 5. Disposable verification and retained attempts

After the approved correction, before this restart:

- Focused backend: **279 passed in 105.36s**, native exit 0. All five expansion modules,
  original frozen language cases, preservation controls and source-chain certification.
- Focused activation APIs: **five passed in 25.06s**, native exit 0. Fifteen ordinary
  requests, six compound phrases, generic dispatch, exact components, unchanged
  garments, preference effects, replay/history and requested negative controls.
- Actual Chrome / production Next: **10/10 passed in 1.6m**, Playwright and harness
  native exit 0. The retained nine journeys plus a new external preservation journey
  cover the original five requests, standalone friends and exact six compounds.
  Every backend shuts down normally with exit 0. The harness explicitly terminates
  its owned Next process with exit 1; this is not graceful installed-service recovery.
  No automatic retries or deadline increases were used. Verification ports are free.
  Canonical-dinner and native-200%-zoom captures were inspected; the visible result
  preserves dinner/friends, exact component terms, provisional source and tie disclosure.

After restart, the actual factory/immutable-validator probe passed with native exit
0 and matching verified child selections. The focused disposable API smoke repeated:
**five passed in 34.79s**, native exit 0, covering all fifteen ordinary requests, exact
compounds, generic dispatch, history/replay, preferences and negative controls. These
overlap pre-start checks and are not an additional independent evaluation. No post-start
browser or broad regression invocation is claimed. All automated writes remain
disposable; the manual private account was not used.

These overlap the accepted implementation tests. They are focused verification, not
a new whole-system regression, independent NLP/fashion evaluation or NFR benchmark.
The unchanged accepted production frontend build **J2J5xgB9_QsntW_s_6zy7** is reused
with its verified production inputs. Browser accounts, tokens, images, preferences
and database are disposable on owned 3100/3101 outside OneDrive. Processing is an
explicit synthetic port fixture; no real CV/VTOFF/VTON result is claimed. Browser
development identity is off, with ordinary registration/login. Controlled API test
identities are confined to disposable fixtures.

Before correction, the factory probe exited 1 for the reproduced compatibility defect.
The first mixed API/NLP arm retained **86 pass / two fail**, native exit 1: the dinner
regression and an external smoke assertion that incorrectly equated an exhaustive
no-result's `complete` field with success. The latter helper now asserts outcome and
selected structure; no application contract was weakened. A negative-only arm passed
four with the known positive regression deselected, not relabelled as passed.
The earlier nine-browser arm passed but did not submit the exact original dinner
phrase; it did not establish preservation of that request. The new preservation
journey closes that gap. Original attempts, logs, patches and helpers remain identified.
The latest top-level API observation files describe the corrected rerun; earlier native
failure logs and helper originals retain their separate evidence.

## 6. Owner manual UAT after activation

Open **http://localhost:3000/auth**, sign in
yourself and confirm the wardrobe you recognise. Use **New Chat** for each request.
Do not review, relabel, re-upload, tag occasions or set up preference profiles merely
to enable otherwise eligible existing garments.

|Request|Expected interpretation / automatic goal|
|---|---|
|I'm going to study at the library.|Library study / casual|
|I have a group project meeting at university.|Academic group study / casual|
|I need to go to the office tomorrow.|Office day; tomorrow retained / smart casual|
|I have a meeting with my colleagues.|Workplace meeting; colleagues retained / smart casual|
|I'm attending a birthday party.|Birthday gathering / casual|
|I'm visiting my friend's house.|House gathering / casual|
|I'm going to watch a movie.|Cinema outing / casual|
|I'm meeting someone at a café.|Social café meetup / casual|
|I'm sightseeing around the city.|City sightseeing / casual|
|I'm taking a train for a trip.|Ordinary transit; train facet retained / casual|

Also try the exact compound/preservation checks:

- `I'm going on a dinner date.`: date plus dinner facet, both mandatory gates,
  one smart-casual goal.
- `I'm attending a birthday dinner.`: dinner plus birthday facet, both gates,
  one dinner smart-casual goal.
- `I'm going on a date at a café.`: date with café venue, smart casual.
- `I'm going to class at university.`: class with venue, casual.
- `I'm having dinner with my family.`: dinner with family, smart casual.
- `I'm hanging out with friends.`: casual outing, casual.
- Original shopping/class/friends-outing/date/dinner requests: three casual and two
  smart-casual goals. In particular test `I'm meeting friends for dinner.` again.
- `Suggest an outfit`: generic legacy scoring, no contextual bundle requirement.

Expect a complete eligible outfit with names/images, exact R/C/P raw states and
decision contributions, 3/5 / 1/5 / 1/5 weights/terms, total, interpreted details,
objective/source authority, tie basis and conspicuous fallback/coverage notes.
Relative R is recorded-style alignment, not a fashion-confidence probability.
Unknown raw C is distinct from its conventional decision contribution. A fallback
must identify its actual legacy profile; limited coverage must not claim a global
optimum. Known R=0 is explained without pretending the soft target was matched.

The no-preference synthetic equivalent selects Blue T-shirt/Blue Jeans for casual
goals and Navy Dress/Grey Jacket for smart-casual goals. **Actual private winners are
not guaranteed**: saved facts, restrictions, joins and preferences were not inspected.
Equivalent goals may share winners. Existing strict wedding guest, university
presentation and employment interview evidence requirements remain; missing facts
can correctly prevent a result. Unsupported formal/specialist meaning, ambiguous
project meetings, contradictions and unrelated occasions must remain controlled
outcomes, not permissive generic substitutions.

Record the request, visible interpretation/objective/profile, outcome/components,
whether explanations are understood and any usability issue. Do not change real
restrictions or availability to manufacture failures. Account-specific investigation
would need separately named minimal read-only authority; no private repair is approved.

## 7. Future safe stop/start boundary

Do not execute another start while services run. This document does not authorise a
future stop. A later authorised clean stop uses the retained identity-checking helper:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
& (Join-Path $manualRuntime 'stop.ps1')
```

A future separately approved start needs current identities, free ports, completed
manual writes and a fresh zero-target gate. Preserve actual nonfeature settings and
use all eight process-only selections with existing `start.ps1`:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE = 'compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE = 'experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE = 'context_relevance_decision_v1'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE = 'context_18_v1'
& (Join-Path $manualRuntime 'start.ps1')
```

Do not use a bare Uvicorn command, historical PID, process-name kill, unrelated port
owner, auth bypass, cache/data deletion or unrelated terminal's AI/security overrides.
The prepared operation additionally preserves distinct inspected child selections;
a bare eight-flag snippet alone does not provide that preservation guarantee.

## 8. Evidence and disposition

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\context_18_activation_20261028
```

Starting hashes, runtime/configuration observations, schema gate, approval and exact
correction copies, original/final source confirmations, descendant manifest, factory,
API/browser native results and prepared operation are retained. No full environment
or secret is printed. The earlier correction proposal and pending integrity index
retain their original pre-approval state; this report records the subsequent approval.

Prepared integrity checks all **575 starting scoped paths**: 571 remain unchanged,
and exactly four have the authorised correction/test/support advances. The new
correction fixture and two new task reports are separate additions. All current
32 production hashes, seven launcher/settings hashes and three generated root files
match their prepared expectations. Staging is empty; scoped whitespace checks pass.
The guarded operation and its inputs are hashed before presenting restart approval.
Final integrity additionally confirms the retained prepared input hashes, exact
approval, successful single operation, all three zero-target operation gates,
after-start identities/configuration/public checks and post-start disposable results.
Prepared report/index copies retain their earlier pending state separately from this
completed report and final delivery index. Observed runtime logs/process records and
cache activity are distinct from source, launcher or private-content edits.

**Activation complete; owner's actual manual UAT results pending.** The approved
correction and the separately approved restart are complete. New manual services
remain running. No private account, garment, preference, history or image contents
were accessed. No migration, model change, global/launcher edit, staging, commit or
deployment occurred. No next policy increment or private-data transition begins here.

Independent human appropriateness, true model operation and formal NFR acceptance
remain OPEN. The original 155-row baseline stays **144 Verified / 2 Partial /
9 Unverified / 0 Blocked**; RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY
ACCEPTED; whole-FYP acceptance remains NOT READY.
