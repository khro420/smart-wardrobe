# Context-aware wedding recommendations: implementation and local verification

2026-10-24, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
The owner approved the wedding policy W01-W05,
the named shared/T scope and the named R implementation scope in the
[extension proposal](CONTEXT_AWARE_RECOMMENDATION_EXTENSION_PROPOSAL.md).
The proposal remains a historical preparation document; the actual approval is
recorded in `storage/verification/contextual_wedding_v1/ownership-approval.json`.
This is the authorised extension, with no new numbered acceptance phase.

The extension recognises situations such as **"I'm going to a wedding"** and
offers one provisional guest outfit from the current owned, confirmed, available
wardrobe when the approved evidence rules pass. It never interprets wedding
alone as formal. The result explicitly discloses an assumed guest role and an
unspecified dress code. This is bounded rule-based interpretation, not a claim
of unrestricted language or independent fashion expertise.

## Implemented behaviour

The existing vocabulary, interpreter and declaration policy remain unchanged.
New `contextual-nlp-1.0.0` interpretation and
`wedding-guest-suitability-1.0.0` rules are selected together by an opt-in setting.
Non-wedding requests delegate to the original interpreter/evaluator. A delegated
result retains the effective legacy vocabulary/evaluator/policy and separately
records the contextual adapter, so its provenance identifies both accurately.
The original fixed U15 wedding label remains unsupported in the original
interpreter; only the new opted-in profile adds its support. No old evaluation
label or recorded failure is changed.

Natural situation prefixes, straight/curly/missing apostrophe variants, explicit
guest roles and supported dress-code clauses are recognised by a bounded grammar.
Meaningful unknown tokens, conflicting conditions, alternatives, negation and
multiple requests are rejected. An explicit formal/black-tie code or supported
recognition of a bridal-party role yields PolicyUnavailable, never a casual
fallback. Other unrepresented roles/requirements remain UnsupportedRequest.
Existing explicit colour, style and category constraints remain mandatory.

New immutable context distinguishes actual fields from assumptions. It does
not fabricate an explicit style or formality. The existing request type and
serialization remain unchanged for non-contextual requests. Versions, code/policy
hashes and the actual winning-member evidence are stored with new results.

### Reusable attribute review and optional overrides

An ordinary garment's **Contextual recommendations** controls let its owner
review the current style once. This action is separate from per-occasion tagging.
The server binds the review to the exact canonical singleton style and category,
with a version, source and UTC timestamp. Category/style edits invalidate the
review; re-entering an old value does not resurrect it. Unknown, empty,
unrecognised or multiple-style evidence cannot establish a positive review.
An old confirmation is not automatically promoted to reviewed evidence.

For no specified dress code, W01 admits reviewed `smart casual` style. Explicit
smart casual uses W02; explicit casual uses W03 and reviewed `casual` style.
There is no formality hierarchy or inference from `classic`, garment name,
colour, sleeve length, dress category, material prose or development output.
Uncovered attributes are Unknown (W04). Unsupported required codes have no
policy (W05). Each rule covers every member, including outerwear.

Wedding Allow/Deny controls are optional. An identifiable explicit Deny always
fails, including alongside Allow. Otherwise malformed authoritative declarations
block inference; a clean explicit Allow takes precedence for its exact condition.
Only genuinely absent declarations allow attribute inference. Existing formality
declarations retain authority for the requested dress code. Wedding Allow does
not waive another condition. Other occasions do not imply wedding suitability.

The new namespaced JSON representation is `contextual_suitability_v1` in the
existing garment attributes, mirrored without overwriting unrelated evidence.
It does not use or rewrite v1 reserved custom tags. A separate authenticated
owner endpoint requires a content revision and uses the existing write transaction;
stale writes return409. Generic attribute writes cannot create review metadata,
and confirmation strips that namespace from automatic processing output.
Inconsistent/corrupt metadata is not silently repaired. There is no SQL schema
migration, historical backfill, provider change or automatic cleanup.

### Selection, persistence and explanation

Only all-Pass candidates reach the existing scorer. Structural generation,
mandatory colour/style/category rules, compatibility scoring, exact 60/20/20
weights, tie ordering and full enumeration are preserved. Runtime primary and
independently prepared compact facts, public reconstruction and the scoring gate
explicitly admit the new evaluator and must agree. New tests also use a separate
manually specified rule oracle rather than calling the production resolver twice.

The existing repository already compares complete snapshots under its write
lock and writes generic provenance JSON atomically. Its source needed no change:
a review/override changed after ranking is detected as WardrobeChanged before
chat persistence. New provenance records interpretation assumptions, policy
version/hash and the declaration/inference basis and reviewed evidence for each
member/condition. The result and history card explain this basis. Saved outfits
use the existing eligibility checks. Old keyed results and historical explanations
replay their stored values without reinterpretation or rescoring.

## Local activation and manual use

The default remains **disabled**. Invalid or incomplete profile selection fails
startup readiness. The new profile requires the existing Assistant and suitability
flags. The intended existing flags remain:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='true'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED='true'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE='wedding_guest_v1'
```

The existing manual local launcher already retains the chosen local DB/media
and secret and inherits this new process environment setting. When ready to
activate, from one VS Code PowerShell terminal:

```powershell
& "$env:LOCALAPPDATA\SmartWardrobe\manual-j22-20261024\stop.ps1"
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE='wedding_guest_v1'
& "$env:LOCALAPPDATA\SmartWardrobe\manual-j22-20261024\start.ps1"
```

This is an instruction for the owner, not an executed restart. The original
manual services were left running. No User/Machine environment value or launcher
settings file was changed. The launcher retains its five existing recommendation
flags, DB, media and secret. The ordinary dev frontend uses current sources;
no earlier production build is substituted.

Open `http://localhost:3000/wardrobe`. Correct any inaccurate style using **Edit**,
save it, then open **Contextual recommendations** and choose **I reviewed the
current style**. This is reusable attribute evidence, not a wedding tag. Keep
the optional wedding override on inference unless an explicit exception is
intended. Open `http://localhost:3000/assistant`, choose **New Chat** and enter
"I'm going to a wedding" or specify a supported casual/smart-casual dress code.
If the wardrobe cannot establish all conditions, the Assistant gives a specific
controlled no-result message. A result is not guaranteed for every wardrobe.

