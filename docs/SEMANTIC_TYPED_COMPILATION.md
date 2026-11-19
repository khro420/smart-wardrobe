# Typed semantic compilation candidate (Phase 2U)

`hybrid-semantic-intent-1.3.0` is an additive, opt-in candidate. The normal
`local_semantic_nlp_v1` profile continues to select grammar 1.1.0. This change
does not edit `.env`, restart services or reinterpret archived requests.

## Handover status

Grammar 1.3 is shipped for review and remains disabled. Keep
`SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE=local_semantic_nlp_v1` for the
stable 1.1 interpreter. The prior Phase 2U-B closure recorded 168 passing tests;
the fresh Phase 2U-B reserve recorded 23/24 exact structured agreements,
1/14 false rejections and 0/10 incorrect acceptances. A shopping plan phrased
as purchasing books with a white-top requirement still refused because source
coverage was incomplete. This task does not fix that limitation or activate
1.3. Earlier exposed evaluation cases are regression evidence, not new held-out
validation. Installation uses the same pinned assets as 1.1; see
[the installation guide](HYBRID_SEMANTIC_NLP.md).

Phase 2U-C corrects copular shopping departures: in “I'm off to the mall to
purchase books”, the departure modifier and purpose infinitive can share a
positive self-subject governor. Coverage requires that dependency relationship
and a destination; it does not authorize assistant purchase commands or erase
independent garment requirements. The candidate's registered fingerprint is now
`9ad44475f9917bbf46d36775abcf8df014987ebfa2ab8ec5e87f6265ea1bc178`.
No existing live 1.3 proofs were present; 1.0–1.2 readers are unchanged.

The correction passed 185 focused checks. Its separately sealed, once-opened
16-case reserve recorded 13/16 exact agreements, 2/10 false rejections and
0/6 incorrect acceptances. One further exact mismatch was a prewritten label
using `in` instead of the existing material `contains_any` operator; cotton
and the shirt category were both preserved. The two genuine false rejections
concern a plural shopping-purpose declaration and an “I'd like either…”
request. Original labels/results remain retained; no correction was tuned to
the opened reserve. Activation remains blocked, grammar 1.1 remains active,
and no local profile change or restart followed.

### Phase 2U-D local activation

The next correction resolves subjects attached to an auxiliary spine and binds
an infinitival purchase purpose to its existing shopping activity. No subject
is borrowed from a product, complement or unrelated clause. Positive
first-person `would like` requests license their verb only when a direct,
already validated garment object is present. Same-member, same-axis OR remains
exact; correlated category/attribute branches and cross-role alternatives refuse.

The frozen candidate passed 27 new and 128 relevant existing checks. A fresh
24-case reserve, manually labelled and sealed before source changes, then ran
once: 24/24 full structured agreements, 0/14 false rejections, 0/10 incorrect
acceptances, zero interpretation errors. No source tuning followed that run.
The previous cotton-label correction is an explicit evaluation erratum; the
original Phase 2U-C labels and raw results remain preserved.

The registered 1.3 fingerprint is
`ea22cb9d0967594d03074117d7e67f832f1eb9e5392e4fdc4731683fc760df4c`.
No live 1.3 proof predated the correction. Historical 1.0–1.2 readers and all
scoring/evidence policies are unchanged. Only the local semantic selector was
changed to `local_semantic_nlp_structured_v1`, and only the owned backend on
8000 was restarted. Frontend 3000 was retained. The repository `.env.example`
still selects stable 1.1; no commit or push is part of this phase.

Refresh the existing UI and use New Chat. In the authenticated capabilities
response, `mixed_wardrobe.grammar_version` must be
`hybrid-semantic-intent-1.3.0`, with
`mixed_wardrobe.contextual.semantic_interpreter.profile` equal to
`local_semantic_nlp_structured_v1` and `ready=true`. Unauthenticated requests
continue to return 401. Accepted language may still legitimately produce
InsufficientEvidence or no matching outfit when qualified garment facts are absent.

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
