# Phase 5F-2E-3C-2: explicit compatibility decision policy

Date: 2026-10-20. Isolated experimental implementation and offline verification.
No production activation, migration, default change or historical rewrite.

## Sources and approval boundary

Original report, PDF pages 188-189 (printed 177-178): RN-17 requires documented
three-component scoring; RN-18-21 require ranking, highest valid selection,
deterministic ties and exactly one result. Sections 4.4.3 and 4.10.4 (PDF pages
232, 285-288) separate generation, mandatory rules, scoring and ranking; only valid
candidates may be scored. The report establishes S=w_r R+w_c C+w_p P and consistent
normalisation, not the numerical weights or missing-evidence conventions below.
See FYP_CONTEXT.md sections 6.1-6.4 and the completed garment, NLP, structural,
request-evaluation, suitability, colour and scoring contracts.

Phase 3B/3C-2 user approval supplies these NEW experimental conventions: exact
possible-value bounds, midpoint decisions, a separate 1/2 no-pair reference and
fixed 0.60/0.20/0.20 weights. They are not report-defined measurements or proven
fairness. Phase 3A rules and both prior uncached/cached implementations remain
unchanged and executable. This document supersedes their session-coverage refusal
only for this explicitly selected new policy, not for the old scorers or live UI.

## Exact policy

Enabled atomic outputs are the unchanged colour rule (same recognized primary
colour or a recognized achromatic member gives 1, otherwise 0) and style Dice.
Unknown attributes produce unresolved outputs; they never become observations.
For M atomic outputs, K=sum(known outputs) and m=unresolved count:

    L = K/M
    U = (K+m)/M
    C_decision = (L+U)/2
    S = (3/5)R + (1/5)C_decision + (1/5)P

These are exact Fractions and deterministic possible-value bounds, not confidence
intervals or probabilities. With all evidence, L=U=measured C. With none, raw C
stays Unknown, bounds are [0,1] and the fully conventional decision is 1/2.
Partially unresolved candidates have a PartiallyConventional basis and retain
all atomic values, reasons, observed/possible counts and original rule-policy
version/hash. A measured zero remains Available with value 0.

Single dresses retain exactly one one_piece garment, zero pairs and zero atomic
outputs. New raw pairwise status is NotApplicable (the old scorer's two factors
were already NA; its summary Unknown remains unchanged in the old implementation).
There are no artificial atoms or interval bounds. Decision basis NoPairReference
records 1/2 separately; this is not evidence of internal dress quality.

For top/bottom, dress/outerwear and top/bottom/outerwear, M is respectively 2,2,6.
Optional outerwear participates in all genuine unordered garment pairs. No garment
count bonus, normalization by annotation coverage or additional tie-breaker exists.

## Narrow versioned adapter and preserved contracts

Existing ComponentScore.contribution returns zero for a None raw value;
RecommendationScore validates total from those contributions; CandidateRanker
uses those same contributions. Putting a midpoint into summary.value would
falsely change raw evidence to Available. Editing these contracts would also
change historical/live behavior, so neither approach is used.

CompatibilityDecision is a separate frozen object containing raw ComponentScore,
structure, basis, exact decision/bounds/K/counts, pair count and decision-policy
identity. DecisionCompatibilityComponent is an explicitly named frozen ComponentScore
subtype tagged compatibility-decision-component-1.0.0. Its summary/details must
exactly equal decision.raw; only its contribution property supplies the explicit
recorded decision value. Base ComponentScore, RecommendationScore, ScoredCandidate,
RankingOutcome and CandidateRanker source and invariants remain unchanged. Existing
validators run normally and the ranker compares total -> R -> decision -> P ->
stable key. No unchecked constructors, provisional winners or coverage tie-breaker.
The adapter is never implicitly constructed from a legacy score payload.

Versioned JSON configuration has default_activation=false and is checked against
the exact approved schema/policy; activation, alternative weights or other rules
are rejected. An explicit DecisionRecommendationScorer is the only new orchestration
entry point. A fresh gate, R/P scorers and compatibility scorer belong to each
rank call. It has no service composition registration, route, flag or live default.

## Cache, eligibility and stream guarantees

