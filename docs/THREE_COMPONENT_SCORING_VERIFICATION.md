# Phase 5F-2E-3J-5: three-component scoring and controlled activation readiness

2026-10-22. Verification-only change. Owner has accepted the existing bounded heuristic, without independently validated fashion-quality claims. This phase does not activate any production default. **Final verification: PASS WITH LIMITATIONS, ready for owner closure; scoring-default recommendation: DEFER.** The completed resumption below supersedes the earlier resource-blocked checkpoint. Formal NFR-02 and overall release acceptance remain open.

## Current configuration and report authority

Original report sections4.4.3/4.10.4 require documented three-component scoring, normalised consistent scales, weights summing to1, valid candidates only and deterministic top-one ranking. The particular colour/Dice/midpoint/dress conventions and exact numeric weights are accepted implementation policies, not report-prescribed fashion facts.

Production remains compact_exhaustive execution, compatibility_deferred scoring, suitability default false. Reference execution remains supported. Scoring selector accepts only compatibility_deferred and experimental_compatibility_decision_v1; execution accepts only compact_exhaustive/reference. Invalid selections reject composition even when the Assistant is disabled. Tests reuse existing rejection checks, four-way execution and rollback paths. No client selector is added. Environment is read by composition at startup, not assumed from a .env file.

Isolated real-suitability tests explicitly select Assistant true, suitability true, compact_exhaustive and experimental_compatibility_decision_v1. The dedicated browser launcher uses genuine upload/review/confirm and authenticated login on disposable SQLite with labelled development AI, not real model quality. The separate four-way production-browser/performance fixture retains suitability false and synthetic strict linked garments; it is not a deployment or CV proof. These distinct evidence populations must not be conflated.

## Formula and exact conventions, unchanged

Experimental `S=(3/5)R+(1/5)C_decision+(1/5)P`; deferred `S=(7/10)R+(3/10)P`. Exact Fraction arithmetic is preserved. Weights sum to1, no per-candidate renormalisation. Every mandatory-valid candidate is considered through the complete stream, then compared by total,R,C contribution,P,stable ordered role/garment key. The stable key is the tuple of role/ID entries, not an arbitrary fashion preference; the separate SHA candidate identity is not substituted for that key. One highest-ranked result is published only after stream completion and independent mandatory validation.

Recognised identical or achromatic primary colour pair ->1; other recognised pair ->0, a limited coordination proxy rather than proof of a clash. Style atom is Dice `2|A intersection B|/(|A|+|B|)` for complete known nonempty style sets. Empty style collections have no positive style evidence; pairwise compatibility style is unresolved, not a measured zero. Multiple style annotations are sets. Outerwear participates in every genuine pair. No pattern/material/fit/Oklab rule is enabled.

For M atoms, known sum K and m unresolved atoms, `L=K/M`, `U=(K+m)/M`, `C=(L+U)/2`. Computed/PartiallyConventional/FullyConventional remain distinct; raw unknown is NULL, not a measured midpoint. A dress is one garment, zero pairs, raw NotApplicable, NoPairReference contribution1/2. A conventional numerical contribution is neither a human rating nor positive mandatory evidence. Unknown/Fail mandatory conditions cannot be rescued by P or C. Named/alias/exact-anchor colour policy stays unchanged; approximation disabled.

R averages supplied field contributions. Passed hard fields contribute1; style contributes matching base members divided by base members, which permits different valid-request scores. Generic request has R numerical0 with NotApplicable, not perfect1. P uses the authenticated stored snapshot/importance values; colour presence, base-style fractions and supported category/group presence follow existing rules. No preferences has numerical0 with NoPreferences. Style may contribute through R/C/P; signals are intentionally related and not claimed statistically independent.

## Fixed cases and independent arithmetic

Initial synthetic `scoring_acceptance.v1.json` freezes9 descriptor/request/preference cases before execution. Supplementary `scoring_evidence_competition.v1.json` adds one independently specified missing/empty/known/dress competition case, frozen before its own first execution; the original9-case fixture is not tuned or rewritten. No ratings/reviewers or real-population frequencies are fabricated.

The new test oracle imports no production scoring formulas: it enumerates simple fixture slot combinations with itertools, computes Fraction R/C/P and both totals independently, and uses the documented tie sequence. For each actual confirmed candidate, production R/C/P and compatibility basis must equal the oracle. Actual integrated HTTP winners/totals/scored counts must equal it under all four engine/profile selections. Historical same-key retries after each selection change must preserve score metadata and provenance. Actual materialised garment IDs and exact results are retained in comparisons.jsonl; friendly descriptor labels are fixed, while normal confirmation issues fresh UUIDs. Reproduction of ID-sensitive ties uses those captured materialised IDs; a new upload can create new UUIDs, not a new ranking rule.

