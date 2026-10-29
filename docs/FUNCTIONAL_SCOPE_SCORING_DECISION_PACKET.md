# Phase 5F-2E-3J: functional scope and scoring decision packet

2026-10-22, Asia/Kuala_Lumpur. **DESIGN / APPROVAL PREPARATION ONLY.**
Phase3I is owner-closed PASS WITH LIMITATIONS. This packet makes recommendations,
not approvals: no code, routing, flags, models, migrations or historical data
changed. Compact/deferred remain the actual defaults; suitability stays opt-in
and approximate hex matching disabled. The93-row audit is not repeated.

Authority: original Project I report, RN-13/RN-17 (PDF188), FR-VIS-04 (PDF176),
NFR01/02/03 (PDF180), sections4.4.3 (PDF232-233),4.10.4 (PDF285-288), and current
`FINAL_ACCEPTANCE_READINESS_REVIEW.md`. Exact scoring rules/conventions below are
implementation policies, not numerical rules imposed by the report.

## D1. RN-17 recommendation: ACCEPT for bounded functional use

**ACCEPT the existing experimental_compatibility_decision_v1 policy as the
proposed FYP standard heuristic; do not activate it until the owner separately
approves activation and verification.** Do not claim independently validated
fashion quality. Live RN-17 remains Partial until approved activation occurs.

This refines Phase3I's proposal for further review: the suggested24 examples/two
reviewers are an optional broader quality pilot, not an RN-17 acceptance
prerequisite. The report requires documented R/C/P criteria for every valid
candidate; it does not impose a new human-review sample size or accuracy target.
Existing independent arithmetic/differential tests and the explicit analytical
examples below are sufficient evidence for accepting the implemented calculation
as a bounded heuristic, provided the owner accepts its disclosed conventions.
No human ratings have been supplied or fabricated.

| Policy to accept unchanged | Meaning / limitation |
|---|---|
| S=(3/5)R+(1/5)C_decision+(1/5)P |Exact0.60/0.20/0.20, common0-1 scale, no per-candidate weight renormalisation. Every mandatory-valid candidate scored; complete stream required. |
| Colour: identical or achromatic |Recognised equal primary colours or black/white/grey member ->1; other known pairs ->0. A coordination proxy, not proof that other pairings clash. Only approved names/aliases/exact anchors. |
| Style: Dice |2*intersection/(sizeA+sizeB) on known nonempty supported sets, not a garment-style prediction or proof of style identity. |
| Whole candidate |Average real pairwise colour/style atoms; pairs1/0/1/3 for top-bottom/dress/dress-outerwear/trio. No fake dress member or garment-count reward. Pattern/fit/material not scored. |
| Missing evidence |M atoms, known sum K, unknown count m: L=K/M, U=(K+m)/M, decision=(L+U)/2. Raw Unknown remains Unknown; this is a decision convention, not probability/confidence. |
| Single dress |Raw NotApplicable, zero pairs, separately recorded NoPairReference1/2. No measured dress rating or automatic perfect score. |
| Ranking/provenance |Total,R,C_decision,P,stable ID; exact fractions and stored original metadata. Computed/PartiallyConventional/FullyConventional/NoPairReference are distinct and explained in UI/API. |

R and P remain unchanged: R averages supplied fields; matching-base style fraction
can distinguish mandatory-valid candidates, while passed hard category/colour
fields usually contribute1. P uses supported stored type/value preferences and
importance weights; no preferences contributes0 with NoPreferences diagnostics,
not a perfect match. Hard conditions always precede all scoring.

Minimum analytical sign-off, using synthetic descriptors rather than ratings:

| Example | R,C_decision,P | Exact S |
|---|---|---:|
| Blue vintage top + white vintage bottom, requested vintage |1,1,0 |4/5 |
| Blue vintage top + red classic bottom, requested vintage |1/2,0,0 |3/10 |
| Blue vintage dress, requested vintage |1,1/2,0 |7/10 |
| Vintage top + bottom missing style/colour |1/2,1/2,0 |2/5 |
| First pair plus red classic outerwear |1,1/2,0 |7/10 |
| Vintage dress + white outerwear with unknown style, known coordinating colours |1,3/4,0 |3/4 |

Independent Fraction arithmetic was checked without importing application scorers;
these six totals match the current configured weights. Existing
`test_compatibility_decision.py` already covers independent atomic bounds, exact
weighted arithmetic, every structure winning/replay, annotation removal,
request/preference independence, tampering and fail/unknown before scoring.
Phase3H retains292 focused passes,1,798 backend passes plus the known architecture
failure, and28/35 browser passes. Those suites were not rerun in this phase.

