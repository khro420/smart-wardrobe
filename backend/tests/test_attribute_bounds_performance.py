"""Disposable bounded mechanics measurements; no formal NFR acceptance claim."""
import json,time,tracemalloc
from pathlib import Path
import pytest
from tests.test_attribute_qualification import make_member,condition,POLICY
from tests.test_attribute_candidate_selection import candidate
from tests.test_attribute_history import captured,WEARER,BASE
from tests.test_attribute_nlp import pipeline
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,encode,decode
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent,AttributeSelectionEvidence,MAX_INTENT,MAX_EVIDENCE,bounded_provenance
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier


def test_exact_versioned_wire_and_archive_byte_boundaries(captured):
    rq=condition('descriptive_tag','\U0001f455'*100,op='exact_text')
    padded=rq.payload+b' '*(32768-len(rq.payload))
    assert decode(padded)==rq.to_dict()
    with pytest.raises(AttributeRequestError):decode(padded+b' ')
    # A bounded JSON decoder does not relax canonical wire serialization.
    with pytest.raises(AttributeRequestError):AttributeConditions(padded)
    for constructor,payload,limit in ((AttributeIntent,encode(captured.to_dict()['intent']),MAX_INTENT),
        (AttributeSelectionEvidence,captured.payload,MAX_EVIDENCE)):
        padded=payload+b' '*(limit-len(payload))
        assert len(padded)==limit and constructor(padded)
        with pytest.raises(ValueError):constructor(padded+b' ')
    value={'attribute_selection':captured.to_dict(),'transport_fixture':''}
    # The core and full envelope limits are independent. Padding here is a
    # deliberately nonsemantic transport fixture, never a valid recommendation.
    core={'transport_fixture':''};fill=360448-len(encode(core))
    value['transport_fixture']='x'*fill
    assert len(encode({k:v for k,v in value.items() if k!='attribute_selection'}))==360448
    assert len(bounded_provenance(value).encode())<=589824
    value['transport_fixture']+='x'
    with pytest.raises(AttributeRequestError):bounded_provenance(value)


def test_unicode_codepoints_and_collection_limits():
    assert condition('garment_name','\U0001f455'*100,op='exact_text')
    with pytest.raises(AttributeRequestError):condition('garment_name','\U0001f455'*101,op='exact_text')
    raw=condition('descriptive_tag','one',op='contains_any').to_dict()
    raw['groups'][0]['conditions'][0]['values']=[str(i) for i in range(20)]
    assert AttributeConditions.from_dict(raw)
    raw['groups'][0]['conditions'][0]['values'].append('20')
    with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(raw)
    raw=condition('pattern','plain').to_dict()
    raw['groups']=[{**raw['groups'][0],'id':f'g{i:02}', 'conditions':[{**raw['groups'][0]['conditions'][0],'id':f'c{i:02}'}]} for i in range(1,9)]
    assert AttributeConditions.from_dict(raw)
    raw['groups'].append({**raw['groups'][0],'id':'g09'})
    with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(raw)


