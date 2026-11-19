# Outfit Review 1.1 — guided editing and experimental AI assessment

The main application's `/outfit-review` page now offers highlighted garment cards,
plain-language corrections, explicit confirmation and model-backed assessments.
It remains independent of saved wardrobe/recommendation records.

## Observation and correction

New analyses use `outfit-review-observation-1.1.0`. It adds jersey, socks/hosiery,
a generic visible-pair unit, optional visual-appearance style, and an explicit
feet observation. Socks do not establish shoes. A user can record a visible pair
with Unknown type, and can leave skirt/shorts/skort unresolved without guessing.
The 1.0 observation/confirmation readers, prompts and original predictions remain
unchanged and readable. Existing ephemeral 1.0 analyses can still use their old
backend contracts; re-upload/re-analyze for the new hosiery representation.

The editor uses the protected, oriented photo for highlights/crops. Draw a region
to add or adjust a garment. Confirm one garment versus a pair, choose a clothing
type or Unknown, and correct supported attributes. Choosing/confirming a category
explicitly updates its wearing role and clears conflicting alternatives; the UI
discloses this and keeps other values unchanged. Duplicate/pair reconciliation
is an explicit user action, not overlap-based inference. Review retained details
after grouping. Layers and ambiguous identities remain separate questions.

Confirmation1.1 records an explicit target assertion even when the user agrees
with an AI-preselected target. It checks every actual correction, ownership,
image binding, stale digest and revision link. Scope changes (region, grouping or
person) mark retained facts as user-scope-reviewed, not model-verified. Original
AI JSON remains immutable. These are review assertions, not wardrobe B0/B1 facts.

## Actual AI feedback versus basic summary

**Review My Outfit** uses the cached Qwen3-VL-4B language capability on the confirmed
fact catalog and MiniLM/spaCy's structured occasion. It does not re-observe the
photo or consume unconfirmed predictions. The rater chooses qualitative anchors,
reason codes and practical advice, citing catalog references. It cannot supply
a free-form overall number, extra garment, material, brand or body comment.

The server independently validates references/reasons, whole-outfit evidence
coverage and score eligibility. Specific factual prose is rendered from confirmed
values; subjective judgments/advice are model-selected, not inferred through
keyword counts. This constrained presentation avoids unchecked generative clothing
claims. Unsupported judgments are rejected, not silently converted into praise.
An explicit dress code must be considered by the occasion judgment. No interview
or wedding dress-code default is imposed by this adapter.

**Basic summary (CPU only)** is the earlier descriptive fallback, clearly labelled
as such. It is not AI aesthetic feedback and always withholds numerical scores.
The existing 18-context interpreter and Outfit Assistant behavior are unchanged.

## Published rubric

`outfit-review-experimental-rubric-1.1.0` uses these **subjective experimental**
anchors, not fashion-quality probabilities or validated universal standards:

| Anchor | Meaning | Points |
|---|---|---:|
| Strong | Clearly supported coherence/alignment for the named dimension | 90 |
| Coherent | Generally aligned, with minor reservations | 75 |
| Mixed | Meaningful competing elements/tension | 50 |
| Needs attention | Substantial supported mismatch | 25 |
| Not assessable | Evidence or judgment is insufficient | — |

Dimension scope and numerical eligibility:

- **Occasion suitability,40%:** known categories and reviewed appearance styles;
  shoes or bare feet actually visible; role/context safely interpreted; no extra
  conditions the visual method cannot independently assess. Socks-only/out-of-frame
  shoes withhold this score. No claim of venue admission or institutional policy.
- **Colour coordination,25%:** named visible colours for every item. An unspecified
  multicolour palette or uncertain colour is insufficient for a complete rating.
  Repeated-colour reasoning must cite an actual shared recorded colour.
- **Style consistency,20%:** all categories and appearance-style labels known.
  Garment names alone do not establish style, material or physical fit.
- **Pattern/layering,15%:** all patterns reviewed and layering relationships resolved.
  The model must cite every relevant pattern/layer; missing layers are not invented.

For complete supported judgments, overall = Σ(points × weight)/100, using exact
Fraction arithmetic and one-decimal display. Example75/90/75/50 gives75/100.
If **any** dimension is Not Assessable, the overall is withheld; supported dimension
ratings may still display. No weights are redistributed, and no Outfit Assistant
R/C/P computation is reused. Models cannot bypass evidence gates with a high anchor.
No calibration/general fashion-accuracy claim follows from arithmetic/unit tests.

