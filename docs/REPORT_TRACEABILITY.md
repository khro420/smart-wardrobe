# Report-to-repository traceability

## Approved shared integration corrections (Phase 5F-2E Integration)

`RECOMMENDATION_SOURCE_ACTIONS.md` and `PHASE_5F_INTEGRATION_VERIFICATION.md`
supersede prior audit descriptions of the review payload and recommendation-source
action defects. Unsupported review keys are removed without expanding ReviewItem;
supported existing collections/tags are preserved. Saving and recommendation-source
visualisation reuse the strict transaction-bound Phase 1 contract. Saving creates
one idempotent independent Outfit without modifying Recommendation/chat/scoring
history. Queued recommendation visualisation is revalidated before inference,
with no transaction held during inference. This supports FR-DW-09/11/16-19,
FR-VIS-01-05/08, RN-11/23/28 and report sections 4.6.4/4.8.2. Six existing app
files and one new action helper are the only intentional backend source changes;
frozen scoring archives/oracles remain unchanged and exact integration hashes
are separately pinned. No schema, CV, VTON, generation, scoring, ranking,
experimental-policy default or historical frontend action activation occurs.

## RN-17 reviewed evidence and coverage readiness (Phase 5F-2E-1)

`COMPATIBILITY_EVIDENCE_READINESS.md` and the versioned collection/schema under
`docs/datasets` define actual garment/image provenance, independent review
declarations, exact 0-4 ratings, reference/development/locked-validation splits
and explicit lookup-exemplar selection. Offline import and coverage tools reuse
existing structure-aware signatures, reference validation and full structural
streams. They do not score unknown references as zero, discard candidates, install
a session gate, change weights or activate compatibility. Synthetic probes and
unit-test ratings are separate from human evidence. The real collection is empty;
RN-17 remains partial until reviewed coverage/quality and activation are approved.
RN-15/16/18-23 boundaries and completed-2D1 application source are preserved.
`PHASE_5F_2E_1_EVIDENCE_VERIFICATION.md` records commands, measured probe coverage,
memory/time limitations and outstanding independent review/NFR-02 evidence.

## Exact score-validation arithmetic investigation (Phase 5F-2D-2D2)

`PHASE_5F_2D_2D2_SCORE_VALIDATION_VERIFICATION.md` records the frozen completed-2D1
reference, independently archived corrected integer-arithmetic trial, 932-case
numeric/error/subclass comparisons, full stream comparisons, fresh ABBA timings
and regressions. The prototype is **not retained in production**: reductions in
Fraction operations did not establish a sufficiently consistent application
benefit. All 156 application Python/JSON files match completed 2D1; its approved
progress optimization remains. This preserves RN-15-21 / sections 4.4.3/4.10.4,
independent score validation, exact weights/ties, eligibility and completion.
No NFR-02 compliance or final FYP acceptance is claimed. Compatibility remains
deferred, suitability opt-in and approximate hex matching disabled. No base-outfit
intermediates, mandatory cache, member reuse, pruning or Phase 2D3 work is included.

## Fully validated stream progress construction (Phase 5F-2D-2D1)

`PHASE_5F_2D_2D1_PROGRESS_VERIFICATION.md` records the independently frozen
completed-2B reference, per-construction/per-yield differential traces, historical
score fingerprints, fresh ABBA benchmarks, validation counts and regressions.
Only exact-base-type normal progress copying changes to fresh, fully validated
constructors; subclasses and terminal/error paths retain generic replacement.
RN-15-21, sections 4.4.3/4.10.4, mandatory eligibility, exact scoring, tie order,
complete-stream guarantees and persistence remain unchanged. Large-wardrobe
performance improves incrementally; small slower cells are reported. Neither
NFR-02 five-second HTTP/browser compliance nor final FYP acceptance is claimed.
Compatibility remains deferred, suitability opt-in and approximate hex matching
disabled. No score arithmetic shortcut, mandatory cache, member reuse, pruning,
teammate workflow change or Phase 2D2 optimization is included.

## Scoring hot-path equivalence and bounded reuse (Phase 5F-2D-2B)

`PHASE_5F_2D_2B_SCORING_VERIFICATION.md` records the independent completed-2A
source reference, incremental preparation/reuse measurements, exact differential
streams, cache bounds and regression evidence. This supports preserving RN-15–21
and report sections 4.4.3/4.10.4 while investigating NFR-02; it does not establish
five-second HTTP/browser compliance or final FYP acceptance. Scoring weights,
mandatory eligibility/gates, structural completeness, deterministic tie order,
full-stream completion and persistence semantics remain unchanged. Compatibility
is deferred, suitability opt-in, approximate hex matching disabled. No pruning
or validation shortcut is authorized. See the verification report for remaining
performance limits and separately deferred teammate workflow blockers.

## End-to-end audit and performance diagnosis (Phase 5F-1)

`PHASE_5F_REQUIREMENTS_AUDIT.md` maps each FR-HR-01–12, FR-OA-01–12,
FR-CH-01–16, RN-12–23 and NFR-01–05 to actual code/executed evidence and
distinguishes report requirements from approved implementation policies.
`PHASE_5F_VERIFICATION.md` records the isolated production-browser/real-HTTP
workload, raw-sample methodology, performance diagnosis, security and teammate
coordination. This supersedes any interpretation of functional phase closure
as full FYP acceptance: RN-17 compatibility is partial; NFR-02 fails at 200
garments; the normal review/confirmation journey remains blocked.

Evidence tooling: `frontend/playwright.phase5f.config.ts`,
`frontend/tests/phase5f/`, `backend/tests/phase5f_server.py`,
`backend/tests/test_phase5f_audit.py`, `backend/scripts/summarize_phase5f.py`
and `backend/scripts/profile_phase5f_auth.py`. Generated raw measurements,
profiles, evaluation reports and dependency audits are under ignored
`storage/verification/phase5f/`. No production algorithm, shared UI behaviour,
database migration, colour/suitability activation or Phase 5F-2 remediation
is performed by this phase.

## Recommendation frontend integration (Phase 5E)

`frontend/app/page.tsx` and `components/HomepageRecommendation.tsx` connect
FR-HR-01–12/RN-24–26 to the homepage API: automatic single-result generation,
page-flow idempotency, no refresh control and no chat/NLP/scoring call.
`app/assistant/page.tsx`/`components/OutfitAssistant.tsx` connect FR-OA-01–12,
FR-CH-07/NFR-07 to the integrated pipeline: one locked request, stable retry key,
explicit New Chat, completed read-only restoration and controlled outcomes.
`app/history/page.tsx`, `app/history/[chat_id]/page.tsx` and
`components/CompletedChatView.tsx` connect FR-CH-08–16 to authenticated searchable,
paginated history, race protection and historical garment display.

`frontend/lib/api.ts` preserves bearer authentication and structured errors;
the additive authenticated capability endpoint and explicit `pipeline=integrated`
guard prevent disabled-feature fallback without changing legacy callers.
`frontend/tests/recommendation.spec.ts` and
`backend/tests/test_frontend_recommendation_boundary.py` provide verification.
See `FRONTEND_RECOMMENDATION_INTEGRATION.md` for flags, ownership, reproduction
and limitations. NFR response-time acceptance is not established by these small
fixtures. The existing garment-review 422/409 blocker remains teammate-owned.

## Completed history backend (Phase 5D)

ChatHistoryService/ChatHistoryQuery provide authenticated GET /chats and /chats/id
for coherent owned completed Assistant interactions, including saved legacy
recommendations. Unicode case-insensitive literal search escapes LIKE wildcards;
signed anchored keyset pagination exposes totals and continuation. Detail reuses
Phase 5A historical restoration without NLP/ranking, retains unavailable item
identities and suppresses inaccessible media. Read-only SQLite URI/query_only
connections prohibit writes. This supports FR-CH-08–15 and the retrieval side of
FR-CH-01–16; successful creation remains Phase 5A/5C. See
[history contract](CHAT_HISTORY_CONTRACT.md). NFR-03 needs defined-workload/browser
verification; the separate 22.53s Assistant performance issue remains unresolved.

