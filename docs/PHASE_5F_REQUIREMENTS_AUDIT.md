# Phase 5F-1 requirements audit

Source of truth: `RSW_ChongWeiPing_Project1 (1).pdf`, read from the original
Downloads file on 2026-10-18. PDF pages below are 1-based, including front matter;
the report's printed page number is PDF page minus 11. The FYP context/contracts
are implementation guidance, not substitutes for the original requirement text.
No production recommendation, frontend behaviour, saving, CV or VTON code is
changed in this verification phase.

## Classification and evidence limits

- **V — Fully implemented and verified** for the stated approved policy and
  executed synthetic/isolation workload; not a human fashion-quality claim.
- **I — Implemented but not independently verified** in the deployment/quality
  context specified in the row.
- **P — Partially implemented**, including report-defined capability gaps.
- **D — Unsupported or intentionally deferred**.
- **B — Blocked by another module**.
- **X — Inconsistent with the report**.

R = user's NLP/Recommendation responsibility; S = shared authentication/application
boundary; T = teammate-owned Digital Wardrobe/CV/visualisation. Passing a class's
unit tests alone is not used to certify an end-to-end requirement. Detailed
commands/results, latency evidence and remaining gates are in
`PHASE_5F_VERIFICATION.md`.

## Homepage: report PDF pages 169–170 (printed 158–159)

| Requirement | Meaning | Status / owner | Actual implementation and executed evidence |
| --- | --- | --- | --- |
| FR-HR-01 | Automatically start on authenticated homepage access | V / R,S | `frontend/components/HomepageRecommendation.tsx` effect → homepage POST; real-backend browser workflow and page-flow/reload test in `frontend/tests/recommendation.spec.ts`. |
| FR-HR-02 | Only current owned confirmed available garments | V / R,T boundary | `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py` joins processing item/job with strict owner/status; `test_confirmed_garment_snapshot.py`, `test_homepage_recommendation.py`, `test_outfit_assistant.py` exercise rejected/accepted/pending/NULL/missing/foreign/archived cases. |
| FR-HR-03 | Establish sufficient garment categories | V / R | `garment_retrieval_service.py`, `structural_policy.py`, `recommendation_engine.py`; executed `test_structural_candidates.py` empty/insufficient/unknown data cases. |
| FR-HR-04 | Generate combinations of eligible wardrobe garments | V / R | `candidate_generator.py` lazy product; independent expected-set tests and measured exhaustive candidate counts at 20/50/100/200 garments, without saved outfits. |
| FR-HR-05 | Exclude structure/mandatory compatibility violations | V for approved mandatory structure / R | `mandatory_rule_evaluator.py`, structure policy; all four supported structures tested. No unapproved fashion-clash rule is inferred. Broad aesthetic compatibility remains unvalidated (RN-17). |
| FR-HR-06 | Deduplicate candidates | V / R | Generator and immutable candidate identity; `test_structural_candidates.py` duplicates/order-independence/expected-set assertions. |
| FR-HR-07 | Randomly select one valid outfit | V / R | `reservoir_selector.py`; exact enumeration of equiprobable random paths, seeded statistical sanity check and no-provisional-result failure tests in `test_homepage_recommendation.py`. |
| FR-HR-08 | Display selected outfit | V / R | `RecommendationResult.tsx` ordered complete items; actual backend/browser workflow plus outerwear/missing-media fixture tests. |
| FR-HR-09 | No user refresh during current flow | V / R | No refresh recommendation control; browser checks no such button, same-key reload and genuinely new navigation key. Saved-outfit retry is a separate existing collection. |
| FR-HR-10 | Explain insufficient/no valid outfits | V / R | Service controlled statuses and `recommendation-messages.ts`; backend empty/insufficient tests and frontend no-result handling. |
| FR-HR-11 | Explain processing failure | V / R | Homepage service returns no incomplete recommendation; late-stream failure tests and browser ProcessingFailure test verify no saved substitute. |
| FR-HR-12 | No Homepage chat record | V / R | Homepage persistence has NULL chat; `test_homepage_recommendation.py`/`test_recommendation_persistence.py` inspect actual database rows. |

## Outfit Assistant: report PDF pages 171–172 (printed 160–161)

