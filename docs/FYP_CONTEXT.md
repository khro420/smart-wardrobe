t# Smart Wardrobe — FYP Project Context for VS Code / Codex

> **Purpose:** This document transfers the approved requirements, decisions, boundaries, and design of the Smart Wardrobe final-year project into a coding assistant's working context. It is a **specification reference**, **not a claim that these features have been implemented**.
>
> **Primary source:** *Smart Wardrobe: AI-Powered Garment Intelligence and Personalized Outfit Recommendation System*, FYP report, Chapters 1–4 (BMCS3404 Project I), especially Chapter 3 (Methodology and Requirements Analysis) and Chapter 4 (System Design). Section numbers and requirement IDs below refer to that report. If a question requires finer detail, consult the full report.
>
> **Repository rule:** Before proposing changes, inspect the actual project files, README, package manifests, existing `AGENTS.md` instructions, database migrations, tests, and recent code. The report is authoritative for the **intended system design**; the repository is authoritative for **what is currently implemented**. When they differ, explain the discrepancy and ask before making architectural changes. Do not assume that planned services, functions, database tables, endpoints, tests, or AI models already exist.

## 1. Project at a glance

- **Product:** Web-based Smart Wardrobe application for managing personal garments and receiving outfit recommendations that can be saved or visualised.
- **Underlying goal:** Reduce manual outfit-selection effort and make more effective use of clothing already owned by a user.
- **Research/design focus for this development work:** A wardrobe-constrained **Recommendation, NLP Interaction and Chat History** subsystem. It interprets a supported natural-language outfit request, retrieves eligible wardrobe garments, constructs valid outfits, ranks them, presents **one** recommendation, and preserves successful interactions as read-only history.
- **Development approach:** Iterative and Incremental Development; Object-Oriented Design (OOD); architectural descriptions organised using the **4+1 View Model**. See report §§3.2, 4.2.
- **Target technical architecture:** Three-tier client/server application: component-based web presentation tier; **FastAPI modular-monolith** application tier; **PostgreSQL** plus protected image/file storage data tier, connected over HTTPS REST/JSON. These are the planned architecture and technology choices in report §4.3; verify how much has actually been built.
- **Target users:** Guests for registration/login and authenticated Registered Users managing a personal casualwear wardrobe, their preferences, recommendations, visualisations, and own history. See report §§1.5, 3.3.
- **Division of work:** The **Recommendation and Interaction** workstream owns NLP request processing, outfit generation, compatibility constraints, user preferences, scoring/ranking, homepage recommendations, completed chat history, and integration with other subsystems. A separate **Computer Vision and Visualisation** workstream owns garment processing/segmentation, attributes and representations, Digital Wardrobe and outfit visualisation. Both must agree on data contracts. See report §1.7.
- **State when the source report was submitted:** Requirements analysis, literature research and detailed system design were documented in Chapters 1–4. The report does not establish an implemented or tested application. The current VS Code repository may have progressed since that report; **inspect it first**.

## 2. Working rules for Codex

1. **Read before editing.** Inspect project files and `AGENTS.md`, then summarise current implementation status before changing code. In the VS Code screenshot, the workspace contained `smart-wardrobe/` with `ai-services/`, `backend/`, `docs/`, and `frontend/`; `frontend/` showed a Next.js-related structure and an `AGENTS.md`. This is only a screenshot observation, not a verified current repository inventory.
2. **Keep approved boundaries.** Recommend only current authenticated-user-owned, confirmed and available garments **provided by `ConfirmedGarmentQuery`**. Do not directly query or manufacture garments from within the recommendation module.
3. **Separate hard constraints from soft preferences.** Reject ineligible garments and invalid outfit candidates *before* request/preference ranking. A high score must never rescue an invalid candidate.
4. **Exactly one result on success.** The Outfit Assistant handles one user request and returns one top-ranked valid outfit. A completed interaction is read-only. Start a new chat for a new request.
5. **No open-ended chatbot behaviour.** No follow-up clarification questions, multi-turn conversational memory within a chat, unrelated general questions, or shopping/catalogue recommendations in this scope.
6. **Do not invent design constants.** The report specifies a three-part scoring formula and weight-sum constraint but not final experimental weight values. Likewise, do not invent complete garment-category/colour/style enumerations or specific model/provider choices; locate approved values in the report, data contracts and code.
7. **Preserve distinct homepage behaviour.** Homepage uses valid-outfit generation followed by **random selection of exactly one candidate**, not the Outfit Assistant's weighted score; it creates **no NLP chat** and has **no user-controlled Refresh Recommendation function**.
8. **Respect ownership of other modules.** Outfit saving is done by Digital Wardrobe; image processing and virtual try-on are done by their owning subsystems. Integrate through the documented contracts, not their private tables or implementations.
9. **Keep integrity and security checks server-side.** Authentication, ownership checks, reference revalidation, consistent persistence, input validation, and controlled failure states are not optional.
10. **Never confuse specifications with results.** Performance numbers and NLP accuracy below are **requirements/targets**, not measured outcomes. Do not say they were achieved without actual tests.
11. **Prefer incremental changes.** Before implementing a feature, identify related use case/FR/NFR/RN IDs, files affected, integration assumptions, migration impact, and tests. Ask for approval before redesigning documented workflows or changing cross-subsystem contracts.

