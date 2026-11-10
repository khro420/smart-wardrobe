"""Independent frozen identities and reusable synthetic source declarations."""
from pathlib import Path
import json,copy,uuid
import pytest
from app.domain.value_objects import verified_garment_subtype as types
DATA=json.loads((Path(__file__).parent/'fixtures/verified_subtype_acceptance.v1.json').read_text(encoding='utf-8'))
OWNER='owner';PROFILE='profile'
def row(category='short_sleeve_top',name='unqualified blouse name'):
    return {'id':'garment','user_id':OWNER,'category':category,'preferred_media_id':'media','name':name,'attributes_json':'{}'}
def declared(kind='t_shirt',category='short_sleeve_top',state='Known'):
    garment=row(category)
    event=dict(contract=types.EVENT_VERSION,event_id='event',owner_id=OWNER,subject_kind='garment',subject_id='garment',wearer_profile_id=PROFILE,action_id=str(uuid.uuid4()),ordinal=1,prior_revision=None,event_kind='owner_confirm' if state=='Known' else 'owner_unspecified',state=state,subtype=kind if state=='Known' else None,category=category,media_id='media',source_binding_sha256=types.binding(garment,OWNER),registry_version=types.VERSION,registry_sha256=types.RESOURCE_SHA256,origin='owner_selected',contributor=OWNER,recorded_at='2026-11-08T00:00:00+00:00',review_basis='synthetic_fixture_declaration',reason='Independent synthetic product identity declaration',transfer_source=None,unresolved_restriction='blouse' if kind=='blouse' and state=='Known' else None)
    event['revision']=types.digest(event)
    return garment,event,types.project(garment,OWNER,[event])
def test_exact_five_parent_compatible_identities():
    registry=types.registry()
    assert {e['id'] for e in registry['entries']}=={'t_shirt','polo_shirt','button_up_shirt','knit_top','blouse'}
    assert all(e['parents']==['short_sleeve_top','long_sleeve_top'] for e in registry['entries'])
    assert registry['model_emitters']==registry['measured_emitters']==[]
def test_registry_tamper_is_not_a_new_authority():
    changed=copy.deepcopy(types.registry());changed['entries'][0]['id']='blouse'
    with pytest.raises(ValueError):types.registry(changed)
def test_names_are_not_subtype_evidence():
    assert types.project(row(name='blouse polo T-shirt red silk floral'),OWNER,[])['state']=='Absent'
