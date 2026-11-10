"""Actual authenticated API/writer benchmark; no formal NFR assertion here."""
from pathlib import Path
import json,os,time
import pytest
from tests.test_p2_preference_integration import p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,submit_p2,save,wardrobe
from tests.test_p2_preference_bounds import maximal_settings
from tests.test_p2_performance_equivalence import frozen_modules

def populate(client,wearer,size):
    from app.infrastructure.persistence import postgresql_repository as db
    wardrobe(client);upper=size//3;lower=size-2*upper;outer=upper
    with db.connection() as conn:
        templates={r['name']:dict(r) for r in conn.execute('SELECT * FROM garments')}
        conn.execute('DELETE FROM garments')
        for n,name in enumerate(['Blue T-shirt']*upper+['Blue Jeans']*lower+['Grey Jacket']*outer):
            g=dict(templates[name]);p=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(g['processing_item_id'],)).fetchone())
            p['id']='benchmark-item-'+str(n);g['id']='benchmark-garment-'+str(n).zfill(3);g['processing_item_id']=p['id']
            for table,row in (('processing_items',p),('garments',g)):
                keys=tuple(row);conn.execute('INSERT INTO '+table+' ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',tuple(row[k] for k in keys))
    save(client,wearer,maximal_settings()[0])
    return upper*lower*(1+outer),upper

def result_core(value):
    proof=value['provenance'].get('context_relevance') or {}
    return {'items':[(i['garment_id'],i['name'],i['category']) for i in value['items']],
        'score':value['score_metadata'],'scored_count':value['provenance']['scored_count'],
        'coverage':proof.get('coverage'),'numeric_ties':proof.get('numeric_ties'),'strongest_unresolved':proof.get('strongest_unresolved')}

@pytest.mark.parametrize('size',[10,30,60,100])
def test_real_API_complete_response_matches_frozen_B2_numeric_results(p2_api,size,monkeypatch,tmp_path):
    from app.application.ports.assistant_runtime import assistant_service
    import app.application.recommendation.attribute_preference_preparation as preparation
    import app.application.recommendation.attribute_preference_relative_facts as facts
    import app.application.recommendation.attribute_preference_selection as selection
    client,wearer=p2_api;count,lower_start=populate(client,wearer,size)
    service=assistant_service();service.execution_engine='compact_exhaustive'
    oldprep,oldfacts=frozen_modules();samples=[]
    def trio(label):
        results={}
        for mode in ('P1','P2','alternative'):
            start=time.perf_counter()
            if mode=='alternative':
                root=results['P2'];step=root['scoring_display']['refinement']['next_action']
                response,value=submit_p2(client,wearer,root['request_text'],step['submission_key'],step['refinement'])
            else:response,value=submit_p2(client,wearer,profile=None if mode=='P1' else 'attribute_preference_decision_v2')
            elapsed=time.perf_counter()-start;assert response.status_code==201,value
            if mode!='alternative':
                assert value['provenance']['scored_count']==count
                assert [i['garment_id'] for i in value['items']]==['benchmark-garment-000',f'benchmark-garment-{lower_start:03}']
            else:assert value['items']!=results['P2']['items']
            results[mode]=value;samples.append({'implementation':label,'size':size,'mode':mode,'api_seconds':elapsed,'service':value['timings'],'core':result_core(value)})
        return results
    with monkeypatch.context() as patch:
        patch.setattr(preparation,'PreparedAttributePreferences',oldprep.PreparedAttributePreferences)
        for name in ('P2CompactFacts','P2RelativeFacts','P2RelativeTracker','public_score','measure'):patch.setattr(facts,name,getattr(oldfacts,name))
        for name in ('P2RelativeFacts','P2RelativeTracker','public_score','measure'):patch.setattr(selection,name,getattr(oldfacts,name))
        expected=trio('certified_frozen_B2')
    for _ in range(int(os.environ.get('P2_PERF_RESPONSE_REPEATS','3'))):
        actual=trio('current')
        for mode in expected:assert result_core(actual[mode])==result_core(expected[mode])
    (tmp_path/'complete-response-samples.json').write_text(json.dumps(samples,indent=2))
