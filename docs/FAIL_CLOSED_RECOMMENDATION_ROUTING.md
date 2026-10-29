# Phase 5F-2E-3J-14: fail-closed recommendation routing and regression verification

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-13 is owner-closed PASS WITH LIMITATIONS. The owner explicitly authorised the
generation-route correction, the shared frontend API helper if needed, and
directly necessary tests, source transitions and documentation. That scope
satisfies the shared-file approval boundary; no Digital Wardrobe or CV/VTON
application file was edited. No global feature default or deployment was activated.

## Problem and exact production changes

J-13's disposable authenticated reproduction returned201 for three unqualified
POSTs while Assistant integration was disabled, including two with the same key.
Each wrote a distinct legacy recommendation/chat, with no integrated receipt.
The explicit integrated URL already returned404 IntegrationDisabled. The retained
J-13 evidence remains unchanged; it describes the old source state.

Only two production files change:

|File|J-14 change|
|---|---|
|`backend/app/api/recommendation_routes.py`|Remove the disabled/unqualified call to `recommendation_service.create_recommendation`. Both generation URL forms now return the same existing404 IntegrationDisabled response when the injected integrated service is None.|
|`frontend/lib/api.ts`|Deprecate the unused one-argument overload and reject it with ApiError422/InvalidInput before any network request. Keep its exported signature for source compatibility. The keyed overload still checks capabilities and posts explicitly to `?pipeline=integrated`.|

There is no service exception handler added: an infrastructure/scoring/persistence
failure is not converted into IntegrationDisabled. Enabled generation still calls
the same service and uses its unchanged outcome-to-HTTP mapping. Homepage, list,
history, saved-outfit lookup and save actions retain their existing boundaries.
`recommendation_service.py` remains byte-identical, including historical read/save
functionality. No recommendation/scoring/evidence algorithm was edited.

## HTTP contract and compatibility

Authentication and Pydantic body validation still run through the same FastAPI
dependencies/model. Unknown pipeline values still return422 before dispatch.
Malformed supplied keys still produce model-validation422 even when disabled;
missing or null keys pass the model and are handled at dispatch/service level.
The ordering of the existing extra-field check also remains unchanged.

|State and request|Result|
|---|---|
|Unauthenticated/invalid bearer, with development identity disabled|401; no generation writes.|
|Authenticated malformed body/key or unknown pipeline|422; no generation writes.|
|Assistant disabled, explicit or unqualified, model-valid body (key present/absent/null)|404, `{"status":"IntegrationDisabled","outcome":"IntegrationDisabled","complete":false}`; no legacy dispatch or generation writes.|
|Assistant enabled, explicit or unqualified, valid fresh key/request|Same integrated workflow;201 on Selected, existing controlled outcomes otherwise.|
|Enabled missing/null key or extra unsupported body fields|Existing422 InvalidInput; no legacy fallback.|
|Enabled same owner/key/text, including switching URL form|200 replay of the original integrated result; no extra rows.|
|Enabled same owner/key with different text|409 IdempotencyConflict; original record remains unchanged.|

This intentionally ends disabled legacy-generation compatibility. Old clients
cannot use disabling integration to generate placeholder results or bypass keyed
persistence. Enabled unqualified requests remain supported with the integrated
key requirements; clients should use explicit integrated requests and durable
keys. Existing legacy rows remain readable and actionable under existing owner/
eligibility rules. No historical data migration, deletion or rescore is needed.

The deprecated frontend overload now rejects instead of returning an unkeyed
legacy result. No current production component uses that overload. External
clients/importers cannot be discovered completely from this checkout and must
be told about the new disabled/unkeyed response contract before deployment.
The normal Assistant already passes its durable key and needs no component edit.

## API, concurrency and historical evidence

`backend/tests/test_fail_closed_routing.py` adds26 cases using authenticated
HTTP boundaries and disposable SQLite. It exercises both URL forms, enabled/off,
valid/missing/malformed keys, null/extra bodies, auth/validation ordering,
cross-form replay, conflicts, concurrent keys and legacy historical actions.
`api-trials-final.jsonl` retains full synthetic responses and row-count evidence.

