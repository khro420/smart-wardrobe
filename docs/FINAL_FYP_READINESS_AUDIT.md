# Phase 5F-2E-3J-17: final FYP acceptance, traceability and release-readiness audit

2026-10-23, Asia/Kuala_Lumpur. **Overall recommendation: NOT READY for final whole-FYP acceptance.**
The intended explicitly configured recommendation workflow is **READY WITH
LIMITATIONS for bounded local demonstration**. It is implemented and extensively
verified; it does not need another recommendation algorithm or capacity study.
The full report inventory nevertheless has actual shared functional gaps,
uninspected teammate model evidence, and outstanding formal/deployment decisions.
Those are distinguished throughout this audit. This is not a deployment approval.

J-1 through J-16 are owner-closed PASS WITH LIMITATIONS under session authority.
J-16's105 browser/21 HTTP observations,221 focused regressions and unchanged
deadline maxima are accepted bounded evidence. Its elevated CPU and shutdown
timeout remain unresolved. **No application/default/provider/model/test/evaluation
input or old evidence is edited here.** No tests, server, GPU/model, private
database, migration or performance collector was run. Only new documentation and
read-only file/hash/catalog/log audit artifacts were created.

## 1. Inventory, status rules and recalculated totals

Authority is the original Chong Wei Ping Project I report,
`C:/Users/chong/Downloads/RSW_ChongWeiPing_Project1 (1).pdf`, SHA256
`5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`.
The PDF was read directly. Its tables contain **100 FRs,25 NFRs and30 RNs =155
requirements**, plus **20 CA constraints/assumptions**, kept in a separate register.
Teammate O1/O2/AIR handoff IDs are from a different report and are not added to
this denominator. PDF pages are one-based; printed page=PDF page-11.

`original-requirement-catalog.json` re-extracts every original ID/sentence/page/
priority; only whitespace/zero-width PDF formatting is normalized. All93 old
matrix sentences also match the new original extraction. The appendix below
contains the complete155-row matrix, not a sample; JSON/CSV versions retain the
same wording, source page, responsibility, implementation, executed evidence,
scope/limits and remaining action per row. FR tables do not assign priorities;
RN-01..29 are Must and RN-30 Should. The original NFR priorities are retained.

- **Verified:** implementation plus retained evidence for the explicitly stated
  supported integrated local contract. Not global deployment/model/fashion proof.
- **Partial:** an identified part of the original capability/flow is missing or
  differs from it. An honest unavailable outcome does not implement that feature.
- **Unverified:** code/observations may exist, but the required evidence,
  environment or acceptance maximum has not been established.
- **Blocked:** an external prerequisite prevents the relevant completion work.
  No row is assigned Blocked merely because an approval or artifact is pending;
  the audit itself can finish and its missing evidence is named explicitly.

Statuses refer to the **intended explicitly enabled configuration**, with defaults
and operational/formal acceptance recorded separately. A deliberate default-off
setting is not itself missing source implementation. A profile that has never
been generally enabled is also not described as globally active.

| Family | Total | Verified | Partial | Unverified | Blocked |
|---|---:|---:|---:|---:|---:|
|RN|30|29|1|0|0|
|FR-HR|12|12|0|0|0|
|FR-OA|12|12|0|0|0|
|FR-CH|16|16|0|0|0|
|FR-DW|20|15|1|4|0|
|FR-VIS|16|14|1|1|0|
|FR-ACC|15|6|6|3|0|
|FR-PP|9|4|2|3|0|
|NFR|25|16|1|8|0|
|**All original FR/NFR/RN**|**155**|**124**|**12**|**19**|**0**|


Primary ownership slices, without double counting:

| Responsibility slice | Total | Verified | Partial | Unverified |
|---|---:|---:|---:|---:|
| Your RN/Homepage/Assistant/chat functionality |70|69|1|0|
| T Digital Wardrobe/CV/VIS (including shared handoffs) |36|29|2|5|
| Shared account/profile and R/shared NFRs |49|26|9|14|

Your NFR responsibilities, including missing production diagnostic logging, are
in the shared NFR slice;69/70 does not claim all your quality/release obligations
are finished. Shared save/source boundaries also require T ownership agreement.

**Reconciliation of the old denominator:** the actual
`FINAL_ACCEPTANCE_READINESS_REVIEW.md` matrix recorded **84 Verified,5 Partial,
4 Unverified,0 Blocked out of93**, not85/93. It omitted62 of the full155,
including RN-30, most account/profile/wardrobe rows and22 NFRs. On the **same93**
today the count is **87 Verified,2 Partial,4 Unverified,0 Blocked**. Changes:

| ID | Then | Now | Actual closing evidence |
|---|---|---|---|
|FR-VIS-04|Partial|Verified|J-1 strict saved-outfit eligibility and execution tuple revalidation; later shared regressions retained.|
|RN-17|Partial|Verified, explicit profile|J-5 owner-accepted bounded policy and independent arithmetic; J-12/J-15/J-16 actual configured exact results. Default deployment activation remains separate.|
|RN-28|Partial|Verified, bounded output population|J-15 independent73/73 output audits and J-16 persisted current-member checks. No retroactive certification of pre-correction legacy demonstrations.|

RN-30 is additionally Verified among the62 newly counted rows. RN-13 remains
Partial; FR-VIS-01 remains Partial; FR-VIS-09 and formal NFR-01/02/03 remain
Unverified. The full-inventory count is a traceability result, not a comparable
before/after accuracy percentage or an unconditional FYP pass rate.

Four newly inventoried account/profile rows (FR-ACC-04/09/11 and FR-PP-04)
were conservatively moved from an initial audit draft to Unverified after tracing
their evidence: source code exists, but neighbouring successful flows do not
establish their targeted negative-path checks. The draft is retained separately;
the124/12/19 totals above are final. No old report or test result was changed.

## 2. Recommendation module implementation completion

| Capability | Actual state and retained evidence | Remaining issue type |
|---|---|---|
| NLP intent/five-field extraction | Implemented versioned phrase/field interpreter; fixed120 labels pass original80% criterion; J-15 actual API records complete. | Two additional classic-outfit labels fail; fixed author-labelled English is not general language coverage. |
| Confirmed garment acquisition | Only current user-owned, confirmed/available query snapshots; no legacy NULL-link trust; J-1/J-12/J-15/J-16. | Real attribute quality and account inventory are external evidence/data gates. |
| Candidate generation | Exhaustive four structures, deduplication, stable IDs; no incomplete-stream success or truncation; J-6/J-8 equivalence and J-10 maximum proof. | No new enumeration architecture needed. |
| Mandatory request/suitability gates | Hard Fail/Unknown precede scoring; every member including outerwear evaluated; J-3/J-4/J-12. | RN-13 full original scope Partial; exercise/formal/non-anchor colour limitations below. |
| Three-component scoring | Exact3/5 request+1/5 compatibility decision+1/5 preference, common scale, no per-candidate renormalization; every valid candidate scored. | Independently tested arithmetic; fashion quality not independently validated. |
| Preferences/ranking/selection | Stored supported type/value/weight normalization, exact totals, total/R/C/P/stable-ID ordering, one deterministic winner. | Shared profile UI/write validation incomplete; arbitrary notes are not inferred preferences. |
| Homepage | Separate random valid selection, one result, no user Refresh and no Assistant chat; J-13/J-14/J-16. | Actual deployment flag/approved image scope remains a release decision. |
| Outfit Assistant | One request, one result or controlled terminal message, New Chat, no clarification or completed-chat resubmission. | Broad catch returns controlled errors but lacks required production failure logging. |
| Persistence/idempotency/history | Atomic chat/request/items/metadata/receipt/snapshots; keyed replay/conflict; owner search/cursors; immutable historical explanation. | SQLite-tested; OS-kill/multi-process recovery and deployed TLS not certified. |
| Save/VIS handoff | Independent saved outfit references current validated garments; idempotent save; original history preserved; source IDs re-resolved by VIS. | T owns inference and11-class supported-model acceptance; outerwear rejected wholly. |
| Garment quota | Always100 non-archived owner rows; transaction-bound whole-batch guard; archives release slots; no pending reservation. | Real over-limit/unusual-status inventory/recovery still needed before rollout. |
| Disabled generation | J-14 explicit and unqualified POST fail closed404; no legacy generation writes; unkeyed frontend helper rejects. | External old callers must receive compatibility notice; historical read/action code retained. |
| Activation/restart/rollback | J-13/J-14 real child-process cycles preserve stored results and new-profile semantics. | Explicit local launch only; persistent installed service and J-16 shutdown are unverified. |
| RN-28/RN-30 final evaluation | J-15 complete152-case records and73 generated-output audits; J-16 adds36 checked persisted outputs. | Exact bounded populations; does not independently certify real model attributes or all historical negative tests. |
| NFR performance | J-16 every applicable observed result within3/5/2s. | Formal test/deployment baseline and history maximum not approved. |

There is no evidence-based need for another scoring design, another garment-limit
reduction or a repeated J-9/J-10 study. Actual recommendation-related unfinished
work is sanitized production error logging, the known additional phrase failures
if their labels are to be supported, and any capabilities outside the bounded
RN-13 scope that the supervisor still requires. Shared preference editing is a
real end-user capability gap; correct scorer handling of fixture-supplied
preferences does not supply those controls.

## 3. RN-13/RN-17/RN-27/RN-28/RN-29/RN-30 and NLP limitations

**RN-13 remains Partial against the unrestricted original row.** Implemented
declarations cover campus, work, casual_outing, shopping, dinner, party, date,
travel; casual and smart_casual formality. Each member must explicitly Allow.
Deny fails; absent, malformed or conflicting declarations stay Unknown. Exercise
and formal are PolicyUnavailable. No style-to-occasion inference, occasion
inheritance, formality hierarchy, per-garment colour binding or approximate hex
classification is introduced. Approved names/aliases/exact anchors and explicit
owner colour review are usable; arbitrary non-anchor primaries and ambiguous
evidence remain restricted. Owner declaration is not extraction-quality proof.
The empty-pixel black fallback remains indistinguishable from genuine black
without original nonempty foreground/extraction proof or separate owner review.
Null/empty/omitted style semantics and historical raw evidence remain preserved.

**RN-17 is functionally Verified in the explicit accepted bounded profile.**
The accepted policy uses identical/achromatic colour coordination, Dice style,
real pairwise atoms, missing-atom midpoint, and no-pair dress reference1/2.
Unknown is not a measured0 or confidence; removing a known low atom can improve
rank. A conventional dress/unknown score can beat measured low evidence; provenance
must remain visible. Style may contribute through R,C and P. The selected weights
and conventions are not optimality, statistical independence or fashion-taste
proof. A human study supports stronger claims but is not an invented mandatory
RN-17 arithmetic prerequisite. Unset deployment still uses deferred70/0/30 and
does not fulfil the three-component release behaviour until explicitly configured.

**RN-27/RN-29:** retained original fixed labels have intent120/120, all five-field
values450/450, supplied fields130/130 and exact structured match120/120. The
required threshold remains80% intent/field extraction. Labels contain40 detailed,
30 partial,30 unsupported and20 no-feasible cases, separate from development
examples. This is author-labelled synthetic English, not an independent user
corpus. Source/dataset hashes remain intact; no new NLP evaluation was executed.

**J-15 is not a clean152/152 label pass.** It executed all120 original cases and
32 supplements/controls;150 downstream expectations matched. **S07/S15 “Suggest
a classic outfit” remain UnsupportedRequest despite labels expecting
Supported/style=classic.** Existing “classic look/style” support does not erase
this wording defect. S31/S32 are separate controls, not replacement labels.
**N05 exercise and N06 formal remain PolicyUnavailable**, whereas the original
shared no-feasible scenario says NoEligibleGarments. J-15 separately froze actual
policy-precedence expectations; the original differences remain visible. These
requests are supported NLP intent but unsupported downstream capability. S20
model-validation rejection has no fabricated interpreter result.