| Fixed case | R | C decision | P | Deferred total | Experimental total | Evidence |
|---|---:|---:|---:|---:|---:|---|
| Known contrasting colour/disjoint style pair, generic |0|0|0|0|0|Computed zero, not unknown |
| Blue/white pair, one missing style, generic |0|3/4|0|0|3/20|PartiallyConventional |
| Both colours/styles missing, generic |0|1/2|0|0|1/10|FullyConventional |
| Blue/white pair, deliberate empty styles, generic |0|3/4|0|0|3/20|PartiallyConventional |
| Blue pair, styles vintage+classic versus vintage; vintage request, classic preference |1|5/6|1/2|17/20|13/15|Computed Dice2/3 |
| Single dress, generic/no preferences |0|1/2|0|0|1/10|NoPairReference, raw NA |
| Dress+white vintage outerwear, outerwear request |1|1|0|7/10|4/5|Computed |
| Blue/white vintage pair + red classic outerwear, outerwear request |1|1/2|0|7/10|7/10|Computed6 genuine atoms |

### Mixed ranking change

The mixed wardrobe has blue vintage top t, white vintage bottom b1, red classic bottom b2, blue vintage dress d and red classic outerwear o. Request vintage. Equal stored preferences: red colour and top group. All six supported candidates pass mandatory requirements.

| Candidate | R | C | P | Deferred | Experimental |
|---|---:|---:|---:|---:|---:|
| t+b1 |1|1|1/2|17/20|9/10 |
| t+b1+o |1|1/2|1|1|9/10 |
| t+b2 |1/2|0|1|13/20|1/2 |
| t+b2+o |1/2|1/3|1|13/20|17/30 |
| d |1|1/2|0|7/10|7/10 |
| d+o |1|0|1/2|17/20|7/10 |

Deferred selects t+b1+o at1; experimental selects t+b1 at9/10, tied on total/R with the trio but ahead on C1 versus1/2. This is an accepted weighting/tie trade-off, not evidence of improved taste. The changed R/P weights also contribute; this is not an isolated C ablation. The multi-style case explicitly overlaps style through R,C and P.

The supplemental competition includes a blue vintage top, red/classic bottom, missing-evidence bottom, white/empty-style bottom, blue vintage dress and white vintage outerwear. Under the same vintage request, unlayered known-low pair has R1/2,C0,S3/10; missing pair R1/2,C1/2,S2/5; empty-style/known-coordinating pair R1/2,C3/4,S9/20. Missingness can outrank observed low evidence; it is disclosed, not claimed objectively better. Dress raw NA contributes1/2 and S7/10; dress+outerwear has C1,S4/5. Both profile winners and all candidate arithmetic are retained, not just a selected screenshot. These cases demonstrate conventions across structures without garment-count bonuses or dress exclusion.

## Suitability, persistence and UI

Eighteen experimental integrated cases vary top/bottom/outerwear over Allow,Deny,missing,conflict,malformed and Deny+Unknown. All-positive passes; any Deny fails before scoring, otherwise Unknown is insufficient. Maximum matching colour preference and style cannot rescue failure. Genuine review/confirmation and strict Phase1 retrieval are used. Existing full J-4 matrix and regression tests retain8/2, exercise/formal unavailable, cumulative five-field matching, arbitrary hex unknown and unsupported local bindings.

Dedicated experimental browser journey performs actual upload/review/confirm, friendly Campus/Casual controls and If-Match save, reload, a five-field request, declaration change, fresh failure and immutable completed replay/history. A dress correctly displays Default contribution for a single-piece outfit with NoPairReference provenance. Four-way production-browser tests cover Computed,partial,fully unknown,zero,dress,trio,dress+outerwear explanations, history and cross-user denial. No major dashboard or frontend application change is made.

Existing explanations explicitly say rules are not independent fashion ratings, unknown is not poor compatibility, midpoint is a ranking convention and dress has no garment-pair measurement. Raw evidence and decision are separate. Historical deferred records remain deferred after selecting experimental; no rescore or rewrite. Atomic rollback, failures after provisional winner, transaction revalidation, duplicate-key concurrency and idempotent replay remain regression gates. Test-only loopback selectors do not add ordinary-client runtime overrides.

