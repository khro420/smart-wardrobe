# Garment workflow handoff

This handoff records the completed **Objective O1: Smart Wardrobe and Garment
Understanding** scope from Khor Hua Sheng's report. All 25 mapped requirements
(FR-01–FR-05, FR-10–FR-24, FR-37–FR-39 and AIR-01–AIR-02) have executable evidence.
It does not claim that every Objective O2 report requirement passed or that the wider
subsystem is complete. Existing shared
authentication and the already integrated recommendation boundary are used where O1
requires them; no model was retrained during this completion pass.

## O1 completion status

Status on 2026-09-05: **complete — 25/25 mapped requirements passed**.

- The wardrobe now supports garment and outfit browse, search, allowlisted sort,
  category/favourite filters and outfit creation-type filtering.
- Garment editing covers the report-permitted name, category, primary colour,
  pattern, fit, style, material and custom tags. Outfit editing covers name,
  description, favourite state, ordered membership and ownership revalidation.
- Archive is owner-scoped, preceded by a dependency preview and explicit browser
  confirmation, and blocked while an active outfit or unfinished visualisation
  depends on the record. Outfit membership replacement and archives are atomic.
- Capacity was exercised in an isolated runtime at 500 garments, 1,000 outfits and
  2,000 memberships for one user without a schema change or integrity failure.
- Existing YOLO weights and held-out DeepFashion2 results were preserved. The full
  32,153-image conversion audit, 13-category metrics and 20 labelled failure examples
  remain the AIR-01/AIR-02 evidence.

The machine-readable requirement matrix is
`storage/verification/o1/requirements-audit.json`, mirrored at
`backend/runs/o1/requirements-audit.json`. Reproduce the capacity and consolidation
steps with `backend/scripts/verify_o1_capacity.py` and
`backend/scripts/audit_o1_requirements.py`; the browser workflow remains
`backend/scripts/verify_browser_workflow.py`.

## Run the working demo

From the repository root, open two PowerShell terminals. Use the Python environment
that contains the project's dependencies and GPU-compatible PyTorch installation.

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

Open http://localhost:3000/auth, register or sign in, then open `/extract`.
The UI calls `/api/v1` on its own origin; Next.js proxies those requests to
`http://127.0.0.1:8000`. This also avoids a phone browser interpreting `localhost`
as the phone's backend. Restart Next.js when changing proxy configuration.

For first-time installation, use `python -m pip install -r requirements.txt`
inside `backend` and `npm ci` inside `frontend`. Preserve the working GPU PyTorch
environment; the installed nightly CUDA build used for verification is recorded
in the segmentation evidence rather than replaced by this task.

`SMART_WARDROBE_BACKEND_URL` changes the Next.js server's proxy destination.
`NEXT_PUBLIC_API_URL` remains an optional explicit browser API override; leave it
unset for the default same-origin setup. A plain Uvicorn invocation reads process
environment variables, not `backend/.env` automatically. If using that file, install
`python-dotenv` and pass `--env-file .env` to Uvicorn.

The acceptance walkthrough uses isolated state at `storage/workflow-demo`, backend
port 8001 and UI port 3001. To reproduce that setup:

