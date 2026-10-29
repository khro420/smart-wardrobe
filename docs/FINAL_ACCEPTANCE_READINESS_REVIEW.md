# Phase 5F-2E-3I: final functional requirements and NFR acceptance readiness

Date: 2026-10-22 (Asia/Kuala_Lumpur). **DESIGN AND EVIDENCE REVIEW ONLY.**
Phase 3H is owner-closed PASS WITH LIMITATIONS. Overall final FYP acceptance is
**NOT READY**. Compact execution remains the accepted default; deferred scoring
remains the scoring default. Nothing in this review authorises policy activation,
production changes, migrations, historical rewrites or another benchmark.

Only this new documentation file is created. No tests, benchmark, model inference
or database migrations are run for this review. Retained results are attributed
to their original phases; a passing unit test is not human fashion validation.

## Authority and status semantics

Original source: `C:/Users/chong/Downloads/RSW_ChongWeiPing_Project1 (1).pdf`,
SHA256 `5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`.
The requirement wording in the matrix was re-extracted directly from the PDF;
whitespace and unreadable apostrophe glyphs are normalised, not paraphrased.
PDF page numbers are one-based; printed page = PDF page minus 11. RN-01 to
RN-29 are all Must requirements in the report. RN-30 is Should and is discussed
separately, not substituted for RN-29.

The earlier `PHASE_5F_REQUIREMENTS_AUDIT.md` is a historical evidence source,
not the current acceptance verdict. Its review-payload, save-mutation and
historical-action gaps were subsequently corrected. Its original latency
failures must remain preserved. Chapter 4 sections 4.4.3 (PDF232-233) and
4.10.4 (PDF285-288) require three component scoring, consistent scales,
weight sum one, every valid candidate, and total/R/C/P/stable-ID ranking.
They do not supply validated fashion rules, numeric wardrobe baselines,
acceptance percentiles, or a special single-dress compatibility rating.

- **Verified:** actual integrated implementation plus retained functional evidence
  for the stated supported policy, SQLite/runtime and cases. This does not mean
  all languages, deployed environments, arbitrary fashion judgments or GPU models.
- **Partial:** a stated functional capability remains incomplete in the accepted
  default or an identified path; a disabled experiment does not close it.
- **Unverified:** implementation/observations exist but the required acceptance
  environment, maximum workload or independent evidence is not established.
- **Blocked:** an identified external prerequisite prevents the relevant work.
  External evidence gates are identified below; no row is called Blocked merely
  because it would benefit from additional testing.

R = your Recommendation/Interaction subsystem; T = teammate CV/Digital Wardrobe/
Visualisation; Shared includes authentication, deployment and agreed contracts.
Verified rows assume the **enabled integrated application path**, not a claim
that unknown deployment settings are correct. Integration flags still default
false in composition. API/data protection is verified; a public route shell
is not a grant of private data. Explicit deployment acceptance remains open.

## Implementation and evidence key

Each matrix row names actual code behaviour and a key below; these references
and the listed tests are part of that row's evidence, not inferred services.

| Key | Actual production sources / retained evidence |
|---|---|
| NLP/EXTRACT | `backend/app/application/nlp/nlp_interpreter.py:12`, `request_field_extractor.py:13`, `intent_classifier.py:5`, `controlled_value_mapper.py:6`, `structured_request_builder.py:5`; immutable `structured_outfit_request.py`; versioned `nlp/config/vocabulary.v1.json`. |
| QUERY | `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py:123`; immutable `backend/app/shared_contracts/confirmed_garment_snapshot.py`; no legacy NULL-link trust. |
| GEN/RULE | `backend/app/application/recommendation/compact_exhaustive_scorer.py:53`, `compact_mandatory_verifier.py`, `structural_policy.py:9`, `candidate_generator.py`, `request_constraint_evaluator.py:7`; no truncation or incomplete-stream success. |
| SCORE | `backend/app/application/recommendation/assistant_scoring_selection.py:15`, `request_match_scorer.py:7`, `preference_scorer.py:10`, `compatibility_decision_policy.py:41`, `candidate_ranker.py:5`; raw evidence distinct from decision contributions. |
| HOME | `backend/app/application/recommendation/homepage_recommendation_service.py:13`, `reservoir_selector.py:18`, `frontend/components/HomepageRecommendation.tsx:8`. |
| ASSIST | `backend/app/application/recommendation/outfit_assistant_service.py:35`, `backend/app/api/recommendation_routes.py:47`, `frontend/components/OutfitAssistant.tsx`. |
| HISTORY/PERSIST | `backend/app/infrastructure/persistence/chat_history_query_adapter.py:24`, `recommendation_repository_adapter.py:24` (write transaction at51), `frontend/components/CompletedChatView.tsx:8`, `frontend/app/history/page.tsx`. |
| SAVE/ACTIONS | `backend/app/application/recommendation/recommendation_service.py:145`, `recommendation_actions.py:13`, `frontend/components/RecommendationResult.tsx:14`; historical action controls explicitly enabled by CompletedChatView. |
| VIS | `backend/app/application/visualisation/outfit_identifier_validator.py:14`, `outfit_visualisation_service.py`, `personal_image_service.py`, `visualisation_result_service.py`, `backend/app/domain/value_objects/visualisation_plan.py`, `frontend/app/try-on/page.tsx` and `result/page.tsx`. |
| T-N | `backend/tests/test_nlp_interpreter.py`, `test_nlp_evaluation.py`; alias, absent-field, unsupported/binding and development/evaluation separation tests. |
| T-E | `backend/scripts/evaluate_nlp.py`; fixed `backend/tests/fixtures/nlp_evaluation.v1.json`; retained `storage/verification/phase5f/nlp-evaluation.json`. |
| T-G | `backend/tests/test_confirmed_garment_snapshot.py`, `test_structural_candidates.py`, `test_request_candidates.py`, `test_compact_exhaustive.py`, `test_compact_assistant_integration.py`. |
| T-R | `backend/tests/test_recommendation_scoring.py`, `test_candidate_ranking.py`, `test_preference_modelling.py`, `test_compatibility_decision.py`, `test_prepared_aggregation.py`, exact differential/frozen-reference suites. |
| T-H | `backend/tests/test_homepage_recommendation.py`; `frontend/tests/recommendation.spec.ts` and actual backend login/Homepage/browser flow. |
| T-A | `backend/tests/test_outfit_assistant.py`, `test_compact_assistant_integration.py`, `test_compact_default_readiness.py`; `frontend/tests/phase5f/compact-integrated.spec.ts`, `frontend/tests/recommendation.spec.ts`. |
| T-CH | `backend/tests/test_chat_history.py`, `test_recommendation_persistence.py`, `test_historical_recommendation_actions.py`; `frontend/tests/historical-actions.spec.ts`. |
| T-D | `backend/tests/test_recommendation_actions.py`, `test_historical_recommendation_actions.py`; `frontend/tests/recommendation-actions.spec.ts`, `historical-actions.spec.ts`; actual upload/review/confirmation with development AI, not real extraction quality. |
| T-V | `backend/tests/test_vton_contracts.py`, `test_workflow.py`, recommendation/historical-action suites; UI/source inspection. Contract/development/fake-adapter evidence does not certify the real GPU model. |
| T-L | `storage/verification/phase5f/latency.json`; `docs/PHASE_5F_VERIFICATION.md`; `backend/runs/chat_history/benchmark.v1.json` and `docs/CHAT_HISTORY_CONTRACT.md` (historical query/API evidence); Phase3G/H raw timing files. |