**RN-28/RN-30:**71 API plus one Assistant/one Homepage browser recommendation give
J-15's73/73 independent validity audits. All152 API records retain original text,
expected/actual fields or justified null, status, raw result, exact scores,
membership/owner/query proof and explicit no-result outcomes. J-16's36 persisted
recommendations also have current member/metadata/receipt/snapshot checks.
Controlled failures, negative legacy reproductions and old slow measurements
remain historical evidence. The accepted current release population, not every
old pre-fix experiment, is the boundary of the Verified claim.

## 4. Consolidated J-1 through J-16 evidence

All rows cite retained execution, not newly run tests. Counts overlap between
phases and focused/broad suites; **do not add them as distinct tests**. The user
has accepted each phase for closure with its limitations, including phases whose
performance gate failed. A completed diagnostic phase is not a passing latency
result. Current corrections supersede described old code behaviour without
rewriting its raw evidence or report.

| Phase/report | Retained result | Accepted limitation and current use |
|---|---|---|
|J-1: [Strict saved-outfit source and queued snapshot revalidation](SAVED_OUTFIT_VISUALISATION_ELIGIBILITY.md)|97 focused;1,854 broad passes+known architecture failure;35 browser|Former FR-VIS-04 gap closed; no real inference/legacy-link repair.|
|J-2: [Forward null/empty/omitted style semantics and form preservation](FORWARD_STYLE_EVIDENCE.md)|195 focused;1,895 broad passes+known failure;42 browser+10 affected final cases|No historical rewrite; malformed legacy evidence remains explicit.|
|J-3: [8/2 owner controls and optimistic custom-tag concurrency](OWNER_DECLARED_SUITABILITY_CONTROLS.md)|177 focused+1 archival;1,948 broad passes+known failure;54 browser|Evaluator activation separate; annotations can become stale.|
|J-4: [Controlled supported suitability through normal Assistant](CONTROLLED_SUITABILITY_VERIFICATION.md)|269 focused+1 additional;2,036 broad passes+known failure;54 disabled+1 enabled browser|Exercise/formal and general hex not fulfilled; no default change.|
|J-5: [Bounded exact three-component scoring/independent arithmetic](THREE_COMPONENT_SCORING_VERIFICATION.md)|456 focused+1 supplemental;2,064 broad passes+known failure;28+1 browser;36 transport|All6 experimental200 timings above5s remain; no global activation.|
|J-6: [One exact numeric certificate-reuse correction](THREE_COMPONENT_PERFORMANCE_CORRECTION.md)|610 focused;29 differential;2,094 broad passes+known failure;28+1 browser;36 final transport|Experimental200 max4.964s; homogeneous evidence/cache/resource limits and blocked attempts preserved.|
|J-7: [Varied evidence release-gate verification](EVIDENCE_DIVERSITY_RELEASE_GATE.md)|286 focused;56 transport;4 separate terminal functional checks|5 timings above5s and4 browser locator errors retained; no release-default activation.|
|J-8: [One invariant-request-details preparation correction](SUITABILITY_HOT_PATH_DIAGNOSIS.md)|538 focused;2,361 broad passes+known failure;462,252 exact scores;16 before/20 corrected requests|Corrected arm8 above5s; collection pass is not latency pass; all blocked attempts preserved.|
|J-9: [150 capacity feasibility study, subsequently owner-closed](CAPACITY_150_VERIFICATION.md)|569 focused;28 browser;48 measured correct submissions|7/48 above5s;150 not demonstrated. No reopening or replacement of those results.|
|J-10: [100 feasibility including maximum structural combination](CAPACITY_100_VERIFICATION.md)|425 focused;20/20 measured correct submissions;none above5s|17,710/38,148 candidates; owner selected100. Evidence did not itself implement a quota.|
|J-11: [100 non-archived entry quota/API/subset UI](WARDROBE_QUOTA_IMPLEMENTATION.md)|375 shared regressions;35 final focused including25 quota;54 regression+6 final quota browser|Actual SQLite concurrency/batch rollback; over-limit real accounts not inventoried; same-job409 unchanged.|
|J-12: [Intended startup profile, release journey and matched sanity](INTEGRATED_ASSISTANT_RELEASE_VERIFICATION.md)|354+39 backend checks;8 functional browser;8 qualified transport submissions|Prior zero-request blocked attempt retained; no persistent service activation; old legacy risk later closed byJ14.|
|J-13: [Actual child-process activation/restart/rollback](CONTROLLED_ASSISTANT_ACTIVATION_REHEARSAL.md)|296 backend;4 production-browser stages;4 clean backend shutdowns|Disabled legacy bypass intentionally reproduced; not certified; current correction isJ14.|
|J-14: [Disabled generation closed on both URL forms; unkeyed helper rejected](FAIL_CLOSED_RECOMMENDATION_ROUTING.md)|443 backend including26 new cases;4 browser stages;4 clean backend shutdowns|Historical read/save/VIS preserved; external legacy callers need migration notice; no default activation.|
|J-15: [Final original+supplement API execution and independent RN-28/30 audit](FINAL_RECOMMENDATION_VALIDITY_EVALUATION.md)|152 API records;150 expectations matched;73/73 generated audits;629 regressions;1 browser test|S07/S15 remain classic-outfit wording failures; N05/N06 retain original-label versus PolicyUnavailable differences.|
|J-16: [Three original NFRs in one frozen intended local configuration](FINAL_NFR_PERFORMANCE_ACCEPTANCE.md)|105 browser+21 HTTP;all correct/on-time;221 focused regressions|NFR1/2/3 maxima2.2861/3.471/0.3994s; baseline approval/resource/shutdown limits remain.|


`phase-register.json` stores every report path/hash, closure authority and artifact
directory. `REPORT_TRACEABILITY.md` is historical and stops its recent additions
at J-8; it is not silently presented as an up-to-date J-16 acceptance matrix.
This new audit is the consolidated current view; no old traceability file changed.

## 5. Final NFR assessment and all retained J-16 observations

Original Must sentences, PDF180/printed169:

- **NFR-01:** The system shall display one valid homepage outfit recommendation within three seconds after the homepage has completed loading under the baseline test environment.
- **NFR-02:** The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment.
- **NFR-03:** The system shall return chat-history search results within two seconds under the maximum chat-history workload defined in the system test plan.

The frozen local release used compact/experimental/suitability on; integrated
Homepage/Assistant; unchanged quota/fail-closed route; actual app.main/Uvicorn
one worker; SQLite3.49.1; Python3.12.10; FastAPI0.146.0/Uvicorn0.54.0;
production Next16.4.2 build `K69qSH2Qlp-dAB6ZtNOys`; Chromium156.0.8078.4 /
Playwright1.64.1 headless1280x960. Hardware was Ryzen5 7235HS/8 logical CPUs,
19.692GiB RAM, Windows11 build26200 and WD PC SN5000S local C: storage. Normal
same-origin loopback proxy3100->3101 was used. Database/media/hot logs stayed
outside OneDrive; source/build remained in that workspace. Original report,
source/policy/package/build hashes and exact environment remain in J-16.

J-16 plan SHA256:
`88a1beb98a852dcd0e4944c50e774b9ae002e64a5e715ded9364aae0fea44554`;
frozen execution-index SHA256:
`836a9a7b02160e76a95a971f8103abe047fa75a2444e50ce43c0de9411d48249`.
All243 frozen entries still match. The owner's capacity is **100 active stored
garments**, not150/200 or100 lifetime archive rows. Frozen balanced100 has17,710
candidates and maximum-combination10038,148. History is **proposed10,000 personal
plus10,000 foreign completed chats**,50-row pages, not an approved/enforced history
maximum. It has coherent owned snapshots, mixed available/saved statuses and
timestamp ties. No supported history status-filter UI/API exists.

Boundaries remain: NFR-01 native document load to a valid visible complete outfit
including all protected synthetic PNG thumbnails; NFR-02 captured submit to correct
terminal UI including thumbnails on Selected; NFR-03 initial navigation or search/
Load more action to expected visible IDs/count/order. Later-page preparation and
detail opening are outside that search action, explicitly disclosed. Actual login
API/signed bearer and normal sessionStorage are used, not test identities. Public
auth setup is outside timing; no ranking warm-up or first-sample removal. Fresh
context per cell, caches reused for later trials; cold OS/disk caches are not
claimed. Direct HTTP comparisons are separate and do not replace browser timing.

All seconds below; displayed rounding does not decide acceptance. Full precision,
IDs, keys, responses and browser clocks remain in J-16 `runs/initial/trials.json`,
`timing-ledger.csv` and `performance-summary.json`. This table consolidates those
measurements; **none was rerun**.

| NFR | Cell | Browser seconds, all five in order | Median | Maximum | Direct HTTP seconds |
|---|---|---|---:|---:|---:|
|NFR03|empty_first|0.399400, 0.218000, 0.224400, 0.215600, 0.208600|0.218000|0.399400|0.149498|
|NFR03|empty_next|0.169700, 0.189600, 0.161900, 0.188400, 0.280900|0.188400|0.280900|0.113807|
|NFR03|common_first|0.089700, 0.079900, 0.078200, 0.089900, 0.091000|0.089700|0.091000|0.070178|
|NFR03|common_next|0.112100, 0.096600, 0.128500, 0.110800, 0.129600|0.112100|0.129600|0.086199|
|NFR03|no_match|0.086500, 0.074900, 0.097800, 0.089100, 0.094900|0.089100|0.097800|0.072974|
|NFR03|unicode|0.094100, 0.096300, 0.094300, 0.090900, 0.092800|0.094100|0.096300|0.084595|
|NFR03|percent|0.094000, 0.094900, 0.096800, 0.110000, 0.093400|0.094900|0.110000|0.090186|
|NFR03|underscore|0.105800, 0.109400, 0.093000, 0.108500, 0.095000|0.105800|0.109400|0.072096|
|NFR03|many|0.125800, 0.110000, 0.127300, 0.141200, 0.128400|0.127300|0.141200|0.112060|
|NFR03|few|0.093400, 0.090800, 0.091900, 0.090600, 0.092300|0.091900|0.093400|0.067782|
|NFR01|balanced-100|0.456200, 0.408300, 0.405100, 0.350300, 0.424900|0.408300|0.456200|0.336444|
|NFR01|maximum-100|0.851900, 2.286100, 0.716900, 0.814200, 0.752700|0.814200|2.286100|0.633362|
|NFR02|balanced-100-generic|1.056400, 1.056100, 1.158700, 1.376700, 0.991500|1.056400|1.376700|1.199177|
|NFR02|balanced-100-allow|1.805200, 1.627400, 1.626100, 1.649600, 1.744500|1.649600|1.805200|1.729966|
|NFR02|maximum-100-generic|2.590600, 1.708100, 1.932500, 3.132100, 2.446100|2.446100|3.132100|2.616590|
|NFR02|maximum-100-allow|2.537300, 3.076600, 3.471000, 3.346500, 3.324700|3.324700|3.471000|3.308095|
|NFR02|empty|0.057600, 0.058100, 0.057700, 0.059100, 0.057000|0.057700|0.059100|0.039222|
|NFR02|no_match|0.071600, 0.057400, 0.057000, 0.057100, 0.059100|0.057400|0.071600|0.032492|
|NFR02|unsupported|0.038900, 0.026900, 0.028400, 0.027300, 0.028900|0.028400|0.038900|0.007878|
|NFR02|unavailable (diagnostic)|0.040600, 0.040900, 0.042500, 0.041100, 0.040300|0.040900|0.042500|0.014633|
|NFR02|insufficient (diagnostic)|0.058500, 0.057800, 0.059000, 0.072500, 0.059200|0.059000|0.072500|0.031946|


Every observed principal result and separately labelled diagnostic met its
unchanged deadline. The first Homepage maximum-combination cell's **second**
browser value2.2861s remains, with no faster replacement. NFR-01 navigation-to-
visible five-value sequences are0.5249/0.4512/0.4429/0.3896/0.4620 balanced and
0.9499/2.3293/0.7594/0.8664/0.8002 maximum; none completed before load. NFR-02
selected results retain exact J-10 scores/winners, complete candidate counts and
24 new chats. Homepage adds12 recommendations/no chats;30 terminal/diagnostic
requests add no generation rows. All20,000 seeded history rows per table remain
unchanged in four tables; current quotas/wardrobe/preferences are unchanged.
Search results have the expected owner-only stable ordering/literal escaping.

