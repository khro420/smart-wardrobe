# AI Outfit Review — confirmation-first prototype

Phase 3G adds the guided garment editor, socks/shoes observation1.1 and conditional
model-anchored scoring. See [the updated workflow and rubric](AI_OUTFIT_REVIEW_SCORING.md).
The descriptive v1/basic-summary behavior documented below remains available as
the explicit CPU-only fallback; it is not labelled as model-generated assessment.

This independent page uses a photograph, not the saved wardrobe. Outfit Assistant,
its grammars/scoring/history, Student 1 extraction/VTON and existing media records
are unchanged. The prototype defaults **off**. No service is started on import.

## Local setup (existing main installation)

Reuse the approved cached **Qwen3-VL-4B-Instruct Q4_K_M**, matching F16 projector,
and **llama.cpp b12359/b1b770d90 CUDA12.4 Windows** bundle. No download, model
conversion or application dependency upgrade is automatic. Model/runtime hashes
are checked before loading. `psutil==7.2.2` is declared for worker supervision;
reuse the installed environment if it already satisfies it. Existing MiniLM and
spaCy assets/setup are reused on CPU, without external APIs or downloads.

The default model directory is
`%LOCALAPPDATA%\SmartWardrobe\model-cache\phase3b`, with the executable at
`cuda\llama-server.exe`. Override only if your approved bundle is elsewhere.

After stopping **only your owned backend**, start the same main backend with an
explicit process-local opt-in (do not start a second server on occupied 8000):

```powershell
cd "C:\Users\chong\Desktop\Smart Wardrobe\smart-wardrobe-clean\backend"
$env:SMART_WARDROBE_OUTFIT_REVIEW_ENABLED="true"
# Optional, only for a different already-approved cache location:
# $env:SMART_WARDROBE_OUTFIT_REVIEW_MODEL_DIR="C:\private\model-cache\phase3b"
# $env:SMART_WARDROBE_OUTFIT_REVIEW_LLAMA_SERVER="C:\private\model-cache\phase3b\cuda\llama-server.exe"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep your existing frontend on `http://localhost:3000`. A development frontend
picks up the new page/navigation. A production frontend needs its ordinary build
and owned restart to include source changes. Do not alter wardrobe storage paths,
replace databases, or start another application environment. Removing the opt-in
from the backend process disables the feature; this task does not edit live `.env`.

## Browser workflow

1. Sign in normally and open **AI Outfit Review** (`/outfit-review`). Use a photo
   you own or have permission to upload. Upload a JPEG/PNG <=10 MiB, >=128px per
   side, <=25 megapixels. The oriented preview strips EXIF metadata.
2. **Close games and other GPU-intensive work**, leave processing/VTON idle, then
   tick the GPU-availability acknowledgement and click **Analyze Outfit**. This
   explicitly starts actual inference; assets-present is not a readiness/accuracy
   guarantee. Status is polled, so long inference does not extend the proxy timeout.
3. Review the actual regions and inventory. Select the intended person. Correct
   category/role, colours, pattern, sleeve extent/rolled state; mark uncertain
   details Unknown. Remove false items; add genuinely visible missed items and
   set their true regions. Numeric coordinates are normalized 0..1000.
4. Resolve duplicate identities, footwear pairs, dangling/cyclic layers and all
   blocking issues. The model's proposals stay visible separately. Do not merge
   genuine layers simply because boxes overlap. If a crowd model improperly
   preselected your desired person, clear the selection and save, then explicitly
   select the person and save; the original contract requires a recorded user
   target-selection change. A clearer single-person photo is often preferable.
5. Save corrections with a reason, explicitly review the full inventory, then
   click **Confirm Outfit Details**. Confirmation means user review, not measured
   AI accuracy. Unknown clothing type is allowed; do not guess skirt/shorts/skort.
6. Enter one supported occasion and role/dress code where relevant, e.g.
   `I'm going to the library to study.` or
   `I have a job interview as a candidate in smart casual.` Click **Review My Outfit**.
7. Read the evidence-linked sections, limitations and suggestions. Editing the
   inventory invalidates confirmation; changing inventory/occasion hides stale
   results. The feature does not silently assume an interview/wedding dress code.

Some occasion phrasings and dress codes remain unsupported by the existing
interpreter. They request clarification, not a neutral fallback. Clothing-only
text is not a substitute for an occasion. Explicit garment/style conditions and
optional wishes are retained, but this prototype does not certify every such
requirement from a photograph. Materials, brands and hidden properties remain
unassessed. No body attractiveness/weight/shape evaluation is performed.