## Performance collection plan, not NFR acceptance

After tests/builds finish, use existing representative balanced structural workload at50/100/200 (2,430/17,710/134,820 candidates), vintage request and one blue colour preference. Preserve both deferred and experimental under compact, three fresh submissions per size/profile/layer for HTTP and actual production browser:36 calls. No reference stress matrix is repeated. All first calls, errors, timeouts and values above5s are retained. Existing proxy policy is unchanged. Browser boundary is submit to visible result card; login/page preparation is outside and image-loading acceptance is not claimed for synthetic media. HTTP is direct authenticated backend, separate from the production same-origin browser proxy boundary.

Retain existing collection controls:10s settle, at most120s preflight, three consecutive observations CPU<=20% and free RAM>=4GiB. These are measurement controls, not a report-defined acceptance baseline. Before/after CPU/RAM/process observations are snapshots, not continuous isolation. No user applications are stopped. No hidden ranking warm-up or candidate truncation. The fixture's existing compact observer captures timing/cache diagnostics without enabling heavy profiling; result times are sanity measurements, not clean production deployment certification.

No suitable pre-existing frozen varied-evidence50/100/200 service fixture is selected here. The known homogeneous balanced fixture is kept unchanged for comparability; the separately frozen10 semantic cases exercise varied evidence but are not mislabelled a large-wardrobe performance population. Formal representative evidence distributions and NFR baseline remain separate approval work. The five-second NFR-02 target is unchanged and this is not formal acceptance.


## Completed functional verification

| Check | Result |
|---|---|
| New initial fixed-case and mandatory-suitability suite |27 passed,23.59s |
| Focused scoring/ranking/persistence/suitability/action/visualisation suite |456 passed,189.89s |
| Supplementary missing/empty/dress competition |1 passed,5.00s, added after broad collection |
| Broad backend, separate CV geometry excluded |2,064 passed,1 known failure,370.73s |
| Production browser four-way profile/engine/history/UI cases |28 passed,44.4s |
| Actual experimental+enabled-suitability browser |1 passed,50.3s |
| TypeScript/lint/isolated production build |Exit0; two existing navigation warnings only |

The sole broad failure remains test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations, whose retained assertion forbids ai-services. Neither folder nor assertion is changed. The supplementary case is reported separately rather than added to broad/focused totals. The initial new test run omitted its imported lifecycle fixture and errored before execution; the corrected setup is retained with the original log. No production bug fix or policy change followed.

Saved-outfit strict validation, forward style states, If-Match contention/rollback, suitability, old historical records, atomic persistence and stream completion/failure remain covered by these unchanged regression suites. The28 production-browser checks use suitability disabled; the actual confirmed-garment journey separately uses suitability enabled. Old54 browser results are not called newly rerun. Heavy CV geometry, real models, PostgreSQL/deployment and formal NFR acceptance remain outside this verification.

The owner-accepted profile's RN-17 calculation is functionally verified under explicit selection with existing explanations and four-way equivalence. Actual normal/default workflow still selects deferred and does not provide the three-component criterion; RN-17 default-path closure therefore still needs separately approved activation and its configuration checks. This is not a new demand for fashion reviewers or a new architecture. Human fashion-quality validation remains a limit on stronger claims, not a fabricated arithmetic acceptance threshold.

## Resource qualification before timing

After all test/build/browser workloads finished, a three-second host sample reported Ryzen5 7235HS,8 logical processors,17% CPU and7.51GiB free physical RAM. OneDrive used13.54% and OneDrive.Sync.Service4.69% machine CPU in that delta sample. These different measurement windows are not additive to the single OS sample. This is material competing activity in the OneDrive-backed workspace, so timed collection did not begin and workload relief was requested. host-before-timing.json is retained. No user applications were terminated. Subsequent resource observations and any blocked collection attempts must remain separately labelled.


## Current stage status: functional PASS, performance PENDING / resource-blocked

A fresh recheck at17:09:22+08:00 reported29% CPU and7.48GiB free RAM. OneDrive consumed13.35% machine CPU in the separate three-second delta and its sync service2.54%. Both host observations are retained. Owner workload relief was requested asynchronously; no confirmation had arrived at this checkpoint. No timed submissions were started, so **no50/100/200 medians/maxima/timeouts are fabricated**. Previous phases' results, including experimental200 median6.017s, remain historical evidence; deferred quiet200 median4.542s does not establish experimental performance.