Retained Phase3H totals: 292 focused passes; 1,798 backend passes and one known
ai-services assertion; 28 four-way and35 legacy browser passes; TypeScript,
lint (two existing navigation warnings), isolated production build and diff
checks passed. Two resource-blocked attempts ran no timed submissions. The quiet
retry passed all9 default-browser submissions. These results were **not rerun**
during Phase3I. All18 Phase3H deliverable file hashes matched its retained index
at the beginning of this review.

## Full requirement acceptance matrix

The exact requirement wording and PDF page are followed by status, actual
implementation, existing test evidence, gap, ownership and minimum closure.
'No implementation change' is limited to that row's stated functional scope;
it does not waive the shared acceptance/deployment gates below.

### Recommendation and NLP

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| RN-01 | The NLP component shall classify each submitted request as either a supported outfit-recommendation request or an unsupported request. (p.186) | Verified | NLP/EXTRACT: Binary supported/unsupported orchestration | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-02 | The NLP component shall extract the occasion from a supported request when occasion information is present. (p.186) | Verified | NLP/EXTRACT: Approved nine-occasion extraction, without suitability inference | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-03 | The NLP component shall extract the requested style from a supported request when style information is present. (p.186) | Verified | NLP/EXTRACT: Approved style aliases extracted independently | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-04 | The NLP component shall extract the preferred colour from a supported request when colour information is present. (p.186) | Verified | NLP/EXTRACT: Approved fourteen global colours extracted; local garment-colour binding rejected | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-05 | The NLP component shall extract the requested garment category from a supported request when garment-category information is present. (p.186) | Verified | NLP/EXTRACT: Specific categories and preserved broad groups extracted | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-06 | The NLP component shall extract the formality level from a supported request when formality information is present. (p.187) | Verified | NLP/EXTRACT: casual/smart_casual/formal extraction, distinct from style | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-07 | The NLP component shall convert the extracted request information into structured fields that can be processed by the recommendation component. (p.187) | Verified | NLP/EXTRACT: Immutable StructuredOutfitRequest built from five fields | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-08 | The NLP component shall represent an absent optional request field using its documented null or default value rather than creating an unsupported user requirement. (p.187) | Verified | NLP/EXTRACT: Absent optional fields remain None | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-09 | The NLP component shall return an unsupported-request status when the submitted text cannot be interpreted as an outfit-related request. (p.187) | Verified | NLP/EXTRACT: Unsupported intent/meaning returns controlled outcome | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-10 | The NLP component shall complete the request-processing workflow without generating a follow-up clarification question. (p.187) | Verified | NLP/EXTRACT: One interaction, no follow-up clarification | T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-11 | The recommendation component shall obtain current user-owned, confirmed and available garment records only through the ConfirmedGarmentQuery interface provided by the Digital Wardrobe subsystem. (p.187) | Verified | QUERY: owner/status/confirmed item and processing-job owner joins through injected contract | T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-12 | The recommendation component shall exclude supplied garments that do not contain the attributes required for recommendation processing or that violate mandatory recommendation-specific conditions for the current request. (p.188) | Verified | RULE/GEN: missing required evidence is not Pass; unsupported structure excluded | T-G/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-13 | The recommendation component shall filter candidate garments according to the structured conditions extracted from the submitted request. (p.188) | Partial | RULE: collective categories, global authoritative primary colours and base-style evidence; default occasion/formality PolicyUnavailable | T-G/T-A | Default cannot fulfil occasion/formality; most non-anchor CV hex colours are unknown; per-garment bindings unsupported. | R + shared annotation owner | Approve bounded suitability and colour evidence coverage/acceptance policy; implement only separately approved gaps. |
| RN-14 | The recommendation component shall generate outfit candidates using only eligible garments retrieved for the submitted request. (p.188) | Verified | GEN: exhaustive combinations from query snapshots, no saved outfits required | T-G/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-15 | The recommendation component shall exclude an outfit candidate before scoring when it violates a mandatory request condition. (p.188) | Verified | RULE/GEN: Fail or Unknown never passes independent scoring gate | T-G/T-R | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-16 | The recommendation component shall exclude an outfit candidate before scoring when it violates a configured garment-category or outfit-structure rule. (p.188) | Verified | GEN: approved thirteen-category/four-structure policy before scoring | T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-17 | The recommendation component shall calculate a score for each valid outfit candidate using the documented request-match, compatibility, and user-preference criteria. (p.188) | Partial | SCORE: live default R/P with compatibility unavailable; opt-in decision profile has three terms | T-R/T-A | Live compatibility weight is zero; experimental aesthetic proxies and dress/missing conventions lack independent quality review. | R | Complete narrow policy/ranking review, then seek separate scoring-default approval; do not close RN-17 yet. |
| RN-18 | The recommendation component shall rank valid outfit candidates according to their calculated recommendation scores. (p.189) | Verified | GEN/ASSIST: Exact streaming ranking by total score | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-19 | The recommendation component shall select the highest-ranked valid outfit for a successfully processed NLP request. (p.189) | Verified | GEN/ASSIST: Highest valid candidate published only after completion | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-20 | The recommendation component shall apply the documented tie-breaking rule when two or more valid candidates receive the same highest score. (p.189) | Verified | GEN/ASSIST: Total, R, C, P, stable identifier tie sequence | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-21 | The recommendation component shall return exactly one outfit recommendation for each successfully processed NLP request. (p.189) | Verified | GEN/ASSIST: Exactly one successful result | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-22 | The recommendation component shall return a no-result status when no outfit candidate satisfies all mandatory request and outfit-structure conditions. (p.189) | Verified | GEN/ASSIST: No invalid fallback; explicit no-result, evidence and capability outcomes | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-23 | The recommendation component shall not generate garment identifiers, attributes, or availability information that are absent from the retrieved wardrobe records. (p.189) | Verified | GEN/ASSIST: Only snapshot garment IDs/attributes, no fabrication | T-G/T-R/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-24 | The homepage recommendation component shall select outfits only from candidates that satisfy the configured outfit-structure and compatibility rules. (p.190) | Verified | HOME: approved mandatory structure/compatibility policy, no aesthetic score threshold | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-25 | The homepage recommendation component shall randomly select exactly one outfit from the valid candidate collection. (p.190) | Verified | HOME: exhaustive reservoir selection of exactly one valid candidate | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-26 | The homepage recommendation component shall operate independently of NLP request processing and shall not create a chat-history record. (p.190) | Verified | HOME/PERSIST: NLP-independent generation; homepage chat_id NULL | T-H/T-CH | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| RN-27 | The NLP component shall achieve at least 80% correct intent classification and request-field extraction across the fixed labelled evaluation dataset. (p.190) | Verified | NLP: fixed author-labelled 120-case evaluation exceeds original 80% criterion | T-N/T-E | Verified only on the frozen synthetic dataset, not independent language generalisation. | R | Preserve fixed labels/hash and original criterion; broader human evaluation is a separate quality task. |
| RN-28 | Every outfit recommendation produced during system evaluation shall use only current user-owned, confirmed and available garment records supplied through ConfirmedGarmentQuery and shall satisfy all applicable recommendation-specific eligibility conditions, mandatory request constraints, outfit-structure rules and compatibility rules. (p.190) | Partial | QUERY/RULE/GEN/PERSIST: strict validity verified in retained integration populations | T-G/T-A/T-CH | No consolidated final acceptance population covering the agreed final capabilities, real attribute distributions and every evaluated output; legacy route is not certified. | R | Freeze acceptance configuration and combined request/wardrobe labels; audit every generated evaluation result without changing constraints. |
| RN-29 | The NLP evaluation dataset shall include supported requests, partially specified requests, unsupported requests, and requests for which no valid outfit can be generated. (p.191) | Verified | NLP dataset: 40 detailed, 30 partial, 30 unsupported and 20 no-feasible scenarios | T-E | Dataset-content requirement met; downstream result for these 20 cases remains NotEvaluated. | R | Keep dataset content verified; execute downstream scenarios for combined acceptance/RN-28 and RN-30 evidence. |

