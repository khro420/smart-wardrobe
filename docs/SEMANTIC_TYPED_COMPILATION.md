# Typed semantic compilation candidate (Phase 2U)

`hybrid-semantic-intent-1.3.0` is an additive, opt-in candidate. The normal
`local_semantic_nlp_v1` profile continues to select grammar 1.1.0. This change
does not edit `.env`, restart services or reinterpret archived requests.

## Handover status

Grammar 1.3 is shipped for review and remains disabled. Keep
`SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_v1` for the
stable 1.1 interpreter. The final focused closure recorded 168 passing tests;
the fresh Phase 2U-B reserve recorded 23/24 exact structured agreements,
1/14 false rejections and 0/10 incorrect acceptances. A shopping plan phrased
as purchasing books with a white-top requirement still refused because source
coverage was incomplete. This task does not fix that limitation or activate
1.3. Earlier exposed evaluation cases are regression evidence, not new held-out
validation. Installation uses the same pinned assets as 1.1; see
[the installation guide](HYBRID_SEMANTIC_NLP.md).

The candidate reuses the installed, pinned CPU MiniLM and spaCy assets. It needs
no new package, model download or external API. Dependency analysis grounds
event heads, actors, venues and modifiers in the existing 18-context ontology.
Unrelated positive events refuse; supported birthday/dinner and dinner/date
compositions retain their existing facets. Lecture attendance and library study
cannot become presentation or shopping merely because the unrestricted NLI
classifier prefers those labels. The proposal retains that unrestricted result
for diagnosis; it is not an authorization to invent a context or garment fact.

Typed conditions compile directly into `AttributeConditions`/`AttributeIntent`
and `GeneralContextRequest`. No generated English is reparsed. Articles and
same-field OR values retain the garment role; jeans requires trousers AND denim,
and shirt requires a short/long-sleeve top category. One optional upper/lower
colour/category wish uses the existing bounded promotion policy. A bare
`preferably blue` requires an unambiguous positive hard-group antecedent.
An ordinary bare `I want a top` retains its existing coarse category request,
earned request-match value and absence of B1. Unsupported combinations of that
coarse request with other typed clauses refuse rather than silently change R.
Neutral `casual/formal/smart casual outfit` retains the predecessor's B1
all-present style qualification; it is not converted into contextual formality.
Interview actors belonging to another person are not silently bound to the
selected wearer, including possessors and third-party event subjects.

Every source token has a coverage reason. Clothing modifiers cannot borrow
permission from event vocabulary. Ambiguous OR branches, unsupported material
wishes, negated necessities, conditional/comparative requirements and relative
negative forms that need additional positive witnesses refuse rather than
weaken admission. Unsupported input is never retried as neutral text.

The raw request and normalization character map are retained. The new producer
has its own source/resource fingerprint; the nested context resource hashes
continue to mean the existing context18 schema/vocabulary, not a claim that the
legacy English parser ran. Independent reconstruction re-derives the typed
source graph. The writer separately repeats extraction under its existing
write lock, then independently enumerates and verifies exact scores/winners.
History verifies the signed frozen model output without reclassifying it.
Old 1.0/1.1/1.2 readers and their source fingerprints remain unchanged.

After approval and passing the activation gates, the existing server-owned
selector can use `SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_structured_v1`
with the existing mixed/context/language/interview/fashion/personalization
prerequisites. Selecting an unavailable model or inconsistent prerequisite
refuses explicitly; it never falls back silently. No additional application,
database, branch or worktree is needed.

`tests/test_semantic_structured.py` contains exposed development regressions,
adversarial source-scope cases and disposable persistence/receipt/history tests.
Those development examples are not held-out evidence. The separately sealed
Phase 2U validation reserve is evaluated only after the correction freeze and
is not used to tune this candidate.

Phase 2U-A adds dependency-scoped negative selection-command coverage. A closed
set of existing selection predicates, including the previously registered B1
`include` command, requires a direct negation, a direct garment/generic target,
an allowed actor and a validated exclusion group. The explicit clause boundary
is used when spaCy attaches an imperative across a semicolon. The proof records
the verb, operator, target and clause spans plus the exclusion group identifier;
independent reconstruction derives them again. Unknown action verbs, reported
speech, ability statements, conditionals and unbound optional wishes are not
licensed by this rule. This does not change garment evidence or scoring.

Phase 2U-B classifies requested actions before garment compilation. A positive
purchase/order directed at the assistant is unsupported. Source-bound self
plans and outfit-advice activity adjuncts may use the existing shopping policy.
Purchase targets are retained with exact spans as activity arguments, not B1
requirements about the wardrobe. A negated assistant transaction needs a
separate positive outfit request and creates no garment prohibition. Product
objects and purpose/beneficiary arguments remain distinct; meaningful positive
event purposes remain subject to contextual validation. Reported/conditional,
quoted, unresolved actor and purchased-item reference cases refuse. These
records are independently reconstructed and bound into the 1.3 fingerprint.
No model, source qualification, scoring or historical-reader contract changes.
