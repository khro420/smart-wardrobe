# Context Framework Phase 2: Date and Dinner policy implementation and verification

2026-10-25, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
The expressly approved Date/Dinner policies now operate through the accepted
`general_context_v1` framework. No separate event interpreter, service, evaluator
or scorer is introduced. Wedding and legacy profiles remain available. The manual
application was not restarted; this report does not activate a profile globally.

**155 requirements remain 144 Verified / 2 Partial / 9 Unverified / 0 Blocked.**
RN-13 remains Partial; NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. Whole-FYP
acceptance remains NOT READY. These are bounded prototype appearance rules,
not independently established fashion, comfort, weather or safety judgements.

## 1. Authority and exact scope

The owner answered **“Approve these Date/Dinner policy rules”**, **“Approve friends
and plain restaurant treatment”**, and **“Owners approve this exact implementation/test
scope”** for the concrete proposal. [ownership-approval.json](../storage/verification/date_dinner_policy_v1/ownership-approval.json)
records all three answers, the named paths and exclusions. The accepted proposal,
its 58 labels and the Phase 1 report/results retain their original bytes.

Exactly **12 existing production files change; no production file is added**:

| Owner | Approved paths | Implemented change |
|---|---|---|
|R NLP|`backend/app/application/nlp/general_context_interpreter.py`; `backend/app/application/nlp/config/context_grammar.v1.json`|One shared going-out frame; grammar 1.1.0; original text/spans and unknown-modifier guards retained.|
|R taxonomy/policy|`backend/app/application/recommendation/config/situation_taxonomy.v1.json`; `backend/app/application/recommendation/config/context_policy_registry.v1.json`|Taxonomy/registry 1.1.0; exact date/dinner declaration projections and two appended policy bindings. Wedding binding subtree remains equal.|
|R registry/compiler|`backend/app/application/recommendation/context_policy_registry.py`; `backend/app/application/recommendation/context_constraint_compiler.py`|Strict three-binding activation envelope, allowlisted reviewed-style set predicate, approved per-binding companions/venue and assumptions.|
|R evidence/evaluator|`backend/app/application/recommendation/context_evidence_resolver.py`; `backend/app/application/recommendation/general_context_evaluator.py`|Exact legacy declaration channel, shared inference, explicit/inferred provenance and additive 1.1.0 explanations for new bindings.|
|Shared frontend|`frontend/lib/api.ts`; `frontend/lib/recommendation-messages.ts`; `frontend/components/OutfitAssistant.tsx`; `frontend/components/RecommendationResult.tsx`|Typed explanations, provisional guideline/limits, stated venue/companions and careful insufficient-evidence guidance. Stored 1.0.0 and wedding rendering retained.|

Only three existing verification/support files advance: `integration_source_guard.py`,
`test_general_context.py` and `test_general_context_equivalence.py` under backend/tests.
The two test modules name exactly G03/G08/G22/G23 as intentional inactive-to-available
transitions and update the capabilities list. Their original copies and frozen Phase 1
label fixture remain. No other existing test, oracle, label or manifest is edited.
Six named new test/fixture/browser/configuration files provide separate coverage.

[source-transition.json](../storage/verification/date_dinner_policy_v1/source-transition.json)
and `date_dinner_context_sources.v1.json` pin all twelve exact before/after hashes.
The existing guard follows this transition after prior transitions; earlier manifests
are not repinned. Before copies and the phase patch identify this increment within
the earlier uncommitted workspace. No staging/commit/reset/packaging is inferred.

## 2. Approved policies and interpretation

| Condition | Date policy | Dinner policy |
|---|---|---|
|Unspecified code|DT01: current reviewed casual OR smart casual may infer Pass.|DN01: same bounded positive appearance rule.|
|Explicit casual|DT02: current reviewed casual only.|DN02: current reviewed casual only.|
|Explicit smart casual|DT03: current reviewed smart casual only.|DN03: current reviewed smart casual only.|
|Missing/stale/malformed/uncovered evidence|DT04: Unknown; no invented attributes.|DN04: same.|
|Formal/black tie or unsupported required context|DT05: unavailable, even with owner Allow.|DN05: same.|

Bindings are `date_appearance_v1` / `date-appearance-1.0.0` and
`dinner_appearance_v1` / `dinner-appearance-1.0.0`. They use the same resolver,
compiler, evaluator, member preparation, mandatory gate and scorer as the framework.

All five requested phrases work without a fixed command prefix. Natural and command
wording resolve to the same exact date/dinner declaration target. “Going out for
dinner” supplies no outdoor environment. Dinner may retain explicitly stated friends;
date-with-friends is unavailable. A plain explicitly stated restaurant is admitted
for either binding without supplying garment evidence or a dress code. Other venues,
specialised modifiers and unsupported conditions remain controlled unavailable or
UnsupportedRequest. No upscale venue, gender, weather or role is invented.