Qualification passed at15.8203/19.2308/19.2308% CPU and>=4GiB freeRAM. The same
attempt qualified before the workload-pause reply was processed; there was no
resource-blocked retry. All65 preflight samples remain. During122 active one-
second samples CPU ranged **47.88–100%**, freeRAM **5.477–6.026GiB**. This is not
continuous idle/background isolation. Counters/ASGI/rAF observation costs and all
warnings remain recorded; no overhead was subtracted. Post-collection backend
shutdown timed out and required owned-process cleanup (section8). Small samples,
headless local browser, synthetic images, one worker and loopback do not certify
real-photo/GPU-contention/concurrent-user/production-wide guarantees.

| NFR | Observed recommendation | Formal status |
|---|---|---|
|01|Observed local PASS;10 browser+2 HTTP; browser max2.2861s, medians0.4083/0.8142s|Unverified formal acceptance; actual baseline/image/network scope not approved.|
|02|Observed local PASS;35 principal browser+7 HTTP, plus10+2 diagnostics; browser max3.471s|OPEN / NOT FORMALLY ACCEPTED. Medians and unavailable-diagnostic speed do not substitute for fulfilment/deadlines.|
|03|Observed local PASS;50 browser+10 HTTP; browser max0.3994s; all query medians in table|Unverified formal maximum acceptance;10k+10k remains a proposed system-test-plan maximum.|

**Exactly what is still needed for formal NFR acceptance:**

1. Owner/supervisor/deployment owner adopts the precise test-plan environment:
   owner's100 capacity, actual chosen DB, single-interaction/one-worker topology,
   five release flags, hardware/storage/network/browser and synthetic-versus-real
   image boundary. This documents the100 decision; it does not reopen it.
2. The system test plan formally designates the10k personal+10k foreign maximum,
   page size/query/page/status scope and meaning of a completed search. A history
   storage quota is not required merely to specify a test maximum.
3. Approvers accept or amend the stated T0/T1, five-per-cell schedule/every-trial
   3/5/2s interpretation, resource qualification/observed runtime limits and image
   representativeness. They decide whether these retained observations suffice.
4. If the accepted deployment differs materially (e.g. required PostgreSQL,
   external network, real images or active GPU contention), define only the
   missing verification delta. Do not relabel SQLite/synthetic results as those
   environments or repeat this completed matrix just to collect more passes.

No known latency defect in this100 workload requires a new optimisation. No
formal acceptance is fabricated here; the original deadlines remain unchanged.

## 6. Exact intended release settings and rollback; NOT EXECUTED

| Surface | Implemented/current code default | Tested intended release |
|---|---|---|
|Homepage flag|false|true|
|Assistant flag|false|true|
|Execution engine|compact_exhaustive|compact_exhaustive|
|Scoring profile|compatibility_deferred|experimental_compatibility_decision_v1|
|Suitability flag|false|true; supported8/2 only|
|Quota|Always100 non-archived owner entries in application writer|Same, independent of flags|
|Disabled generation|J-14 fail-closed both explicit/unqualified POSTs; old unkeyed helper rejects|Same|

The audit process's five release environment variables are unset; this is not an
inspection of an installed service. Source defaults and actual deployed settings
are different claims. The explicit intended configuration is implemented/tested
through normal startup; no code default change is needed to select it.

After deployment-owner approval and quota inventory, set these in the **actual
backend service environment** (example PowerShell process/children only):

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='true'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED='true'
```

Retain the explicitly approved `SMART_WARDROBE_DATA_DIR`,
`SMART_WARDROBE_DATABASE` SQLite file and private non-default
`SMART_WARDROBE_TOKEN_SECRET`; set production environment/development identity
according to the approved launcher. The current token is a signed HMAC bearer
payload/expiry/signature, not a separately certified standards-based JWT/OIDC
implementation. Use actual account login; no fixture accounts, `/_test` server
or development model-copy output belongs in a real release. T owns real AI flags,
model paths and evidence. This audit approves no new AI setting or asset download.

For the tested local ports, from backend the application entry point is:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 3101 --workers 1
```

From frontend, using the **existing verified build and its proxy target3101**:

```powershell
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/fail-closed-routing-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3101'
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100
```

These are local examples, not persistent service configuration or HTTPS proof.
A different proxy/build directory must be reviewed/built with its actual target;
changing a shell value does not prove an old build's rewrites changed. Pin source,
policy, package and build hashes. A plain `.env` file is not automatically loaded
by normal Uvicorn; the owner must specify an actual environment-loading mechanism.
Do not edit versioned policy `default_activation` values.

Stop/drain every affected backend instance using the agreed service mechanism,
wait for process/port release, then start with the approved settings. Verify
capabilities, a fresh keyed normal Assistant result with experimental weights/
evaluator provenance, supported Allow/Deny/Unknown outcomes, Homepage/no chat,
quota99/100, and original stored historical replay. No process adopts environment
changes by hot reload. Installed service persistence/drain/multi-worker behaviour
is not proven by this local command. Same-origin proxy supports the existing
If-Match workflow; separate origins require the still-unresolved CORS/If-Match
review (current allowlist also lacks PUT) and deployed TLS verification.

