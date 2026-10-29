# Post-Phase-5 manual usability and integration readiness

2026-10-26, Asia/Kuala_Lumpur. **Review prepared; local launch awaits owner decision.**
Phase 5 is owner-accepted PASS WITH LIMITATIONS. This is startup/UAT preparation,
not a new implementation phase. No production, policy, launcher, private data or
global configuration was changed. No service, browser account, model inference,
regression suite or benchmark was started for this review.

**Current status: the application is not running on its intended local ports.**
The saved manual launcher omits the context profile. A fresh launch needs an explicit
process-only `general_context_v1` selection to expose the accepted contextual work.
The existing backend also executes database initialisation and recovery hooks at
startup; do not run the commands below until the decision in section 3 is approved.

**155-requirement baseline remains 144 Verified / 2 Partial / 9 Unverified / 0 Blocked.**
RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. Whole-FYP
acceptance remains NOT READY.

## 1. Current inspection findings

| Item | Actual current finding |
|---|---|
|Latest source|All **903 indexed Phase 5 deliverables match** their accepted hashes. Current grammar/taxonomy/registry are 1.3.0; eight approved context bindings are present.|
|Listening ports|No listeners found on 3000, 8000, 3100 or 3101. IPv4 loopback probes also find all four closed.|
|Application processes|No matching project Uvicorn/Next process found in the explicit process inspection. No process was stopped.|
|Website|Intended **http://localhost:3000**, sign-in **http://localhost:3000/auth**; not currently reachable because the frontend is stopped.|
|Backend|Intended **http://127.0.0.1:8000**; health **http://127.0.0.1:8000/health**; stopped.|
|Saved manual runtime|`C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024`|
|Actual configured DB|`C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\smart_wardrobe.db`; present. No replacement/test DB is selected.|
|Actual media root|`C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\media`; present. Photos/files were not opened.|
|Secret persistence|Existing `token-secret.txt` in that manual runtime is present. Its contents were not printed or included in review evidence; reuse that same file.|
|J-22 store|Read-only immutable schema inspection finds `revoked_access_tokens`, digest/owner/expiry/revocation-time columns, expiry index, primary-key index and users foreign key. No bearer hashes or other data rows were queried. This is not a fresh runtime logout test.|
|SQLite sidecars|No `-wal` or `-shm` file at inspection. DB/media/secret size/timestamps remain unchanged during the schema inspection.|
|Old saved status|`running-status.json` and `resolved-configuration.json` describe October 24, not current liveness, account counts or Phase 5 loading. Historical PIDs are not stop targets.|

Evidence: [inspection.json](../storage/verification/post_phase5_manual_uat_20261026/inspection.json),
dependency probe and review integrity index in the same directory. Schema access
used `mode=ro&immutable=1`; no account, garment, chat, recommendation or revocation
row contents were inspected. Existing accounts/garments/history are intentionally
not inventoried here. Old zero-count startup ledgers must not be treated as evidence
that the current private database is empty.

## 2. Correct feature selection, proxy and environment

These are the actual variable names consumed by current composition/selection:

| Variable | Required value | Saved manual settings |
|---|---|---|
|`SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE`|`general_context_v1`|**Missing**. Current inspection-process/User/Machine lookup also finds no profile override. Default is `disabled`.|
|`SMART_WARDROBE_ASSISTANT_ENABLED`|`true`|Correct.|
|`SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED`|`true`|Correct; required by the general context profile.|
|`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`|`compact_exhaustive`|Correct.|
|`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`|`experimental_compatibility_decision_v1`|Correct; exact 3/5, 1/5, 1/5.|
|`SMART_WARDROBE_HOMEPAGE_ENABLED`|`true`|Correct; still the separate random/no-chat Homepage workflow.|

The saved backend wrapper explicitly supplies the existing DB/data paths,
`SMART_WARDROBE_ALLOW_DEV_IDENTITY=false`, development environment and secret read
from the retained file. There is no authentication bypass to enable. A fresh VS Code
terminal may have its own session overrides; the table describes inspected settings
and this inspection process, not an unseen terminal's environment.