Today/tonight/tomorrow remain timing information: current wardrobe only, no forecast
or future availability. Dress code and requested formality remain separate frame
slots with the existing effective scoring projection. No implicit formality condition
is created for unspecified requests; no guest-role assumption leaks from wedding.
Compound “dinner date”, negation, conflicting codes, calendar-date questions, weather
and unknown meaningful code/modifiers are not reduced to a permissive generic outfit.

## 3. Evidence, declarations and explanations

Capability admission precedes overrides. Every member, including outerwear, must pass:

1. An identifiable applicable exact Deny wins, including Allow+Deny and Deny with
   malformed companion evidence.
2. Otherwise malformed authoritative declarations or a malformed contextual namespace
   remain Unknown; they cannot be bypassed by Allow or inference.
3. A clean exact date/dinner or explicitly requested formality Allow supplies only
   that condition's positive evidence, recorded as `explicit_declaration`.
4. Genuinely absent declarations may use the approved current singleton owner-reviewed
   style/category binding, recorded as `attribute_inference` with DT/DN rule IDs.
5. Missing/stale review or a valid uncovered style stays Unknown. Classic is not
   declared unsuitable; it simply lacks a positive inference rule in this policy.

Wedding overrides do not establish date/dinner evidence. Dinner Allow does not
establish date suitability, nor does Date Deny automatically prohibit dinner.
Occasion Allow cannot waive a separately requested formality Deny. An unrequested
formality declaration is not silently turned into an occasion requirement.
Original legacy conflict semantics remain unchanged and blocked.

Existing reusable style review is sufficient for these approved appearance heuristics.
No per-event tag matrix, review writer, new evidence field, automatic backfill or
AI-confidence admission is added. Unreviewed model/saved style alone remains Unknown.
No garment/attribute is fabricated. This does not independently certify model accuracy
or real-world appropriateness.

New success/history explanations retain policy/bundle hashes, declaration target,
exact supporting declarations, rule/basis, actual review and observed style. The UI
discloses that an unspecified-code suggestion uses a **provisional casual/smart-casual
appearance guideline**, without claiming a dress code was inferred. It identifies
stated companions/venue and disclaims unestablished comfort/weather/shoes/accessories.
Insufficient-evidence guidance explicitly says a correct uncovered style should not
be relabelled merely to obtain a result. Old stored explanation formats still render.

## 4. Preserved boundaries and bounded work

Exact Fraction R/C/P calculations, 3/5+1/5+1/5 weights, preferences, compatibility,
four structures, exhaustive enumeration, candidate counts and deterministic tie order
are unchanged. Context creates no bonus or extra request term. With one blue reviewed
dress and no preferences, R=1, C=1/2, P=0 gives 7/10. The independent four-garment
fixture verifies all candidate decisions/scores and the stable dress-A+outer-A winner
at 4/5; compact/reference/public checks agree. Unknown outerwear never passes implicitly.

ConfirmedGarmentQuery ownership/confirmed/availability, quota 100, review storage,
atomic persistence, historical replay, durable logout and Homepage remain byte-identical.
Real API negatives cover archived/unavailable/foreign/unconfirmed rows, missing
structure and hard colour/category contradictions. Rank-to-commit review change
returns WardrobeChanged with no partial chat. A legacy date result replays with its
original score/provenance across profile reselection; frozen wedding replay and
other atomic/auth boundaries remain in the broader regression.

For each new binding, a 100-snapshot/two-condition call-count check records **400
primary/independent resolutions plus 4 winning-member gate resolutions, 5 compilations**.
They occur before enumeration or after its completion. This reuses the existing
bounded preparation contract; no per-candidate NLP/config/database/model work,
speculative optimisation, new capacity study or full NFR benchmark is introduced.
Functional durations below are not latency acceptance. Formal NFR-01/02/03 remain open.

## 5. Executed verification

| Check | Actual final evidence |
|---|---|
|Focused backend regression|**1077 passed in 380.87s**, native exit 0; includes **270 new cases** plus the prior 807-case scope with the explicitly approved current-contract adaptations.|
|Approved independent matrix|**58/58 API outcomes** match unchanged approved labels, including the five requested phrases, scopes, malformed/stale evidence, structures, strict eligibility and persistence. Complete responses are retained per case.|
|Other new backend coverage|192 independent member combinations, 10 rejected registry mutations, 6 complete four-structure score/reference/public comparisons, 2 semantic-score equivalence groups and 2 bounded preparation checks. These overlap the 270 and are not added again.|
|General profile / actual Chrome|**14/14 in 44.5s**: 3 new Date/Dinner journeys plus 11 unchanged framework/shared/logout cases.|
|Frozen wedding profile / actual Chrome|**10/10 in 21.7s** using unchanged wedding browser definitions plus shared/logout cases.|
|TypeScript / scoped lint / production build|Native exit 0; separate retained build **gQn37OXAxL5LiBqhqoxPT**. Generated Next tsconfig/next-env/AGENTS copies retained and original bytes restored.|
|Source/data integrity|All **1,187 starting files remain: 1,172 unchanged, exactly 15 approved changes**. All 36 protected boundaries and 392 other application paths match; staging empty.|
|Old evidence continuity|All 438 Phase 1 entries reconcile: 423 unchanged, 15 approved live source/test references advance with retained original bytes. All 9 proposal deliverables remain exact. No old raw artifact/report/label/manifest rewritten.|