The owner must explicitly accept these effects:

- An unknown atom contributes1/2 rather than measured0; removing a known low
  observation can improve rank. Unknown is never promoted to mandatory Pass.
- A dress or fully unknown pair can beat a known low-score pair without measured
  evidence of superior appearance. Conventional provenance must remain visible.
- Style appears in R, C and possibly P: different roles, correlated signals.
  Current weights do not claim statistical independence or eliminate double reward.
- Compared with deferred, R/P weights also change from.70/.30 to.60/.20.
  Example: requested vintage; A=red/green vintage pair, B=blue/white vintage pair;
  equal preference weights for red colour and top group give P_A=1,P_B=1/2.
  Both R=1; C_A=1/2,C_B=1. Deferred chooses A (1 versus17/20).
  Experimental totals both9/10, then C chooses B. This is a policy trade-off,
  not evidence of improved fashion quality. If red were mandatory, B fails before
  scoring and cannot be rescued.
- Generic request/no preferences: deferred totals all0; experimental totals C/5.
  Fully unknown/no-pair contributes1/10, not a measured quality estimate.

Accepting this functional policy does not certify real colour/style coverage,
fashion taste, weights as optimal, or NFR-02. Retain per-structure evidence and
conventional-contribution diagnostics. Existing same-profile engine parity,
complete-stream, persistence/replay and explanation checks are the minimum
activation regression gate. A further human fashion study can support stronger
claims but is not an invented mandatory prerequisite for RN-17.

Sources: `assistant_scoring_selection.py:15`, `compatibility_decision_policy.py:41`,
`rule_based_compatibility_scorer.py:11`, versioned scoring/rule configs;
`frontend/components/CompatibilityExplanation.tsx`.

## D2. RN-13: minimum fulfilment policy and annotation workflow

**Recommend owner-declared suitability through the existing reserved tags,
with a small wardrobe-edit UI, then separately approve enabling its evaluator.**
No style/category/fit/material inference, occasion inheritance or formality
hierarchy. Current default still returns PolicyUnavailable for these fields.

| Extracted field/value | Existing evidence mechanism | Genuine fulfilment after separately approved enablement |
|---|---|---|
| campus,work,casual_outing,shopping,dinner,party,date,travel |Exact rec:v1:occasion:<value>:allow/deny |Only if every candidate member, including outerwear, explicitly allows that requested value. |
| casual,smart_casual formality |Exact rec:v1:formality:<value>:allow/deny |Same all-member requirement; values independent. |
| exercise occasion; formal formality |No approved policy |Remain PolicyUnavailable, not guessed from sporty/formal style. |
| Colour/category/style |Current primary-colour, category/group and base-style policies |Unchanged; missing mandatory evidence never counts positive. Per-garment colour bindings remain unsupported. |

Per garment, Allow ->Pass, Deny ->Fail, absent/invalid/conflicting allow+deny
->Unknown. Outfit aggregation: any Fail wins; otherwise any Unknown is
InsufficientEvidence; only all Pass meets that suitability condition. A deny for
work does not deny dinner; ordinary tags are not declarations. Named colours/
exact anchors remain unchanged and stale palettes never override a corrected
primary. No arbitrary hex equivalence or approximation is introduced.

Minimum UI proposal (requires owner/T frontend approval): add an 'Owner-declared
suitability' section to the existing wardrobe garment editor, not another chat
flow. Each of8 occasions and2 formality values has Unknown/Allow/Deny, default
Unknown. Show current declarations/conflicts and explain their meaning. Encode
existing tags through a small formatter; preserve ordinary tags/unrelated
annotations; never silently sanitise malformed declarations into valid evidence.
Saving one selection replaces only its allow/deny pair. Explicitly show invalid
saved evidence requiring owner correction. Do not prefill from model/style data.
Review-page integration is optional; annotation after normal confirmation is
sufficient for the minimum workflow. No new schema/request field is needed.
Annotations are owner statements, can become stale after garment edits and lack
dedicated review provenance; disclose that and ask owners to revisit relevant
annotations, rather than silently declaring automatic revalidation.

Minimum colour workflow: existing primary-colour editing already accepts names.
Offer approved-name guidance/swatches (or a small chooser with keep-current
option) so owners can explicitly review a CV hex as an approved named colour.
This is a declaration, not automatic hex classification. Preserve current hex
unless edited; do not add colour names or overwrite values/palettes automatically.

