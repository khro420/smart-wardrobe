# Phase 3B-3A: owner-declared suitability infrastructure

## Authority and activation boundary

The original Project I report is primary. RN-12/13/15 and sections 4.10.2–4.10.3
require eligibility and mandatory-condition evaluation before scoring; RN-23
prohibits fabricated attributes. Section 4.10.4 separates request, compatibility
and preference scoring. CA-05 limits supported garment categories. The report
does not specify these exact suitability declarations or their aggregation.
They are user-approved implementation policies, not report-established rules.

The capability is explicitly injected, not default behaviour. No Phase 1,
Phase 2, Phase 3A, Phase 3B-1 or Phase 3B-2A contract/source is modified.
No live recommendation, persistence, frontend, Digital Wardrobe, CV, scoring,
ranking or performance algorithm is changed. Approximate hex remains disabled
as mandatory evidence. These declarations are not aesthetic compatibility rules.

```python
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator

# Inject the existing Phase 1 query and a fresh evaluator for EACH session.
engine = RequestCandidateEngine(query, evaluator_factory=SuitabilityRequestEvaluator)
with engine.generate_candidates(user_id, structured_request) as session:
    candidates = list(session)
    # Only complete=True certifies successful stream exhaustion.
    # Apply existing controlled status handling; do not use partial results.
```

Unchanged RequestCandidateEngine(query) still returns PolicyUnavailable for
supplied occasion/formality, even when reserved tags exist. Exercise occasion
and formal formality are PolicyUnavailable even with the opt-in evaluator;
capability checking occurs before garment retrieval. There is no activation
switch in live composition wiring.

## Versioned annotation grammar

config/suitability_policy.v1.json declares owner-declarations-1.0.0 and
default_activation false. Enabled occasions: campus, work, casual_outing,
shopping, dinner, party, date, travel. Enabled formality: casual, smart_casual.
Values and disabled capabilities are validated against exactly the approved
policy. Frozen policy objects normalize collection inputs to immutable tuples.

Existing custom_tags strings use exact, lowercase tokens:

```text
rec:v1:occasion:campus:allow
rec:v1:occasion:work:deny
rec:v1:formality:casual:allow
rec:v1:formality:smart_casual:allow
```

Only this reserved grammar supplies suitability evidence. Ordinary tags such
as campus, office, casual, formal, sporty or occasion:campus:allow have no
reserved meaning. No style/category/fit/material/colour is converted into
suitability. No occasion propagation or formality hierarchy exists. One garment
can explicitly allow several values without implying any unlisted value.
The existing review limit of 20 text values (100 characters each) still applies;
ordinary tags share this budget with declarations.

## Evidence and aggregation

SuitabilityEvidenceParser reads only immutable snapshots from the Phase 1
contract and caches parsed evidence by garment ID for one session. Conflicting
snapshots sharing an ID raise an error rather than reusing stale evidence.
GarmentSuitabilityEvidence and SuitabilityDeclaration are frozen; nested caller
lists are copied to tuples. Diagnostics retain Missing/Empty/Parsed/Malformed
collection states and malformed dimensions.

| Evidence for requested enabled value | Garment condition |
|---|---|
| Valid allow only | Pass |
| Valid deny only | Fail |
| Allow and deny together | Unknown |
| Missing, empty, or no annotation for that value | Unknown |
| Phase 1 flags custom_tags malformed | Unknown; do not recover from a mirror |
| Malformed reserved tag affecting the dimension | Unknown; no partial positive evidence |

Malformed reserved records taint the named dimension; if the dimension cannot
be identified, both dimensions are tainted. This includes unknown versions,
unknown values/decisions, unsupported value annotations and case/grammar errors.
For example malformed occasion records do not invalidate an independent valid
formality declaration. Conflicting allow/deny is scoped to its exact value.
An unsupported-value tag cannot enable that request capability.

Every worn garment, including optional outerwear, is evaluated. Any definite
Fail wins; otherwise any Unknown gives Unknown; all Pass is required for Pass.
Missing outerwear evidence prevents only the layered candidate from passing;
the separately generated unlayered candidate can still qualify. Garments are
not discarded globally just because an unrelated optional annotation is absent.
Condition evidence_ids identify constituents contributing the condition's final
state (allow, deny or unknown), not uniformly positive evidence.

SuitabilityRequestEvaluator projects an internal copy of the immutable request
without occasion/formality solely for the existing minimum evaluator. It then
appends independently evaluated supplied suitability conditions. The original
request and NLP semantics are unchanged; no supplied condition is ignored.
Phase 3B-1 collective categories, global primary colours and base-style evidence
retain their original evaluation. The existing session colour/style cache metric
is unchanged; suitability cache size is available on evaluator.parser.cache_size.