The frontend wrapper sets `NEXT_PUBLIC_API_URL=/api/v1` and
`SMART_WARDROBE_BACKEND_URL=http://127.0.0.1:8000`. `next.config.ts` rewrites
`/api/v1/:path*` to that backend. Use the frontend's same-origin API; do not replace
it with a direct browser-to-8000 URL or use verification ports 3100/3101. Default
browser CORS origins/headers are not expanded by this review.

The manual frontend uses `next dev --webpack`, with cache directory
`.next-integration-run/manual-j22-dev-20261024`. That old directory name does not
pin source to J-22: a fresh development process reads the current working tree.
No old production build is launched. Do not delete its cache or previous builds.

The inspected backend configuration/launcher does not automatically load a `.env`
file. Copying `.env.example` alone is not an effective substitute for these process
variables. Prefer the verified manual wrapper instead of bare `python` from an
unspecified Windows PATH/environment.

## 3. Launch boundary and exact decision required

Nothing currently needs to be stopped. **No restart/start was performed.** The
pending operation would create one Uvicorn worker and one Next development process
from the latest source, targeting the existing private DB/media/secret, with only
the requested process-level feature selection.

`app.main:lifespan` always calls:

1. `configure_local_workflow()`;
2. `initialise_database()`, which executes idempotent schema statements but can also
   apply missing columns/recommendation/auth migrations and legacy garment or
   visualisation backfills;
3. interrupted-job/visualisation recovery, which can mark queued/processing records
   failed.

Starting the server is therefore not a purely read-only action. The existence of
the revocation table does not prove that every startup branch would be a no-op.
This review did not run those functions, inspect backfill row contents, query pending
private jobs or grant private migration/recovery authority.

**Required decision:** approve a gated local launch on the **existing** manual DB,
media and secret. First permit a read-only startup-effects preflight using schema,
migration metadata and aggregate eligibility counts only. Start only if it finds
no missing schema/migration, legacy backfill or interrupted-record recovery changes
needed. If any are needed, stop and report them for a separate decision; do not
apply them, repair rows, substitute another DB or disable safeguards. Keep the six
requested flags process-only and retain existing AI modes. Alternatively choose
commands/checklist only and leave services stopped.

If approved and preflight succeeds, ordinary startup may open short write
transactions for existing schema validation, and normal manual use will persist
the user's own actions. This is not approval for a new schema/data migration.
Startup also appends runtime logs and writes Next development cache/generated type
metadata; it may regenerate frontend tsconfig/next-env/AGENTS entries. No application
logic or scoring/default change is proposed. These effects should be recorded during
the later launch, not silently attributed to this read-only review.

## 4. Exact Windows / VS Code commands after that decision

Use two PowerShell terminals. These reuse the actual existing wrappers and their
configured DB/media/secret; they do not create a synthetic runtime. **Do not run
them while the private-startup gate above is unresolved.**

Backend terminal:

```powershell
$manual = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE = 'compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE = 'experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
& (Join-Path $manual 'backend.ps1')
```

The wrapper loads the retained secret without displaying it, sets the saved data
paths and invokes this exact cached dependency/runtime command from `backend`:

```powershell
uv run --offline --no-project --python 3.12 `
  --with fastapi==0.146.0 --with uvicorn==0.54.0 `
  --with pillow==13.0.0 --with numpy==2.5.4 --with python-multipart==0.0.32 `
  python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

That expanded command is explanatory: **do not run it alone without the wrapper's
data/secret environment**. Do not add `--reload`, rotate the secret, drop tables or
run migration/cleanup/seeding scripts.

Frontend terminal:

```powershell
$manual = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
& (Join-Path $manual 'frontend.ps1')
```

It runs `npm.cmd run dev -- --hostname localhost --port 3000` from the current
`frontend` directory and sets the correct proxy/cache variables. After both are
ready, open **http://localhost:3000/auth**. Use your existing account; do not share
its password/token. Registration is optional if you personally want another account:
full name, email, 12–256-character password and matching confirmation; success
returns to sign-in rather than issuing a session automatically.

For a later approved background launch, set the same six variables then call
`& (Join-Path $manual 'start.ps1')` **instead of** the two terminal commands. It
inherits the missing context override, checks ports and records its own PIDs.
Do not run both methods. Running start.ps1 without the override still selects the
legacy profile. No launcher/settings edit is necessary for this process-only choice.

After a future approved launch, lightweight checks are:

