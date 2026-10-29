# Phase 5B: opt-in Homepage recommendation backend

## Requirements and boundary

Original report FR-HR-01–12, RN-11/12/16/23–26, sections 4.4.2/4.10.5 establish
current owned confirmed available garments, complete valid outfits, deduplication,
one random result, atomic recommendation/items, no NLP/chat, controlled failures
and no user refresh control. NFR-01 targets display within three seconds after
homepage loading in the defined baseline environment; backend timing alone does
not establish browser compliance.

Exact four compositions are approved Phase 3A implementation policy, not exact
fashion rules prescribed by the report. Homepage applies that structural policy
only: top+bottom, either with one outerwear; dress, optionally one outerwear.
No invented aesthetic hard constraints, style clash rule, preference query,
NLP, request score, Jaccard/holistic compatibility score or ranking is used.
Outfits are generated from individual wardrobe garments, without saved outfits.
Structural validity is not independently validated aesthetic compatibility.

## Composition and API

HomepageRecommendationService receives RecommendationEngine and an injected
HomepageRepository. The additive HomepageRepository port extends the existing
Phase 5A port with read-only find_homepage_submission and persist_homepage.
Existing persist/get signatures and returned records remain unchanged.
SqliteRecommendationRepository supplies both additive operations and reuses its
existing transaction implementation. persist_homepage returns (record,replayed),
with replay identity resolved under the write lock, including identical samples.

At startup SMART_WARDROBE_HOMEPAGE_ENABLED=true explicitly composes the service.
Default/absent/other values leave it disabled. Restart to change the flag. No
frontend integration or production enablement is performed by this phase.

POST /api/v1/recommendations/homepage requires existing authenticated context and:

```json
{"submission_key":"caller-generated-page-flow-uuid"}
```

Key grammar: 1–200 ASCII characters; first alphanumeric, remaining alphanumeric
or '.', '_', ':', '-'. No whitespace normalization, browser-supplied garments,
user IDs, requests or extra fields are accepted. The key represents one page
flow, not the user's entire account/session. Caller retains it across transport
retries and gives a new flow a new key. No frontend refresh control is introduced.

| HTTP | status | Meaning |
| --- | --- | --- |
| 201 | Selected | Newly committed single recommendation |
| 200 | Selected, replayed=true | Original durable result recovered |
| 200 | NoEligibleGarments | No strict/structurally supported garments |
| 200 | InsufficientStructure | Cannot fill a complete base |
| 200 | NoStructuralCandidates | Complete enumeration yielded no candidates |
| 409 | IdempotencyConflict | Existing key has another request fingerprint |
| 409 | WardrobeChanged | Selected evidence changed before commit |
| 503 | ProcessingFailure / Interrupted | No complete selection can be published |
| 503 | PersistenceFailure | Lookup/write failed; no uncommitted sample returned |
| 404 | IntegrationDisabled | Explicit integration flag is off |
| 401 | Existing authentication error | Missing/invalid credentials |
| 422 | Existing validation error | Invalid body/key or unexpected fields |

Success has complete=true, recommendation, replayed, currently_eligible and
diagnostic backend timings. A stored recommendation contains NULL chat and all
NULL scores. Provenance records actual structural version, uniform reservoir
method, candidate count and structural-only validity. No scores are fabricated.
Failures contain no provisional recommendation; complete=false. Completed
no-result outcomes have complete=true and candidate_count=0 but are not stored.

No change to existing Assistant POST, save route or visualisation. The existing
recommendation-list query gains only chat_id IS NOT NULL: chatless Homepage
records must not enter its old inner-chat reader and turn the legacy list into
a 404. Existing Assistant entries/shape stay unchanged. New Homepage results are
read through the Phase 5A reader. There is no new searchable history API.

## Uniform streaming selection and failure guarantees

ReservoirSelector retains one provisional candidate and an integer count. The
first candidate is selected; candidate k replaces it exactly when an injected
uniform random_below(k) returns zero. Production uses secrets.randbelow. A
candidate selected at step k survives with probability product(j=k+1..N)(1-1/j),
so final selection probability is (1/k)*(k/N)=1/N. This is uniform across distinct
valid outfit candidates, not across structural categories or individual garments.

The selector consumes the entire stream and checks terminal status, complete
flag and exact observed/declared candidate count. Safe close must also succeed.
Exceptions, interrupts, invalid random draws, inconsistent metadata and close
failures discard the provisional sample. No limits/truncation are introduced.
Sample memory is O(1); the existing engine additionally holds O(garment count)
wardrobe groups. It never stores an O(candidate count) list for selection.

## Retries, stale garments and transaction scope

