# Phase 5C: opt-in Outfit Assistant backend

## Authority and scope

Report FR-OA-01–12, FR-CH-01–07/13–16 and sections 4.4.3, 4.8.2 and 4.10.4
define single-request interpretation, mandatory-before-scoring, one completed
winner, atomic user-owned history and retry protection. Section 4.10.5 separates
Homepage random selection from Assistant ranking. Phase 5C wires existing
algorithms; it does not change Phase 1–5B contracts, garment/CV/VTON algorithms,
saving, frontend or searchable history. Exact weights, declaration annotations
and deterministic English rules are previously approved implementation policies,
not numerical constants or complete fashion rules specified by the report.

## Explicit activation and HTTP contract

SMART_WARDROBE_ASSISTANT_ENABLED=true at startup composes OutfitAssistantService.
Default is false. Restart after changing flags. No .env or frontend was enabled.
Disabled mode preserves the old Assistant service for compatibility testing;
its placeholder interpretation, structure heuristic and artificial scores are
not claimed compliant with the integrated FYP design.

POST /api/v1/recommendations uses the existing authenticated user dependency.
Enabled request body:

```json
{"request_text":"Suggest an outfit with vintage style","submission_key":"new-interaction-uuid"}
```

Original text is 1–500 characters, nonblank. Key is required when enabled:
1–200 ASCII characters, first alphanumeric, rest alphanumeric or '.', '_', ':',
'-'. Keys are caller-generated per intentional interaction, reused for retries.
Enabled mode rejects extra fields (including chat_id/user_id/garment_ids).
Disabled mode still accepts the old request_text-only body and ignores other
legacy extra fields; submission_key is optional in the shared boundary model.
There is no follow-up route, existing-chat mutation or multi-message model.

New successes retain legacy top-level recommendation fields, status=available
(or persisted current status on replay), items and numerical applicable scores.
outcome=Selected, complete, replayed, recommendation, timings, provenance and
score_metadata are additive. Numerical compatibility remains NULL, not measured
zero. The service's internal status is Selected; HTTP maps that back to the
legacy recommendation status and exposes the machine outcome separately.

| HTTP | outcome/status | Meaning |
| --- | --- | --- |
| 201 | Selected | New complete, atomically persisted interaction |
| 200 | Selected, replayed=true | Original committed interaction recovered |
| 200 | NoEligibleGarments / InsufficientStructure / NoStructuralCandidates | No complete input/candidate |
| 200 | NoMatchingCandidates / InsufficientEvidence | Complete mandatory search without a passing outfit |
| 422 | InvalidInput / UnsupportedRequest / PolicyUnavailable | Invalid, unrepresentable or unavailable request |
| 422 | InvalidPreferenceData / ProfileUnavailable | Cannot safely apply configured scoring inputs/profile |
| 409 | IdempotencyConflict / WardrobeChanged | Changed payload or stale selected evidence |
| 503 | ProcessingFailure / ProcessingError / Interrupted / InvalidScoringInput / PersistenceFailure | No certifiable completed result |
| 401 | Existing authentication response | Missing or invalid credentials |

Framework body errors use existing structured 422 validation details. Enabled
failures never call the legacy heuristic. Completed no-result outcomes may have
complete=true for the completed search, but do not create completed chats.

## Interpretation, mandatory rules and ranking

Flow: authenticated text -> early durable replay lookup -> existing NLPInterpreter
-> immutable StructuredOutfitRequest -> existing RequestCandidateEngine ->
RecommendationScorer -> strict atomic Phase 5A persistence. No direct call passes
request fields to Phase 3A's guarded structural-only NLP operation.

The five supported fields retain exact Phase 2 semantics. Categories/groups are
collective constraints; colours are global positive current-primary evidence;
style needs positive base-garment evidence. Unknown/malformed evidence is not a
positive match; definite failure wins. Unrepresentable garment/colour bindings,
negation, alternatives and unsupported conditions return UnsupportedRequest.
No generic fallback, invented attribute or clarification turn is added.