### Homepage

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| FR-HR-01 | The system shall initiate homepage recommendation generation when an authenticated Registered User accesses the homepage. (p.169) | Verified | HOME UI: effect starts authenticated homepage flow | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-02 | The system shall retrieve only confirmed and available garments belonging to the authenticated Registered User. (p.169) | Verified | QUERY: strict current eligibility | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R + shared auth/query | Retain evidence; no implementation change required. |
| FR-HR-03 | The system shall determine whether sufficient eligible garment categories are available to form a complete outfit. (p.169) | Verified | HOME/GEN: sufficient supported category slots | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-04 | The system shall generate possible outfit combinations using the eligible wardrobe garments. (p.169) | Verified | HOME/GEN: lazy wardrobe combinations | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-05 | The system shall exclude outfit combinations that violate the required garment-category structure or mandatory compatibility rules. (p.169) | Verified | HOME/GEN: approved mandatory structure and compatibility rules | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-06 | The system shall remove duplicate outfit combinations before selecting a homepage recommendation. (p.169) | Verified | GEN: deterministic IDs/deduplication | T-H/T-G | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-07 | The system shall randomly select one outfit from the valid homepage recommendation candidates. (p.170) | Verified | HOME: reservoir random top-one, not weighted Assistant ranking | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-08 | The system shall display the selected outfit recommendation on the homepage. (p.170) | Verified | HOME UI: ordered complete recommendation cards | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-09 | The system shall not provide a user-controlled function for refreshing or requesting another homepage recommendation during the current homepage recommendation flow. (p.170) | Verified | HOME UI: no refresh control; same-flow retry retains key | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-10 | The system shall display an appropriate message when insufficient garments or no valid outfit combinations are available. (p.170) | Verified | HOME UI/service: explicit empty/insufficient/no-valid outcome | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-11 | The system shall display an error message when the homepage recommendation process cannot be completed. (p.170) | Verified | HOME UI/service: failure message, no saved substitute | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-HR-12 | The system shall not create a chat-history record for an outfit recommendation generated automatically on the homepage. (p.170) | Verified | PERSIST: homepage insert has no NLP chat | T-H | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |

### Outfit Assistant

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| FR-OA-01 | The system shall allow an authenticated Registered User to access the Outfit Assistant. (p.171) | Verified | ASSIST/API: authenticated operations and private data | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R + shared auth | Retain evidence; no implementation change required. |
| FR-OA-02 | The system shall display the Outfit Assistant request interface and provide a New Chat option for starting a new single-request recommendation interaction. (p.171) | Verified | ASSIST UI: request interface and New Chat | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-03 | The system shall allow the Registered User to create a new chat. (p.171) | Verified | ASSIST UI: independent draft/key; completed row only on success | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-04 | The system shall allow the Registered User to submit one natural-language outfit request within a new chat. (p.171) | Verified | ASSIST UI/service: one locked request plus durable submission key | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-05 | The system shall reject a request that is empty or contains only whitespace characters. (p.171) | Verified | NLP/UI: empty/whitespace rejected | T-A/T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-06 | The system shall process the submitted request using the NLP and recommendation components. (p.171) | Verified | ASSIST: actual NLP, eligible retrieval, mandatory evaluation and ranking orchestration | T-A/T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-07 | The system shall display exactly one outfit recommendation when the submitted request is processed successfully. (p.172) | Verified | ASSIST UI: one result on successful completion | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-08 | The system shall display the original request together with its corresponding recommendation. (p.172) | Verified | ASSIST/PERSIST/UI: original text retained with result | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-09 | The system shall display an unsupported-request message when the request cannot be interpreted. (p.172) | Verified | NLP/ASSIST UI: controlled unsupported message | T-A/T-N | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-10 | The system shall display a no-result message when no suitable outfit can be generated. (p.172) | Verified | ASSIST UI: controlled no-result, evidence and capability messages | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-11 | The system shall display an error message when request interpretation, garment retrieval or recommendation generation fails. (p.172) | Verified | ASSIST UI/service: interpretation/retrieval/generation/storage error handling | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-OA-12 | The system shall prevent another request from being submitted within a completed chat. (p.172) | Verified | ASSIST/CH UI: completed chat read-only, New Chat for another request | T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |

### Completed Chat History

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| FR-CH-01 | The system shall create a completed chat-history record only after one outfit recommendation has been generated successfully. (p.173) | Verified | PERSIST: completed chat only on successful atomic recommendation write | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-02 | The system shall associate each completed chat-history record with the original submitted request, the generated Recommendation, the authenticated user identifier and the creation time, while the garments belonging to the recommendation shall be represented through its associated RecommendationItem records. (p.173) | Verified | PERSIST: user/request/time/recommendation and item associations | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-03 | The system shall store the request and corresponding recommendation as one complete operation. (p.173) | Verified | PERSIST: one SQLite write transaction for chat/recommendation/items/metadata | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-04 | The system shall prevent a record containing only the request or only the recommendation from being presented as a completed chat. (p.173) | Verified | HISTORY: coherence predicate hides partial/corrupt records | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-05 | The system shall mark a successfully saved chat-history record as completed and read-only. (p.173) | Verified | HISTORY/UI: completed/read-only record and GET-only detail | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-06 | The system shall prevent the Registered User from submitting another request within a completed chat. (p.174) | Verified | HISTORY/UI: no append; key/text conflicts rejected | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-07 | The system shall prevent duplicate chat-history records when the same request submission is unintentionally processed more than once. (p.174) | Verified | PERSIST: unique user/operation/key plus fingerprint under write lock | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-08 | The system shall allow a Registered User to search their own completed chat-history records using the supported search field. (p.174) | Verified | HISTORY/UI: own request-text literal casefold search | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-09 | The system shall return only chat-history records belonging to the authenticated Registered User. (p.174) | Verified | HISTORY: owner-bound query and joins | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R + shared auth/query | Retain evidence; no implementation change required. |
| FR-CH-10 | The system shall display all completed personal chat records when the search field is empty. (p.174) | Verified | HISTORY/UI: empty search browses all pages; total/cursor explicit | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-11 | The system shall display a no-results message when no chat-history record matches the submitted search term. (p.174) | Verified | HISTORY/UI: no-match empty state | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-12 | The system shall allow a Registered User to select and view one of their previous completed chat records. (p.174) | Verified | HISTORY/UI: owner-selected historical detail | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-13 | The system shall display the saved request and corresponding recommendation when a completed chat record is opened. (p.174) | Verified | HISTORY/PERSIST/UI: saved original request and historical item snapshots | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |
| FR-CH-14 | The system shall prevent a Registered User from accessing a chat-history record belonging to another user. (p.175) | Verified | HISTORY/API: missing/foreign generic 404 | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R + shared auth/query | Retain evidence; no implementation change required. |
| FR-CH-15 | The system shall indicate when a garment referenced by a historical recommendation is no longer available in the current digital wardrobe. (p.175) | Verified | HISTORY/UI: historical snapshot retained, current strict eligibility flag shown | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R + shared auth/query | Retain evidence; no implementation change required. |
| FR-CH-16 | The system shall inform the Registered User when a successfully generated request and recommendation cannot be saved to chat history. (p.175) | Verified | ASSIST/PERSIST/UI: PersistenceFailure with rollback; replay recovers lost response | T-CH/T-A | None in the stated functional scope; global evidence/deployment qualifications still apply. | R | Retain evidence; no implementation change required. |