## Outfit Assistant backend integration (Phase 5C)

Default-off OutfitAssistantService connects existing NLPInterpreter,
RequestCandidateEngine, RecommendationScorer/eligibility gate and Phase 5A atomic
storage. This supports FR-OA-01–12, FR-CH-01–07/13–16 and report 4.4.3/4.8.2/4.10.4;
frontend controls, searchable history and final quality/performance validation
remain incomplete. Explicit compatibility_deferred (.70/0/.30) is interim;
compatibility stays Unavailable/NULL. Suitability is separately opt-in, unknown
hex unpromoted, no unsupported fallback. Original/structured text, exact score
metadata and captured user preference evidence are retained. See
[Assistant integration contract](OUTFIT_ASSISTANT_INTEGRATION.md).

## Homepage backend (Phase 5B)

Explicitly opt-in HomepageRecommendationService uses Phase 1/3A acquisition and
complete structural generation, uniform O(1)-sample reservoir selection and
Phase 5A atomic persistence with NULL chat/scores. Durable retry lookup precedes
generation; concurrent commits resolve to the same original record. No NLP,
preferences, scoring, Assistant ranking or chat creation is used. This supports
FR-HR-01–12/RN-24–26 and report 4.10.5; actual automatic browser triggering and
NFR-01 display timing await frontend integration. See
[Homepage backend contract](HOMEPAGE_RECOMMENDATION.md). New POST is default-off;
old Assistant endpoints and teammate workflows remain unchanged except the
legacy Assistant list excludes chatless Homepage records to preserve readability.

## Recommendation persistence foundations (Phase 5A)

Independent RecommendationRepository/SqliteRecommendationRepository implement
atomic successful Homepage/Assistant storage, scoped durable idempotency,
historical item snapshots and exact scoring/policy metadata. This supports
FR-HR-12, FR-CH-01–07/13–16 and report sections 4.8.2/4.10.4–4.10.5.
The Phase 1 adapter optionally borrows the writer's transaction connection;
strict confirmed/user-owned/available eligibility and both public methods remain
unchanged. BEGIN IMMEDIATE protects snapshot comparison and all writes against
concurrent SQLite writers. Separate additive migrations audit historical conflicts
without repair. PostgreSQL DDL is supplied but not deployment-verified.

See [persistence contract](RECOMMENDATION_PERSISTENCE.md). Live endpoints,
selection, existing history readers, save-as-outfit and visualisation remain
unchanged. New read-model semantics are explicitly selected, not activated in
legacy APIs. Strict recommendation-source action validation remains deferred for
teammate coordination. Neither aesthetic compatibility validation nor Phase 5B
Homepage orchestration is claimed complete.

## Structure-aware whole-outfit experiment (Phase 4B-A)

`HolisticRecommendationScorer`/`HolisticCompatibilityScorer` specialize the
existing scoring roles and reuse Phase 4A R/P, eligibility, exact score objects
and ranking. New structure-aware immutable signatures contain one actual dress
member or top/bottom, with optional outerwear. `compatibility_reference_policy.py`
validates review provenance and exact 0–4 normalization. Production references
are empty; populated synthetic fixtures require explicit test opt-in.

This supports the architecture/formula in sections 4.4.3/4.10.4 and RN-15–RN-21.
Exact signature/reference semantics are user-approved experimental policies, not
report-prescribed fashion rules. Known zero, unknown evidence/reference and
unavailable policy remain distinct. Coverage is reported per structure; missing
references neither exclude dresses nor reject otherwise valid sessions. The
v2 experimental profile is explicit, leaving Phase 1–4A source/contracts and
all live/default/persistence/frontend behaviour unchanged. No full compatibility
accuracy, RN-28 or NFR performance achievement is claimed. See
[Whole-outfit compatibility](OUTFIT_COMPATIBILITY_POLICY.md) for synthetic worked
examples, held-out protocol, coverage limitations and future activation decisions.


## Independent preference/scoring/ranking infrastructure (Phase 4A)

The report's five scoring classes are implemented independently under
application/recommendation, with a SELECT-only ActivePreferenceQuery adapter,
explicit preference normalization, exact versioned profiles and immutable score
wrappers. This maps RN-15–RN-21, sections 4.4.3/4.10.4 and the preference
type/value design in 4.8.2. FR-PP-03/05 motivate controlled scoring semantics;
the permissive account APIs/storage and existing notes are unchanged.

Request coverage, preference weighted averages and shared-style Jaccard are
approved implementation policies, not report-mandated functions. The heuristic
is experimental and rejects unpaired candidate sessions rather than penalizing
a single dress or changing per-candidate weights. The separately selected
deferred profile is interim and does not complete final compatibility scoring.
No live integration, persistence/history writes, suitability default activation,
hex approximation, frontend or Phase 1–3 contract changes occur. Full RN-28
validity, personalisation quality and NFR response targets are not claimed.
See [Recommendation scoring](RECOMMENDATION_SCORING.md) for formulas, exact
worked examples, verification, capability limits and the unchanged 422/409 blocker.


## Opt-in declaration suitability infrastructure (Phase 3B-3A)

`suitability_policy.py`, `config/suitability_policy.v1.json`,
`suitability_evidence_mapper.py`, `occasion_evaluator.py`, `formality_evaluator.py`
and `suitability_request_evaluator.py` add an explicitly selected evaluator via
the existing factory injection. Frozen declaration evidence is in
`domain/value_objects/garment_suitability_evidence.py`. Default/live behaviour and
completed contracts remain unchanged. Exercise/formal remain unavailable.

RN-12/13/15 and sections 4.10.2–4.10.3 motivate mandatory evaluation; RN-23
requires unavailable data to remain unknown. Exact reserved tags and all-garment
aggregation are user-approved implementation rules, not report-specified fashion
rules. No full RN-28 validity, independent appropriateness, Phase 4 scoring or
NFR-01/02 performance result is claimed. Tests cover policy scenarios, the real
backend tag lifecycle, strict eligibility and stream completion. The existing
frontend review payload mismatch is reproduced without teammate file changes.
See [Occasion/formality policy](OCCASION_FORMALITY_POLICY.md) for diagnostics,
manual-entry/provenance/staleness limitations and coordination requirements.


## Experimental Oklab infrastructure (Phase 3B-2A)

`recommendation/oklab.py`, `prototype_colour_classifier.py`,
`config/colour_prototypes.v1.json` and `domain/value_objects/colour_classification.py`
implement deterministic experimental naming and abstention. All prototypes are
initial unreviewed candidates. `colour_dataset.py` and
`scripts/evaluate_colour_classifier.py` validate partitioned labels, detect
overlap and assess supplied experiments; calibration cannot select validation.
No real calibrated thresholds or achieved holdout results exist.

This supports future RN-12/13/15 evidence and RN-23 integrity; the report does
not define Oklab or thresholds. Phase 3B-1 mandatory evidence stays exact/named
only. Full RN-28 validity and NFR-01/02 performance are not established.
See [Colour classification](COLOUR_CLASSIFICATION.md) for methodology, tests,
the empty-extraction black fallback and separate performance work.


## Minimum request constraints (Phase 3B-1)

The independent RequestCandidateEngine/Session wraps Phase 3A without changing
its contract. RequestConstraintEvaluator implements collective category/group
membership, global primary-colour presence and positive style evidence on at
least one base garment. GarmentEvidenceMapper caches classification per session;
ColourClassifier uses Phase 2 aliases and W3C-defined exact anchors only.
Immutable evidence/evaluation objects are in
`domain/value_objects/request_candidate_evaluation.py`.

This maps the implemented portions of RN-12–RN-16 and sections 4.10.2–4.10.4.
Unknown evidence never satisfies a requirement. Occasion/formality returns
PolicyUnavailable (Phase 3B-3), approximate hex classification remains disabled
(Phase 3B-2), and scoring/ranking/persistence integration is not implemented.
See [Recommendation rules](RECOMMENDATION_RULES.md) for approved policy details,
limitations and tests. Full RN-28 and end-to-end recommendation validity are not
claimed. `tests/test_request_candidates.py` and
`scripts/benchmark_request_candidates.py` verify minimum policies and exhaustive
versus optimized filtering equivalence.

