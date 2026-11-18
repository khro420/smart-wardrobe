from dataclasses import replace
from fractions import Fraction as F
import copy,json,uuid
import pytest
from tests.test_mixed_context_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)
from tests.test_fashion_compatibility_v2 import frozen,scope
from app.development.mixed_wardrobe import core,context_selection,gateway,personalization as p
from app.development.mixed_wardrobe.fashion import FashionFacts
from app.development.mixed_wardrobe.fashion_contract import ENV as FASHION_ENV,PROFILE as FASHION
from app.development.mixed_wardrobe.store import FixtureError
from app.domain.value_objects.recommendation_score import RecommendationScore,ComponentScore,ScoreEvidence

def data():return {'version':p.PROFILE,'policy_sha256':p.POLICY_SHA256,'owner':'owner','wearer':'wearer','recent':[],'feedback':[]}

def score(v=F(1,2)):
    c=ComponentScore(ScoreEvidence('test',v,'Available',1,1))
    return RecommendationScore(c,c,c,v,'test','test',(F(3,5),F(1,5),F(1,5)))

def test_exact_ties_exposure_explicit_feedback_and_no_inferred_dislike():
    a=(('upper','a'),('lower','b'));b=(('upper','c'),('lower','d'));c=(('upper','e'),('lower','f'))
    scores={a:score(),b:score(),c:score(F(1,4))};d=data()
    d['recent']=[{'id':'previous','created_at':'time','base':[list(x) for x in a]}]
    p.validate(d,'owner','wearer');chosen,view=p.choose(d,scores,a,None,())
    assert chosen==b and view['scores_unchanged'] and view['explicit_feedback'] is None
    d['feedback']=[{'id':'feedback','created_at':'time','base':[list(x) for x in b],'verdict':'dislike'}]
    assert p.choose(d,scores,a,None,())[0]==a
    assert p.choose(d,{b:score()},b,None,())[0]==b  # dislike is never an exclusion
    assert p.choose(d,scores,a,{'optional':True},())[0]==a
    assert p.choose(d,scores,a,None,(a,))[0]==a  # existing continuation owns ordering
    # A positive vote cannot promote an actually lower scoring outfit.
    d['feedback']=[{'id':'f','created_at':'time','base':[list(x) for x in c],'verdict':'like'}]
    assert p.choose(d,scores,a,None,())[0]!=c
    with pytest.raises(ValueError):p.validate(d,'foreign','wearer')
    with pytest.raises(ValueError):p.validate({**d,'recent':d['recent']*11},'owner','wearer')

@pytest.mark.parametrize('raw,context',[
    ('Recommend an outfit.',False),('I need jeans.',False),("I'd prefer black trousers.",False),
    ("I'm going shopping.",True),("I'm meeting friends for dinner.",True),
])
def test_preferences_three_engines_and_context(monkeypatch,raw,context):
    rows=tuple(replace(r,declaration={**r.declaration,'material':['denim'] if r.snapshot.category=='trousers' else ['cotton']}) for r in frozen())
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
    catalog=scope();catalog['original']['wearer']={'profile_id':'wearer'}
    catalog['original']['preferences']=[{'preference_id':'pref','user_id':'owner','preference_type':'colours','value_json':'{"values":["black"]}','weight':'1','source':'user_profile','is_active':True}]
    select=context_selection.select if context else core.select
    a=select(catalog,raw,'wearer',_fashion=FashionFacts,_personalization=data())
    b=select(catalog,raw,'wearer','compact_exhaustive',_fashion=FashionFacts,_personalization=data())
    c=select(catalog,raw,'wearer',independent=True,_fashion=FashionFacts,_personalization=data())
    assert a==b==c and a['status']=='Selected'
    assert a['selected']['score']['profile_name']==FASHION and a['personalization']['profile']==p.PROFILE

