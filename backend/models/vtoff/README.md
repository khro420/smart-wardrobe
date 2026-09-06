# VTOFF model assets

Run `python scripts/setup_vtoff.py` from `backend/` to populate this directory
with pinned official assets. Large weights and Hugging Face cache files are
ignored by Git; `README.md` and the generated `manifest.json` are retained.

The integration uses the authors' multi-garment TryOffDiff v2 checkpoint under
the Server Side Public License (SSPL) published with the model. Its model card
states that it is intended for academic research and is not available for
commercial use unless the full source code is shared. Review those terms before
deployment or distribution.
