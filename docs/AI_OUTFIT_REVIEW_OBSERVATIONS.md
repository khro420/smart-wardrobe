# AI Outfit Review observation foundation

Phase 3F integration update: the pure foundation below remains unchanged; a
separate opt-in page/service now consumes it. See
[confirmation-first prototype setup](AI_OUTFIT_REVIEW_PROTOTYPE.md). The Phase 3E
scope and pilot findings below remain historical evidence, not a readiness claim.

Status: independent, unwired foundation. No application routes, uploads, wardrobe
registration, fashion scores, review-history tables or runtime flags are added.
Qwen3-VL-4B-Instruct Q4_K_M is the initial **candidate**, not a validated production
model. 8B remains experimental. Model weights stay outside Git.

## Contracts

`backend/app/application/outfit_review/contract.py` defines
`outfit-review-observation-1.0.0`. `Prediction.model_json_schema()` produces its
model-facing JSON Schema; `Observation.model_json_schema()` includes the envelope.

- Image identity: original bytes SHA256, oriented RGB-pixel SHA256, dimensions and
  coordinate contract. Regions use full EXIF-oriented image coordinates 0..1000.
  No VTON resizing/cropping is applied.
- Scene: visible person regions, IDs, target ID and single/multiple/no/unclear
  person status. Multiple people require explicit user target selection. All
  retained items must reference that target; bounding boxes must lie within it.
- Garments: unique physical-item IDs, image region, category, wearing role,
  visibility, single/pair/unresolved identity, colours, pattern, sleeve length and
  sleeve rolled state. Unknown attributes have no value. Uncertain alternatives
  remain alternatives. Clothing categories never establish fabric composition.
- Relationships: observed/uncertain layering and unresolved identity questions.
  Cycles, dangling references, exact-region duplicates and split footwear pairs
  are surfaced for review. Overlapping layers are **not** merged by IoU.
- Evidence: immutable raw model JSON and its exact parsed representation, image
  identities, model/revision/weights/projector hashes, runtime/build/executable
  hash, prompt/settings hashes, run ID and timestamp. `model.preview()` exposes
  per-item JSON pointers and image/region/run references. Confidence is not
  manufactured; current predictions have no calibrated probability.

`jacket`/`coat` map to outerwear; `dress` maps to one_piece. Category/role conflicts
are blocked, not automatically corrected. Skirt/shorts uncertainty is one item
with alternative categories, not two garments. A footwear pair may be one item;
separate shoe records require explicit grouping review. Off-frame footwear is a
visibility state, not an invented garment or an Unknown garment placeholder.
Material composition, brand, comfort and body measurements remain unassessed.

Validation checks internal consistency, **not visual truth**. A plausible region
does not prove a garment exists. Slightly different boxes can still describe the
same physical garment; the user must review the whole inventory, including
duplicates, real layers and missing items. An error-free schema is not accuracy.

## Correction and confirmation

`confirmation.py` defines `outfit-review-confirmation-1.0.0`. The intended UI flow:

1. Present the oriented photograph with item regions, categories, attributes and
   warnings; disclose that they are AI predictions.
2. Let the image owner select a target, correct a category/attribute, remove a
   false item, add a visibly missed item with its region, or mark a detail Unknown.
   For an uncertain type the owner may clear alternatives and retain Unknown;
   do not force a guess. Resolve garment identity/pair/layer questions explicitly.
3. Submit the expected review digest, replacement inventory and exact correction
   operations/reasons. `revise()` checks ownership/image binding, stale revisions
   and complete change coverage. Original AI output remains immutable.
4. Require explicit current-image inventory review before `confirm()`. Structural
   conflicts block confirmation. `provenance()` distinguishes unchanged reviewed
   AI fields from user-corrected fields. Corrections remain user assertions, never
   model verification or measured initial accuracy.

The API is pure and exercised using disposable fixtures. **No authenticated
confirmation endpoint/UI is implemented in this phase.** A future endpoint must
construct `Authority` from its authenticated session and the existing protected
media owner lookup; never accept it from client JSON. Digests detect content/link
changes but are not authentication/signatures: accept stored server records only,
not arbitrary client-supplied `Review`/`Confirmation` objects. Revalidate records
using `verify()` and confirmation validation. This is not wardrobe B0/B1 evidence.

Bounds: JPEG/PNG <=20 MiB, 25 megapixels, minimum 128px; 8 people, 24 items,
32 layer links, 24 identity questions, 4 alternatives/values, 64 KiB raw response,
16 correction revisions, 48 explicitly described changes per revision. No cache,
model loading or background worker is added. Reject malformed/unbounded output;
retain the original failed response in private evaluation artifacts.

## Reuse and preview

`images.prepare_image()` reuses Student 1's non-persisting EXIF/RGB decoder and
checks JPEG/PNG headers before decoding. It never calls media storage or garment
registration. For a future live upload, use existing protected-media validation
and ownership interfaces first; this pure helper does not authorize media access.

The current garment segmentation port and `DetectedGarment` can supply **optional
fallible supporting evidence** in a later experiment. They are not invoked here.
Do not substitute the development fallback for actual YOLO inference, treat a
missing detector box as absence, map empty-mask black defaults into clothing facts,
or automatically override the VLM. No new hybrid superiority is claimed.

Private offline region preview (from `backend`, using the existing environment):

```powershell
.venv\Scripts\python.exe scripts\preview_outfit_review.py observation.json photo.jpg NEW-preview.html
.venv\Scripts\python.exe -m pytest tests/test_outfit_review_observation.py -q
```

The preview embeds the photo; keep it private. It verifies exact image identity,
refuses overwrite, displays all proposals/warnings and cannot save confirmations.
It is a development artifact, not the final review page.

## Inference and accuracy gate

`model.py` supplies the frozen versioned prompt and pure output adapter. A separate
evaluator owns inference. Use the cached model/runtime, serialized requests,
`--cache-ram 0` and existing activity/job/memory guard. Do not auto-launch model
workers or affect Student 1 services. Fail closed on unavailable activity readings,
competing work, <512 MiB free VRAM or <2 GiB available RAM (8 GiB preload).

Measure raw garment recovery, unsupported claims, category correctness, attribute
coverage, target selection, latency and actual human correction counts separately.
Retain failed outputs. Exposed regressions and old H1/H2 labels are not a fresh
held-out benchmark. User-corrected outputs never enter initial-model accuracy.
Occasion-aware feedback can be prototyped only after explicit confirmation;
unattended fashion evaluation remains blocked on broader independent validation.

Phase 3E pilot outcome: one baseline H1 response and one revised H2 response were
completed before a contradictory category proposal stopped the frozen attempt.
No inference was retried. The consumer subsequently retained that contradiction
as a blocking review issue instead of discarding the complete proposal. The
revised output also called the human-labelled skirt shorts and left every colour
unknown. This experimental prompt has **not** demonstrated improved accuracy or
coverage and must not be treated as a production-ready observation approach.
