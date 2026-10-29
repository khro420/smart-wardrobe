# Phase 5D: completed, read-only chat history backend

## Authority, audit and scope

Original report FR-CH-01–16, sections 4.4.2, 4.8.2, 4.11 and the SW_UC08
history flow establish private completed single-request interactions, search,
restoration, stale-garment indication and no subsequent messages. Phase 5D adds
only retrieval/search: completed creation remains Phase 5A/5C; Homepage remains
Phase 5B. Literal matching, cursor format and page sizes below are implementation
policies, not report-defined constants. No frontend or recommendation optimisation
is included.

Runtime schema/code audit confirmed nlp_chats stores one request, not messages.
recommendations.chat_id is nullable; Phase 5A enforces unique non-null associations.
Existing successful statuses are available/saved, with types assistant (Phase 5C)
and wardrobe_outfit (legacy). Legacy create stores keyword entities and floating
scores without snapshots/exact metadata; legacy save changes status to saved.
These records must not disappear merely because save was used. No actual
deployment SQLite database or database-location environment override was available;
compatibility is tested against representative populated temporary databases.

## Eligibility and API

Authenticated GET /api/v1/chats?search=...&limit=50&cursor=... returns summaries.
GET /api/v1/chats/{chat_id} restores one interaction. No mutation/message/generation
route is added. Existing endpoints and Phase 5A–5C write/idempotency behaviour
are unchanged. History requires no new integration flag; Homepage/Assistant
generation flags remain independent and default-off.

Eligible rows require owned completed chat, non-null completed_at, nonblank
original text, exactly one same-owner recommendation in the existing known
successful available/saved states and assistant/wardrobe_outfit types, and at
least one recorded item. Pending/failed/incomplete/orphan/ambiguous associations
are excluded. Unknown future recommendation status/type semantics are not
invented here. chatless Homepage results cannot enter the join. Current garment
availability is deliberately not a history eligibility predicate.

The original legacy generation cannot be retroactively certified Phase 5C-valid.
Completed legacy lifecycle/ownership is sufficient for preservation; absent
policy/score evidence remains absent rather than falsely asserting modern
validation or aesthetic quality. No history is fabricated for failed requests.

List response:

```json
{"status":"CompletedChats","items":[{"chat_id":"...","request_text":"...","created_at":"...","completed_at":"...","recommendation_id":"...","recommendation_status":"saved","read_only":true}],"total":1,"limit":50,"next_cursor":null,"read_only":true}
```

An empty page uses status=NoResults with items=[], total and next_cursor. A
foreign/missing/ineligible chat ID returns the same 404 NotFound body. Invalid
queries/cursors return 422 InvalidInput. Operational failures return 503
HistoryUnavailable without internal details. Existing bearer authentication gives
401 for missing/invalid credentials. No foreign identifiers or counts are returned.

## Literal matching and explicit pagination

Search is case-insensitive literal substring matching against original request
text only. Unicode casefold is applied to both text and term using a deterministic
SQLite function, not limited to SQLite's ASCII lower(). '%', '_' and the chosen
escape character '!' are escaped before parameterized LIKE ... ESCAPE '!'.
Backslash and quotes remain literal. Empty string matches all eligible personal
records; whitespace is literal and is not silently trimmed. Maximum term length
is 500 characters.

Ordering is created_at DESC, chat ID ASC. Existing timestamps are stored ISO
strings; no timestamp rewriting is performed. Default page size 50, allowed 1–100.
This is explicit response pagination, not silent history truncation: total and
next_cursor expose remaining records, and every matching item can be traversed.

Keyset cursors carry an initial upper anchor and last-returned key. HMAC-SHA256
signing reuses the existing configured authentication secret. Cursors are versioned
and bound to authenticated user and exact search string; invalid/tampered/reused
foreign-term cursors are rejected. SQL still independently enforces user scope;
a cursor is not authorization. Rotating the secret invalidates existing cursors.

Normal newer inserts do not shift remaining pages. One read transaction keeps
count/page internally consistent. Separate HTTP requests are not one long-lived
database snapshot: deletion, lifecycle changes or backdated inserts can affect
later pages/totals. No transaction is retained between pages. The anchored total
excludes new records above the first-page boundary; a fresh search includes them.

## Restoration and media privacy

Detail returns original text, stored interpreted intent/entities, structured
request when the persisted object has the recognized six-field shape, timestamps,
and the original recommendation. No NLP mapping or semantic reinterpretation is
performed. Legacy keyword JSON is preserved in interpreted_entities while
structured_request remains null. Missing/malformed interpretation is explicitly
indicated; unavailable fields are never invented.

The query adapter reuses Phase 5A's protected read-model helper on its own
read-only connection. It restores stored IDs, roles, ordering, captured name/
category, available score columns, exact metadata and policy provenance. Legacy
items lacking snapshots have snapshot_available=false and null display fields;
missing exact fractions/provenance remain null. Stored float scores are historical
values, not endorsed compatibility measurements. Corrupt snapshot/score metadata
causes controlled operational failure rather than invented data.

Current Phase 1 membership is reported separately as currently_eligible. It is
not a fresh historical-outfit structure/request/aesthetic evaluation. Archived,
missing, foreign or no-longer-confirmed garments retain historical item identities
and captured display text. No current foreign garment attributes are copied.