| Requirement | Meaning | Status / owner | Actual implementation and executed evidence |
| --- | --- | --- | --- |
| FR-OA-01 | Authenticated access | V for protected data/operations / S,R | Bearer API guards; browser real login and backend 401 tests. The route shell is public; no private recommendation/history is returned without authentication. |
| FR-OA-02 | Request interface and New Chat | V / R | `OutfitAssistant.tsx`; browser UI submission, read-only completion and New Chat tests. |
| FR-OA-03 | Start independent interaction | V / R | UUID per intentional New Chat; browser distinct-key assertion; backend independent-chat row-count tests. Draft creation does not prematurely create a completed database chat. |
| FR-OA-04 | One natural-language request per chat | V / R | Submitted text/key lock, synchronous busy guard and server operation-scoped idempotency; duplicate-click/retry/remount browser tests and concurrent backend submissions. |
| FR-OA-05 | Reject empty/whitespace input | V / R | UI prevents whitespace submission; NLP preprocessor/API service reject empty input; `test_nlp_interpreter.py`, `test_outfit_assistant.py`. |
| FR-OA-06 | Process through NLP and recommendation | P / R | Real `OutfitAssistantService` composes interpreter → mandatory evaluation → scoring → atomic write, verified by API/browser and independent arithmetic tests. Default downstream occasion/formality policy and general hex evidence remain unavailable; compatibility deferred. |
| FR-OA-07 | Exactly one result on success | V / R | Complete-stream ranker and service; real backend/browser shows one result, exhaustive scored-count and independent winner tests. |
| FR-OA-08 | Show original request with recommendation | V / R | Locked original text and historical restoration; browser and stored-text/whitespace preservation tests. |
| FR-OA-09 | Explain unsupported input | V / R | Conservative NLP outcome before retrieval; browser unsupported test and backend no-completed-history assertions. |
| FR-OA-10 | Explain no suitable outfit | V / R | NoMatchingCandidates versus InsufficientEvidence/PolicyUnavailable; three-state backend tests and browser controlled outcomes. This is not proof of broad suitability support. |
| FR-OA-11 | Explain interpretation/retrieval/generation error | V / R | Controlled failures; late-stream/close-failure tests discard provisional winner; browser persistence failure and transport retry tests. |
| FR-OA-12 | Completed chat cannot accept another request | V / R | Read-only original text, no textbox and explicit New Chat; completed detail is GET-only; browser completion/history tests. |

## Chat history: report PDF pages 173–175 (printed 162–164)

| Requirement | Meaning | Status / owner | Actual implementation and executed evidence |
| --- | --- | --- | --- |
| FR-CH-01 | Completed history only after successful recommendation | V / R | Repository single transaction; unsupported/no-result/late-failure tests assert zero completed chat rows. |
| FR-CH-02 | Link request, recommendation, user, time and items | V / R | Actual schema/atomic inserts and item rows; `test_recommendation_persistence.py` and `test_chat_history.py` compare restored original values. |
| FR-CH-03 | Store request/recommendation atomically | V on SQLite / R | `BEGIN IMMEDIATE`, commit after all writes; failure injection at revalidation/chat/recommendation/item/snapshot/metadata/submission/before_commit. PostgreSQL unverified. |
| FR-CH-04 | Do not present partial records as completed | V / R | History coherence predicate rejects missing/incoherent items, duplicate recommendations and corrupt metadata; executed parametrized history tests. |
| FR-CH-05 | Completed saved chat is read-only | V / R | Completed status, history read-only connection, GET-only API and no editing UI; backend forbidden mutation and browser tests. |
| FR-CH-06 | No additional request in completed chat | V / R | No append endpoint; same key/different text conflicts; read-only detail cannot submit; browser asserts no textbox/generation call. |
| FR-CH-07 | Prevent duplicate completed chats | V on tested SQLite connections / R | Unique user/operation/key, fingerprint under write lock; concurrent retry/conflict/rollback tests; browser same-key lost-response recovery. |
| FR-CH-08 | Search own completed requests | V / R | `chat_history_query_adapter.py` user-bound literal casefold search; real SQL/API tests and browser form. |
| FR-CH-09 | Return only owner's history | V / R,S | User-bound SQL/coherent joins; cross-user API 404 and real-browser backend check. |
| FR-CH-10 | Empty search browses all completed personal records | V / R | Cursor pagination over all eligible records, total count, empty-search SQL tests and browser load-more. All means all pages, not one unlimited response. |
| FR-CH-11 | Show no search results | V / R | Empty state in history page and no-match backend assertions; no generation on read. |
| FR-CH-12 | Open previous completed chat | V / R | `/history/[chat_id]` GET-only detail, actual persisted backend chat browser flow. |
| FR-CH-13 | Display saved request and historical recommendation | V for original text/items / R | Immutable stored display snapshots, interpretation and ordered garment cards survive archival. Scores/provenance are restored by API and verified, but full score/provenance diagnostics are NOT displayed by the current UI (additional Phase 5F check gap, not an invented original display requirement). |
| FR-CH-14 | Prevent cross-user detail access | V / R,S | Actual owner-bound lookup, generic missing/foreign 404, protected-media owner checks; backend tests and actual second-user request. |
| FR-CH-15 | Indicate unavailable historical garment | V / R,T boundary | Snapshot retained; current strict eligibility flag and inaccessible media suppressed; browser archive/read-only card, foreign/missing/unconfirmed backend cases. |
| FR-CH-16 | Explain failed history save | V / R | PersistenceFailure with no partial success; transaction rollback and frontend controlled-failure tests. Lost-response retry resolves committed submission rather than duplicating. |