**Full RN-13 closure still needs implementation and an agreed scope.** Build/test
the annotation controls, preserve null semantics, and separately enable/test the
existing evaluator. Owner/supervisor must accept the bounded8/2 suitability scope
and named/anchor/owner-reviewed colour evidence, or approve additional evidence
policies for exercise/formal/general hex. NLP recognising9/3 values is not proof
the downstream system fulfils all of them. Controlled unavailable outcomes are
honest failure handling, not complete fulfilment. No full RN-13 closure is
recommended merely because the opt-in evaluator exists.

Sources: `suitability_policy.v1.json`, `suitability_evidence_mapper.py:6`,
`garment_suitability_evidence.py:35`, `occasion_evaluator.py:5`,
`suitability_request_evaluator.py:11`, `workflow_runtime.py:69`.

## D3. FR-VIS-04: trusted confirmation and minimum safe correction

**Recommend proof-based strict current validation for both source types, after
T agrees the trust policy and affected records are inventoried read-only.**
Do not reinterpret NULL as confirmation or indiscriminately rewrite/reject
legitimate records under a guessed legacy policy.

| Record/workflow | Confirmed evidence actually supported | Recommendation requiring T agreement |
|---|---|---|
| Normally processed |confirm_candidates transaction creates garment with processing_item_id and changes accepted item to confirmed; job lookup owner-bound |Use existing Phase1 owner/available/confirmed-item/job-owner proof, no new job-status rule. |
| Manually corrected processing candidate |Same linked item confirmed by the normal save operation |Accept on same proof; manual edits do not invalidate legitimate confirmation. |
| Manually created outfit |create_outfit links existing garments; does not create/confirm new garments |Outfit creation_type='manual' is not confirmation. Validate each constituent. |
| Separate manually confirmed garment |No standalone garment-create/attestation route found in inspected APIs/writer |Do not invent support or trust. T must identify any external supported workflow and its auditable proof before implementation. |
| Legacy with valid confirmed owner links |Existing proof remains valid regardless of age |Accept; no blanket age-based exclusion. |
| NULL/dangling/missing links or job-owner mismatch |No equivalent confirmation proof in current contract |Unverified, not automatically valid. Inventory and agree review/attestation/reprocessing route; keep records/history untouched. No fabricated links or status repair. |
| accepted/pending/rejected item |Review state, not confirmed persisted-garment proof |Not eligible for a new visualisation until a genuine approved confirmation occurs. |

Current source resolution calls strict_items only for recommendations; saved
outfits can admit accepted/NULL links. Execution re-resolves/comparisons only
for recommendations; saved-outfit queued items otherwise receive just current
owner/available checks. Thus create-time correction alone is insufficient.

Smallest future change: in `outfit_identifier_validator.resolve_source`, validate
all saved-outfit member IDs against the transaction-bound confirmed query port,
once per resolution, applying the agreed trust policy without importing a
concrete persistence adapter. Preserve complete ordered membership, supported
VTON roles/categories, media ownership and no silent member dropping. Do not
impose recommendation top/bottom composition rules on unrelated manual outfits.

In `run_visualisation`, extend the existing pre-inference re-resolution and
frozen member tuple comparison to saved-outfit sources as well: garment ID,
media ID, category, role and order. Reject changed membership/confirmation/
availability/ownership/media or invalid source before inference, using existing
controlled errors. Keep the stored configuration for the job; do not silently
replace it with current defaults. Validate within the short claim transaction,
commit/rollback before inference, and retain the current GPU queue/adapter.
Invalid create inserts no request/items; invalid queued source becomes failed
without calling inference. Never hold a transaction across GPU waiting/generation.

Minimum tests: real normal/manual-outfit confirmation remains accepted; linked
legacy proof accepted; agreed unproven NULL cases controlled; accepted/pending/
rejected, missing item/job, foreign job/garment, archived, duplicates/order and
unsupported category rejected. Cover second invalid member, insert rollback,
change between prepare/create and create/execution, membership/media/category
edits, concurrent source writes/claims, cross-user access and no inference on
rejection. Keep recommendation-source regressions and history snapshots unchanged.

Sources: `wardrobe_service.py:75,109,114,255`, `wardrobe_routes.py`,
`outfit_identifier_validator.py:14`, `outfit_visualisation_service.py:39,95`.


## D4. Shared data and VTON decisions