## 3. Project scope and exclusions

### In scope (report §1.5)

- Account registration/authentication, personal profiles and stored clothing preferences.
- Digital wardrobe with garment upload, AI-assisted garment segmentation/analysis, user review and correction, confirmed structured garment records, browsing and management.
- Recommendation from the user's **own current wardrobe**, using garment/category information, compatibility constraints, preferences and relevant supported request fields.
- Automatic homepage outfit recommendation.
- Task-bounded, text-based **Outfit Assistant** for natural-language recommendation requests.
- Searchable, read-only history of successfully completed Outfit Assistant requests and their associated recommendation.
- Saving valid recommendations as outfits through Digital Wardrobe.
- Outfit visualisation by a separate subsystem; the report describes virtual try-on as an AI-generated **preview**, not an accurate fit measurement.

### Explicit constraints (report §§1.5.6, 3.3.7; CA-01–CA-13)

- **Web-based prototype**; personal recommendations and chat history require login.
- **Casualwear** and supported garment categories only; standardised garment representations and the project's recognised fields/controlled values.
- **Rule-/constraint-/preference-based outfit generation**, not unrestricted generative creation of garment combinations.
- No clothing recommendations from external retailers, shops or other users' wardrobes.
- One request per chat and one recommendation on success; no additional messages in a completed chat.
- NLP limited to supported outfit requests and supported request fields; no clarification turns.
- Homepage recommendation and chat history are separate operations.
- No guaranteed physical-fit prediction, 3D body modelling, physics-based cloth simulation, general-purpose open-domain chat, e-commerce integration or social networking.
- **Do not add weather as an extracted NLP field merely because weather is mentioned as an outfit consideration in the background.** The approved extraction fields are those listed in §5 below.

## 4. Roles and principal user flows

### Actors and use cases (report §3.3.3)

- **Guest:** Register account (`SW_UC01`), Log In (`SW_UC02`).
- **Registered User:** Manage Profile and Preferences (`SW_UC03`); View Homepage Recommendations (`SW_UC05`); Use Outfit Assistant (`SW_UC06`); View Recommendation Chat History (`SW_UC08`); Log Out (`SW_UC09`).
- Wardrobe management, saving outfits and outfit visualisation are integrated system capabilities; the related `SW_UC07` is **Visualise Outfit**, as referenced in the use-case flows. See the full system use-case diagram for the complete set.
- **Internal algorithms (NLP, retrieval, ranking, storing) are not independent user use cases.** They implement the outward-facing use cases above. See §3.3.8.

### User-facing functional requirements by family (report §3.3.4)

| IDs | Design responsibility |
|---|---|
| `FR-ACC-01`–`FR-ACC-15` | Registration, login, authentication/session handling, logout |
| `FR-PP-01`–`FR-PP-09` | Profile editing, clothing preferences, validation, user ownership |
| `FR-DW-01`–`FR-DW-20` | Upload/processing/review/confirmation, personal wardrobe management, saving recommendation as an Outfit |
| `FR-HR-01`–`FR-HR-12` | Automatic homepage recommendation, valid candidate rules, random single selection, no user refresh, no chat |
| `FR-OA-01`–`FR-OA-12` | New Outfit Assistant chat, one request, one recommendation or explicit failure result, completed read-only chat |
| `FR-CH-01`–`FR-CH-16` | Atomic completed-chat persistence, deduplication, search, open history, ownership, stale garment handling |
| `FR-VIS-01`–`FR-VIS-16` | Validated visualisation sources, current garment resolution, personal-image validation, backend generation and feedback |