**Recommendation at this checkpoint: DEFER the normal scoring-default transition pending controlled performance collection.** This is not a rejection of the owner-accepted calculation or a reproduced scoring defect. Functional/profile/suitability/history evidence passes. The current200-garment timing risk is unresolved; if controlled experimental200 still exceeds5s, report the failures and seek separately authorised targeted optimisation before formal release acceptance. No workload reduction, timeout increase or weight/rule change is authorised.

**J-5 is not yet ready for closure:** the requested targeted36-call sanity remains outstanding. After resource relief, recheck competing processes and run only the prepared targeted collector; do not repeat passing functional/broad suites without a new reason. Retain new run labels, all observations and any resource-blocked attempts. A complete performance report must precede the final ACTIVATE/REVISE/DEFER decision. General production scoring/suitability defaults remain unchanged. No formal NFR-02 acceptance, experimental activation or next phase occurs.

## Changed-file inventory

Only new test/evidence/configuration files plus the appended traceability are introduced:

| File | Purpose |
|---|---|
| backend/tests/fixtures/scoring_acceptance.v1.json | Frozen nine-case synthetic descriptor/request/preference set. |
| backend/tests/fixtures/scoring_evidence_competition.v1.json | Separately frozen missing/empty/dress competition case. |
| backend/tests/test_scoring_acceptance.py | Independent Fraction oracle, real-confirmed per-candidate evidence, four-way HTTP winners/replay and experimental mandatory-suitability cases. |
| backend/tests/scoring_suitability_server.py | Explicit experimental+enabled-suitability disposable authenticated browser launcher. |
| frontend/tests/phase5f/scoring-suitability.spec.ts | Real annotation-to-experimental recommendation/history workflow. |
| frontend/tests/phase5f/scoring-acceptance-performance.spec.ts | Prepared36-call resource-qualified collector; not yet executed. |
| frontend/playwright.scoring-suitability.config.ts | Isolated enabled experimental browser environment. |
| frontend/playwright.scoring-acceptance.config.ts | Production build/server isolation for existing28 four-way browser checks and targeted sanity. |
| docs/THREE_COMPONENT_SCORING_VERIFICATION.md | This report and pending-performance assessment. |
| docs/REPORT_TRACEABILITY.md | Appended scoped status only. |

Local storage/verification/phase5f2e3j5 artifacts additionally contain original hashes/config, full commands/logs, exact materialised comparisons, raw browser result, resource observations and integrity indexes. No production application source, package lock, historical scoring configuration, prior fixture/archive or previous raw evidence was modified. Original tsconfig bytes were restored after checking only generated build includes changed. Existing source guards passed in the broad suite. Prior J-2/J-3/J-4 raw indexes match37/26/33 artifacts respectively. No real CV, Postgres or deployed worker certification is claimed.


## Resumed targeted performance: completed after owner paused OneDrive

The owner confirmed syncing was paused and authorised continuation of the existing work. host-after-pause.json reports37% OS CPU and6.67GiB free RAM in its initial snapshot; the separate process delta no longer showed OneDrive among the leaders. The existing automated preflight then retained8 observations, including startup CPU69%, and qualified at9%,18%,19% CPU with approximately7.55-7.56GiB free RAM. No timed submission occurred before qualification. All test/build/functional-browser workloads had ended. The prior resource-blocked narrative and report are retained verbatim in verification-before-resumption.md rather than erased.

The production Next collector completed **36/36 authenticated submissions**, each HTTP201/Selected with complete backend processing,36 distinct recommendation IDs and36 chat IDs. All three sizes examined the expected2,430/17,710/134,820 candidates. Compact execution was explicit throughout; both profiles were selected only through the existing disposable loopback fixture control. The normal API/browser path uses authenticated submissions; no ordinary client override or production configuration change is introduced. For each size/profile, six fingerprints (three HTTP, three browser) agree on exact selected members, scores and normalised semantic provenance.

Three trials per size/profile/layer; seconds below are median / maximum. Raw JSON retains every trial, resource observation, completion record, score and provenance.

| Garments / candidates | Deferred HTTP | Deferred browser | Experimental HTTP | Experimental browser |
|---|---:|---:|---:|---:|
|50 /2,430 |0.146 /0.156 |0.292 /0.360 |0.190 /0.219 |0.254 /0.363 |
|100 /17,710 |0.623 /0.647 |0.721 /0.807 |0.836 /0.881 |0.950 /1.041 |
|200 /134,820 |4.549 /4.580 |4.631 /4.658 |5.952 /6.015 |6.069 /6.103 |

