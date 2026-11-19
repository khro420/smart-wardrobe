# Local hybrid semantic interpreter

The repository's default interpreter uses `hybrid-semantic-intent-1.1.0`. Its additive
`mixed-hybrid-semantic-selection-1.1.0` contract preserves explicit mandatory
shirt nouns as same-member category constraints (`short_sleeve_top` or
`long_sleeve_top`) alongside material/colour requirements. Jeans still require
trousers AND qualified denim. No garment name or image supplies those facts.
The frozen semantic 1.0.0 reader and grammars 1.6–1.9 keep their historical meanings.
Use New Chat for the corrected interpretation; old receipts replay their records.

Phase 2U-D verified the opt-in typed interpreter `hybrid-semantic-intent-1.3.0`
and activated it locally with `local_semantic_nlp_structured_v1`. The repository
example still defaults to 1.1. See [typed compilation status](SEMANTIC_TYPED_COMPILATION.md)
for the 1.3 validation, scope and local activation details; archived readers
retain their original identities.

Phase 2V adds and locally activates `hybrid-semantic-intent-1.4.0` through
`local_semantic_nlp_unified_v1` for context-only, clothing-only, explicit outfit
style and combined requests. It preserves the 1.3 reader and uses the same
assets and policies. See [unified intent and verification](UNIFIED_OUTFIT_INTENT.md).

Phase 2V-A locally activates patch grammar `hybrid-semantic-intent-1.4.1` with
`local_semantic_nlp_appearance_v1` for source-bound positive appearance goals.
The 1.4 reader stays frozen; model assets, contexts and scoring remain unchanged.

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

## Already configured Windows: update to Grammar 1.4.1

Run these commands from your existing checkout root on `main`. Review any local
changes first; if Git reports a conflict or refuses the fast-forward, preserve
that work and reconcile it rather than resetting it.

```powershell
git status --short
git pull --ff-only origin main
notepad .\backend\.env
```

In the editor, change only this existing key (one assignment, no duplicate):

```dotenv
SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_appearance_v1
```

Retain all database/media paths, signing secrets, account credentials, model
settings and other profiles. Reuse the installed MiniLM + spaCy packages/assets;
this update adds no dependency or model download. The manifest, pinned semantic
requirements and missing-asset installer are already included in the repository.
Full setup and the portable-dataset installer are for installation, not this
upgrade; they are unnecessary for an already configured wardrobe.

Stop only this checkout's backend through its owning terminal/process owner
(Ctrl+C in its backend terminal). Keep the frontend running. Then start the
backend from the checkout root in that terminal:

```powershell
Push-Location .\backend
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

After stopping that terminal's backend later, `Pop-Location` returns to the
checkout root. If port 8000 is occupied, identify its owner before starting;
do not terminate unrelated Python processes. The existing `Start-Windows.ps1
-Stop` stops both recorded services, so use the backend's owner for a backend-only
restart. Existing wardrobe storage and authentication are retained throughout.

Refresh localhost:3000 and sign in normally. In Outfit Assistant's authenticated
`GET /api/v1/recommendations/capabilities` response, verify:

```text
mixed_wardrobe.grammar_version = hybrid-semantic-intent-1.4.1
mixed_wardrobe.contextual.semantic_interpreter.profile = local_semantic_nlp_appearance_v1
mixed_wardrobe.contextual.semantic_interpreter.ready = true
```

For a read-only browser-console check in the signed-in localhost:3000 tab:

```javascript
(async () => {
  const token = sessionStorage.getItem("smart_wardrobe_access_token");
  if (!token) return console.log("Sign in first.");
  const response = await fetch("/api/v1/recommendations/capabilities", {
    headers: { Authorization: `Bearer ${token}` }
  });
  const body = await response.json();
  const mixed = body.mixed_wardrobe;
  console.log({ status: response.status, grammar: mixed?.grammar_version,
    profile: mixed?.contextual?.semantic_interpreter?.profile,
    ready: mixed?.contextual?.semantic_interpreter?.ready });
})();
```

Only share the printed status/version/readiness object, never credentials or
authorization headers. An unauthenticated GET returns 401. If readiness is false,
use the existing asset troubleshooting/setup instructions below; do not replace
the wardrobe database or copy another PC's environment/secrets.

Use **New Chat** and try `I want to look sporty.` or `I'd like a short-sleeved top.`
Selection still requires qualified evidence. Date plus mandatory sporty style
currently remains InsufficientEvidence for the shipped wardrobe under the
unchanged date policy; this is distinct from an interpretation failure.

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
