# Phase 5F-2E-3A: experimental rule-based compatibility

Date: 2026-10-20. Explicit selection only. Neither Homepage nor Outfit Assistant
is wired to this scorer. Live compatibility_deferred, suitability opt-in,
approximate-hex disablement, saved actions and all previous algorithms are unchanged.

## Authority and limitations

Original Project I report RN-17 (PDF188/printed177), RN-18-21 (PDF189),
RN-24-26 (PDF190), sections 4.4.3 (PDF232-233) and 4.10.4 (PDF285-288)
require separate normalized request/compatibility/preference scoring, mandatory
validity first, deterministic total/R/C/P/stable-ID ordering and exactly one
result on success. The exact heuristics here are approved experimental policies,
not independently validated fashion rules or numerical constants in the report.
NFR-02 (PDF180) is end-to-end five-second acceptance, not a Python timing target.

## Exact policy

rule_based_compatibility.v1.json is version rule-based-compatibility-1.0.0,
default_activation=false, pattern_enabled=false, approximate_hex_enabled=false.
Strict schema validation rejects altered rules, activation and internal weights.
Policy and profile hashes are canonical JSON SHA256 values.

Only current primary colour is used, through the existing named aliases and exact
anchors. Secondary/palette data cannot override it. Valid non-anchor hex is
Unrecognized, not nearest-class evidence. The fourteen names are unchanged.

For every unordered garment pair i,j (including outerwear), colour a(i,j)=1
when their recognized primaries are equal OR either is black/white/grey;
otherwise a(i,j)=0. Both colours must be recognized even if one is achromatic.
A measured zero means this coordination proxy was not satisfied, not fashion clash.

For complete recognized nonempty style sets A,B, b(i,j)=2|A intersect B|/(|A|+|B|).
Aliases are canonicalized, duplicates removed. Unsupported labels retain explicit
diagnostics and make style evidence incomplete; recognized labels are not salvaged
as a falsely complete set. No style-to-formality/occasion implication is introduced.

For q>0 pairs, A=sum(a)/q, B=sum(b)/q, C=(A+B)/2. All calculations use Fraction.
Pattern, fit, material, category attractiveness, dominance and temperature are not
scoring factors. Pattern activation requires a new policy version and approval;
there is no hidden pattern contribution in this version.

## Evidence, structures and completion

| Structure | Actual pairs | Compatibility |
|---|---:|---|
| upper+lower | 1 | Exact C if all required pair evidence is known. |
| upper+lower+outerwear | 3 | Exact mean of all three relationships. |
| one_piece | 0 | Summary Unknown; both factor results NotApplicable. |
| one_piece+outerwear | 1 | Exact C if complete; the generated singleton dress remains Unknown. |

Missing styles (None), explicit empty styles (()), malformed collections and
unrecognized text remain distinct prepared states. Current scalar snapshot projection
can collapse blank/invalid source colour/pattern values into absence/fallback; this
scorer cannot reconstruct lost raw state or claim dedicated review provenance.
Existing ColorAnalyzer's empty-pixel #000000 is indistinguishable from genuine black
in the snapshot. Eligibility/confirmation does not prove successful extraction.

Any unavailable required pair evidence makes full C None/Unknown. Available factors
and pair diagnostics remain visible, with observed/possible relationship counts.
No available-only averaging, weight redistribution or missing-evidence bonus occurs.
Partial evidence is represented by Unknown summary plus partial coverage, rather than
misusing the old numeric Partial state. Known zero remains Available with Fraction(0).
Invalid/unavailable configuration raises a policy error; the coordinator maps it to
ProfileUnavailable and never returns a winner.

Prepared annotations are frozen, with frozenset styles and tuple diagnostics, cached
once per garment within each scorer/session. Reusing an ID with changed snapshot
raises an error; fresh sessions may correctly see updated garments.