The retained 19,900-entry bounded session-local pair cache is reused unchanged.
It stores only exact atomic colour/style outputs, never midpoint decisions. The
existing immutable snapshot/evidence, owner, gate-context and rule-policy checks
remain in force. Decision configuration is fixed/validated once per rank call;
a decision is derived anew with that policy identity. No decision-cache key omits
policy context because there is no decision cache. Eviction recomputes exactly.
An explicit cached=False mode uses the unchanged uncached rule scorer as oracle.

Phase 1 query, structural generation, mandatory Pass/Fail/Unknown semantics and
fresh independent scoring verification remain unchanged. Unknown mandatory colour
or suitability evidence is not rescued by a conventional compatibility contribution.
All mandatory-valid candidates are scored, including dresses and incomplete C.
Full successful exhaustion and close are required before one winner is returned.
Late errors/interruption invalidate the whole selection and retain partial counts.
No candidate collection is materialized or truncated by the new coordinator.

Diagnostics separate raw Unknown from raw NotApplicable and count Computed,
PartiallyConventional, FullyConventional and NoPairReference contributions, plus
atomic known/possible totals and structure coverage. No evidence state is silently
changed to zero to satisfy arithmetic.

## Persistence and exact offline replay

No production schema, repository or live writer/reader was changed. Existing
SqliteRecommendationRepository writes compatibility_score from summary.value:
measured 0 remains SQL 0; Unknown and NA remain SQL NULL. Its existing generic
score_json serializer includes the named adapter's raw evidence AND separate
decision (exact numerator/denominator, bounds, coverage, basis, structure, policy
version/hash). The experimental provenance also identifies the decision profile.

The new explicit decision_score_codec rejects absent/legacy adapter tags, invalid
fractions, mismatched policy/profile identity, inconsistent raw versus decision
metadata and invalid totals. It reconstructs the frozen adapter, invokes existing
RecommendationScore validation and exactly replays S. It never coerces NULL to
zero or infers a midpoint from a legacy row. SQL REAL columns are approximate
display values and are not authoritative for rational replay. Metadata can be
replayed as an audit of recorded arithmetic, not as proof of current eligibility
or cryptographic authenticity. Future live readers must deliberately recognize
the adapter before showing decision and raw evidence separately; old consumers
must not reconstruct a total from nullable display columns.

Five disposable SQLite cases cover complete, measured-zero, partially missing,
entirely missing and single-dress scores using the unchanged real repository.
Only disposable data is written. No deployment DB or historical record is touched.
Live persistence/consumer activation requires a separately approved integration.

## Synthetic demonstrations and limitations

The evaluation script uses fixed SYNTHETIC garments, no reference photographs,
reviewers, labels or independent fashion-quality judgments. A generic request
with NoPreferences contributes R=0 and P=0 under the unchanged Phase 4A semantics:

| Example | Raw C | Bounds | Decision basis/value | Total |
|---|---|---|---|---|
| Same blue/classic top + bottom | 1 | [1,1] | Computed 1 | 1/5 |
| Blue/classic top + red/sporty bottom | 0 | [0,0] | Computed 0 | 0 |
| Single dress | NA | none | NoPairReference 1/2 | 1/10 |
| Blue/classic dress + white/classic outerwear | 1 | [1,1] | Computed 1 | 1/5 |
| Blue/classic top + red/sporty bottom + white/classic outerwear | 1/2 | [1/2,1/2] | Computed 1/2 | 1/10 |
| Remove top style from blue/red zero example | Unknown | [0,1/2] | PartiallyConventional 1/4 | 1/20 |
| One missing primary, matching known styles | Unknown | [1/2,1] | PartiallyConventional 3/4 | 3/20 |
| Both garments lack colour and style | Unknown | [0,1] | FullyConventional 1/2 | 1/10 |

The dress beats the measured-zero combination and loses to measured-one. A
measured 1/2 and the no-pair 1/2 tie without any coverage preference; stable key
resolves a complete numerical tie. Changing request/preferences can change R/P
and total while intrinsic compatibility stays identical.