**Notable functional requirements:** `FR-HR-09`: no user-controlled homepage refresh; `FR-HR-12`: no homepage chat record; `FR-OA-05`: reject whitespace-only request; `FR-OA-07`: exactly one recommendation on success; `FR-OA-12`: completed chat cannot accept another request; `FR-CH-01`/`03`/`04`: a chat is completed only after successful generation and coherent persistence; `FR-CH-08`–`15`: searchable, user-owned, read-only history and stale-garment indication; `FR-DW-16`–`19`: saving recommendations reuses existing validated garments rather than duplicating garment records.

## 5. NLP interpretation contract

**Source:** report §§1.5.4, 3.3.6, 4.4.4, 4.10.1; `RN-01`–`RN-10`.

### Supported input and output

- Each new Outfit Assistant interaction takes **one natural-language outfit request**.
- Recognise whether the intent is a supported **outfit-recommendation request**.
- Extract only these supported fields when present:
  - `occasion`
  - `style`
  - `colours` / colour preferences in the request
  - `garmentCategories` / requested garment category
  - `formality`
- Map recognised language to **controlled values** consistent with garment records and recommendation rules.
- Construct a `StructuredOutfitRequest` containing the recognised intent plus the above optional fields.
- If an optional field is absent, leave it `null` or use the **documented default**; do not invent a requirement not present in the user's message.
- **Empty/whitespace-only:** return `InvalidInput`.
- **Outside supported outfit-request intent:** return `UnsupportedRequest` **before garment retrieval**.
- **No follow-up clarifying questions**. A partially specified supported request can proceed with documented null/default fields.

### Designed NLP service decomposition (report §4.4.4)

- `NLPInterpreter`: orchestration; operation `interpret()`.
- `RequestPreprocessor`: trim, empty-input validation, normalisation (case, spacing, punctuation, supported alternative wording).
- `IntentClassifier`: classify supported vs unsupported outfit intent.
- `RequestFieldExtractor`: extract occasion/style/colours/categories/formality.
- `ControlledValueMapper`: map recognised phrases to approved controlled vocabulary.
- `StructuredRequestBuilder`: construct `StructuredOutfitRequest`.

**Do not have `NLPInterpreter` retrieve garments, rank outfits, or store chat records.** Those responsibilities belong to other components.

### Source-aligned pseudocode (design logic, not executable code)

```text
interpret(requestText):
  text = trim(requestText)
  if text is empty: return InvalidInput
  text = normalise(text)
  if classifyIntent(text) != SUPPORTED_OUTFIT_REQUEST: return UnsupportedRequest
  fields = extractOccasionStyleColoursCategoriesFormality(text)
  fields = mapToApprovedControlledValues(fields)
  fillMissingOptionalFieldsWithDocumentedNullOrDefaults(fields)
  return StructuredOutfitRequest(intent, fields)
```

**NLP performance requirement (not a result):** `RN-27` targets **at least 80%** correct intent classification and request-field extraction on a **fixed labelled evaluation dataset**; `RN-29` requires supported, partially specified, unsupported, and no-valid-outfit examples; `RN-30` proposes recording expected/actual structured fields, status, and recommendation result. No achieved accuracy is asserted.

## 6. Recommendation engine — authoritative processing logic

**Source:** report §§1.5.3, 3.3.6, 4.4.3, 4.10.2–4.10.5; `RN-11`–`RN-26`.

### 6.1 Controlled wardrobe acquisition

- The **Digital Wardrobe subsystem**, not Recommendation, owns garment creation/editing/deletion, confirmation, ownership and current availability state.
- Recommendation obtains current, **authenticated-user-owned, confirmed and available** garment records through **`ConfirmedGarmentQuery`** only (`RN-11`; `CA-03`/`04`).
- `GarmentRetrievalService` consumes this interface and applies **recommendation-specific eligibility checks**. Do not accept browser-supplied garment IDs as an authoritative candidate collection; do not bypass the boundary to read wardrobe tables.
- Discard garments missing attributes required by recommendation processing (`RN-12`). For an Outfit Assistant request, apply mandatory explicit request conditions at the appropriate eligibility/candidate-rule stages (`RN-13`).
- Distinguish **hard user-request constraints** from **stored soft user preferences**. A stored preference ordinarily affects scoring rather than automatically excluding garments. Never hallucinate missing wardrobe garments, IDs or attributes (`RN-23`).