## Structural candidate generation (Phase 3A)

See [Recommendation rules](RECOMMENDATION_RULES.md) for user-approved compositions
and the structural-only validity/completion protocol. Independent retrieval,
CandidateGenerator, MandatoryRuleEvaluator and RecommendationEngine are in
`backend/app/application/recommendation/`. Immutable candidate/result objects
are in `backend/app/domain/value_objects/`; versioned structure configuration is
`application/recommendation/config/structure.v1.json`.

This implements the structural portions of RN-11–RN-16, RN-22/23 and CA-03/04,
with report sections 4.4.3, 4.5.2 and 4.10.2–4.10.3 as design references.
Garments come only from Phase 1's injected strict query. Optional NLP conditions
return PolicyUnavailable until Phase 3B; candidates are not fully request-valid
or compatibility-valid. No live API, selection, scoring or persistence behavior
is changed. `tests/test_structural_candidates.py` verifies structures and stream
integrity; `scripts/benchmark_structural_candidates.py` records exhaustive
counts, time and working memory without silent truncation or invented thresholds.

## Independent NLP interpretation (Phase 2)

See [NLP request contract](NLP_REQUEST_CONTRACT.md) for the approved vocabulary,
five-field/category-group representation, conservative failure semantics and
evaluation limitations. `backend/app/application/nlp/` implements the six
classes from section 4.4.4 and the section 4.10.1 interpretation algorithm.
Immutable request/outcome objects are in `backend/app/domain/value_objects/`.
The vocabulary is versioned in `application/nlp/config/vocabulary.v1.json`.

This maps RN-01–RN-10, RN-27 and the NLP portion of RN-29/RN-30, FR-OA-05/09/11,
CA-07/08/10 and NFR-10/12/20/22. It is not wired to routes, the placeholder
recommendation algorithm, garment acquisition or the frontend. Occasion
recognition never claims wardrobe suitability. Per-garment colour bindings
cannot be represented by the approved schema and are explicitly unsupported.

`backend/scripts/evaluate_nlp.py` evaluates the frozen 120-case labelled resource
and records expected/actual fields, outcomes, provenance and metrics. RN-27
achieves 100% intent and 100% field accuracy on this author-labelled synthetic
benchmark; combined exact match is reported without an additional threshold.
This is not independently collected user evidence or end-to-end recommendation
validation. `backend/tests/test_nlp_interpreter.py` and `test_nlp_evaluation.py`
cover interpretation, boundaries, immutable types and metric/data integrity.

## Recommendation garment data contract (Phase 1)

See [Garment data contract](GARMENT_DATA_CONTRACT.md) for the approved strict
confirmation policy and immutable read model. The report-aligned
`ConfirmedGarmentQuery.get_confirmed_available_garments(user_id)` is implemented
in `backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py`,
with snapshots in `backend/app/shared_contracts/confirmed_garment_snapshot.py`.
The composition root injects this query through
`backend/app/application/ports/recommendation_runtime.py`; recommendation
acquisition consumes snapshots without reading the wardrobe table directly.

This maps RN-11, CA-04, FR-DW-11 and NFR-08/09/20/24/25 from Chong Wei Ping's
report. Only owned, available garments with linked confirmed processing items
are returned. Legacy ID queries retain their ownership/availability-only policy;
unlinked, accepted, pending, rejected or missing provenance is excluded only
from the new query. Contract coverage is in
`backend/tests/test_confirmed_garment_snapshot.py`. NLP, eligibility rules,
compatibility, scoring, ranking and homepage generation remain outside Phase 1.

The Phase 1 correction preserves both string/list fit and material values,
enforces constructor-level immutability, and distinguishes malformed optional
collections using `invalid_attributes` from missing or explicitly empty values.
This metadata does not alter garment eligibility, database records, frontend
responses or recommendation selection.

For the verified upload-to-wardrobe development slice, figure/table mappings,
demo commands and explicit remaining report gaps, see
[Garment workflow handoff](GARMENT_WORKFLOW_HANDOFF.md).

For the VTON runtime contract, pinned CatVTON assets, lifecycle, frontend flow,
hardware boundary, evaluation commands, and O3 acceptance matrix, see
[VTON implementation handoff](VTON_HANDOFF.md).

## Deployment and root folders

| Report component or requirement | Repository location |
| --- | --- |
| Figure 4.13 Presentation Tier | `frontend/` Next.js application |
| Figure 4.13 FastAPI Application Runtime | `backend/app/` |
| Figure 4.13 GPU-capable Python AI Inference Runtime | `backend/app/infrastructure/ai/` with `backend/models/` |
| Figure 4.13 PostgreSQL + pgvector Data Tier | `backend/migrations/001_initial_schema.sql` |
| Figure 4.13 Protected Image / File Storage | `backend/app/infrastructure/media/`; generated local state is `storage/media/` |
| AIR-01 to AIR-07 training/evaluation artefacts | `backend/datasets/`, `backend/scripts/`, `backend/runs/` |

## Figure 4.8 package diagram

| Report package | Repository package |
| --- | --- |
| `api`: garment-processing, wardrobe, visualisation routes | `backend/app/api/`; `recommendation_routes.py` is the report's accompanying NLP/recommendation integration boundary |
| `application`: garment processing, wardrobe, visualisation, ports | `backend/app/application/`; `recommendation/` implements the report's NLPChat/Recommendation flow without adding an extra Figure 4.8 top-level package |
| Shared account/profile responsibility in the overall class diagram | `backend/app/application/account/`, `backend/app/api/account_routes.py` |
| `domain`: entities and value objects | `backend/app/domain/` |
| `infrastructure`: AI, persistence, media | `backend/app/infrastructure/` |
| `shared_contracts` | `backend/app/shared_contracts/` |

## Requirement and implementation mapping

| Report design responsibility | Implementation location |
| --- | --- |
| Authenticated ownership boundary and `USER_PREFERENCE` lifecycle | `backend/app/infrastructure/security.py` (scrypt password hashing and signed bearer tokens), `backend/app/application/account/account_service.py`, `frontend/app/profile/` |
| Protected `MEDIA_ASSET` metadata and opaque storage | `backend/app/infrastructure/media/protected_media_store.py` |
| `PROCESSING_JOB` / `PROCESSING_ITEM` lifecycle | `backend/app/application/garment_processing/` |
| Segmentation, VTOFF, attribute/embedding and VTON ports/adapters | `backend/app/application/ports/`, `backend/app/infrastructure/ai/`; deterministic segmentation-baseline evidence is generated by `backend/scripts/verify_vtoff_standardisation.py`. Model-backed VTOFF uses the pinned official multi-garment TryOffDiff v2 adapter, keeps the observed crop as fallback, and is evaluated on a cleaned paired VITON-HD slice by `backend/scripts/prepare_vitonhd_vtoff_evaluation.py` and `backend/scripts/evaluate_vtoff_paired.py`. The same evaluator accepts an officially licensed DressCode manifest from `backend/scripts/prepare_dresscode_vtoff_evaluation.py`. Real 768-D SigLIP embeddings are implemented in `attribute_embedding_adapter.py` and audited by `backend/scripts/evaluate_visual_embeddings.py`. |
| Candidate review and confirmed persistence | `backend/app/api/garment_processing_routes.py`, `backend/app/application/wardrobe/wardrobe_service.py` |
| Transactional `GARMENT`, `OUTFIT`, `OUTFIT_ITEM` save | `backend/app/application/wardrobe/wardrobe_service.py` |
| `NLP_CHAT`, `RECOMMENDATION`, `RECOMMENDATION_ITEM` lifecycle | `backend/app/application/recommendation/recommendation_service.py`, `backend/app/api/recommendation_routes.py`, `frontend/app/page.tsx` |
| Personal-image and `VISUALISATION` lifecycle | `backend/app/application/visualisation/`; queued claim, cancellation, recovery, controlled errors and completion validation are exercised in `backend/tests/test_vton_contracts.py` |
| Visualisation from a saved `OUTFIT` or persisted `RECOMMENDATION` | `VisualisationPrepare`, `VisualisationCreate`, `outfit_visualisation_service.py`, `frontend/app/try-on/page.tsx`; persisted recommendation history is `frontend/app/history/page.tsx` |
| Frozen `VISUALISATION_ITEM.source_media_id` provenance | `backend/app/application/visualisation/outfit_visualisation_service.py` |
| Image upload to crop/VTOFF comparison and review flow | `frontend/app/extract/`, `frontend/lib/api.ts` |
| Profile retrieval and permitted display-name editing | `frontend/app/profile/`, `backend/app/api/account_routes.py` |
| Register, login, and logout user goals | `frontend/app/auth/`, `backend/app/api/account_routes.py`, `backend/app/infrastructure/security.py` |