The20-cell generation matrix covers both states and URL forms with valid,
missing, malformed-pattern, non-string and empty keys. For every rejected
submission, complete before/after row collections compare equal for:
recommendations, nlp_chats, recommendation_items, recommendation_metadata,
recommendation_submissions and recommendation_item_snapshots. A forbidden
legacy-generator spy is never called. Additional repeated disabled submissions
against an existing historical record also preserve all six row collections.

Two threads submit the same key/text through different URL forms after a barrier.
The actual repository uses independent SQLite connections: responses are201 and
200, with one recommendation ID, one chat ID, identical score metadata and exactly
one new row in each of the six tables for this single-dress fixture. This is
same-file/threaded connection evidence, not multi-process/PostgreSQL certification.
Serial cross-form replay and changed-text conflict also preserve the original
scores, provenance, items and receipt without appending rows.

A genuine synthetic legacy record is created directly as a historical fixture,
outside the public generation route. With integration disabled its list/chat
read, eligible save and saved-outfit VIS preparation succeed; foreign-owner
chat/save/VIS actions return404. The save consumes no garment slot and preserves
scores/record counts. Its normal available-to-saved action is not disguised as
byte-identical status history. No real account or existing deployment row was
modified. Old snapshot/tampering and workflow tests similarly seed historical
legacy records directly, preserving their read/save/VIS assertions rather than
reopening a public generation path.

## Frontend, startup and rollback verification

The helper contract test transpiles the actual `frontend/lib/api.ts` export into
a browser-like sandbox with a fetch recorder. Unkeyed calls reject with zero
network requests; keyed enabled calls use the explicit integrated URL and retain
their key; keyed disabled calls fetch capabilities and issue zero generation
POSTs. This is a helper test; real application requests are verified separately.

The isolated browser supervisor starts untouched `app.main:app` with normal
composition/authentication and a new production Next build, not a selector API
or test application. It runs activated experimental/suitability, same-config
restart, deferred/suitability-off rollback and Assistant-disabled stages against
the same disposable DB. J-13 scripts/tests are preserved; separate J-14 copies
retain the independent score/history expectations and replace only the obsolete
disabled-generation expectation. Backend launch/shutdown and browser results are
recorded in `verified/process-ledger.json` and its stage logs.

Activation explicitly pins compact, experimental_compatibility_decision_v1,
suitability=true, Assistant=true and Homepage=true in child environments.
Rollback retains compact/Assistant/Homepage and changes scoring to deferred and
suitability to false. The final stage sets Assistant=false. These selections are
local child-process settings, not installed/global environment changes.

The normal activated journey confirms reviewed synthetic top/trousers/dress,
uses real owner suitability controls, verifies random valid Homepage selection,
and submits via the normal Assistant with exact60/20/20 components/provenance.
Deny, Unknown, conflicting declarations and exercise/formal unavailable cases
retain their outcomes. Quota99-to100, whole-batch conflict/retry after archive,
full upload admission, owner isolation and saved-outfit preparation remain intact.
Restart and deferred rollback preserve original experimental history text and
keyed replay while fresh requests use the selected profile. In the disabled
stage the UI displays its existing disabled message and issues no generation
POST. Direct unqualified absent/repeated-key calls now all return404.

Stopped-stage read-only SQLite snapshots compare all earlier generation rows
unchanged across the rehearsal. The disabled snapshot must equal the rollback
snapshot in all six generation tables, not merely preserve a row subset. There
is no frontend/profile override or hidden legacy result. No inference, capacity
experiment or NFR latency collection is part of these functional checks.

## Source ownership, guards and regression scope