| Decision | Concrete recommendation | Approval/evidence required |
|---|---|---|
| Style null/empty |Future writes: omitted=unchanged; null=missing/unknown; []=deliberately empty annotation set; nonempty supported strings/lists preserved. Empty tags mean no assigned supported tag, not proof of no aesthetic style. Never rewrite historical collections. |T approves `_write_representation` preserving None rather than styles-or-empty. Review/wardrobe forms must preserve unchanged raw values; clearing to unknown and explicitly choosing empty must not be conflated. Wardrobe currently sends csv(blank)=[] even on unrelated edits, so writer-only correction is insufficient. Minimal explicit Unknown/No assigned tags choice plus dirty-value preservation; no new style vocabulary or Phase1 contract. |
| Genuine black versus fallback |Hex value,100% palette coverage, confirmed state and ordinary success status cannot distinguish current empty-pixel #000000 fallback. Proof needs retained exact image/mask plus evidence of nonempty analysed foreground and resulting extraction, or an explicit owner-reviewed black declaration. |T supplies existing logs/inputs if available. Owner colour review establishes declared primary colour, not CV extraction success. If absent, label provenance unavailable; separately propose minimal extraction-status/foreground metadata in existing attributes only with approval. No retroactive inferred labels, new model or change to black matching in this stage. |
| Outerwear VTON |Retain rejection of both outwear categories and no silent stripping of outerwear from an outfit. Recommendations may legitimately include outerwear, independently of VTON support. |Recommend explicit supervisor/T acceptance that VTON covers11 top/bottom/dress classes and supported multi-pass outfits, excluding outerwear. If the committed VTON scope includes it, FR-VIS acceptance remains Partial and T must propose a separately approved solution; do not build another model here. |
| Existing real VTON evidence |Request the bundle below before commissioning a replacement run. Handoff reports real upper-body smoke; local raw authority is missing. |T provides existing raw artifact/provenance or states which part is unavailable; supervisor reviews remaining functional/quality coverage. No inference or dataset acquisition is launched here. |

Teammate evidence request, prepared for the owner to forward (not sent):

> Please provide the exact existing `storage/verification/vton/smoke/results.json`
> and its output-media reference/file/hash; person/garment input references and
> hashes through authorised private access; frozen source type/items/categories/
> roles/order; CatVTON source and weight revisions, asset manifest/checksums;
> preprocessing/model/configuration identifiers, seed/steps/guidance/resolution/
> precision; environment/GPU/CUDA/dependency identifiers; raw latency/VRAM/status/
> error records and command used. Please distinguish the reported single
> upper-body smoke from any completed lower/dress/multi-pass evaluation. Redacted
> identifiers/hashes are acceptable where images cannot be shared; do not send
> other users' photos. Identify absent artifacts rather than reconstructing them
> as if original. Also supply existing O1/CV/VTOFF raw audit references where
> they support shared acceptance, and clarify licensed DressCode work remaining.

Keep the current labelled development fallback distinct from model-backed output.
A smoke run demonstrates bounded operation, not reliable fashion quality or
measurement-accurate fit. No review ratings or missing provenance are fabricated.

## D5. Release configuration and legacy generation

**Recommend explicit integrated release configuration and fail-closed legacy
GENERATION fallback retirement, subject to approval.** Keep history/read/save/
visualisation APIs and historical legacy records. Do not delete the whole
recommendation_service module: it still owns actions/read functionality.

| Server setting | Actual current behaviour | Proposed release after prerequisite approvals |
|---|---|---|
| SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE |compact_exhaustive default |compact_exhaustive explicitly pinned; reference remains rollback. |
| SMART_WARDROBE_ASSISTANT_SCORING_PROFILE |compatibility_deferred default |experimental_compatibility_decision_v1 only after D1 acceptance plus separate activation approval. Until then keep deferred; do not claim RN-17 closed. |
| SMART_WARDROBE_HOMEPAGE_ENABLED |false if unset |true for intended release; preserve random selection. |
| SMART_WARDROBE_ASSISTANT_ENABLED |false if unset |true for intended release; new writes use integrated pipeline. |
| SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED |false if unset |true only after D2 controls, annotation workflow and tests are approved/completed; otherwise stay false with explicit limitation. |
| Approximate hex |disabled by approved code/configuration |remain disabled; no fabricated environment toggle or calibration approval. |

Settings belong to the actual service launcher/environment and require restart;
writing a .env file alone is not proof a plain Uvicorn process loaded it. Freeze
the effective release manifest and fail explicitly for unknown selections.

