"""Actual bounded mechanics and measurements; no formal NFR or model-quality claim."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json,sqlite3,time,tracemalloc,uuid
import pytest
from tests.test_p2_preference_selection import snapshot,family,EMPTY,engine_fixture
from tests.test_attribute_qualification import make_member
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.application.recommendation.attribute_preference_policy import AttributePreferencePolicy
from app.application.recommendation.attribute_preference_codec import build_archive_snapshot,bounded_provenance
from app.domain.value_objects.attribute_preferences import PreferenceDocument,AttributePreferenceSnapshot,PreferenceError,encode,DOCUMENT


def maximal_settings():
    """All finite representations plus bounded dynamic sets, without changing labels."""
    policy=AttributePreferencePolicy.load();families={}
    definitions={row['axis']:row for row in policy.snapshot()['axes']}
    for row in policy.snapshot()['finite']:
        if row['status']=='Blocked':continue
        definition=definitions[row['axis']]
        f=families.setdefault(definition['family'],{'mode':'override','importance':'1','axes':{}})
        a=f['axes'].setdefault(row['axis'],{'scope':definition['default_scope'],'importance':'1','liked':[],'avoided':[]})
        a['liked'].append(row['value'])
    for axis in ('primary_colour','secondary_colour','palette_colour'):
        values=families['colour']['axes'][axis]['liked']
        values.extend('#%06x'%n for n in range(1,33-len(values)))
    families['colour']['axes']['palette_coverage']={'scope':'all_selected','importance':'1',
        'liked':[{'colour':'#%06x'%n,'minimum':'0.500001'} for n in range(1,33)],'avoided':[]}
    families['descriptive_tag']={'mode':'override','importance':'1','axes':{'descriptive_tag':{'scope':'all_selected','importance':'1','liked':['\U0001f455'*98+f'{n:02d}' for n in range(20)],'avoided':[]}}}
    document=PreferenceDocument.from_dict({'contract':DOCUMENT,'families':families,'last_action':None})
    return families,document


@pytest.mark.parametrize('size',[0,1,100])
def test_maximal_preparation_and_38148_aggregations_have_no_loop_IO(size,monkeypatch,tmp_path):
    families,document=maximal_settings()
    collection=tuple(make_member(f'g{n:03}','pattern','plain',category=(['vest']*33+['trousers']*34+['long_sleeve_outwear']*33)[n]) for n in range(size))
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    captured=build_archive_snapshot(snapshot(families),AttributePreferencePolicy.load())
    tracemalloc.start();started=time.perf_counter()
    prepared=PreparedAttributePreferences(captured,collection,request=StructuredOutfitRequest(),original_text='Recommend an outfit.')
    preparation=time.perf_counter()-started;calls=prepared.predicate_calls
    values=sum(len(a[p]) for f in families.values() for a in f['axes'].values() for p in ('liked','avoided'))
    assert values<=320 and calls==size*values and calls<=32000
    def forbidden(*args,**kwargs):raise AssertionError('Source/normalization/I/O inside preference enumeration')
    with monkeypatch.context() as patch:
        from app.application.recommendation.preference_normalizer import PreferenceNormalizer
        from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
        patch.setattr(Path,'open',forbidden);patch.setattr(sqlite3,'connect',forbidden)
        patch.setattr(PreferenceNormalizer,'normalize',forbidden);patch.setattr(AttributeEvidencePolicy,'fact',forbidden)
        started=time.perf_counter();examined=0
        for upper in collection[:min(size,33)]:
            for lower in collection[33:67]:
                for outer in (None,*collection[67:]):
                    members=(('upper',upper.snapshot.garment_id),('lower',lower.snapshot.garment_id))
                    if outer:members+= (('outerwear',outer.snapshot.garment_id),)
                    result=prepared.evaluate(members,EMPTY)
                    assert 0<=result.total.lower<=result.total.upper<=1
                    examined+=1
        aggregation=time.perf_counter()-started
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert examined==(38148 if size==100 else 0)
    assert prepared.predicate_calls==calls and len(prepared._cache)<=256
    (tmp_path/'p2-preparation-aggregation.json').write_text(json.dumps(dict(size=size,configured_values=values,
        configuration_bytes=len(document.payload),predicate_calls=calls,structural_examined=examined,
        preparation_seconds=preparation,aggregation_seconds=aggregation,traced_peak_bytes=peak,cache_entries=len(prepared._cache),candidate_external_calls=0)))


def captured_evidence():
    from app.application.recommendation.attribute_preference_verifier import build
    from tests.test_p2_preference_selection import kernel_rank
    from app.application.recommendation.refinement_verifier import snapshot_digest,request_digest
    from app.domain.value_objects.attribute_selection_evidence import description_digest
    garments,old,request,*_=engine_fixture(['blue']);text="I'm going shopping."
    saved=build_archive_snapshot(old.snapshot,AttributePreferencePolicy.load())
    prepared=PreparedAttributePreferences(saved,old.collection,request=request,original_text=text)
    result=kernel_rank(garments,prepared,request)
    return saved,build(prepared,result.winner.verified,result.winner.score,'a'*64,snapshot_digest(garments),description_digest(old.collection),request_digest(text,request,())).evidence


def test_new_bounds_exact_UTF8_and_one_byte_over_without_widening_old_versions():
    from app.domain.value_objects.attribute_preference_evidence import AttributePreferenceEvidence,ratio,read_ratio
    document=PreferenceDocument.from_dict({'contract':DOCUMENT,'families':{},'last_action':None})
    saved,evidence=captured_evidence()
    from app.domain.value_objects.attribute_preferences import decode
    padded=document.payload+b' '*(32768-len(document.payload))
    assert decode(padded)==document.to_dict()
    with pytest.raises(PreferenceError):decode(padded+b' ')
    with pytest.raises(PreferenceError):PreferenceDocument(padded)  # Stored settings must also be canonical.
    for cls,payload,limit in ((AttributePreferenceSnapshot,saved.payload,131072),(AttributePreferenceEvidence,evidence.payload,344064)):
        padded=payload+b' '*(limit-len(payload));assert cls(padded)
        with pytest.raises(PreferenceError):cls(padded+b' ')
    core={'attribute_preference':evidence.to_dict(),'padding':''}
    core['padding']='x'*(368640-len(encode({'padding':''})))
    assert bounded_provenance(core)
    core['padding']+='x'
    with pytest.raises(PreferenceError):bounded_provenance(core)
    # Transport-only envelope boundary: it is not a valid semantic sidecar.
    transport={'attribute_preference':{'transport':''}}
    transport['attribute_preference']['transport']='x'*(1048576-len(encode(transport)))
    assert len(bounded_provenance(transport).encode())==1048576
    transport['attribute_preference']['transport']+='x'
    with pytest.raises(PreferenceError):bounded_provenance(transport)
    assert read_ratio(ratio(F(1,10**4095+1)))==F(1,10**4095+1)
    with pytest.raises(PreferenceError):ratio(F(1,10**4096))
    from app.application.recommendation.refinement_verifier import bounded_provenance as versioned
    with pytest.raises(ValueError):versioned({'padding':'x'*327680})


def test_P2_maximum_transport_ten_rows_three_SELECTs_500_unrelated(tmp_path):
    from app.infrastructure.persistence.refinement_lineage_query import read_chain,bounded_record
    from app.domain.value_objects.recommendation_refinement import step_key
    root=str(uuid.uuid4());ids=[root]+[str(uuid.uuid4()) for _ in range(9)]
    # Deliberately nonsemantic transport records; never reported as ten valid recommendations.
    value={'attribute_preference':{},'refinement':{'version':'recommendation-refinement-evidence-2.0.0','root_id':root}}
    provenance=bounded_provenance(value).ljust(1048576,' ');score=json.dumps('x'*262142);request=json.dumps('x'*65534)
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript('''CREATE TABLE recommendations(id TEXT PRIMARY KEY,user_id TEXT,chat_id TEXT,recommendation_type TEXT);
        CREATE TABLE nlp_chats(id TEXT PRIMARY KEY,user_id TEXT,request_text TEXT,extracted_entities_json TEXT);
        CREATE TABLE recommendation_metadata(recommendation_id TEXT PRIMARY KEY,provenance_json TEXT,score_json TEXT);
        CREATE TABLE recommendation_submissions(user_id TEXT,operation TEXT,submission_key TEXT,recommendation_id TEXT,UNIQUE(user_id,operation,submission_key));''')
    for n,identifier in enumerate(ids):
        conn.execute('INSERT INTO recommendations VALUES (?,?,?,?)',(identifier,'owner-A',identifier,'assistant'))
        conn.execute('INSERT INTO nlp_chats VALUES (?,?,?,?)',(identifier,'owner-A','Synthetic transport fixture',request))
        conn.execute('INSERT INTO recommendation_metadata VALUES (?,?,?)',(identifier,provenance,score))
        if n:conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?)',('owner-A','assistant',step_key(root,n),identifier))
    for n in range(500):conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?)',('owner-A','assistant','unrelated-'+str(n),'absent'))
    queries=[];conn.set_trace_callback(queries.append);tracemalloc.start();started=time.perf_counter()
    parent,chain=read_chain(conn,'owner-A',ids[-1]);elapsed=time.perf_counter()-started
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(chain)==10 and len(queries)==3
    payload=sum(len(row[k].encode()) for row in chain for k in ('provenance_json','score_json','extracted_entities_json'))
    assert payload==13762560
    with pytest.raises(ValueError):bounded_record({**parent,'provenance_json':provenance+' '})
    with pytest.raises(LookupError):read_chain(conn,'foreign',ids[-1])
    (tmp_path/'p2-maximum-transport.json').write_text(json.dumps(dict(records=10,selects=3,unrelated_receipts=500,payload_bytes=payload,seconds=elapsed,traced_peak_bytes=peak,semantic_status='Nonsemantic transport upper bound only; not ten valid recommendations or NFR acceptance.')))
    conn.close()


from tests.test_p2_preference_integration import p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,submit_p2,save,wardrobe


def test_actual_100_shared_inventory_baseline_P2_persistence_refinement_and_capacity(p2_api,monkeypatch,tmp_path):
    from statistics import median
    from app.application.ports.assistant_runtime import assistant_service
    from app.infrastructure.persistence import postgresql_repository as db
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.attribute_preference_verifier import build
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    client,wearer=p2_api;wardrobe(client);service=assistant_service()
    # Build an explicitly synthetic strict source collection in this disposable
    # fixture, preserving completed same-owner jobs and unique confirmed items.
    with db.connection() as conn:
        templates={r['name']:dict(r) for r in conn.execute('SELECT * FROM garments')}
        conn.execute('DELETE FROM garments')
        def insert(n,name):
            g=dict(templates[name]);p=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(g['processing_item_id'],)).fetchone())
            p['id']='benchmark-item-'+str(n);g['id']='benchmark-garment-'+str(n).zfill(3);g['processing_item_id']=p['id']
            for table,row in (('processing_items',p),('garments',g)):
                keys=tuple(row);conn.execute('INSERT INTO '+table+' ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',tuple(row[k] for k in keys))
        for n,name in enumerate(['Blue T-shirt']*33+['Blue Jeans']*34+['Grey Jacket']*33):insert(n,name)
    families,_=maximal_settings();save(client,wearer,families)
    assert len(SqliteConfirmedGarmentQuery().get_confirmed_available_garments('style-owner'))==100
    # Stage timings come from the production coordinator/kernel/writer, rather
    # than a replacement selection implementation. Three untraced observations
    # per mode establish medians/ranges; a separate P2 invocation measures peak.
    kernel_times=[];preparation_times=[];original_rank=CompactExhaustiveScorer.rank;original_prepare=PreparedAttributePreferences.__init__
    def rank(self,*args,**kwargs):
        self.instrument=True;answer=original_rank(self,*args,**kwargs);kernel_times.append(dict(self.timings));return answer
    def prepare(self,*args,**kwargs):
        started=time.perf_counter();original_prepare(self,*args,**kwargs);preparation_times.append(time.perf_counter()-started)
    monkeypatch.setattr(CompactExhaustiveScorer,'rank',rank);monkeypatch.setattr(PreparedAttributePreferences,'__init__',prepare)
    samples=[];roots=[]
    for mode in ('P1','P2'):
        for observation in range(3):
            started=time.perf_counter();response,result=submit_p2(client,wearer,profile=None if mode=='P1' else 'attribute_preference_decision_v2');elapsed=time.perf_counter()-started
            assert response.status_code==201,result
            assert result['provenance']['scored_count']==38148
            assert [i['garment_id'] for i in result['items']]==['benchmark-garment-000','benchmark-garment-033']
            samples.append(dict(stage=mode+' initial',seconds=elapsed,service=result['timings'],kernel=kernel_times[-1]))
            if mode=='P2':roots.append(result)
    for root in roots:
        step=root['scoring_display']['refinement']['next_action'];started=time.perf_counter()
        response,result=submit_p2(client,wearer,root['request_text'],step['submission_key'],step['refinement']);elapsed=time.perf_counter()-started
        assert response.status_code==201,result
        assert result['provenance']['refinement']['root_R']==root['provenance']['refinement']['root_R']
        assert result['items']!=root['items']
        samples.append(dict(stage='P2 alternative',seconds=elapsed,service=result['timings'],kernel=kernel_times[-1]))
    tracemalloc.start();started=time.perf_counter();response,peak_result=submit_p2(client,wearer);traced_seconds=time.perf_counter()-started
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();assert response.status_code==201,peak_result
    with db.connection() as conn:
        row=conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(peak_result['id'],)).fetchone()
        provenance_bytes=len(row['provenance_json'].encode());score_bytes=len(row['score_json'].encode())
        assert score_from_json(row['score_json']).profile_name=='attribute_preference_decision_v2'
        before=conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]
        # A separate synthetic legacy-overcapacity source must reject before
        # enumeration without silently clipping or deleting any source record.
        g=dict(conn.execute('SELECT * FROM garments ORDER BY id LIMIT 1').fetchone());p=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(g['processing_item_id'],)).fetchone())
        p['id']='benchmark-over-item';g['id']='benchmark-over-garment';g['processing_item_id']=p['id']
        for table,value in (('processing_items',p),('garments',g)):
            keys=tuple(value);conn.execute('INSERT INTO '+table+' ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',tuple(value[k] for k in keys))
    response,over=submit_p2(client,wearer);assert response.status_code==409 and over['outcome']=='WardrobeCapacityExceeded',over
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM garments').fetchone()[0]==101
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==before
    groups={stage:{'observations':3,'median_seconds':median(s['seconds'] for s in samples if s['stage']==stage),
        'range_seconds':[min(s['seconds'] for s in samples if s['stage']==stage),max(s['seconds'] for s in samples if s['stage']==stage)]} for stage in ('P1 initial','P2 initial','P2 alternative')}
    (tmp_path/'p2-integrated-100.json').write_text(json.dumps(dict(garments=100,structures_examined=38148,samples=samples,summary=groups,
        preparation_observations_seconds=preparation_times,traced_P2_seconds=traced_seconds,traced_peak_bytes=peak,
        provenance_bytes=provenance_bytes,score_bytes=score_bytes,
        boundary='Synthetic authenticated disposable API/current production kernel and writer. No model/private user data or formal NFR acceptance.'),indent=2))