Removing a known low observation can RAISE a midpoint. This is a documented
missingness sensitivity, not a quality improvement or a neutral fairness proof.
The identical/achromatic colour rule assigns blue/red 0 even if a human might
like that combination; no positive human judgment is fabricated here. The narrow
heuristic has no independent fashion-accuracy estimate. Approved midpoint/no-pair
conventions require user evaluation before activation. Suitability stays opt-in,
approximate hex stays disabled and no pattern or new harmony rule is added.

## File inventory

New application/config files (five):
- backend/app/domain/value_objects/compatibility_decision.py
- backend/app/application/recommendation/compatibility_decision_policy.py
- backend/app/application/recommendation/decision_recommendation_scorer.py
- backend/app/application/recommendation/decision_score_codec.py
- backend/app/application/recommendation/config/compatibility_decision.v1.json

New verification/documentation files:
- backend/tests/test_compatibility_decision.py: arithmetic, all structures, state
  distinctions, exact replay, actual disposable SQLite, mandatory tampering,
  deterministic ties, annotation removal, concurrent sessions and stream failures.
- backend/tests/fixtures/compatibility_decision_sources.v1.json: separate new pins.
- backend/scripts/evaluate_compatibility_decision.py: reproducible synthetic examples.
- backend/scripts/benchmark_compatibility_decision.py: paired cached baseline/new
  policy full-pipeline timing, result/coverage/cache data and fresh-process RSS.
- docs/COMPATIBILITY_DECISION_POLICY.md: this contract and verification record.

Modified support files:
- backend/tests/integration_source_guard.py: recognize only separately pinned new
  files, retaining all previous baseline, authorized-source and archive checks.
- docs/RECOMMENDATION_RULES.md: explicit policy status/link.
- docs/REPORT_TRACEABILITY.md: requirement evidence and unresolved acceptance gates.

Generated ignored artifacts live in storage/verification/phase5f2e3c2. They are
not production configuration. The before.json manifest covers 172 pre-phase
entries: 167 application files/configs (157 original + seven Phase 3A + three
cache files) and five frozen app archives. No old pin or archive is rewritten.

## Reproduction commands