Minimum route proposal: when integrated Assistant is unavailable, both explicit
and unqualified generation POSTs return the existing IntegrationDisabled-style
controlled response rather than invoking create_recommendation's old heuristic.
When enabled, both use the integrated path and its submission-key validation.
Inventory legacy callers and update them to supported requests/idempotency keys
as a coordinated change; this is an intentional legacy-generation compatibility
decision, not a silent behavioural change. Keep completed legacy reads/saves
supported under existing strict action policies. Do not add ordinary-client
engine/profile selection. An off/misconfigured release must not advertise or
return placeholder generation as verified integrated success.

This requires owner approval for the routing/caller change and deployment flags;
none were changed now. Minimum checks: flag-on/off, unqualified/explicit requests,
missing/invalid keys, authentication, cross-user history, deterministic replay,
no legacy writes while disabled, legacy read/save continuity, four engine/profile
configurations and reference rollback. Sources: `workflow_runtime.py:33`,
`recommendation_routes.py:47`, `assistant_models.py`, `recommendation_service.py:63`.

## D6. PostgreSQL versus SQLite: a real commitment decision

The original design explicitly specifies PostgreSQL/pgvector, not just a filename:
PDF210/213 Data Tier; PDF218 transaction/rollback; PDF220 completed-chat PostgreSQL
transaction; PDF259/262 deployment/data design. **Treat PostgreSQL as the approved
design commitment unless the supervisor explicitly accepts a prototype deviation.**
It is not independently enforced by a technology-named RN-17 criterion, but must
not be silently removed from the report architecture.

| Outcome requiring an explicit decision | Minimum genuine work / claim allowed |
|---|---|
| A: PostgreSQL remains required |Agree one shared DB/provider and actual driver/configuration; reconcile singular deployment schema versus plural SQLite table names, identifiers, JSON/vector representations and SQL parameter/row handling across account, wardrobe, processing and recommendation users. Implement real connection/transaction ports and repository/query adapters against that schema, not a filename rename. Audit actual fresh/populated test migrations and constraints; abort conflicts without rewriting data. Verify authenticated queries, atomic chat/items/idempotency, row locking/revalidation of garment/processing evidence, concurrent duplicate-key submissions, rollback, save/VIS source safety and historical replay. Unique constraints plus a PostgreSQL-specific race/locking strategy are needed; BEGIN IMMEDIATE does not transfer. Enumeration outside writes, VTON outside long transactions. All real deployment checks on disposable DBs first. |
| B: Supervisor accepts SQLite academic prototype |Retain honest SQLite naming/documentation, enabled foreign keys and tested transaction semantics; declare PostgreSQL/pgvector implementation outside demonstrated deployment and amend accepted architecture/report scope. Record deployment concurrency/storage/backup limits. No claim of executed PostgreSQL migrations/locking; do not invent equivalent behaviour. This avoids a cross-module DB rewrite only if the deviation is genuinely approved. |

Recommendation for remaining workload: seek a prompt supervisor decision on B
before starting cross-module DB work. If not accepted, A is required and must be
estimated/coordinated with T; it cannot honestly be promised as a two-file
recommendation-only patch. No DB migration or connection is attempted here.
Sources: `postgresql_repository.py:183`, `recommendation_migrations.py:8`,
`backend/migrations/001_initial_schema.sql`, `003_recommendation_foundations.sql`.


## D7. NFR approval checklist: proposals, not a benchmark authorisation

Original PDF180/printed169 wording, unchanged:

- NFR-01: The system shall display one valid homepage outfit recommendation
  within three seconds after the homepage has completed loading under the
  baseline test environment.
- NFR-02: The system shall return either one outfit recommendation, a no-result
  response, or an unsupported-request response within five seconds after a
  valid NLP request is submitted under the baseline test environment.
- NFR-03: The system shall return chat-history search results within two seconds
  under the maximum chat-history workload defined in the system test plan.

The report delegates workload/environment to a test plan; no approved numeric
baseline was found. These choices require owner/supervisor approval before
fixtures are frozen and formal timing begins.

