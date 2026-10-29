# Phase 2: independent English NLP interpretation

## Authority and boundary

Primary design: Chong Wei Ping's original Project I report, RN-01–RN-10,
RN-27–RN-30, FR-OA-05/09/11, CA-07/08/10 and NFR-10/12/20/22. Class
decomposition follows section 4.4.4 (printed pp.223–224); interpretation follows
4.10.1 (pp.266–268) and validation follows 4.11.3 (pp.287–289).

The user approved deterministic rules, English-only scope and the vocabulary
below after report review. These are implementation decisions, not enums
mandated by the report. No trained model, LLM service or new runtime dependency
is used. The six classes are RequestPreprocessor, IntentClassifier,
RequestFieldExtractor, ControlledValueMapper, StructuredRequestBuilder and
NLPInterpreter. Vocabulary loading is a supporting configuration component.

There is deliberately no API route, frontend, database, garment-query,
recommendation engine or chat-history integration. Existing application behavior
and the closed Phase 1 contract are unchanged. NLPInterpreter.interpret(text)
is the internal entry point; the module can be evaluated without FastAPI.

## Input, output and meaning

Text must be a nonempty string of at most 500 original characters, matching the
existing request limit. Original text is retained verbatim. A separate copy uses
NFKC Unicode normalization, case folding, whitespace normalization, apostrophe
normalization and hyphen/underscore-to-space normalization. Punctuation and
negation are not erased before interpretation. Evidence spans refer to this
normalized copy, not offsets in the original text.

StructuredOutfitRequest contains intent plus exactly five optional fields:
occasion, style, colours, garment_categories and formality. Absent values are
None. Colours and category constraints are immutable tuples; JSON serialization
uses arrays. Singular fields reject conflicting values. Repeated equivalent
values are deduplicated. Constructors validate/detach mutable collection inputs.

Category constraints have kind='category' or kind='group' and a canonical value.
This is the approved representation inside garment_categories, not a new NLP
attribute. Groups express membership requirements, not requests for every member.
The interpreter does not compute whether garments satisfy them.

NLPOutcome statuses are Supported, InvalidInput, UnsupportedRequest and
ProcessingError. Only Supported carries a StructuredOutfitRequest. Unsupported
reason codes include unsupported_intent, negation, alternatives,
multiple_requests, conflicting_occasion/style/formality,
garment_colour_binding and unrecognized_condition. No clarification dialogue or
multi-turn memory exists. Processing errors expose no exception/secret details.
An unexpected failure is logged without submitted text or stack details.

## Approved vocabulary v1.0.0

The exhaustive machine-readable alias definitions are in
backend/app/application/nlp/config/vocabulary.v1.json. Changes require explicit
review, versioning and reevaluation; arbitrary free-text garment tags do not
extend this vocabulary automatically.

| Field | Canonical values |
| --- | --- |
| Occasion | campus, work, casual_outing, shopping, dinner, party, date, travel, exercise |
| Style | casual, classic, formal, minimal, smart casual, sporty, streetwear, vintage, bohemian |
| Colour | black, white, grey, navy, blue, red, green, yellow, orange, pink, purple, brown, beige, cream |
| Formality | casual, smart_casual, formal |
| Category | Existing thirteen GARMENT_STRUCTURE IDs; canonical outwear spelling is retained |
| Category group | top, bottom, dress, outerwear |

| Canonical occasion | Aliases |
| --- | --- |
| campus | campus, university, college, class, classes, lecture, lectures |
| work | work, office |
| casual_outing | casual outing, going out casually |
| shopping | shopping, shopping trip |
| dinner | dinner, dinner outing |
| party | party |
| date | date, date night |
| travel | travel, travelling, traveling, trip |
| exercise | exercise, workout, working out, gym |

Style phrases: casual style/look, classic style/look, formal style/look,
minimal/minimalist/minimalist style, smart casual style/look, sporty/sporty
style/athletic look, streetwear/streetwear style, vintage/vintage style and
bohemian/boho/boho style. Grey accepts gray; navy accepts navy blue. Other colour
names match themselves. Longer overlapping phrases win.

Formality accepts casual outfit/clothes or casually dressed; smart casual
outfit/clothes; formal outfit/clothes or formally dressed. Hyphenated expressions
normalize to the same aliases. Casual/formal/smart-casual style/look goes to
style only, while outfit/clothes goes to formality only. Bare overlapping words
are unsupported. Separate phrases may explicitly populate both fields.
Occasion alone never infers formality/style.

Specific category aliases use short/long sleeve or sleeved top/outerwear/dress,
vest, sling top, shorts, trousers/pants, skirt, vest dress and sling dress.
General top/tops, bottom/bottoms, dress/dresses and outerwear retain group kind:

| Group | Existing member IDs |
| --- | --- |
| top | short_sleeve_top, long_sleeve_top, vest, sling |
| bottom | shorts, trousers, skirt |
| dress | short_sleeve_dress, long_sleeve_dress, vest_dress, sling_dress |
| outerwear | short_sleeve_outwear, long_sleeve_outwear |

Shirt, jacket, jeans, tank top, neutral colour groups, light/dark/pastel modifiers,
hex-to-name classification and unsupported occasion/formality terms are not
silently mapped. Weather, fit, material, gender and season are not request fields.

