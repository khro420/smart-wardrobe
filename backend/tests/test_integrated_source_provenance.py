"""Check the reviewed integration against its two fixed source authorities.

This is a new current contract. Original historical source guards and their
expected hashes remain unchanged on their designated certified snapshots.
"""
import hashlib
import json
from pathlib import Path


def test_exact_approved_application_and_preserved_teammate_sources():
    root = Path(__file__).resolve().parents[2]
    raw = (Path(__file__).parent / 'fixtures/integrated_source_provenance.v1.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '956dee4e8daa58445039b9c1b24ef515ffd1d80583b007eeb8f4dd315d825072'
    spec = json.loads(raw)
    assert set(spec) == {'version', 'team_baseline_commit', 'approved919_manifest_sha256',
                         'approved919_application_files', 'preserved_team_only_model_vendor_files'}
    assert spec['version'] == 'integrated-source-provenance-1.0.0'
    assert spec['team_baseline_commit'] == 'a69d95ba6caf84eacbeec661ee7867068b073a1d'
    assert spec['approved919_manifest_sha256'] == '7efecc48d0781af466a8f41eb9155e583b1a3676f8645f7aa90bd325682388b3'
    assert len(spec['approved919_application_files']) == 350
    assert len(spec['preserved_team_only_model_vendor_files']) == 422
    for authority in ('approved919_application_files', 'preserved_team_only_model_vendor_files'):
        assert spec[authority]
        for name, expected in spec[authority].items():
            target = (root / name).resolve()
            assert target.is_relative_to(root)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, name