| NFR-02 decision to approve | Specific recommendation / justification |
|---|---|
|100 or200 garments |Recommend a declared interactive capacity of200 current eligible garments for this local academic release;100 remains a smaller diagnostic workload. This covers the already exercised200 use scenario without inventing a100-item product ceiling. It is a proposed capacity target, not an observed average wardrobe size. Owner/supervisor must confirm it matches intended use.100 is an acceptable alternative only with an independently documented usage/scope reason, not because its old timing was faster. |
|Categories |200:80tops (20 per existing top category),80bottoms (28shorts/26trousers/26skirt),20dresses (6short/6long/4vest/4sling),20outerwear (10 each).134,820 structural combinations before request filtering; existing13 categories only.100 halves these counts with the established40/40/10/10 fixture. This is deliberate category coverage, not a claimed natural population frequency. |
|Attributes |Freeze a reviewed CV/wardrobe snapshot-based mix of current primary names/anchors/non-anchor hex/missing values, single/multiple/unknown/empty styles and ordinary/reserved tags. T must supply/approve the actual histogram before the final distribution is accepted. Do not reuse homogeneous blue/vintage or call arbitrary60%named realistic when CV emits hex. If representative raw records are unavailable, explicitly approve a labelled synthetic stratified substitute with limitations, not invented empirical data. |
|Final profile |After D1 and separate activation approval, test compact plus the accepted three-component profile as the intended release. Until then compact/deferred is actual state. Both profiles' previous results remain; deferred success does not certify experimental performance. Freeze the actual effective profile before formal collection. |
|Requests/preferences |Five successful cases: generic outfit; vintage style; blue+white global colours; include outerwear; vintage+blue global colour. Freeze expected NLP/candidate outcomes and vary0/1/3 supported stored preferences with exact weights/values. Add empty-wardrobe, definite nonmatch and unsupported-intent terminal fixtures. Bound colour associations and scope as currently approved, no NLP changes to make benchmark phrases easier. |
|Deployment |Recommend the existing local Ryzen5 7235HS/8 logical processors/~19.69GiB RAM/Windows11 only if accepted as the academic target. Record exact OS/browser/disk/network/storage, Python3.12/Next16.4.2/package/source/policy hashes; production Next and one Uvicorn process, same-origin proxy, no dev server. DB must be the outcome approved under D6; no assumed PostgreSQL equivalence. Real protected garment thumbnails, valid owner/item/job links and no saved-outfit prerequisite. |
|Concurrency |One active submitted interaction initially, no overlapping CV/VTON/build/tests. This is a bounded single-interaction acceptance claim;2/4 concurrent-user capacity and GPU-contention cases are separately labelled additional tests, not silently claimed supported latency. |
|Repetitions |Recommend10 fresh-key trials per request/preference stratum:5x3x10=150 successful submissions, plus3 terminal cases x10=30, total180 on the one accepted profile. Include first actual recommendation; no hidden ranking warm-up. This replaces the unapproved30-per-cell proposal for a smaller bounded acceptance run, not to discard slow results or claim statistical confidence. If supervisor requires30, total540; choose before execution. Existing100/200 evidence remains retained; do not automatically rerun a96-trial matrix. |
|Acceptance statistic |Every required baseline response has its correct outcome and browser completion <=5.000s. Report all values/count/median/max; no p95 or passing median substitutes for the deadline. This is the recommended operational interpretation requiring approval, not a new report percentile.10/30 trials do not prove a universal latency guarantee. |
|Boundary/images |Monotonic submit to visible correct terminal state including NLP, retrieval, exhaustive ranking, commit, transport/proxy and UI. For recommendations, agree loaded reviewed/approved-fallback thumbnails as part of visible completion; no broken/synthetic missing-media fixtures for formal image-loading claims. No-result/unsupported T1 is the corresponding visible message. Login/pre-submission page setup outside the boundary, stated explicitly. |
|Timeout/error treatment |Existing proxy/client timeouts unchanged. Retain every above5s/error/timeout/unfinished case and eventual backend commit; late commit is not on-time UI success. Correct UnsupportedRequest422 is an expected terminal outcome, not an accidental infrastructure failure. No slow-sample replacement or exclusion. |
|Resources |Three preflight samples <=20%CPU and >=4GiB RAM after startup settle, all samples/blocked attempts retained; stop unrelated test/build work. For formal run validate low-overhead continuous observation and monitor cost; snapshots alone do not prove isolation. Resource disturbance does not erase timed failures; a corrected-condition run has a new label and preserves the first. |
|Scalability/stress |Under the proposed200 baseline,100 is smaller diagnostic; a larger balanced fixture, e.g.300, is scalability only if separately approved. Outerwear-heavy200 (67/67/0/66;300,763 candidates) is explicitly stress by composition, not a substitute baseline. No candidate truncation. Keep all old100/200/stress/blocked populations with their original labels. |

Terminal fixtures: zero eligible wardrobe ->NoEligibleGarments/no-result; full
recognised blue/white wardrobe plus global red request ->NoMatchingCandidates;
outside-scope weather request ->UnsupportedRequest. The definite-nonmatch fixture
must not contain unknown primaries that could correctly yield InsufficientEvidence.
Add separate labelled PolicyUnavailable cases for exercise/formal or disabled
suitability; do not call these successful fulfilment or confuse unavailable
capability with unsupported NLP intent. Owner/supervisor should agree their
terminal-category treatment. No completed chat on unsupported/no-result outcomes.

