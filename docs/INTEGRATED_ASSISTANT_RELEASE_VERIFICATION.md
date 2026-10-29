# Phase 5F-2E-3J-12: integrated Assistant release configuration verification

2026-10-23, Asia/Kuala_Lumpur. Verification only; no production source, global
default, deployment environment, database provider or historical record changed.
J-11 is accepted for closure PASS WITH LIMITATIONS and its inventory is now
reconciled. **J-12 overall: PASS WITH LIMITATIONS; ready for owner review.**
The qualified eight-call regression completed after the owner paused workloads.

## J-11 inventory reconciliation

All seven approved application changes exist in the working tree. Every current
file matches the J-11 `wardrobe_quota_sources.v1.json` after-hash and its frozen
deliverable-index hash; every captured original matches the before-hash. All50
J-11 indexed deliverables verify. The three frontend pages are tracked modified
files, not absent implementations. The session's14-file display is not a complete
source inventory. No actual inconsistency was found, so verification proceeded.

| Approved application file | Actual Git state | J-11 frozen transition |
|---|---|---|
|`backend/app/application/wardrobe/wardrobe_service.py`|Tracked, modified|Verified|
|`backend/app/api/wardrobe_routes.py`|Tracked, modified|Verified|
|`backend/app/api/garment_processing_routes.py`|Tracked, modified|Verified|
|`frontend/app/wardrobe/page.tsx`|Tracked, modified|Verified|
|`frontend/app/extract/page.tsx`|Tracked, modified|Verified|
|`frontend/app/extract/results/page.tsx`|Tracked, modified|Verified|
|`frontend/lib/api.ts`|Tracked, modified|Verified|

`j11-reconciliation.json`, seven phase-specific diffs, the cumulative Git patch
and `inventory-git-status.txt` retain this evidence. The J-11 guard/manifest/report
are untracked earlier deliverables in this checkout; that does not remove them
from the verified source state. Existing cumulative changes are not all J-12
changes. No J-11 report, source guard, manifest, index or raw artifact was rewritten.

## Intended configuration and actual defaults

The intended controlled release is compact execution, experimental three-component
scoring, suitability enabled, strict confirmed-available acquisition, all four
supported structures and the implemented100-active-entry quota. Exact weights
are3/5 request,1/5 compatibility decision,1/5 preferences, with no per-candidate
renormalization. Every mandatory-valid candidate is scored before publication of
exactly one deterministic winner. The tie sequence remains total/R/C/P/stable ID.

| Server selection | Code fallback when unset | Controlled J-12 child processes |
|---|---|---|
|`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`|`compact_exhaustive`|`compact_exhaustive`|
|`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`|`compatibility_deferred`|`experimental_compatibility_decision_v1`|
|`SMART_WARDROBE_ASSISTANT_ENABLED`|false|true|
|`SMART_WARDROBE_HOMEPAGE_ENABLED`|false|true|
|`SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED`|false|true|

The five flags are unset in the inspected host process/user/machine environment
(`host-release-flags.json`). This is not an inspection of a separately deployed
service environment. The tested configuration comes from explicit environment
values in the disposable test launcher; it is not a global default activation.
The100 quota is always enforced by its application writer, independent of these
recommendation flags. Named/exact-anchor colour policy remains unchanged;
approximate hex matching stays disabled. Homepage remains random, independently
of deterministic Assistant ranking.

Enabled suitability values remain campus, work, casual_outing, shopping, dinner,
party, date and travel; casual and smart_casual formalities. Exercise/formal remain
PolicyUnavailable. Owner Allow evidence is required for every member, including
outerwear; Deny fails and missing/conflicting/invalid evidence stays Unknown.
No style-to-occasion inference, automatic annotation, missing-value promotion or
general hex classification is introduced.

## Actual entry points and restart behaviour

`frontend/lib/api.ts:createRecommendation` checks authenticated capabilities,
then posts to `/api/v1/recommendations?pipeline=integrated` with a durable
submission key. The normal Assistant component uses this function; an ordinary
client cannot select execution/profile/evaluator parameters. Wardrobe annotation
controls persist reviewed owner declarations independently of evaluator enablement.

`app.main:lifespan` calls `configure_local_workflow`. Composition validates engine/
profile selections even when Assistant integration is disabled, captures the
environment, chooses the existing suitability evaluator and installs the service.
Profile selection validates the original exact policy/score metadata. There is
no test selector call in the primary browser journey or performance collector.
Test observers only record completed service results/cache counters; they do not
replace engines, weights, evidence rules or ranking results.