The production VTON implementation is the pinned original SD-based CatVTON mix
runtime in `backend/app/infrastructure/ai/catvton_runtime.py`. Its generated
output is distinct from the explicitly labelled development-copy adapter. The
O3 auditor is fail-closed. The real checkpoint and official licensed DressCode
evidence are now present: the paired 30-sample CatVTON evaluation covers ten
fixed-seed examples each for upper body, lower body and dresses. It retains
input/output hashes, model-asset provenance, configuration, hardware, latency,
peak VRAM, per-group SSIM/LPIPS/DISTS results and manually reviewed visible
failure labels. The authoritative O3 matrix is
`storage/verification/o3/requirements-audit.json` and records 18/18 passed.

## Objective O1 acceptance matrix

Objective O1 is complete against the report mapping: **25/25 requirements passed**.
The authoritative item-by-item acceptance statements and evidence paths are in
`storage/verification/o1/requirements-audit.json` and mirrored under
`backend/runs/o1/requirements-audit.json`.

| Report requirements | Completed behavior | Primary evidence |
| --- | --- | --- |
| FR-01–FR-05 | Authenticated image entry/upload, decoded validation, instance segmentation, category/box/mask/confidence | `tests/test_garment_workflow.py`; held-out segmentation audit/results |
| FR-10–FR-16 | Candidate display/correction/selection, individual or collective persistence, constituent garments, atomic save | `tests/test_garment_workflow.py`; O1 browser workflow |
| FR-17–FR-21 | Manual outfits, recommendation-to-outfit integration, separate collections, browse/search/sort/filter and ownership | `tests/test_o1_wardrobe.py`; `tests/test_workflow.py`; O1 browser workflow |
| FR-22–FR-24 | Permitted garment/outfit edits, favourites, dependency preview, explicit archive confirmation and safe block policy | `tests/test_o1_wardrobe.py`; O1 browser workflow |
| FR-37–FR-39 | Failure integrity, state/timestamp/error/media traceability, cancellation and restart recovery | `tests/test_garment_workflow.py` |
| AIR-01–AIR-02 | Exact 32,153-image/49,523-instance conversion audit; precision/recall, box/mask mAP, 13 per-category records, 20 labelled failures | `storage/verification/segmentation/held_out_evaluation/` |

Release evidence also records 38/38 backend tests, a passing frontend lint and
production build, a no-error real-browser walkthrough, and an isolated capacity run
at 500 garments plus 1,000 outfits per user with unchanged schema and database
integrity. Reproducers are `backend/scripts/verify_o1_capacity.py`,
`backend/scripts/verify_browser_workflow.py` and
`backend/scripts/audit_o1_requirements.py`.

`backend/app/infrastructure/persistence/postgresql_repository.py` is the runnable local SQLite compatibility implementation. `backend/migrations/` is the authoritative PostgreSQL + pgvector deployment schema. The local store preserves the same named entities, statuses, ownership predicates, and visualisation source invariant so development and test flows do not claim PostgreSQL execution when a database server is absent.

## Objective O2 acceptance matrix

The earlier O2 delivery record below describes the September 2026 interim state.
Its former DressCode deferral has now been closed by the local, officially
authorised paired-test audit at
`storage/verification/vtoff/dresscode_dataset_audit.json`, followed by 30-example
category-balanced TryOffDiff and CatVTON evaluations. These are reconstruction
quality experiments only; they do not establish real-world garment size or
physical-fit accuracy.

| Report requirements | Current result | Primary evidence or remaining gate |
| --- | --- | --- |
| FR-06 | Passed | TryOffDiff v2 is a genuine optional reconstruction; crop/mask remain observed evidence and the crop is always the default/fallback. |
| FR-07–FR-08 | Passed, with quality warning | All 13 category-to-role/layer mappings, colour metadata and real embeddings are present. Weak and subjective fields remain directly reviewable/editable. |
| FR-09 | Passed | Real finite L2-normalised 768-D vectors pass processing-to-garment persistence. A live PostgreSQL 16 + pgvector run loaded the extension, verified both `VECTOR(768)` columns, and transactionally round-tripped 768 dimensions through `processing_item` and `garment`. |
| FR-10–FR-18, FR-20–FR-21, FR-38 | Passed | 45 backend tests plus the frontend production build cover correction, preferred-media choice, atomic individual/outfit saving, recommendation-to-outfit saving, ownership and traceability. |
| AIR-03 | User-deferred; not passed | The 30-pair cleaned VITON-HD upper-body evaluation is complete. On 2026-09-06 the user closed the current delivery while deferring lower-body and dress paired evaluation until DressCode is obtained under its authors' official agreement. Prepared code samples all three groups, validates generation-cache provenance and refuses evaluation completion until 10–20 metric-ranked failures have substantive visual labels. |
| AIR-04 | Passed | Generated assets are separately identified, warned, reviewed and never silently preferred. |
| AIR-05 | Passed, with quality warning | A blind 39-item held-out audit reports metrics and 12 labelled failures; a 104-item embedding audit reports retrieval metrics and 12 labelled failures. Temperature accuracy is 89.7%; coarse colour and dominance are only 35.9% and 38.5%, so they are not treated as authoritative. |
| AIR-07 | Passed for executed experiments | VITON-HD VTOFF, attribute, embedding and pgvector records include versions/hashes or schema identity, config, seeds, concrete CPU/GPU/OS details, timing, VRAM where applicable, terminal status, error arrays, failures and limitations. The fail-closed O2 auditor validates these fields. No DressCode evaluation evidence is claimed. |

The recommendation contract in
`backend/app/shared_contracts/confirmed_garment_query.py` exposes opaque garment
identifiers only. Its SQLite adapter filters by both caller ownership and
`available` status. Resolution and save paths reject archived or foreign items;
no internal NLP interpretation or ML ranking is claimed as O2 work.


## Phase5F-2E-Integration-UI: historical recommendation actions

| Requirement | Evidence added |
|---|---|
| FR-DW-16-20 | CompletedChatView explicitly enables historical saving; RecommendationResult uses saved-state GET and strict save POST; real browser confirms normal Outfits collection and repeat/concurrent ID stability. |
| FR-VIS-01-04 | Historical recommendation source flows through existing prepare/create/status APIs; supported source tested end-to-end, stale/foreign/outerwear sources rejected without partial outfits. |
| FR-CH-01-16 (preserved) | Original request and recommendation remain read-only; SQL/API equality tests, no extra generation/chat, unavailable cards, owner access, existing search/pagination/New Chat regressions. |
| Section4.6.4 | Independent saved Outfit/Visualisation actions leave historical interaction unchanged, as explicitly described in the report. |

See [HISTORICAL_RECOMMENDATION_ACTIONS.md](HISTORICAL_RECOMMENDATION_ACTIONS.md) for the
phase-specific file inventory, exact commands, test results and live-model limitations.
This frontend integration does not establish final FYP acceptance or RN-17 activation.


## Phase 5F-2E-3A: experimental rule-based compatibility infrastructure

