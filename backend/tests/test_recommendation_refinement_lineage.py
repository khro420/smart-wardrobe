"""Stored-chain and index controls, without a private database or app initializer."""
from fractions import Fraction as F
from dataclasses import replace
from copy import deepcopy
import json,sqlite3
import pytest
from tests.test_recommendation_refinement_ranking import rank
from tests.test_context_relevance_ranking import rows
from app.domain.value_objects.recommendation_refinement import RefinementPlan,RefinementAction,digest,step_key
from app.application.recommendation.refinement_verifier import finalize_supplement,request_digest,snapshot_digest,preference_digest
from app.application.recommendation.refinement_lineage_service import validate_chain,continuation
from app.application.recommendation.refinement_selector import base_signature
from app.application.recommendation.decision_score_codec import score_to_json
from app.infrastructure.persistence.refinement_lineage_query import read_chain


def records(count=2):
    result=[];seen=[];plan=RefinementPlan();text="I'm going shopping."
    for ordinal in range(count):
        ranked=rank(text,plan);assert ranked.status=='Selected'
        score=ranked.winner.score;relative=json.loads(ranked.ranking_evidence);payload=relative['context_plan']['request']
        identifier=f'00000000-0000-4000-8000-{ordinal+1:012d}'
        action=RefinementAction('alternative',parent_recommendation_id=result[-1]['id']) if ordinal else None
        supplement=finalize_supplement(plan,identifier,action,score,relative,
            snapshot_digest(rows()),preference_digest('owner',()),request_digest(text,payload,()))
        row=dict(id=identifier,user_id='owner',request_text=text,extracted_entities_json=json.dumps(payload),
            provenance_json=json.dumps({'context_relevance':relative,'refinement':supplement}),score_json=score_to_json(score))
        if ordinal:row['submission_key']=step_key(result[0]['id'],ordinal)
        result.append(row);seen.append(base_signature(ranked.winner.verified.candidate))
        plan=RefinementPlan(root_id=result[0]['id'],parent_id=identifier,ordinal=ordinal+1,
            root_R=F(1),root_total=F(4,5),seen=tuple(seen))
    return result


def test_chain_and_stale_parent_plan_are_exact():
    saved=records()
    assert len(validate_chain('owner',saved))==2
    plan,request=continuation('owner',saved[0],saved,saved[0]['request_text'],step_key(saved[0]['id'],1))
    assert plan.ordinal==1 and len(plan.seen)==1
    assert digest(request.to_dict())==digest(json.loads(saved[0]['extracted_entities_json']))
    with pytest.raises(ValueError):continuation('owner',saved[0],saved,saved[0]['request_text'],'arbitrary-key')
    with pytest.raises(LookupError):validate_chain('another-owner',saved)


@pytest.mark.parametrize('field,value',[
    ('root_R',{'numerator':'0','denominator':'1'}),('ordinal',3),
    ('seen_sha256','f'*64),('selection_scope_sha256','a'*64),
    ('policy_sha256','b'*64),('root_id','00000000-0000-4000-8000-000000000009'),
    ('excluded_categories',['trousers']),('request_fingerprint_version',1),
])
def test_forged_stored_lineage_rejected(field,value):
    saved=records();provenance=json.loads(saved[1]['provenance_json'])
    provenance['refinement'][field]=value;saved[1]['provenance_json']=json.dumps(provenance)
    with pytest.raises(ValueError):validate_chain('owner',saved)


def test_bounded_index_read_and_missing_foreign_parent():
    saved=records();conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript('''CREATE TABLE recommendations(id TEXT PRIMARY KEY,user_id TEXT,chat_id TEXT,recommendation_type TEXT);
      CREATE TABLE nlp_chats(id TEXT PRIMARY KEY,user_id TEXT,request_text TEXT,extracted_entities_json TEXT);
      CREATE TABLE recommendation_metadata(recommendation_id TEXT PRIMARY KEY,provenance_json TEXT,score_json TEXT);
      CREATE TABLE recommendation_submissions(user_id TEXT,operation TEXT,submission_key TEXT,fingerprint TEXT,recommendation_id TEXT UNIQUE,PRIMARY KEY(user_id,operation,submission_key));''')
    for row in saved:
        conn.execute('INSERT INTO recommendations VALUES (?,?,?,?)',(row['id'],'owner',row['id'],'assistant'))
        conn.execute('INSERT INTO nlp_chats VALUES (?,?,?,?)',(row['id'],'owner',row['request_text'],row['extracted_entities_json']))
        conn.execute('INSERT INTO recommendation_metadata VALUES (?,?,?)',(row['id'],row['provenance_json'],row['score_json']))
        conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)',('owner','assistant',row.get('submission_key','initial'),'hash',row['id']))
    for i in range(500):conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)',('owner','assistant',f'unrelated-{i}','h',f'unrelated-{i}'))
    statements=[];conn.set_trace_callback(statements.append)
    parent,chain=read_chain(conn,'owner',saved[1]['id'])
    assert parent['id']==saved[1]['id'] and len(chain)==2
    assert len(statements)==3 and all(s.startswith('SELECT') for s in statements)
    validate_chain('owner',chain)
    with pytest.raises(LookupError):read_chain(conn,'foreign',saved[0]['id'])
    explain=conn.execute("EXPLAIN QUERY PLAN SELECT recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation=? AND submission_key IN (?,?)",('owner','assistant','a','b')).fetchall()
    assert any('INDEX' in row['detail'] and 'user_id=? AND operation=? AND submission_key=?' in row['detail'] for row in explain)
    conn.close()