### Shared saving

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| FR-DW-16 | The system shall allow a Registered User to save a valid outfit recommendation displayed through Homepage Recommendations, the Outfit Assistant or Recommendation Chat History as a permanent outfit in their Digital Wardrobe. (p.167) | Verified | SAVE/UI: separate permanent outfit from homepage/Assistant/history | T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared: R integration, T wardrobe | Retain evidence; no implementation change required. |
| FR-DW-17 | The system shall create one Outfit record and the required OutfitItem relationships when a recommendation is saved. (p.167) | Verified | SAVE: atomic Outfit plus ordered OutfitItem rows | T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared: R integration, T wardrobe | Retain evidence; no implementation change required. |
| FR-DW-18 | The system shall reference the existing garment records when saving a recommendation and shall not create duplicate garment records. (p.167) | Verified | SAVE: reference existing garments, no garment inserts | T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared: R integration, T wardrobe | Retain evidence; no implementation change required. |
| FR-DW-19 | The system shall verify that all referenced garments belong to the authenticated Registered User before saving the recommendation. (p.167) | Verified | ACTIONS: all members current owner-scoped strict query | T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared: R integration, T wardrobe | Retain evidence; no implementation change required. |
| FR-DW-20 | The system shall display the successfully saved recommendation in the Registered User’s Outfits collection. (p.168) | Verified | SAVE/UI: separate saved-state lookup and Outfits collection | T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared: R integration, T wardrobe | Retain evidence; no implementation change required. |

### Shared visualisation

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| FR-VIS-01 | The system shall allow a Registered User to request outfit visualisation from a selected saved outfit, Homepage recommendation, Outfit Assistant recommendation or recommendation displayed through Recommendation Chat History. (p.176) | Partial | VIS/UI: source links from saved outfit/homepage/Assistant/history | T-V/T-D | Outerwear recommendations deliberately cannot be visualised; final model-backed source coverage not independently accepted. | Shared: R handoff, T VTON | Agree supported VTON scope with T/supervisor; verify real top/bottom/dress source journeys. |
| FR-VIS-02 | The system shall receive the selected source type and corresponding Outfit or Recommendation reference required to initiate the visualisation workflow. (p.176) | Verified | VIS/API: exactly one source type and identifier | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared | Retain evidence; no implementation change required. |
| FR-VIS-03 | The system shall verify that the selected Outfit or Recommendation reference is accessible to the authenticated Registered User before resolving the source for visualisation. (p.176) | Verified | VIS: owner-bound source lookup before resolution | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | Shared | Retain evidence; no implementation change required. |
| FR-VIS-04 | The system shall resolve the selected Outfit or Recommendation reference to its current garment records and shall reject visualisation processing when any required garment reference is missing, duplicated, unowned, deleted, unavailable, unconfirmed or otherwise invalid for the supported visualisation workflow. (p.176) | Partial | VIS/ACTIONS: recommendation source strict; saved-outfit branch accepts accepted or unlinked garments | T-D/T-V | Confirmed code-path gap for saved-outfit source: no strict processing-job ownership check; accepted/NULL links may pass. | Shared, T-owned saved-outfit path | T/shared approval for minimum saved-outfit-source strict revalidation and focused stale/foreign-job/accepted/NULL tests; no change made here. |
| FR-VIS-05 | The system shall obtain the reviewed garment image or approved fallback image associated with each resolved and validated current garment record required for visualisation. (p.177) | Verified | VIS: current preferred reviewed media resolved and owner-authorised | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | T + shared media | Retain evidence; no implementation change required. |
| FR-VIS-06 | The system shall allow the Registered User to select or upload an authorised personal photograph when a personal base image is required. (p.177) | Verified | VIS UI/personal_image_service: private photo upload/selection | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-07 | The system shall validate the selected personal image before beginning visualisation processing. (p.177) | Verified | VIS: decoded media/type/availability/owner validation and preprocessing contract | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-08 | The system shall create the internal visualisation request using the authenticated user, resolved and validated current garments, supported garment roles, processing order and selected personal image where applicable. (p.177) | Verified | VIS: immutable ordered garment/person/configuration plan and persisted items | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-09 | The system shall process the visualisation request using the backend AI inference environment rather than the web browser. (p.177) | Unverified | VIS: backend CatVTON adapter and GPU slot exist; development mode is labelled | T-V + teammate handoff | Handoff reports a real upper-body smoke run, but its raw results.json is absent here; no current model-backed cross-structure acceptance bundle. | T + shared evidence | Obtain exact raw smoke/model/config hashes from T; verify real supported multi-pass structures on authorised images. |
| FR-VIS-10 | The system shall maintain a controlled status for each visualisation request, such as queued, processing, completed, failed or cancelled. (p.177) | Verified | VIS: queued/processing/completed/failed/cancelled lifecycle | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-11 | The system shall display the generated outfit visualisation only after processing has completed successfully. (p.177) | Verified | VIS UI/result service: only completed outputs expose media | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-12 | The system shall allow the Registered User to export or download a successfully completed visualisation through an authorised application-controlled action. (p.178) | Verified | VIS UI/protected media: authorised download action | T-V + source inspection | Protected owner contract exists; final model-backed output/download journey not re-executed in Phase 3H. | T + shared media | Retain contract proof; include output download in T acceptance walkthrough. |
| FR-VIS-13 | The system shall store each successfully completed visualisation together with the exact garment references, personal-image reference, generated output-media reference and relevant processing configuration required to preserve generation traceability. (p.178) | Verified | VIS: garment/person/output/configuration snapshots retained | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-14 | The system shall allow the Registered User to retry or safely cancel a failed or long-running visualisation request. (p.178) | Verified | VIS UI/service: owner-scoped cancellation and retry/new request | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | T + R historical handoff | Retain evidence; no implementation change required. |
| FR-VIS-15 | The system shall display an appropriate error message when the selected garments, personal image or visualisation process cannot be completed. (p.178) | Verified | VIS UI/service: invalid source/person/inference controlled errors | T-V/T-D | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |
| FR-VIS-16 | The system shall present visualisation results as an outfit preview without claiming measurement-accurate fit. (p.178) | Verified | VIS result notice/UI: preview, explicit non-measurement-accurate fit disclaimer | T-V | None in the stated functional scope; global evidence/deployment qualifications still apply. | T | Retain evidence; no implementation change required. |