Default RequestConstraintEvaluator returns PolicyUnavailable for occasion and
formality. SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED=true is a separate explicit
opt-in, effective only when Assistant integration is enabled. It injects the
existing SuitabilityRequestEvaluator, requiring owner declarations on every
constituent including outerwear. Exercise/formal remain unavailable. Approximate
hex classifications stay disabled; unknown primary hex cannot satisfy mandatory
colour constraints. Suitability declarations are not independently proven fashion
appropriateness. No saved outfits are needed for any of the four structures.

Only compatibility_deferred is requested, with exact weights (.70,0,.30).
The service additionally checks the returned profile, weights and Unavailable
compatibility state before persistence. Existing request/preference formulas,
eligibility gate, exact Fraction arithmetic and total/R/C/P/stable-key tie order
remain unchanged. No Jaccard or holistic scorer is activated. A generic request
without supported preferences yields zero positive contributions and stable-ID
tie-breaking; this is not superior-fashion-quality evidence. Deferred C is an
interim functional profile, not full three-component quality validation.

The scorer exhausts and validates the full stream, retains only one provisional
best, and rejects partial/close-failed/interrupted searches. Only a complete
Selected outcome with a winner and positive scored count reaches the writer.
No ranking algorithm is reimplemented and no candidate collection is truncated.
CapturedCandidateEngine only observes the actual session for provenance; it does
not evaluate or alter candidates.

## Preference consistency

Each interaction wraps the existing ActivePreferenceQuery in a new
CapturedPreferenceQuery. One user-scoped read returns immutable PreferenceSnapshot
rows from the existing SQLite read transaction. Those exact rows drive existing
normalization/scoring and are copied to provenance with a SHA-256 digest. The
wrapper rejects repeated reads, avoiding inconsistent values within one ranking.

Policy is stable-at-preference-read, NOT commit-time freshness. Preferences can
change afterward; the current recommendation deliberately retains its captured
snapshot rather than reranking or claiming it reflects newer preferences.
There is no new preference revision field, migration or commit-time revision
check. SQL-backed tests edit preferences after the read and prove the stored
score/provenance retain the original values. Unsupported prose style_note remains
diagnosed under Phase 4A; it is not keyword-mined into preferences.

## Storage and idempotency

AssistantRepository adds find_assistant_submission/persist_assistant to the
existing repository boundary. Existing Phase 5A persist/get and Homepage methods
remain unchanged. Storage and schema are reused, not duplicated.

Fingerprint v1 remains SHA-256 of canonical sorted JSON containing operation,
actual structured request JSON and exact original request text. The original
text is not trimmed for storage/fingerprinting: changed whitespace/text under the
same key is a conflict even when NLP would interpret it identically. Early replay
looks up the stored structured payload and combines it with incoming original
text to verify that fingerprint, without rerunning NLP under a newer vocabulary.
This is safe because the enabled request has only original text and key as
inputs; policy changes do not reinterpret an already committed interaction.

Scope remains (authenticated user, assistant operation, submission key). New keys
permit identical text as independent chats. Concurrent misses may rank separately
outside transactions, but BEGIN IMMEDIATE resolves replay and serializes the
final strict snapshot comparison plus chat/recommendation/items/metadata/key
insertion. One committed chat/recommendation wins; losers receive its result.
Lost responses recover through early lookup. Archived garments do not trigger a
reroll: historical snapshots/availability are returned. Creation-time validity
is not a fresh assertion about an edited historical outfit.

The writer revalidates strict ownership/availability/confirmed processing-job
provenance and all projected selected attributes in the same write transaction.
WardrobeChanged is explicit. All write-stage failures roll back. Original text,
actual structured fields, exact scores/availability/weights, mandatory evaluation,
actual evaluator/structural/scoring/vocabulary versions and captured preferences
are stored atomically with historical item snapshots. No transaction spans NLP,
enumeration, ranking or VTON. No unsuccessful interaction is presented as a
completed chat. A commit whose response is lost may already exist; retry recovers
it rather than creating duplicate history.

## Boundaries and remaining work

