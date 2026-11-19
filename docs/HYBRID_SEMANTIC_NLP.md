# Local hybrid semantic interpreter

The current interpreter uses `hybrid-semantic-intent-1.1.0`. Its additive
`mixed-hybrid-semantic-selection-1.1.0` contract preserves explicit mandatory
shirt nouns as same-member category constraints (`short_sleeve_top` or
`long_sleeve_top`) alongside material/colour requirements. Jeans still require
trousers AND qualified denim. No garment name or image supplies those facts.
The frozen semantic 1.0.0 reader and grammars 1.6–1.9 keep their historical meanings.
Use New Chat for the corrected interpretation; old receipts replay their records.

The pretrained `cross-encoder/nli-MiniLM2-L6-H768` classifier selects among the
existing 18 context descriptions. The pretrained spaCy `en_core_web_sm` dependency
parser extracts garment phrases, scope, actors and contextual observations.
Models run locally on CPU, in evaluation mode, without remote code or an API.
They receive request text, never garment images, account data or wardrobe facts.

Source-grounding, complete modifier/negation coverage, role and schema checks
validate the untrusted proposal. A deterministic compiler emits the existing
structured context/B1/optional contracts. Its canonical sentences are an output
encoding, not a list of input examples. Unsupported meaning refuses explicitly.
Models never supply garment evidence, scores or outfit selection.

New writes repeat extraction under the write lock and independently reconstruct
the candidate universe, scores and winner. History verifies the stored signed
proposal, source spans and dependency bindings without classifying the context
again. Existing Fashion Compatibility v2, exact 3/5–1/5–1/5 weights, feedback,
diversity, eligibility, proof readers, receipts and continuation limits remain.

## Installation and activation

Python 3.12 on Windows, Node.js and the existing application are required.
`Setup-Windows.ps1 -Mode CPU` installs the pinned semantic dependencies and runs
`backend/scripts/setup_semantic_nlp.py`. GPU setup installs the same CPU NLP path;
Student 1's model execution settings are separate. `-SkipSemanticModel` skips the
NLI asset download, leaving explicit model-unavailable errors if activated.

For an **existing configured wardrobe**, stop only its owned backend, then run
from the checkout root (this does not install or replace a database):

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements-semantic.txt
.\backend\.venv\Scripts\python.exe -B .\backend\scripts\setup_semantic_nlp.py
```

Set this server-owned key in `backend/.env`, preserving every other setting:

```dotenv
SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_v1
```

The existing mixed-wardrobe, contextual-language and interview-default profiles
must already be configured. Missing prerequisites refuse; there is no silent old
interpreter fallback. Restart the owned backend and refresh the existing UI.
Capabilities advertise `mixed_wardrobe.contextual.semantic_interpreter.ready` and
the new grammar identity. Requests still require authentication and the intended
wearer. Do not copy another PC's virtual environment, credentials or `.env`.

The pinned NLI weights occupy 328.5 MB plus about 2.6 MB tokenizer data; the syntax
wheel is about 13 MB. Torch and the other Python dependencies require additional
disk/RAM and a network connection at installation. Runtime is offline. Asset
hashes, model revision and syntax-package hashes are recorded in
`semantic_model_manifest.json`; missing/changed assets refuse explicitly.
CPU latency and peak RAM are not benchmarked by this functional phase.

## Phase 2T evaluation candidate

Normal `local_semantic_nlp_v1` remains grammar **1.1.0**. The main codebase also
contains an opt-in **1.2.0** candidate, selected only with the existing key set to
`local_semantic_nlp_scope_v1`. Keep that candidate disabled for ordinary use: its
generalization review found substantial false rejection and a retained lectures
versus presentation accuracy failure. No live activation or service restart was
performed during Phase 2T.

The candidate preserves context modifiers before local NLI and independently
projects a complete trailing `preferably [canonical colour]` onto a proven hard
garment anchor. It records the original model slots, exact source projections
and frozen context result in a new additive proof revision. Writes repeat the
extraction under lock; history revalidates source projections without rerunning
context classification. Scoring and historical 1.0/1.1 readers are unchanged.

On 20 untouched requests, structured agreement was 9/20 for 1.1 and 12/20 for the
candidate; clear-request false rejection remained 8/13. These are small, manually
labelled semantic tests, not a broad accuracy certification. Discovery cases
used for correction live in `semantic_scope_regressions.v1.json` and do not count
as held-out evidence. The failed lectures assertion is retained, not skipped.

## Boundaries

This is bounded English interpretation, not unrestricted conversational reasoning.
Unknown modifiers, weather needs, unsupported comparisons, incompatible events,
ambiguous roles and unrepresented constraints must refuse. Optional material,
multiple optional wishes and optional OR retain the existing policy restrictions.
Own-wedding participant roles do not inherit the guest policy. Possessive
“friend's wedding” does not mean the friend is accompanying the wearer.
Negated wishes and negated necessity are not converted into hard exclusions.
An accepted interpretation can still produce InsufficientEvidence or no match.
The model supplies no confidence threshold or accuracy certification for clothing.

The failed small generative-model exploration was not selected for runtime.
No LLM server, cloud subscription, training, CV asset or GPU is required by this
interpreter. Source tests require the installed local semantic models.