def test_scope_hash_detects_competitor_and_preferences():
    original=rows();changed=[replace(g,updated_at='changed') if g.garment_id=='G08' else g for g in original]
    assert snapshot_digest(original)!=snapshot_digest(changed)
    assert snapshot_digest(original)==snapshot_digest(original[::-1])
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    assert preference_digest('owner',())!=preference_digest('owner',(PreferenceSnapshot('p','owner','colours','{"values":["green"]}','1'),))


@pytest.mark.parametrize('kind',['below_floor','already_seen'])
def test_remaining_blocker_must_belong_to_remaining_floor_pool(kind):
    saved=records();provenance=json.loads(saved[1]['provenance_json']);relative=provenance['context_relevance']
    from app.domain.value_objects.context_relevance import ratio
    relative['coverage']['point_candidates']-=1;relative['coverage']['unresolved_candidates']=1
    high=F(1,2) if kind=='below_floor' else F(1)
    relative['strongest_unresolved']={'key':[['one_piece','G06']] if kind=='below_floor' else [['upper','G01'],['lower','G04']],
        'R_low':ratio(F(0)),'R_high':ratio(high),'optimistic':[ratio(F(3,5)*high+F(2,5)),ratio(high),ratio(F(1)),ratio(F(1))]}
    # 7/10 bound ties this selected 7/10 alternative; its R=1 wins the secondary comparator.
    relative['coverage']['global_optimum_certified']=kind=='below_floor'
    saved[1]['provenance_json']=json.dumps(provenance)
    with pytest.raises(ValueError,match='below the original floor|already selected base'):validate_chain('owner',saved)



def test_ten_slot_upper_bound_transport_and_supplement_rejection(tmp_path):
    import time,tracemalloc
    from app.domain.value_objects.context_relevance import RelativeEncodingLimit
    from app.application.recommendation.refinement_verifier import validate_refinement
    from app.application.recommendation.decision_score_codec import score_from_json
    saved=records();record=saved[0];proof=json.loads(record['provenance_json'])
    oversized=deepcopy(proof['refinement']);oversized['root_id']='x'*32768
    with pytest.raises(RelativeEncodingLimit):
        validate_refinement(oversized,proof['context_relevance'],score_from_json(record['score_json']),record['id'],record['request_text'],json.loads(record['extracted_entities_json']))
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript("CREATE TABLE recommendations(id TEXT PRIMARY KEY,user_id TEXT,chat_id TEXT,recommendation_type TEXT);CREATE TABLE nlp_chats(id TEXT PRIMARY KEY,user_id TEXT,request_text TEXT,extracted_entities_json TEXT);CREATE TABLE recommendation_metadata(recommendation_id TEXT PRIMARY KEY,provenance_json TEXT,score_json TEXT);CREATE TABLE recommendation_submissions(user_id TEXT,operation TEXT,submission_key TEXT,fingerprint TEXT,recommendation_id TEXT UNIQUE,PRIMARY KEY(user_id,operation,submission_key));")
    root=record['id']
    for ordinal in range(10):
        identifier=f'00000000-0000-4000-8000-{ordinal+1:012d}'
        raw=json.dumps({'refinement':{'root_id':root},'padding':''},separators=(',',':'))
        # Size-only transport fixture: intentionally not a valid semantic proof.
        raw=raw.replace('"padding":""','"padding":"'+'x'*(327680-len(raw))+'"');assert len(raw)==327680
        conn.execute('INSERT INTO recommendations VALUES (?,?,?,?)',(identifier,'owner',identifier,'assistant'))
        conn.execute('INSERT INTO nlp_chats VALUES (?,?,?,?)',(identifier,'owner','request','{}'))
        conn.execute('INSERT INTO recommendation_metadata VALUES (?,?,?)',(identifier,raw,'x'*262144))
        conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)',('owner','assistant',step_key(root,ordinal) if ordinal else 'initial','hash',identifier))
    for n in range(500):conn.execute('INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)',('owner','assistant',f'unrelated-{n}','hash',f'unrelated-{n}'))
    statements=[];conn.set_trace_callback(statements.append);tracemalloc.start();start=time.perf_counter()
    parent,chain=read_chain(conn,'owner',identifier)
    elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(chain)==10 and len(statements)==3
    assert sum(len(r['provenance_json'])+len(r['score_json']) for r in chain)==5898240
    conn.execute("UPDATE recommendation_metadata SET provenance_json=provenance_json||'x' WHERE recommendation_id=?",(identifier,))
    with pytest.raises(ValueError,match='Oversized'):read_chain(conn,'owner',identifier)
    conn.close()
    (tmp_path/'maximum-chain-transport.json').write_text(json.dumps({'semantic_validity':False,'purpose':'fixed indexed transport/size boundary only','records':10,'bytes':5898240,'selects':3,'seconds':elapsed,'peak_bytes':peak},indent=2))