### Performance

| ID | Original wording (PDF page) | Status | Actual implementation | Existing evidence | Remaining gap | Owner | Minimum closure action |
|---|---|---|---|---|---|---|---|
| NFR-01 | The system shall display one valid homepage outfit recommendation within three seconds after the homepage has completed loading under the baseline test environment. (p.180) | Unverified | HOME: observed post-load browser maximum 2.809s at 200; three-second target | T-L | No approved final deployment baseline; five observations/size and synthetic media do not certify real image/network performance. | Shared: R, deployment owner, supervisor | Approve NFR-01 environment/workload and post-load boundary, then verify representative images and every observed response. |
| NFR-02 | The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment. (p.180) | Unverified | ASSIST: compact/deferred nine-call sanity passed, 200 median 4.542s/max 4.573s | T-L | Five-second baseline still unapproved; earlier 200/stress slow and timeout results retained; homogeneous sanity is not formal acceptance. | Shared: R, deployment owner, supervisor | Approve the NFR-02 plan below, freeze fixtures/configuration, then run only the approved formal population. |
| NFR-03 | The system shall return chat-history search results within two seconds under the maximum chat-history workload defined in the system test plan. (p.180) | Unverified | HISTORY: observed search API/browser values below two seconds in documented populations | T-L | Maximum history workload not approved; historical API 10k/10k evidence is not a current approved browser maximum test. | Shared: R, deployment owner, supervisor | Approve maximum personal/other-user history and query/measurement profile, then verify it without changing the two-second target. |

Matrix totals (93 requirements): Verified=84, Partial=5, Unverified=4, Blocked=0. These are scope-qualified functional statuses, not a final FYP pass rate.


## Corrections to the original audit and remaining shared limitations

| Finding | Current evidence and classification | Minimum closure / owner |
|---|---|---|
| Normal review422/409 |FIXED for current browser payload. `frontend/app/extract/results/page.tsx:46` submits neckline/sleeve details as ordinary custom tags, not unsupported attribute keys. Valid string/list values are preserved. Actual browser top/trousers upload-review-confirm tests passed. The old negative test deliberately submits an obsolete payload; it does not prove today's frontend still does. |Retain tests; real CV quality remains T verification, not a reopened payload blocker. |
| Historical saving/actions |FIXED for supported recommendation sources. Strict transaction revalidation, immutable original recommendation, repeat-safe separate outfit save and historical action controls exist. Archival correctly blocks new actions without erasing history. |No further implementation indicated by current evidence; retain regression proof. |
| Saved-outfit-source validation |ACTUAL FR-VIS-04 GAP. `outfit_identifier_validator.py:14` calls strict_items only for recommendation sources. The saved-outfit path permits linked accepted items/NULL links and does not verify processing-job ownership. NULL is not proof of a legitimate manually confirmed record; its trust policy is unresolved. |T/shared agreement on confirmation proof for manual/legacy records, then minimal prepare/create/execution validation/tests; no automatic new legacy policy or historical rewrite. |
| Style null versus empty |INTEGRATION DATA LOSS. `wardrobe_service.py:42` uses `json.dumps(styles or [])`, collapsing missing style and intentional empty collections on some normal writes. Snapshot/mapper distinguish Missing versus Known-empty correctly but cannot recover discarded intent. Requested style can become definite nonmatch rather than Unknown. |T-approved forward-write semantics and review/edit/persist/query tests. Existing JSON/columns can represent the distinction; no new field/migration justified. Do not reinterpret all historical empty lists or change Phase1 contract. |
| CV black provenance |DATA-QUALITY LIMITATION. `color_analyzer.py:29` emits #000000 for empty pixels, indistinguishable from actual black in current snapshots. Confirmation is owner acceptance, not proof of extraction success; approximate Oklab cannot solve this provenance ambiguity. |T evidence policy or explicitly reviewed primary colour. Any pipeline/metadata addition needs separate approval; no invented confidence or new model. |
| Real CV/VTOFF/VTON |REPORTED EVIDENCE NOT ALL LOCALLY AVAILABLE. `VTON_HANDOFF.md` reports a real RTX5060 upper-body smoke:66.528s inference,101.598s including loading,5,271,428,096 bytes peak VRAM. Its named `storage/verification/vton/smoke/results.json` is absent here. O1 raw audit paths named in GARMENT_WORKFLOW_HANDOFF are also absent. |Obtain raw artifacts/input-model-config hashes from T; do not claim the teammate never ran them or substitute development tests. Fill real supported/multi-pass coverage on authorised images. Licensed DressCode is needed for the promised category-balanced quantitative evaluation, not every functional smoke. |
| PostgreSQL |REAL DEPLOYMENT/ARCHITECTURE ALIGNMENT GAP. Despite its name, `postgresql_repository.py:183` uses sqlite3 and PRAGMA foreign_keys=ON. BEGIN IMMEDIATE, idempotency/failure tests and row-auditing migrations certify SQLite only. SQL assets do not establish a working PostgreSQL app adapter/locking guarantee. |Owner/supervisor decide final DB commitment. If PostgreSQL is mandatory, a separately approved adapter/migration/concurrency task is implementation work. No initialization or migration was run here. |
| ai-services assertion |UNRESOLVED ARCHITECTURE/TEST CONTRACT. `test_report_architecture.py:28` forbids ai-services; that directory exists with app/scripts subdirectories, while ordinary rg enumeration returned no source files there. README declares backend the sole runtime. Directory existence alone does not prove a competing active runtime. |Review actual ownership/layout with T; approve a minimal test/document correction if warranted. Do not delete folders or call the assertion definitively obsolete without that decision. |
| Feature flags/legacy route |RELEASE CONFIGURATION GATE. `workflow_runtime.py:33` defaults integrated Homepage/Assistant flags false. Explicit integrated requests fail closed, but `recommendation_routes.py:47` sends an unqualified POST to the legacy generator when Assistant is off. That path still has heuristic roles, four-item cap, keyword extraction and hardcoded R/C; strict garment acquisition alone does not make it the accepted pipeline. Today's UI capability guard avoids it. |Freeze intended enabled flags/deployment and decide whether legacy generation is isolated/prohibited/retained. Do not certify arbitrary legacy requests using integrated evidence; routing changes need approval. Actual deployment env was not inspected. |

The original FR-OA-06 orchestration wording is Verified without asserting that
RN-13/RN-17 are complete. RN-29 dataset-content coverage is Verified without
asserting that its downstream outcomes ran. RN-28 remains Partial until a final
combined acceptance population/configuration is frozen and audited. Additional
RN-30 is Should: final combined evaluation should replace NotEvaluated with real
recommendation results; it does not change RN-27's original80% threshold.

Full rich score dashboards are desirable unless separately specified, not a
prerequisite for FR-CH-13's original text/outfit display. Independent real-user NLP
corpus work supports broader language claims, not a stricter invented RN-27
criterion. A complete reviewed-reference lookup library is a different optional
scoring method and is not required to activate the existing rule-based model.

## RN-17: standard-profile decision

**Recommend further narrowly scoped policy/ranking verification, with continued
deferral as the default in the meantime. No activation is authorised here.**
Do not build another scoring framework or require every outfit signature rated.