Experimental profiles are separately versioned rule-based-scoring-1.0.0:
rule_based_request_led=(3/5,1/5,1/5), rule_based_balanced=(1/2,3/10,1/5).
No existing configuration is edited. Both configurations disable default activation.

The explicit RuleBasedRecommendationScorer reuses ScoringEligibilityGate, existing
R/P scorers, exact RecommendationScore validation, ExactScoreReuse and CandidateRanker.
C does not read request/preference values. R/P may remain NA/NoPreferences under
existing semantics; they are never made perfect defaults. Generic no-preference
requests can have total=w_c*C when C is available, without reweighting.

The experimental whole-session gate exhausts every mandatory-passing candidate.
Unknown C never reaches ComponentScore.contribution or weighted arithmetic. Available
candidates may build an internal incumbent, but any unknown candidate prevents its
publication. Complete coverage failure returns existing InsufficientEvidence with
reason=compatibility_evidence_incomplete, complete=true, no winner, and per-structure
examined/available/unknown/zero/no_pairs counters. Request failures remain separate
stream counters. Scored_count counts numerical scores; accepted_examined includes
all mandatory-passing candidates. Late iteration/interruption/close failures never
return a successful incumbent. Counts after failure are partial; no complete coverage rate is reported.

This safeguard is NOT the final live recommendation policy. It especially blocks
any unconstrained session containing a dress, including wardrobes that also have
fully scored layered dresses. No dresses are removed from live recommendations.

## Synthetic worked examples

| Outfit | Colour mean | Style mean | C |
|---|---:|---:|---:|
| blue classic top + blue classic bottom | 1 | 1 | 1 |
| blue classic top + red sporty bottom | 0 | 0 | 0 |
| blue {classic,vintage} dress + black classic jacket | 1 | 2/3 | 5/6 |
| white classic top + navy classic bottom + red sporty jacket | 2/3 | 1/3 | 1/2 |
| dress alone | NA | NA | Unknown |
| known colours, missing bottom style | 1 | Unknown | Unknown |

With R=1,C=5/6,P=1 the request-led total is 29/30; balanced total is 19/20.
The reproducible weight-sensitivity fixture has blue vintage top, red vintage bottom
(C=1/2,P=3/5), black vintage bottom (C=1,P=0), no request fields. Preferences are
red colour importance 0.6 and classic style importance 0.4. Request-led chooses red
(total 11/50); balanced chooses black (total 3/10). These are synthetic calculations,
not human evaluations. A name such as request_led is a profile identifier, not a
claim that absent request fields were given a positive score.

Unintuitive results: identical named colours can hide different shades; distinct
blue/navy receive no repeated-colour credit; deliberately mixed styles score low;
monochromatic/shared-style combinations can score1 without fitting physical layering,
print scale, user taste or perceived fashion quality. These rules deliberately
measure narrow annotation coordination, not general aesthetic appropriateness.

## File inventory

New production files (seven):
- backend/app/application/recommendation/rule_based_compatibility_policy.py: strict immutable policy/profile loading and hashes.
- backend/app/application/recommendation/config/rule_based_compatibility.v1.json: approved disabled experimental rules.
- backend/app/application/recommendation/config/scoring_policy.rule_based.v1.json: two disabled evaluation profiles.
- backend/app/application/recommendation/rule_based_compatibility_evidence.py: session-local prepared recognized/missing/malformed evidence.
- backend/app/application/recommendation/rule_based_compatibility_scorer.py: intrinsic rule arithmetic, pair/factor diagnostics and Unknown singleton handling.
- backend/app/application/recommendation/rule_based_recommendation_scorer.py: independently verified full-stream experimental ranking and coverage safeguard.
- backend/app/domain/value_objects/rule_based_compatibility.py: frozen prepared annotation value object.

