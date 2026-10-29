# A1 context relevance: standalone Phase A checkpoint and ownership gate

2026-10-27, Asia/Kuala_Lumpur. **Phase A catalogue/definitions verified; staged
implementation is incomplete. Stop before the unapproved shared-source boundary.**

The owner expressly approved D01–D03 and staged progress under D06 in the attached
implementation request. The five automatic prototype objectives and their resolution
definitions are implemented as standalone recommendation code. **76 Phase A tests
pass in 1.14s; native pytest/uv exit 0.** No scoring kernel, API/persistence/history
integration, frontend change or browser verification has been implemented here.

The request explicitly says its project-side approval does not claim independent
supervisor/team approval of shared files. No exact-scope D04/D05 approval was found.
Earlier owner-style/automatic-admission approvals name different increments and
cannot authorise this one. This is an ownership checkpoint, not another product
design-review cycle. D01–D03 are accepted product instructions and are not reopened.

The existing manual application was neither stopped nor restarted. No private
database, garment, photo, account, preference or historical response was inspected.
No secret, launcher, environment default, model or migration was changed.

## 1. Actual authorised changes

All paths are relative to the project root. Exactly four new production files were
added; **no existing production or test/support file changed**.

|New production file|Responsibility / source authority|
|---|---|
|`backend/app/application/recommendation/context_relevance_policy.py`|R-local standalone catalogue validation and objective preparation under the owner's Phase A instruction. Reuses existing capability compilation; no live factory import.|
|`backend/app/domain/value_objects/context_relevance.py`|R-local immutable objective/resolution definitions. These are not changes to the existing shared ranking outcome, recommendation write contract or stored proof. Crossing those boundaries still needs D04.|
|`backend/app/application/recommendation/config/context_relevance_policy.v1.json`|Approved product semantics expressed as pinned, default-off definitions, not executed scoring/selection logic.|
|`backend/app/application/recommendation/config/context_relevance_objectives.v1.json`|Five exact normative objectives, existing binding scopes, authority, explanations and provisional limits.|

New verification files are `backend/tests/test_context_relevance_math.py`,
`backend/tests/fixtures/context_relevance_labels.v1.json` and
`backend/tests/fixtures/context_relevance_sources.v1.json`. This new report is the
only additional repository document. All **540 pinned starting paths remain
unchanged**, including the previous policy pack, historical oracles, twenty proposed
existing production paths and existing `integration_source_guard.py`.

No teammate approval is inferred from placing a recommendation-local value object
in the domain package. It is not exposed to shared API/storage clients. No shared
writer, codec, query, route, composition or frontend source was edited.

## 2. Implemented definition contracts

|Identity|What is actually implemented|
|---|---|
|`context-relevance-policy-1.0.0`|Closed policy configuration and validation; exact 3/5,1/5,1/5 weight definitions, duplicate-mask/mode names and default-off status. No R/P computation or ranked selection yet.|
|`context-relevance-objectives-1.0.0`|Five pinned automatic defaults with exact applicability and prototype-convention authority.|
|`context-relevance-objective-1.0.0`|Immutable style objective, source of authority, target, explanation/limits and canonical semantic-test identity.|
|`context-relevance-resolution-1.0.0`|Separate Resolved, ObjectiveUnavailable, AdmissionUnavailable and OutOfScope states, with strict hashes/reasons/authority consistency.|
|`context-relevance-labels-1.0.0`|Frozen mechanics inputs before scorer implementation: fourteen approved expectations and twenty independently authored point rows under two goals. Not executed ranker results.|
|`context-relevance-sources-1.0.0`|Phase A additions and unchanged starting-source hashes. It does not advance the shared source guard or certify a complete implementation.|

`context_relevance_decision_v1`, `best_evidenced_with_coverage_v1` and
`baseline_disclosed_v1` are validated **definition names**, not available live
scoring/selection modes at this checkpoint. The live factories and old profile
allowlist retain bytes and do not import this module.

The catalogue resolves these exact bare requests in the definition tests:

|Request|Automatic objective|
|---|---|
|I'm going shopping.|casual|
|I'm going to class.|casual|
|I'm going out with friends.|casual|
|I'm going on a date tonight.|smart casual|
|I'm meeting friends for dinner.|smart casual|

