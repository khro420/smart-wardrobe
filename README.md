# Smart Wardrobe — Windows handover

One FastAPI backend, one Next.js frontend, and SQLite for the runnable local app.
PostgreSQL/pgvector deployment migrations remain in `backend/migrations/`;
PostgreSQL is **not** required for this setup.

## After pulling

Install Python3.12 (tested3.12.10, with the Windows `py` launcher), Node.js24 LTS
(tested24.19.0, npm included) and Git. From this checkout:

If this PC already has a wardrobe, stop its services and back up its storage
privately before pulling. Keep local changes; if Git refuses the pull, reconcile
them rather than resetting. The old tracked credential-bearing seed is removed
from the new Git tree; retain any needed private copy outside the checkout.
The active existing database is not replaced by setup.

```powershell
git pull --ff-only origin main
powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Windows.ps1 -Mode CPU
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Windows.ps1
```

Setup installs `backend/.venv`, pinned CPU dependencies and `npm ci`, then prompts
for a **new local password**. No shared password is published. Sign in as
**khorhs2004@gmail.com** with that new password at **http://localhost:3000**.
Backend health: **http://127.0.0.1:8000/health**. Select **My wardrobe**.
If Python is not registered with `py`, pass
`-PythonExe "C:\path\to\Python312\python.exe"`. Add `-WithTests` for focused
pytest dependencies. No environment activation or reinstall is needed after
reopening VS Code; run Start-Windows again.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Windows.ps1 -Stop
```

Stop affects only launcher-owned process identities. Occupied ports are refused,
not killed. Logs are in `storage/launcher/`. The frontend uses the same-origin
`/api/v1` proxy. Its bounded local transport window supports slow verified work;
it is not a performance acceptance claim.

## Included dataset and generated configuration

`assets/development/` contains a SHA256-manifested, credential-free snapshot,
images, synthetic declarations and historical authorities. Setup installs into
**storage/portable-development/**, leaving an existing `storage/smart_wardrobe.db`
and its media untouched. Environment files are backed up in
`storage/config-backups/`, unrelated settings are preserved, and required feature
selectors/local paths are generated. Re-running setup does not reset credentials
or data. Do not copy another PC's `.env`, runtime secret or virtual environment.

The export retains58 garments:21 available originals,30 available synthetic
fixtures and7 archived originals; six saved outfits;124 recommendations and70
chats. All51 available preferred images are present;58 physical media files are
bundled. **469 older media records reference files already absent on the source
PC**, mostly processing inputs/masks/person/output history. They are not invented
or regenerated. Older try-on images need an authorized original transfer or a
new upload. The available recommendation wardrobe is complete.

All32 transferred fixture/mixed proofs are independently reconstructed before
installation. Proof contents, scores, IDs, source distinctions, grammar identities
and lineage remain unchanged. Fresh local import MAC signatures and authentication
material replace source-machine credentials. Archived paths remain inert provenance,
never runtime dependencies. The current catalog binding is versioned/portable;
all active storage locations are generated for the destination. Source password
hashes, tokens, signing secrets and private keys are absent.

## Enabled assistant features

- The local pretrained hybrid semantic interpreter, followed by deterministic
  validation and grammar1.9 composition: multiple hard requirements, negation,
  OR alternatives and one bounded optional preference. Historical grammars remain
  readable. See [semantic NLP setup and limits](docs/HYBRID_SEMANTIC_NLP.md).
- The18 approved contextual policies and meaning-based paraphrases; strict
  interview role handling and the disclosed smart-casual default.
- Unified original/synthetic sources with normal B0/B1 qualification intact.
- Fashion Compatibility v2, current recorded P1 clothing preferences and exact
  **3/5R+1/5C+1/5P** scores.
- Explicit Like/Dislike/Clear, exact-score-tie diversity, independent locked
  persistence, immutable History and authenticated Suggest another outfit with
  Seen-base exclusion and the ten-result cap.

Try new chats: “I need jeans.”, “I want a cotton shirt.”, “I'm going shopping.”,
“I need an outfit for a job interview as the candidate.” and “I'd prefer blue
trousers.” Unsupported conditions and unqualified evidence still refuse. Viewing
or continuation never implies dislike. Soft continuation, similarity and
specific-garment replacement remain unsupported. Mixed development results do not
enable Save-as-outfit/VTON; Student1's normal saved-outfit workflows remain.

## CV, embeddings, VTOFF and virtual try-on

CPU mode supports the application, NLP, wardrobe/media, persistence and History.
Existing development image/try-on adapters are labelled substitutes, **not model
inference or accuracy evidence**. Student1's code is retained, including group
try-on. Project CV checkpoints and the small Fashionpedia head are tracked.

For actual GPU inference, use compatible NVIDIA hardware/drivers and the existing
`backend/requirements.txt`: Torch2.11.0+cu128, torchvision0.26.0+cu128, CUDA12.8
wheels. Windows native extensions may need MSVC Build Tools, a matching CUDA
Toolkit and vendored Detectron2/DensePose prerequisites. Verify CUDA/BF16 on the
teammate PC; CPU checks do not certify GPU readiness.

```powershell
# Explicit large dependency/model downloads; review licenses first.
powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Windows.ps1 -Mode GPU -DownloadModels
```

Pinned downloaders: `backend/scripts/setup_vtoff.py` installs
[TryOffDiff](https://huggingface.co/rizavelioglu/tryoffdiff),
[SigLIP](https://huggingface.co/google/siglip-base-patch16-512), VAE and scheduler;
`backend/scripts/setup_vton.py` installs
[CatVTON](https://huggingface.co/zhengchong/CatVTON), SD1.5 inpainting and VAE assets.
Large third-party weights/caches are excluded from Git. Downloaders verify pinned
revisions/hashes; license acceptance/network access may be necessary. TryOffDiff
research/SSPL and CatVTON CC BY-NC-SA restrictions still apply. See
[VTOFF assets](backend/models/vtoff/README.md), [VTON handoff](docs/VTON_HANDOFF.md),
[group try-on](docs/group-try-on.md) and
[garment workflow](docs/GARMENT_WORKFLOW_HANDOFF.md). Actual GPU/model inference
on the teammate's hardware is not claimed verified by the CPU handover.

## Focused verification

```powershell
# Install with -WithTests first. Run backend tests from backend/.
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests/test_portable_development.py
cd ../frontend
npx tsc --noEmit --incremental false
```

Use disposable storage for functional tests, never the live wardrobe. Some strict
historical-authority/performance tests require original external evidence;
unavailable authorities retain their failures and are not replaced with new hashes.
NFR-02 and human fashion/model accuracy remain unaccepted. Actual clean-install
verification and limitations are in [HANDOVER_VERIFICATION.md](docs/HANDOVER_VERIFICATION.md).
Never publish generated `.env`, local storage/logs, account credentials or keys.