**Legacy boundary remains a release limitation.** Explicit integrated requests
when the service is off return404 IntegrationDisabled without a new write. The
frontend's capability guard avoids calling that disabled path. An unqualified
POST with Assistant disabled still invokes legacy generation; a disposable API
test confirms its201 legacy response. With Assistant enabled, unqualified calls
use the integrated service and its key validation. Integrated evidence cannot
certify the disabled legacy path. Retiring that fallback would require separate
approval for `backend/app/api/recommendation_routes.py`, its caller inventory and
focused routing tests; no such production edit was made in J-12.

Composition/rebinding tests verify the same effective release selections and
persisted replay across repeated configuration loads. Separate production-browser
and performance launches use fresh backend processes and the same launcher flags;
their runtime records identify selections. This does not establish installed
service persistence or multi-worker drain/restart behaviour. Environment editing
is not hot reload. `config.py` reads `os.environ`; merely writing a `.env` file is
not proof that a plain Uvicorn launcher loaded it. The actual supervisor/service
configuration remains to be approved and inspected.

The tested frontend uses the existing production Next build from J-11, build ID
`QWKAiLQdQhaueWmL7ukvL`, with the normal same-origin proxy to its disposable backend.
Application/frontend sources still match that verified source state; another build
was unnecessary. Same-origin PATCH carries existing If-Match headers. A separate
cross-origin deployment still needs the previously identified CORS/If-Match review;
this test does not approve another frontend/backend-origin topology.

## End-to-end and regression results

354 focused backend tests passed in145.43s, including11 new fixed-startup-release
tests and existing quota, suitability, scoring oracle, rollback/replay, strict
query, history/actions, saved-outfit and frozen-source regressions. A separate39
tests passed in19.18s for the fixed experimental release profile: all10 supported
suitability values under Allow/Deny/Unknown, controlled unavailable/unsupported/
empty outcomes, all four structures with combined five-field requests, and an
injected late metadata failure with complete rollback and same-key retry.

The exact independent Fraction oracle covers all nine retained scoring cases,
components,0.60/0.20/0.20 weights, winner IDs, stable ranking, profile provenance,
replay and fresh-key determinism. Raw NotApplicable/NoPreferences remain NULL
while their numerical contributions are zero. Full-quota tests add99 unavailable
unverified rows around one valid confirmed garment: usage becomes100, acquisition
still yields only the valid garment, scores/history replay remain exact and saving
an existing recommendation consumes no garment slots.

Eight production-browser tests passed in35.5s with actual authenticated API and
disposable SQLite. The new normal journey uploads and reviews a development
candidate, confirms from99 to100, displays the quota and completion notice, and
submits through the normal Assistant. A campus request without declarations
correctly returns InsufficientEvidence; a vintage request returns one confirmed
dress with exact total7/10 under the intended profile. Existing browser flows
verify owner-declared campus/casual controls, positive/negative outcomes,
immutable history/replay, quota conflicts, explicit subset selection, committed
archive refresh, stale-count/name/selection preservation, unavailable-capacity
recovery and a lost successful-response reconciliation without another write.

The99 pre-existing entries in the boundary-browser setup are deliberately
unverified fixture rows and do not become recommendation eligible. J-10 frozen
performance populations instead have100 genuine fixture-confirmed item/job/owner
links and unchanged materialised attributes. Synthetic/development processing is
used throughout; neither setup is real CV/VTON quality validation.

Initial new-test failures were fixture/expectation issues, retained in logs:
history's import-captured DB default needed the disposable test path; absent
public R/P values needed their documented NULL states rather than an invented
numeric-zero display; the default evaluator factory is a lambda constructing the
evaluator. These corrections change only new tests, preserve independent exact
contribution expectations and leave production/original oracles untouched.

TypeScript and relevant ESLint passed. `git diff --check` passed; new-file
whitespace checks cover added tests/configuration/documentation. All1,745
pre-existing captured files remain byte-identical, including the50 indexed
J-11 deliverables. Production source, old source guards/manifests, frozen inputs,
earlier reports and all captured prior verification artifacts remain unchanged.

## Matched release performance regression

The plan is frozen before collection in `performance-plan.json`: unchanged
J-10 balanced100 (17,710 structures) and maximum-combination100 (38,148), the
same rows/IDs/preferences/request, compact+experimental+suitability only, each
one fresh HTTP call followed by three fresh browser calls. This is eight calls,
not another capacity distribution, optimisation study or rerun of J-7/J-10.

