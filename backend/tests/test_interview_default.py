"""Interview inference is a policy setting, not an observed dress-code fact."""
from dataclasses import replace
import copy
import json
import uuid
import pytest
from tests.test_mixed_context_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)
from app.development.mixed_wardrobe import interview_default as default, context_language as archived, context_selection as selection, core, gateway
from app.development.mixed_wardrobe.interview_default_contract import ENV,PROFILE,VERSION
from app.development.mixed_wardrobe.context_contract import ENV as CONTEXT_ENV,PROFILE as CONTEXT_PROFILE
from app.development.mixed_wardrobe.context_language_contract import ENV as LANGUAGE_ENV,PROFILE as LANGUAGE_PROFILE
from app.application.recommendation.attribute_preference_codec import restore_request
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from app.development.mixed_wardrobe.store import FixtureError


@pytest.mark.parametrize('raw,role',[
    ('I need an outfit for a job interview as the candidate.','candidate'),
    ('I need an outfit for a job interview as the interviewer.','interviewer'),
    ("I'm being interviewed for a position.",'candidate'),
    ("I'm interviewing job applicants.",'interviewer'),
    ('IM BEING INTERVIEWED FOR A JOB, I NEED TROUSERS.','candidate'),
    ("I'm being interviewed for a job, preferably with a white shirt.",'candidate'),
    ("I need an outfit for a job interview as the candidate, no shorts.",'candidate'),
])
def test_omission_is_inferred_without_changing_observations(raw,role):
    d=default.document(raw);observed=d['request'];effective=d['evaluation_request']
    assert d['normalization']['original_text']==raw and observed['context']['role']['values']==[role]
    assert observed['formality'] is None and observed['context']['dress_code']['state']=='Unspecified' and observed['context']['formality']['state']=='Unspecified'
    assert effective['formality']=='smart_casual' and effective['context']==observed['context']
    assert not any(s['slot'] in ('formality','dress_code') for s in d['original_context_spans'])
    assert d['interview_default']['inferred'] and d['interview_default']['origin']=='approved_policy_default'
    assert d['interview_default']['verified_dress_code'] is False and d['interview_default']['message']==default.MESSAGE
    for s in d['original_hard_spans']+d['original_optional_spans']+d['original_context_spans']:
        assert raw[s['start']:s['end']]==s['text']
    with pytest.raises(AttributeRequestError):archived.document(raw)


@pytest.mark.parametrize('role',['candidate','interviewer'])
def test_explicit_smart_casual_is_never_labelled_inferred(role):
    raw=f'I need a smart casual outfit for a job interview as the {role}.'
    d=default.document(raw);old=archived.document(raw)
    assert d['request']==old['request']==d['evaluation_request']
    assert d['interview_default']['inferred'] is False and d['interview_default']['origin']=='user_specified'
    assert d['interview_default']['message'] is None


@pytest.mark.parametrize('raw',[
    'I need a formal outfit for a job interview as the candidate.',
    'I need a casual outfit for a job interview as the interviewer.',
    'I need an outfit for a job interview as the candidate; the dress code is black tie.',
    'I need an outfit for a job interview.',
    'I need an outfit for a job interview as the candidate and interviewer.',
    'I am not going to a job interview as the candidate.',
    'I need an outfit for a job interview as the candidate, not smart casual.',
    'I need a waterproof outfit for a job interview as the candidate.',
])
def test_no_default_for_explicit_unsupported_negated_or_ambiguous_requests(raw):
    with pytest.raises(AttributeRequestError):default.document(raw)