- `/health` returns 200; `/auth` loads; unauthenticated frontend API requests
  requiring auth may return 401, which is not a login failure.
- Sign in yourself. In the normal capabilities response, confirm both feature
  booleans plus `context_support.version=context-registry-1.3.0` and the eight
  enabled binding definitions. The Assistant should display the new everyday examples.
- Do not dump browser storage, full environment variables, request headers or the
  secret file. No account creation/login or private write is performed by this review.

### Safe stop / restart later

For the two-terminal method, press **Ctrl+C in each owned terminal** and wait for
normal backend shutdown before starting it again. Preserve the data directory,
secret and revocation table; use the same commands/flags on restart. A non-reloading
backend must be restarted to load later Python changes, subject to the same gate.

For the background `start.ps1` method only, use
`& (Join-Path $manual 'stop.ps1')` after authorising that stop. Its helper checks
recorded PID creation identity and sends Ctrl+C; it does not force-kill reused or
unrelated PIDs. It does not manage processes started in the two VS Code terminals.
Do not run it now against historical records. If a future port is occupied, identify
its actual owner first; do not use `Stop-Process -Name node/python` or blanket port kills.

## 5. Dependency and AI availability

The **actual manual UV argument set**, inspected offline without app startup,
resolves Python **3.12.10** and FastAPI/Uvicorn/Pillow/NumPy/multipart. Torch,
torchvision, OpenCV, Ultralytics, Transformers, Diffusers, Accelerate and safetensors
are absent in that environment. Frontend Next entry point and the two declaration
files restored during Phase 5 are present. No dependency was installed/downloaded
or model/adapter instantiated for this review.

No AI-mode override is saved in the manual settings; current inspection-process,
User and Machine lookups show none for the checked mode flags. Thus the inspected
defaults are AI mode `production` and embedding/VTOFF/VTON `auto`, not a promise of
working real models. Do not force `AI_MODE=development` as an undocumented shortcut:
that also selects a development-copy VTON output, which is not garment try-on.

| Component | Readiness for this local manual environment |
|---|---|
|Accounts, Digital Wardrobe, preferences|Implemented; usable after approved startup/sign-in. Actual account contents, write access and garment inventory remain untested manually.|
|Assistant / Homepage / history|Implemented. Assistant needs the explicit general profile; actual results depend on eligible current wardrobe evidence. Homepage remains random/no-chat.|
|Garment detection/segmentation|Default `backend/models/cv/best.pt` is missing, and real CV dependencies are absent. Source selects the labelled development candidate when weights are absent. No trained segmentation/mask quality is established.|
|Attribute extraction / embedding|SigLIP weights/config and the Fashionpedia head are missing; real libraries are absent. Development attribute path reports embedding unavailable. It does not automatically provide trustworthy style/material/appearance facts.|
|VTOFF / standardisation|A VTOFF manifest is present, but required checkpoint, VAE and SigLIP assets are missing. Manifest presence is not readiness. The scheduler file's byte size also differs from its manifest entry; no large-file hash validation/inference was attempted. Real reconstruction is unavailable. The adapter can retain crop/original evidence for unsupported/low-confidence development input; this is not model-generated standardisation.|
|VTON visualisation|Default VTON manifest is missing; source selects UnavailableVTONAdapter in inspected production/auto mode. Save/source eligibility UI may be exercised separately, but no real try-on result is promised.|

The development garment adapter produces an unclassified, confidence-0,
review-required candidate, not a model prediction. Without a generated crop, the
processing orchestrator retains the uploaded source as crop evidence. User corrections
are still necessary before confirmation. Do not describe a development fallback as
real segmentation, learned attributes, a generated garment or independent fashion
validation. Deterministic image utilities being present does not certify real-model
or segmentation-dependent standardisation in this environment.

Do not download models, change AI modes, run setup_vton/verification/model scripts,
or upload private photos as an automated smoke test. Any teammate asset transfer,
GPU/dependency setup and real inference need their separate scope/permission.

## 6. Evidence categories and manual recording

Use these labels rather than turning every observation into an acceptance pass:

| Label | Meaning |
|---|---|
|A — automated baseline|Previously executed synthetic/disposable evidence. Phase 5: 1,878 passes plus separate source guard; 73/73 API labels; 21 general and 10 wedding Chrome executions with overlap. These were inspected, not rerun here.|
|B — fresh manual|How the real interface behaves for you after approved startup. **All checklist items below are Pending**, not newly passed.|
|C — actual data dependent|Existing accounts, current available/confirmed garments, saved style/evidence/declarations/preferences and complete structures. Not inventoried here.|
|D — teammate/model dependent|Real CV/attributes/VTOFF/VTON assets, configuration/dependencies, lawful inputs/outputs and independent evidence. Not supplied by A.|
|E — unsupported policy|Inactive or unrepresented context/code/goal. A controlled refusal is correct; do not relabel it as useful context suitability.|

For each manual check record request/action, expected context, visible outcome,
explanation understood yes/no, actual usability issue and time. You may record a
chat identifier locally for your own follow-up; do not paste credentials, tokens,
private images or complete private responses into the review. An optional screenshot
should be redacted. Separate a bug from truthful insufficient evidence and from
your subjective view of outfit appropriateness. NFR stopwatch acceptance is not
part of this checklist.

## 7. Account, wardrobe and preference checklist

All items are B/C; A supplies prior regression evidence. **Default observation is
read-only. Save/register/confirm/review/preferences/logout are real writes when you
choose them yourself; no such actions are performed by the assistant here.**

1. [ ] Open `/auth` after launch and sign in with an existing account. Expected:
   Homepage, no unexplained account replacement or empty-data reset. If missing
   data is suspected, stop and compare the configured path; do not register/reseed
   to mask a wrong DB. Older tokens may simply have expired (default TTL 12 hours).
2. [ ] Optionally register only if you want a real new account. Verify required
   confirmation and success-to-login; do not assume registration is a login.
3. [ ] Open My wardrobe. Compare a few items you recognise; use filters to understand
   status. Only current owned, available garments joined to confirmed processing
   items/jobs can enter Assistant selection. Listing filters do not restrict the
   Assistant's underlying eligible snapshot. The quota counts all non-archived
   entries, not only the currently visible/confirmed subset.
4. [ ] Open a garment's **Contextual recommendations** details. Compare its actual
   category/image/style; do not relabel a correct style to force a recommendation.
   If the singleton canonical style is true, optionally click **I reviewed the
   current style**. This saves immediately; there is no staged attestation Cancel.
   Reuse that review across supported contexts; per-event tags are optional.
5. [ ] If you choose to test editing, change a style draft in **Edit**, then **Cancel**.
   Reopen it and confirm saved values are intact. Saving a real style/category
   correction can invalidate dependent reviews; explicitly review the correct
   current value again when needed. Do not change all garments for UAT.
6. [ ] Inspect **Reusable appearance observations** and the
   [observation guide](APPEARANCE_OBSERVATION_REVIEW_GUIDE.md). Choose Unknown when
   uncertain. These additional observations are needed for bounded interviews,
   not ordinary campus/shopping/outings or every garment. A collar is not implied
   by long sleeves; tailoring/structure is an owner judgement, not a quality/fit rating.
7. [ ] If you choose, edit appearance drafts and use **Cancel appearance changes**:
   restore saved values without a write. Save only observations you actually made.
   **Withdraw appearance observations** is a real write removing those observations;
   it preserves style review/wedding choices. A dated clean/intact observation is
   not continuous verification of today's physical condition.
8. [ ] Open Profile. Check the four preference groups and importance values.
   Optionally change a draft and Cancel. If saving, expect each group to save
   independently and affect fresh scoring only, not rewrite historical results.
   Clear selection is a draft until Save. Do not store unsupported prose to test
   whether it will be guessed.

If a natural network/save failure occurs, preserve the visible error/draft and
avoid repeated uncertain submissions. Existing automated checks already inject
failure/rollback/lost-response cases. Do not stop a private server or cut a save
request deliberately just to reproduce them during normal-user UAT.

## 8. Request-by-request manual checklist

For every row click **New Chat** first. A successful completed request is read-only;
this is not a multi-turn conversation. No row guarantees a result from your actual
wardrobe. All need a complete supported structure and current eligibility. Every
selected member, including selected outerwear, must pass contextual conditions.
Exact applicable Deny wins; malformed required evidence blocks; clean scoped Allow
and approved reviewed inference remain distinct. A clean Allow cannot enable an
unsupported code or waive another required condition.