| Requirement | Evidence and limitation |
|---|---|
| RN-17 / sections4.4.3,4.10.4 | Exact approved colour/style C and two opt-in R/C/P profiles. No live activation or human fashion-quality claim. Single-dress and incomplete-evidence policies remain activation blockers. |
| RN-15-16 / RN-28 | Existing independent scoring gate and Phase1 query reused unchanged; real DB and tampering tests. |
| RN-18-21 | Existing exact weighted score and deterministic ranker reused; numerical comparison only after mandatory validation, no final winner from an incomplete/unknown-covered stream. |
| RN-24-26 | Homepage remains independent/random, with no new aesthetic hard threshold; this phase does not claim closing additional Homepage compatibility policy gaps. |
| NFR-02 | Complete synthetic backend time/memory measurements; no HTTP/browser five-second acceptance claim. |

See [RULE_BASED_COMPATIBILITY.md](RULE_BASED_COMPATIBILITY.md) for the phase-specific
inventory, commands/results, synthetic-data interpretation and single-dress options.


## Phase 5F-2E-3C-1: exact compatibility pair-cache optimisation

| Requirement / contract | Evidence and limitation |
|---|---|
| RN-17 / sections 4.4.3, 4.10.4 | Separate cached experimental twin preserves existing colour/style rules, exact C, Unknown/NotApplicable and evidence provenance; no fashion-quality claim or live activation. |
| RN-15-16 / RN-28 / Phase 1 | Unchanged strict query and independent gate; actual SQLite eligibility tests, changed snapshots/policies, owner and parallel-session isolation tests. |
| RN-18-21 / Phase 4A | Exact R/P, weighted score, ranker, full-stream completion, count and failure semantics preserved against original Phase 3A oracle. |
| NFR-02 | Six alternating full-backend timing pairs at each of five workloads; 200-garment cached medians 21.307s / 46.502s. Additional bounded memory documented; no end-to-end target compliance claimed. |
| Frozen source integrity | Original 157 application files, seven Phase 3A additions and five frozen archives unchanged; only three separately pinned experimental application additions. |

See [COMPATIBILITY_PAIR_CACHE.md](COMPATIBILITY_PAIR_CACHE.md) for exact commands,
counts, hit rates, memory, regression results and retention decision. This phase
does not establish final FYP acceptance or start the later decision-policy phase.


## Phase 5F-2E-3C-2: explicit compatibility decision policy (offline only)

| Requirement / contract | Evidence and limitation |
|---|---|
| RN-17 / sections 4.4.3, 4.10.4 | Separate immutable raw/decision representation, exact bounds and midpoint; no-pair reference permits all four structures. Conventions and 60/20/20 weights are approved experimental policies, not report-defined measurements or human quality validation. |
| RN-15-16 / RN-28 / Phase 1 | Existing strict acquisition and independent scoring verifier unchanged. Mandatory Fail/Unknown cannot be overridden by soft conventions. |
| RN-18-21 / Phase 4A | Existing score validation and ranker reused through explicit versioned ComponentScore subtype; exact total -> R -> decision -> P -> stable ID, one result only after complete stream/close. |
| Data design / score provenance | Disposable real SQLite tests retain raw Unknown/NA as NULL and exact decisions/bounds/coverage/identity in existing metadata. Explicit versioned offline decoder exactly reconstructs totals; no production migration or repository change. |
| NFR-02 | All five workloads benchmarked against cached Phase 3A using repeated matched passes and separate peak RSS. Decision validation adds runtime cost; no end-to-end acceptance claim. |
| Integrity / production boundary | Original 157 files, seven Phase 3A additions, three cache files and frozen archives preserved. Live compatibility-deferred service, Homepage selection, suitability and approximate-hex defaults unchanged. |

See [COMPATIBILITY_DECISION_POLICY.md](COMPATIBILITY_DECISION_POLICY.md) for all
files, exact commands, verification results and limits. Live activation, consumer
presentation/provenance review, quality evidence and NFR-02 remain separate gates.


## Phase 5F-2E-3C-3A: decision performance and activation-readiness audit

| Requirement / contract | Evidence and limitation |
|---|---|
| RN-17 / sections 4.4.3,4.10.4 | Separate prepared implementation preserves original decision-policy arithmetic and all measured/conventional evidence. No new fashion-accuracy claim. |
| RN-15-16 / Phase 1 | Strict query, mandatory evaluation and independent scoring verification unchanged; differential tests retain failure/unknown rejection. |
| RN-18-21 | Original decision and score constructors still validate every candidate; same exact scores, deterministic winner, metadata and complete-stream/failure outcomes. |
| Data design / historical records | Disposable SQLite and actual history restoration verify all raw/decision bases and exact replay without writer/schema changes or historical rewrites. Live service/profile/UI integration remains unapproved. |
| NFR-02 | Focused A/B/C/D profiling and six alternating complete runs at every requested workload; backend, HTTP and browser are distinguished. No truncation or five-second acceptance claim. |
| Source integrity | Original 157 files, seven Phase 3A, three cache files, five Phase 3C-2 additions and frozen archives preserved; two separately pinned new experimental modules only. |

See [DECISION_SCORER_PERFORMANCE.md](DECISION_SCORER_PERFORMANCE.md) for measured
results, exact commands, retain/revert decision and the minimum separately
approved activation stage. Default/live compatibility remains deferred.

## Phase 5F-2E-3C-3B — controlled Assistant integration

The default remains compatibility-deferred. Explicit server-only
`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE=experimental_compatibility_decision_v1`
selects the prepared decision scorer; this is not default-on deployment approval.

| Requirement / boundary | Evidence |
|---|---|
| RN-17–21; §§4.4.3/4.10.4 | Exact `.60R+.20C_decision+.20P`, original gate, tie order, complete stream and pinned policy; existing deferred arithmetic unchanged. |
| RN-15/16; NFR-24/25 | Existing Phase 1 query, mandatory evaluator, independent gate and transaction-bound snapshot revalidation retained. |
| FR-OA; NFR-06/07 | Real Assistant/SQLite/API tests cover one result, exact metadata, eight rollback stages, concurrent retry, conflict and idempotent replay. |
| FR-CH; NFR-08/09 | Shared read-only stored-evidence projection, legacy deferred preservation, profile changes, stale wardrobe and cross-user History denial. |
| FR-DW / FR-VIS boundary | Existing action paths unchanged; regression tests include actual historical save/visualisation with development AI and strict stale-source checks. |
| NFR-14/15 | Minimal shared decision-aware component distinguishes calculated rules, unknown evidence, midpoint conventions and single-piece no-pair reference. |
| NFR-02 | Separate real service, authenticated HTTP and production-browser measurements; five-second target unchanged, slow workloads remain acceptance gaps. |
| Integrity | Original 157-file reference retained; 154 current files unchanged and exactly three authorized integration replacements separately pinned. Old experimental files/manifests/archives unchanged. |

See [ASSISTANT_DECISION_INTEGRATION.md](ASSISTANT_DECISION_INTEGRATION.md) for
actual commands/results, workload qualifications and remaining activation gates.
Suitability stays opt-in; approximate hex remains disabled. No human fashion
quality validation or final application/FYP acceptance is claimed.

Phase 3C-3B final measured limitation: 90 retained service/HTTP/production-browser
trials yielded 81 completed responses and nine production-proxy failures. Default
200-garment browser median/max: 22.387/22.668s. Experimental 100-garment browser
median/max: 7.298/7.685s; all experimental 200-garment browser trials reset around
30s. Both stress-browser groups failed. NFR-02 remains UNMET on these tested
workloads; backend commit after proxy failure does not constitute browser success.
Functional tests pass, the known architecture assertion remains, and default-on /
general deployment / final FYP acceptance are not approved.

### Phase 5F-2E-3C-3C: NFR-02 diagnosis and exact aggregation reuse

See [ASSISTANT_NFR02_DIAGNOSIS.md](ASSISTANT_NFR02_DIAGNOSIS.md) for original
NFR-02 wording, its unspecified baseline conditions, separate scalability tests,
actual-path profiling, HTTP/browser errors, transaction safety and verification.
RN-17's experimental exact 0.60/0.20/0.20 formula and decision conventions remain
unchanged. A bounded session cache reuses only immutable numeric compatibility
summaries; independent eligibility, exact score validation, full enumeration,
deterministic ranking and transactional snapshot revalidation remain active.
The original prepared scorer and earlier frozen archives remain differential
references. Only the explicitly selected experimental factory uses the new
coordinator; deferred remains the default. Local performance improvement is not
NFR-02 acceptance, human compatibility validation, or production approval.

