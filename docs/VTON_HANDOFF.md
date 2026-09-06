# VTON implementation and acceptance handoff

## Implemented scope

The local academic prototype implements single-garment virtual try-on for the
eleven DeepFashion2 top, bottom and dress classes. A source containing multiple
garments is rejected because the selected CatVTON checkpoint does not establish
outfit-level multi-garment compositing. The two outerwear classes are also
rejected because the original checkpoint and automatic-mask contract do not
provide enough evidence for reliable layering in this project.

The runtime uses the original Stable-Diffusion-based CatVTON mix checkpoint at
768 × 1024 in BF16. It does not use CatVTON-FLUX or the mask-free variant.

| Asset | Pinned identity | Licence/use constraint |
| --- | --- | --- |
| CatVTON source | commit `7818397f25613beedb3d861a34769f607cfcf3b1` | CC BY-NC-SA 4.0; academic/non-commercial use only, attribution and share-alike apply |
| CatVTON mix weights | HF revision `2969fcf85fe62f2036605716f0b56f0b81d01d79` | CC BY-NC-SA 4.0 |
| Stable Diffusion 1.5 inpainting UNet/scheduler/safety checker | HF revision `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb` | CreativeML OpenRAIL-M use restrictions apply |
| SD VAE FT-MSE | HF revision `31f26fdeee1355a5c34592e401dd41e45d25a493` | MIT |
| DressCode | user-supplied official test-set copy | Access-controlled; obtain and use only under the authors' agreement; never redistribute through this repository |

Vendored source is at `backend/vendor/CatVTON/` with its licence. Checkpoints
are deliberately ignored by Git. `setup_vton.py` downloads the exact revisions,
hashes every file and creates `backend/models/vton/manifest.json`. Inference
verifies all hashes and required files before loading and receives only local
paths, so an API request cannot silently fetch or change model assets.

## Input and output contract

`POST /api/v1/visualisations/prepare` accepts exactly one owner-scoped
`outfit_id` or `recommendation_id`. It returns the resolved source type and ID,
one supported garment, its reviewed protected `source_media_id`, the mapped
CatVTON category (`upper`, `lower`, or `overall`), and person-photo guidance.

`POST /api/v1/visualisations` adds one available owner-scoped
`person_image_id`. Within one transaction it creates a queued request and a
`visualisation_item` snapshot containing the garment ID, exact protected media
ID, category, role, and order. The request snapshots the person media ID and
generation configuration. Queue capacity defaults to eight.

The model adapter receives:

- decoded, EXIF-normalised RGB person pixels fitted to 768 × 1024;
- decoded garment pixels alpha-composited on white and aspect-padded to
  768 × 1024;
- CatVTON automatic masks produced by the pinned DensePose and SCHP weights;
- 50 DDIM steps, guidance 2.5, deterministic seed 42, and BF16 precision.

The adapter must return a decodable 768 × 1024 PNG, a model version, latency,
output kind, and runtime metadata. Generated outputs that are flat colour or
pixel-identical to the prepared person input fail closed. A technically valid
file is stored as owner-scoped protected media before a conditional
`processing → completed` update. Failed or cancelled records never expose an
output media ID. Development mode remains visibly labelled as a copied fallback
and is not accepted as real VTON evidence.

Supported category mapping:

| CatVTON mode | DeepFashion2 categories |
| --- | --- |
| `upper` | `short_sleeve_top`, `long_sleeve_top`, `vest`, `sling` |
| `lower` | `shorts`, `trousers`, `skirt` |
| `overall` | `short_sleeve_dress`, `long_sleeve_dress`, `vest_dress`, `sling_dress` |

## Setup and operation

Use the existing CUDA environment so its working Torch and torchvision builds
are preserved. Install only the additive CatVTON preprocessing packages:

```powershell
cd backend
python -m pip install -r requirements-vton.txt
python scripts/setup_vton.py
```

Production uses `SMART_WARDROBE_AI_MODE=production` and
`SMART_WARDROBE_VTON_ENABLED=auto`. With `auto`, a missing manifest returns the
controlled `unavailable` result. Useful overrides are
`SMART_WARDROBE_VTON_DEVICE`, `SMART_WARDROBE_VTON_QUEUE_LIMIT`,
`SMART_WARDROBE_VTON_STEPS`, `SMART_WARDROBE_VTON_GUIDANCE`, and
`SMART_WARDROBE_VTON_SEED`. The documented image size and BF16 precision are
fixed by the domain contract.

Run a real smoke test with an authorised person image and garment image:

```powershell
python scripts/verify_vton_inference.py --person path/to/person.png --garment path/to/garment.png --category short_sleeve_top
```

The script writes output plus model, configuration, input hashes, latency, peak
VRAM, GPU, CUDA, OS, status, and controlled errors under
`storage/verification/vton/smoke/`.

For category-balanced paired evaluation, first prepare a locally licensed
DressCode manifest with the existing audit command, then run:

```powershell
python scripts/prepare_dresscode_vtoff_evaluation.py --dataset-root path/to/DressCode --license-confirmed
python scripts/evaluate_vton_paired.py --per-group 10
```

The evaluator selects ten paired test cases per upper-body, lower-body, and
dress group with a fixed seed. It records per-example SSIM, LPIPS, DISTS,
latency, peak VRAM and file hashes, plus aggregate metric summaries and hardware.
These reconstruction metrics and qualitative review establish bounded image
quality; they do not establish garment sizing or physical-fit accuracy.

## File-specific implementation map

| Responsibility | Files |
| --- | --- |
| Stable contracts and category policy | `backend/app/domain/value_objects/visualisation_plan.py`, `generated_visualisation.py` |
| Model-independent boundary and composition | `backend/app/application/ports/vton_port.py`, `visualisation_repository.py`, `backend/app/infrastructure/workflow_runtime.py` |
| Pinned CatVTON and preprocessing | `backend/app/infrastructure/ai/catvton_runtime.py`, `vton_adapter.py`, `vton_preprocessing.py`, `gpu_runtime.py` |
| Source/person validation and lifecycle | `backend/app/application/visualisation/outfit_identifier_validator.py`, `personal_image_service.py`, `outfit_visualisation_service.py`, `visualisation_result_service.py` |
| API | `backend/app/api/visualisation_routes.py`, `backend/app/domain/value_objects/requests.py` |
| Persistence | `backend/migrations/002_vton_runtime_metadata.sql`, `backend/app/infrastructure/persistence/postgresql_repository.py` |
| Web flow | `frontend/app/try-on/page.tsx`, `frontend/app/try-on/result/page.tsx`, `frontend/app/history/page.tsx`, `frontend/lib/api.ts` |
| Setup and evidence | `backend/scripts/setup_vton.py`, `verify_vton_inference.py`, `evaluate_vton_paired.py`, `audit_o3_requirements.py` |
| Regression tests | `backend/tests/test_vton_contracts.py`, `backend/tests/test_workflow.py` |

## Acceptance matrix

The functional implementation covers FR-18 and FR-25–FR-39 plus AIR-06. The
auditor records these separately and refuses to treat missing real-model
evidence as completion.

| Requirement | Implementation acceptance | Evidence gate |
| --- | --- | --- |
| FR-18, FR-25 | Persisted recommendations and every named visualisation entry point use the same source contract | Backend tests, frontend lint/build, history UI |
| FR-26 | Whole source rejected for unknown, duplicate, unavailable, unreviewed, unowned, multi-garment, outerwear, or missing media | `test_vton_contracts.py` |
| FR-27–FR-31 | Available owner images only; upload/selection; decoded byte/format/resolution/ownership validation; protected storage | API tests and protected-media service |
| FR-32 | Frozen person and garment media reach real CatVTON | Real smoke result must be `complete` |
| FR-33–FR-36 | All lifecycle states, owner-only completed output, explicit AI/fit notice, retry creates a new record | Tests, result UI lint/build |
| FR-37–FR-39 | Fail-closed completion, persisted provenance/errors/timestamps, safe idempotent cancellation | Tests and migration audit |
| AIR-06 | Named entry points use confirmed reviewed media and retain the physical-fit disclaimer | Tests and built web flow |
| AIR-07, NFR-02, NFR-12 | Pinned model/config/preprocessing/dependencies/seeds plus measured RTX 5060 latency/VRAM and category evidence | Real smoke plus licensed DressCode evaluation |

Generate the authoritative JSON matrix after release checks:

```powershell
python -m pytest -q --junitxml=runs/o3/pytest.xml
python scripts/audit_o3_requirements.py --frontend-lint-pass --frontend-build-pass --allow-incomplete
```

`--allow-incomplete` writes the honest matrix while real-model or DressCode
evidence is absent. Omit it for a release gate that must fail until every O3 row
passes.

## Hardware boundary and remaining evidence

CatVTON documents under 8 GB VRAM at 1024 × 768. The real smoke run on this
machine's RTX 5060 Laptop GPU completed the 50-step BF16 generation in 66.528
seconds with 5,271,428,096 bytes peak allocated VRAM; total wall time including
model and preprocessing load was 101.598 seconds. The GPU reports 8,546,484,224
bytes total memory, so the selected batch-one profile is feasible with limited
headroom. All AI adapters share one process-wide GPU slot; VTON stays queued
until it owns that slot and maps CUDA OOM to a controlled terminal error. The
machine-readable authority is `storage/verification/vton/smoke/results.json`.

The implementation and real upper-body smoke inference are complete without
DressCode. A complete evaluation claim across
upper, lower, and dress remains blocked until the user supplies DressCode under
the authors' official agreement and the category-balanced evaluation finishes.
No dataset content is downloaded, copied, or committed by the repository.