```powershell
# Backend terminal, from backend/
$env:SMART_WARDROBE_DATA_DIR = 'C:/Users/khorh/smart-wardrobe/storage/workflow-demo'
$env:SMART_WARDROBE_AI_MODE = 'production'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```powershell
# UI terminal, from frontend/
$env:SMART_WARDROBE_BACKEND_URL = 'http://127.0.0.1:8001'
$env:SMART_WARDROBE_BUILD_DIR = '.next-verification'
npm run dev -- --port 3001
```

## Demonstration steps

1. Register a private account or sign in at `/auth`.
2. Open Add from image from the wardrobe, or Add an outfit in the navigation.
3. Upload a JPEG/PNG. An existing local example is
   `backend/datasets/deepfashion2_yolo_seg/images/validation/000001.jpg`.
4. Wait for the job to reach `review_required`. Each detection has its own retained
   crop, predicted category and confidence. Open the details to inspect its
   source-space mask and bounding box.
5. Compare the retained segmentation crop with the transparent, centred 512 x 512
   standardised garment and choose which representation to save. Correct the name,
   category, colour and optional manual attributes. Explicitly accept each desired
   candidate; reject unwanted or overlapping predictions.
   Accepting one candidate does not accept any other candidate.
6. Save selected garments, or enter an outfit name and Save as outfit. Pending and
   rejected candidates are excluded. Edited details must be applied before saving.
7. Refresh the wardrobe. Garments remain stored with their chosen media and edits.
   Outfit saving also creates the confirmed constituent garments and memberships.
8. Reopen a completed job: it shows the saved state and no save controls. Repeating
   the API confirmation returns a conflict without inserting duplicates.

The model can predict overlapping categories for the same clothing region. The
provided sample deliberately demonstrates that review and rejection are necessary.
Multiple predictions do not prove that each prediction is a distinct true garment.

## Report alignment for this slice

Source: `RSW_KhorHuaSheng_Project 1.pdf`. Printed page numbers are one less than PDF
page numbers in the inspected sections. The figures were rendered and inspected,
including Figures 4.4, 4.8, 4.13, 4.14, 4.16 and 4.17, plus Tables 4.4 and 4.5.

| Report requirement or design | Implementation and evidence |
| --- | --- |
| FR-01–03: shared upload and decoded validation | Both wardrobe entry contexts reach `/extract`; byte limits, decoded JPEG/PNG format, declared MIME agreement, minimum dimensions and a 25 MP maximum are validated before a job is created. Orientation is normalised and EXIF is removed. Invalid-upload tests run after importing the actual model library. |
| FR-04–05; §4.10.1: instance segmentation | Existing `models/cv/best.pt` is used through `GarmentSegmentationPort`. `DetectedGarment` carries category, confidence, source-space box, PNG mask and individual PNG crop. Native source-space masks avoid letterbox stretching. Invalid/empty masks, boxes, unsupported categories and low-confidence predictions are excluded. Real-weight smoke evidence covers three validation images. |
| FR-06, 12: VTOFF representation and review | The original tight RGBA segmentation crop is retained unchanged. `TryOffDiffAdapter` conditions the official multi-garment TryOffDiff v2 model on the original worn-person image and predicted garment category, then stores a separate generated asset. Crop, mask and source references remain provenance; the crop remains the safe default. The UI labels VTOFF as synthetic, warns that hidden details may be invented, and requires explicit selection. Missing assets, unsupported classes and inference failures fall back to the crop. |
| FR-07–09, 11: structured, editable representation | Category/role/layering and masked colour analysis are retained. Fit, style and material default to unavailable; the user can supply these, pattern and tags. Predicted category/confidence remain evidence; corrected category is stored separately until confirmation. Embeddings remain unavailable, with dimensional/non-finite validation in place. FR-07 is therefore partial. |
| FR-10–16; Figure 4.17; §4.10.4 | Candidate summary rows have previews and expandable review details. One decision updates one candidate. Accepted selections save as garments or one outfit in one transaction. Empty/duplicate selections and unavailable preferred media are rejected. Failure-injection and concurrent-confirm tests prove rollback and duplicate prevention. |
| FR-17, 19–21; Tables 4.4–4.5 | Confirmed garments and outfits are separate owner-scoped collections. Manual outfits preserve selected garment order. Both collections expose search, allowlisted sort and supported filters. Temporary candidates are not wardrobe records. New-process/database tests verify committed persistence; bearer-token and dependency-endpoint tests verify cross-user denial. |
| FR-22–24 | Garment and outfit fields, favourite state and ordered outfit membership are editable with ownership revalidation. Dependency preview identifies active outfits and queued/processing visualisations before archive. Unsafe removal is blocked; otherwise the browser requests explicit confirmation before owner-scoped soft archive. |
| FR-37–39: failure, traceability, cancellation | Conditional job transitions preserve cancellation during inference. Repeated job execution cannot generate another candidate set. Internal errors are logged but API messages are controlled. Interrupted queued/processing jobs become failed on restart; review-ready/completed records persist. The local runtime supports one API process. |
| Figure 4.4: responsibility and value-object boundaries | `ProcessingJobService` owns create/get/cancel/restart recovery; `GarmentProcessingOrchestrator` coordinates model adapters; `ReviewService` owns correction and preferred-media choice; `ConfirmedGarmentWriter` delegates saving to wardrobe. Segmentation and standardisation return model-independent value objects. Logical diagram operations are represented by Python service modules, adapter classes and protocols. |
| Figure 4.8: package/dependency structure | The existing `api`, `application`, `domain`, `infrastructure`, `shared_contracts` layout is retained. Author-owned garment/wardrobe application services depend on injected ports; the composition root binds concrete media, database and AI adapters. Domain types do not import FastAPI, SQLite or YOLO. An AST-based test checks these dependency constraints. |
| Figure 4.13: deployment boundaries | Next.js remains in `frontend`, FastAPI in `backend/app`, and GPU inference behind backend AI adapters. Media is private backend storage. PostgreSQL 16 + pgvector was verified through an ephemeral local Compose deployment; SQLite remains the explicitly identified application compatibility store for the local demo. |
| Figure 4.14; Tables 4.4–4.5: data relationships | Jobs reference source media; candidates retain box, mask/crop/optional VTOFF/preferred-media references and embedding availability; unique garment-to-candidate linkage prevents duplicate conversion; outfit membership stores role and order. Media dimensions and original filename are recorded. Confirmed representation maps into `secondary_colour`, `style_tags`, `custom_tags`, `structural_scores`, `additional_attributes` and `embedding`. Local column names such as `id`/`job_id` map to the report's logical identifiers; JSON is used for vectors/JSONB fields in SQLite. |
| NFR-03–08: ownership, privacy, recovery and UI | Protected media requires authentication and ownership. Invalid uploads do not create jobs. Request failures are readable; image failures have retry controls. Desktop (1440 px) and mobile (390 px) browser walkthroughs pass. This does not claim a full WCAG audit or all report performance targets. |

## Verification

Verified on 2026-09-05: **38 backend tests passed**, frontend lint passed, and the
default Next.js production build (Turbopack) passed. The final real-model browser
walkthrough passed with no page errors or image-sizing warnings. Tests include
transaction rollback, concurrent confirmation, bearer-token ownership, committed
data read from a fresh interpreter, malformed uploads after YOLO import, mask/crop
geometry, package-dependency boundaries, collection querying, complete permitted
edits, atomic outfit membership replacement and dependency-aware archive policy.

```powershell
# From backend/
python -m unittest discover -s tests -t .
python scripts/verify_o1_capacity.py
python scripts/audit_o1_requirements.py
python scripts/verify_segmentation.py
python scripts/verify_vtoff_standardisation.py --limit 15  # deterministic baseline only
python -m pip install -r requirements-vtoff.txt
python scripts/setup_vtoff.py
python scripts/verify_vtoff_inference.py --steps 20
```

```powershell
# From frontend/
npm run lint
npm run build
```

For the browser walkthrough, install `backend/requirements-dev.txt` into the chosen
development environment and use an installed Microsoft Edge browser. With the
isolated demo running:

```powershell
# From backend/
python scripts/verify_browser_workflow.py
```

The browser script creates a unique demo account. It verifies registration,
real-model upload, separate previews, candidate-specific decisions, complete garment
edits, collection controls, manual outfit editing, dependency-aware confirmed
archive, both saving modes and completed-job behavior. Generated evidence is private
and excluded from Git:

- `storage/verification/o1/requirements-audit.json`
- `storage/verification/o1/capacity.json`
- `storage/verification/o1/browser/browser-workflow.json`
- `storage/verification/o1/browser/review-desktop.png`
- `storage/verification/o1/browser/review-mobile.png`
- `storage/verification/o1/browser/wardrobe-desktop.png`
- `storage/verification/o1/browser/wardrobe-o1-complete.png`
- `storage/verification/segmentation/results.json` and per-candidate masks/crops
- `storage/verification/vtoff_standardisation/results.json` and 15 labelled pairs
- `storage/verification/vtoff/smoke/results.json` and a labelled real-model comparison
- `storage/verification/workflow-latency.json`

The real-weight smoke run used an NVIDIA GeForce RTX 5060 Laptop GPU, `cuda:0`,
Ultralytics 8.4.70, PyTorch 2.12.0.dev20260408+cu128, NumPy 2.4.6 and OpenCV 4.14.0.
The weight SHA-256 is
`2d162cc52e69e526e715a883ab67dcabba7470a29cc6d9af51558eeaf8de49c0`.
Three samples produced 3, 2 and 1 candidates. These smoke timings and memory figures
are recorded in the JSON; they are not dataset accuracy or load-test results.

## Held-out segmentation evaluation (AIR-01–02)

The existing `backend/models/cv/best.pt` weights were evaluated without
retraining against the converted DeepFashion2 `validation` split. The conversion
audit checked all 32,153 source annotations, converted images and label files:
49,523 expected instances exactly matched 49,523 emitted instances, with no
malformed labels, missing files, or count mismatches. There are 1,812 valid
background/empty-label images in the split.

| Metric | Box | Mask |
| --- | ---: | ---: |
| Precision | 0.6981 | 0.6785 |
| Recall | 0.7699 | 0.7617 |
| mAP@0.50 | 0.7531 | 0.7324 |
| mAP@0.50:0.95 | 0.6455 | 0.5596 |

Per-category metrics, the full audit, Ultralytics plots and 20 labelled
false-positive/false-negative examples are saved in
`storage/verification/segmentation/held_out_evaluation/` and
`backend/runs/held_out_segmentation/metrics/`. The evidence sample uses a fixed
seed over 1,000 held-out images. Common classes perform strongly (for example,
shorts box/mask mAP@0.50 of 0.9337/0.9312), while rare `short_sleeve_outwear`
is the weak class (0.2479/0.1804). The failure images show missed garments and
top/bottom-versus-dress/outerwear confusions in multi-garment, outdoor and
occluded examples. This is a held-out model evaluation, not a claim of
deployment accuracy for unrestricted user photographs.

## VTOFF reconstruction and deterministic baseline (AIR-03–04)

The production boundary now distinguishes two different operations. The tight
transparent crop is observed YOLO segmentation evidence. `TryOffDiffAdapter` is a
genuine diffusion reconstruction using the official pinned multi-garment v2
checkpoint, a SigLIP image encoder and Stable Diffusion VAE. It conditions on the
full worn-person image and category, not the transparent crop. Generated RGB
output is stored separately with model revision, seed, steps, guidance, latency,
peak VRAM and all evidence-media references. It is never selected automatically.

The older 512 x 512 alpha-mask centring transform remains only as a deterministic
segmentation baseline under `segmentation_standardisation.py`. It cannot infer
occluded regions and is no longer stored or presented as VTOFF output.

A real cold-start smoke run used DeepFashion2 validation image `000001.jpg`, a
YOLO `sling_dress` prediction (confidence 0.782), seed 42, guidance 2.0 and 20
diffusion steps. It produced a 512 x 512 RGB reconstruction in 30.24 seconds with
2,215,769,600 bytes (2.06 GiB) peak allocated VRAM on the RTX 5060 Laptop GPU.
The labelled comparison and machine-readable provenance are saved under
`storage/verification/vtoff/smoke/` and `backend/runs/vtoff/smoke/`. Qualitatively,
the model reconstructed a full black suspender-style dress, but invented garbled
white graphic detail. This is direct evidence for the synthetic warning and
mandatory user review; it is not a paired AIR-03 quality score.

A paired upper-body evaluation is now also present. The official VITON-HD archive
was checked for its exact byte size, CRC integrity, safe member paths and decodable
images. Only `test/image` and `test/cloth` were extracted. The 42 duplicate/leaked
test names published by TryOffDiff were excluded, leaving 1,990 complete one-to-one
pairs and zero unpaired examples. The archive SHA-256 is
`d6acbe1d6e3573e33e27a322f59efd480c5d180c8c87576718430cf20439dfe0`.

The pinned model was evaluated on a fixed-seed random sample of 30 cleaned pairs
(sample seed 20260905; generation seed 42; 20 steps; guidance 2.0). This is a
development evaluation slice, not a paper-comparable full-test score.

| Metric | TryOffDiff v2 | Observed segmentation baseline |
| --- | ---: | ---: |
| SSIM (higher is better) | 0.8192 | 0.7475 (n=29) |
| LPIPS (lower is better) | 0.2997 | 0.4221 (n=29) |
| DISTS (lower is better) | 0.2557 | 0.2556 (n=29) |
| Subset FID | 86.0155 | not computed |
| Subset KID | -0.00246 | not computed |

On the 29 pairs with a YOLO upper-garment crop, generation won 27 SSIM, 26
LPIPS and 16 DISTS comparisons. Mean paired differences were +0.0701 SSIM,
-0.1207 LPIPS and +0.00019 DISTS, so VTOFF improves overall product-like
appearance but does not improve DISTS in aggregate. FID/KID at n=30 are recorded
only as indicative diagnostics; the negative KID estimate is possible on a small
unbiased subset and is not evidence of a perfect model.

The 12 worst metric-ranked examples were inspected and labelled. Recurring failures
are illegible or missing logo text, displaced/smoothed prints, loss of layered or
sheer construction, colour shifts, and changed neckline, sleeve, width or hem
geometry. Median warm inference was 8.46 seconds, mean latency 9.05 seconds and
maximum allocated VRAM was 2,267,650,048 bytes. Results, per-pair records and
labelled sheets are under `storage/verification/vtoff/paired_evaluation/` and
`backend/runs/vtoff/paired_evaluation/`; the audit is in
`storage/verification/vtoff/paired_dataset_audit.json` and mirrored under runs.

The runtime offer policy is therefore deliberately conservative. VTOFF is withheld
when model assets are unavailable, the category is unsupported, segmentation
confidence is below 0.50, or inference/output validation fails. A generated result
is only an optional reviewed alternative: the observed crop remains selected by
default. Segmentation confidence and generated LPIPS were almost uncorrelated in
this sample (Pearson r=-0.099), so confidence is only a category-reliability gate;
it must not be represented as a hallucination or fidelity detector.

The reproducible real-weight check generated 15 labelled comparison pairs from the
DeepFashion2 validation images without retraining or changing `best.pt`.

| Verification invariant | Result |
| --- | ---: |
| Separate original and standardised assets | 15/15 |
| Transparent 512 x 512 PNG | 15/15 |
| Longest alpha-mask edge is 448 px | 15/15 |
| Horizontal/vertical centring error is at most 1 px | 15/15 |

Per-pair source image, category, confidence, dimensions, mask bounds and SHA-256
values are recorded in `storage/verification/vtoff_standardisation/results.json`
and `backend/runs/vtoff_standardisation/results.json`. Labelled side-by-side images
are under `storage/verification/vtoff_standardisation/pairs/`. These results prove
only the deterministic segmentation baseline; they do not measure learned
product-image reconstruction or a full virtual try-on system.

## Remaining report work

- Additional dataset slices, independent real-user-photo evaluation and model
  improvement for weak categories remain optional future work. AIR-01–02 now has
  a held-out conversion audit, precision/recall, box/mask AP, per-category
  metrics and labelled failure evidence; the model was not retrained.
- Extend AIR-03 from the completed 30-pair VITON-HD development slice to the
  lower-body and dress groups. VITON-HD only validates upper-body garments.
  `prepare_dresscode_vtoff_evaluation.py` now audits only official paired test
  manifests, and `evaluate_vtoff_paired.py` supports fixed-seed stratified
  upper/lower/dress evaluation, but the authors' access-controlled DressCode
  dataset has not been supplied. No unofficial mirror is accepted. DressCode
  generation caches are tied to model hash, source/target hashes, group,
  category, seed, steps and guidance; mismatches require explicit regeneration.
  The evaluator writes a failure-label template and remains `review_pending`
  until all selected failures have substantive visual labels. The old 15
  mask-centering pairs remain baseline evidence and must not be reported as
  generative quality evidence.
- PostgreSQL + pgvector verification is complete. The live PostgreSQL 16 run loaded
  the `vector` extension, confirmed both columns as `vector(768)`, transactionally
  round-tripped 768 dimensions through `processing_item` and `garment`, and rolled
  the verification records back. Evidence is in
  `storage/verification/pgvector/results.json`.
- Full VTON generation, evaluation and visualisation-specific requirements. The
  existing development VTON implementation is outside this slice and remains a
  labelled copy of the personal image.
- Durable multi-worker AI execution, full capacity/coverage measurement and a
  complete accessibility audit. Cancellation is logically safe; it does not
  pre-empt a GPU call already in progress. Interrupted visualisations and jobs
  are now marked failed on restart; aged unreferenced intermediate media can be
  inspected or archived with `backend/scripts/cleanup_orphaned_media.py`, and
  `backend/scripts/benchmark_workflow.py` records repeatable single-process
  latency smoke evidence. The UI now includes skip navigation, visible keyboard
  focus, semantic navigation state, labelled upload controls and live status
  announcements. These are not a replacement for multi-worker/load or full
  WCAG evaluation.
- Advanced NLP/ML recommendation evaluation remains outside this slice. The
  persisted request, recommendation, preference-aware scoring, save-as-outfit,
  and recommendation-to-visualisation workflows are implemented in this
  repository.

This document records scoped report alignment and known gaps. It is not a claim
that every feature and acceptance target in the complete FYP report is finished.

## O2 scoped closure handoff (2026-09-06)

The O2 delivery is closed at **11/12 evidence groups passed plus 1/12 explicitly
user-deferred**. AIR-03 lower-body/dress evidence is not passed and must not be
described as evaluated; it is deferred until official DressCode access. There are
no other incomplete delivery gates.
Machine-readable status is stored in
`storage/verification/o2/requirements-audit.json` and
`backend/runs/o2/requirements-audit.json`.

Completed O2 work:

- A pinned `google/siglip-base-patch16-512` vision encoder produces real finite,
  L2-normalised 768-D embeddings with versioned white-alpha/pad preprocessing.
  On 104 held-out DeepFashion2 polygon crops (8 per category), leave-one-out
  category retrieval achieved 47.12% top-1 accuracy, 46.59% macro F1, 0.2635
  mean precision@5 and 0.6011 MRR. This is a small category-retrieval audit, not
  recommendation-ranking evidence. Vectors persisted identically from processing
  item to confirmed garment while the segmentation crop remained preferred. The
  regenerated manifest explicitly records Windows build, Intel CPU, 32 logical
  CPUs, NVIDIA GeForce RTX 5060 Laptop GPU, 8.55 GB device memory, CUDA 12.8,
  terminal status and an empty error list.
- AIR-05 uses 39 prediction-hidden, single-reviewer labels spanning all 13
  categories. Colour temperature achieved 89.74% accuracy and 87.48% macro F1.
  Coarse primary colour achieved only 35.90% accuracy/13.48% macro F1, and
  single-colour dominance 38.46% accuracy/38.10% macro F1. Those low results are
  retained as evidence, not tuned away. Colour, temperature and dominance are
  editable suggestions; fit, style, material, pattern and tags also remain
  explicitly user-reviewable. Twelve labelled attribute failures are retained.
- The recommendation-facing `ConfirmedGarmentQuery` adapter returns opaque IDs
  only for the caller's confirmed, available garments. Recommendation resolution,
  saving and visualisation reject foreign or archived membership. Internal NLP
  and ranking remain outside O2.
- The paired VITON-HD and AIR-05 manifests now carry explicit terminal status,
  error arrays and measured CPU/GPU/OS hardware fields. The O2 auditor verifies
  those fields before AIR-07 can pass; it no longer relies on hardware prose.
- The relevant release checks pass: 45 backend tests, including fail-closed
  DressCode licence/structure/group-sampling checks, frontend lint and the
  Next.js production build. A `pytest.ini` confines discovery to `backend/tests`
  so model and dataset trees are not scanned.
- FR-09 now has live PostgreSQL 16 + pgvector evidence: the extension and report
  tables loaded, both embedding columns reported `vector(768)`, and transactional
  inserts round-tripped 768 dimensions through `processing_item` and `garment`.

Deferred report work:

1. Obtain DressCode from the official authors under their agreement, place it at
   `backend/datasets/dresscode`, and run the prepared audit/evaluator to produce
   lower-body and dress paired metrics plus reviewed failure labels.

This user-approved scoped closure is not an AIR-03 pass. Do not substitute an
unofficial DressCode mirror, count the deterministic mask-centering baseline as
VTOFF, describe lower/dress evaluation as completed, or describe the weak
colour/dominance outputs as reliable automation.