Resolution requires no wardrobe read, review action or preference configuration.
An existing supported explicit style overrides the default without modifying the
interpreted request or weakening its hard style gate. A separate supported code
does not inherit the unspecified-code default. An unsupported code/condition cannot
become a fallback. Wedding, presentation, interview, inactive and generic requests
are left to their current dispatch.

The loader validates the existing admission binding, modifiers and interpretation
identities. Alternate server catalogue bundles need explicit expected hashes and
the same closed semantics. A valid subset can express an absent objective; a damaged,
unknown-version, altered-target or corrupt-hash file raises an error, not fallback.
Default bytes pin all five approved objectives.

The new JSON reader reads at most 64 KiB plus one sentinel byte, rejects duplicate
keys/non-finite values, and bounds tree depth and node count. Strings, entry count,
targets, operators and scopes are bounded. After preparation, `resolve()` performs
no file, database, network or model operations. These are configuration/preparation
bounds, not formal latency or candidate-enumeration acceptance.

## 3. Executed evidence and retained attempts

Evidence is outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\a1_context_relevance_phase_a_20261027
```

The retained owner request and `authority.json` distinguish project-side approval
from absent shared-owner approval. `frozen-labels-before-scorer.json` predates any
scorer implementation and matches the repository labels exactly. Original strict
AR03/AR09/AR14 expectations remain in the historical oracle; the new label wrapper
expressly records their approved missing-objective/coverage/code transitions.

|Check|Actual outcome / limits|
|---|---|
|Final focused Phase A invocation|**76 passed in 1.14s**, native exit 0; cached offline Python 3.12/pytest. No application startup.|
|Objective/capability tests|All five exact requests, explicit style precedence, supported separate codes, unsupported formal/black-tie/soft preferences, specialist/inactive/generic isolation, forged interpretation hashes and changed flat projections.|
|Configuration/definition tests|Pinned hashes, closed targets/operators/weights/defaults, unknown/duplicate situations, scope changes, missing entries, duplicate keys, non-finite JSON, invalid encoding, depth/size, immutable objects and no resolution-time file I/O.|
|Independent arithmetic|Forty written point totals from the retained twenty-row/two-goal oracle agree with exact Fraction arithmetic. This is input validation inside one test, not forty executed scorer cases.|
|Source continuity|540 starting scoped paths unchanged; four new production files, three verification files and this report. Empty staging; new-file whitespace checks clean. No existing source-guard adaptation.|
|API/browser/full R/C/P display|**Not executed / not implemented**. Phases B–D await the shared-source gate.|
|Old numerical behavior, transaction/history/logout/automatic Add|Sources unchanged and new definitions disconnected. No fresh behavioral suite is claimed for these boundaries.|

The first invocation retained **74 passed / 1 failed / 2 setup/teardown errors**,
native exit 1. The failure showed that a deeply nested JSON fixture could parse
under pytest's recursion setting; an explicit depth/node budget now rejects it.
The two errors came from a 65,537-byte pytest parameter becoming an oversized Windows
`PYTEST_CURRENT_TEST` environment value. Short explicit parameter IDs fix the test
harness without changing the fixture bytes or size expectation. Original source
copies and native logs remain under `phase-a-attempt-1`; final inputs/logs are under
`phase-a-attempt-2`. The invocations overlap and their passing counts are not pooled.

`uv --no-project` warns that no project manifest was found; native child exit codes
determine outcomes. Dependencies came from the offline cache. Temporary pytest
data and source copies remain outside OneDrive. No browser, model or manual-account
operation occurred.

## 4. Exact remaining source approvals

Section 2 of the attached implementation request requires: **“If approval is
missing, stop before editing that boundary, report the specific files and decision
required, and preserve the already completed authorised checkpoints.”** That is the
reason for this stop. The previous policy pack's D04/D05 and preceding Option A
ownership table identify the same shared boundaries.

**D04: relevant shared API, immutable-contract, storage, composition and integration
owners must explicitly approve this increment**, including:

1. `backend/app/application/recommendation/decision_score_codec.py`
2. `backend/app/application/recommendation/scoring_display.py`
3. `backend/app/api/recommendation_routes.py`
4. `backend/app/domain/value_objects/ranking_outcome.py`
5. `backend/app/domain/value_objects/recommendation_persistence.py`
6. `backend/app/infrastructure/persistence/recommendation_repository_adapter.py`
7. `backend/app/infrastructure/workflow_runtime.py`
8. `backend/tests/integration_source_guard.py`, for exact named source transitions
   and new-file certification, without repinning any historical manifest.

The source-guard approval is needed before advancing frozen existing R scoring
files in Phase B. The five Phase B numeric files themselves are in the R scoring
area approved from the project side: `request_match_scorer.py`,
`compact_scoring_facts.py`, `compact_exhaustive_scorer.py`,
`aggregated_decision_scorer.py`, `preference_scorer.py`. Their later exact transitions,
the four R integration files and two proposed new scoring/verifier modules remain
within the original twenty-existing/six-new production scope. None was edited now.

**D05: relevant shared frontend owners must explicitly approve** these four files
and the already named browser test/configuration scope:

1. `frontend/lib/api.ts`
2. `frontend/lib/recommendation-messages.ts`
3. `frontend/components/OutfitAssistant.tsx`
4. `frontend/components/RecommendationResult.tsx`

The required decision is whether those actual owners have approved these exact
contracts/files for this increment. Project-side product approval or an earlier
increment's consent is insufficient under the attached request. No independent
supervisor or teammate approval is recorded by this task.

## 5. Actual proof-size boundary requiring D04 resolution

The approved pack says to check proof/fraction bounds against the existing valid
preference-weight domain before freezing the shared display/storage contract. That
check found a real limitation: `precise_weight()` accepts arbitrary finite decimal
strings in [0,1], and `NormalizedPreference` accepts the resulting positive Fraction.
There is no finite decimal-digit bound in those existing internal contracts.

Pure in-memory synthetic probes accept weights `1e-324`, `1e-5000` and `1e-20000`.
Their denominators have 325, 5,001 and 20,001 decimal digits. The latter two already
exceed this interpreter's 4,300-digit integer-to-string limit. No private preferences
or database rows were read. Normal HTTP float inputs have a narrower domain; these
probes establish no frequency or presence of extreme weights in actual accounts.

`proof-size-boundary.json` retains exact constructions and native exit 0. A universal
finite exact proof-size guarantee cannot be derived from this unbounded internal
input contract. Increasing an interpreter limit would not establish such a bound.

Recommended D04 direction: approve an explicit **new-profile-only** finite encoding
budget and controlled overflow failure, with the exact numerical budget/state and
user message reviewed alongside the codec. Preserve old accepted weights/profiles;
do not truncate fractions, invent a score, silently use floats, or invoke baseline
fallback on this technical boundary. Owners may instead approve a separately named
input-domain restriction, but that would expand scope into preference contracts and
needs its own authority. No such restriction or budget was implemented here.

This is the unfinished shared proof/display-size part of Phase A, not a reason to
reopen the approved five objectives or their mathematical direction. Later immutable
proof, persisted coverage, archived policy decoding and full R/C/P display remain
unimplemented until the shared decision is resolved.

## 6. Completion and next checkpoint

The authorised standalone catalogue/definition checkpoint is complete and verified.
**The full requested implementation remains incomplete.** Phase B scoring, Phase C
API/persistence/history/UI and Phase D disposable browser verification have not begun.
The five expected winners remain frozen acceptance inputs, not fresh end-to-end
recommendations from a new ranker.

After the exact shared approvals and proof-size decision, continue within the
original scope: implement numerical/public/reference/compact agreement first,
integrate immutable actual-profile/mode/objective/coverage proof and full component
display, then verify disposable API/browser workflows. Do not expose an isolated
scorer as a live feature before provenance and historical coexistence are complete.

**Not ready for a manual activation/restart.** No stop/start permission is requested
or inferred here. The new ranking profile remains unavailable/default-off in live
composition. Existing manual services and private data remain outside this task.

The original 155-row baseline stays **144 Verified / 2 Partial / 9 Unverified /
0 Blocked**; RN-13 remains Partial, NFR-02 remains OPEN / NOT FORMALLY ACCEPTED,
and whole-FYP acceptance remains NOT READY. Independent human appropriateness
evaluation remains OPEN. No new fashion, model, performance or deployment acceptance
is claimed.