Read-only lookup precedes retrieval/generation, comparing the exact Phase 5A
v1 fingerprint for operation homepage, request={} and original text=NULL. A
retry returns the original record without drawing again, even when the wardrobe
is now empty or garments are archived. currently_eligible=false and item flags
explicitly distinguish historical recovery from a newly current valid outfit;
no replacement garment is substituted. Read metadata/media visibility can change
while saved identity, roles, order and captured display remain historical.
currently_eligible reports Phase 1 garment membership, not a fresh outfit-level
structure/aesthetic evaluation after edits. Replayed results retain creation-time
validity provenance and must not be presented as newly generated current outfits.

Concurrent misses may both enumerate before one commits. This intentionally
does not hold a write lock during generation. Phase 5A's BEGIN IMMEDIATE and
scoped uniqueness serialize final writes; the losing request returns the durable
winner and replayed=true, even if both sampled the same outfit. No successful
record is created for an incomplete generation. A commit whose response is lost
is recovered on the next key lookup. Failed/no-result attempts do not reserve a
durable successful key and may be attempted again.

The existing write transaction covers idempotency resolution, strict current
Phase 1 revalidation, complete selected-snapshot equality, recommendation/items,
display snapshots, provenance and commit. A changed garment produces an explicit
WardrobeChanged outcome; it never silently rerolls. Full Phase 5A limitations
remain, including no PostgreSQL runtime writer and existing legacy-parent SQL
integrity limitations. New schema changes are not required in Phase 5B.

## Tests and benchmark methodology

Tests cover all four actual persisted structures/order, strict Phase 1 exclusion,
unknown categories, empty/insufficient/no-candidate streams, deterministic draws,
all 24 equiprobable draw paths for four candidates, and a seeded Pearson
uniformity sanity check (df=3, p=.001 critical value 16.266). These test sampling,
not fashion quality. Failure-after-sample, close/incomplete/count errors, stale
evidence, rollback, concurrency, conflicts, lost-response recovery, API auth,
default-off/opt-in composition and forbidden NLP/preference/scoring calls are
covered. Existing Phase 1–5A regressions are run separately with this selection.

benchmark_homepage_recommendation.py uses temporary actual SQLite databases with
synthetic confirmed garments, production secrets.randbelow and real atomic
persistence. It checks exhaustive expected counts, measures three trials per
size, and records source hashes/platform. Generation excludes fixture creation
and migrations. Per-next timing separates enumeration from residual sampling/
stream-control overhead; the latter includes instrumentation overhead. Write
timing separates lock/revalidation from writes/readback/commit. No HTTP/browser,
authentication, real CV/media inference or end-to-end NFR claim is included.

Existing strict save/visualisation reconciliation, review payload 422/409 and
single-outfit visualisation capability limits remain deferred. Approximate hex
matching stays disabled, suitability opt-in, experimental scores unactivated.
No Phase 5C/Assistant, Phase 5D/history or frontend work is included.

## Executed verification (2026-10-18)

Exact commands from backend:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 --with fastapi --with pillow --with numpy --with python-multipart python -B scripts/benchmark_homepage_recommendation.py --sizes 20 50 100 200 --repeats 3 --output runs/homepage/benchmark.v1.json
```

Final focused: 94 passed (48 Homepage + 46 persistence), one existing Starlette
deprecation warning, 20.90s. Final combined: 572 passed, 1 failed, same warning,
36.03s. Only failure is test_report_architecture.py:28 asserting the existing
ai-services directory must be absent. No deletion/restructure/assertion change
occurred. No new regression failure was observed. Earlier partial test runs and
the initial seeded-RNG benchmark are superseded by these final runs.

From repository root, git diff --check passed. Separate trailing-whitespace
inspection covered all eight new source/test/script/doc files. No frontend,
PostgreSQL deployment or real CV/VTON inference tests were performed; the
unrelated segmentation-geometry test module was not part of this regression
selection. Existing save/VTON contract tests were included without modifying
their algorithms or validation paths.

Benchmark artifact: backend/runs/homepage/benchmark.v1.json (generated and
Git-ignored). Independent component medians across three trials, seconds:

| Garments | Candidates | Total | Enumeration | Selection/control | Lock/revalidate | Write/readback/commit |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 198 | .028831 | .002476 | .000323 | .001285 | .020413 |
| 50 | 2,430 | .060048 | .030893 | .003789 | .001992 | .021056 |
| 100 | 17,710 | .275641 | .220661 | .027015 | .002284 | .022643 |
| 200 | 134,820 | 2.620645 | 2.310016 | .273332 | .005013 | .023782 |

Component medians need not sum to the total median; lookup/setup/other overhead
are separate in the artifact. At 200 garments total trials ranged 2.442–3.081s.
The near/exceeded-three-second backend timing leaves an unresolved NFR-01 risk;
it does not meet or prove the eventual browser display target. No optimisation,
candidate truncation or Phase 3B request-filtering speed-up is claimed.

Phase 5B backend status: PASS WITH LIMITATIONS, ready for owner review. Default
activation remains false and Phase 5C has not started.