## Feedback and scoring limits

Feedback v1 is deterministic and grounded in the confirmed inventory. It reports
specific colours/patterns/layers, identifies missing information, and offers
conditional styling/venue checks. It is **not** a trained aesthetic critic or a
validated fashion-quality measurement. No second VLM feedback call is made.

`outfit-review-experimental-rubric-1.0.0` proposes occasion 40%, colour 25%, style
20%, pattern/layering 15%. Suitability/style measurement methods are not yet
validated; every numeric dimension and final score currently abstains:
**Not enough information to provide a reliable score**. Missing weights are never
redistributed; the Outfit Assistant R/C/P formula is not used.

## Security, temporary data and GPU isolation

- Dedicated `/api/v1/outfit-reviews` routes require a real signed bearer using the
  existing revocation-aware authentication. Development `X-User-Id` is refused.
  Authority comes from the stored owner and image digest, never client JSON.
- Raw photo, oriented preview, model output, corrections and feedback stay in
  bounded process memory: 15-minute fixed TTL, cleanup every 30 seconds, at most
  two reviews per owner/eight total, <=96 MiB photo bytes overall. No photo/media
  DB rows, garment registrations, review-history tables or migrations are created.
  A restart loses temporary reviews. Delete removes their retrievable state.
  Already-running work is bounded by startup/inference deadlines and cannot
  publish into a deleted/expired review. No permanent-save workflow is added.
- Owner-only photo/JSON responses use `no-store`. Photo preview is oriented PNG;
  the exact original remains private in temporary memory. Browser object URLs are
  revoked on leaving the page. Invalid raw outputs remain unconfirmed, temporarily
  viewable by their owner; technical logs are not exposed.
- One serialized review operation, the existing Student 1 GPU lock, read-only job
  state and actual GPU-engine sampling gate model execution. Idle CUDA presence
  alone is not treated as inference. Missing/stale/invalid readings fail closed.
- Retained floors: 8 GiB available RAM before load, 2 GiB during inference,
  512 MiB free VRAM; five quiet intervals, sustained competing backend activity
  or any active processing/VTON job stops only the owned review worker. This is
  monitored isolation plus user-confirmed availability, not an OS GPU reservation.
- GPU activity protocol 1.1 distinguishes a backend without a CUDA context from
  missing telemetry: zero activity is accepted only from a complete, fresh, valid
  GPU-engine inventory while process identity/job checks remain active. Missing,
  invalid or stale telemetry still refuses execution. Creating a CUDA context or
  running Student 1 inference just to pass this check is unnecessary.
- Fixed model settings: 16 GPU layers, CPU projector, `--fit off --cache-ram 0`,
  6144 context, 1024 image tokens, one slot, 180s startup and 300s inference bounds.
  There is no automatic retry/offload retuning. A Windows kill-on-close job owns
  the new model subtree; closing the backend also ends that model worker.
  Temporary monitor/native logs are removed after inference; no photo is written
  to those directories. All existing application processes are left alone.

Discord and video playback can continue during coding and CPU checks. They need
not be closed just to use the page. Before a new vision execution, measure current
headroom and competing activity; if the 8 GiB preload gate fails, defer analysis
or deliberately free resources. Do not lower the gate or promise uninterrupted
video playback during GPU inference from a single utilization sample.

## Focused verification

```powershell
# backend (existing environment, disposable pytest storage)
.venv\Scripts\python.exe -m pytest tests/test_outfit_review_observation.py tests/test_outfit_review_prototype.py tests/test_outfit_review_occasion.py -q
# frontend
node_modules\.bin\tsc.cmd --noEmit --incremental false
node_modules\.bin\eslint.cmd components/OutfitReview.tsx lib/outfit-review.ts app/outfit-review/page.tsx
node_modules\.bin\playwright.cmd test --config=playwright.outfit-review.config.ts
```

The browser checks reuse the existing frontend and intercept **all** API calls;
their inference/results are fixtures, not recognition evidence. Chromium runs
with `--disable-gpu`. The CPU occasion tests use the installed MiniLM/spaCy assets.
Real vision testing is separate and requires closing games plus explicit GPU
availability confirmation before each new GPU evaluation session. Never claim
user-corrected inventories as initial model accuracy. H2's lower-garment subtype
remains unresolved under the separate reviewer clarification; exclude it from
definitive subtype-accuracy denominators until independently resolved.