@pytest.mark.parametrize('role',['candidate','interviewer'])
def test_three_engine_winner_scores_equal_existing_explicit_policy(role,monkeypatch):
    from tests.test_context_relevance_ranking import rows
    from app.development.main_fixture.core import FixtureRow
    frozen=tuple(FixtureRow(g,{'category':g.category,'style':list(g.style_tags),'primary_colour':g.primary_colour}) for g in rows())
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen)
    v={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
    raw=f'I need an outfit for a job interview as the {role}.'
    explicit=f'I need a smart casual outfit for a job interview as the {role}.'
    expected=selection.select(v,explicit,'wearer',independent=True)
    a=selection.select(v,raw,'wearer',_interpret=default.document)
    b=selection.select(v,raw,'wearer','compact_exhaustive',_interpret=default.document)
    c=selection.select(v,raw,'wearer',independent=True,_interpret=default.document)
    assert a==b==c and a['status']=='Selected'
    for k in ('selected','baseline','mandatory','candidate_scores_sha256'):assert a[k]==expected[k]
    assert a['context']['interview_default']['message']==default.MESSAGE
    assert a['context']['summary']['formality'] is None
    assert a['context']['summary']['inferred_defaults']['verified_dress_code'] is False
    assert json.loads(core.encoded(a))==a


def test_missing_style_and_explicit_formality_denial_stay_strict():
    from tests.test_context_relevance_ranking import rows
    d=default.document('I need an outfit for a job interview as the candidate.')
    req=restore_request(d['evaluation_request']);e=EvaluatorSpecification.current('context_18_v1',interview_default=True).construct()
    good=rows()[1];missing=replace(good,style_tags=None)
    assert e.member_condition(good,req,'occasion')[0]=='Pass'
    missing_evaluator=EvaluatorSpecification.current('context_18_v1',interview_default=True).construct()
    assert missing_evaluator.member_condition(missing,req,'occasion')[0]=='Unknown'
    deny=replace(good,custom_tags=('rec:v1:formality:smart_casual:deny',))
    # A changed snapshot belongs to a separate resolver session.
    fresh=EvaluatorSpecification.current('context_18_v1',interview_default=True).construct()
    assert fresh.member_condition(deny,req,'formality')[0]=='Fail'
    assert not EvaluatorSpecification.current('context_18_v1').construct().supports(restore_request(d['request']))


def test_authenticated_persistence_message_history_receipts_rollback_and_old_reader(mixed,monkeypatch):
    client,_,pid,_,_,_=mixed
    monkeypatch.setenv(CONTEXT_ENV,CONTEXT_PROFILE);monkeypatch.setenv(LANGUAGE_ENV,LANGUAGE_PROFILE);monkeypatch.delenv(ENV,raising=False)
    explicit='I need a smart casual outfit for a job interview as the candidate.'
    old=post(client,pid,explicit);assert old.status_code==201,old.text
    oldp=old.json()['provenance']['phase2nd_mixed_selection']
    raw='I need an outfit for a job interview as the candidate.'
    assert post(client,pid,raw).status_code==422
    monkeypatch.setenv(ENV,PROFILE);s=gateway.open_store(enabled=True)
    cap=client.get('/api/v1/recommendations/capabilities').json();assert cap['mixed_wardrobe']['contextual']['interview_default']['enabled']
    def counts():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
    original=gateway.mirror;before=counts();key=uuid.uuid4().hex
    def fault(c,*args):original(c,*args);raise RuntimeError('Injected interview-default rollback')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fault);assert post(client,pid,raw,key).status_code==503
    assert counts()==before
    result=post(client,pid,raw,key);assert result.status_code==201,result.text
    r=result.json();p=r['provenance']['phase2nd_mixed_selection'];assert p['version']==VERSION
    assert p['decision']['intent']['request']['formality'] is None
    assert r['mixed_wardrobe_display']['decision']['context']['interview_default']['message']==default.MESSAGE
    assert post(client,pid,raw,key).json()['id']==r['id']
    assert post(client,pid,explicit,key).status_code==409
    history=client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert history.status_code==200 and history.json()['request_text']==raw
    assert history.json()['structured_request']['formality'] is None
    assert history.json()['recommendation']['mixed_wardrobe_display']==r['mixed_wardrobe_display']
    assert r['development_continuation']['next_action'] is None
    forged=copy.deepcopy(p);forged['decision']['intent']['interview_default']['inferred']=False
    with s.connection() as c:c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(forged).decode(),core.digest(forged),s.sign(forged),r['id']))
    with s.connection() as c:
        with pytest.raises(FixtureError,match='IndependentFixtureHistoryMismatch'):
            s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(r['id'],)).fetchone(),s.catalog['owner_id'])
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(p).decode(),core.digest(p),s.sign(p),r['id']))
    monkeypatch.delenv(ENV,raising=False)
    assert client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
    restored=client.get('/api/v1/chats/'+old.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert restored.status_code==200 and restored.json()['recommendation']['provenance']['phase2nd_mixed_selection']==oldp