Default S=(7/10)R+0*C+(3/10)P, raw C Unavailable/NULL. Integrated experimental
S=(3/5)R+(1/5)C_decision+(1/5)P; it is not the old Jaccard experiment. Both use
exact Fractions, constant normalised weights, every mandatory-valid candidate,
complete-stream publication and total/R/C/P/stable-ID ranking. Absent R/P have
zero numerical contribution with their true NotApplicable/NoPreferences/Unknown
states, not perfect matches. Exact historical scores/provenance are restored,
not rescored. Four-way browser, replay, persistence and differential proof exists.

R averages supplied fields: category/colour/implemented suitability contribute1
after a mandatory pass; style is matching base members / base members. Therefore
most non-style hard fields cannot distinguish passing candidates; style can.
P uses supported stored type/value preferences and importance weights, not the
legacy preference-count placeholder. Missing preferences are not perfect P;
preferences never override an explicit mandatory request.

Colour atoms are1 for identical recognised primaries or an achromatic member
(black/white/grey), otherwise0 when both are known. This is a limited coordination
proxy, not a claim other chromatic pairings clash. Style atoms are Dice:
2*intersection/(sizeA+sizeB), on supported complete, nonempty sets. Pattern, fit/material
and Oklab distance are not enabled compatibility measurements. Every genuine
unordered pair has colour/style atoms, M=2/2/6 for pair/dress+outerwear/trio.
For known sum K and m unresolved atoms: L=K/M, U=(K+m)/M,
C_decision=(L+U)/2. These are possible-value bounds, not confidence/probability.
Fully observed C is its ordinary mean; fully unknown decision is conventional1/2.

A single dress remains one one_piece garment, zero pairs, raw NotApplicable and
explicit NoPairReference1/2. No fake second garment, perfect dress rating or
count bonus occurs. Comparability is implemented, but perceived-quality fairness
across structures is not independently established. Outerwear participates in
all real pairs.

### Why activation still needs a bounded review

- Same/achromatic colour and Dice style are reproducible proxies, not validated
  fashion taste. Distinct chromatic pairings can be deliberately coordinated.
- Replacing a known0 atom with unknown increases that atom's decision contribution
  to1/2. A dress/fully unknown outfit can outrank an observed low-score pair
  without measured evidence of better quality. Disclosure is necessary but does
  not establish this as an acceptable default ranking convention.
- Style may contribute via current request R, mutual style C and stored style P.
  These have different intentions but correlated signals; normalisation does not
  eliminate double-counting risk. The experimental switch also changes R/P
  weights from.70/.30 to.60/.20, confounding a claim of isolated C improvement.
- Real non-anchor CV hex coverage and upstream style-null loss can make C mostly
  conventional. Audit coverage by structure; do not invent a minimum percentage.
- UI/API distinguish Computed, PartiallyConventional, FullyConventional and
  NoPairReference. `CompatibilityExplanation.tsx` states these are rules or
  conventions rather than independent ratings. This is transparency proof, not
  fashion-accuracy proof. The empty reference library is not a dependency here.

### Worked examples: synthetic arithmetic, no human ratings

For 'Suggest a vintage outfit', each candidate below passes the minimum of one
base garment with vintage evidence. No stored preferences -> P contribution0.

| Candidate | Garments/evidence | R | Raw/decision C | Experimental S |
|---|---|---:|---|---:|
| A |blue vintage top + white vintage bottom |1 |colour1/style1 ->1 |3/5+1/5=4/5 |
| B |blue vintage top + red classic bottom |1/2 |colour0/style0 ->0 |3/10 |
| C |blue vintage dress |1 |raw NA, NoPairReference1/2 |7/10 |
| D |blue vintage top + bottom missing colour/style |1/2 (Partial) |raw Unknown, [0,1] midpoint1/2 |2/5 |
| E |A + red classic outerwear |1 |six atoms1,1,0,0,1,0 ->1/2 |7/10 |

D beats B by1/10 because of a missingness convention, not observed superiority.
A beats C by1/10 because of pair/no-pair policy, not proven dress quality.
For a generic request with no fields/preferences, deferred totals all tie at0
and stable ID decides. Experimental totals are C/5: A1/5, B0, C1/10, D1/10,
E1/10. A blue vintage dress plus white vintage outerwear has C=1; if outerwear
style is missing but colours coordinate, K=1,M=2,m=1 gives [1/2,1] and decision3/4.

### Minimum pre-activation verification proposal

Freeze policy/config hashes and reviewer instructions first. Proposal:24 held-out
examples (six per supported structure), two independent reviewers, disagreement
record/adjudication, covering mixed/missing styles, real hex evidence, known0,
outerwear, generic requests and preference/request conflicts. This is a small
pilot, not a report-specified sample size or claimed fashion accuracy threshold.
Owner/supervisor must agree the rubric before reviewing; labels must not be
invented, generated by the scorer or used to tune held-out cases.

Use existing tools to reproduce exact components/rankings, report measured versus
conventional contribution coverage per structure, and compare matched deferred/
experimental winners. Run offline weight sensitivity on fixed components;
report correlated style effects and winner changes without changing production
weights or adding a coverage tie-breaker. The report requires documented criteria
and three-component scoring, not a fabricated human-rating accuracy threshold.
The actual decision is explicit owner/supervisor acceptance or rejection of these
criteria/conventions for bounded casualwear, followed by separate activation and
regression/latency approval if accepted. RN-17 remains Partial in the accepted
default. If conventions are rejected, propose one minimum policy revision, not
another major architecture stage.


## Proposed NFR-02 acceptance specification v1.2 (not approved)

Original wording, PDF180/printed169:

> The system shall return either one outfit recommendation, a no-result response,
> or an unsupported-request response within five seconds after a valid NLP request
> is submitted under the baseline test environment.

PDF179 delegates the deployment/workload baseline to the system test plan. A full
report text search located that delegation and the targets, but no approved
numeric hardware, wardrobe, concurrency, repetitions or percentile choices.
`COMPACT_DEFAULT_READINESS.md` contains a v1.1 proposal explicitly pending
approval. Phase3H approved the engine default and sanity check, not that formal
baseline. No approved separate system plan was found in the reviewed repository.
If the owner/supervisor has an approved plan elsewhere, supply and reconcile it;
absence here is not proof none exists outside this checkout.