The collector verifies J-10 fixture/expected hashes and exact semantic fingerprints,
complete scored counts, provenance and unchanged pair/aggregation cache bounds.
It uses normal login/JWT, POST/submission keys, the current production proxy and
visible-result boundary. Thumbnail completion is outside that original boundary;
protected synthetic thumbnails are available. All first, slow, failed and blocked
observations are retained. There is no recommendation warm-up, timing timeout
extension, candidate pruning, profile override endpoint or hidden reclassification.

Original resource qualification remains three consecutive CPU<=20% and free
RAM>=4GiB observations after10s settling, bounded120s wait. Before timing, CPU
was68%, with Roblox around24.2% of total machine CPU; no timings had started.
The owner was asked to pause heavy workloads, and no applications were stopped.
Formal NFR-02 remains OPEN; these snapshots are not continuous isolation.

**Initial performance attempt was resource-blocked.**
The bounded initial attempt retained42 preflight samples: CPU25-77%, never three
consecutive samples<=20%. It submitted **zero timed requests**. Raw
`performance-initial.json`, `performance-initial.log`, summary and Playwright trace
remain preserved. No slow sample was discarded because no timed sample exists.
The collector's one failed test records resource qualification failure, not a
failed recommendation. Its functional/backend runtime selections were verified
before preflight; no selection endpoint was called.

After the owner confirmed paused workloads, a read-only check showed9%CPU.
All48 initial J-12 indexed deliverables and frozen collector/fixture hashes were
verified before resuming. The initial report and commands are backed up as
`report-before-resume.md` and `commands-before-resume.txt`; the original blocked
index/summary/raw artifacts remain unchanged. The new `quiet-retry` label and
separate output directory preserve the first attempt. No other test/build/profile
work ran concurrently with timing.

Automatic preflight qualified at **19%,18%,15% CPU**, after19 retained samples.
**All eight requests succeeded (HTTP201), with eight distinct recommendation IDs
and chat IDs, zero errors/timeouts and zero responses above5s.** Effective
provenance confirms compact execution, experimental scoring and suitability.
Every selected-member/exact-score/semantic-provenance fingerprint matches its
retained J-10 result; all17,710/38,148 valid candidates were scored. Pair cache
remained<=19,900 and aggregation/certificate caches<=256; quotas stayed100 before
and after each workload. No profile/evaluator selector endpoint was called.

|Workload|HTTP seconds, first call|Browser seconds, all three in order|Browser median|Browser maximum|J-10 browser median / maximum|
|---|---:|---|---:|---:|---|
|Balanced100;17,710 candidates|0.8805452|1.0545330,1.1883936,1.0080929|1.0545330|1.1883936|1.0778876 /1.1883160|
|Maximum-combination100;38,148 candidates|1.8574733|2.2383556,2.3846428,2.1178632|2.2383556|2.3846428|1.9780911 /2.3466895|

Full floating-point observations are retained in `performance-quiet-retry.json`
and its summary. Minimum observed deadline headroom is **2.6153572s**. The
maximum-combination browser maximum is approximately38ms above J-10, while its
three-sample median is approximately260ms higher than the earlier five-sample
median. Balanced observations remain close. These sequential small populations
support usable headroom for this frozen release regression; they do not establish
statistical equivalence, isolate a quota-overhead effect or justify attributing
latency changes to an algorithm change. There was no scoring/enumeration change.

Before/after timing snapshots ranged **9-90% CPU** and **7.10-7.50GiB free RAM**.
Passing initial qualification is not continuous process isolation; CPU snapshots
can include browser/backend work and background activity. No observation was
removed or replaced. These resource limits and sample-size/boundary qualifications
remain part of the evidence, even though every response met the5s regression
bound. This is not formal NFR-02 acceptance or concurrent-user/deployment capacity
proof. No additional timing or capacity experiment is recommended by these results.

`resume-plan.json` records execution order before resumption: the unchanged pinned
collector explicitly runs balanced then maximum, as the original report states.
The original plan's schedule list enumerates the same workload cells in reverse
order; that metadata-order discrepancy is disclosed rather than rewritten.
The fixed collector, workload rows, repetitions, scoring/evidence decisions,
timeouts and resource controls are byte-identical. The first attempt had zero
timed calls, so no measurement was reordered or replaced.