## Recommendation: report PDF pages 188–189; algorithm pages 285–288

| Requirement | Meaning | Status / owner | Actual implementation and executed evidence |
| --- | --- | --- | --- |
| RN-12 | Exclude missing required evidence / mandatory violations | V within approved enabled policies / R | Retrieval rejects unsupported structural data; request evaluator unknown is never Pass. Generic requests do not invent a requirement for attributes they do not use. Unknown evidence, malformed fields and complete-stream tests executed. |
| RN-13 | Filter by extracted structured conditions | P / R | Collective categories, global primary colours, base-style evidence implemented and tested. Named aliases/exact anchors only; general hex approximate evidence disabled. Occasion/formality default PolicyUnavailable; opt-in declarations cover only approved values. |
| RN-14 | Candidates only from eligible retrieved garments | V / R,T boundary | Contract-injected query, deterministic generator, strict eligibility integration tests and measured full candidate counts. No saved outfits needed. |
| RN-15 | Reject mandatory request failure before scoring | V / R | Three-state evaluator plus independent scoring gate; tests forbid scoring Fail/Unknown and reject tampered inputs. |
| RN-16 | Reject structure failures before scoring | V / R | Approved 13-category roles and four compositions, immutable verified input; independent expected-set and structure mapping tests. |
| RN-17 | Documented request, compatibility, preference scores | P / R | Exact normalized R/P implemented and tested. Live profile weights 0.70/0/0.30, C unavailable/NULL. Three-term arithmetic infrastructure exists, but a meaningful live compatibility component is intentionally deferred. This does not fully satisfy the report's three-component evaluation intent. |
| RN-18 | Rank valid candidates by scores | V within current profile / R | Streaming ranker compares exact weighted values without candidate truncation; independent arithmetic/order tests and exhaustive count assertion. Quality of that ordering is not independently validated. |
| RN-19 | Select highest-ranked valid outfit | V within current profile / R | Top-one stream winner only after completion; independently calculated expected winner, late/close failure tests and real service. |
| RN-20 | Deterministic tie breaking | V / R | `candidate_ranker.py`: total, R, C, P, stable key; each tie stage and input-order independence tested using exact fractions. |
| RN-21 | Exactly one result per successful NLP request | V / R | Ranking result, atomic one-chat/one-recommendation relation and UI single card. |
| RN-22 | No result if no candidate satisfies mandatory rules | V / R | No matching, insufficient evidence, no structural candidates and unavailable policy distinguished; no invalid fallback; backend/browser evidence. |
| RN-23 | No fabricated garments/attributes/availability | V / R,T boundary | Snapshot projection/immutable collection tests, real strict query, transaction-bound comparison and historical display tests; synthetic test records are explicitly labelled fixtures. |

## Non-functional: report PDF page 180 (printed 169)

