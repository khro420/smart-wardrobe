"""Current descendants retain historical numerical and negative authorities."""
from tests.retained_evidence import review_path, review_reference
from dataclasses import replace
import copy,json
from pathlib import Path
import pytest
from fastapi import HTTPException
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.application.wardrobe.profile_service import selected_history_profile
from tests.test_recommendation_persistence import store
from tests.test_recommendation_actions import ready,history
from tests.test_release_configuration import release,lifecycle
from tests.current_contract_fixtures import original_fields_exact,wearer_id


def test_acceptance_specification_is_the_frozen_owner_approved_input():
    path=Path(__file__).parent/'fixtures/reconciliation_cases.v1.json'
    approved=review_path('phase_regression_contract_reconciliation_20261107/approved-contract/INDEPENDENT_ACCEPTANCE_SPECIFICATION.json')
    assert path.read_bytes()==approved.read_bytes()


@pytest.mark.parametrize('size',[100,101,150])
def test_current_quota_descendant_completes_or_refuses_without_clipping(size):
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from tests.test_structural_candidates import garment,Query
    session=RecommendationEngine(Query([garment(str(i),'vest_dress') for i in range(size)])).generate_homepage_candidates('owner')
    result=list(session)
    if size==100:
        assert len(result)==100 and session.result.complete
    else:
        assert not result and not session.result.complete
        assert session.result.status=='WardrobeCapacityExceeded'


def test_read_only_history_selection_does_not_create_missing_user_or_default(store):
    with db.connection() as conn:
        before={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in ('users','wardrobe_profiles')}
    for owner in ('owner','absent-subject'):
        with pytest.raises(HTTPException) as exc:selected_history_profile(owner,None)
        assert exc.value.status_code==404
    with db.connection() as conn:
        assert before=={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in before}
    profile=wearer_id('owner')
    assert selected_history_profile('owner',profile)['id']==profile
    with pytest.raises(HTTPException) as exc:selected_history_profile('other',profile)
    assert exc.value.status_code==404


def test_actual_foreign_history_request_remains_404_without_new_profile(release):
    client,_=release
    with db.connection() as conn:
        before={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in ('users','wardrobe_profiles')}
    response=client.get('/api/v1/chats/missing',headers={'Authorization':'Bearer '+issue_access_token('missing-authenticated-subject')})
    assert response.status_code==404
    with db.connection() as conn:
        assert before=={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in before}


def test_current_outerwear_support_descendant_retains_history(ready):
    from app.application.visualisation.outfit_identifier_validator import resolve_source
    path,record=ready
    with db.connection() as conn:
        conn.execute("UPDATE garments SET category='long_sleeve_outwear'")
    with db.connection() as conn:
        before=history(conn)
        plan,source=resolve_source(conn,'owner',recommendation_id=record['id'])
        assert plan.modes==('upper',) and source['categories']==['upper']
        assert history(conn)==before


def test_current_unsupported_role_still_refuses_without_history_or_job_write(ready):
    from app.application.visualisation.outfit_identifier_validator import resolve_source
    with db.connection() as conn:conn.execute("UPDATE recommendation_items SET garment_role='unsupported'")
    with db.connection() as conn:
        before=history(conn)
        with pytest.raises(HTTPException) as exc:resolve_source(conn,'owner',recommendation_id=ready[1]['id'])
        assert exc.value.status_code==422
        assert history(conn)==before and conn.execute('SELECT count(*) FROM visualisations').fetchone()[0]==0


def test_current_capabilities_have_explicit_default_off_versioned_contracts():
    from app.api.recommendation_routes import capabilities
    value=capabilities('synthetic-owner',None,None)
    assert set(value)=={'homepage_enabled','assistant_enabled','wearer_identity','attributes','attribute_preferences','palette_compatibility'}
    assert value['homepage_enabled'] is value['assistant_enabled'] is False
    assert value['wearer_identity']['version']=='assistant-wearer-intent-1.0.0'
    assert value['attributes']['version']=='attribute-request-capabilities-1.0.0' and value['attributes']['enabled'] is False
    assert value['attribute_preferences']=={'version':'attribute-preference-request-capabilities-1.0.0','enabled':False,'profile':'attribute_preference_decision_v2','default':'p1','explicit_selection_required':True}
    assert value['palette_compatibility']=={'version':'palette-compatibility-capabilities-1.0.0','enabled':False,'profile':'recorded_palette_compatibility_v1','default':'c1','explicit_selection_required':True}


@pytest.mark.parametrize('mutation',['score','state','count','order','new_field','new_evidence'])
def test_named_metadata_descendant_rejects_semantic_or_unregistered_changes(mutation):
    expected={'status':'Selected','complete':True,'winner':{'total':{'numerator':3,'denominator':5},'state':'Available','observed':1,'members':['a','b']},'scored_count':2}
    actual={**copy.deepcopy(expected),'ranking_evidence':None,'refinement_summary':None}
    original_fields_exact(expected,actual)
    if mutation=='score':actual['winner']['total']['numerator']=4
    elif mutation=='state':actual['winner']['state']='Unknown'
    elif mutation=='count':actual['scored_count']=1
    elif mutation=='order':actual['winner']['members'].reverse()
    elif mutation=='new_field':actual['invented']=True
    else:actual['ranking_evidence']={'hidden':'qualified'}
    with pytest.raises(AssertionError):original_fields_exact(expected,actual)