## Workflow and resources

1. Sign in at `http://localhost:3000/outfit-review`; upload a consented JPEG/PNG.
2. Confirm GPU availability and Analyze Outfit.
3. Resolve the plain-language questions, save corrections and confirm the inventory.
4. Describe the occasion, including relevant participant role and actual dress code.
5. Reconfirm GPU availability for model feedback, or choose the CPU-only summary.
6. Read the dimensional explanations, practical advice and experimental-score label.

Each model action is serialized and uses the same pinned assets/runtime and
`--cache-ram 0` guard. The 8GiB preload RAM,2GiB runtime RAM and512MiB free-VRAM
floors remain unchanged. No model downloads or automatic retries occur. A model
failure retains the confirmed inventory and accepts no score. CPU-only work can
continue with Discord/video; resource-sensitive inference requires a fresh check.

Activation remains the existing process-only `SMART_WARDROBE_OUTFIT_REVIEW_ENABLED=true`
opt-in; default/example files remain off. The owned backend must load the updated
code. The development frontend picks up the new components; no second application
environment is used. See [prototype setup](AI_OUTFIT_REVIEW_PROTOTYPE.md).

Bearer authentication, temporary photo bounds/expiry, no-store responses and
atomic owner-scoped transitions remain. No permanent review history, wardrobe
registration, new account or live-data migration is added. A backend restart
clears temporary reviews, so re-upload afterward. Technical IDs, JSON and original
prediction/provenance details are confined to optional developer sections.

## Current real-model verification limit

The bounded Phase 3G H1 check ran actual 4B vision once. Its proposal was rejected
because it repeated the same pattern value three times. The original response
and failure were preserved; no correction, confirmation or score was accepted.
No inference retry or subsequent AI-feedback request ran. The observation must
pass validation before the guided editor becomes available. This remains a
practical model-output reliability limitation, not an accuracy success.

Grounded feedback, rubric arithmetic, correction/privacy flows and desktop/mobile
presentation pass focused CPU/browser fixtures. These are not evidence of a
completed real-model feedback workflow or validated fashion accuracy. If analysis
fails, keep the failure visible; do not treat the unvalidated proposal as facts.

## Phase 3G-A: auditable output handling

New analyses wrap the same 1.1.0 prediction vocabulary in observation envelope
`outfit-review-observation-1.1.1`. Its required normalization record uses
`identical-attribute-label-dedup-1.0.0`: bounded attribute arrays may remove only
byte-identical repeated strings, retaining first occurrence order. Raw JSON,
its SHA256, normalized JSON SHA256 and each exact before/after path are retained.
The reader independently recomputes the record and validates the prediction.

For example, `checked, checked, checked` can become one `checked` label; this says
nothing about whether the garment is actually checked. Distinct conflicting
observed values still fail. Uncertain alternatives retain distinct values and
their uncertainty. No category, role, region, state or unsupported label is
repaired. Oversized arrays, duplicate JSON keys and unknown/value inconsistencies
remain errors. Category/role and identity issues still need explicit review.

The model-facing schema now encodes Unknown/observed/uncertain value cardinality
directly. Constraints are independently checked; decoding is not visual proof.
Historical observation1.0/1.1 and confirmation readers remain strict and their
serialized records/digests are unchanged. The new envelope and normalization
are included in the existing owner/image/revision confirmation binding.

The ordinary editor explains any identical-label normalization; raw predictions
and detailed transformations remain under Developer details. Neither normalized
nor user-corrected outputs establish model recognition accuracy. Phase 3G's failed
raw result and measurements remain preserved as historical results.

The real Phase 3G-A workflow reached authenticated corrections and confirmation,
then ran actual feedback inference. That response decorated its reference IDs
with values and omitted one garment from its whole-outfit colour citations. It
remains rejected; it was not repaired or presented as a successful review.
Feedback decoding now uses catalog-bound reference choices and fixed dimension
slots, requiring complete evidence for an assessed dimension or an explicit
Not Assessable result. These constraints mirror the unchanged independent
assessor; no missing reference is appended after generation. The final decoding
correction passes focused CPU tests but has not been retested on the real model.
No full real-model end-to-end pass or accepted fashion score is claimed.