Chrome is actual installed product **156.0.8078.48**, not bundled Chromium. Browser arms
use ordinary app.main/Uvicorn, production Next and normal proxy on 3100/3101,
real register/login, disposable synthetic databases, development identity off and
generated unpublished child secrets. Development processing is disclosed; VTOFF/VTON
are off. There is no real-model, private-account or system-browser update operation.
The 24 browser executions have overlapping definitions, not 24 distinct cases.
No new Edge/Firefox/latest-release or universal accessibility claim is made.

New explanation/name bounds fit 360/390/768/1280/1920px; full 100-character names,
keyboard request/history actions, Save as outfit and VIS source preparation pass.
Native Chrome zoom is settings zoom 2, DPR 2, physical width 1440, content width
711, CSS zoom 1 and visual scale 1. Both Date/Dinner and reused wedding result/history
bounds pass. Visual review inspected the 360px result; native screenshot/geometry
and DOM bounds are retained, not a complete subjective accessibility study.

## 6. Retained attempts and operational limits

All attempts remain under [date_dinner_policy_v1](../storage/verification/date_dinner_policy_v1/).
The initial run retained 200 failures/10 passes/58 setup errors: the new registry
validator incorrectly assigned wedding W02/W03 using the new social-rule order.
The validator was corrected to preserve the frozen wedding code mapping; no old
rule JSON/label changed. The next run retained 248 passes/20 failures, all caused
by new tests expecting decimals rather than the existing exact fraction JSON.
Correcting those assertions produced 268 passes. Two social call-count cases and
complete per-candidate assertions then entered the final 1077-case regression.
Intermediate passes overlap and are not pooled as extra distinct coverage.

A preliminary inline PowerShell probe failed quoting before Python executed. The
first new audit read curly-apostrophe frozen labels using the Windows default encoding;
explicit UTF-8 corrected that helper. Neither was an application failure or required
an old oracle/production policy change. Existing uv no-project, Starlette/httpx
deprecation and Playwright colour warnings remain; native child codes determine checks.
No retry, extended deadline or weakened Deny/unknown condition converted a failure.

Both owned browser backends complete normal shutdown with native exit 0; owned
frontends/browsers stop and ports 3100/3101 are free. Synthetic DBs remain at ledger
paths. No unrelated process/manual service was stopped. These ordinary stops do not
diagnose J-16's historical larger-run shutdown timeout or establish multi-worker,
in-flight, forced-termination or installed-service recovery.

## 7. Use, remaining work and disposition

The existing process-only opt-in remains:

```powershell
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
```

It requires Assistant and suitability enabled; the intended compact demonstration
also uses compact_exhaustive and experimental_compatibility_decision_v1. Global
default remains disabled. This phase does not restart/alter the manual application,
its existing database/media/secret or any deployed setting. No migration is added.

Only Date/Dinner is added to wedding in the general profile. Interviews,
presentations, graduations, beach activities, hiking and travel remain unavailable;
formal/specialised/comfort/weather capabilities and model-derived trust need separate
evidence, concrete policy and ownership approval. Primitive reuse is not policy consent.

[requirement-baseline.json](../storage/verification/date_dinner_policy_v1/requirement-baseline.json)
pins the complete unchanged 155-row authority. RN-13 and FR-VIS-01 remain Partial;
FR-DW-03/04/06/07, FR-VIS-09 and NFR-01/02/03/11 remain Unverified. Remaining
acceptance dependencies are bounded RN-13 and VTON scope, lawful real-model evidence,
final SQLite/PostgreSQL architecture, formal NFR baseline/history maximum,
HTTPS/deployment/data/cutover and canonical ai-services reconciliation. None is
resolved by these author-labelled appearance policies.

**PASS WITH LIMITATIONS.** The approved rules and exact scope are implemented and
verified for the documented local contract. Whole-FYP acceptance remains NOT READY;
NFR-02 remains OPEN / NOT FORMALLY ACCEPTED. No additional policy increment,
deployment, private data operation, default activation or full benchmark begins.
Wait for owner review.
