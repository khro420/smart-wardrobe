# Unified outfit intent — Grammar 1.4

`local_semantic_nlp_unified_v1` selects `hybrid-semantic-intent-1.4.0` in the
existing main application. It uses the same pinned MiniLM + spaCy assets and
the same 18 context policies. No new package, model download, database or service
is required. The local semantic profile is opt-in; `.env.example` retains its
existing default. Grammar 1.3 remains a frozen historical interpreter.

## Meaning and evidence

- Context-only requests keep the existing contextual interpretation.
- Clothing-only requests do not need an occasion. Existing category, colour,
  material, pattern, sleeve, OR, negation and optional-preference contracts apply.
- Explicit outfit styles use the existing canonical recorded-style schema:
  sporty, casual, smart casual, formal, minimal, classic, streetwear, vintage
  and bohemian. A whole-outfit style is a mandatory `all_selected/all_present`
  B1 `style/contains_any` requirement. Every selected garment needs qualified
  evidence; names, images and unverified saved predictions do not supply it.
- A context plus a style/clothing condition keeps both. Context suitability
  cannot erase the mandatory condition. Conflicts or missing evidence can
  correctly produce a refusal, InsufficientEvidence or no qualified match.
- Recorded style is distinct from an asserted event dress code. Explicit
  dress-code clauses retain the existing contextual contract and policy checks;
  an outfit-style request does not fabricate verified dress-code evidence.
- `Show me something with long sleeves` means an existential qualified sleeve
  requirement across selected garments. It does not assume a top, dress or
  outerwear category. `long sleeves` uses the existing canonical descriptor
  mapping to wrist-length; no new fine value is inferred. A bare `short sleeve`
  requires clarification. A named `short-sleeved top` keeps its upper role.
- `would like` is a bounded positive request form; `prefer` remains optional.
  Optional outfit-style wishes are not supported and are never converted into
  mandatory requirements. Existing bounded top/bottom wishes remain unchanged.
- Whole-outfit style combinations, unresolved comparisons/similarity, unsupported
  modifiers/actions and ambiguous cross-role OR refuse rather than lose meaning.

## Implementation and history

`semantic_unified_fragments.py` binds explicit outfit-wide facts and request
predicates to actual source dependencies and spans. `semantic_unified_source.py`
retains the existing contextual relations while acquiring those typed fragments.
`semantic_unified_actions.py` preserves purchase-command checks and validates
nominal activity adjuncts of a first-person departure, including parser attachment
variants. No list of whole input sentences is used.

`semantic_unified.py` validates the full source graph, uses the unchanged typed
context constructor and binds the new producer identity to the complete intent.
It never reparses generated English. New proof-version dispatch extends the
existing writer/history paths; no proof codec, scoring algorithm or schema was
replaced. Locked extraction, independent complete candidate reconstruction,
source revalidation, receipts, rollback and continuation limits still apply.
The raw request and normalization map remain exact. Old 1.3 source hashes and
historical meanings are unchanged; old history and parent chains retain their
own version rather than being reinterpreted as 1.4.

## Verification and local use

Final focused run: 107 passing cases; TypeScript passed. The separately sealed
20-case wording reserve ran once after correction freeze: 20/20 complete
structured agreements, 0/12 false rejections, 0/8 incorrect acceptances, zero
errors. These are bounded functional results, not broad language-accuracy or
NFR performance certification.

The local backend was restarted on 8000 with
`SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_unified_v1`.
Frontend 3000 was retained. Refresh, select the intended wearer and use New Chat:

1. `I'm going on a date.`
2. `I want a sporty outfit.`
3. `I'd like a short-sleeved top.`
4. `I'm going on a date and I want a sporty outfit.`
5. `I'm studying at the library and I'd prefer black trousers.`

Only interpretation acceptance is implied: an actual outfit still requires
qualified evidence and compatibility. The authenticated capabilities endpoint
advertises the new grammar/profile using the existing mixed-wardrobe capability.
No additional installation, account, wardrobe selector or UI mode is needed.

## Phase 2V-A appearance-goal correction

Local successor `hybrid-semantic-intent-1.4.1`, selected by
`local_semantic_nlp_appearance_v1`, adds positive first-person appearance goals
such as `I want to look sporty`, `I need to look classic` and `I'd like to look
casual`. It binds an existing canonical style complement to the existing
mandatory whole-outfit style contract. Adjectival and canonical nominal
complements are supported, including spaCy's noun analysis of `smart casual`.
Optional wishes, third-party/reported goals, past assertions, search/look-at
meanings, comparisons and unresolved instructions remain refusals. Explicit
assistant purchase actors cannot borrow an appearance-goal activity frame.

The reported `im going for dating` already resolved to `social.date`; no new
dating vocabulary was added. The correction covers the appearance predicate
and its style, retaining exact original text/spans and every existing context
policy. Grammar 1.4 source bytes and its historical reader remain unchanged.

Verification: 58 focused cases passed. A separately sealed, once-opened
12-case reserve achieved 12/12 exact structured agreements, zero false
rejections among six supported requests and zero incorrect acceptances among
six required refusals. No source tuning followed that validation.

The live male `My wardrobe` scope has two qualified sporty synthetic garments
(TEST-2ND-006 grey top and TEST-2ND-022 grey shorts). Their complete sporty outfit
has Unknown date suitability under the unchanged date-appearance policy, which
uses saved casual/smart-casual labels. No outfit currently passes both date
suitability and mandatory sporty evidence. Both the informal and ordinary
date-plus-sporty requests therefore correctly remain InsufficientEvidence;
sporty-only requests can succeed. No evidence was relabelled to change this.