| Pending request / expected context | Role/code needed? | Evidence required and correct no-result / visible guidance |
|---|---|---|
|[ ] **I'm going to a wedding.** → wedding guest appearance|Guest convention is disclosed if role absent; no universal formal code inferred.|Unspecified-code W01 inference needs current reviewed smart casual, or applicable clean wedding permission; separately requested formality must pass. Missing/stale evidence can give InsufficientEvidence; restrictions can yield NoMatchingCandidates. Expect the guest assumption and invitation/footwear limits. B/C, A baseline.|
|[ ] **I'm going on a date tonight.** → date appearance|No role or dress code required; tonight is information only.|Current reviewed casual OR smart casual may infer for unspecified code; exact date declarations apply. Expect provisional appearance guideline, no venue/weather/comfort inference; missing review can correctly prevent a result. B/C.|
|[ ] **I'm meeting friends for dinner.** → dinner appearance|No role/code required; friends is stated metadata.|Same supported style sets within DN rules and exact dinner scope. Wedding/date permission is not dinner permission. Family-dinner wording is a separate unsupported case. B/C.|
|[ ] **I have a university presentation.** → academic presentation|**Role missing:** no automatic presenter/attendee.|Correct PolicyUnavailable with missing role, rather than ordinary campus fallback. Then optionally try **I'm presenting my project at university.** Explicit presenter + unspecified-code policy uses reviewed smart casual. Attendee unspecified-code policy permits reviewed casual/smart casual. Campus Deny vetoes; Campus Allow alone is insufficient. B/C.|
|[ ] **I have a job interview.** → employment interview|**Role and code missing.**|Correct PolicyUnavailable. A supported full example is **I'm being interviewed for a job; the dress code is smart casual.** It requires current reviewed smart casual, dated clean/intact observation and upper collar / lower tailoring / structured one-piece / structured OR tailored outerwear as applicable. Work Deny vetoes; Work Allow does not establish child evidence. Missing observations yield Unknown, not automatic professional suitability. B/C.|
|[ ] **I'm going to class.** → ordinary academic attendance|No role/code needed; ordinary academic class convention disclosed.|Current reviewed casual OR smart casual may infer, or clean exact campus Allow. No lab/PE/uniform support. Missing interview observations must not be demanded. B/C.|
|[ ] **I have university tomorrow.** → same campus policy|No student role/code inferred; tomorrow is information only.|Same evidence and campus Deny scope; no future availability/weather claim. Missing current review may correctly yield InsufficientEvidence. B/C.|
|[ ] **I'm going shopping.** → ordinary shopping|No role/code needed.|Reviewed casual OR smart casual, or exact clean shopping Allow; provisional appearance guideline visible. Unsupported shopping-related occupational/specialised requirements cannot be ignored. B/C.|
|[ ] **I'm going out with friends.** → ordinary casual outing|No role/code required; friends is not clothing evidence.|Same reviewed sets or exact casual_outing permission. No inferred restaurant, weather or dress code and no numeric friends bonus. B/C.|
|[ ] **Suggest an outfit for campus.** → same ordinary campus binding|No role/code added.|Must share the natural-language request's exact declaration scope; wording must not bypass campus Deny. New Chat creates a fresh key, so exact historical replay is not implied merely by similar wording. B/C.|
|[ ] **Suggest something blue for shopping.** → shopping plus hard blue|No role/code required.|Same shopping evidence; at least one member must satisfy the existing global blue constraint. It does not mean every garment is blue. Missing/unrecognised colour can block proof; known absence can give NoMatchingCandidates. No arbitrary-hex or colour-weather inference. B/C.|

For an explicit everyday **casual** or **smart-casual** code/formality, matching
reviewed style is required for inference and the separate formality condition must
pass. Occasion Allow alone cannot waive it. By contrast **Suggest a casual outfit**
without a situation follows the original formality/declaration path; **Suggest a
casual style outfit** is a style request. They are not currently interchangeable.

If selected, check actual wardrobe membership, complete structure, request conditions,
explicit/inferred basis, assumptions and usable actions. Record whether the result
feels appropriate separately; synthetic contract tests do not establish independent
fashion quality. If no result, check the named context/guidance before changing data.

## 9. Negative and unsupported checklist