Other new files:
- backend/scripts/evaluate_rule_based_compatibility.py: synthetic examples, coverage, weight sensitivity, exhaustive backend benchmarks and separate tracemalloc passes; refuses source/existing output paths.
- backend/tests/test_rule_based_compatibility.py: truth table, exact arithmetic, fixtures, Phase1 DB filtering, gate tampering, oracle comparisons and failure behavior.
- backend/tests/fixtures/rule_based_experimental_sources.v1.json: exact new application-file hashes.
- docs/RULE_BASED_COMPATIBILITY.md: this contract, verification and decision record.

Modified files:
- backend/tests/integration_source_guard.py: allow only the seven separately hash-pinned new opt-in modules in source-set checks; old source_hash checks and frozen archive checks remain unchanged. No historical archive or existing approval manifest is rewritten.
- docs/RECOMMENDATION_RULES.md: experimental status and link.
- docs/REPORT_TRACEABILITY.md: limited RN-17 evidence, preserved RN18-28 and remaining gaps.

All 157 pre-existing production application Python/JSON files remain byte-identical
to the before-phase SHA256 manifest. No frontend, DB schema, persistence, wardrobe,
CV/VTOFF/VTON, gate or live scoring code is modified.

## Reproduction commands

Run in backend, PowerShell (Python3.12 supplied by uv):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_rule_based_compatibility.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -u scripts/evaluate_rule_based_compatibility.py --sizes 20 50 100 200 --heavy --measure-memory --output ../storage/verification/phase5f2e3a/evaluation.v1.json
```

Use a new output name when reproducing: the evaluator refuses existing artifacts.
Run git diff --check at repository root. Verification results follow below.

## Offline evidence and evaluation interpretation

The 12 deliberately constructed synthetic sessions produce 17 candidate observations.
Coverage: top/bottom5/10, layered top/bottom2/2, dress0/3, dress/outerwear2/2.
The strict gate blocks 8/12 sessions (66.67%). One of 26 garment observations has
unusable colour (3.85%); four have missing/empty/malformed/unrecognized styles
(15.38%). These examples intentionally emphasize failures. Rates are NOT estimates
of actual users' wardrobes, and per-structure denominators differ. Unknown single
relationships are separate from missing annotation rates.

Controlled large synthetic workloads use complete approved annotations, so every
multi-garment candidate has numerical C, but any generated singleton dress still
blocks the whole experimental session. The outerwear-heavy workload has no dresses.
The timing comparison changes the scorer and coverage work, not just one arithmetic
operation. R/P remain unchanged; generic requests have no preferences. Times exclude
DB/HTTP/browser/model processing. Peak memory is incremental Python tracemalloc
allocation of a separate complete pass, excludes input construction, and is not RSS.
One uninstrumented repetition cannot establish median/p95 or a causal speed estimate.
No five-second acceptance or performance improvement is claimed.

## Single-dress decision and route to RN-17

No workaround is implemented. Options requiring separate review:

1. Preserve Unknown and the current live deferred profile. Honest and fair to dresses,
   but RN-17 three-component activation remains incomplete.
2. A constant solo-dress score (0,0.5,1) or vacuous pair mean. This is a scoring-definition
   convention, not measured compatibility, and can favor/penalize a structure. Not recommended.
3. Add current, trustworthy internal visual relationships (e.g. independently reviewed
   internal palette/region/pattern evidence) through coordinated contracts. This could
   support real intra-garment coordination, but current primary-only snapshots cannot
   supply it; stale palette data and uncalibrated hex must not substitute. Needs new
   evidence, validation and teammate approval, not a mandatory new AI model.
4. A separately evaluated unary whole-outfit simplicity/coherence rubric used consistently
   across ALL structures. This changes C's definition and still needs a defensible rule
   and independent examples; garment count or recognized-field completeness is not a
   substitute. No suitable unary formula is currently approved.

The two rules can demonstrate reproducible RN-17 component arithmetic on covered
multi-garment candidates after explicit policy approval; they do not establish
complete RN-17 across the supported wardrobe or fashion-quality accuracy. A more
complex clash matrix is not automatically more defensible. First review real
examples for narrow-policy usefulness, colour recognition coverage and mixed-style
bias. Retain a small model if it is useful; propose extensions only against observed
failures. Resolve single-dress and session-coverage policy before live activation,
then separately approve service profile/wiring/provenance changes, regression tests
and end-to-end latency/quality verification. Homepage remains independent and random;
soft C must not silently become a hard Homepage compatibility threshold.


## Automated verification results

Final focused run: **236 passed, 1 dependency deprecation warning (3.92s)**.
Broad backend run: **991 passed, 1 failed, 1 warning (94.10s)**. The final two
additional focused tests were added afterward and passed in the 236-test run.
The sole broad failure remains test_report_architecture.py:28, which asserts
ai-services does not exist. No folder or assertion was changed. The source-set,
archive hashes and independent historical arithmetic/stream oracle checks passed.
CV test_segmentation_geometry.py was not executed in this environment (cv2/torch).
Live GPU/model quality, deployed PostgreSQL, HTTP/browser acceptance and frontend
builds are not evaluated by this backend-only experimental phase.

Development test history: the first command used the repository cwd with a
backend-relative test path, so no tests ran. The first correct focused run had
223 passed/2 failed due to test assumptions about conflicting snapshots and tuple
candidate keys; these fixtures were corrected without weakening production checks.
Subsequent focused runs passed 230, 234 and finally 236 tests as coverage expanded.

All 157 pre-existing production app files were checked against before.json; none
changed or disappeared. New app files are separately pinned, and existing archive/
source hash validation remains in force. git diff --check passed (exit 0), with
only existing LF/CRLF informational warnings. No historical reference archives or
integration-actions approval manifest was edited.


## Measured backend performance and memory

Timing table uses the separate timing-only repeat after regression processes exited.
The first run overlapped some regression activity; both raw runs are retained.
Memory values use the first run's separate complete tracemalloc passes. No sampling
or truncation was used. Each timing cell is one full pass, not a median/p95.

| Garments / distribution | Candidates | Deferred seconds | Experimental seconds | Deferred peak bytes | Experimental peak bytes |
|---|---:|---:|---:|---:|---:|
| 20 | 198 | 0.017392 | 0.034414 | 161,993 | 176,552 |
| 50 | 2,430 | 0.188869 | 0.357178 | 107,881 | 190,948 |
| 100 | 17,710 | 1.157675 | 3.319963 | 110,091 | 243,022 |
| 200 | 134,820 | 12.574415 | 24.788985 | 113,260 | 347,827 |
| 200 outerwear-heavy | 300,763 | 25.771373 | 57.341236 | 110,100 | 339,013 |

All four ordinary size sessions are blocked by generated single dresses, despite
full annotation of their multi-garment candidates. The heavy session has no dresses
and returns Selected only after all 300,763 candidates have been evaluated.
Added compatibility work increases observed backend time; no optimization or NFR-02
compliance is claimed. Peaks are Python allocations, not total process memory.

Raw reports (generated verification artifacts, not production configuration):
- storage/verification/phase5f2e3a/evaluation.v1.json
- storage/verification/phase5f2e3a/evaluation.timing.v1.json
- storage/verification/phase5f2e3a/before.json: pre-existing application hash comparison.

Timing-only repeat command (same backend cwd/environment):

```powershell
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -u scripts/evaluate_rule_based_compatibility.py --sizes 20 50 100 200 --heavy --output ../storage/verification/phase5f2e3a/evaluation.timing.v1.json
```

**Phase 5F-2E-3A readiness: PASS WITH LIMITATIONS, ready for user review.**
The approved experimental arithmetic/infrastructure/evaluation scope is complete.
No production activation, dress workaround, Phase 5F-2E-3B continuation or further scoring
policy is approved by this status. Full live RN-17 and NFR-02 remain incomplete.