def test_authenticated_preferences_feedback_history_and_continuation(mixed,monkeypatch):
    client,_,pid,ids,_,_=mixed
    monkeypatch.setenv(FASHION_ENV,FASHION);monkeypatch.setenv(p.ENV,p.PROFILE)
    s=gateway.open_store(enabled=True);owner=s.catalog['owner_id']
    raw='Recommend an outfit.';key=uuid.uuid4().hex
    first=post(client,pid,raw,key);assert first.status_code==201,first.text
    a=first.json();pa=a['provenance']['phase2nd_mixed_selection']
    assert a['mixed_wardrobe_display']['decision']['personalization']['eligible_ties']>1
    second=post(client,pid,raw);assert second.status_code==201,second.text
    b=second.json();pb=b['provenance']['phase2nd_mixed_selection']
    assert s.base(pa['decision'])!=s.base(pb['decision'])
    assert pa['decision']['selected']['score']==pb['decision']['selected']['score']
    assert post(client,pid,raw,key).json()['id']==a['id']
    assert post(client,pid,'I need jeans.',key).status_code==409
    headers={'X-Wardrobe-Profile-Id':pid};url='/api/v1/recommendations/'+a['id']+'/feedback'
    def vote(verdict,wearer=pid):return client.put(url,headers=headers,json={'wearer_profile_id':wearer,'verdict':verdict})
    assert client.get(url+'?wearer_profile_id='+pid,headers=headers).json()['verdict'] is None
    assert vote('like').status_code==200
    with s.connection() as c:
        stored=c.execute('select * from user_preferences where preference_type=?',(p.FEEDBACK_TYPE,)).fetchone();before=dict(stored)
        assert stored['is_active']==0 and stored['weight']==0
    assert vote('like').status_code==200
    with s.connection() as c:assert dict(c.execute('select * from user_preferences where id=?',(stored['id'],)).fetchone())==before
    assert vote('dislike').json()['verdict']=='dislike'
    assert vote('like',str(uuid.uuid4())).status_code in (404,409)
    assert client.get(url+'?wearer_profile_id='+pid).status_code==200
    # Viewing/replaying has not changed the explicit verdict.
    assert client.get(url+'?wearer_profile_id='+pid,headers=headers).json()['verdict']=='dislike'
    action=a['development_continuation']['next_action'];assert action
    child=post(client,pid,raw,action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text
    cp=child.json()['provenance']['phase2nd_mixed_selection']
    assert cp['personalization']==pa['personalization'] and cp['ordinal']==1
    assert s.base(cp['decision'])!=s.base(pa['decision']) and s.action('unused',{**cp,'ordinal':9}) is None
    assert post(client,pid,raw,action['submission_key'],refinement=action['refinement']).json()['replayed']
    assert vote('clear').json()['verdict'] is None
    assert client.put('/api/v1/account/preferences/colours',headers=headers,json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
    fresh=post(client,pid,'I need jeans.');assert fresh.status_code==201,fresh.text
    fp=fresh.json()['provenance']['phase2nd_mixed_selection']
    assert fp['catalog']['original']['preferences'] and fp['decision']['selected']['score']['preference']['summary']['value'] is not None
    # Preference editing does not rewrite old P scores or records.
    history=client.get('/api/v1/chats/'+a['chat_id'],headers=headers);assert history.status_code==200,history.text
    assert history.json()['recommendation']['provenance']['phase2nd_mixed_selection']==pa
    def counts():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
    before=counts();original=gateway.mirror
    def fail(c,*args):original(c,*args);raise RuntimeError('injected personalized rollback')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fail);assert post(client,pid,'I need jeans.').status_code==503
    assert counts()==before
    # Changing only explicit feedback between passes is independently detected.
    def changed():assert vote('like').status_code==200
    with pytest.raises(FixtureError,match='ChangedPersonalizationSources'):s.recommend(owner,pid,raw,uuid.uuid4().hex,before_lock=changed)
    assert counts()==before
    assert vote('clear').status_code==200
    # A current feedback storage mutation cannot forge an explicit vote.
    with s.connection() as c:c.execute('update user_preferences set preference_value_json=? where preference_type=?',('{"invalid":true}',p.FEEDBACK_TYPE))
    assert client.get(url+'?wearer_profile_id='+pid,headers=headers).status_code==409
    # Immutable historical proof does not consult the overwritten feedback row.
    assert client.get('/api/v1/chats/'+a['chat_id'],headers=headers).status_code==200
    monkeypatch.delenv(p.ENV)
    assert client.get('/api/v1/chats/'+a['chat_id'],headers=headers).status_code==200

def test_new_interview_profile_and_policy_identity(monkeypatch):
    from app.development.mixed_wardrobe import interview_default
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen())
    catalog=scope();catalog['original']['wearer']={'profile_id':'wearer'}
    for role in ('candidate','interviewer'):
        raw=f'I need an outfit for a job interview as the {role}.'
        a=context_selection.select(catalog,raw,'wearer',_interpret=interview_default.document,_fashion=FashionFacts,_personalization=data())
        b=context_selection.select(catalog,raw,'wearer',independent=True,_interpret=interview_default.document,_fashion=FashionFacts,_personalization=data())
        assert a==b and a['context']['interview_default']['message']==interview_default.MESSAGE
    monkeypatch.setitem(p.POLICY,'history_limit',100)
    with pytest.raises(ValueError,match='Unregistered'):p.validate(data(),'owner','wearer')

def test_malformed_feedback_cannot_borrow_recent_source_shape():
    d=data();r={'id':'prior','created_at':'time','base':[['upper','a'],['lower','b']]}
    d['recent']=[r];d['feedback']=[r]
    with pytest.raises(ValueError,match='source fields'):p.validate(d,'owner','wearer')
    d['feedback']=[[]]
    with pytest.raises(ValueError,match='source fields'):p.validate(d,'owner','wearer')

def test_foreign_feedback_and_resigned_snapshot_tamper(mixed,monkeypatch):
    client,_,pid,_,_,_=mixed;monkeypatch.setenv(FASHION_ENV,FASHION);monkeypatch.setenv(p.ENV,p.PROFILE)
    s=gateway.open_store(enabled=True);r=post(client,pid,'I need jeans.');assert r.status_code==201,r.text
    saved=r.json();rid=saved['id'];proof=saved['provenance']['phase2nd_mixed_selection']
    email='foreign-'+uuid.uuid4().hex+'@example.test';password='Disposable-'+uuid.uuid4().hex
    assert client.post('/api/v1/account/register',json={'email':email,'password':password,'password_confirmation':password,'display_name':'Foreign fixture'}).status_code==201
    login=client.post('/api/v1/account/login',json={'email':email,'password':password});assert login.status_code==200
    headers={'Authorization':'Bearer '+login.json()['access_token'],'X-Wardrobe-Profile-Id':pid}
    url='/api/v1/recommendations/'+rid+'/feedback'
    assert client.get(url+'?wearer_profile_id='+pid,headers=headers).status_code in (403,404)
    assert client.put(url,headers=headers,json={'wearer_profile_id':pid,'verdict':'like'}).status_code in (403,404)
    with s.connection() as c:assert c.execute('select count(*) from user_preferences where preference_type=?',(p.FEEDBACK_TYPE,)).fetchone()[0]==0
    forged=copy.deepcopy(proof);forged['personalization']['owner']='foreign'
    with s.connection() as c:
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(forged).decode(),core.digest(forged),s.sign(forged),rid))
        with pytest.raises(ValueError,match='Foreign personalization'):s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(rid,)).fetchone(),s.catalog['owner_id'])
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(proof).decode(),core.digest(proof),s.sign(proof),rid))