Run from backend in PowerShell; the uv environment is isolated, without dependency
or project-default changes. Model execution remains outside this experiment.

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_compatibility_decision.py tests/test_compatibility_pair_cache.py tests/test_rule_based_compatibility.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/evaluate_compatibility_decision.py --output ../storage/verification/phase5f2e3c2/examples.v1.json
uv run --no-project --python 3.12 python -B -u scripts/benchmark_compatibility_decision.py --sizes 20 50 100 200 --heavy --pairs 2 --memory --output ../storage/verification/phase5f2e3c2/paired.v2.json
```

Use a new artifact filename when reproducing; tools refuse existing/source output.
Run git diff --check at repository root.

## Benchmark interpretation

Both arms use the retained cache. Raw report keys uncached/cached are inherited
from shared tooling and explicitly mapped in arm_labels: uncached means cached
Phase 3A baseline; cached means cached new decision policy. They do NOT denote
cache-disabled execution in this comparison. The new policy's separate uncached
correctness oracle is covered by differential tests, not this performance table.

Two alternating matched pairs per workload (baseline/new then new/baseline), plus
one fresh-process RSS pass per arm/workload. GC collection occurs outside timing;
normal GC stays enabled. The request has no fields/preferences. Complete backend
retrieval/generation/mandatory/gate/R/P/C/ranking is timed, excluding SQL/HTTP/browser.
Normal baselines refuse selection due to dresses, while the new policy scores
those dresses and selects after complete enumeration. All multi-piece evidence is
known in these synthetic performance workloads. This is additional functionality,
not a behavior-equivalent speed benchmark or a claim of improved latency.

Fingerprints are stable separately for each policy and its memory pass; differences
between old and new are expected. They include status, completeness, count,
diagnostics, winning key and complete score/evidence. Candidate counts and all cache
counters are asserted exactly. The full snapshot/user/request comparisons are in
the differential suite. Exact winner metadata size is recorded per arm to expose
extra provenance allocation. Memory uses Windows peak working-set RSS in separate
complete processes, including interpreter/imports/inputs, not tracemalloc.

Host is the same Windows 11 Ryzen 5 7235HS / Python 3.12.10 environment as 3C-1;
script/config/source hashes are recorded. No broad regression test runs alongside
the timing suite. A brief report-PDF read overlapped its initial portion; host
background scheduling and power/thermal state are not independently controlled.
Two pairs are descriptive measurements, not statistical significance or p95.

Final measured results, tests and source-integrity checks follow after completion.


## Final offline results

Completed artifacts: paired.v2.json and examples.v1.json in
storage/verification/phase5f2e3c2. The initial smoke and incomplete paired.v1.json
are retained as development records, not final measurements. The first timing
attempt was stopped after separating NA/Unknown diagnostics and strengthening
no-pair validation; v2 reran all sizes with the final application hashes.

All ten matched pairs (20 timing arms), plus ten fresh-process memory passes,
completed. Each policy's fingerprints repeat exactly across timing/memory passes.
All five final benchmark source/config sets match the current measured files;
the complete raw report records individual scores, diagnostics and fingerprints.
Different baseline/new fingerprints are expected because their policies differ.

| Garments | Candidates | Cached baseline median seconds (range) | Decision median seconds (range) | Median paired overhead |
|---|---:|---:|---:|---:|
| 20 | 198 | 0.041305 (0.038238-0.044371) | 0.059164 (0.053433-0.064896) | 42.997% |
| 50 | 2,430 | 0.461013 (0.447132-0.474893) | 0.662865 (0.651168-0.674563) | 43.992% |
| 100 | 17,710 | 3.191576 (2.833812-3.549340) | 4.313507 (4.090400-4.536613) | 36.079% |
| 200 | 134,820 | 21.542519 (21.440925-21.644114) | 32.050583 (31.446357-32.654810) | 48.795% |
| 200 heavy | 300,763 | 49.670226 (48.391397-50.949055) | 69.922672 (69.750849-70.094496) | 40.858% |

Overhead = median(100*(decision_i-baseline_i)/baseline_i). It is not the ratio
of separate medians. Every new-policy timing arm is slower. This is an honestly
reported functionality/validation cost, not a retained performance optimization.
No arbitrary candidate cap or score validation shortcut was introduced.

| Garments | Pair visits | Unique pairs / misses | Hits | Evictions | Baseline / decision peak RSS bytes |
|---|---:|---:|---:|---:|---:|
| 20 | 452 | 100 | 352 | 0 | 26,017,792 / 26,173,440 |
| 50 | 6,425 | 625 | 5,800 | 0 | 26,492,928 / 27,324,416 |
| 100 | 49,700 | 2,500 | 47,200 | 0 | 28,217,344 / 29,270,016 |
| 200 | 390,800 | 10,000 | 380,800 | 0 | 36,724,736 / 37,502,976 |
| 200 heavy | 893,311 | 13,333 | 879,978 | 0 | 41,070,592 / 41,082,880 |

Both arms have identical cache counters and retain all candidates. Unique-pair
counts are derived independently from wardrobe composition and verified by misses
(no eviction in these workloads). Cache high-water equals unique pairs. Eviction
and capacity-zero correctness are exercised separately in differential tests.
RSS is one fresh-process measurement per arm/workload, not a memory distribution
or universal ceiling; per-process startup variation explains small differences.

| Garments | Computed decisions | Partial / fully conventional | No-pair references | Known / possible atomic outputs |
|---|---:|---:|---:|---:|
| 20 | 196 | 0 / 0 | 2 | 904 / 904 |
| 50 | 2425 | 0 / 0 | 5 | 12850 / 12850 |
| 100 | 17700 | 0 / 0 | 10 | 99400 / 99400 |
| 200 | 134800 | 0 / 0 | 20 | 781600 / 781600 |
| 200 heavy | 300763 | 0 / 0 | 0 | 1786622 / 1786622 |

All atomic evidence in these performance fixtures is known. Atomic coverage is
100% of applicable outputs; this excludes the NA dresses and does not mean every
outfit has measured compatibility. Baseline numerically scores N-D and returns
InsufficientEvidence for each ordinary workload; new policy scores N and returns
Selected. Heavy baseline and new both score all 300,763 and return Selected.
The 12 independent SYNTHETIC example cases instead include 16 candidate occurrences:
8 Computed, 3 PartiallyConventional, 1 FullyConventional, 4 NoPairReference;
23/28 applicable atomic outputs known (82.14%). These are demonstration counts,
not real-world coverage or a held-out quality dataset.

Winner metadata JSON is 3,989 bytes for each new ordinary-workload winner. Those
baseline outcomes have no published winner (reported output payload size 0, which
does NOT mean no score objects were constructed). In the heavy case, baseline
winner metadata is 1,878 bytes and the new decision metadata 3,712 bytes. Exact
metadata includes duplicated raw evidence in the named adapter and decision for
explicit auditability; no production writes occur during these benchmarks.

Each scored candidate adds one bounds/decision construction and validation plus
one adapter validation, while retaining original score validation and verification.
Atomic scanning, exact bound arithmetic and metadata/result construction add work
on top of the retained pair cache. Runtime measurements isolate their combined
policy overhead, not the separate causal cost of each instruction or allocation.
No new per-instruction profiler claim is made. Only the incumbent survives between
iterations; full provenance JSON is serialized only for returned winners in the
tool, outside the measured rank call. Candidate metadata is not all materialized.

The actual examples confirm all four structures can win: top_bottom, dress,
dress_outerwear and top_bottom_outerwear. The changed-request/preferences fixture
has R=1/2, raw C=decision=0, P=1/2 and S=2/5; its original generic version has
R=P=0 and S=0 with identical intrinsic compatibility. All 12 examples replay exactly.

## Acceptance recommendation

This phase establishes isolated arithmetic, evidence/provenance and streaming
infrastructure, not independent fashion-quality acceptance. Academic RN-17 limits
remain: narrow colour/Dice heuristics, no reviewed fashion-accuracy evidence,
midpoint missingness sensitivity, convention-based dress treatment and incomplete
live three-component integration. Evidence completeness is not fashion quality.
The 200-garment decision medians are 32.05s and 69.92s before HTTP/SQL/browser;
NFR-02's eventual five-second full response requirement remains unresolved and
new policy overhead worsens that risk. No end-to-end compliance is claimed.

Recommend review/closure of this isolated phase with limitations, but NOT live
activation. A separately approved phase must review consumer presentation/replay,
provenance safeguards, policy usefulness and annotation-removal sensitivity,
performance feasibility and end-to-end security/regressions. Current Homepage,
Assistant deferred scoring, feature flags, histories and all teammate algorithms
remain unchanged. Phase 3C-3 has not begun.


## Final automated verification

- Focused exact command above: 586 passed, 1 existing dependency deprecation
  warning, 17.67s, exit 0. This includes 95 new tests plus 491 unchanged cache/rule
  tests. Initial implementation runs passed 82 and then 576 tests as coverage grew.
- Broad exact command above: 1,343 passed, 1 failed, 1 existing warning, 108.77s,
  exit 1. Sole failure: tests/test_report_architecture.py:28,
  ReportArchitectureTests.test_single_backend_and_canonical_ml_locations,
  assertFalse((ROOT / "ai-services").exists()). No folder/test was deleted or weakened.
- The warning is the existing FastAPI/Starlette TestClient httpx deprecation.
- Explicitly excluded: tests/test_segmentation_geometry.py (cv2/torch environment
  not provisioned here). Frontend/browser, GPU/live models, deployed PostgreSQL
  and end-to-end HTTP acceptance were not executed in this isolated backend phase.
- Synthetic evaluation script completed all 12 fixed examples and exact replay.
  Its first attempt used an invalid preference fixture shape (array instead of
  the existing {"values":[...]} object); correcting that tooling fixture required
  no application/scoring change. An initial import smoke used the repository cwd
  instead of backend and failed to locate app; corrected test commands are above.
- Original 157 application files, seven Phase 3A additions, three cache files and
  five frozen archives: zero SHA mismatches across the 172 pre-phase entries.
  New five application/config files are separately pinned; no old pins changed.
  All 11 final benchmark source/config hashes and the example-script hash match.
- git diff --check passed (exit 0), with existing LF/CRLF notices for untouched
  recommendation_service.py and frontend/app/history/page.tsx. A separate scan of
  all 13 phase files, including new/untracked files, found no trailing whitespace.

Overall: PASS WITH LIMITATIONS for isolated implementation/offline verification.
No production activation or Phase 5F-2E-3C-3 work was performed. Await user review.
