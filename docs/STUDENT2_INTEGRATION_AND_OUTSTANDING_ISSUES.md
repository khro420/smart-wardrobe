# Integrated assistant baseline for teammate functional testing

Integration date: 11 November 2026. This delivery is for functional testing. It is **not performance accepted or production certified**.

## Provenance and scope

The integration starts from team `origin/main` commit `a69d95ba6caf84eacbeec661ee7867068b073a1d` at `https://github.com/khro420/smart-wardrobe.git`. Work was performed in a separate checkout, with a verified full Git bundle of the original repository retained outside the repository. The original OneDrive working copy was not used as the integration workspace.

The functional authority is the exact **919-input** isolated implementation, manifest SHA256 `7efecc48d0781af466a8f41eb9155e583b1a3676f8645f7aa90bd325682388b3`. Its production policy fix is `wearer_category_service.py`, SHA256 `f2a25c66cfda817422ed15bc2eaf8ee8c8758fd86b3943792d0524053b7651bc`. Its corrected processing test fixture is SHA256 `b30f6b40aa14bcd13f8e6e8aebfe2d7ee079b59973289473e3d2646863d6dd61`. The earlier running demo was a different 918-input source and is not this authority. The integrated Git tree has its own identity; it is not relabeled as the isolated source.

The separate **922-input historical verification** delivery was reviewed independently. This integration adopts its public closed 53-route request inventory and original current authentication/capability assertions, using synthetic fixtures instead of its private-demo fixture. The original inventory SHA256 is `82ecbbf6a6954625200dc79af863026b5d23a92c0eb5c4189dc83e217b22a5bc`; the public copy relocates one evidence-path metadata field, with route and capability values unchanged. Its validator for the old 918-input descendant chain, private database fixture and source-bound history fixtures are not merged. Original historical assertions remain associated with their certified source stages.

| Area | Integrated functionality |
|---|---|
| NLP | Conversational interpretation, all 18 contexts, bounded informal/contraction frames, original text/spans, FR-01 multi-garment binding, FR-02 missing-apostrophe frames, FR-03 quoted unsupported-form refusal |
| B0/B1 | Versioned owner descriptions, exact evidence qualification, typed mandatory garment conditions, conjunction binding, negation/conflict/unknown handling |
| Selection | Confirmed available owned garments, four outfit structures, hard predicates, deterministic candidate ranking and stable ties |
| Scores | C1 and explicitly selected C2; P1 and explicitly selected wearer-specific P2; exact `T = 3/5 R + 1/5 C + 1/5 P`; NA contributes zero |
| Types and wearer | Five verified top types, owner event journal, processing-item review and confirmation transfer, v1/v2 wearer policy, shared account inventory, male/female and unresolved-subtype rules |
| Assistant | Current APIs, capability contracts, structured controls and explanatory UI, initial selection and ordinary/pure-B1 alternatives |
| Alternatives/history | Bound actual parents, captured requirements/settings, Seen-base exclusion, floor, ten-result limit, specialist restrictions, durable snapshots, exact replay, account/wearer isolation |
| Supporting services | Authentication/revocation, repositories, profile details/archive, description/preferences/subtype APIs, processing and confirmation wiring, protected media and read-only history |
| Verification | Functional regressions, the fixed seven-binding runtime restorer, current closed route/capability checks, self-contained combined HTTP/browser smoke |

The pre-insert processing view has no persisted subject ID. The policy annotation fix evaluates category eligibility without looking up subtype events for that exact transient shape. Genuine processing-item IDs exist after INSERT; authenticated owner subtype review can then occur. Confirmation creates a distinct garment ID and transfers authoritative evidence normally. Unknown male top subtypes remain unresolved, and prohibited categories remain denied. No detector claim creates verified subtype authority.

The processing test's outer fixture restores the exact prior seven composed services by identity after dependent fixture teardown, including exceptions and pre-existing active configurations. It does not globally reset tests to a fabricated disabled configuration.

## Teammate preservation and contract reconciliation

The latest team upload, image processing, CV extraction/classification, media, VTOFF/VTON, vendor and model sources were compared before integration. The underlying CV and VTON implementations shared with the isolated source are semantically unchanged; team-only vendor/model files remain preserved. No model weight is replaced or downloaded for application inference. Shared orchestration uses the existing mirror implementation through its port and retains genuine extraction payloads and normal review/confirmation.

Related shared changes are deliberate: profile removal uses authenticated archival to preserve history instead of destructive deletion. Legacy DELETE returns `409 ProfileArchiveRequired`; use the archive endpoint. Existing inactive/archived wearer and ownership checks remain enforced. This is part of immutable-history integration, not a change to extraction or try-on algorithms.