Historical media IDs additionally require actual same-owner available media_assets
records and current garment eligibility. Otherwise IDs are withheld and
historical_media_accessible=false. Storage keys/filesystem paths are never exposed;
normal protected-media authorization still applies. An accessible old media ID
represents the captured historical image, not an automatic current image substitute.

read_only=true and requires_action_revalidation=true do not authorize saving or
VTON. Those actions are separate; no action/capability is enabled by this API.
Their existing strict-eligibility inconsistencies remain deferred for teammate
coordination, as do the garment-review neckline/sleeve_length 422/409 issue and
the independent-outfit versus recommendation.status=saved discrepancy.

## Read-only enforcement and architecture

ChatHistoryService consumes the ChatHistoryQuery port. Infrastructure owns all
SQL; routes obtain authenticated identity and the composed service. No NLP,
scorer, ranker, generation, wardrobe writer, save or VTON operation is invoked.

SQLite connections use URI mode=ro (no creation/writes), PRAGMA query_only=ON
and a read transaction. Rollback/close end that read snapshot. Tests attempt a
DELETE and compare full database dumps before/after list/detail. Standard bearer
authentication does not write. Existing development X-User-Id authentication may
ensure a development account through its pre-existing hook; it is not a production
read-only guarantee and was not used for no-write API assertions.

No schema migration or shared persistence changes are needed. main.py registers
the two GET routes; workflow_runtime.py supplies the query/service. Existing
Phase 5A methods and Homepage/Assistant composition remain unchanged.

## Performance scope and retained issues

The reproducible benchmark seeds synthetic completed legacy histories at 1,000
and 10,000 personal records, plus an equal unrelated-user population. It performs
three trials each for empty, normal, literal '%'/'_', Unicode and no-match terms
with a 50-item page. Query-boundary timing includes connection, SQL/count and
pagination; TestClient API timing additionally includes authentication and response
processing. It is not pure SQL-engine timing or real-network/browser latency.
Fixture creation, migrations and application startup are excluded.

NFR-03 targets two-second search under the defined maximum workload. These are
representative datasets, not an approved maximum-history workload specification;
fast backend timings alone do not demonstrate full browser/NFR compliance.

Assistant performance remains unresolved and unchanged: 200 garments, 134,820
candidates, approximately 22.53s instrumented backend run; NFR-02 is not met for
that workload. No Assistant optimisation, candidate truncation or scoring-policy
activation is performed in Phase 5D. PostgreSQL history execution and frontend
integration require later verification. Phase 5E has not started.

## Executed verification (2026-10-18)

Exact commands from backend:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_chat_history.py tests/test_outfit_assistant.py tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_chat_history.py tests/test_outfit_assistant.py tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
uv run --no-project --python 3.12 --with fastapi --with httpx --with pillow --with numpy --with python-multipart python -B scripts/benchmark_chat_history.py --sizes 1000 10000 --repeats 3 --output runs/chat_history/benchmark.v1.json
```

Final focused: 153 passed (24 history, 35 Assistant, 48 Homepage, 46 persistence),
19.07s. Combined: 631 passed, 1 failed, 40.07s. Both have one existing Starlette
TestClient deprecation warning. Only failure: test_report_architecture.py:28
expects existing ai-services to be absent. No folders/assertions were altered.

Tests cover literal special/Unicode/injection-like terms, empty searches, stored
completion/ownership, Homepage exclusion, saved legacy records, malformed or
missing metadata, media privacy, missing/foreign/archived garments, original roles
and ordering, actual Phase 5C restoration, stable cursor traversal/newer inserts,
tampered/foreign/search-mismatched cursors, API auth/405/404/422 responses, actual
composition, read-only DELETE rejection and whole-database before/after equality.

git diff --check passed from repository root, with separate trailing-whitespace
inspection of all nine new source/test/script/doc files. No browser E2E,
PostgreSQL deployment, actual deployment-data audit, real CV/VTON inference or
unrelated segmentation-geometry test was run. Existing Phase 1–5C, wardrobe/save
and visualisation contracts are included in the selected regressions.

Generated Git-ignored benchmark artifact: backend/runs/chat_history/benchmark.v1.json.
Final medians across three trials, 50-item pages (milliseconds):

| Personal + other-user chats | Search | Query boundary | API |
| --- | --- | --- | --- |
| 1,000 + 1,000 | empty | 8.693 | 13.699 |
| 1,000 + 1,000 | CAMPUS | 8.311 | 10.699 |
| 10,000 + 10,000 | empty | 87.280 | 90.470 |
| 10,000 + 10,000 | CAMPUS | 62.533 | 66.979 |
| 10,000 + 10,000 | literal % | 63.063 | 69.703 |
| 10,000 + 10,000 | literal _ | 75.252 | 79.327 |
| 10,000 + 10,000 | café | 68.703 | 67.106 |
| 10,000 + 10,000 | no match | 60.807 | 66.268 |

Maximum observed API trial: .130268s. Direct and API medians come from independent
reads with scheduling/cache variation, so API medians need not always exceed the
direct-query median. These measurements are below two seconds for this workload;
they do not prove formal NFR-03/browser compliance at an approved maximum workload.
No change or improvement to the separate 22.53s Assistant benchmark is claimed.

Phase 5D status: PASS WITH LIMITATIONS, ready for owner review. Phase 5E has not
started and no frontend or generation flag was activated.