Do not delete/archive real items or mass-change tags to manufacture failures.
Use an already-applicable condition, or explicitly choose an optional reversible
change to one item you own and record its original setting. A valid alternative
outfit may still exist; a Deny on one garment does not require global failure.

| Pending check | Correct expected behaviour |
|---|---|
|[ ] Missing/unreviewed/stale/uncovered required style|Unknown; InsufficientEvidence is valid if no complete proven candidate remains. Do not prompt users to relabel classic as casual just to get a result. Unrelated missing appearance observations do not block everyday contexts. B/C.|
|[ ] Applicable explicit Deny|Denied member excluded; another fully eligible outfit may be Selected. If no alternative exists, NoMatchingCandidates. Changing natural wording to a command must not bypass scope. B/C.|
|[ ] **I'm going shopping; the dress code is casual.** with only nonmatching evidence|Separate matching formality gate remains mandatory. Smart-casual-only inference does not establish casual; occasion Allow does not erase a formality Deny. Outcome depends on other eligible alternatives. B/C.|
|[ ] No complete supported structure / no combination meeting hard requirements|NoEligibleGarments, InsufficientStructure/NoStructuralCandidates, InsufficientEvidence or NoMatchingCandidates as appropriate. No invented member or partial outfit. Low compatibility score alone is not a newly imposed hard rejection threshold. B/C.|
|[ ] **I'm going shopping; the dress code is formal.**|PolicyUnavailable / unsupported_dress_code, even with owner Allow. Black tie likewise unavailable. E.|
|[ ] **I'm going hiking.**|Recognised, policy unavailable. No sportswear/safety/equipment assumption. E/D.|
|[ ] **I'm going to the beach.**|Recognised, policy unavailable. No invented swimming activity/UV or water protection. E/D.|
|[ ] **I'm attending a graduation as a guest.**|Recognised, policy unavailable. No wedding inheritance, regalia or institutional compliance claim. Some other graduation phrases still reject parsing. E.|
|[ ] **Suggest an outfit for travel.**|General-profile travel is recognised but inactive; older declared travel support does not activate it here. Direct **I'm travelling tomorrow** remains unsupported wording. E.|
|[ ] **I'm going shopping or to class.** / **I'm going to class and a wedding.**|UnsupportedRequest; no silently selected first occasion. E.|
|[ ] **I'm going shopping; prefer blue.**|Soft preference represented but unavailable; not turned into a hard condition or saved preference. Comfort goals similarly unsupported. E.|
|[ ] **I'm not going shopping.** / contradictory codes|Controlled UnsupportedRequest, no requirement deletion. E.|
|[ ] **I want something smart casual.** / **I'm having dinner with my family.**|Still unsupported; no unapproved standalone or family-dinner extension. E.|

For unavailable specific requests, the UI should explain the limitation and invite
an edited **new** request. It must not label a generic outfit suitable for the
discarded situation. Technical 503/network errors are operational failures, not
successful fashion refusals; record them separately and do not force data repair.

## 10. History, saved outfits and security checklist

1. [ ] After a successful request, open Recommendation history, search using its
   wording, and open the completed chat. Check original request, stored explanation,
   garment names and scores. B/C; previous exact replay/source tests are A.
2. [ ] Reopen the same historical record. If you later choose a real preference or
   review change, the old record must not be reinterpreted or rescored. A fresh New
   Chat with identical words is a different key and may legitimately produce a
   different result. The normal UI does not expose raw submission keys; do not edit
   tokens/keys in DevTools to fake a normal-user replay test.
3. [ ] Optionally **Save as outfit** if you want a real stored outfit. Expect the saved
   state. Current ownership/status/source eligibility still applies; an old snapshot
   is not a guarantee that an archived/unavailable member can be saved/visualised now.
   Opening source preparation is not proof that real VTON inference is available.
4. [ ] Optionally open a separate incognito browser and sign in again to create a
   distinct session. Do not copy tokens between sessions. Sign out in the first:
   expect pending/disabled state, successful cleanup and `/auth`. New protected access
   using that session must be invalid; stale cached page pixels alone do not prove
   continued authorised server access.
5. [ ] The separate new session should remain valid; log back in to the first as
   needed. Logout is per bearer and all its copies, not account-wide logout. New
   v2 logins are independent; identical legacy bytes share one revocation identity.