Generated tracked `frontend/.next-o1-verification` output is removed from the commit and ignored. Existing public numerical-oracle archives already tracked on main remain unchanged; no new historical archive or private fixture bank is added. Hash-bound source/resource bytes are preserved through Git attributes rather than platform newline conversion. Some shared source diffs therefore preserve the approved CRLF bytes without changing Python/TypeScript semantics. Canonical `backend/datasets` and `backend/runs` README placeholders survive a fresh clone while their generated contents remain ignored.

## Run the combined application with disposable data

Use Python 3.12 and the locked frontend dependencies. The validated runtime used Python 3.12.10, Node 24.19.0, Next 16.4.2, React 19.2.4 and Uvicorn 0.54.0. The frontend lockfile is retained. The backend's broad ML requirements remain separate from the small functional adapter environment.

From the repository root, for synthetic functional testing:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install fastapi==0.146.0 uvicorn==0.54.0 pillow==13.0.0 numpy==2.5.4 python-multipart==0.0.32 pytest==9.1.1 httpx==0.28.1 jsonschema==4.26.0
.venv\Scripts\python backend\scripts\run_functional_testing.py --data-dir "$env:TEMP\smart-wardrobe-functional" --port 8600
```

Choose a new disposable directory. The explicit [functional profile](../backend/deployment/functional-testing.env.example) enables the supported feature dependencies and signed authentication, sets development image extraction, and disables model/embedding/VTOFF/VTON inference. The launcher creates an ephemeral secret unless a test secret is supplied through the environment; restarting with a new secret invalidates old sessions. It uses one worker, loopback only, no reload. It does not modify the ordinary startup defaults or existing deployment profile.

In another terminal:

```powershell
cd frontend
npm ci
$env:SMART_WARDROBE_BACKEND_URL = 'http://127.0.0.1:8600'
npm run build
npm run start -- --hostname 127.0.0.1 --port 3600
```

Register an account through `/auth`. Configure each wearer's gender in the normal profile UI before requests under policy v2. Garment inventory is shared per account, with an unchanged **100-garment account quota**. A confirmed count is not the same as an eligible count for every wearer. Review extracted attributes and subtype evidence through the normal APIs/UI; synthetic declarations are not model or photographic evidence.

P2 availability does not force P2 on every request. C2 availability does not force C2. Both require explicit request selection; captured alternatives and history retain their original modes. Pure B1 requests require a real nonempty B1 intent with no coarse category/context fields. Ordinary “I want a top.” remains a category request with earned R, not a pure-B1 request.

For real-model deployment, follow the existing backend `.env.example`, model manifests and teammate setup. Supply a non-default secret and appropriate weights/dependencies. The synthetic launcher is not a real-model deployment. Accuracy, GPU behavior and full real-image VTOFF/VTON output are not certified by synthetic tests.

## Database compatibility and verification

Runtime persistence remains SQLite despite the legacy repository module name. Initialization and feature-owned stores add the versioned profile details, descriptions/preferences, subtype events and immutable recommendation metadata/snapshots. Do not execute the public PostgreSQL reference SQL as a SQLite migration. No shared or production database was migrated by this integration.

A disposable database was created with the exact main baseline application through registration, upload, review and confirmation, then opened by the integrated initializer. The existing 20 tables' seven original rows and all media remained identical; the new profile-details table was additive. Normal full-feature processing, subtype evidence, confirmation, recommendations and history were also exercised separately. Back up real storage before any operator-controlled rollout; missing gender/subtype evidence must be reviewed rather than invented during migration.

The combined verification results and exact inventory are recorded below before publication. Tests operate on disposable storage. Optional retained public evidence paths use `SMART_WARDROBE_VERIFICATION_ROOT` or the ignored repository-local `retained-verification` directory. Application startup has no dependency on that test-only location. Relocation changes transport paths, not historical hash authorities or numerical labels. Private databases and regenerated goldens are not substitutes for missing evidence.

Three relocated JSON source-authority fixtures have an explicit finite transport contract. The guard checks their exact current bytes, the original pinned 919 manifest and original bytes, then proves that every non-path JSON value is unchanged. It does not return an old hash for arbitrary current bytes. Eighteen positive/tamper controls cover current-byte changes, wrong/unknown identities, original source/manifest replacement and non-transport edits even if a changed current digest is supplied. The original expected authority hashes and numerical expectations remain unchanged.

For the full current regression, mount the owner's original public review packages under `SMART_WARDROBE_VERIFICATION_ROOT`, then run `python backend/scripts/run_functional_regression.py --baseline-oracle <original-approved-baseline-numerical-reference-directory>`. That original B0 oracle directory contains its certified `app.zip` and `manifest.json`; no new goldens are generated. Add `--with-cv` only when the teammate CV dependencies are installed. Without the optional historical packages, additional evidence-dependent tests will fail; application startup and the new normal HTTP/browser smoke do not need those packages. The runner has an explicit versioned scope and preserves native pytest exits, failures and skips.

Historical source identity assertions are executable on their designated 844/915/918 snapshots, not assertions that arbitrary current Git bytes match an old manifest. The processing module also contains one assertion specific to the isolated 919 delivery layout; it passes unchanged on that original snapshot and joins those 42 earlier stage assignments. The current integration has a separate exact-byte test against approved application/configuration hashes and main's preserved model/vendor hashes. Current behavior is tested independently. Missing historical criteria remain failures/unverified; they are not converted to passes by selecting a current functional scope.

<!-- INTEGRATED_VALIDATION_RESULTS -->
Combined repository results: **16,023 unique current passes, 25 retained missing-J15 failures and 152 unverified skips**, across 16,200 unique current nodes. No additional applicable functional failure remains. The actual failing node set matches the earlier missing-J15 set exactly. This is not a zero-exit full historical certification.

| Native current run | Actual outcome | Exit |
|---|---|---:|
| Final shard0 |2,529 passed;25 missing-J15 failed|1|
| Final shard1 |6,412 passed;152 unverified skips|0|
| Unchanged shard2 |7,060 passed|0|
| Additional distinct current checks |1 integrated source proof;18 transport controls;3 teammate geometry cases passed|0 each|

Supplementary/focused reruns overlap coverage and are not added to those unique totals. The isolated 919 source-layout assertion passes separately on its original snapshot; the other 42 historical assignments retain earlier evidence and were not rerun as current Git assertions.

Frontend: fresh production build **`RXWDqhdXuOR9todMp9i-m`** completed, type checks exit 0, lint exit 0 with zero errors/five warnings. The new production-mode browser scenario passes with real signed authentication, four normal uploads/reviews/confirmations, genuine subtype evidence, initial recommendation, distinct bound alternative, exact history/readback/reload, wearer switch and cross-wearer404. No dependency override or SQL garment seeding is used in that smoke. One-worker backend and production Next used owned 8600/3600 listeners and disposable storage; both were stopped by held process handles afterward.

Existing teammate regression modules were included where available. The separate geometry environment passed all three crop/mask/colour cases (torch 2.15.0, torchvision 0.29.2, opencv-python 5.0.0.93, scikit-learn 1.9.1 and ultralytics 8.4.208). The detector is mocked; real-weight segmentation/VTOFF/VTON accuracy is unverified. A staged checkout tested with Windows `core.autocrlf=true` passes seven source/architecture checks, including exact 350 application/configuration and 422 preserved model/vendor hashes.

All failed attempts remain retained outside Git. The first backend command collected no tests due to a command argument error. The first focused run had 176 passes/3 failures: two new capability-fixture activation errors and one old source-layout assertion. The first broad run had 15,993 passes/34 failures/152 skips:25 missing-J15, those two fixture errors, that source-layout assertion, one missing canonical directory-layout check, two path-transport authority mismatches and three missing baseline-oracle environment inputs. The feature flag, finite transport proof, explicit oracle configuration and tracked empty-directory README placeholders address these causes; the original source-layout assertion executes on its original stage. Native affected shards were rerun. No old expected score, numerical label or policy was changed. The initially normalized staged checkout failed the exact-byte proof; Git index byte preservation was corrected before publication.

See [machine-readable results and per-module counts](INTEGRATION_VALIDATION_SUMMARY.json) and [complete integrated file inventory](STUDENT2_INTEGRATION_FILE_INVENTORY.json). Current functional readiness with the disclosed evidence/model limitations supports teammate testing. NFR-02 and full historical certification remain outstanding.
<!-- END_INTEGRATED_VALIDATION_RESULTS -->

To rerun the self-contained combined workflow against owned servers:

```powershell
cd frontend
$env:SW_INTEGRATION_URL = 'http://127.0.0.1:3600'
npx playwright test --config=playwright.integrated.config.ts
```

Chrome must be installed. The test creates its own disposable account, profiles and four garments through normal authenticated processing/review/confirmation APIs, signs in through the UI, obtains an initial recommendation and genuine alternative, reads/reloads history and switches wearer. Old phase-specific browser scripts remain external-fixture workflows; they are not the self-contained integration test and should not be pointed at a manually used database.

## NFR-02 failure and unresolved interruption

No optimization or new performance campaign was performed for this functional integration. The retained **controlled Phase A of 10 November 2026** remains a failure in the attempted scope and incomplete overall:

| Observation | Retained fact |
|---|---|
| Resource qualification | Passed the original three windows; CPU means 4.91%, 8.85%, 7.57%; available RAM minima 7.95–7.99 GiB; 30.015 seconds |
| Genuine parent setup | 700/700 passed |
| Timed attempts | 535/1,400; 534 correct completed results and one HTTP 500; 865 not run |
| Five-second bound | 184 correct responses exceeded it; maximum 24.1871656 seconds |
| Cells | 15 complete, one partial, 24 not reached; ten complete cells passed, five complete failed, partial failed |
| B20 | All eight completed cells passed |
| Measured B100 contextual cases | P1/C1 approximately 3.2 s; P2/C1 16–18 s; P1/C2 5.8–6.0 s; P2/C2 about 21 s, scenario-specific |
| Interrupted request | B100 female P2/C2 context alternative warm9, sample535: plain-text HTTP500 after 11.8440834 s; proxy `read ECONNRESET`; backend ended unexpectedly |

The backend exit value was retained as `1073807364`. Its termination initiator and root cause are **not established**. There was no successful recommendation or receipt for that failed request, and no hidden retry. It is not justified to call this a recommendation-engine exception or blame a particular application/user action from the exit value alone. Normal collector shutdown/native-exit/observer completion records were missing. Recovery did not invent them.

The final one-second resource sample did not confirm AC; 16 timing-span samples had less than 4 GiB available RAM. All 184 slow correct responses occurred before the first unconfirmed-AC sample. No sample was discarded. Background competition and intrinsic cost are not isolated by these observations. The original manual demo's data/source were preserved, but its listeners were absent at recovery: runtime continuity was not certified.

Ranking was the longest existing reported server span in the slow completed cases (for example, about 18.5 s ranking within about 21.3 s client response for a measured P2/C2 case, persistence about 1.17 s). These spans may overlap and do not form a complete decomposition. They identify a stage to investigate, **not a proven function-level hotspot**. There is no profiler evidence yet. A correct result over five seconds still fails NFR-02. Untimed functional correctness does not establish latency acceptance.

The **100-garment supported maximum remains distinct from the earlier, unrun 200-eligible-garment stress target**. Full Phase A, Phases B/C, and the stress target are not certified. The five-second requirement and all original resource thresholds remain unchanged.

## Historical limitations, retained evidence and next work

J15 still lacks its original public hash-certified source/input/control manifests and retained initial/alternative/negative exports: the earlier baseline had 25 native evidence-dependent failures and 152 unverified skips. The original J16 preparer/coherent fixture remains unavailable. The combined run's actual counts are reported above; none are presumed from that earlier baseline. No historical goldens, labels, source certificates or deadlines were regenerated or relaxed.

Retained owner evidence is outside Git in review directories named `runtime_isolation_correction_20261109`, `historical_authority_reconciliation_20261108`, `workload_applicability_correction_20261110`, `phase_a_controlled_retry_919_20261110`, and `full_isolated_integration_20261110`. The accepted untimed preflight has 153 current API passes. The controlled performance evidence seal is SHA256 `e139d1b51649b4cb611ddceef1e98d44ffc81f3b6c9a21df64e1652f62c61595`. These names identify owner-retained records, not public download URLs. Ask the owner for authorized evidence access; private full responses and large logs are deliberately excluded here.

Remaining work, in order:

1. Teammate/supervisor functional testing of the combined flows, including available real image/model workflows.
2. Investigate unexpected backend termination with process-lifetime evidence, crash/event logs and reproducible controls.
3. Separately authorized profiling of the slow ranking scenarios; distinguish acquisition, scoring, combinatorics, persistence and concurrent interference.
4. Scoped optimization only after a reviewed hypothesis, with exact behavioral/numerical equivalence tests.
5. Repeatable full NFR-02 evaluation with frozen source/workload/oracles, original resource gates and no discarded failures.
6. Final integrated regression/acceptance, plus authentic historical evidence recovery or an explicitly governed limitation decision.

Secrets, private databases, demo/benchmark records/media, tokens, virtual environments, node dependencies, generated build/runtime files, large diagnostic logs and machine-specific absolute paths are excluded. This document discloses outstanding work; it does not waive acceptance criteria.

Original-workspace preservation was rechecked against all 1,302 original tracked-file hashes and its unchanged clean main commit. Every original demo row, schema/configuration, 103 media files and 918 source inputs also match the previous retained final state. The original demo listeners remain absent; they were not restarted. The full Git bundle and both the 153-cell untimed and failed Phase A evidence seals remain verified outside Git.

An external publication helper initially failed to read UTF-8 under the Windows locale. Its retained failed attempt was corrected with explicit UTF-8; no application or test result changed.

The external inventory helper also corrected an abbreviated Git object-ID assumption before generating the final file list; its failed attempt is retained.

Git whitespace diagnostics retain existing trailing spaces/EOF whitespace in approved source inputs. Those bytes are preserved for source identity; they are cosmetic findings, not passing whitespace-check exits or functional failures. The newly adapted capability module retains identical test ASTs after removing surplus terminal blank lines.
