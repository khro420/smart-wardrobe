"""Exact approved B0 descendant; old numerical/source authorities retain bytes."""
from tests.retained_evidence import review_path, review_reference
import ast
import hashlib
import json
from pathlib import Path
import pytest
from tests import integration_source_guard as guard
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.wardrobe import description_projector as d
from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence, seal_field, digest, encode

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'backend/tests/fixtures/description_sources.v1.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def test_complete_scope_frozen_labels_and_exact_sources():
    manifest=json.loads(MANIFEST.read_text())
    scope=json.loads(review_reference(manifest['approved_scope_path']).read_text())
    frozen=review_reference(manifest['approved_scope_path']).parent
    starts=json.loads((frozen/'starting-source-hashes.json').read_text())
    existing={e['path']:e['before_sha256'] for key in ('existing_production','existing_verification') for e in scope[key]}
    additions={e['path'] for key in ('new_production','new_verification') for e in scope[key]}
    assert len(existing)==15 and len(additions)==17
    assert set(manifest['additions'])==additions-{'backend/tests/fixtures/description_sources.v1.json'}
    for path,value in starts.items():
        assert sha(ROOT/path)==guard.description_digest(path,value),path
    for path,value in manifest['additions'].items():assert sha(ROOT/path)==guard.attribute_digest(path,value),path
    assert sha(ROOT/'backend/tests/fixtures/description_labels.v1.json')==sha(frozen/'independent-acceptance.json')
    assert not set(existing)&additions


def test_old_ranking_snapshot_and_getter_remain_original():
    manifest=json.loads(MANIFEST.read_text())
    baseline=review_reference(manifest['baseline_source_path'])
    snapshot='backend/app/shared_contracts/confirmed_garment_snapshot.py'
    assert sha(ROOT/snapshot)==sha(baseline/snapshot)
    query='backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py'
    def extract(path):
        text=path.read_text();tree=ast.parse(text)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SqliteConfirmedGarmentQuery')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_confirmed_available_garments')
        return ast.dump(method,include_attributes=False)
    assert extract(ROOT/query)==extract(baseline/query)


@pytest.mark.parametrize('mutation',['version','fields','resource','canonical','event','reason','channel'])
def test_corrupt_new_evidence_does_not_gain_a_current_claim(mutation):
    policy=DescriptionPolicy.load()
    row={'id':'g','user_id':'a','processing_item_id':'i','category':'vest','name':'Name','preferred_media_id':'m','attributes_json':'{"pattern":"plain"}'}
    document=d.project(row,'a',policy).to_dict()
    if mutation=='version':document['contract']='future'
    elif mutation=='fields':document['extra']='ignored?'
    elif mutation=='resource':document['vocabulary_hash']='f'*64
    else:
        field=document['fields']['pattern']
        if mutation=='canonical':field['canonical_values']=['unsupported fabricated pattern']
        elif mutation=='reason':field['uncertainty_reasons']=['unknown reason']
        elif mutation=='event':field['selected']['event_id']='forged'
        elif mutation=='channel':field['selected']['value']=[['nested value']]
        document['fields']['pattern']=seal_field(field)
    document['revision']='';document['revision']=digest(document)
    with pytest.raises(ValueError):GarmentDescriptionEvidence.from_dict(document)


def test_encoding_boundary_and_historical_read_without_loader(monkeypatch):
    policy=DescriptionPolicy.load()
    row={'id':'g','user_id':'a','processing_item_id':'i','category':'vest','name':'Name','preferred_media_id':'m','attributes_json':'{}'}
    document=d.project(row,'a',policy)
    encoded=document.payload
    boundary=encoded+b' '*(32768-len(encoded))
    assert len(boundary)==32768
    assert GarmentDescriptionEvidence(boundary).to_dict()==document.to_dict()
    with pytest.raises(ValueError):GarmentDescriptionEvidence(boundary+b' ')
    attrs={d.KEY:document.to_dict()};row['attributes_json']=json.dumps(attrs)
    monkeypatch.setattr(DescriptionPolicy,'load',classmethod(lambda cls: (_ for _ in ()).throw(AssertionError('active loader called'))))
    assert d.project(row,'a',None).to_dict()==document.to_dict()
    assert len(encode(d.project({**row,'attributes_json':'{"pattern":"'+('x'*50000)+'"}'},'a',policy).to_dict()))<=32768