6. [ ] If logout reports a network/server error, do not assume server invalidation
   succeeded. Keep the normal Retry sign out flow. Do not remove the DB/secret,
   clear revocation records, rotate secrets or disable auth to make login work.

Restart invalidation, copied-token denial and lost-response races already have A
evidence. A private-server restart is not required to repeat them for this checklist;
it would require the separate launch/stop decision and current startup preflight.

## 11. Practical usability findings and prioritised future proposals

These are source/evidence observations and questions for fresh B testing, **not UI
changes or user-study findings**. Phase 5 screenshot/test evidence demonstrates
bounded geometry/actions on synthetic data, not how easily a normal user understands
the terminology or judges a real outfit.

| Priority | Current concern | Proposed follow-up, requiring its own approval |
|---|---|---|
|1|The old launcher silently selects the legacy context profile, so accepted natural requests appear broken.|Make manual feature selection/version visible in operator status; consider an explicitly approved launcher context setting. This review provides a process override and makes no edit.|
|1|Generic insufficient-evidence text does not always identify the exact member and missing field.|Design actionable per-member guidance using existing safe provenance; distinguish missing review, uncovered style, malformed data, Deny and structural shortage. No automatic reclassification or relaxation.|
|1|Casual style versus casual formality is easy to confuse; supported natural phrasing remains bounded.|Show interpreted requirements/examples before submission in a separately scoped UX design. Keep existing scoring/declaration meanings; do not silently remap wording.|
|1|Real image processing is incomplete locally while the rest of the app can run.|Clearly label development/unavailable sources. Obtain existing teammate evidence/assets lawfully before proposing installs/inference. No fallback may be presented as real AI quality.|
|2|Style review is inside Contextual recommendations, whose help still emphasises wedding and sits near wedding overrides.|Consider reusable-attribute-first progressive disclosure and context-relevant help. Do not add mandatory event-tag grids. Wardrobe UI is unchanged here.|
|2|All three interview construction fields appear for every garment; tailoring/structure are subjective and condition is dated.|Evaluate definitions/visual examples and role-relevant field guidance, preserving Unknown. No automatic category/style-to-feature inference or expert-certification claim.|
|2|Capability and limitation paragraphs are long on a narrow screen; role/code discovery often happens after a refusal.|Measure comprehension with real users; consider concise supported examples and structured missing-context guidance. Multi-turn clarification needs a separate key/history contract review.|
|2|Compatibility contribution, midpoint/no-pair reference and overall score may look like confidence or aesthetic accuracy.|Improve explanation wording/layout through a scoped proposal; keep exact 60/20/20 arithmetic. Ask users what they believe the number means.|
|3|Some parsed concepts are inactive; users may expect unrestricted conversation or family/travel support.|Publish a concise supported/unsupported guide and prioritise further design from observed manual friction. No automatic new policy batch.|

Positive foundations: explicit New Chat/read-only completed requests, discoverable
everyday examples in the general profile, visible assumptions/limits, reusable style
review, Unknown choices and dated observations, distinct control outcomes, history
provenance and tested wrapping/keyboard/native zoom. Validate usefulness and clarity
manually without converting those source observations into a new acceptance rate.

## 12. Remaining acceptance and disposition

RN-13 and FR-VIS-01 remain Partial. FR-DW-03/04/06/07, FR-VIS-09 and NFR-01/02/03/11
remain Unverified. Remaining owners/decisions include lawful real CV/segmentation/
attribute/VTOFF/VTON evidence; bounded RN-13/VTON category/scope acceptance; final
SQLite versus PostgreSQL/pgvector architecture; formal NFR baselines/history maximum/
resources/statistics; actual HTTPS/deployment/launcher/retention/cutover/recovery;
and canonical ai-services layout/assertion reconciliation. Ordinary clean stops do
not erase the earlier large-run shutdown issue.

**UAT preparation complete; launch and fresh manual results pending.** No claim of
current live backend/frontend/proxy/login, actual-wardrobe suitability, real-model
operation, universal accessibility or formal NFR-02 acceptance is made. Preserve
the accepted Phase 5 results and all earlier failures. No implementation, model
download/inference, private data migration/write, service restart/stop, global
activation, full benchmark, commit/staging/reset/delete or next policy phase begins
from this document. **Wait for the owner's gated launch decision.**