### Phase 5F-2E-3C-3E: isolated compact exhaustive scoring

See [COMPACT_EXHAUSTIVE_ENGINE.md](COMPACT_EXHAUSTIVE_ENGINE.md) for the source
freeze, architecture, exact numerical/mandatory equivalence argument, authored
files, complete verification commands and retained raw evidence. RN-17 still
requires scoring every mandatory-valid candidate: lazy compact products enumerate
all four existing structures, independently verify eligibility, calculate and
validate exact R/C/P/total, and rank by the original role/garment-ID tie key.
Complete-stream accounting and full public winner reconstruction must succeed
before selection. No candidate pruning, compatibility policy or weight change is
introduced. Strict acquisition and commit-time snapshot revalidation remain the
unchanged Phase 1/persistence responsibilities.

The current retained aggregated scorer is the primary experimental differential
reference. All 178 pre-existing application files and 31 earlier reference files
remain byte-identical; the compact executor has a separate source manifest and
new pre-phase archive. Actual service, database, HTTP and production-browser
integration uses an isolated test-only provenance bridge. Live factories,
Homepage, frontend application code and historical records are unchanged.

NFR-02 retains its original five-second valid-NLP-response requirement. Matched
HTTP/browser results, failed proxy trials, backend completion, diagnostic timings
and memory observations are reported separately. A measured configuration below
five seconds does not establish formal acceptance without the report's missing
baseline workload/environment definitions. The 200-garment and outerwear-heavy
cases remain scalability evidence. Retention of this isolated experiment is not
approval for production integration, default activation, human fashion-quality
validation or final FYP acceptance.

Executed evidence: 123 focused tests passed; each broad profile run passed 1,666
tests with the same existing architecture assertion failure. Large audits compared
305,060 full candidate records with zero mismatches. The 100-garment compact
browser medians were 1.365 s deferred / 1.777 s experimental, versus 3.870 / 6.511 s;
200 garments remained above five seconds. The original matrix stopped at 141/144
trials under observed memory pressure; its failures and separate stress browser
repeat remain retained. Both compact repeat trials succeeded while both retained
reference browser requests timed out and later committed. Retain this experiment
as PASS WITH LIMITATIONS; no live scorer, default or policy activation is approved.

### Phase 5F-2E-3C-3F: controlled compact execution integration

See [COMPACT_ENGINE_INTEGRATION.md](COMPACT_ENGINE_INTEGRATION.md) for the actual
Assistant integration, exact verification commands, resource-labelled timing
evidence and proposed formal NFR-02 test plan. The server-only execution setting
`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE` defaults to `reference`; explicit
`compact_exhaustive` is independent of the unchanged scoring-profile allowlist
and deferred default. Both settings reject unknown values at startup. Clients
cannot override them through request bodies or arbitrary query parameters.

RN-17/section4.10.4 remain exhaustive and exact: the unchanged compact core scores
every independently mandatory-valid candidate, finishes its complete ledger and
reconstructs/verifies the public winner before the original service persists it.
Immutable prepared metadata replaces the service's direct captured-session
provenance dependency without fabricating stream completion. New compact records
identify their actual executor; all scoring-policy/evidence provenance remains
unchanged. Existing atomic writes, strict transaction-bound garment revalidation,
durable idempotency and read-only historical restoration remain authoritative.

Only two existing application files are modified for wiring/context consumption;
three application modules are added. Existing frozen archives and the five compact
kernel files remain unchanged, with a new explicit before/after integrity chain.
No migration, frontend application/API change, Homepage change, scoring rule,
pruning, parallel worker or asynchronous recommendation workflow is introduced.

The report's five-second NFR-02 bound is unchanged. Current measurements do not
retroactively establish the report's unspecified baseline workload/hardware/
concurrency/statistic. Before/after resource observations and every timeout remain
retained, including populations with competing CPU activity. The proposed formal
test plan requires separate approval; integration is not final FYP acceptance or
approval to change either default. Suitability stays opt-in; approximate hex and
pattern scoring remain disabled.

Final Phase3F verification:271 focused tests passed. Broad deferred/experimental
collections passed1,752/1,771 tests respectively, each with the unchanged
`test_report_architecture.py` `ai-services` assertion failure. Four-way browser
functional tests28 passed; existing browser regressions35 passed; actual compact
timeout/retry/rollback/concurrency safety passed. TypeScript, lint, isolated
production build and `git diff --check` passed (existing lint/deprecation warnings
remain; CV geometry was not executed in the unavailable dedicated environment).

The main96 matched timing trials retained seven reference browser proxy failures
and no compact transport failures; all backend jobs settled. A separate56-trial
20/50/100 repeat had no transport errors; populations are not pooled. Exact
semantic fingerprints agree within and across applicable populations. At100
garments all observed compact browser calls were below five seconds; at200 and
outerwear-heavy stress they were not. CPU contention remained visible in both
populations, and the original report's numeric baseline remains undefined.
Functional integration is PASS WITH LIMITATIONS; formal NFR-02/final FYP
acceptance remains unapproved. Neither default has changed.

## Phase 5F-2E-3C-3G: compact-default readiness (transition not applied)

See [COMPACT_DEFAULT_READINESS.md](COMPACT_DEFAULT_READINESS.md) and the inactive
versioned [transition plan](config/assistant_execution_transition.v1.json).
Current execution/scoring defaults remain `reference` / `compatibility_deferred`;
the Assistant feature flag, algorithms, source-integrity pins, APIs, atomic
persistence and historical semantics are unchanged. No application source or
database migration is added. The JSON plan is not loaded by the application and
requires separate approval before deployment activation.

RN-17/section4.10.4 four-way focused regressions passed291 tests. Both backend
profile collections passed1,797 tests each with the same existing `ai-services`
architecture assertion failure. Actual-service four-way browser tests28 and
existing browser regressions35 passed. TypeScript, ESLint and isolated production
build pass; existing navigation/deprecation warnings and unexecuted dedicated CV
geometry verification remain documented separately.

New actual-composition tests verify captured in-flight contexts in both engine
directions/profiles, exact historical replay after rollback, atomic failed-write
recovery with the same key, unchanged defaults and rejected invalid startup
settings. These validate application-level replacement, not an untested deployed
load balancer, graceful-drain configuration or crash-recovery mechanism.

NFR-02 retains the original five-second bound. The proposed baseline specification
explicitly includes diverse attributes, request/preference variants,30 consecutive
repetitions per defined case, browser terminal-response boundaries and retention
of every slow/failed response. Hardware, workload and statistic choices are
pending approval; earlier homogeneous measurements are not that formal dataset.

The new controlled collection was blocked before any timed request: after the
test/build workloads finished, idle CPU observations remained72%,82%,90%.
`storage/verification/phase5f2e3c3g/transport-controlled-1.json` retains the
preflight and zero trials; its collection-test exit1 is an environment block,
not a new recommendation regression or a zero-error latency result. Earlier
Phase3F timing files/timeouts remain unchanged. Controlled20/50/100/200/stress
comparisons, formal NFR-02 acceptance and production-default approval remain
outstanding. Experimental scoring remains default-off independently of engine
readiness; no subsequent phase is started.

### Resumed Phase3G controlled comparisons

After the owner paused heavy applications and OneDrive syncing, the resource
observer's confirmed OneDrive CPU activity fell to near zero. Two additional
preflights remain retained with zero timing trials. Test-only collection-controls
1.1.0 waits up to120s for three consecutive unchanged20%-CPU/4GiB-RAM qualifying
observations, preserving every settling observation; no request warm-up or NFR
threshold change. Final qualifying CPU values were14%,20%,7%.

`transport-controlled-4.json` completed96 matched trials. Compact had0/48
transport failures; reference4/48, all stress browser proxy timeouts. Every backend
job settled and all10 workload/profile fingerprint groups match within the run
and the retained Phase3F population. Backend, HTTP and visible browser timings
are separately retained; no candidate truncation or proxy-timeout increase.