### 6.2 Candidate generation and mandatory validation

1. Group eligible garments by supported garment category/role.
2. Construct only supported complete outfit combinations; do not invent unsupported outfit compositions.
3. Deduplicate repeated combinations.
4. Reject candidates that fail **mandatory outfit structure**, **mandatory request conditions** (for an Outfit Assistant request) or **configured garment compatibility**.
5. Score **only valid candidates**. If none remain, return a clear no-valid-outfit/no-result state (`RN-22`).

**Invariant:** Compatibility and structure constraints cannot be overridden by ranking scores. Do not infer that model-predicted compatibility is necessarily the project approach; the approved design uses explicit rules and attributes.

### 6.3 Outfit Assistant scoring and ranking

For each **valid** candidate outfit `o`:

```text
S(o) = w_r * R(o) + w_c * C(o) + w_p * P(o)
w_r + w_c + w_p = 1
```

Where:

- `R(o)` = how closely the outfit matches **the current request** (supported occasion, style, colour, garment category, formality).
- `C(o)` = garment/outfit **compatibility** scoring (after mandatory compatibility has passed).
- `P(o)` = match against the user's **stored clothing preferences**.
- The three component score ranges must be **normalised consistently** before weighting.
- `w_r`, `w_c`, `w_p` are **configurable and documented**; **the report does not mandate particular numerical weights**. Do not set production defaults without checking approved configuration/implementation decisions.

Rank candidates by **descending total score**. If tied, compare in this exact order:

1. Descending `requestMatchScore`.
2. Descending `compatibilityScore`.
3. Descending `preferenceScore`.
4. Stable candidate/garment identifier ordering as the final deterministic tie-break.

Select and return **exactly one highest-ranked valid candidate** for a successful Outfit Assistant request (`RN-17`–`RN-21`). Store scores at the **recommendation level**, not as attributes of each garment.

### 6.4 Homepage recommendation is a different algorithm

- Trigger when an authenticated user accesses the homepage (`FR-HR-01`).
- Obtain the user's current confirmed and available garments through `ConfirmedGarmentQuery`.
- Apply recommendation eligibility, candidate-generation, outfit-structure and mandatory compatibility checks.
- If there is no eligible/full/valid outfit, return an appropriate insufficient-garments or no-recommendation state.
- If valid candidates exist, **randomly select exactly one**, display it, and persist the result as a Homepage recommendation (`RN-24`–`RN-26`).
- **Do not** invoke NLP interpretation, NLP request-weighted ranking or completed chat-history creation.
- **No user-facing Refresh Recommendation control.** Do not add one unless the requirement is explicitly changed (`FR-HR-09`).
- The UI may provide **Save outfit** and **Try it on** actions on the displayed recommendation; these delegate to their respective owning subsystems.

### 6.5 Result statuses and safe outcomes

Distinguish at least:

- `InvalidInput` (empty/whitespace text).
- `UnsupportedRequest` (not recognised as a supported outfit request).
- Insufficient or missing eligible garments (`NoEligibleGarments` / no recommendation).
- No valid candidate satisfying mandatory rules (`NoValidCandidates` / no result).
- A successful single recommendation.
- Processing/persistence errors with safe, user-readable feedback.

These represent **documented logical outcomes**; actual HTTP statuses, API JSON shapes, type names, and error codes must be confirmed or designed together with the live code and report. Do not confuse unsupported input with a genuinely supported request that has no valid outfit.

## 7. Conversation, history, saving and visualisation

### Single-request Outfit Assistant (`SW_UC06`)

1. User starts a **New Chat** and submits one text request.
2. `NLPRecommendationService` coordinates `NLPInterpreter` → garment retrieval → valid candidate generation → scoring/ranking.
3. If successful, return **one** outfit recommendation alongside the original request.
4. Save the successful interaction in **one atomic operation**, linking its `NLP_CHAT`, `RECOMMENDATION` and associated `RECOMMENDATION_ITEM` records.
5. Completed chat becomes **read-only**. A new request must start a **new** chat. If interpretation is unsupported or no valid recommendation exists, the design does **not** create a completed chat record.
6. Duplicate submission/retry handling must not create duplicate completed history records (`FR-CH-07`, `NFR-07`).

