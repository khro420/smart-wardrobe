# CatVTON model assets

The application uses the original Stable-Diffusion-based CatVTON mix checkpoint
for a non-commercial academic prototype. CatVTON code and checkpoints are
CC BY-NC-SA 4.0. The Stable Diffusion inpainting base uses CreativeML OpenRAIL-M;
the Stability AI VAE is MIT-licensed. Retain every upstream notice.

Run python scripts/setup_vton.py from backend/ to download pinned assets and
produce manifest.json. Request-time inference is local-only and refuses missing
or mismatched revisions.

The supported runtime profile is one top, bottom, or dress reference at 768 x
1024, batch one, BF16, 50 steps, guidance 2.5, and seed 42. Outerwear and
multi-garment outfits are rejected before inference. Lower-body and dress
acceptance remain blocked until the officially licensed DressCode evaluation data
is supplied.