At candidate level, any field Fail dominates Unknown. Stream outcomes remain:
MatchingCandidates only after exhaustive completion with at least one passing
candidate; InsufficientEvidence if no candidate passes and some are Unknown;
NoMatchingCandidates if all definitely fail. Structural-empty outcomes remain
distinct. Failure/interruption leaves complete false, including failure after
emitting a passing candidate. No invalid fallback or truncation is introduced.

## Meaning and limitations of suitability

Allow means the owner declares the garment suitable for inclusion in an outfit
under the named ordinary context. It does not independently establish social
appropriateness, venue dress codes, comfort, safety or activity performance.
Work does not imply formal. Sporty does not imply exercise suitability.
The five-field request cannot specify every venue or activity context.

Declarations can become stale after category, interpretation or garment changes.
There is no dedicated review provenance, timestamp or invalidation mechanism.
No provenance is invented from mere confirmation. Review/reassessment remains a
manual coordination responsibility. These are minimum declaration-based rules,
not a claim of full RN-28 validity. Different style tags can coexist; aesthetic
compatibility remains separate. Future Phase 4 scores cannot rescue missing or
denied mandatory conditions. Two passing outfits may have identical suitability
contributions without inventing confidence scores.

## Verified tag lifecycle and existing frontend blocker

tests/test_suitability_tag_workflow.py uses the actual API/services and isolated
test persistence with development garment processing. It verifies exact tokens
through valid review payload -> processing attributes -> accepted/confirmed
record -> garment JSON/dedicated custom_tags -> wardrobe update -> API retrieval
-> a fresh Phase 1 query/snapshot. It does not claim trained-CV or browser E2E
coverage. Eligibility integration excludes accepted/pending/rejected records,
NULL/dangling processing links, archived records, foreign garments and foreign
processing-job provenance. No saved outfits are required or created.

The current frontend extract/results/page.tsx submits neckline and sleeve_length
inside attributes on accepted reviews, even when values are null. ReviewItem's
allowlist excludes both keys. Reproduced API tests for top and bottom categories
return 422; subsequent confirmation of the still-unaccepted item returns 409.
Removing only those unsupported keys makes review and confirmation succeed.
This is an EXISTING blocker in the normal frontend accept/confirm path, not a
failure of backend tag persistence. The extraction screen also constructs
custom_tags from silhouette/neckline/sleeve details rather than offering reserved
suitability controls. Existing arbitrary annotations should not be assumed to
survive another UI review that rebuilds this list.

Teammate coordination: agree whether to remove the two unsupported payload keys
or deliberately support them through validated contracts and persistence.
The redundant derived custom tags must also be considered. No such teammate
files are changed here. Existing wardrobe editing has a comma-separated Tags
input, whose reserved tokens contain no commas; backend editing preservation is
tested. No browser interaction or new UI controls were implemented.

Manual technical tag entry is NOT an acceptable final user experience. A future
friendly occasion/formality selector, merging/preserving ordinary tags, review
guidance and stale-declaration handling require separate frontend approval and
Digital Wardrobe coordination. The present backend infrastructure is usable
through valid APIs, not presented as a complete user-facing feature.

## Tests and evaluation boundary

tests/test_suitability_policy.py covers enabled values, all four structures,
outerwear, unknown/conflicting/malformed evidence, no hierarchy or inference,
failure precedence, deterministic order, immutable evidence, unavailable values,
five-field NLP input and preservation of the default evaluator/colour rules.
Stream tests include close, query/parser errors, KeyboardInterrupt and failure
after an emitted candidate. The existing regression suites remain required.

fixtures/suitability_evaluation.v1.json contains 16 fixed SYNTHETIC executable
policy expectations, assessed by test_suitability_evaluation.py. They are not
independent garment appropriateness labels, user evaluation or accuracy claims.
No real-world suitability precision, coverage or reviewer agreement is asserted.
Independent garment review and a usable annotation workflow remain future work;
no numerical quality threshold is invented from RN-27 or the report.

## Executed verification (2026-10-15)

Commands run from backend, using isolated test persistence and development AI:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Final focused result: **66 passed**, one Starlette TestClient deprecation warning,
4.49s. The 16 fixed synthetic scenario expectations all passed; this is not
real-world appropriateness accuracy. Final backend regression: **365 passed,
1 failed**, same warning, 19.10s. Remaining failure is the pre-existing
test_report_architecture.py:28 assertion that ai-services must be absent.
No folders were deleted/restructured. An initial combined run additionally
exposed a new test fixture sharing a dangling processing ID with an older test;
the new fixture now uses a UUID and the full rerun resolves that collision.
No production change was required.

`git diff --check` passed from the repository root. New untracked files also
received a separate trailing-whitespace check. Frontend browser E2E, real CV
inference, independent appropriateness evaluation and performance benchmarking
were not executed; they are outside this opt-in infrastructure verification.
The existing frontend blocker is explicitly reproduced by tests, not fixed.
