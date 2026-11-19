"""Offline, read-only garment-region preview; no server, auth, or DB access.

Run from backend: python scripts/preview_outfit_review.py observation.json photo.jpg preview.html
The HTML contains the photo: keep it private. It is a development artifact, not
an authenticated confirmation endpoint or a model accuracy assessment.
"""
import base64
import html
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.application.outfit_review.contract import Observation
from app.application.outfit_review.images import prepare_image
from app.application.outfit_review.model import preview


def render(observation: Observation, photo: bytes) -> str:
    identity, png = prepare_image(photo)
    if identity != observation.image:
        raise ValueError("Preview photo differs from observation image")
    data = preview(observation)
    e = html.escape
    regions, rows = [], []
    for item in observation.prediction.items:
        x, y, r, b = item.region.xyxy
        regions.append(f'<rect x="{x}" y="{y}" width="{r-x}" height="{b-y}"/><text x="{x}" y="{y+18}">{e(item.id)}</text>')
        attrs = "; ".join(f"{name}: {getattr(item, name).state} {' / '.join(getattr(item, name).values) or 'unknown'}"
                          for name in ("colours", "pattern", "sleeve_length", "sleeve_state"))
        rows.append(f"<tr><td>{e(item.id)}</td><td>{e(item.category)} / {e(item.role)}</td><td>{e(attrs)}</td><td>{e(item.visibility)}</td></tr>")
    picture = base64.b64encode(png).decode("ascii")
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'">
<title>Outfit observation — private development preview</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:24px auto}}svg{{max-height:650px;width:100%}}rect{{fill:none;stroke:#d000ff;stroke-width:3}}text{{fill:#d000ff;font-size:18px;paint-order:stroke;stroke:white;stroke-width:2px}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #ddd}}</style>
<h1>AI garment proposals — review required</h1>
<p>Boxes and attributes are model predictions. A box is not proof of a visible garment. No fashion score is produced.</p>
<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" style="aspect-ratio:{identity.width}/{identity.height}"><image href="data:image/png;base64,{picture}" width="1000" height="1000" preserveAspectRatio="none"/>{''.join(regions)}</svg>
<p>Contract issues: {e(', '.join(data['issues']) or 'none detected; visual review still required')}</p>
<p>Footwear visibility: {e(observation.prediction.footwear_visibility)}. Scene: {e(observation.prediction.scene)}.</p>
<table><tr><th>Item</th><th>Category / role</th><th>Attributes</th><th>Visibility</th></tr>{''.join(rows)}</table>
<p>Material composition, brand, comfort and body measurements remain unknown. Correction/confirmation is an unwired server-side contract, exercised in disposable tests; this preview cannot authenticate or save corrections.</p></html>'''


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: preview_outfit_review.py observation.json photo.jpg NEW-preview.html")
    source, image, destination = map(Path, sys.argv[1:])
    if source.stat().st_size > 256 * 1024 or image.stat().st_size > 20 * 1024 * 1024:
        raise SystemExit("Bounded observation/photo required")
    observation = Observation.model_validate_json(source.read_text(encoding="utf-8"))
    document = render(observation, image.read_bytes())
    with destination.open("x", encoding="utf-8") as output:
        output.write(document)
    print("Private offline preview created; no application data was written.")