To return to the original profile, set the new variable to `disabled` and restart
through the same launcher. Stored results/reviews remain; no data rollback or
secret rotation is needed. No automatic application activation or real-account
review/write was performed for this implementation.

## Verification and integrity

Final check results are recorded below. All new evidence is
under `storage/verification/contextual_wedding_v1/`. The final production build
is separate at `.next-integration-run/contextual-wedding-production` with build
ID `Qg3Yk0WYe1Jn95o7nH24-`. Browser verification uses actual installed Chrome,
ordinary app.main/Uvicorn and production Next on isolated3101/3100, real disposable
registration/login and synthetic reviewed/confirmed images. AI development
processing is explicitly confined to those child processes; no real model runs.

- Backend final: **703 passed in545.51s**, native exit0, including84 new
  contextual checks, the original compact frozen-source check and the original
  Assistant transitive-source integrity check. Earlier runs overlap, not extra
  distinct coverage. Much of the final duration is retained source auditing;
  it is not a recommendation latency measurement.
- Actual Chrome: **10/10 passed in39.8s**, two new wedding journeys plus eight
  unchanged shared account/profile/filter/classic/history/logout journeys.
  Chrome reports156.0.8078.48; no new latest-browser acceptance is claimed.
- The successful wedding journey includes keyboard submit, full100-character
  name at360px, save eligibility, real source preparation and immutable history.
  The separate journey verifies Deny rejection and unsupported formal code.
- Final TypeScript, scoped lint and production build passed with native exit0.
  No full performance matrix or new capacity study was run.
- Starting-file integrity: all1156 captured Git-visible paths present;
  **1139 unchanged, exactly17 approved existing-file advances** (15 production,
  one guard and one protected-route inventory test). Whitespace, Python syntax
  and empty staging checks pass. This is the captured source inventory, not a
  claim to have opened or hashed private databases or every ignored old artifact.
  The production transition
  is exactly15 existing files plus seven new modules/configuration files.
  Existing scoring arithmetic/policies, original NLP/vocabulary/declaration policy,
  auth/logout code, quota constant, query eligibility SQL, CV/VTON and defaults
  are preserved. The query adapter adds evidence projection only.

The existing test `test_durable_logout.py` was named before its one mechanical
inventory correction:36 protected handlers, with the new endpoint explicitly
required to use the authoritative authentication dependency. Its original is
retained. The only other modified old test/support file is
`integration_source_guard.py`; it follows a new exact source-transition manifest
after older transitions and does not repin old ZIPs/manifests. Before-copies,
starting hashes and a patch distinguish this work from the pre-existing dirty
tree. No staging, commit, reset, deletion or release packaging was performed.

Initial new backend tests retained7 failures/73 passes: Unicode apostrophe
handling was corrected only in the new interpreter; the new delegation test
was corrected to recognise the expressly approved U15 profile difference; tests
that changed a snapshot within one cached session were corrected to use fresh
sessions and now separately require conflict rejection. The corrected80-case
run passed; later four added cases cover explicit constraints/delegated metadata,
dress-code conjunctions, corrupt mirrors and automatic-metadata stripping.

The initial broad run retained697 passes and one guard failure. The new guard
extension originally tried advancing a hash before older transitions completed;
it now waits for its exact captured before-hash. The corrected focused original
compact source check passed. Initial browser collection retained7 passes/3
failures: two new login locators matched both mode and submit buttons, and one
old assertion exposed delegated provenance naming. The login locators and actual
effective/delegating provenance were corrected. The next run retained8 passes/2
failures from the new alerts also matching Next's route announcer. Scoping those
new assertions to their message fixed the ambiguity; verified is10/10 without
retries or altered deadlines. Old tests/results were not rewritten to erase
these attempts. The frontend production sources/build did not change after the
passing build; backend provenance refinement is included in the verified run.

All isolated browser-run backends completed normal shutdown/exit0 and released
their ports. Temporary DB paths and child PIDs remain in process ledgers. No
manual-session process was stopped. These small ordinary stops do not diagnose
or erase J-16's historical shutdown issue. Existing uv/Starlette/Playwright
warnings and native exit results remain in retained logs.
The final index reader initially expected UTF-8 for PowerShell's UTF-16 log;
BOM-aware decoding corrected that helper without rewriting the raw test log.

## Disposition and remaining limits

**PASS WITH LIMITATIONS.** This extension adds a bounded wedding
guest capability; it does not close unrestricted RN-13 or FR-VIS-01. The155-row
baseline remains **144 Verified / 2 Partial / 9 Unverified**. Whole-FYP acceptance
remains NOT READY and NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. Existing
real-model evidence, supported VTON scope, SQLite/PostgreSQL/canonical-layout,
formal NFR and actual deployment/TLS decisions remain separate.

Other occasions retain their existing behaviour. Formal/black-tie weddings,
unsupported roles/cultural/weather requirements and unreviewed automatic
attributes remain unavailable or Unknown. Provisional guest conventions and
owner descriptions are not independent fashion-quality or model-accuracy proof.
No new formal acceptance, global activation, private DB migration or deployment
is inferred from these local functional checks.