**Rollback of scoring/suitability while retaining integration**, in that same
actual backend launcher:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='false'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED='true'
```

Restart all affected instances; new requests use70/0/30 and unavailable requested
suitability, while stored experimental results replay without rescoring. Preserve
DB, secret, annotations, quota, histories and J-14 correction. `reference` is an
existing optional execution rollback, not necessary for profile rollback. If an
actual feature shutdown is needed, Assistant=false now fails closed for both
generation URL forms; Homepage has its independent flag. Removing overrides
restores source defaults only after clearing persistent service overrides and
restarting. No data rollback or legacy generation reopening is required.

## 7. Cross-module/database reconciliation: A/B/C/D

A=Verified locally; B=teammate evidence missing/unavailable here;
C=actual capability/architecture incomplete or differing; D=scope/acceptance
decision required. These may coexist; B never means the teammate never tested.

| Dependency | Class / actual state | Minimum owner action |
|---|---|---|
|Wardrobe confirmation/quota/archive|A: J-11 atomic limit, different-job races, whole-batch rollback, subset notice and archive dependencies verified.|T/deployment performs separately authorized read-only actual-account count/status inventory. Preserve all over-limit records; agree support for non-visible statuses. No automatic archive/history repair.|
|Lifetime/pending capacity|A/D:100 non-archived rows; archived rows retained, pending jobs reserve0; unavailable/unverified active rows count.|Keep honest usage; don't equate100 eligible candidates,100 photos or100 lifetime records. No new media/job quota implied.|
|Garment browse/search|C: category/name/favourite/current-available implemented; original colour/style/availability filter coverage incomplete.|T agrees scope or approves narrow filter correction and tests; no recommendation retrieval change.|
|CV integration contract|A: detection/attribute/standardisation ports; owned media and reviewed confirmation; strict immutable query snapshot downstream.|Retain model-independent contract; never manufacture missing styles/colours/links.|
|Real segmentation/attributes|B/D: handoff reports held-out13-category evaluation and smoke, but named raw paths and mirrors absent.|T transfers existing raw inputs/masks/results/weights/config/provenance, including known failures and unavailable fields, before any replacement run.|
|VTOFF/black provenance|A contract/fallback; B real raw bundle unavailable; D owner colour review versus extraction proof.|T supplies retained mask/nonempty foreground/extraction evidence if available. No automatic relabelling of black/palettes/history.|
|VTON/VIS|A source/queue/order/ownership/status/config contract; B real smoke/reconstruction bundle unavailable; C outerwear unsupported; D11-class scope.|T/supervisor accept11 top/bottom/dress classes and supported sequential passes, or separately scope required missing support. No silent stripping or new model here.|
|SQLite versus report design|A actual sqlite3 provider/transactions; C no working app PostgreSQL adapter; D architecture deviation unresolved.|Supervisor accepts documented SQLite academic deviation or requires a genuine shared PostgreSQL implementation/migration/locking verification.|
|Canonical architecture|C: retained ai-services folder contradicts an existing canonical-location assertion; known broad-suite failure remains.|Shared architecture/T owner inventories/reconciles supported layout separately. Do not delete folder or weaken the assertion to turn it green.|
|Deployment/service topology|A local single-worker loopback; B installed launcher/TLS/drain/worker concurrency not inspected; D actual target.|Deployment owner approves topology and recovery scope; narrow shutdown follow-up below before a reliable local-service claim.|

`GARMENT_WORKFLOW_HANDOFF.md` reports its own25/25 O1 and12/12 O2 evidence groups,
held-out segmentation, real VTOFF and PostgreSQL schema smoke work.
`VTON_HANDOFF.md` reports pinned CatVTON academic/noncommercial setup and real-model
acceptance. These are teammate assertions, not this audit's independently verified
raw results. The inspected named `segmentation/results.json`,
`vtoff_standardisation/results.json`, `vtoff/smoke/results.json`,
`vton/smoke/results.json`, `pgvector/results.json` and O1/O2 matrices are absent
both in storage/verification and backend/runs. `dependency-evidence-presence.json`
retains exact checks. No weights/private photos/database were opened or model run.
Transfer lawful existing evidence first; do not infer that those tests never ran.

VTON's supported set is four tops, three bottoms and four dresses, with pinned
sequential multi-pass inputs/order. Both outerwear categories remain rejected.
Contract/development output download checks do not independently validate garment
coverage, image quality or every real-model source journey. Recommendations can
validly contain outerwear while their whole-outfit VIS action is unavailable.

The FYP design explicitly specifies PostgreSQL/pgvector (PDF210/213 data tier,
218/220 transactions and259/262 deployment). The provider filename is not proof:
it calls sqlite3, plural SQLite tables and BEGIN IMMEDIATE. PostgreSQL Compose,
DDL/vector columns or reported standalone schema smoke do not connect the live
application to PostgreSQL. If the design remains required, real shared provider,
row/JSON/vector/schema mapping, data migration and per-owner concurrency strategy
are incomplete. SQLite transaction tests do not transfer to PostgreSQL. If the
supervisor accepts the academic SQLite deviation, document it explicitly instead
of undertaking an unnecessary cross-module database rewrite. No such decision
was invented or implementation started here.

## 8. Shutdown issue: observed once, unresolved, not established reproducible

The retained J-13 verified cycle has four backend exits0 with complete ASGI
shutdown logs. J-14 has four more, on the current production source state, with
startup/activated/restart/rollback/disabled-stage data preserved. All eight log/
ledger confirmations were checked read-only in this audit.

J-16's one collection completed all126 observations and its historical equality
check, then backend14568 logged Shutting down but did not exit within30s. The
supervisor raised TimeoutExpired; owned-process termination was required. Its
WinError10054 callback is also retained. No ASGI task/connection/thread dump or
second failing shutdown was captured. Larger history, browser/backend clients,
resource activity and the transparent measurement wrapper differ from the earlier
rehearsal, but there is **no evidence identifying any as the cause**.

Current conclusion: **one undiagnosed operational shutdown failure, not evidence
of a reproducible application defect and not proof of a harmless one-off**.
The eight clean earlier stops do not resolve the newer failure. Functional
response/history correctness survives; service stop/drain/recovery is unverified.

Before claiming reliable local prototype release operation, separately approve
one narrow lifecycle check: disposable SQLite, actual intended launcher/config,
normal authenticated successful submission plus history read, client/context
closure, then normal graceful stop with the declared bounded wait. Retain child/
application PID, open requests/connections/tasks where observable, shutdown log
and exit code. If it hangs, capture focused state and stop only the owned process;
then scope a correction based on that reproduction. A wrapper-versus-unwrapped
comparison is justified only if needed to isolate a reproduced difference.
No performance matrix, new capacity population, model run or automatic production
patch is required or launched. A later clean stop would be additional evidence,
not erasure of J-16. Forced termination during writes/multi-worker drain remain
separate unless explicitly in the accepted deployment scope.

## 9. Repository, source and evidence integrity

HEAD is `e717f5f785a6325894981a025aeb313167df850e`, dated2026-10-11. The starting
working tree has **29 tracked modified and398 untracked file entries**, excluding
new J-17 files; staged changes are empty. Many core recommendation sources,
fixtures, tests and reports are untracked. Verification describes this working
tree, **not a clean committed checkout or deployable HEAD**. Earlier phase changes
were neither attributed to J-17 nor staged, committed, squashed or discarded.
Before a release artifact/commit, owners must review the exact tracked/untracked
source set and preserve the evidence separately; no approval to commit is inferred.

Read-only checks verified1,198 captured Git-visible/indexed files,2,207 retained
evidence/source paths (overlapping sets, not additive), all76 accepted J-16
deliverables and all243 frozen J-16 execution entries. All match their starting
bytes. The existing hash-transition helper verifies the178-entry original compact
ZIP and approved current source transitions, including J-1/J-2/J-3/J-6/J-8/J-11/
J-14 changes. No original manifest/hash expectation was repinned.

Across27 retained phase indexes there are1,056 indexed references (duplicates
across indexes),1,027 matching current bytes and29 legitimate earlier-state
references to subsequently advanced source/helper/traceability/resumed files.
**No indexed path is missing.** Examples are J-11 frontend API/guard advanced
by J-14, J-6 facts advanced by J-8, and J-12 initial report/commands superseded
by its preserved labelled retry. Current sources pass the explicit transition
chain and all pre-J-17 inventories. Older indexes remain unchanged; an old source
hash is not asserted to equal the later approved source. Initial audit path-base
resolution treated local evidence filenames as repo-relative; the new
`historical-index-reconciliation.json` resolves those correctly without editing
the old indexes or misreporting missing artifacts.

There are36 identical-byte artifact groups (copied before-files, repeated configs/
audit snapshots and empty passing logs). Superseded, interrupted, failed,
resource-blocked and final generated attempts retain their distinct labels.
Nothing was deduplicated/deleted. Existing app entry points, package lock,
Next config, deployment docs/Compose and verified build ID are present. The
installed service/TLS deployment manifest and teammate raw evidence are the
remaining release/evidence gaps, not absent J-11 frontend implementations.

The known `test_single_backend_and_canonical_ml_locations` asserts that
ai-services must not exist; it does exist. Retained broad runs (including J-8's
2,361 passes plus that failure) remain non-green. This phase did not rerun or
weaken the test or delete ai-services. The separate CV geometry/model environment
was not certified by those broad suites. Source/reference integrity passing is
not a claim that all architecture/model tests pass.

Only focused read-only hashing/catalog/source/log checks and whitespace validation
were performed. No regression suite, performance collector, application runtime,
model, migration or actual-account inventory was launched. All new audit additions
are indexed under `storage/verification/phase5f2e3j17/`; exact commands/diagnostic
corrections are retained there. Original J-15 mismatches/J-16 raw timings and
all older captured evidence preserve their hashes.

## 10. Minimum remaining work, classification and owners

| Issue class | Exact unresolved work | Owner/dependency | Minimum completion evidence |
|---|---|---|---|
|Functional defects/differences|Registration confirmation/server format checks/success-to-login flow; server-side active-session invalidation (FR-ACC-02/03/05/06/07/15).|Shared account/auth/UI owner; approve exact source/contract before editing.|Focused invalid/direct-API/duplicate registration and logout-token replay checks plus normal browser flow.|
|Functional gaps|Controlled profile colour/style/category/formality editing and save-time value validation (FR-PP-03/05); cancel/failure preservation currently unverified.|Shared profile/R integration owner.|One minimal existing-semantics UI/API correction; invalid-value, cancel and failed-update preservation checks.|
|Functional gap|Wardrobe colour/style/availability search coverage (FR-DW-13).|T-owned module; explicit approval or scope amendment.|Owner-isolated query/filter/browser cases, no quota/eligibility policy change.|
|Functional gaps/accepted-scope choice|R production failure-context logging (NFR-13); S07/S15 classic-outfit failures; RN-13 outside8/2/named-anchor evidence.|R/shared approval; supervisor decides whether bounded RN-13 scope suffices.|Sanitized fault logs/redaction checks; if wording required, narrow frozen-label-preserving fix; no human ratings or invented evidence.|
|Missing evidence|Real CV/VTOFF/VTON raw bundles and authoritative supported-model scope.|T supplies existing artifacts first; supervisor confirms11-class exclusion.|Input/output/model/config hashes, known failures, authorized supported journeys; only missing coverage needs a new run.|
|Acceptance decision/conditional implementation|SQLite academic deviation versus original PostgreSQL/pgvector design; canonical ai-services layout.|Supervisor+shared provider/architecture/T owner.|Document accepted deviation or separately implement/test genuine provider/migrations/locking; preserve old references.|
|Acceptance decisions|Formal NFR baseline/history maximum/image/resource/statistic adoption.|Owner/supervisor/deployment owner.|Signed-off test-plan decisions in section5; bounded J-16 numbers remain unchanged.|
|Operational missing proof|Reproduce/characterize one observed shutdown failure before reliable local release claim.|Deployment/shared owner; narrowly approved lifecycle verification.|One bounded stop cycle and state/log evidence; correction only if reproduced.|
|Deployment/data readiness|Real quota/status inventory and unusual-record support; source packaging, TLS, real launcher flags/secret/DB retention, viewport/keyboard/zoom/three browsers.|T+deployment+shared frontend; approved real DB target first.|Read-only inventory; curated working-tree release; focused compatibility/accessibility and actual HTTPS/startup/replay proof.|

These are distinct types of unfinished work. Missing approval is not recast as
missing scorer code; missing raw files do not disprove teammate execution; an
implemented fallback does not fulfil an unavailable request field. Real source
gaps are not waived by passing capacity/performance results.

**Estimated necessary rounds, conditional on decisions:** with an accepted
SQLite/bounded8/2/11-class local scope and available existing model artifacts,
plan **one coordinated, explicitly approved functional-closure implementation
round plus one focused evidence/release verification round (about2 rounds)**.
Group account/profile/wardrobe/logging/required phrase corrections by owner rather
than inventing a phase per row. The second round covers changed paths, profile
cancel/failure, accessibility/browser/TLS and the narrow shutdown check; reuse
existing score, capacity and NFR evidence where unchanged. Documentation approvals,
artifact transfer and curated release packaging are tasks, not reasons for
repetitive implementation phases. A reproduced shutdown defect may need one
additional targeted fix/recheck. If PostgreSQL or new full suitability/VTON scope
remains mandatory, estimate **1–2 additional shared implementation/verification
rounds**, subject to design and data review; no honest fixed total can precede
that scope decision. No such round starts automatically.

## 11. Final recommendation

**NOT READY for final whole-FYP acceptance.** The evidence is sufficient to show
the intended configured recommendation workflow works within its disclosed
bounded policies and100-garment capacity. It is not sufficient to claim all155
original requirements, real model integration, formal NFR baselines and operational
deployment are closed. The12 Partial rows include actual capability/flow gaps;
the19 Unverified rows primarily need specific evidence or formal environment/
maximum acceptance. There is no basis to restart recommendation architecture,
lower capacity again or repeat the J-16 matrix just for more passing numbers.

This documentation/evidence audit is complete for owner review. Global defaults,
production sources, historical wardrobe/evaluation data, teammate modules,
database provider, model assets and all prior evidence remain unchanged.
**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. No J-18 begins. Wait for review.**

## Appendix A. Complete155-requirement matrix

R=your NLP/recommendation/chat workstream; T=teammate CV/Digital Wardrobe/VIS;
Shared=account/profile/frontend/deployment/contract owners. Evidence keys such as
J-12 refer to the exact report and raw directory in section4 and phase-register.json.
T-N/T-G/T-R/T-H/T-A/T-CH/T-D/T-V refer to the unchanged test/source evidence key
in FINAL_ACCEPTANCE_READINESS_REVIEW.md; they are retained tests, not new runs.
Each sentence below is the original requirement, not a shortened paraphrase.

### RN

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|RN-01|The NLP component shall classify each submitted request as either a supported outfit-recommendation request or an unsupported request. (PDF186/printed175; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Binary supported/unsupported orchestration|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-02|The NLP component shall extract the occasion from a supported request when occasion information is present. (PDF186/printed175; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Approved nine-occasion extraction, without suitability inference|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-03|The NLP component shall extract the requested style from a supported request when style information is present. (PDF186/printed175; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Approved style aliases extracted independently|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-04|The NLP component shall extract the preferred colour from a supported request when colour information is present. (PDF186/printed175; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Approved fourteen global colours extracted; local garment-colour binding rejected|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-05|The NLP component shall extract the requested garment category from a supported request when garment-category information is present. (PDF186/printed175; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Specific categories and preserved broad groups extracted|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-06|The NLP component shall extract the formality level from a supported request when formality information is present. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: casual/smart_casual/formal extraction, distinct from style|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-07|The NLP component shall convert the extracted request information into structured fields that can be processed by the recommendation component. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Immutable StructuredOutfitRequest built from five fields|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-08|The NLP component shall represent an absent optional request field using its documented null or default value rather than creating an unsupported user requirement. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Absent optional fields remain None|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-09|The NLP component shall return an unsupported-request status when the submitted text cannot be interpreted as an outfit-related request. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: Unsupported intent/meaning returns controlled outcome|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-10|The NLP component shall complete the request-processing workflow without generating a follow-up clarification question. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|NLP/EXTRACT: One interaction, no follow-up clarification|T-N; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-11|The recommendation component shall obtain current user-owned, confirmed and available garment records only through the ConfirmedGarmentQuery interface provided by the Digital Wardrobe subsystem. (PDF187/printed176; Must)|R: NLP/recommendation/chat; **Verified**|QUERY: owner/status/confirmed item and processing-job owner joins through injected contract|T-G; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-12|The recommendation component shall exclude supplied garments that do not contain the attributes required for recommendation processing or that violate mandatory recommendation-specific conditions for the current request. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Verified**|RULE/GEN: missing required evidence is not Pass; unsupported structure excluded|T-G/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-13|The recommendation component shall filter candidate garments according to the structured conditions extracted from the submitted request. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Partial**|Mandatory gates implemented; all-member explicit Allow/Deny/Unknown works for8 occasions/2 formalities.|J3/J4/J12/J15/J16; test_suitability_assistant_e2e.py; suitability controls browser|Exercise/formal PolicyUnavailable; non-anchor hex and missing/conflicting evidence remain Unknown; no per-garment colour binding.|Supervisor accepts bounded8/2/named-anchor scope, or owner separately scopes missing evidence policies; deployment enablement separate.|
|RN-14|The recommendation component shall generate outfit candidates using only eligible garments retrieved for the submitted request. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Verified**|GEN: exhaustive combinations from query snapshots, no saved outfits required|T-G/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-15|The recommendation component shall exclude an outfit candidate before scoring when it violates a mandatory request condition. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Verified**|RULE/GEN: Fail or Unknown never passes independent scoring gate|T-G/T-R; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-16|The recommendation component shall exclude an outfit candidate before scoring when it violates a configured garment-category or outfit-structure rule. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Verified**|GEN: approved thirteen-category/four-structure policy before scoring|T-G; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-17|The recommendation component shall calculate a score for each valid outfit candidate using the documented request-match, compatibility, and user-preference criteria. (PDF188/printed177; Must)|R: NLP/recommendation/chat; **Verified**|Exact60/20/20 calculation for every mandatory-valid candidate in explicit experimental release profile.|J5 independent Fraction oracle; J6/J8 equivalence; J12/J15/J16 exact persisted scores|Bounded heuristic only: midpoint/no-pair1/2 and overlapping style signals; no fashion-quality/optimal-weight proof; unset default remains deferred.|Retain accepted heuristic; deployment owner explicitly configures profile. No mandatory invented human-rating study.|
|RN-18|The recommendation component shall rank valid outfit candidates according to their calculated recommendation scores. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: Exact streaming ranking by total score|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-19|The recommendation component shall select the highest-ranked valid outfit for a successfully processed NLP request. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: Highest valid candidate published only after completion|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-20|The recommendation component shall apply the documented tie-breaking rule when two or more valid candidates receive the same highest score. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: Total, R, C, P, stable identifier tie sequence|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-21|The recommendation component shall return exactly one outfit recommendation for each successfully processed NLP request. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: Exactly one successful result|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-22|The recommendation component shall return a no-result status when no outfit candidate satisfies all mandatory request and outfit-structure conditions. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: No invalid fallback; explicit no-result, evidence and capability outcomes|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-23|The recommendation component shall not generate garment identifiers, attributes, or availability information that are absent from the retrieved wardrobe records. (PDF189/printed178; Must)|R: NLP/recommendation/chat; **Verified**|GEN/ASSIST: Only snapshot garment IDs/attributes, no fabrication|T-G/T-R/T-A; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-24|The homepage recommendation component shall select outfits only from candidates that satisfy the configured outfit-structure and compatibility rules. (PDF190/printed179; Must)|R: NLP/recommendation/chat; **Verified**|HOME: approved mandatory structure/compatibility policy, no aesthetic score threshold|T-H/T-G; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-25|The homepage recommendation component shall randomly select exactly one outfit from the valid candidate collection. (PDF190/printed179; Must)|R: NLP/recommendation/chat; **Verified**|HOME: exhaustive reservoir selection of exactly one valid candidate|T-H; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-26|The homepage recommendation component shall operate independently of NLP request processing and shall not create a chat-history record. (PDF190/printed179; Must)|R: NLP/recommendation/chat; **Verified**|HOME/PERSIST: NLP-independent generation; homepage chat_id NULL|T-H/T-CH; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|RN-27|The NLP component shall achieve at least 80% correct intent classification and request-field extraction across the fixed labelled evaluation dataset. (PDF190/printed179; Must)|R: NLP/recommendation/chat; **Verified**|NLP: fixed author-labelled 120-case evaluation exceeds original 80% criterion|T-N/T-E; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Preserve fixed labels/hash and original criterion; broader human evaluation is a separate quality task.|
|RN-28|Every outfit recommendation produced during system evaluation shall use only current user-owned, confirmed and available garment records supplied through ConfirmedGarmentQuery and shall satisfy all applicable recommendation-specific eligibility conditions, mandatory request constraints, outfit-structure rules and compatibility rules. (PDF190/printed179; Must)|R: NLP/recommendation/chat; **Verified**|Strict current query/mandatory/structure checks; independent complete output audit for frozen post-J14 release population.|J15:73/73 independent audits; J16:36 persisted recommendations/owned-confirmed current members|Controlled synthetic acceptance populations, not real CV/general fashion validation or retroactive certification of old legacy negative demonstrations.|Retain raw audited outputs and disclosures; no new generation algorithm needed.|
|RN-29|The NLP evaluation dataset shall include supported requests, partially specified requests, unsupported requests, and requests for which no valid outfit can be generated. (PDF191/printed180; Must)|R: NLP/recommendation/chat; **Verified**|NLP dataset: 40 detailed, 30 partial, 30 unsupported and 20 no-feasible scenarios|T-E; J4/J5/J12/J15|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Keep dataset content verified; execute downstream scenarios for combined acceptance/RN-28 and RN-30 evidence.|
|RN-30|The evaluation record should contain the original request, expected structured fields, actual structured fields, processing status, and generated recommendation result for each evaluated request. (PDF191/printed180; Should)|R: NLP/recommendation/chat; **Verified**|Original text/expected and actual fields/status/result or explicit no-result recorded for every evaluated API case.|J15 case-ledger.csv,152 original+supplement/control records,629 retained regressions|S07/S15 failures retained; N05/N06 original no-feasible versus PolicyUnavailable differences retained; S20 model rejection has null actual fields.|Retain records unchanged; wording correction is separately scoped if required, not a missing-record defect.|

### FR-HR

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-HR-01|The system shall initiate homepage recommendation generation when an authenticated Registered User accesses the homepage. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME UI: effect starts authenticated homepage flow|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-02|The system shall retrieve only confirmed and available garments belonging to the authenticated Registered User. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|QUERY: strict current eligibility|T-H/T-G; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-03|The system shall determine whether sufficient eligible garment categories are available to form a complete outfit. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME/GEN: sufficient supported category slots|T-H/T-G; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-04|The system shall generate possible outfit combinations using the eligible wardrobe garments. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME/GEN: lazy wardrobe combinations|T-H/T-G; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-05|The system shall exclude outfit combinations that violate the required garment-category structure or mandatory compatibility rules. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME/GEN: approved mandatory structure and compatibility rules|T-H/T-G; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-06|The system shall remove duplicate outfit combinations before selecting a homepage recommendation. (PDF169/printed158; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|GEN: deterministic IDs/deduplication|T-H/T-G; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-07|The system shall randomly select one outfit from the valid homepage recommendation candidates. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME: reservoir random top-one, not weighted Assistant ranking|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-08|The system shall display the selected outfit recommendation on the homepage. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME UI: ordered complete recommendation cards|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-09|The system shall not provide a user-controlled function for refreshing or requesting another homepage recommendation during the current homepage recommendation flow. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME UI: no refresh control; same-flow retry retains key|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-10|The system shall display an appropriate message when insufficient garments or no valid outfit combinations are available. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME UI/service: explicit empty/insufficient/no-valid outcome|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-11|The system shall display an error message when the homepage recommendation process cannot be completed. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HOME UI/service: failure message, no saved substitute|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-HR-12|The system shall not create a chat-history record for an outfit recommendation generated automatically on the homepage. (PDF170/printed159; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|PERSIST: homepage insert has no NLP chat|T-H; J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|

### FR-OA

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-OA-01|The system shall allow an authenticated Registered User to access the Outfit Assistant. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST/API: authenticated operations and private data|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-02|The system shall display the Outfit Assistant request interface and provide a New Chat option for starting a new single-request recommendation interaction. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI: request interface and New Chat|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-03|The system shall allow the Registered User to create a new chat. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI: independent draft/key; completed row only on success|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-04|The system shall allow the Registered User to submit one natural-language outfit request within a new chat. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI/service: one locked request plus durable submission key|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-05|The system shall reject a request that is empty or contains only whitespace characters. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|NLP/UI: empty/whitespace rejected|T-A/T-N; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-06|The system shall process the submitted request using the NLP and recommendation components. (PDF171/printed160; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST: actual NLP, eligible retrieval, mandatory evaluation and ranking orchestration|T-A/T-N; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-07|The system shall display exactly one outfit recommendation when the submitted request is processed successfully. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI: one result on successful completion|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-08|The system shall display the original request together with its corresponding recommendation. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST/PERSIST/UI: original text retained with result|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-09|The system shall display an unsupported-request message when the request cannot be interpreted. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|NLP/ASSIST UI: controlled unsupported message|T-A/T-N; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-10|The system shall display a no-result message when no suitable outfit can be generated. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI: controlled no-result, evidence and capability messages|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-11|The system shall display an error message when request interpretation, garment retrieval or recommendation generation fails. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST UI/service: interpretation/retrieval/generation/storage error handling|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-OA-12|The system shall prevent another request from being submitted within a completed chat. (PDF172/printed161; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST/CH UI: completed chat read-only, New Chat for another request|T-A; J12/J14/J15/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|

### FR-CH

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-CH-01|The system shall create a completed chat-history record only after one outfit recommendation has been generated successfully. (PDF173/printed162; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|PERSIST: completed chat only on successful atomic recommendation write|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-02|The system shall associate each completed chat-history record with the original submitted request, the generated Recommendation, the authenticated user identifier and the creation time, while the garments belonging to the recommendation shall be represented through its associated RecommendationItem records. (PDF173/printed162; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|PERSIST: user/request/time/recommendation and item associations|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-03|The system shall store the request and corresponding recommendation as one complete operation. (PDF173/printed162; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|PERSIST: one SQLite write transaction for chat/recommendation/items/metadata|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-04|The system shall prevent a record containing only the request or only the recommendation from being presented as a completed chat. (PDF173/printed162; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY: coherence predicate hides partial/corrupt records|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-05|The system shall mark a successfully saved chat-history record as completed and read-only. (PDF173/printed162; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: completed/read-only record and GET-only detail|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-06|The system shall prevent the Registered User from submitting another request within a completed chat. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: no append; key/text conflicts rejected|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-07|The system shall prevent duplicate chat-history records when the same request submission is unintentionally processed more than once. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|PERSIST: unique user/operation/key plus fingerprint under write lock|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-08|The system shall allow a Registered User to search their own completed chat-history records using the supported search field. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: own request-text literal casefold search|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-09|The system shall return only chat-history records belonging to the authenticated Registered User. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY: owner-bound query and joins|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-10|The system shall display all completed personal chat records when the search field is empty. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: empty search browses all pages; total/cursor explicit|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-11|The system shall display a no-results message when no chat-history record matches the submitted search term. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: no-match empty state|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-12|The system shall allow a Registered User to select and view one of their previous completed chat records. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: owner-selected historical detail|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-13|The system shall display the saved request and corresponding recommendation when a completed chat record is opened. (PDF174/printed163; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/PERSIST/UI: saved original request and historical item snapshots|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-14|The system shall prevent a Registered User from accessing a chat-history record belonging to another user. (PDF175/printed164; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/API: missing/foreign generic 404|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-15|The system shall indicate when a garment referenced by a historical recommendation is no longer available in the current digital wardrobe. (PDF175/printed164; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|HISTORY/UI: historical snapshot retained, current strict eligibility flag shown|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-CH-16|The system shall inform the Registered User when a successfully generated request and recommendation cannot be saved to chat history. (PDF175/printed164; Not specified in FR table)|R: NLP/recommendation/chat; **Verified**|ASSIST/PERSIST/UI: PersistenceFailure with rollback; replay recovers lost response|T-CH/T-A; J11/J12/J14/J16|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|

### FR-DW

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-DW-01|The system shall allow a Registered User to upload supported JPEG or PNG images for garment processing. (PDF165/printed154; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Authenticated JPEG/PNG decoded type/size/resolution/media ownership checks; full-quota advisory upload rejection.|J11 upload-before-media tests; J12-J14 normal upload; protected_media_store.py|One image can yield several candidates; upload reserves no garment slots; real detector quality separate.|Retain upload validation and authoritative confirmation guard.|
|FR-DW-02|The system shall validate the uploaded image according to its file type, size, resolution and ownership. (PDF165/printed154; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Authenticated JPEG/PNG decoded type/size/resolution/media ownership checks; full-quota advisory upload rejection.|J11 upload-before-media tests; J12-J14 normal upload; protected_media_store.py|One image can yield several candidates; upload reserves no garment slots; real detector quality separate.|Retain upload validation and authoritative confirmation guard.|
|FR-DW-03|The system shall detect and segment garment instances contained in an uploaded image. (PDF165/printed154; Not specified in FR table)|T: Digital Wardrobe/CV; **Unverified**|YOLO adapter/pipeline carries per-instance category/confidence/source-space mask/box/crop through real processing ports.|garment_segmentation_adapter.py; GARMENT_WORKFLOW_HANDOFF.md reports held-out/smoke; retained development workflow tests|Named local real segmentation raw evidence/mirrors absent; development fixture does not independently validate segmentation.|T transfers existing raw input/model/config/output evidence first; verify only missing authorized coverage, not retrain automatically.|
|FR-DW-04|The system shall produce the detected garment category, segmentation mask, bounding box and confidence value for each detected garment instance. (PDF165/printed154; Not specified in FR table)|T: Digital Wardrobe/CV; **Unverified**|YOLO adapter/pipeline carries per-instance category/confidence/source-space mask/box/crop through real processing ports.|garment_segmentation_adapter.py; GARMENT_WORKFLOW_HANDOFF.md reports held-out/smoke; retained development workflow tests|Named local real segmentation raw evidence/mirrors absent; development fixture does not independently validate segmentation.|T transfers existing raw input/model/config/output evidence first; verify only missing authorized coverage, not retrain automatically.|
|FR-DW-05|The system shall allow the Registered User to select the intended garment when multiple garment instances are detected. (PDF165/printed154; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Review accepts/rejects individual detections; J11 explicit accepted-candidate save subset and completion notice.|J1/J2 review lifecycle; J11 subset browser/API; J12/J14 normal confirm|Subset confirmation completes job; unselected candidates cannot be resumed later.|Retain explicit selection notice; no new detection-selection workflow required for this contract.|
|FR-DW-06|The system shall generate a standardised garment image from the selected garment or return an approved fallback when standardisation cannot be completed. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Unverified**|Standardisation/fallback, palette/attribute and pinned768D embedding adapters exist behind workflow ports.|vtoff_adapter.py,attribute_embedding_adapter.py,cv/pipeline.py; T handoffs; development/contract regressions|Real standardisation/attribute/raw model bundle unavailable locally; ambiguous fallback black and missing base-style provenance remain.|T supplies exact existing real outputs/weights/config/input hashes and supported-field evidence; owner-reviewed colour is not CV success proof.|
|FR-DW-07|The system shall extract supported garment information, including category, colour, pattern, style-related descriptors and visual embedding. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Unverified**|Standardisation/fallback, palette/attribute and pinned768D embedding adapters exist behind workflow ports.|vtoff_adapter.py,attribute_embedding_adapter.py,cv/pipeline.py; T handoffs; development/contract regressions|Real standardisation/attribute/raw model bundle unavailable locally; ambiguous fallback black and missing base-style provenance remain.|T supplies exact existing real outputs/weights/config/input hashes and supported-field evidence; owner-reviewed colour is not CV success proof.|
|FR-DW-08|The system shall display the garment-processing outputs and extracted attributes for user review before permanent storage. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-09|The system shall allow the Registered User to correct editable garment attributes. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-10|The system shall allow the Registered User to reject an unsuitable garment-processing output. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-11|The system shall save a garment as a confirmed wardrobe record only after the Registered User accepts the processing output. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-12|The system shall allow a Registered User to view garments stored in their own digital wardrobe. (PDF166/printed155; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-13|The system shall allow a Registered User to search and filter wardrobe garments using supported information such as category, colour, style and availability. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Partial**|Garment listing searches name/category and filters category/favourite; available-only rows.|wardrobe_routes.py garments; wardrobe_service.list_garments; wardrobe/page.tsx|No colour/style/availability selector or search of those fields as named in original requirement.|T agrees supported search scope or implements narrow owner-scoped filters; no quota count inferred from filtered length.|
|FR-DW-14|The system shall allow a Registered User to update the editable information of a garment that they own. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-15|The system shall allow a Registered User to delete or archive a garment that they own, subject to related outfit and visualisation references. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|Owner review/correction/rejection before atomic confirmation, listing/editing and dependency-aware soft archive; quota recount within BEGIN IMMEDIATE.|J1/J2/J3 style/tag lifecycle; J11 quota/workflow; J12/J14 browser; test_o1_wardrobe.py|Archive releases slot only after commit; no hard delete/restore, no forced dependency removal; non-visible unusual statuses need support.|Retain contract; deployment owner/T inventories existing counts/statuses read-only before rollout.|
|FR-DW-16|The system shall allow a Registered User to save a valid outfit recommendation displayed through Homepage Recommendations, the Outfit Assistant or Recommendation Chat History as a permanent outfit in their Digital Wardrobe. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|SAVE/UI: separate permanent outfit from homepage/Assistant/history|T-D; J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-DW-17|The system shall create one Outfit record and the required OutfitItem relationships when a recommendation is saved. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|SAVE: atomic Outfit plus ordered OutfitItem rows|T-D; J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-DW-18|The system shall reference the existing garment records when saving a recommendation and shall not create duplicate garment records. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|SAVE: reference existing garments, no garment inserts|T-D; J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-DW-19|The system shall verify that all referenced garments belong to the authenticated Registered User before saving the recommendation. (PDF167/printed156; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|ACTIONS: all members current owner-scoped strict query|T-D; J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-DW-20|The system shall display the successfully saved recommendation in the Registered User’s Outfits collection. (PDF168/printed157; Not specified in FR table)|T: Digital Wardrobe/CV; **Verified**|SAVE/UI: separate saved-state lookup and Outfits collection|T-D; J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|

### FR-VIS

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-VIS-01|The system shall allow a Registered User to request outfit visualisation from a selected saved outfit, Homepage recommendation, Outfit Assistant recommendation or recommendation displayed through Recommendation Chat History. (PDF176/printed165; Not specified in FR table)|T: VTON/VIS; R handoff; **Partial**|VIS/UI: source links from saved outfit/homepage/Assistant/history|T-V/T-D; J1/J11/J14|Outerwear recommendations deliberately cannot be visualised; final model-backed source coverage not independently accepted.|Agree supported VTON scope with T/supervisor; verify real top/bottom/dress source journeys.|
|FR-VIS-02|The system shall receive the selected source type and corresponding Outfit or Recommendation reference required to initiate the visualisation workflow. (PDF176/printed165; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS/API: exactly one source type and identifier|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-03|The system shall verify that the selected Outfit or Recommendation reference is accessible to the authenticated Registered User before resolving the source for visualisation. (PDF176/printed165; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: owner-bound source lookup before resolution|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-04|The system shall resolve the selected Outfit or Recommendation reference to its current garment records and shall reject visualisation processing when any required garment reference is missing, duplicated, unowned, deleted, unavailable, unconfirmed or otherwise invalid for the supported visualisation workflow. (PDF176/printed165; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|Both saved-outfit and recommendation references use current strict transaction-bound proof; queued frozen tuple revalidated before inference.|J1:97 focused/35 browser; J11/J14 strict save/source regressions|Supported11 VTON categories only; valid legacy proof accepted, NULL/dangling/foreign links not trusted; no real-model-quality assertion.|Former saved-outfit validation gap closed. Retain source/claim tests and historical snapshots.|
|FR-VIS-05|The system shall obtain the reviewed garment image or approved fallback image associated with each resolved and validated current garment record required for visualisation. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: current preferred reviewed media resolved and owner-authorised|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-06|The system shall allow the Registered User to select or upload an authorised personal photograph when a personal base image is required. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS UI/personal_image_service: private photo upload/selection|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-07|The system shall validate the selected personal image before beginning visualisation processing. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: decoded media/type/availability/owner validation and preprocessing contract|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-08|The system shall create the internal visualisation request using the authenticated user, resolved and validated current garments, supported garment roles, processing order and selected personal image where applicable. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: immutable ordered garment/person/configuration plan and persisted items|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-09|The system shall process the visualisation request using the backend AI inference environment rather than the web browser. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Unverified**|VIS: backend CatVTON adapter and GPU slot exist; development mode is labelled|T-V + teammate handoff; J1/J11/J14|Handoff reports a real upper-body smoke run, but its raw results.json is absent here; no current model-backed cross-structure acceptance bundle.|Obtain exact raw smoke/model/config hashes from T; verify real supported multi-pass structures on authorised images.|
|FR-VIS-10|The system shall maintain a controlled status for each visualisation request, such as queued, processing, completed, failed or cancelled. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: queued/processing/completed/failed/cancelled lifecycle|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-11|The system shall display the generated outfit visualisation only after processing has completed successfully. (PDF177/printed166; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS UI/result service: only completed outputs expose media|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-12|The system shall allow the Registered User to export or download a successfully completed visualisation through an authorised application-controlled action. (PDF178/printed167; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS UI/protected media: authorised download action|T-V + source inspection; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain contract proof; include output download in T acceptance walkthrough.|
|FR-VIS-13|The system shall store each successfully completed visualisation together with the exact garment references, personal-image reference, generated output-media reference and relevant processing configuration required to preserve generation traceability. (PDF178/printed167; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS: garment/person/output/configuration snapshots retained|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-14|The system shall allow the Registered User to retry or safely cancel a failed or long-running visualisation request. (PDF178/printed167; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS UI/service: owner-scoped cancellation and retry/new request|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-15|The system shall display an appropriate error message when the selected garments, personal image or visualisation process cannot be completed. (PDF178/printed167; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS UI/service: invalid source/person/inference controlled errors|T-V/T-D; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|
|FR-VIS-16|The system shall present visualisation results as an outfit preview without claiming measurement-accurate fit. (PDF178/printed167; Not specified in FR table)|T: VTON/VIS; R handoff; **Verified**|VIS result notice/UI: preview, explicit non-measurement-accurate fit disclaimer|T-V; J1/J11/J14|Verified for supported enabled local contracts; separate deployment/model/formal gates still apply.|Retain evidence; no implementation change required.|

### FR-ACC

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-ACC-01|The system shall allow a Guest to access the account-registration form. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Public /auth registration mode exists; guest can access its form.|auth/page.tsx; existing browser auth-route rendering and J13/J14 account journeys|Registration content/flow gaps are separate rows below.|Retain public form; coordinate the separate registration corrections.|
|FR-ACC-02|The system shall allow a Guest to enter the required registration information, including full name, email address, password and password confirmation. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Form and RegisterRequest accept display_name,email,password; no password-confirmation field or match check.|Static auth/page.tsx and account_routes.py inspection; J13/J14 only exercise existing3-field registration|Full-name/display-name interpretation must be agreed; confirmation required by original wording is absent.|Shared account/UI owner approves and implements confirmation contract plus mismatch/empty/direct-API checks.|
|FR-ACC-03|The system shall validate that all required registration fields have been completed using the accepted format. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Pydantic length bounds and browser required/email checks exist; register inserts/hash only after those checks.|account_routes.py RegisterRequest; account_service.register; retained test_workflow.py registration|No server email-format or password-confirmation validation; direct API can bypass browser-only email checks.|Shared account owner closes original registration validation before full account acceptance.|
|FR-ACC-04|The system shall verify that the entered email address is not already associated with another account. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|Duplicate-email lookup/lowercasing and unique schema exist; duplicate returns409 in source.|Static account_service.register/schema; retained workflow proves registration success, not an executed duplicate-email case|No retained targeted duplicate-account rejection response located; no new test is authorized in this documentation audit.|Shared account owner includes duplicate-email/atomicity check in the single approved account verification round.|
|FR-ACC-05|The system shall verify that the password and password confirmation match before creating the account. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Form and RegisterRequest accept display_name,email,password; no password-confirmation field or match check.|Static auth/page.tsx and account_routes.py inspection; J13/J14 only exercise existing3-field registration|Full-name/display-name interpretation must be agreed; confirmation required by original wording is absent.|Shared account/UI owner approves and implements confirmation contract plus mismatch/empty/direct-API checks.|
|FR-ACC-06|The system shall create a registered-user account only after all submitted registration information has passed validation. (PDF160/printed149; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Pydantic length bounds and browser required/email checks exist; register inserts/hash only after those checks.|account_routes.py RegisterRequest; account_service.register; retained test_workflow.py registration|No server email-format or password-confirmation validation; direct API can bypass browser-only email checks.|Shared account owner closes original registration validation before full account acceptance.|
|FR-ACC-07|The system shall display a registration-success message and direct the user to the login page after the account has been created. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Register returns an access token; auth UI immediately saves it and navigates to Homepage.|account_service.register and auth/page.tsx submit branch; retained normal registration journeys|Original success-message then login-page flow differs from implemented automatic sign-in.|Account/UI owner implements original flow or obtains explicit scope amendment; do not silently relabel compliance.|
|FR-ACC-08|The system shall allow a Guest with an existing account to log in using a registered email address and password. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Required login fields, hash verification/general401, signed session token and protected owner routes; successful UI login routes to Homepage.|test_workflow.py; recommendation.spec.ts real login; J13/J14/J16 normal account API/browser|Local signed HMAC bearer implementation; HTTPS/deployment and logout revocation assessed separately.|Retain actual authentication/protection; do not replace it with test identities in deployment.|
|FR-ACC-09|The system shall validate that the required login information has been entered before processing the login attempt. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|LoginRequest required/length bounds and browser required fields are implemented.|Static account_routes.py LoginRequest/auth form; retained normal login success only|No retained targeted empty/missing-login-fields execution located; malformed recommendation body tests are not login tests.|Shared account owner verifies empty/missing login inputs with the original validation contract.|
|FR-ACC-10|The system shall verify the submitted email address and password against a registered account. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Required login fields, hash verification/general401, signed session token and protected owner routes; successful UI login routes to Homepage.|test_workflow.py; recommendation.spec.ts real login; J13/J14/J16 normal account API/browser|Local signed HMAC bearer implementation; HTTPS/deployment and logout revocation assessed separately.|Retain actual authentication/protection; do not replace it with test identities in deployment.|
|FR-ACC-11|The system shall display a general invalid-credentials message when the submitted login information cannot be verified. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|Invalid account/password source branch returns general401 Invalid email or password.|Static account_service.login; retained invalid-bearer routing tests do not test incorrect login credentials|No retained wrong-password/unknown-email general-message execution located.|Shared account owner verifies both failures without account-disclosure differences in the approved account check.|
|FR-ACC-12|The system shall create an authenticated session after a successful login and direct the Registered User to the homepage. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Required login fields, hash verification/general401, signed session token and protected owner routes; successful UI login routes to Homepage.|test_workflow.py; recommendation.spec.ts real login; J13/J14/J16 normal account API/browser|Local signed HMAC bearer implementation; HTTPS/deployment and logout revocation assessed separately.|Retain actual authentication/protection; do not replace it with test identities in deployment.|
|FR-ACC-13|The system shall prevent unauthenticated users from accessing registered-user functions and user-owned information. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Required login fields, hash verification/general401, signed session token and protected owner routes; successful UI login routes to Homepage.|test_workflow.py; recommendation.spec.ts real login; J13/J14/J16 normal account API/browser|Local signed HMAC bearer implementation; HTTPS/deployment and logout revocation assessed separately.|Retain actual authentication/protection; do not replace it with test identities in deployment.|
|FR-ACC-14|The system shall allow an authenticated Registered User to log out. (PDF161/printed150; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Sign out clears browser authentication and owner drafts, then navigates to /auth.|Layout.tsx signOut; recommendation.spec.ts Sign-out clears owner-scoped drafts; J11/J14 browser regressions|Clearing this browser does not revoke a copied bearer token; FR-ACC-15 remains Partial.|Retain browser sign-out behaviour; close the separate invalidation contract.|
|FR-ACC-15|The system shall invalidate the active session, clear the stored authentication information and direct the user to the login page after logout. (PDF162/printed151; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Browser token/draft removal and auth redirect implemented; server only verifies HMAC and expiry.|Layout.tsx; security.py token_user_id; account_routes.py has no logout/revocation route|A previously copied unexpired token is not invalidated by browser logout; no session revocation store/version.|Shared auth owner agrees and implements actual active-session invalidation, with replay-after-logout tests; no security change authorized here.|

### FR-PP

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|FR-PP-01|The system shall allow a Registered User to view their own profile information and stored clothing preferences. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Owner-scoped profile/preferences reads, bounded display-name update and stored style-note save/display exist.|account_service.py; profile/page.tsx; test_workflow.py profile/preference API and login flows|Verified for implemented profile fields; does not imply full structured preference UX or arbitrary-format acceptance.|Retain implemented owner profile; address missing preference capabilities in FR-PP-03/05.|
|FR-PP-02|The system shall allow a Registered User to edit their profile information. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Owner-scoped profile/preferences reads, bounded display-name update and stored style-note save/display exist.|account_service.py; profile/page.tsx; test_workflow.py profile/preference API and login flows|Verified for implemented profile fields; does not imply full structured preference UX or arbitrary-format acceptance.|Retain implemented owner profile; address missing preference capabilities in FR-PP-03/05.|
|FR-PP-03|The system shall allow a Registered User to update supported clothing preferences, including preferred colours, styles, garment categories and levels of formality. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|Backend/scorer support structured colours/styles/categories/formality, but profile UI exposes only free-text style_note.|profile/page.tsx; account_service.upsert_preference; PreferenceNormalizer; J12-J16 fixture preferences|Most free-form notes do not map to a supported style; ordinary users lack controlled editors for the four original preference groups.|Shared profile/R owner approves minimal controlled preference editing wired to existing scorer semantics; no new algorithm needed.|
|FR-PP-04|The system shall validate the updated profile information before saving it. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|ProfileUpdate bounds display_name length; UI trims; normal profile update is exercised.|account_routes.py ProfileUpdate; profile/page.tsx; retained test_workflow.py successful profile edit|No retained invalid-profile-fields execution located; complete accepted-format rules are not independently verified.|Shared profile owner agrees valid/invalid formats and verifies server rejection before persistence.|
|FR-PP-05|The system shall validate that clothing-preference values use the categories and values supported by the system. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Partial**|PreferenceUpsert bounds weight but accepts arbitrary preference_type and JSON value; normalizer validates later at scoring.|account_routes.py; requests.py PreferenceUpsert; account_service.upsert_preference; preference_normalizer.py|Unsupported/malformed values can be stored; downstream rejection/diagnostics are not save-time validation.|Shared API owner approves type/value validation at write boundary; preserve supported stored semantics and unknown historical data.|
|FR-PP-06|The system shall save valid profile and preference changes and display the updated information to the Registered User. (PDF163/printed152; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Owner-scoped profile/preferences reads, bounded display-name update and stored style-note save/display exist.|account_service.py; profile/page.tsx; test_workflow.py profile/preference API and login flows|Verified for implemented profile fields; does not imply full structured preference UX or arbitrary-format acceptance.|Retain implemented owner profile; address missing preference capabilities in FR-PP-03/05.|
|FR-PP-07|The system shall allow the Registered User to cancel editing without saving the changes. (PDF164/printed153; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|Profile fields are local state until Save; navigation can abandon edits; no explicit cancel/reset control.|Static profile/page.tsx; no retained cancel-specific profile verification located|Cannot certify original cancel-without-saving workflow from profile API success tests.|Agree intended cancel UX and verify discarded edits; implement a small control only if navigation alone is not accepted.|
|FR-PP-08|The system shall retain the previously stored profile and preference information when an update fails. (PDF164/printed153; Not specified in FR table)|Shared: account/profile/frontend; **Unverified**|Profile/preference writes use context-managed transaction; UI displays failed save.|account_service.py connection context; profile/page.tsx catch; retained workflow success evidence|No retained focused profile/preference failure-injection preservation evidence located.|Verify failed update preserves prior values in the approved account/profile correction round.|
|FR-PP-09|The system shall prevent a Registered User from viewing or modifying the profile and preferences belonging to another user. (PDF164/printed153; Not specified in FR table)|Shared: account/profile/frontend; **Verified**|Owner-scoped profile/preferences reads, bounded display-name update and stored style-note save/display exist.|account_service.py; profile/page.tsx; test_workflow.py profile/preference API and login flows|Verified for implemented profile fields; does not imply full structured preference UX or arbitrary-format acceptance.|Retain implemented owner profile; address missing preference capabilities in FR-PP-03/05.|

### NFR

| ID | Original wording / authority | Owner / status | Actual implementation | Executed verification evidence | Accepted scope and limitations | Remaining completion/approval action |
|---|---|---|---|---|---|---|
|NFR-01|The system shall display one valid homepage outfit recommendation within three seconds after the homepage has completed loading under the baseline test environment. (PDF180/printed169; Must)|R + shared NFR/deployment; **Unverified**|J16 complete observed local pass at unchanged3s/5s/2s, with full browser/HTTP raw ledger and correctness audit.|J16:105 browser+21 HTTP;221 regressions; performance-summary.json/timing-ledger.csv/trials.json|Formal baseline/history maximum unapproved; CPU47.88-100%, synthetic images, one local worker; post-collection shutdown timeout.|Owner/supervisor adopts or amends exact environment/workload/boundaries/statistics and qualifications; no automatic rerun of completed passing cells.|
|NFR-02|The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment. (PDF180/printed169; Must)|R + shared NFR/deployment; **Unverified**|J16 complete observed local pass at unchanged3s/5s/2s, with full browser/HTTP raw ledger and correctness audit.|J16:105 browser+21 HTTP;221 regressions; performance-summary.json/timing-ledger.csv/trials.json|Formal baseline/history maximum unapproved; CPU47.88-100%, synthetic images, one local worker; post-collection shutdown timeout.|Owner/supervisor adopts or amends exact environment/workload/boundaries/statistics and qualifications; no automatic rerun of completed passing cells.|
|NFR-03|The system shall return chat-history search results within two seconds under the maximum chat-history workload defined in the system test plan. (PDF180/printed169; Must)|R + shared NFR/deployment; **Unverified**|J16 complete observed local pass at unchanged3s/5s/2s, with full browser/HTTP raw ledger and correctness audit.|J16:105 browser+21 HTTP;221 regressions; performance-summary.json/timing-ledger.csv/trials.json|Formal baseline/history maximum unapproved; CPU47.88-100%, synthetic images, one local worker; post-collection shutdown timeout.|Owner/supervisor adopts or amends exact environment/workload/boundaries/statistics and qualifications; no automatic rerun of completed passing cells.|
|NFR-04|The system shall handle failures in NLP interpretation, garment retrieval, recommendation generation, and chat-history storage without terminating the user session or causing the application to become unresponsive. (PDF180/printed169; Must)|R + shared NFR/deployment; **Verified**|Controlled failure/no partial result; atomic request/recommendation/item/metadata/receipt persistence, immutable history and duplicate-key replay.|test_recommendation_persistence.py; J12 late-fault rollback; J14 cross-form concurrent201/200; J15 faults; J16 history hashes|Same-file SQLite connections; not OS-kill/in-flight drain/multi-process/PostgreSQL recovery certification.|Retain functional atomicity/replay; verify actual service lifecycle separately without rewriting history.|
|NFR-05|The system shall preserve existing wardrobe and chat-history records when the processing of a new NLP request fails. (PDF180/printed169; Must)|R + shared NFR/deployment; **Verified**|Controlled failure/no partial result; atomic request/recommendation/item/metadata/receipt persistence, immutable history and duplicate-key replay.|test_recommendation_persistence.py; J12 late-fault rollback; J14 cross-form concurrent201/200; J15 faults; J16 history hashes|Same-file SQLite connections; not OS-kill/in-flight drain/multi-process/PostgreSQL recovery certification.|Retain functional atomicity/replay; verify actual service lifecycle separately without rewriting history.|
|NFR-06|The system shall store a completed chat-history record as a single atomic operation so that the request and corresponding recommendation are either both stored or neither is stored. (PDF181/printed170; Must)|R + shared NFR/deployment; **Verified**|Controlled failure/no partial result; atomic request/recommendation/item/metadata/receipt persistence, immutable history and duplicate-key replay.|test_recommendation_persistence.py; J12 late-fault rollback; J14 cross-form concurrent201/200; J15 faults; J16 history hashes|Same-file SQLite connections; not OS-kill/in-flight drain/multi-process/PostgreSQL recovery certification.|Retain functional atomicity/replay; verify actual service lifecycle separately without rewriting history.|
|NFR-07|The system shall prevent duplicate chat-history records from being created when the same request submission is unintentionally processed more than once. (PDF181/printed170; Must)|R + shared NFR/deployment; **Verified**|Controlled failure/no partial result; atomic request/recommendation/item/metadata/receipt persistence, immutable history and duplicate-key replay.|test_recommendation_persistence.py; J12 late-fault rollback; J14 cross-form concurrent201/200; J15 faults; J16 history hashes|Same-file SQLite connections; not OS-kill/in-flight drain/multi-process/PostgreSQL recovery certification.|Retain functional atomicity/replay; verify actual service lifecycle separately without rewriting history.|
|NFR-08|The system shall require an authenticated session before homepage recommendations, NLP requests, or chat-history records can access user-specific wardrobe data. (PDF181/printed170; Must)|R + shared NFR/deployment; **Verified**|Signed authentication/owner checks; bounded text/search validation and parameterized SQL; controlled client errors conceal internal faults.|J14 auth/routing matrix; J15 owner/fault cases; J16 literal/Unicode history; existing security remediation evidence|Code/runtime scope only; deployed TLS, secret lifecycle, broad penetration testing and token revocation are separate.|Retain authenticated boundaries and safe errors; no broad security rewrite authorized.|
|NFR-09|The system shall prevent one user from accessing, searching, or viewing the wardrobe records, NLP requests, recommendations, or chat histories belonging to another user. (PDF181/printed170; Must)|R + shared NFR/deployment; **Verified**|Signed authentication/owner checks; bounded text/search validation and parameterized SQL; controlled client errors conceal internal faults.|J14 auth/routing matrix; J15 owner/fault cases; J16 literal/Unicode history; existing security remediation evidence|Code/runtime scope only; deployed TLS, secret lifecycle, broad penetration testing and token revocation are separate.|Retain authenticated boundaries and safe errors; no broad security rewrite authorized.|
|NFR-10|The system shall validate and sanitise all NLP request text and chat-history search input before the input is processed or submitted to the database. (PDF181/printed170; Must)|R + shared NFR/deployment; **Verified**|Signed authentication/owner checks; bounded text/search validation and parameterized SQL; controlled client errors conceal internal faults.|J14 auth/routing matrix; J15 owner/fault cases; J16 literal/Unicode history; existing security remediation evidence|Code/runtime scope only; deployed TLS, secret lifecycle, broad penetration testing and token revocation are separate.|Retain authenticated boundaries and safe errors; no broad security rewrite authorized.|
|NFR-11|The system shall transmit authenticated requests, wardrobe information, recommendations, and chat-history data through encrypted HTTPS connections in the deployed environment. (PDF182/printed171; Must)|R + shared NFR/deployment; **Unverified**|Current measured topology uses local HTTP; deployment documentation describes frontend/backend separation.|J13/J14/J16 process commands; backend/deployment/README.md|No actual HTTPS endpoint/certificate/proxy configuration or deployed encrypted journey inspected.|Deployment owner provides approved TLS topology and verifies authenticated transport; local HTTP cannot certify this row.|
|NFR-12|The system shall not expose authentication tokens, database credentials, internal exception traces, or server configuration details through user-facing messages. (PDF182/printed171; Must)|R + shared NFR/deployment; **Verified**|Signed authentication/owner checks; bounded text/search validation and parameterized SQL; controlled client errors conceal internal faults.|J14 auth/routing matrix; J15 owner/fault cases; J16 literal/Unicode history; existing security remediation evidence|Code/runtime scope only; deployed TLS, secret lifecycle, broad penetration testing and token revocation are separate.|Retain authenticated boundaries and safe errors; no broad security rewrite authorized.|
|NFR-13|The system shall record processing failures with sufficient technical information for troubleshooting while excluding authentication credentials and other security-sensitive values from application logs. (PDF182/printed171; Must)|R + shared NFR/deployment; **Partial**|CV workflow logs exceptions, but Assistant/Homepage catch broad failures and return generic status without diagnostic logging.|outfit_assistant_service.py except Exception; homepage_recommendation_service.py except Exception; grep/static review|Test-only ASGI logs and Uvicorn access messages do not supply production recommendation failure context or secret-redaction proof.|R/shared owner approves minimal sanitized failure-context logging plus failure/redaction verification; no raw request/token logging.|
|NFR-14|The system shall present validation, unsupported-request, no-result, and processing-error messages using clear language that identifies the result and an appropriate next action without exposing internal technical details. (PDF182/printed171; Must)|R + shared NFR/deployment; **Verified**|Shared result/message components and consistent Layout provide controlled outcome text, next-action guidance and common page controls.|recommendation-messages.ts,RecommendationResult.tsx,Layout.tsx; retained J11/J14/J15 browser outcomes|Subjective usability/full accessibility and all-browser behaviour not certified by component reuse.|Retain wording/layout; complete explicit accessibility/browser verification in shared final check.|
|NFR-15|The system shall maintain a consistent arrangement and terminology for recommendation cards, NLP request controls, chat-history records, and error messages across the supported pages. (PDF182/printed171; Should)|R + shared NFR/deployment; **Verified**|Shared result/message components and consistent Layout provide controlled outcome text, next-action guidance and common page controls.|recommendation-messages.ts,RecommendationResult.tsx,Layout.tsx; retained J11/J14/J15 browser outcomes|Subjective usability/full accessibility and all-browser behaviour not certified by component reuse.|Retain wording/layout; complete explicit accessibility/browser verification in shared final check.|
|NFR-16|The recommendation and NLP interaction pages shall remain usable without horizontal scrolling at viewport widths from 360 pixels to 1,920 pixels. (PDF183/printed172; Should)|R + shared NFR/deployment; **Unverified**|Responsive layouts, native controls/labels/focus and accessible status markup exist; primary retained runs use Chromium1280x960.|Layout.tsx/Assistant/history components; T mobile screenshots reported; J16 browser-environment.json|No complete retained360-1920 no-scroll, keyboard journey,200% zoom or actual latest Chrome/Edge/Firefox verification located.|Shared frontend owner supplies existing evidence or performs one focused viewport/keyboard/zoom/three-browser check; no performance matrix rerun.|
|NFR-17|All interactive controls required to submit an NLP request, search chat history, and open a chat-history record shall be accessible using keyboard navigation. (PDF183/printed172; Should)|R + shared NFR/deployment; **Unverified**|Responsive layouts, native controls/labels/focus and accessible status markup exist; primary retained runs use Chromium1280x960.|Layout.tsx/Assistant/history components; T mobile screenshots reported; J16 browser-environment.json|No complete retained360-1920 no-scroll, keyboard journey,200% zoom or actual latest Chrome/Edge/Firefox verification located.|Shared frontend owner supplies existing evidence or performs one focused viewport/keyboard/zoom/three-browser check; no performance matrix rerun.|
|NFR-18|Text displayed within recommendation results, chat-history records, form labels, validation messages, and action controls shall remain readable at a browser zoom level of 200%. (PDF183/printed172; Should)|R + shared NFR/deployment; **Unverified**|Responsive layouts, native controls/labels/focus and accessible status markup exist; primary retained runs use Chromium1280x960.|Layout.tsx/Assistant/history components; T mobile screenshots reported; J16 browser-environment.json|No complete retained360-1920 no-scroll, keyboard journey,200% zoom or actual latest Chrome/Edge/Firefox verification located.|Shared frontend owner supplies existing evidence or performs one focused viewport/keyboard/zoom/three-browser check; no performance matrix rerun.|
|NFR-19|The recommendation and NLP interaction functions shall operate correctly on the latest stable versions of Google Chrome, Microsoft Edge, and Mozilla Firefox available during system testing. (PDF183/printed172; Should)|R + shared NFR/deployment; **Unverified**|Responsive layouts, native controls/labels/focus and accessible status markup exist; primary retained runs use Chromium1280x960.|Layout.tsx/Assistant/history components; T mobile screenshots reported; J16 browser-environment.json|No complete retained360-1920 no-scroll, keyboard journey,200% zoom or actual latest Chrome/Edge/Firefox verification located.|Shared frontend owner supplies existing evidence or performs one focused viewport/keyboard/zoom/three-browser check; no performance matrix rerun.|
|NFR-20|The system shall separate NLP interpretation logic, recommendation rules, ranking logic, data-access operations, and user-interface presentation into independently maintainable components. (PDF183/printed172; Must)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|
|NFR-21|Recommendation rules and ranking weights shall be maintained in configurable components so that they can be modified without changing the NLP-page or homepage interface code. (PDF184/printed173; Should)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|
|NFR-22|Changes to NLP interpretation rules shall not require modification of chat-history storage or homepage recommendation functions unless the stored data structure is intentionally changed. (PDF184/printed173; Should)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|
|NFR-23|The system shall provide unit tests for the principal successful, unsupported-request, no-result, and processing-failure paths of the NLP interpretation and recommendation-generation components. (PDF184/printed173; Should)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|
|NFR-24|The system shall use consistent persistent references across subsystem boundaries: garment records shall be obtained through the Digital Wardrobe subsystem’s ConfirmedGarmentQuery, while Recommendation-to-Visualisation requests shall transfer a Recommendation reference through the VisualisationGateway rather than a trusted final list of garment identifiers. (PDF184/printed173; Must)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|
|NFR-25|The system shall safely reject or handle missing, malformed, unauthorised or stale cross-subsystem references. Recommendation processing shall use only garment records supplied through ConfirmedGarmentQuery, while Outfit Visualisation shall resolve and revalidate referenced garments against the current Digital Wardrobe state before visualisation processing. (PDF184/printed173; Must)|R + shared NFR/deployment; **Verified**|Separated NLP/rule/rank/query/UI modules, versioned configurable policies, tests and validated ID-based query/VisualisationGateway handoff.|Original source/transition guards; J1 source revalidation; J5/J8 exact oracles; J14/J15/J16 regressions|Known ai-services canonical-folder assertion remains a distinct architecture issue; configurability does not authorize casual policy edits.|Retain module contracts; shared architecture owner reconciles canonical layout separately without deleting ai-services.|

## Appendix B. Separate20-constraint/assumption register

These are not additional FR/NFR/RN requirements and do not inflate the155-row
verified tally. Assumptions are evaluated conditions, not implemented features.
Unverified does not imply a new feature must be built to make every assumption
universally true. Original wording is retained from PDF193–197.

| ID/type | Original wording | Status / evidence boundary | Owner / remaining action |
|---|---|---|---|
|CA-01/Constraint|The recommendation and NLP interaction functions shall be delivered as part of a web-based Smart Wardrobe System. (PDF193)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-02/Constraint|Personalised recommendations and chat-history functions are available only to authenticated users. (PDF193)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-03/Constraint|Outfit recommendations are limited to garments stored in the authenticated user’s digital wardrobe. (PDF193)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-04/Constraint|Only confirmed and available garment records may be used for recommendation generation. (PDF193)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-05/Constraint|The prototype is limited to the casualwear garment categories defined within the project scope. (PDF194)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-06/Constraint|Recommendation generation is based on documented rules, constraints, preferences, and scoring criteria. (PDF194)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-07/Constraint|Each NLP chat contains one submitted request and one corresponding recommendation. (PDF194)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-08/Constraint|The NLP workflow does not support follow-up clarification questions. (PDF194)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-09/Constraint|Each successfully processed NLP request returns exactly one outfit recommendation. (PDF194)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-10/Constraint|NLP interpretation is limited to the supported request fields documented for the prototype. (PDF195)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-11/Constraint|Random homepage recommendations do not create NLP chat-history records. (PDF195)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-12/Constraint|Recommendation outputs depend on garment identifiers and attributes provided by other system components. (PDF195)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-13/Constraint|The project must be completed within the available FYP schedule, development resources, and prototype deployment environment. (PDF195)|Unverified as a universal/deployed assumption.|Owner/supervisor confirms schedule/resources/release scope.|
|CA-14/Assumption|Users provide outfit requests that are generally related to clothing, occasion, style, colour, category, or formality. (PDF195)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain bounded vocabulary/ownership/interfaces. CA14 is tested domain handling, not a guarantee of user behaviour.|
|CA-15/Assumption|Garment attributes supplied to the recommendation component are sufficiently accurate for rule application. (PDF196)|Unverified as a universal/deployed assumption.|T supplies real attribute/provenance evidence; do not infer accuracy from synthetic tests.|
|CA-16/Assumption|Users maintain their wardrobe records and garment availability status. (PDF196)|Unverified as a universal/deployed assumption.|Owner/T inventories real wardrobe availability; stale history is shown honestly.|
|CA-17/Assumption|The user has sufficient garment categories available to form at least one valid outfit. (PDF196)|Unverified as a universal/deployed assumption.|No guarantee every owner has sufficient categories; retained controlled no-result handling is appropriate.|
|CA-18/Assumption|Each user account is associated with one personal digital wardrobe and its related recommendation history. (PDF196)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-19/Assumption|The data fields and garment identifiers exchanged between the wardrobe, recommendation, visualisation, and history components remain consistent. (PDF196)|Verified for controlled local contract; J12/J14/J15/J16 owner/query/structure/single-request evidence.|R/shared; retain documented scope; no new implementation.|
|CA-20/Assumption|The supported web browser and network connection are available when the user accesses the system. (PDF197)|Unverified as a universal/deployed assumption.|Deployment owner verifies actual browser/network target; local loopback is limited evidence.|