### History (`SW_UC08`)

- Registered User can list/search/open **only their own** completed recommendation chats.
- Empty search shows all their completed records; no match gives a controlled no-results message.
- Opening a record displays **stored original request** plus **its corresponding recommendation**. It is not a live multi-turn chat.
- Historical records are retained even when a garment later becomes unavailable/archived. Indicate that state without rewriting history.
- **Before saving or visualising an old recommendation, revalidate its current garment references**. Reject or explain stale/unavailable references; historical visibility is not proof of current wardrobe eligibility.

### Save an outfit (`FR-DW-16`–`FR-DW-20`)

- Recommendation passes identifiers/references to **Digital Wardrobe** for revalidation.
- Digital Wardrobe verifies current ownership, confirmation, availability and suitability of all constituent garment records.
- It creates an **`OUTFIT` + `OUTFIT_ITEM`** collection using existing garments; **no duplicate `GARMENT` records**.
- The report specifies `creation_type = recommendation` on the saved outfit; **do not create a direct Recommendation-to-Outfit foreign key** just to implement save.
- Only show a successful Save confirmation when the operation actually completes.

### Outfit visualisation (`FR-VIS-01`–`FR-VIS-16`)

- `RecommendationVisualisationService` checks user access to the selected Recommendation and passes its **Recommendation reference** via **`VisualisationGateway`**; do not supply an arbitrary browser-trusted final list of garments.
- Outfit Visualisation resolves referenced garments and **rechecks current wardrobe ownership/confirmation/availability**; it handles user personal-image validation and backend AI processing.
- Visualisation uses explicit processing states such as queued, processing, completed, failed or cancelled and represents an **AI outfit preview**, not accurate fit measurement.

## 8. Proposed architecture and boundaries

**Source:** report §§4.2–4.8, 4.11.

### Three tiers

| Tier | Responsibilities |
|---|---|
| Presentation | Component-based web frontend; account, Digital Wardrobe, homepage, Outfit Assistant/history, and visualisation UIs; submit HTTPS REST/JSON requests; display results/status; no direct DB access or heavy AI inference in browser |
| Application | **FastAPI modular monolith**; API routing, authentication/authorisation, service orchestration, garment processing/AI adapters, NLP, recommendation, chat history, save/visualisation integration |
| Data | **PostgreSQL** structured relational records and protected file/media storage; access mediated by backend repositories/data-access components |

**Target modules:** Account/Profile, Digital Wardrobe, Garment Processing, NLP Interaction, Recommendation Generation, Chat History, Outfit Visualisation, Data/File Access, AI Model Adapters, and shared auth/logging/error handling.

### Recommendation and NLP services (report §§4.4–4.5)

| Component/service | Approved responsibility |
|---|---|
| `NLPRecommendationService` | Coordinate request path; preferences, interpretation, eligible garments, valid candidates, scoring and completed-chat persistence |
| `NLPInterpreter` | Interpret one text input into `StructuredOutfitRequest` or controlled error |
| `GarmentRetrievalService` | Query `ConfirmedGarmentQuery`; apply recommendation-specific garment eligibility |
| `RecommendationEngine` | Generate candidate outfits and apply mandatory rules; reused by homepage and Assistant |
| `CandidateGenerator` | Build/category-group/deduplicate outfit combinations |
| `MandatoryRuleEvaluator` | Check required structure, explicit request constraints and compatibility |
| `RecommendationScorer` | Score/rank only valid Assistant candidates |
| `CandidateRanker` | Apply deterministic ranking and tie-break rules |
| `HomepageRecommendationService` | Choose **one random valid** outfit, independent of NLP/chat |
| `ChatHistoryService` | Persist/retrieve user-owned completed chats and linked recommendations |
| `RecommendationVisualisationService` | Authorise recommendation access; send recommendation reference through `VisualisationGateway` |

### Provided/required boundary interfaces (report §4.5.2)

- Provided to FastAPI routes: `INLPRecommendationService`, `IHomepageRecommendationService`, `IRecommendationVisualisationService`.
- Required external subsystems: `ConfirmedGarmentQuery` (**Digital Wardrobe → Recommendation**), `VisualisationGateway` (**Recommendation → Outfit Visualisation**).
- Repository contracts: `IPreferenceRepository`, `IRecommendationRepository`, `IInteractionRepository`.
- **No Recommendation-owned direct garment repository**, and no direct coupling from routes to internal persistence implementations.

