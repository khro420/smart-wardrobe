"""Exact labelled rules and full mixed-source scoring; disposable data only."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import copy,json,uuid
import pytest
from tests.test_mixed_context_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post,CONTEXTS)
from app.development.mixed_wardrobe import core,context_selection,gateway
from app.development.mixed_wardrobe.fashion import FashionFacts
from app.development.mixed_wardrobe.fashion_policy import pair_value,policy
from app.development.mixed_wardrobe.fashion_contract import ENV,PROFILE,versions
from app.development.mixed_wardrobe.store import Store,FixtureError
from app.application.recommendation.decision_score_codec import score_from_json,score_to_json
from app.domain.value_objects.attribute_conditions import AttributeRequestError


def frozen():
    from tests.test_context_relevance_ranking import rows
    return tuple(core.FixtureRow(g,{'category':g.category,'primary_colour':g.primary_colour,'pattern':'plain','sleeve_length':'wrist-length' if g.category.startswith('long_') else 'short' if g.category.startswith('short_') else None,'silhouette':'regular','style':list(g.style_tags)}) for g in rows())

def scope():return {'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}

@pytest.mark.parametrize('kind,a,b,expected',[
 ('colour','black','white',F(1)),('colour','red','green',F(3,4)),('colour','red','yellow',F(1,4)),
 ('style','casual','smart casual',F(3,4)),('style','formal','sporty',F(1,4)),
 ('pattern','stripe','plain',F(1)),('pattern','plain','plain',F(3,4)),('pattern','stripe','floral',F(1,4)),
 ('layering','wrist-length','short',F(1,2)),('layering','short','wrist-length',F(1)),
 ('silhouette','regular','loose',F(1)),('silhouette','regular','regular',F(3,4)),('silhouette','peplum','regular',None),
])
def test_independently_labelled_rules(kind,a,b,expected):assert pair_value(kind,a,b)==expected


def test_exact_weighting_unknown_no_pair_and_source_provenance():
    rows=frozen();a,b=rows[0],rows[2]
    a=replace(a,declaration={**a.declaration,'primary_colour':'red','style':['casual'],'pattern':'stripe'})
    b=replace(b,declaration={**b.declaration,'primary_colour':'green','style':['smart casual'],'pattern':'plain'})
    key=(('upper',a.snapshot.garment_id),('lower',b.snapshot.garment_id))
    x=FashionFacts((a,b),None,'scope',False);y=FashionFacts((a,b),None,'scope',True)
    assert x.component(key)==y.component(key)
    assert json.loads(core.encoded(x.describe(key)))==x.describe(key)
    assert x.component(key).summary.value==F(55,68)
    assert sum(F(d['total_contribution']) for d in x.describe(key)['factors'])==F(11,68)
    unknown=tuple(replace(r,declaration={'category':r.snapshot.category}) for r in (a,b))
    c=FashionFacts(unknown,None,'scope',False).component(key)
    assert c.summary.state=='Unknown' and c.summary.value is None and c.contribution==0
    assert all(d.state in ('Unknown','NotApplicable') for d in c.details)
    dress=rows[5];single=FashionFacts((dress,),None,'scope',True).component((('one_piece',dress.snapshot.garment_id),))
    assert single.summary.state=='NotApplicable' and single.summary.value is None
    assert all(s['source']=='synthetic_fixture_declaration' for s in x.describe(key)['sources'])
    with pytest.raises(ValueError):x.component((('upper','foreign'),))


@pytest.mark.parametrize('raw',['Recommend an outfit.','I need jeans.',"I'd prefer black trousers.",'I need grey trousers, not a grey shirt.'])
def test_neutral_reference_compact_independent_and_old_score_codec(monkeypatch,raw):
    rows=frozen();rows=tuple(replace(r,declaration={**r.declaration,'material':['denim'] if r.snapshot.category=='trousers' else ['cotton']}) for r in rows)
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
    a=core.select(scope(),raw,'wearer',_fashion=FashionFacts)
    b=core.select(scope(),raw,'wearer','compact_exhaustive',_fashion=FashionFacts)
    c=core.select(scope(),raw,'wearer',independent=True,_fashion=FashionFacts)
    assert a==b==c
    if a['status']=='Selected':
        score=score_from_json(json.dumps(a['selected']['score']))
        assert score_from_json(score_to_json(score))==score and score.profile_name==PROFILE
        assert score.total==F(3,5)*score.request_match.contribution+F(1,5)*score.compatibility.contribution+F(1,5)*score.preference.contribution
        bad=copy.deepcopy(a['selected']['score']);bad['weights'][0]={'numerator':1,'denominator':1}
        with pytest.raises(ValueError):score_from_json(json.dumps(bad))
    old=core.select(scope(),raw,'wearer')
    if old['status']=='Selected':assert score_from_json(json.dumps(old['selected']['score'])).profile_name!=PROFILE


@pytest.mark.parametrize('sid,raw',list(CONTEXTS.items()),ids=list(CONTEXTS))
def test_all_18_contexts_same_admission_three_engines(monkeypatch,sid,raw):
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen())
    old=context_selection.select(scope(),raw,'wearer')
    a=context_selection.select(scope(),raw,'wearer',_fashion=FashionFacts)
    b=context_selection.select(scope(),raw,'wearer','compact_exhaustive',_fashion=FashionFacts)
    c=context_selection.select(scope(),raw,'wearer',independent=True,_fashion=FashionFacts)
    assert a==b==c and a['status']=='Selected'
    assert a['mandatory']==old['mandatory']
    assert a['fashion']['context']['situation']==sid and not a['fashion']['context']['double_counted']
    assert a['fashion']['context']['channel'] in ('existing_request_R','compatibility_style')
    assert score_from_json(json.dumps(a['selected']['score'])).profile_name==PROFILE


def test_interview_default_and_refusals_unchanged(monkeypatch):
    from app.development.mixed_wardrobe import interview_default
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen())
    for role in ('candidate','interviewer'):
        raw=f'I need an outfit for a job interview as the {role}.'
        a=context_selection.select(scope(),raw,'wearer',_interpret=interview_default.document,_fashion=FashionFacts)
        b=context_selection.select(scope(),raw,'wearer',independent=True,_interpret=interview_default.document,_fashion=FashionFacts)
        assert a==b and a['context']['interview_default']['message']==interview_default.MESSAGE
        assert a['intent']['request']['formality'] is None and a['fashion']['context']['targets']==['smart casual']
        assert a['fashion']['context']['channel']=='existing_request_R'
    with pytest.raises(AttributeRequestError):interview_default.document('I need a formal outfit for a job interview as the candidate.')


def test_fashion_authenticated_mixed_persistence_and_locked_independence(mixed,monkeypatch):
    client,s,pid,ids,_,_=mixed;owner=s.catalog['owner_id']
    old=post(client,pid,'I need jeans.');assert old.status_code==201,old.text
    oldproof=old.json()['provenance']['phase2nd_mixed_selection']
    monkeypatch.setenv(ENV,PROFILE);s=gateway.open_store(enabled=True)
    assert client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['compatibility']['enabled']
    def counts():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
    before=counts();original=gateway.mirror;key=uuid.uuid4().hex
    def fail(c,*args):original(c,*args);raise ValueError('injected fashion rollback')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fail);assert post(client,pid,'I need jeans.',key).status_code==503
    assert counts()==before
    r=post(client,pid,'I need a purple top and denim trousers.',key);assert r.status_code==201,r.text
    data=r.json();proof=data['provenance']['phase2nd_mixed_selection']
    assert proof['version']==versions()[core.VERSION] and data['score_metadata']['profile_name']==PROFILE
    assert {x['source'] for x in proof['decision']['items']}=={'normal_B0_B1','synthetic_fixture_declaration'}
    # Unreviewed original material remains unqualified despite a Jeans name.
    with s.connection() as c:
        catalog=s.capture(c,owner,pid)
    original_row=next(x for x in core.rows_from_catalog(catalog,'female') if isinstance(x,core.OriginalRow) and x.snapshot.garment_id==ids['Blue Jeans'])
    assert core.fact(original_row,'material','scope').state not in ('Known','KnownEmpty')
    assert post(client,pid,'I need a purple top and denim trousers.',key).json()['id']==data['id']
    assert post(client,pid,'I need jeans.',key).status_code==409
    history=client.get('/api/v1/chats/'+data['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert history.status_code==200 and history.json()['recommendation']['mixed_wardrobe_display']==data['mixed_wardrobe_display']
    for item in data['items']:assert client.get('/api/v1/media/'+item['preferred_media_id']).status_code==200
    # Genuine server-bound child retains the new scoring contract and excludes bases.
    action=data['development_continuation']['next_action'];assert action
    child=post(client,pid,data['request_text'],action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text
    cp=child.json()['provenance']['phase2nd_mixed_selection'];assert cp['version']==proof['version'] and cp['ordinal']==1
    assert s.base(cp['decision'])!=s.base(proof['decision'])
    assert post(client,pid,data['request_text'],action['submission_key'],refinement=action['refinement']).json()['replayed']
    assert s.action('unused',{**cp,'ordinal':9}) is None
    soft=post(client,pid,'I need trousers, preferably black.');assert soft.status_code==201,soft.text
    assert soft.json()['development_continuation']['next_action'] is None
    forged=copy.deepcopy(proof);forged['decision']['fashion']['policy_sha256']='0'*64
    with s.connection() as c:
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(forged).decode(),core.digest(forged),s.sign(forged),data['id']))
        with pytest.raises(FixtureError,match='IndependentFixtureHistoryMismatch'):s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(data['id'],)).fetchone(),owner)
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(proof).decode(),core.digest(proof),s.sign(proof),data['id']))
    # Malformed first-pass profile metadata is refused before persistence.
    before=counts();apply=FashionFacts.apply
    def corrupt(self,key,score):
        result=apply(self,key,score)
        return result if self.independent else replace(result,policy_version='invalid-first-pass')
    with monkeypatch.context() as m:
        m.setattr(FashionFacts,'apply',corrupt);assert post(client,pid,'I need jeans.').status_code==503
    assert counts()==before
    monkeypatch.delenv(ENV)
    for saved in (data,old.json()):assert client.get('/api/v1/chats/'+saved['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
    with s.connection() as c:
        assert json.loads(c.execute('select proof_json from phase2nd_mixed_proofs where id=?',(old.json()['id'],)).fetchone()[0])==oldproof
    # New writes require the exact current source; historical replay stays immutable.
    def change():
        with s.connection() as c:c.execute("update garments set name='changed during fashion pass' where id=?",(ids['Blue Jeans'],))
    s.config['fashion_profile']=PROFILE
    with pytest.raises(FixtureError,match='ChangedFixtureSource'):s.recommend(owner,pid,'I need jeans.',uuid.uuid4().hex,before_lock=change)


def test_validly_encoded_first_pass_numeric_tamper_is_rejected_under_lock(mixed,monkeypatch):
    from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore
    client,_,pid,_,_,_=mixed;monkeypatch.setenv(ENV,PROFILE);s=gateway.open_store(enabled=True)
    with s.connection() as c:before=c.execute('select count(*) from recommendations').fetchone()[0]
    apply=FashionFacts.apply
    def corrupt(self,key,score):
        result=apply(self,key,score)
        if self.independent:return result
        r=ComponentScore(ScoreEvidence('request_match',F(1),'Available',1,1))
        altered=replace(result,request_match=r,total=F(3,5)+F(1,5)*result.compatibility.contribution+F(1,5)*result.preference.contribution)
        assert score_from_json(score_to_json(altered))==altered
        return altered
    monkeypatch.setattr(FashionFacts,'apply',corrupt)
    r=post(client,pid,'I need jeans.')
    assert r.status_code==409 and r.json()['status']=='IndependentFixtureWriteMismatch',r.text
    with s.connection() as c:assert c.execute('select count(*) from recommendations').fetchone()[0]==before