| Requirement | Status / owner | Evidence and acceptance limits |
| --- | --- | --- |
| NFR-01: display within 3 seconds after homepage load | V for observed baseline; I for final deployment acceptance / R,S | All five production-browser trials per size pass; 200 median 2.632s, max 2.809s. HTTP p95 3.333s warns of low headroom. Not a general deployment claim. |
| NFR-02: response within 5 seconds | X at 200 garments / R,S | 200 HTTP median 21.823s, browser median 21.710s; every 200 trial fails. Smaller tested wardrobes pass. No candidate cap permitted. |
| NFR-03: search within 2 seconds at defined maximum history | I for final maximum-workload acceptance / R,S | Tested baseline is 1,000 personal seeded chats plus 3,000 other-user chats, 100 matching, limit 50, plus measured successful interactions. This is a documented experiment, not an approved final maximum. |
| NFR-04: controlled failures without losing responsive session | V for exercised failure paths; I for sustained concurrent load / R,S | NLP/retrieval/storage/stream errors, browser recovery/New Chat and authentication error states; no stress/soak or external service failure coverage claimed. |
| NFR-05: preserve wardrobe/history on failed NLP processing | V on tested SQLite / R,T boundary | Full rollback injection, stale selected evidence rejection, no-history unsupported/no-result assertions, foreign/archived guards. No PostgreSQL failure/recovery test in this phase. |

## Cross-module gaps and source reconciliation

| Capability | Classification | Finding / required agreement |
| --- | --- | --- |
| Normal browser upload → confirmation → recommendation | B / T | Actual review submits unsupported neckline/sleeve_length keys (even null); backend rejects 422, subsequent direct confirmation 409. Pre-confirmed fixtures do not close this journey. |
| Recommendation-source save/visualisation strict eligibility | P / T,R coordination | Save checks owned/available but not processing confirmation/job owner. Visualisation also accepts accepted or unlinked records and does not verify processing-job ownership. New audit tests reproduce the gap; no algorithms changed. |
| Save leaves historical recommendation unchanged | X / T,R coordination | Existing `save_as_outfit` changes Recommendation.status to saved; report §4.8.2 describes saving a separate Outfit without changing Recommendation. Existing history deliberately still reads saved records. |
| History save/visualisation actions | D / R,T coordination | Read-only frontend intentionally withholds actions; report's history use-case planned revalidated actions. Separate approval required; cannot claim this integration complete. |
| Outfit aesthetic quality / compatibility | D / R | No approved real holistic references; experimental Jaccard not used live. Structural/request correctness is not fashion-compatibility validation. |
| Named/hex colour suitability | P / R,T coordination | Exact approved anchors/names work; approximate Oklab remains disabled pending reviewed calibration/validation. CV empty-pixel black ambiguity remains. |
| Occasion/formality | P / R,T coordination | Declaration-based opt-in only, no inferred appropriateness; exercise/formal unavailable; manual technical tags not final user experience. |
| PostgreSQL deployment | I / shared | SQLite transactions verified; PostgreSQL SQL/docs exist but neither deployment data nor PostgreSQL concurrency/migration execution verified here. |
| Disabled integration API | V for explicit integrated-only guard; deliberate legacy compatibility / R | `?pipeline=integrated` is fail-closed; unqualified default-off POST deliberately still invokes legacy placeholder. Do not describe this guard as removal of every legacy route. |
| Independent NLP/relevance evaluation | I / R | Fixed 120-case synthetic evaluation can verify its RN-27 metric only. No independently collected/reviewed human dataset or fashion-quality result is supplied. |

## Minimum additional quality evidence (recommendation, not report constants)

Collect a held-out set of real English requests independently labelled for intent,
the five fields, representability/unsupported status and feasible/no-feasible
wardrobe outcome. Freeze it before rule changes and report supplied-field metrics
as well as all-field exact match. Preserve RN-27's >=80% criterion; do not add a
new mandatory threshold. Existing synthetic perfect scores are not independent
language generalization evidence.

For recommendation relevance, independently review examples of all four outfit
structures, mixed styles, missing/malformed evidence, preference conflicts and
unsupported suitability/colour cases. Record each review and disagreement;
separate structural correctness from aesthetic judgment. A proposed small pilot
of 10 held-out outfits per structure, with two independent reviewers and
adjudication, can expose major rubric problems; it is not a statistically validated
accuracy guarantee or an original-report minimum. The reviewed-reference policy
also needs a separate approved development/reference set; validation outfits must
not become lookup references or tuning data. No labels/ratings are fabricated.