| Dimension | Established requirement/current approval | Proposed reproducible choice / unresolved decision |
|---|---|---|
| Response/deadline |Recommendation/no-result/unsupported within5s |Keep5s unchanged; require correct terminal outcome, not merely fast HTTP. |
| Hardware/deployment |A baseline must be defined; none numerically approved |Name CPU/OS/RAM, disk/filesystem, browser/network/proxy, workers and DB. Local Ryzen5 7235HS/8 logical/~19.69GiB RAM can be a local academic baseline only with explicit approval; it is not proven production-equivalent. |
| Software |Compact default accepted, deferred scoring default retained |Freeze Python3.12/Next16.4.2, dependencies/source/config hashes, production next start + one Uvicorn process and same-origin proxy with existing timeout. Record integrated feature and AI flags. SQLite is the runnable DB, not PostgreSQL. |
| Profile |Experimental scoring default-off |Initial formal population should use the accepted release profile. If RN-17 review changes that profile, approve/activate separately and freeze it before collection. Do not average different profiles or automatically repeat the two-profile96-trial study. |
| Baseline size |No numeric intended baseline supplied |Propose100 eligible garments only if independently justified by expected usage and owner/supervisor agreement. If200 is expected normal usage,200 must remain the baseline under the same5s bound. Never relabel a slow intended baseline as scalability after seeing results. |
| Category counts |Thirteen categories and approved four structures |Proposed100:40tops (10 each),40bottoms (14shorts/13trousers/13skirt),10dresses (3short/3long/2vest/2sling),10outerwear (5 each),17,710 complete structures.200 doubles each count,134,820 structures. Preserve exact existing category spellings in frozen rows. |
| Scalability/stress |Retain prior100/200 observations |If100 is baseline, report200 separately. Outerwear-heavy200:67tops/67bottoms/66outerwear gives300,763 structures, labelled stress. No truncation or blending into faster groups. |
| Request variety |Success/partial/unsupported/no-result required in evaluation |Freeze five supported requests below with independently checked structures/feasible candidates; separate terminal fixtures. Capability-unavailable and insufficient-evidence cases keep exact statuses, not fake suitability matches. |
| Preferences |Existing supported types only |Separate0/1/3 active supported preferences: colours; colours+styles+category groups. Freeze values, importance weights and IDs. Hard requests cannot be overridden. |
| Attribute completeness |Use supported existing evidence, no predictions invented |Use reviewed realistic snapshots with named/anchor/non-anchor/missing primaries; single/multiple/missing/empty styles; existing patterns retained. T supplies actual CV/review distribution summary before percentages are accepted. Malformed robustness fixtures remain separately labelled. |
| Earlier proposed mix |v1.1 proposed60%named/20%anchors/10%non-anchor/10%missing colours and70%single/20%multi/10%missing styles |Those are artificial stratification choices, not measured population rates. Actual CV emits hex, so60%named may be unrepresentative. Use them only as coverage fixtures unless reviewed real data justifies them; freeze revised counts before approval/timing, never after slow results. |
| Eligibility |Current owner/confirmed/available contract unchanged |Valid owner/job/item links; separately labelled accepted/pending/rejected/NULL/dangling/archived/foreign decoys must not alter eligible counts. No saved outfits required. No deployment DB used. |
| DB/history |Successful response includes atomic persistence |Frozen disposable DB per request/preference block, initially0 owner chats; keep30 fresh-key writes and growth within block. Record SQLite version/journal/storage placement. History-heavy cases separate. No reset to erase slow trials. |
| Concurrency |Not numerically specified in report |Propose one active interaction for initial local latency baseline, no overlapping CV/VTON/tests/builds. Not proof of concurrent multi-user performance. Future2/4-user capacity cases separately approved before concurrent-service claims. |
| Collection controls |No FYP CPU/RAM thresholds supplied |Retain three consecutive preflight samples <=20%CPU and >=4GiB RAM,10s settle,120s bounded wait, all observations retained. Validate low-overhead continuous monitoring and observer cost before formal collection. Snapshots alone are not continuous isolation. |
| Timing boundary |Submission to terminal response |Browser monotonic submit action to visible correct terminal result; include NLP, retrieval, exhaustive scoring, commit, proxy/network/UI. Record HTTP/backend/service separately. Login/page preparation outside request boundary explicitly; agree whether completed garment image loading is part of visible recommendation. |
| First/warm requests |Not specified |Servers ready before collection; include first actual recommendation, no hidden ranking warm-up. Record cache/asset state and first/subsequent calls. Startup/login have separate timing; no subtraction of slow first calls. |
| Repetitions |Not specified |Propose30 fresh-key trials per supported request/preference block:5x3x30=450 calls for the one accepted profile;3 terminal fixtures x30 with0 preferences=90 more,540 total. Earlier1080 two-profile proposal was not approved. Review workload/cost before collection. |
| Statistic |Five-second bound; report supplies no percentile |Proposed operational gate: every required baseline observation must return its correct terminal result within5s; report each value/count/median/max and optional disclosed exploratory percentile. This interpretation requires approval; a passing median/p95 alone cannot hide a failed deadline.30 samples cannot prove a universal bound. |
| Timeouts/failures |Controlled outcomes and preservation required |Retain errors, unfinished jobs, proxy timeouts and above5s results. No timeout extension, replacement/exclusion of failures or late commits counted as on-time UI success. Resource-affected populations stay labelled; retries use new labels. Fault injection is separate correctness evidence. |
| Reference comparison |Rollback retained |No full benchmark before baseline approval. Small prespecified matched reference checks only if diagnosing a discrepancy; compare engines within profile. Primary acceptance is the intended release configuration. |
| Artifacts |Reproducibility/traceability |Freeze labels/seed/materialised rows, expected interpretations/candidates, source/policy/vocabulary/lock/config hashes, topology, collector/observer versions and all raw trials. No tuning fixtures or changing mixes after seeing acceptance outcomes. |

### Concrete successful requests and terminal cases

1. `Suggest an outfit` - no supplied fields; default tie behaviour exposed.
2. `Suggest a vintage outfit` - valid candidates with different base-style R.
3. `Suggest an outfit with blue and white colours` - global colour constraints.
4. `Suggest an outfit including outerwear` - broad group/layering.
5. `Suggest an outfit with vintage style and blue colours` - combined conditions.

Freeze seed and exact varied category/colour/style rows (proposal: retain
seed20261021); do not reuse only homogeneous blue/vintage garments. Each expected
interpretation and feasible candidate set must be checked before timing. Do not
extend the schema: `blue top and black trousers` remains intentionally
unsupported. A global colour-plus-category phrase must satisfy current grammar
unchanged before it is labelled supported.

- Terminal A: zero eligible garments; valid `Suggest an outfit` ->
  NoEligibleGarments/no-result UI; no completed recommendation/chat.
- Terminal B: complete fully recognised wardrobe with only blue/white primaries;
  global red-colour request -> NoMatchingCandidates. Do not use mixed unknown
  colours for this definite-failure fixture: they can legitimately produce
  InsufficientEvidence instead.
- Terminal C: outside-scope `What is the weather forecast?` -> UnsupportedRequest;
  no retrieval/write. A correct controlled422 is not a recommendation failure
  merely because success responses use201. Invalid/empty input is separate.

Additional capability cases: campus/formality with suitability off ->
PolicyUnavailable, not unsupported NLP intent and not fulfilled occasion. Unknown
hex/missing attributes preserve three-state outcomes. Ask the supervisor how
capability-unavailable responses fit the literal terminal taxonomy; do not
silently conflate outcome statuses. Faults/stale writes remain correctness cases.

Hardware/DB,100-versus200 baseline, realistic evidence mix, concurrency,
repetitions and statistic are genuine approval decisions, not settled report
constants. No formal benchmark is run in Phase3I. Nine successful sanity requests
do not constitute this proposed diverse acceptance population.

## Current NFR acceptance status

| ID | Retained observations | Current formal verdict and minimum closure |
|---|---|---|
| NFR-01 |3s post-homepage-load target. Browser200 median2.632s/max2.809s, five observations; HTTP p95 at200 was3.333s under a different timing boundary. |Unverified final acceptance. Approve homepage/deployment/image-network/load boundary and verify it; no change to random selection. |
| NFR-02 |5s target. Latest compact/deferred50/100/200 browser medians0.190/0.684/4.542s;200max4.573s. Earlier compact200 medians5.038s deferred/6.017s experimental, slower stress/reference timeouts and both blocked attempts remain. |Unverified/formally unaccepted. Approve final release profile and diverse baseline before timing. Neither nine successes nor a passing median certifies the requirement. |
| NFR-03 |2s at system-plan maximum. Phase5F browser1,000 personal+3,000 foreign history max0.179s across groups. Separate10k+10k historical query/API max0.130268s. |Unverified final maximum/browser acceptance. Proposal: review10k personal+10k foreign as maximum,50-item pages, empty/common/no-match/Unicode/literal percent/underscore, first/later pages,30 searches per case. Maximum/topology/statistic still need approval. |