### Suggested logical packages, according to design (report §4.5.3)

- `api`: routes; delegate to application coordination services.
- `application/recommendation`: outfit request orchestration, homepage selection, garment retrieval, candidate generation, rule evaluation, scoring/ranking.
- `application/nlp`: preprocessing, intent, extraction, controlled mapping and request construction.
- `application/chat_history`: history operations.
- `application/visualisation_integration`: Recommendation-to-Visualisation gateway coordination.
- `domain`: persistent domain entities plus temporary request/candidate/score value objects.
- `infrastructure`: repository implementations/data access.
- `shared_contracts`: repository and cross-subsystem interfaces.

**These are responsibility/package concepts from the report, not asserted existing directories.** Adapt to the actual repository while preserving the boundaries.

## 9. Database concepts and integrity

**Source:** report §4.8.2.

| Entity | Key design facts |
|---|---|
| `USER_PREFERENCE` | Many user-owned *type–value* preference entries, not one hardcoded set of columns; `weight`, `source`, `is_active` |
| `NLP_CHAT` | One submitted original request, interpreted intent and extracted information, status, creation/completion times; a completed record represents **one** successful request/result, not a threaded dialogue |
| `RECOMMENDATION` | User-owned recommendation; `recommendation_type` separates Homepage vs NLP; `chat_id` nullable; lifecycle/status; `request_match_score`, `compatibility_score`, `preference_score`, `total_score` |
| `RECOMMENDATION_ITEM` | Recommendation-to-Garment join; `recommendation_id`, `garment_id`, `garment_role`, `item_order`; multiple items per recommendation |
| `GARMENT` | Managed by **Digital Wardrobe**, not by the Recommendation subsystem |
| `OUTFIT` / `OUTFIT_ITEM` | Managed by Digital Wardrobe after validated saving; separate from Recommendation persistence |

### Integrity invariants

- `USER_PREFERENCE`, `NLP_CHAT` and `RECOMMENDATION` must always be scoped to the authenticated owner.
- Homepage Recommendation: `chat_id = NULL`; NLP Recommendation: completed result has a non-null `chat_id` identifying **only one** related Recommendation.
- Unique `(recommendation_id, garment_id)` so a garment cannot be duplicated inside the same recommendation; stable/unique `(recommendation_id, item_order)` is recommended.
- Successful NLP request, recommendation and item records must persist as one **atomic transaction**. Do not expose partial records as completed. Protect against duplicate submission.
- Foreign keys alone do **not** verify same-user ownership across linked chat/recommendation/garment records. Enforce ownership at the application/data-access boundary.
- Prefer validated controlled values for preference type, recommendation type, status, garment role and structured request fields.
- Persist recommendation-level scores with the same normalisation/weight rules as the algorithm; homepage scores may not apply because homepage does not run NLP scoring.
- Stale historical recommendations remain historically viewable but must not silently bypass current-state revalidation on Save/Try it on.

## 10. UI / interaction specifications

**Source:** report §§4.9.1–4.9.5. The report's UI mockups use a shared **AURA** layout (sidebar, spacing, consistent cards and restrained colour palette); inspect actual front-end designs before assuming exact styling.

### Homepage

- Display **one** randomly selected valid outfit based on confirmed available wardrobe garments.
- Show garment items together as one outfit; avoid exposing NLP/chat-specific controls or request ranking.
- Allow optional **Save outfit** and **Try it on**.
- **No Refresh Recommendation button**.
- Support insufficient garments, no valid outfit, loading and processing error states.

### Outfit Assistant request

- Natural-language text area, support hints for occasion/style/colour/category/formality, **New Chat** flow.
- One submitted request per interaction; use defaults for omitted optional fields, no clarification flow.
- Validate empty input; distinguish unsupported vs no valid outfit vs backend failure.

### Outfit Assistant result

- Display **original request** and exactly **one** recommended outfit on success.
- Result is read-only once completed; scores can be supporting display information, not user-editable inputs.
- Optional Save/Try it on delegates to other modules without changing/completing another chat.

### History