Supporting changes are the new backend routing tests, new frontend helper/
browser tests/configuration, J-14 supervisor/audit artifacts and this report.
Six existing tests change only their deliberately superseded routing expectations
or historical fixture setup: `test_workflow.py`, `test_o2_recommendation_boundary.py`,
`test_confirmed_garment_snapshot.py`, `test_outfit_assistant.py`,
`test_phase5f_audit.py` and `test_release_configuration.py`.

`backend/tests/fixtures/fail_closed_routing_sources.v1.json` records exactly two
production before/after hashes. `integration_source_guard.py` follows that new
transition after the prior integration/quota transitions. Every original manifest,
reference archive and scoring expectation remains unchanged. No broad manifest
repinning or independent arithmetic/persistence oracle change was made.
The captured starting workspace contains earlier uncommitted phases; the phase
patch/original copies identify only J-14 changes, not the entire cumulative Git diff.

The initial backend attempt retained151 passes and two failures in the new auth
test: the reused fixture included a development X-User-Id header. The corrected
new test disables development identity, proving invalid bearer401 and preserving
authenticated validation ordering. No production authentication or old assertion
was weakened. The final expanded run passes443 tests in134.28s, with one existing
Starlette/httpx deprecation warning. Exact commands/logs accompany the report.

## Final verification and disposition

|Check|Result|
|---|---|
|Focused backend regressions|443 passed in134.28s, including26 new routing cases and all six intentionally adapted legacy-contract modules.|
|Production-browser rehearsal|Four stages passed with actual app.main/Next/login, including experimental activation, same-config restart, deferred rollback and disabled generation.|
|Disabled writes|All six generation tables are identical before/after the disabled browser stage. Rejected API matrix requests and repeated disabled calls also add no rows.|
|Concurrent duplicate key|201+200, one recommendation/chat, one receipt, identical metadata; one row per generation table in the single-member fixture.|
|Production build|Passed; build ID `K69qSH2Qlp-dAB6ZtNOys`. Previous builds retained.|
|Helper, TypeScript and scoped ESLint|Passed; unkeyed helper sends zero requests and keyed disabled helper sends no generation POST.|
|Source/evidence integrity|1,877 starting hashes checked:1,868 unchanged, exactly nine approved existing-file changes (two production, six tests, one guard). All70 J-13 indexed deliverables unchanged.|
|Whitespace|`git diff --check` and explicit new-file checks passed.|

Backend PIDs28120/26200/6912/3256 each record a normal clean shutdown. Frontend
PID10532 was also stopped; no unrelated process was stopped. The three restarts
share the disposable DB. Raw process flags, commands, row snapshots, browser
responses, API concurrency ledger, phase patch/originals and deliverable hashes
are in `storage/verification/phase5f2e3j14/`. Next-generated tsconfig/next-env
files were restored to their original bytes; the ignored compiler cache is not
included in source-integrity claims. Browser log NO_COLOR/FORCE_COLOR warnings
and the backend dependency deprecation warning are retained.

**PASS WITH LIMITATIONS.** Public disabled legacy generation is closed, enabled
requests retain integrated key semantics, and existing historical actions and
rollback pass. This is tested implementation readiness for owner review, not a
production deployment or final FYP acceptance decision. All prior source
manifests/raw evidence retain their bytes; only the explicit new transition
allows the two production hashes to advance.

## Remaining release limitations

No global defaults or deployment settings change: unset scoring stays deferred,
suitability stays off and integrated feature flags stay off. Fail-closed routing
is an application correction independent of eventual activation; deployment
owners still need an approved launcher/restart plan and real quota inventory.
Preserve over-limit/unusual-status accounts and agree recovery; do not prune them.

SQLite remains the actual provider. PostgreSQL/pgvector architecture commitment,
multi-process recovery/drain/service-manager proof and real CV/VTON raw artifacts
and supported-model coverage remain separate. This phase runs development
processing fixtures and prepares VIS sources; it does not certify model quality.
RN-13's bounded8/2 and colour limitations and RN-17's disclosed heuristic conventions
remain. **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** No next phase is authorised
by this correction; wait for owner review.