All earlier slow/failed/resource-affected observations remain immutable evidence.
New formal artifacts must identify exact engine/profile, dataset and deployment;
faster later runs cannot retroactively turn earlier failures into passes.


## RN-27/RN-29 evaluation evidence limits

Retained `storage/verification/phase5f/nlp-evaluation.json` records intent120/120,
five-field extraction450/450 across90 supported examples, explicitly supplied
fields130/130 and combined exact match120/120: all100%. The original criterion
is at least80% correct intent classification and request-field extraction;
combined exact match has no additional mandatory threshold. The fixed dataset
has40 detailed,30 partial,30 unsupported and20 no-feasible examples, separated
from development examples. It is author-labelled synthetic English, not an
independently collected user corpus. Its labels are not scorer predictions.
Dataset SHA256 `ced6418193e866649b635c6671ff2a1387becbd0435eb9eb0dc3a04a439760ba`
and all retained NLP source hashes were checked against current files in this
review. The evaluator was not rerun. All no-feasible examples identify an empty
confirmed wardrobe scenario, with downstream execution NotEvaluated; broader
combined outcome evidence is still needed for RN-28/RN-30 and formal testing.

## Practical acceptance roadmap

1. **Mandatory functional scope and shared data agreement first.** Prioritise
   RN-13 supported occasion/formality and usable colour evidence, and FR-VIS-04
   saved-outfit confirmation/job ownership. T/shared agreement is needed for
   saved/manual/legacy proof, forward style-null semantics and CV black provenance.
   Freeze intended integrated feature flags and legacy-route boundary. Request
   only narrowly scoped correction/integration approval; no wholesale frontend,
   processing, NLP or architecture rewrite. A supervisor-approved scope decision
   is necessary wherever a report commitment is intentionally limited.
2. **Three-component profile decision.** Conduct the bounded independent ranking/
   convention review using existing tooling. Owner/supervisor must accept or
   reject colour/style proxies, unknown midpoint, dress1/2 and correlated style
   effects. If accepted, separately approve standard-profile activation and
   targeted regressions/latency; if rejected, define one minimal policy revision.
   Deferred remains an honest interim state, not full RN-17 acceptance.
3. **NFR baseline approval before formal timing.** Choose intended release
   profile, DB/hardware, representative100/200 size, mixed evidence and labelled
   terminal outcomes. Freeze inputs and observation method before execution.
   Approve NFR-01 post-load image scope and NFR-03 maximum history alongside it.
   Keep all original targets/results; do not launch another optimisation project
   before these acceptance choices are settled.
4. **Real model and database verification with T.** Transfer/hash-check existing
   reported raw smoke/audit artifacts before repeating work. Fill missing real
   supported/multi-pass examples on authorised images; use licensed data only
   for the promised quantitative evaluation. Verify actual intended DB migrations,
   integrity, concurrent idempotent retries/rollback and transaction revalidation
   in disposable databases after separate approval. SQLite locking does not
   establish PostgreSQL behaviour. Never hold a DB transaction over VTON inference.
   Human/model/DB work can be coordinated in parallel, not replaced by synthetic
   UI screenshots or application test-count totals.
5. **Final FYP evidence/report consolidation.** One versioned bundle should link
   each of93 rows to final code/config, exact commands, input labels, raw outputs,
   model/DB evidence and approved limitations. Execute combined no-feasible
   request/wardrobe scenarios, preserve RN-27's dataset/criterion, reconcile the
   architecture test and update report claims to match approved implementation.
   Final FYP acceptance is an owner/supervisor decision.

### Minimum remaining implementation, only if separately approved

- Saved-outfit-source eligibility proof consistent with agreed confirmation/
  manual/legacy policy, plus focused source/queued-execution tests (T/shared).
- Forward style-null versus empty persistence semantics and lifecycle regression
  tests (T/shared); no automatic historical reclassification or new DB field.
- Bounded live suitability/owner-declared annotation integration if required by
  the agreed RN-13 scope;8 occasions/2 formalities exist opt-in, exercise/formal
  remain unavailable. Do not infer work=formal or sporty=exercise. Technical tag
  entry is not an acceptable final UX; UI changes need separate approval.
- Existing experimental scoring-default switch only if its review is accepted;
  any smallest rejected-rule revision must be specified and approved first (R).
- Actual PostgreSQL application adapter/deployment correction if PostgreSQL remains
  a mandatory report commitment; otherwise an explicitly accepted local-prototype
  deployment limitation. Source files named PostgreSQL are not sufficient proof.
- Any new colour-provenance metadata or CV change depends on T's approved contract;
  no guessed field, new model, approximate-hex activation or NLP rewrite is
  justified by this review. Colour calibration is a human-labelled evidence task
  before any later approximate-colour activation, not an automatic next feature.

### Minimum verification/evaluation

- Independently reviewed policy/ranking examples and weight/missingness/structure
  sensitivity, without fashion-accuracy claims from arithmetic tests alone.
- Frozen combined request/wardrobe labels and audit of every actual generated
  evaluation outcome (RN-28 and RN-30 evidence); RN-29 content already exists.
- Owner/supervisor-approved NFR01/02/03 baseline/maximum workload and executions,
  including recommendation, no-result and unsupported responses, with all raw
  failures, timeouts and resource observations retained.
- Transfer/audit real model evidence plus missing authorised smoke coverage;
  intended-DB migration/concurrency/rollback proof; agreed architecture assertion.
- Final consolidated traceability, reproducible release configuration and actual
  service restart/drain/rollback checks. Three ASGI lifespans are not an OS-level
  multi-worker deployment restart. Keep existing authentication, exact arithmetic,
  stream completeness, idempotency, immutable history and frozen-source tests.

### Recommended next approval

**Phase 5F-2E-3J: Mandatory Functional Scope and Scoring Policy Acceptance Review.**
This is a proposed bounded joint review with T and owner/supervisor, followed only
by individually approved small corrections and existing-tool evaluation, not a
new architecture milestone. First resolve saved/manual/legacy garment trust,
occasion/formality scope/annotation UX, actual CV colour-evidence expectations,
acceptance of midpoint/dress rules, final DB commitment and100-versus200 baseline.
Approve the specific functional fixes and evidence collection separately. Do not
activate a profile, enable suitability/hex, change weights, modify persistence,
run migrations or start the formal benchmark merely because this roadmap exists.

## Audit scope verification

Only this new documentation file was created. Original PDF, all18 retained
Phase3H code/documentation hashes and the retained NLP dataset/source hashes
were checked. No application/default/policy, frontend, prior report/raw evidence,
authentication, history, database or teammate module was modified. No test suite,
benchmark, model inference or migration was run in Phase3I. Earlier test/timing
results are retained evidence, not newly executed claims. No human labels or
missing model/database results were fabricated. Wait for owner review.