No searchable chat routes or frontend changes are included. Frontend integration
must supply stable per-interaction keys, handle outcomes/NULL compatibility,
offer New Chat and keep completed interactions read-only. Existing live history
readers retain legacy semantics; the new persistence reader retains snapshots.
The review payload neckline/sleeve_length 422/409 and strict save/visualisation
eligibility reconciliation remain deferred for teammate approval. No PostgreSQL
runtime deployment, independent aesthetic quality or browser-level completion is
claimed. The known ai-services architecture assertion remains separate.

The benchmark uses synthetic reviewed-state SQLite data, all garments tagged
vintage, a real supported vintage-style request and no stored preferences. It
instruments actual NLP, request/gate checks, exact scoring/ranking and commit.
One trial per size is observational, not a latency distribution or formal quality
evaluation. Ranking timing includes several separately reported component times;
they overlap and must not be summed again. Timer overhead, no HTTP/browser,
fixture/migration exclusion and workload simplicity limit generalization.
NFR-02's five-second response target remains the eventual target; no browser
compliance follows from these backend measurements. No optimisations are included.

## Executed verification (2026-10-18)

From backend, exact commands:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_outfit_assistant.py tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_outfit_assistant.py tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 --with fastapi --with pillow --with numpy --with python-multipart python -B scripts/benchmark_outfit_assistant.py --sizes 20 50 100 200 --output runs/assistant/benchmark.v1.json
```

Focused: 129 passed (35 Assistant + 48 Homepage + 46 persistence), 14.16s.
Combined: 607 passed, 1 failed, 38.94s. Both have one existing Starlette TestClient
deprecation warning. Only combined failure: test_report_architecture.py:28
expects the existing ai-services directory to be absent. No folders/assertions
were deleted/restructured. Initial combined-request fixture used an unsupported
colour/category clause; only the fixture wording was corrected to approved global
colour syntax. No interpreter rules were changed to make that test pass.

Tests exercise real five-field interpretation with explicit suitability, all four
structures, mandatory failures before scoring, malformed/unknown evidence,
strict eligibility, independent .70R+.30P arithmetic and stable ties, no-history
outcomes, concurrent/lost-response retries, original text conflicts, preference
edits after capture, stale garment rollback, provisional-stream failure,
interruption/incomplete/close failure, API ownership/no fallback, and actual
default-off/opt-in composition with default and explicitly enabled suitability.

git diff --check passed from repository root. Separate whitespace inspection
covered seven new source/test/script/doc files. PostgreSQL execution, deployment
data audit, browser E2E, real CV/VTON inference and unrelated segmentation-geometry
tests were not executed. Existing wardrobe/save/visualisation contracts were
included in regressions without modifying their algorithms or validation paths.

Generated Git-ignored artifact: backend/runs/assistant/benchmark.v1.json.
Final instrumented single-trial totals:

| Garments | Candidates fully scored | Total seconds | Ranking seconds |
| --- | --- | --- | --- |
| 20 | 198 | .047736 | .033792 |
| 50 | 2,430 | .300122 | .289657 |
| 100 | 17,710 | 2.015301 | 2.000948 |
| 200 | 134,820 | 22.531149 | 22.510741 |

At 200 garments: NLP .000503s; retrieval .006055s; candidate construction
2.589664s; mandatory evaluation including gate recheck 3.854306s; request scoring
4.215206s; preference scoring .699867s; deferred compatibility overhead .742586s;
lock/revalidation .005872s; writes/readback/commit .011052s. Ranking additionally
includes exact arithmetic, immutable validation, stream bookkeeping and tie
comparison. Component metrics overlap the ranking total and are not a complete
additive profiler decomposition. Earlier measurements are superseded by this
final source-hashed run. NFR-02 is not met for this 200-garment workload; smaller
backend measurements do not prove end-to-end browser compliance.

Functional Phase 5C status: PASS WITH LIMITATIONS, ready for owner review with
the explicit performance failure and deferred compatibility quality retained.
No integration flag was enabled in deployment; Phase 5D has not started.