Compact100-garment browser medians/maxima: deferred0.732/0.780s,
experimental0.927/1.048s. At200 garments: deferred5.038/5.140s (2/3 over5s),
experimental6.017/6.039s (3/3 over5s). Stress exceeds5s for both profiles.
An HTTP-only4.491s deferred200 median is not a passing browser result.

During collection, OS-reported CPU ranged3-73%, so a passed preflight does not
prove continuous isolation. Later native counters showed low load but cannot
conclusively attribute every earlier spike. Formal NFR-02 remains unaccepted:
the proposed mixed-evidence acceptance baseline is unapproved, and the current
homogeneous matched workload is separate diagnostic/scalability evidence.

Engineering readiness is PASS WITH LIMITATIONS for a separately owner-approved
controlled default-transition decision, not blanket production/FYP acceptance.
Both production/source defaults remain reference/deferred. Existing291-focused,
1,797-per-profile backend and28/35 browser results are retained, not claimed as
rerun; application/frozen-source hashes remain unchanged. Resumed changes are
limited to test preflight tooling, documentation and new evidence. Experimental
scoring, suitability activation and approximate colour matching remain unchanged.


## Phase 5F-2E-3C-3H ? compact default activation (functional PASS WITH LIMITATIONS)

Owner-approved execution-default transition only: `compact_exhaustive` replaces
`reference` as the default Assistant executor. `compatibility_deferred` remains
the scoring default; experimental compatibility remains explicitly selected.
See [activation and rollback record](COMPACT_DEFAULT_ACTIVATION.md) and
`config/assistant_execution_transition.v2.json`. Historical v1 review records
remain unchanged. No report-defined scoring formula or five-second NFR-02
requirement changes. RN-17/exact ranking, authenticated strict garment retrieval,
atomic history/idempotency and historical replay are covered by differential,
restart, concurrency and regression tests. Final verification evidence will be
recorded in the activation document. NFR-02 remains OPEN; formal baseline and
final FYP acceptance are separate approval decisions.

Phase 3H final verification: focused 292 passed; broad backend 1,798 passed and
one unchanged ai-services architecture assertion; browser four-way 28 passed,
legacy 35 passed; TypeScript/lint/isolated production build passed. All prior
37 frozen fixture files and 61 Phase 3G evidence files unchanged; only three
application defaults changed. Targeted browser sanity is RESOURCE BLOCKED:
40 preflight samples, CPU 40?71%, RAM 1.91?2.53 GiB, zero timed submissions.
The collector failure/trace is retained and is not an application latency
result. Final Phase 3H closure awaits a resource-qualified nine-call retry;
NFR-02 remains OPEN under its unchanged five-second requirement and separately
unapproved formal baseline. No later phase or experimental scoring activation.


Phase 3H resumed sanity attempt: the owner's precheck was quiet, but the new
collector recorded 42 CPU observations spanning 15 to 90% and stopped at its
unchanged resource gate. RAM was sufficient (8.31 to 9.82 GiB); zero timed
requests ran. Active OneDrive/user Chrome/Discord processes were identified.
Both blocked attempts and all earlier results are retained. See the resumed
section of COMPACT_DEFAULT_ACTIVATION.md. Closure/performance acceptance remains
pending; no code default, scoring, timeout or eligibility changes on resumption.


Phase 3H final quiet retry supersedes the earlier pending sanity status:
preflight CPU 19/11/16%, approximately 11.4 GiB free RAM; nine actual-default
browser requests succeeded (three each at 50/100/200 garments), no failures.
Medians 0.190/0.684/4.542s; maxima 0.234/0.695/4.573s. All selected-member,
exact-score and semantic provenance fingerprints match the corresponding
Phase 3G compact/deferred results. Both blocked attempts and all earlier
above-five-second/stress evidence are retained. Functional/default transition
is ready for owner closure as PASS WITH LIMITATIONS; NFR-02 remains formally
unaccepted and its five-second requirement/baseline approval unchanged.
No further algorithm/default/profile changes occurred during verification.
See COMPACT_DEFAULT_ACTIVATION.md for exact commands, inventory and limitations.


## Phase 5F-2E-3J-1 - saved-Outfit visualisation eligibility and snapshot revalidation

Owner-approved correction for original FR-VIS-04 (PDF176/printed165).
`SAVED_OUTFIT_VISUALISATION_ELIGIBILITY.md` records the implementation, exact
commands/results, disposable confirmation inventory and remaining limitations.
Saved-Outfit sources now require the same injected transaction-bound Phase1
owned/available/confirmed-item/job-owner proof. New requests preserve every
ordered member and fail closed on unproven NULL/manual/legacy records, unsupported
roles/categories and invalid media; valid manually assembled confirmed outfits
remain supported without recommendation composition constraints.
Queued saved sources are re-resolved and compared against the complete frozen
ID/media/category/role/order tuple before inference, within the existing short
claim transaction. Stored configuration is preserved. No GPU waiting/inference
transaction, data repair, migration, frontend/default/scoring/policy activation
or teammate model change is included. Recommendation-source semantics are retained.

The approved source transition is separately versioned in
`backend/tests/fixtures/saved_outfit_visualisation_sources.v1.json`; old archives,
pins and closed Phase3H/I/J evidence remain unchanged. Actual API-confirmed
synthetic disposable fixtures establish source/transaction behaviour, not real
model quality, deployment inventory or PostgreSQL concurrency. FR-VIS-04's
identified saved-source implementation gap is corrected; real VTON/deployment
acceptance and outerwear scope remain separate. Overall FYP acceptance and
formal NFR acceptance are not established by this change. Wait for owner review.

Phase3J-1 final verification: **97 focused passes; 1,854 broad backend passes
and one unchanged ai-services architecture assertion; 35 browser passes;
git diff --check exit0**. The pre-edit inventory and targeted frozen-source guard
each passed. Initial fixture-setup and digest-helper failures are retained.
All38 earlier fixture/archive files and closed3H/I/J reports are byte-identical;
only two production VIS files changed. Ready for owner closure as PASS WITH
LIMITATIONS for the supported source-validation contract, not final FYP/model/
deployment/NFR acceptance. Dedicated CV geometry/model tests were not executed.


## Phase 5F-2E-3J-2 - forward style evidence semantics and wardrobe edit preservation

Explicit owner/teammate approval covers the scoped shared wardrobe/frontend
correction. `docs/FORWARD_STYLE_EVIDENCE.md` documents the contract, changed files,
raw commands/results and limitations. Omitted style updates preserve canonical,
dedicated and legacy-mirror representations; explicit null/[]/assigned tags remain
missing/known-empty/known values through actual review, confirmation, edit and
Phase1 retrieval. Partial frontend payloads and explicit Unknown/Empty actions
prevent display blanks from erasing evidence. A short BEGIN IMMEDIATE read/merge/
write transaction prevents lost concurrent style updates. No schema, query/scoring
contract, mandatory rule, NLP, feature flag, VIS algorithm or default changes.

Existing historical [] intent is not recoverable without owner evidence; records
are not bulk reclassified or repaired. Malformed legacy JSON may block ordinary
editing and remains a separately scoped data-quality issue. Recommendation/chat/
VIS snapshots are preserved, and closed3J-1 source checks remain unchanged.
The separately versioned `forward_style_sources.v1.json` records only this phase's
one backend/three frontend application changes; prior archives/pins remain intact.
Final verification and closure status follow in the implementation report. This
work does not enable RN-13 suitability or activate RN-17 scoring, and does not
establish formal NFR or final FYP acceptance. Wait for owner review.

Phase3J-2 final evidence: **195 focused backend passes; 1,895 broad backend
passes and one unchanged ai-services assertion; 42 browser passes plus10
restarted final-code style/action passes; TypeScript, lint, isolated production
build and git diff --check passed**. Lint retains two existing navigation warnings.
All39 historical fixtures/archives and closed3J-1 VIS files/reports are unchanged.
Initial failures/interrupted runs remain recorded. Ready for owner closure as
PASS WITH LIMITATIONS for forward style evidence; no automatic RN-13 development,
RN-17 activation or NFR acceptance follows.


## Phase 5F-2E-3J-3: owner-declared suitability controls

