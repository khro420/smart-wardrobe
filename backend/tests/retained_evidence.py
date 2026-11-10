"""Portable locations for optional retained public verification authorities.

These helpers relocate references only. They do not accept new source hashes,
change numerical expectations, or turn missing evidence into passing tests.
Application runtime code never imports this module.
"""
import os
import hashlib
import json
from pathlib import Path


def review_path(relative):
    root=Path(os.environ.get('SMART_WARDROBE_VERIFICATION_ROOT',
                             Path(__file__).resolve().parents[2]/'retained-verification')).resolve()
    target=(root/str(relative).replace('\\','/')).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Retained verification reference escapes its configured root.')
    return target


def review_reference(value):
    text=str(value).replace('\\','/')
    if text.startswith('retained://'):
        return review_path(text[len('retained://'):])
    # Original external authorities stay byte-identical. Their historical
    # absolute transport references can be relocated without rewriting them.
    if len(text)>2 and text[1:3]==':/' and '/reviews/' in text:
        return review_path(text.split('/reviews/',1)[1])
    return Path(value)


def assert_relocated_authority(relative, current_root, original_sha256):
    """Prove a finite transport-only descendant without substituting old hashes.

    Both the exact current bytes and genuine original bytes must match their
    fixed records. Every JSON value other than a relocated review path is exact.
    Missing original evidence still fails; arbitrary observed bytes never pass.
    """
    spec = json.loads((Path(__file__).parent / 'fixtures/retained_transport_authorities.v1.json').read_text())
    assert set(spec) == {'version', 'source_manifest_sha256', 'source_review', 'files'}
    assert spec['version'] == 'retained-transport-authorities-1.0.0'
    assert spec['source_manifest_sha256'] == '7efecc48d0781af466a8f41eb9155e583b1a3676f8645f7aa90bd325682388b3'
    assert relative in spec['files'], 'Unknown relocated authority'
    entry = spec['files'][relative]
    assert set(entry) == {'original_sha256', 'relocated_sha256'}
    assert entry['original_sha256'] == original_sha256, 'Wrong original authority identity'
    current = (Path(current_root) / relative).read_bytes()
    assert hashlib.sha256(current).hexdigest() == entry['relocated_sha256'], 'Unregistered relocated authority bytes'
    review = review_path(spec['source_review'])
    manifest_bytes = (review / 'delivery-final-verified/SOURCE_MANIFEST.json').read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == spec['source_manifest_sha256'], 'Original source manifest changed'
    manifest = json.loads(manifest_bytes)
    assert manifest['files'][relative] == original_sha256
    original = (review / 'source' / relative).read_bytes()
    assert hashlib.sha256(original).hexdigest() == original_sha256, 'Original authority bytes changed'

    def relocate(value):
        if isinstance(value, dict):
            return {k: relocate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [relocate(v) for v in value]
        if isinstance(value, str):
            text = value.replace('\\', '/')
            if len(text) > 2 and text[1:3] == ':/' and '/reviews/' in text:
                return 'retained://' + text.split('/reviews/', 1)[1]
        return value

    assert json.loads(current) == relocate(json.loads(original)), 'Non-transport authority change'