The representative attribute histogram is a remaining data-approval dependency;
no distribution or benchmark can honestly be final before that is supplied or
an explicit synthetic substitute is accepted. Names/anchors/non-anchor/missing
and style coverage must be reported, not manipulated to make timing pass.

**Known risk:** Phase3G experimental200 browser median6.017s exceeded5s. The later
4.542s median/4.573s maximum was deferred scoring under quieter conditions. It is
not evidence experimental200 now passes. If the approved final run fails, report
failure and propose only a separately approved targeted correction; do not lower
the workload/omit C/extend5s to manufacture acceptance.

| Other NFR decision | Recommended approval choice |
|---|---|
|NFR-01 workload/boundary |Same declared baseline200 and real protected thumbnails. T0 after homepage load; T1 one complete valid outfit with reviewed/approved fallback images loaded. Include cold-first and later cache states with exact boundary, no warm-up recommendation silently removed.10 page flows proposed;3.000s each, no median-only pass. Random selection unchanged. Existing browser max2.809s is readiness evidence under its original synthetic-media conditions. |
|NFR-03 maximum history |Propose declared maximum10,000 personal completed chats plus10,000 other-user records,50-item pages, genuine coherent historical snapshots. This is a proposed capacity workload already exercised at API/query level, not an approved current maximum. Empty/common/no-match/Unicode/literal%/_ and first/later pages;10 searches per approved query case, search action to visible results <=2.000s each. Detail opening is not silently included/excluded from search timing; record separately. Existing1000+3000 browser and10k+10k API evidence do not certify this formal maximum. |

## D8. Minimum implementation sequence and file/owner boundaries

All rows are proposals needing specific approval, not work launched by this packet.
Existing frozen reference archives must remain unchanged; any approved source
changes need a narrowly recorded hash transition, not weakened scoring oracles.

| Order | Work / owner | Minimum files or configuration surface |
|---|---|---|
|1: J-1 |Saved-outfit eligibility and execution parity; T-owned/shared approval |`backend/app/application/visualisation/outfit_identifier_validator.py`, `outfit_visualisation_service.py`; reuse application transaction-query port; new focused `backend/tests/test_saved_outfit_visualisation_eligibility.py` plus existing recommendation/VTON regressions. Trust/data inventory agreement first. No adapter/model/schema/routing/default changes. |
|2 |Forward style semantics; T + shared frontend approval |`backend/app/application/wardrobe/wardrobe_service.py`; `frontend/app/wardrobe/page.tsx`, `frontend/app/extract/results/page.tsx` only as needed to preserve unchanged values and make null/[] deliberate; lifecycle tests. Phase1 snapshot/query unchanged, no historical rewrite. |
|3 |Bounded RN-13 fulfilment; R evaluator wiring, T garment controls |Proposed small `frontend/components/GarmentSuitabilityFields.tsx` used by wardrobe editor; existing custom_tags PATCH and typed API payload. Approved-name colour guidance on existing primary input. Existing parser/evaluator/config remain unchanged; separately approve enabling suitability via composition/deployment after UI/lifecycle/combined-request verification. Review-page controls optional. |
|4 |RN-17 activation and release guard; R + shared deployment approval |Release launcher/environment/manifest; separately approved scoring-default/selector changes only if application fallback is explicitly to change. Keep exact policy values/profile ID/history codec; do not casually flip versioned JSON default_activation flags (validated loaders expect existing configs). `backend/app/api/recommendation_routes.py` for approved fail-closed legacy generation plus caller/flag tests; no removal of action/read code. |
|5 |DB outcome and model evidence; T/shared + supervisor |D6-B: documentation/acceptance limitation only. D6-A: real shared connection/provider, affected persistence/query adapters and DB-specific migrations/tests across modules; separate estimate/approval, not a recommendation-only patch. VTON/CV existing raw evidence transfer first; model implementation unchanged. |
|6 |Formal verification/evidence only |Approved test fixtures/collector/observation artifacts and targeted regression/evaluation scripts; docs/traceability/report update. No new recommendation architecture or speculative optimisation. |

R-only responsibilities are policy documentation/analytical sign-off, preserving
NLP/mandatory semantics, approved score activation, release request guard and
combined outcome/latency evidence. T owns wardrobe annotation persistence/forms,
confirmation provenance, saved-outfit/VTON validation and real-model artifacts.
Shared work is the contract/UI handoff, transaction/provider, feature/caller
migration and integration tests. Supervisor/owner decides declared feature/DB/
load scope and acceptance statistics. Those roles must not be blurred into
permission to edit teammate files now.