- Search/browse own completed chats, open original request and saved result, read-only display.
- Empty search lists personal completed records; show no-match feedback.
- Mark outdated garment references as unavailable but preserve original history and require revalidation for actions.

### Feedback

- Distinguish loading, success, invalid input, unsupported request, no-result, insufficient garments, unavailable historical item, and processing/storage error.
- Do not reveal credentials, exception stacks, implementation details or other users' data in messages.
- Only confirm a saved/processed operation **after backend success**.

## 11. Non-functional targets, security and quality

**Source:** report §§3.3.5, 4.11. These are **acceptance criteria / targets**, not accomplished test outcomes.

### Performance targets (baseline test conditions)

- `NFR-01`: homepage **one valid outfit within 3 seconds after homepage load completes**.
- `NFR-02`: NLP request returns one recommendation, no-result or unsupported response **within 5 seconds** after a valid request submission in the defined baseline environment.
- `NFR-03`: chat-history search **within 2 seconds** under the defined maximum history workload.
- Avoid unnecessary garment retrieval and score only candidates passing eligibility and mandatory checks; user-scoped indexes are part of the proposed performance design.

### Reliability / consistency

- `NFR-04`/`05`: failures must not crash the session or corrupt existing wardrobe/history.
- `NFR-06`: successful chat/request/recommendation atomic persistence.
- `NFR-07`: duplicate-submission protection.
- Input validation, safe controlled failure responses and appropriate diagnostic logging; never leak secrets.

### Authentication and data protection

- `NFR-08`/`09`: authenticated access and strict user ownership checks on wardrobe, requests, preferences, recommendations and history.
- `NFR-10`: validate request text and history search input; use safe parameterised database operations.
- `NFR-11`: HTTPS for authenticated data in deployed environment.
- `NFR-12`/`13`: do not expose tokens, credentials, stack traces or sensitive logs; log technical failure context without secrets.
- `NFR-24`/`25`: cross-subsystem references must use controlled interfaces and be checked for missing, malformed, unauthorised or stale IDs.

### UI, accessibility and maintainability

- `NFR-14`: clear user-oriented validation/failure messages.
- `NFR-15`: consistent UI arrangement and terminology.
- `NFR-16`: responsive within **360–1920px** viewport widths without horizontal scrolling.
- `NFR-17`: keyboard access for request submission/history search/open.
- `NFR-18`: text remains readable at **200%** browser zoom.
- `NFR-19`: target latest stable Chrome, Edge and Firefox at test time.
- `NFR-20`–`22`: modular separation, configurable scoring weights/rules, independent NLP interpretation updates.
- `NFR-23`: unit tests for success, unsupported, no result and failure paths.

## 12. Verification checklist to turn into tests

Use this checklist when implementing. Do not mark as passed without running tests and retaining evidence. See report §3.3.8, including Tables 3.23–3.24.

### NLP and intent

- [ ] Whitespace-only input → `InvalidInput` and no garment retrieval.
- [ ] Unsupported general-purpose request → `UnsupportedRequest`; no completed chat record.
- [ ] Supported request correctly extracts each of occasion, style, colour, garment category and formality when supplied.
- [ ] Missing optional fields produce documented null/defaults; no follow-up question.
- [ ] Fixed labelled dataset contains supported, partial, unsupported and no-result examples; evaluate against `RN-27` **80% target**.

### Eligibility / outfit rules

- [ ] Only garment records from the authenticated user's `ConfirmedGarmentQuery` result are used.
- [ ] Exclude missing required attributes and mandatory request/structure/compatibility failures **before scoring**.
- [ ] Prevent any fabricated IDs, garments or attributes.
- [ ] Remove duplicate candidate combinations.
- [ ] Return controlled no-result for an eligible request without a valid outfit.
- [ ] Verify `RN-28`: all generated outfits conform to current ownership, confirmation, availability and mandatory rules.

### Ranking / homepage

- [ ] Normalise scores and apply `S = w_r R + w_c C + w_p P` with weights summing to 1.
- [ ] Highest score wins; request > compatibility > preference > stable-ID tie-breaks.
- [ ] Exactly one valid Outfit Assistant recommendation on success.
- [ ] Homepage chooses exactly one random **valid** outfit; does not call NLP scoring.
- [ ] Homepage does not create an NLP chat and has no user-triggered refresh.

### Persistence / history