@pytest.mark.parametrize('size',[0,1,100])
def test_prepare_once_and_no_external_calls_in_candidate_loop(size,monkeypatch,tmp_path):
    categories=['vest']*33+['trousers']*34+['long_sleeve_outwear']*33
    collection=[make_member(f'g{i:03}','pattern','plain',category=categories[i]) for i in range(size)]
    rq=condition('pattern','plain',q='all_present')
    calls=[];original=type(POLICY).fact
    def counted(self,*args,**kwargs):calls.append(args[0].garment_id);return original(self,*args,**kwargs)
    monkeypatch.setattr(type(POLICY),'fact',counted)
    tracemalloc.start();started=time.perf_counter()
    prepared=PreparedAttributeConditions.prepare(rq,collection,POLICY)
    independent=IndependentAttributeVerifier.prepare(rq,collection,POLICY)
    preparation_seconds=time.perf_counter()-started
    assert len(calls)==size*2
    calls.clear()
    def forbidden(*args,**kwargs):raise AssertionError('External/source call inside candidate loop')
    monkeypatch.setattr(type(POLICY),'fact',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    started=time.perf_counter();examined=0
    uppers=[g for g in collection if g.snapshot.structural_role=='top']
    lowers=[g for g in collection if g.snapshot.structural_role=='bottom']
    outers=[g for g in collection if g.snapshot.structural_role=='outerwear']
    for upper in uppers:
        for lower in lowers:
            for outer in (None,*outers):
                members=(('upper',upper.snapshot.garment_id),('lower',lower.snapshot.garment_id))
                if outer:members=(*members,('outerwear',outer.snapshot.garment_id))
                assert prepared.evaluate_members(members)=='Pass'
                assert independent.decision(members)=='Pass'
                examined+=1
    hard_filter_seconds=time.perf_counter()-started
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert examined==(38148 if size==100 else 0)
    assert len(prepared.verdicts)==size and not calls
    # Restore file access only for writing this disposable measurement.
    monkeypatch.undo()
    (tmp_path/'measurement.json').write_text(json.dumps(dict(size=size,structural_examined=examined,
        preparation_seconds=preparation_seconds,hard_filter_seconds=hard_filter_seconds,
        traced_peak_bytes=peak,source_fact_calls=size*2,candidate_external_calls=0)),encoding='utf-8')


def test_more_than_100_captured_descriptions_fails_before_enumeration():
    item=make_member('A','pattern','plain')
    with pytest.raises(AttributeRequestError):PreparedAttributeConditions.prepare(condition('pattern','plain'),[item]*101,POLICY)


def test_maximum_chain_transport_and_unrelated_receipts_are_bounded(captured,tmp_path):
    import sqlite3,uuid
    from app.infrastructure.persistence.refinement_lineage_query import read_chain,bounded_record
    from app.domain.value_objects.recommendation_refinement import step_key
    root=str(uuid.uuid4());ids=[root]+[str(uuid.uuid4()) for _ in range(9)]
    value={'attribute_selection':captured.to_dict(),'refinement':{'root_id':root}}
    provenance=bounded_provenance(value).ljust(589824,' ')
    score=json.dumps('x'*262142);request=json.dumps('x'*65534)
    assert tuple(map(lambda v:len(v.encode()),(provenance,score,request)))==(589824,262144,65536)
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript('''CREATE TABLE recommendations(id TEXT PRIMARY KEY,user_id TEXT,chat_id TEXT,recommendation_type TEXT);
        CREATE TABLE nlp_chats(id TEXT PRIMARY KEY,user_id TEXT,request_text TEXT,extracted_entities_json TEXT);
        CREATE TABLE recommendation_metadata(recommendation_id TEXT PRIMARY KEY,provenance_json TEXT,score_json TEXT);
        CREATE TABLE recommendation_submissions(user_id TEXT,operation TEXT,submission_key TEXT,recommendation_id TEXT,
            UNIQUE(user_id,operation,submission_key));''')
    for n,identifier in enumerate(ids):
        conn.execute('INSERT INTO recommendations VALUES (?,?,?,?)',(identifier,'owner-A',identifier,'assistant'))
        conn.execute('INSERT INTO nlp_chats VALUES (?,?,?,?)',(identifier,'owner-A','Synthetic transport fixture',request))
        conn.execute('INSERT INTO recommendation_metadata VALUES (?,?,?)',(identifier,provenance,score))
        if n:conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?)',('owner-A','assistant',step_key(root,n),identifier))
    for n in range(500):conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?)',('owner-A','assistant','unrelated-'+str(n),'absent'))
    queries=[];conn.set_trace_callback(queries.append);tracemalloc.start();started=time.perf_counter()
    parent,chain=read_chain(conn,'owner-A',ids[-1]);elapsed=time.perf_counter()-started
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(chain)==10 and len(queries)==3 and parent['id']==ids[-1]
    payload=sum(len(row[key].encode()) for row in chain for key in ('provenance_json','score_json','extracted_entities_json'))
    assert payload==9175040
    with pytest.raises(ValueError):bounded_record({**parent,'provenance_json':provenance+' '})
    with pytest.raises(LookupError):read_chain(conn,'foreign-account',ids[-1])
    (tmp_path/'maximum-chain-transport.json').write_text(json.dumps(dict(records=10,unrelated_receipts=500,selects=3,
        payload_bytes=payload,seconds=elapsed,traced_peak_bytes=peak,
        semantic_status='Deliberately nonsemantic upper-size transport fixture; not ten valid recommendations or a formal NFR acceptance.')),encoding='utf-8')
    conn.close()