## D9. Minimum verification, without another infrastructure stage

- Existing RN-17 exact arithmetic, independent gate and differential tests plus
  the six analytical totals/rank-flip above; reviewed example acceptance of
  midpoint/dress policy, not mandatory fabricated human ratings. Preserve unknown
  provenance and explanations. Check both executor paths within profile.
- J-1 source-resolution/create/claim rollback, stale tuple, confirmation/job-owner,
  legitimate manual-outfit and legacy-proof cases; fake adapter must receive zero
  calls on invalid source. No transaction across VTON inference.
- Forward string/list/null/[] omission/clear semantics across review, confirmation,
  unrelated wardrobe edits, persistence and snapshot. Existing historical values
  unchanged; no mirror-based invention.
- Suitability all8/2 values and every member including outerwear, Allow/Deny/
  Unknown/conflict/malformed cases, ordinary tags, preserved unrelated annotations,
  combined five-field request, category/colour/style regressions, unavailable
  exercise/formal and approximate-hex disabled. Owners can operate actual controls,
  not technical tag syntax. No per-garment colour binding extension.
- Enabled/disabled/unqualified release paths, authentication, submission-key retry,
  concurrent writes, history/save/VIS and reference rollback; no legacy placeholder
  result returned when integration is disabled. Preserve historical replay.
- Existing real model bundle transfer/hashes and missing authorised real smoke
  coverage; actual chosen DB proof rather than SQLite-to-PostgreSQL assumptions.
- Only after approval: frozen NFR01/02/03 cases, exact accepted profile/deployment,
  every response and resource condition retained. No formal timing was run here.

## D10. Owner/teammate/supervisor approval form

Please approve or amend these decisions separately; none is pre-approved:

1. **RN-17:** ACCEPT bounded heuristic and its disclosed0.60/0.20/0.20, midpoint,
   dress1/2 and overlap effects; fashion-quality study optional. Later activation
   still requires explicit permission. Alternative REVISE must identify the
   specific convention; DEFER leaves live RN-17 Partial.
2. **RN-13:** approve the existing8-occasion/2-formality owner-declared workflow,
   minimal garment-edit controls and named-colour review; separately choose when
   to enable. Supervisor accepts remaining exercise/formal/general-hex limitations
   or requires an explicitly scoped additional policy.
3. **Trust/J-1:** T confirms normal/manual/legacy confirmation evidence and reviews
   affected unlinked records before approving strict saved-outfit validation.
   No trust-by-NULL, fake links, mass rejection or historical migration.
4. **Style/provenance/VTON:** T approves forward null/[]/unchanged meanings;
   supplies black extraction/owner-review evidence and existing real VTON bundle;
   supervisor accepts11-class VTON excluding outerwear or requires separate work.
5. **Release:** owner approves integrated flags on, planned fail-closed legacy
   generation/caller transition and actual launcher/restart settings; existing
   reference/deferred rollback remains available.
6. **DB:** supervisor chooses required PostgreSQL implementation (A) or explicitly
   accepted SQLite prototype deviation (B); no filename-based PostgreSQL claim.
7. **NFR:** owner/supervisor approves200 or independently justified100 baseline,
   category counts/real attribute histogram, final profile, request/preferences,
   hardware/DB/process/network/image boundary, concurrency1,10 (or30) repetitions,
   every-trial5s statistic, error/resource treatment and NFR01/03 workloads.

**Recommended first narrow implementation stage once accepted:**
Phase5F-2E-3J-1, *Saved-Outfit Visualisation Eligibility and Snapshot Revalidation*.
Limit it to the two existing visualisation validation/orchestration files and
focused tests/integrity documentation after T's trust decision. No scoring/flag
activation, CV/VTON changes, schema migration, unrelated outfit management or
benchmark in the same change. Style semantics and annotation UI follow as their
own separately approved small changes. This is a concrete next-stage proposal,
not approval to start it now.

## Scope and evidence check

Only this new documentation file is created. All18 retained Phase3H deliverable
hashes were checked before writing. Current policies/confirmation/source execution
were inspected; a separate Fraction calculation checked synthetic analytical
examples, not human ratings. No automated test suite, formal benchmark, app/AI
runtime, DB migration or policy activation was run. Historical reports/evidence
remain unchanged. The known ai-services assertion stays separate; do not delete
that directory. Wait for owner review.