- [ ] Successful NLP chat + recommendation + items commit atomically.
- [ ] No partial completed chat on failure; no duplicate record on accidental resubmission.
- [ ] Completed chat is read-only; a new request starts a new chat.
- [ ] User A cannot read/search/access User B's garment/preference/recommendation/history resources.
- [ ] Historical result remains viewable if garments are later archived; Save/Try it on rejects stale garments through current-state revalidation.
- [ ] Saving a recommendation creates validated Outfit + OutfitItem records, with **no duplicate Garment** and no direct Recommendation→Outfit FK.

### Security and quality

- [ ] Safe malformed/unauthorised ID handling, request-input validation and parameterised DB operations.
- [ ] Clear error states, no secret/stack-trace exposure, failure-safe transaction behaviour.
- [ ] Test responsiveness, keyboard navigation, 200% zoom, and documented baseline performance targets.

## 13. Source report map — where to look for more detail

| Report section | Topic |
|---|---|
| §§1.1–1.5 | Background, problem, objectives, contributions, supported scope and exclusions |
| §1.7 | Two-person project responsibility split and integration |
| §§2.7–2.12 | Preference modelling; compatibility; recommendation; ranking/scoring; NLP interaction; evaluation approaches |
| §3.2 | Iterative/incremental methodology, iteration and risk planning |
| §3.3.1 | Requirements sources: literature/documents, existing applications, scenarios, supervisor consultations |
| §3.3.3 | Use-case diagrams and use-case flows, notably `SW_UC05`, `SW_UC06`, `SW_UC08` |
| §3.3.4 | Functional requirements `FR-ACC`, `FR-PP`, `FR-DW`, `FR-HR`, `FR-OA`, `FR-CH`, `FR-VIS` |
| §3.3.5 | `NFR-01`–`NFR-25` |
| §3.3.6 | `RN-01`–`RN-30` |
| §3.3.7 | `CA-01`–`CA-...` constraints and assumptions |
| §3.3.8 | Requirements traceability and planned verification matrix |
| §§4.2–4.3 | Object-Oriented Design, 4+1, three-tier architecture |
| §§4.4–4.5 | Domain classes; Recommendation Engine/NLP classes; component interfaces/packages |
| §4.6 | Activity and sequence models for Homepage, Outfit Assistant and Chat History |
| §4.7 | Deployment and runtime responsibility boundaries |
| §4.8 | ERD, entity descriptions, integrity and ownership rules |
| §4.9 | UI design, mockups and feedback states |
| §4.10.1 | `InterpretOutfitRequest` algorithm |
| §4.10.2 | `FilterRecommendationEligibleGarments` algorithm |
| §4.10.3 | `GenerateValidCandidates` algorithm |
| §4.10.4 | `ScoreRankAndSelect` weighted ranking and tie-break |
| §4.10.5 | `GenerateHomepageRecommendation` algorithm |
| §4.11 | Security, reliability, performance, reproducibility and accessibility design |

## 14. Recommended way to start a Codex session

1. Place this file in the project, preferably at **`smart-wardrobe/docs/FYP_CONTEXT.md`** (create the `docs` folder only if needed). Optionally place the full project report in `docs/` for detailed references; the report contains additional figures, tables, complete requirements and use-case flows.
2. Ask Codex to inspect the **real repository** and existing `AGENTS.md`, then read this file. **Do not overwrite existing AGENTS.md** or invent file paths without checking.
3. Suggested first Codex instruction:

```text
Read docs/FYP_CONTEXT.md and all applicable AGENTS.md files. Inspect the existing repository, including frontend, backend, ai-services, README, database schema/migrations and tests. Do not change files yet. Summarise (1) what is already implemented, (2) what differs from the FYP design, (3) integration blockers, and (4) the smallest safe implementation step for my NLP and Recommendation subsystem. Reference the relevant FR/NFR/RN requirements. Treat FYP_CONTEXT.md as intended design, not proof of implementation.
```

4. For a specific feature, provide Codex the **requirement IDs** and ask for a short implementation plan and tests before code edits.
5. Keep design amendments explicit: when the implementation legitimately departs from the report, note the decision and reason in project documentation rather than silently changing behaviour.

---

**End of context.** This document intentionally prioritises **source-derived design decisions** and concrete development invariants. It contains no claims about test results, a finished backend, model accuracy, or repository features that have not been inspected.