## Remaining acceptance and deployment limits

RN-13 is verified for the controlled8-occasion/2-formality declared scope;
exercise/formal/general non-anchor hex coverage remain unfulfilled without
additional accepted policies or an explicit supervisor scope limitation.
Default-off suitability still does not fulfil those request fields in an unset
deployment. Annotation freshness, null/empty semantics and ambiguous fallback
black provenance retain their earlier qualifications.

RN-17's implemented bounded heuristic is verified in the explicit release profile,
with midpoint, no-pair dress1/2 and correlated style effects disclosed. This is
neither independent fashion-quality validation nor proof of optimal weights.
The unchanged deferred default still leaves live/default RN-17 Partial until
separate activation approval. Existing owner functional-policy acceptance does
not make a disabled profile the running global standard.

No private/deployment quota inventory was performed. Preserve accounts already
above100 and agree recovery for unusual/non-visible statuses before rollout;
never automatically prune/repair historical rows. Pending jobs reserve no slots;
archiving still respects outfit/VIS dependencies. Privileged SQL/future imports
need equivalent guards. Same-job confirmation stays409 on retries, not201 replay.

The runnable provider remains SQLite despite its filename. Test isolation and
BEGIN IMMEDIATE do not certify PostgreSQL, multi-process service capacity or a
required PostgreSQL/pgvector report commitment. The owner/supervisor DB decision,
real CV/VTON artifacts and authorised supported-model journeys remain separate.
No production data/schema/provider/model migration or inference ran here.

## Proposed activation and rollback, NOT EXECUTED

No application change is necessary to enable the tested configuration in a
properly configured service process. After owner approval, deployment owners
must pin the following in the actual backend launcher/service environment:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='true'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED='true'
```

These shell assignments are examples for that process/children, not persistent
deployment settings. Freeze effective source/policy/lock/config hashes, intended
SQLite path and proxy origin; inventory existing quota counts first. Retain the
existing approved authentication/AI configuration; test identities/secrets and
`/_test` fixture servers must never become deployment entry points. Do not flip
validated versioned JSON `default_activation` fields. No new app fallback is
needed for explicit environment activation. If changing unset code defaults is
later required, separately scope selector/service-constructor/composition edits
and their source transition; that is not authorized by this verification.

Restart every backend instance with those settings. Verify capabilities, fresh
normal browser submissions, profile/evaluator/weight provenance, quota99/100 and
supported positive/negative/Unknown outcomes. Verify history/replay without
rescoring. The deployment owner must handle drain/termination: in-flight requests
retain captured selection; a killed process cannot finish. Atomic rollback and
same-key persisted-result recovery remain the mechanisms. A running process
does not adopt changed environment by itself. Restart/rebuild the frontend only
as required by its actual proxy/configuration change and normal release process.

Rollback while retaining the integrated path:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='false'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
```

Restart all affected backend instances and verify a fresh submission plus stored
experimental replay. `reference` is the existing optional execution rollback;
it is not required merely to roll back scoring. Removing scoring/suitability
overrides restores deferred/off only after removing persistent service overrides
and restarting. Keep the100 quota, immutable history, annotations and database;
no data rollback/rewrite is required. Disabling Assistant alone is not a backend
generation shutdown while the unqualified legacy fallback exists. A fail-closed
route/caller transition needs the separate approval described above.

## Final recommendation

**PASS WITH LIMITATIONS.** J-11's inventory condition is resolved. The intended
configuration works through ordinary startup and normal authenticated requests,
including the100 quota.354+39 backend checks, eight functional production-browser
checks, TypeScript, relevant lint and whitespace checks pass. The qualified
eight-call regression passes with exact J-10 semantic fingerprints and2.615s
minimum observed latency headroom. All1,745 pre-existing captured file hashes
and50 J-11 indexed deliverables remain unchanged. The prior blocked disposition
is preserved, superseded by the completed retry rather than erased.

J-12's planned verification is complete. Safe activation/deployment still requires
owner approval of actual service settings, quota inventory, the legacy-route
decision, restart/drain/rollback proof and the database commitment decision.
Global defaults remain deferred/suitability-off, and disabled/unqualified legacy
generation remains a separately scoped release risk. RN-13/RN-17 scope/quality
qualifications above remain; **NFR-02 remains OPEN / NOT FORMALLY ACCEPTED**.
No global activation, optimisation/capacity phase or next phase starts. Wait for
owner review before implementing any activation change.