All experimental200 values: HTTP6.015,5.952,5.951; browser6.049,6.069,6.103. **Six observations exceeded5s; none are discarded.** No error, timeout, incomplete stream or invalid fallback occurred. All first calls remain included. A passing Playwright collector means evidence collection/semantic checks succeeded, not that the5s target passed. The collector reported1 pass in4.1m.

Timed before/after observations ranged2-44% CPU and7.57-9.42GiB free RAM; preflight had a separate9-69% CPU/6.03-7.56GiB range before qualification. These snapshots do not certify continuous isolation. The matching OneDrive PID accumulated only0.703 CPU-seconds across the timed population, consistent with the earlier sync workload being relieved. Other recorded browser/desktop processes remained; their full activity cannot be excluded by snapshots/top-memory lists. CPU activity also includes the collector's own browser/backend and resource probes. The run is resource-qualified under the retained gate, not a claim of perfectly isolated hardware. No timeout, proxy, workload, weights, comparison formula or collection threshold was relaxed.

Environment: Python3.12.10,Windows11 build26200,Ryzen5 7235HS/8 logical,approximately19.69GiB visible RAM; FastAPI0.146.0,Uvicorn0.54.0,Pillow13.0.0,NumPy2.5.4,python-multipart0.0.32; isolated production Next16.4.2,one Uvicorn process,loopback direct HTTP and existing production same-origin browser proxy. Requests are `Suggest an outfit with vintage style`, one stored blue-colour preference, homogeneous blue/vintage descriptors and the unchanged balanced structural population. This is not representative real CV evidence or image-download acceptance, and no varied-evidence large population was invented. Small sequential samples do not support confidence intervals, fashion accuracy or a causal claim based on the small50-garment browser difference.

Evidence: performance-sanity-j5-initial.json,performance-initial.log,performance-summary.json and reproducible summarize_sanity.py, plus the separate Playwright artifact directory. Commands are appended to commands.txt. Earlier96-trial data, historical slow/timeouts and resource-affected attempts are unchanged. Previously passing functional suites were not repeated merely for this resource retry; their exact results remain those reported above.

## Final acceptance and activation decision

**Recommendation: DEFER making experimental_compatibility_decision_v1 the normal scoring default.** The owner-accepted bounded calculation is functionally verified, with exact arithmetic, disclosed conventional contributions, immutable history, mandatory suitability and four-way equivalence. No scoring defect or need to revise accepted weights/rules was reproduced. Nevertheless experimental200 consistently took about6s in this sanity, including all six direct/browser observations above the unchanged5s target. Default activation now would carry a demonstrated latency risk in the intended200-garment workload.

Minimum remaining work before an activation decision:

1. Separately authorise targeted performance diagnosis/correction of the existing exact experimental path, preserving all candidates, arithmetic, diagnostics, eligibility, history and ranking. Do not start another model or architecture, remove C, reduce the intended workload or extend timeouts to manufacture a pass. No such optimisation is performed here.
2. After any approved correction, run independent same-profile parity/regression checks and a bounded matched sanity with every result retained. Repeat broader matrices only if a specific discrepancy justifies it; do not automatically rerun96 trials.
3. Agree/freeze the final release configuration and formal NFR-02 baseline before formal acceptance;5s remains unchanged. This sanity supplies observed deadline misses, but it is not the approved formal acceptance test. NFR-02 remains OPEN/NOT FORMALLY ACCEPTED.
4. Obtain separate approval for any scoring-default transition, preserve reference/deferred rollback, and verify actual service restart/effective configuration and historical retries. Suitability general default remains false until its own decision; neither feature is globally activated here.

RN-17's bounded explicit-profile functional calculation is verified; the current deferred normal path still does not establish full three-component default fulfilment. Independent fashion-quality claims remain unsupported. Real CV/VTON,actual PostgreSQL/deployment and capacity under concurrent requests are not certified.

**J-5 verification is ready for owner closure as PASS WITH LIMITATIONS.** All requested functional and targeted sanity evidence is collected; performance risk and the DEFER decision are explicit. This supersedes the earlier checkpoint stating J-5 was not ready because timing had not yet run. It does not approve profile activation, formal NFR/FYP acceptance, an optimisation task or another phase. Wait for owner review.