Owner/teammate-authorised wardrobe controls expose existing eight-occasion/two-formality reserved declarations and preserve unknown/conflicting/malformed evidence. Conditional custom-tag PATCH protects concurrent replacement within the existing SQLite write transaction. See `OWNER_DECLARED_SUITABILITY_CONTROLS.md` and `storage/verification/phase5f2e3j3/commands.txt` for source inventory and verification. RN-13 remains bounded/incomplete pending separate suitability activation/scope acceptance; exercise/formal/general hex remain unavailable. Compact/deferred, opt-in evaluator, disabled approximate hex and all completed contracts remain unchanged. No NFR/model/deployment acceptance is claimed.

J-3 final verification:177 focused passes; archival check1 pass; final broad backend1,948 passes and only the retained ai-services assertion;54 browser passes; TypeScript/lint/isolated build/diff checks pass.303 baseline hashes and40 prior fixtures checked. Ready for owner review as PASS WITH LIMITATIONS; no evaluator/default activation or full RN-13/NFR acceptance.


## Phase 5F-2E-3J-4: controlled suitability end-to-end verification

Test-only explicit suitability activation exercises all eight approved occasions/two formalities through authenticated compact/deferred Assistant, four structures, five-field NLP, every-member evidence, Fail precedence, current-state filtering and immutable retry/history. See `CONTROLLED_SUITABILITY_VERIFICATION.md` and `storage/verification/phase5f2e3j4/commands.txt`. No production/default, grammar, schema, scoring, eligibility or legacy-routing change. RN-13 is verified only for the tested enabled bounded owner-declaration scope; full acceptance still requires owner/supervisor scope approval and separate release activation. Exercise/formal/arbitrary hex remain unavailable; formal NFR and real model/deployment acceptance are not claimed.

J-4 final:269 focused passes plus1 additional capture pass;2,036 broad backend passes with the unchanged ai-services assertion;54 default-off browser passes plus1 enabled real journey; TypeScript/lint/isolated production build/diff checks pass.371 baseline hashes and41 historical fixture files checked. Controlled bounded verification PASS WITH LIMITATIONS; deployment default remains false and full RN-13/NFR acceptance is not claimed.


## Phase 5F-2E-3J-5: three-component scoring verification

Owner-accepted experimental_compatibility_decision_v1 tested through genuine confirmed wardrobes, independent Fraction oracle, all structures/evidence bases, both profiles and engines, suitability and immutable replay. See `THREE_COMPONENT_SCORING_VERIFICATION.md` and `storage/verification/phase5f2e3j5/commands.txt`. Production compact/deferred and suitability-default-off remain unchanged; no model/schema/eligibility/grammar/legacy-route changes. Functional RN-17 evidence is bounded; default activation and NFR acceptance remain separate. Final performance/activation assessment is in that report.

J-5 checkpoint:456 focused passes, supplementary competition1 pass,2,064 broad passes plus the known ai-services assertion,28 four-way production-browser passes and1 real experimental+suitability browser pass; TypeScript/lint/build/diff checks pass. Independent exact comparisons across10 fixed cases show expected profile-dependent winners. Targeted50/100/200 timing is pending active OneDrive contention; no new latency claim. DEFER scoring-default transition until the authorised controlled sanity is collected; J-5 not ready for closure at this checkpoint.

J-5 resumed/final: after owner paused syncing,8 retained preflight observations qualified at9/18/19%CPU;36/36 actual HTTP/browser submissions completed with exact fingerprints and exhaustive counts. Experimental200 HTTP median5.952s/max6.015s, browser6.069s/max6.103s; all six exceed5s. Deferred200 browser median4.631s/max4.658s. No errors/timeouts; all trials retained. Verification ready to close PASS WITH LIMITATIONS, but recommend DEFER scoring-default activation pending separately approved targeted performance work and formal baseline acceptance. No defaults or production source changed; NFR-02 remains open.


## Phase 5F-2E-3J-6: exact numeric score-certificate reuse

Measured compact scoring/validation overhead led to one bounded correction in compact_scoring_facts.py,retaining all pair visits,mandatory verification,exact score/provenance and all candidates. New before/after hash transition and byte-exact old implementation leave earlier baselines intact. Final610 focused passes,29 differential passes,2,094 broad passes with only the known ai-services assertion,29 browser passes,TypeScript/lint/build/diff checks. See THREE_COMPONENT_PERFORMANCE_CORRECTION.md and phase5f2e3j6 raw artifacts. Post-change clean36-trial sanity is pending active CPU contention; no latency improvement or NFR acceptance claimed yet. Default scoring remains deferred,suitability default-off; current activation recommendation DEFER and phase not ready for closure pending performance.

J-6 owner-requested20:06 recheck led to first collector attempt j6-initial:44 preflight observations,CPU17-76%,RAM8.84-8.99GiB,zero timed submissions,resource_blocked. OneDrive had resumed dominant CPU activity; pause requested. This is not a new recommendation latency failure or NFR result. Prior semantic/regression passes retained; clean performance still pending,defaults unchanged.


J-6 final retry: resource gate passed; 36/36 transport requests HTTP201, exact J-5 fingerprints, zero errors/above5s. Experimental200 browser median/max4.844/4.964s (prior6.069/6.103); deferred3.363/3.371s (prior4.631/4.658). See THREE_COMPONENT_PERFORMANCE_CORRECTION.md and phase5f2e3j6 raw evidence. J-6 ready for closure PASS WITH LIMITATIONS, superseding pending checkpoint. Defaults unchanged; activation requires separate owner review. NFR-02 remains formally unaccepted; narrow maximum headroom, synthetic distribution, snapshots and deployment/concurrency limitations retained. Initial resource-blocked attempt and all prior failures preserved.


## Phase 5F-2E-3J-7: evidence diversity and release gate
Owner-closed J-6 retained. Verification-only:no production source/default/policy change. Two frozen synthetic stratified mixes retain17,710/134,820 structural candidates at100/200;not empirical wardrobe frequencies. Full numeric before/current equivalence610,120 scores;286 focused tests pass. Varied200 experimental2,019 keys,11,480 misses,11,224 evictions,91.49% reuse under unchanged256 bound. Main56 transport submissions produce48 selected records,4 correct HTTP terminals,4 retained browser locator measurement errors;5 responses exceed5s. Generic experimental200 five-browser trials4.746-4.820s,but constrained style5.208s and suitability deferred6.344/6.686s,experimental9.169/9.865s. Resource disturbance retained. Terminal timing retry resource-blocked,zero submissions;separate4 functional browser cases pass,not replacement timing. TypeScript/scoped lint/diff checks pass. See EVIDENCE_DIVERSITY_RELEASE_GATE.md and phase5f2e3j7 raw evidence/commands. Release recommendation DEFER;NFR-02 remains open/formally unaccepted. Terminal browser timing,approved provider/baseline,real distribution and deployment/concurrency remain unresolved. No optimisation,activation or later phase authorised by this result.


## Phase 5F-2E-3J-8: bounded suitability diagnosis and one conditional correction
J-7 owner-closed PASS WITH LIMITATIONS;release gate not passed. Profiles show parsing already session-scoped(~13ms),scoring numeric input reconstruction material. One production file prepares immutable request detail templates;primary/independent mandatory sources unchanged,all policies/defaults/cache bounds unchanged.538focused and2,361broad tests pass;known ai-services assertion remains. Full462,252scores match frozen facts across539,280structural examinations,cache ledgers/winners exact. Two blocked zero-request attempts retained. Fresh before16/corrected20 requests all correct,including4corrected terminal timings. Corrected suitability browser median6.316sdeferred/6.629sexperimental;all8corrected suitability observations exceed5s. Call counts reduced but end-to-end benefit mixed/not established. See SUITABILITY_HOT_PATH_DIAGNOSIS.md,phase5f2e3j8 raw evidence and commands. Recommendation SUPERVISOR SCOPE DECISION REQUIRED;stop optimisation,no J9/default activation. NFR-02 remains open/not formally accepted,200capacity/provider/scope/distribution/concurrency/completion boundary still need approval.
