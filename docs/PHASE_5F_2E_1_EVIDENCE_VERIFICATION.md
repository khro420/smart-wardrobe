# Phase 5F-2E-1 evidence tooling verification

Date: 2026-10-19. Scope: RN-17 evidence schema, validation/import and offline
coverage feasibility ONLY. No compatibility activation, scoring change, default
change, mandatory policy, production application or teammate code modification.

## Changed-file inventory

- `backend/scripts/compatibility_evidence_dataset.py`: strict collection validator,
  isolated import bundle, preserved timestamps/provenance, source split isolation,
  exact review values and descriptive review-quality diagnostics.
- `backend/scripts/audit_compatibility_coverage.py`: exhaustive offline structural
  coverage, unique signatures, per-structure/whole-session analysis, timing/memory
  probes and optional actual captured-wardrobe input. No recommendation scoring.
- `backend/tests/test_compatibility_evidence_dataset.py`: explicitly synthetic
  contract, provenance, leakage, unknown/zero, structure, failure and coverage tests.
- `docs/datasets/compatibility_reviews.schema.v1.json`: versioned JSON Schema.
- `docs/datasets/compatibility_reviews.empty.v1.json`: actual EMPTY collection
  template; no fabricated examples, photos, reviewers or ratings.
- `docs/COMPATIBILITY_EVIDENCE_READINESS.md`: collection blueprint, review protocol,
  contract, reproducibility, feasibility and activation limitations.
- `docs/REPORT_TRACEABILITY.md`: RN-17 evidence stage and preserved boundaries.
- `docs/PHASE_5F_2E_1_EVIDENCE_VERIFICATION.md`: this verification record.

Generated outputs under ignored `storage/verification/phase5f2e1` are experimental
reports, not approved evidence or production configurations. No package manifest
changes: jsonschema is a temporary test dependency for schema consistency checks;
offline CLI tools otherwise use the standard library and existing application.

## Exact commands

From backend, isolated Python 3.12:

```powershell
uv run --no-project --python 3.12 python -B scripts/compatibility_evidence_dataset.py ../docs/datasets/compatibility_reviews.empty.v1.json --output ../storage/verification/phase5f2e1/empty-import.json
uv run --no-project --python 3.12 python -B scripts/audit_compatibility_coverage.py ../docs/datasets/compatibility_reviews.empty.v1.json --sizes 20 50 100 200 --measure-memory --output ../storage/verification/phase5f2e1/coverage.json
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_compatibility_evidence_dataset.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py -q --tb=short
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

At repository root: `git diff --check`.

The first new-fixture run had 37 passes/1 failure because an in-memory tuple was
sent directly to a JSON Schema validator instead of JSON serialization. The
synthetic fixture was corrected. An initial combined test invocation omitted
FastAPI and stopped with two collection errors; rerunning with the existing
backend test dependencies resolved that environment issue. Neither problem
required an application source change.

Focused final result: 93 passed, one existing Starlette TestClient deprecation
warning, 4.02 seconds. Initial broad result before seven additional focused cases:
718 passed, one known architecture assertion failure, same warning, 91.46 seconds.
Final broad run after all changes: **725 passed, 1 failed, 1 warning, 82.11 s**.
The sole failure remains the known architecture assertion described below; no
new regression was observed. This includes original/trial/restored numeric and
historical scoring/stream differential reference tests.

No frontend/browser/build/typecheck rerun is required to substantiate an offline
tooling change; none is claimed. No real CV/VTON or upload-to-recommendation
journey, PostgreSQL deployment, independent human review or fashion-quality
evaluation was executed. Segmentation geometry tests remain excluded for the
previously unavailable CV test dependencies. The known architecture assertion
at test_report_architecture.py:28 requires ai-services to be absent; the existing
directory is preserved and that unrelated assertion is not rewritten.

## Evidence and immutable production boundary

The current approved production-format reference list and new real collection
contain ZERO approved real references. Empty import succeeded, returned
activation_approved=false and dataset hash
`8afe3e9d1d238de272efadcf5089ddfab4494341bfcd146a13b970de9f4427b6`.
No images or individual review ratings were supplied. Exact reviewer agreement,
held-out ranking agreement, real coverage and cross-structure rubric validity
are unmeasured/null. Test-fixture agreement and reviewed-zero cases are synthetic.

All 156 backend/app Python/JSON file names and SHA-256 bytes are checked against
tests/fixtures/performance_reference_2d1/manifest.json. The original score file hash
is `e80f39000e276070fa0ec8d9be04eb455a92a71166dbb5c1d1a8e7fc70d859f1`.
Frozen regression archives remain in place. No live source, reference policy,
weights, feature flags, suitability default, exact arithmetic, ranking, candidate
generation or persistence is changed. Existing live compatibility remains deferred.
Final check: 156 reference files, 156 current files, identical file sets and zero
hash mismatches. `git diff --check` exited 0; the existing history-page LF/CRLF
notice remains. A separate whitespace scan of all eight new/modified files also
found zero trailing-whitespace issues, including untracked files Git does not
check by default.

## Interpretation and outstanding acceptance

Coverage reports are structural candidate audits, not proof of request/compatibility
validity or current real database confirmation. Uniform/varied metadata workloads
are explicitly synthetic; no reference ratings are generated for them. Seen
signatures with different actual garments are counted only when an approved
reference exists. Missing reference is Unknown, not reviewed-zero compatibility.
An empty real collection gives zero such matches, not evidence that signature
generalization works or fails after collection.

The strict whole-session gate is only a reported hypothetical calculation. It
does not exclude candidates or alter the engine. No fallback scoring is activated.
Normal-user gate frequency cannot be estimated without real wardrobe/reference
distributions. Exact-reference lookup remains a bounded prototype option; broader
coverage will likely need separately approved reviewed generalizable rules or a
hybrid. First collect real reviewed reference/validation examples and actual
wardrobes and measure metadata sufficiency and coverage. RN-17 remains partial.
NFR-02 remains open; offline timing is not HTTP response-time acceptance evidence.

## Measured synthetic coverage

Every row below has ZERO covered candidates, 0% candidate/signature coverage,
ZERO seen-signature/different-garment matches and hypothetical gate=false.
All complete signatures are currently unseen by the empty approved lookup.
No candidates were missing metadata in these particular probes; explicit missing/
malformed evidence is covered separately by tests, never removed from denominators.

| Garments/shape | Metadata | Structural candidates | Unique signatures | Baseline seconds | Full audit seconds | Peak traced MiB |
|---|---|---:|---:|---:|---:|---:|
| 20, 8/8/2/2 | uniform | 198 | 4 | .0047 | .0118 | .075 |
| 20, 8/8/2/2 | varied | 198 | 198 | .0034 | .0068 | .048 |
| 50, 20/20/5/5 | uniform | 2,430 | 4 | .0312 | .0787 | .043 |
| 50, 20/20/5/5 | varied | 2,430 | 2,430 | .0300 | .0792 | .719 |
| 100, 40/40/10/10 | uniform | 17,710 | 4 | .2154 | .5951 | .078 |
| 100, 40/40/10/10 | varied | 17,710 | 17,710 | .2521 | .7305 | 6.185 |
| 200, 80/80/20/20 | uniform | 134,820 | 4 | 1.9762 | 5.1882 | .146 |
| 200, 80/80/20/20 | varied | 134,820 | 37,464 | 1.9216 | 5.8566 | 14.135 |
| 200, 67/67/0/66 | uniform | 300,763 | 2 | 4.5045 | 12.8325 | .130 |
| 200, 67/67/0/66 | varied | 300,763 | 75,852 | 4.4932 | 12.3138 | 26.322 |

Role counts are top/bottom/dress/outerwear. The general combination count is
(T*B+D)*(1+O); measured counts are checked against that independent expression.
The additional shape proves the earlier 134,820 count is not a maximum; the tool
does not assert that its new shape is a universal maximum either.

| Garments/shape | Top+bottom | Top+bottom+outerwear | Dress | Dress+outerwear |
|---|---:|---:|---:|---:|
| 20 | 64 | 128 | 2 | 4 |
| 50 | 400 | 2,000 | 5 | 25 |
| 100 | 1,600 | 16,000 | 10 | 100 |
| 200 baseline | 6,400 | 128,000 | 20 | 400 |
| 200 outerwear-heavy | 4,489 | 296,274 | 0 | 0 |

Each represented structure has 0% coverage; absent dress structures in the
outerwear-heavy case have null coverage. Strict hypothetical gate permits 0/10
sessions. This is a result with no real references, not an estimate of ordinary
wardrobe success after evidence collection. Uniform metadata suggests potential
signature reuse but proves no aesthetic equivalence between actual garments.
Varied metadata illustrates the large exact-reference collection burden.

Observed baseline-to-audit deltas at 200 were 3.21/3.93 seconds for baseline
uniform/varied and 8.33/7.82 seconds for outerwear-heavy uniform/varied. They include
signature construction, lookup, set/counter diagnostics and interpreter noise;
do not add them arithmetically to old Assistant latency as a deployment prediction.
Runs are single observations on the development host, not isolated ABBA performance
experiments; a brief focused test run overlapped part of the traced probe period.
No performance acceptance or optimization conclusion is drawn. Traced passes
agree exactly with uninstrumented coverage counts. Memory is incremental Python
allocation peak, not total process memory; the large unique-key sets are audit
diagnostics, not required scorer state.

The raw coverage report records tool hashes. Exact measured tool copies are
preserved under storage/verification/phase5f2e1/measured-tools. After measurement,
the importer was strengthened to retain raw source IDs as well as namespaced
tokens for compatibility with the older evaluator's overlap checks. Empty-dataset
import/coverage behavior is unchanged; the coverage script itself is unchanged.
The strengthened importer was rerun successfully to empty-import-final.json.

```powershell
uv run --no-project --python 3.12 python -B scripts/compatibility_evidence_dataset.py ../docs/datasets/compatibility_reviews.empty.v1.json --output ../storage/verification/phase5f2e1/empty-import-final.json
```

Independent human rating agreement, full ranking agreement, cross-structure score
interpretation and weight sensitivity remain unmeasured. No real reviewed
reference, captured real wardrobe or fashion-quality claim is introduced.

Infrastructure result: **PASS WITH LIMITATIONS, ready for user review**, not
RN-17 completion or final FYP acceptance. Required next evidence: authorized
actual outfit images and snapshots, stable source grouping, independent individual
reviews/adjudication, frozen held-out sources and representative real wardrobes.
Next decision remains reference-only feasibility versus separately approved
generalizable/hybrid design. Do not activate compatibility or proceed to 5F-2E-2.