## Conservative language coverage

Supported intent uses bounded suggest/recommend/give me/show me/help me choose
or pick patterns mentioning outfit/clothes/clothing/look/something, or what
should/can I wear. Clothing words alone are insufficient. Shopping as an occasion
is distinct from buy/purchase intent. Unknown non-grammar words cause unsupported
outcomes rather than silently dropping a possible condition. English-only is a
bounded English grammar, not an external language classifier.

Negation and alternatives are unsupported, never positive requirements. Explicit
unknown conditions and conflicts are rejected. Generic supported requests with
missing fields proceed without defaults. A controlled unsupported result does
not mean an eligible request has no valid outfit.

The approved five-field schema cannot bind a colour to a particular garment.
Requests such as 'blue top and black trousers', 'top in red', and 'blue colours
for a top' therefore return UnsupportedRequest with no partial structured output.
No binding schema extension is introduced. Combined categories/global colours
are accepted only in the bounded, explicitly global form:

```text
Suggest an outfit using blue and black colours with a top and trousers.
```

All extracted colours must be in that using-colours clause, all categories must
follow its with marker, and any detected local binding rejects the request.
Other combined phrasing may be conservatively unsupported. This grammar is a
documented limitation, not a claim of unrestricted semantic understanding.

## Evaluation and leakage controls

RN-27 says: 'at least 80% correct intent classification and request-field
extraction across the fixed labelled evaluation dataset.' Approved measurement:
intent accuracy >=80% and five-field accuracy >=80% on labelled supported
requests. Combined exact-match accuracy is reported without an extra threshold.

tests/fixtures/nlp_evaluation.v1.json has 120 author-labelled synthetic examples:
40 detailed, 30 partial, 30 unsupported and 20 supported no-feasible-outfit
scenarios. It was frozen before first interpreter execution with SHA-256
ced6418193e866649b635c6671ff2a1387becbd0435eb9eb0dc3a04a439760ba.
The evaluator rejects changed labels. Rules were refined with separate
development examples/unit cases; no rule changes were made after the first
fixed-set results to improve those results. Evaluation integrity tests inspect
the frozen resource solely to verify dataset/metric behavior.

Labels were written directly, not inferred from predictions. Nevertheless, the
same implementing agent authored rules and synthetic cases against the approved
vocabulary. This is a scope-conformance benchmark, not independently authored
or collected held-out user data. Similar grammar and vocabulary necessarily
overlap. Perfect scores do not establish real-world language generalization.

Metrics:

- Intent: correct expected status /120; confusion matrix is included.
- Fields: exact canonical value/set for each of five fields across 90 supported
  cases (450 decisions). Failed interpretation makes all five incorrect.
- Explicit fields: exact match on 130 non-null expected fields; absent fields
  cannot inflate this metric.
- Per-field precision/recall/F1: micro counts of canonical values, or typed
  category constraints. None contributes no positive token; plural order does
  not affect evaluation.
- Combined: correct outcome and all fields; unsupported cases require the
  correct unsupported status, with no additional score threshold.

The 20 no-feasible scenarios explicitly define an empty confirmed wardrobe and
expected downstream NoEligibleGarments. Their NLP remains supported. No garment
retrieval or recommendation is executed; recommendation_result is NotEvaluated.
RN-28, end-to-end RN-29/RN-30 recommendation outcomes and NFR-02 response targets
are not claimed. Validation cases (empty/non-string/overlength) are unit tests,
not included to inflate language evaluation accuracy.

## Reproduction and results

From backend/:

```powershell
uv run --no-project --python 3.12 --with pytest python -B -m pytest -p no:cacheprovider tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py -q --tb=short
uv run --no-project --python 3.12 python -B scripts/evaluate_nlp.py --output runs/nlp/evaluation.v1.json
```

The evaluation artifact includes original/expected/actual fields, statuses,
metrics, dataset hash, Python version, vocabulary version and source hashes.
runs/ is ignored generated evidence, not application source. No dataset is
downloaded and no LLM/API is called.

Executed 2026-10-14: intent 120/120 (100%), fields 450/450 (100%), explicit fields
130/130 (100%), combined 120/120 (100%). Precision/recall/F1 are 1.0 for all five
fields. RN-27 is achieved on this approved synthetic benchmark under the stated
measurement only. The result is not an independent real-user accuracy estimate.

Known unrelated architecture-test failure remains the ai-services directory
assertion; no folder or old architecture test is changed. Existing model and
frontend integration limitations remain outside Phase 2.

Focused NLP/unit-evaluator run: **51 passed** in 0.36 seconds, no warnings.
Final existing-backend plus NLP regression run: **165 passed, 1 failed**, in
11.06 seconds, with the existing Starlette TestClient deprecation warning.
The sole failure is test_report_architecture.py:28 (ai-services assertion).
An earlier unit run exposed a Windows default-encoding issue in the dependency
test; explicit UTF-8 reading fixed it before final verification.
`git diff --check` passed.

Exact regression command, from backend/:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

Not executed: heavy segmentation geometry tests, real-model inference/quality,
PostgreSQL deployment verification, capacity, frontend lint/build and browser
tests. There are no frontend/model/schema changes in this phase. Phase 3 is not
started; integration requires separate user review and approval.
