"""Real disposable review writes, validation, stale revision and rollback."""
from dataclasses import replace
import json
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.domain.value_objects.general_context_evidence import KEY, project_appearance_evidence
from tests.test_professional_academic_context import professional_api, appearance
from tests.test_release_configuration import release
from tests.test_forward_style_semantics import lifecycle
from tests.test_contextual_wedding import patch, review


def prepare(professional_api):
    client,create=professional_api;gid=create(['smart casual'])
    patch(client,gid,{'category':'vest_dress'})
    assert review(client,gid,review_style=True).status_code==200
    return client,gid


def row(client,gid): return next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)


def test_owner_unknown_roundtrip_and_namespace_withdrawal(professional_api):
    client,gid=prepare(professional_api)
    old=row(client,gid)['attributes'].get('contextual_suitability_v1')
    response=appearance(client,gid,features={'collared_neckline':None,'tailored_cut':False,'structured_shape':True})
    assert response.status_code==200,response.text
    data=response.json();assert data['appearance_edit']['current']
    assert data['attributes'][KEY]['construction_features']=={'collared_neckline':None,'tailored_cut':False,'structured_shape':True}
    assert data['attributes']['contextual_suitability_v1']==old
    raw=data['attributes'][KEY]
    assert set(raw)=={'schema_version','source','category','media_id','construction_features','condition_observation','reviewed_at'}
    assert raw['source']=='owner_review' and project_appearance_evidence(raw,True).state=='Known'
    assert appearance(client,gid,withdraw=True).status_code==200
    assert KEY not in row(client,gid)['attributes'] and row(client,gid)['contextual_edit']['review_current']


@pytest.mark.parametrize('bad',[{'withdraw':1},{'source':'owner_review'},{'construction_features':{'structured_shape':True},'condition_observation':'clean_intact'},
    {'construction_features':{'collared_neckline':1,'tailored_cut':None,'structured_shape':True},'condition_observation':'clean_intact'},
    {'construction_features':{'collared_neckline':None,'tailored_cut':None,'structured_shape':True},'condition_observation':'perfect'},
    {'withdraw':True,'condition_observation':'unknown'}])
def test_payload_source_boolean_and_completeness_validation(professional_api,bad):
    client,gid=prepare(professional_api);before=row(client,gid)
    response=client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',json={'revision':before['appearance_edit']['revision'],'appearance_review':bad})
    assert response.status_code==422 and row(client,gid)==before


def test_foreign_owner_stale_revision_and_real_trigger_rollback(professional_api):
    client,gid=prepare(professional_api);before=row(client,gid)
    db.ensure_user('foreign-owner')
    response=client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',headers={'Authorization':'Bearer '+issue_access_token('foreign-owner')},
        json={'revision':before['appearance_edit']['revision'],'appearance_review':{'withdraw':True}})
    assert response.status_code==404
    patch(client,gid,{'name':'new name'})
    # Revision hashes meaningful evidence, not the display name; change a bound category.
    patch(client,gid,{'category':'sling_dress'})
    response=client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',json={'revision':before['appearance_edit']['revision'],'appearance_review':{'withdraw':True}})
    assert response.status_code==409
    with db.connection() as conn:
        before_db=tuple(conn.execute('SELECT attributes_json,additional_attributes,updated_at FROM garments WHERE id=?',(gid,)).fetchone())
        conn.execute("CREATE TRIGGER abort_appearance BEFORE UPDATE ON garments BEGIN SELECT RAISE(ABORT,'synthetic injected failure'); END")
    with pytest.raises(Exception): appearance(client,gid)
    with db.connection() as conn:
        assert tuple(conn.execute('SELECT attributes_json,additional_attributes,updated_at FROM garments WHERE id=?',(gid,)).fetchone())==before_db
        conn.execute('DROP TRIGGER abort_appearance')
    assert appearance(client,gid).status_code==200


def test_category_invalidation_generic_patch_protection_and_existing_style_action(professional_api):
    client,gid=prepare(professional_api);assert appearance(client,gid).status_code==200
    raw=row(client,gid)['attributes'][KEY]
    bad=client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{KEY:raw}})
    assert bad.status_code==422
    patch(client,gid,{'category':'sling_dress'})
    assert not row(client,gid)['appearance_edit']['current']
    assert review(client,gid,review_style=True,wedding_choice='allow').status_code==200
    assert not row(client,gid)['appearance_edit']['current']


def test_conflicting_mirror_and_timestamps_are_not_trusted(professional_api):
    client,gid=prepare(professional_api);assert appearance(client,gid).status_code==200
    raw=row(client,gid)['attributes'][KEY]
    assert project_appearance_evidence({**raw,'source':'model','confidence':1.0},True).state=='Malformed'
    assert project_appearance_evidence({**raw,'reviewed_at':'not-a-date'},True).state=='Malformed'
    with db.connection() as conn:
        extra=json.loads(conn.execute('SELECT additional_attributes FROM garments WHERE id=?',(gid,)).fetchone()[0])
        extra[KEY]['condition_observation']='unknown'
        conn.execute('UPDATE garments SET additional_attributes=? WHERE id=?',(json.dumps(extra),gid))
    assert not row(client,gid)['appearance_edit']['current']
    assert appearance(client,gid).status_code==422
