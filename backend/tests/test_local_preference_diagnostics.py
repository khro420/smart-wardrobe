"""Disposable authenticated diagnostics; frozen parser and scores stay unchanged."""
import json
import pytest
from tests.test_local_preference_activation import enabled,post
from tests.test_request_local_persistence import (
    local_store,category_api,language_api,palette_api,p2_api,attribute_api,
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,
    release,lifecycle,runtime_boundary,counts,restrict)
from app.application.ports.assistant_runtime import assistant_service


def clear_fixture_primary_sources(repo):
    # The confirmed query legitimately falls back to the two JSON mirrors.
    # Clear every primary input in disposable rows, not just the SQL column.
    with repo._connect() as conn:
        for row in conn.execute('SELECT id,attributes_json,additional_attributes FROM garments').fetchall():
            mirrors=[json.loads(row[key]) for key in ('attributes_json','additional_attributes')]
            for value in mirrors:
                value.pop('primary_colour',None);value.pop('primary_color',None)
            conn.execute('UPDATE garments SET primary_colour=NULL,attributes_json=?,additional_attributes=? WHERE id=?',
                (json.dumps(mirrors[0]),json.dumps(mirrors[1]),row['id']))


@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
def test_conflicting_wish_is_reported_even_when_hard_evidence_is_unknown(enabled,engine):
    client,repo,_,_,female=enabled
    assistant_service().local_preferences.engine=engine
    clear_fixture_primary_sources(repo)
    before=counts(repo)
    reply=post(client,female,'I need black trousers, preferably blue.')
    assert reply.status_code==200,reply.json().get('outcome')
    result=reply.json()
    assert result['outcome']=='InsufficientEvidence'
    assert result['optional_resolution']=='ContradictedByHard'
    assert result['context_reason']=='hard_evidence_unknown_conflicting_preference'
    assert result['mandatory']['passed']==0 and result['mandatory']['unknown']>0
    assert counts(repo)==before


@pytest.mark.parametrize('text',["I'd prefer black trousers.",'I need trousers, preferably black.'])
def test_unknown_wish_preserves_baseline_and_full_history(enabled,text):
    client,repo,_,_,female=enabled
    restrict(client,repo,['Blue T-shirt','Black Trousers'])
    clear_fixture_primary_sources(repo)
    reply=post(client,female,text)
    assert reply.status_code==201,reply.text
    result=reply.json();display=result['scoring_display'];decision=display['decision']
    assert decision['selected']['key']==decision['baseline']['key']
    assert decision['explanation']=='original_baseline_retained'
    assert decision['selected_optional']['state']=='Unverifiable'
    assert decision['optional_counts']['Satisfied']==0 and decision['promotable']==[]
    history=client.get('/api/v1/chats/'+result['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
    assert history.status_code==200 and history.json()['recommendation']['scoring_display']==display


@pytest.mark.parametrize('text,reason',[
    ('Id prefer black trousers','soft_preference_apostrophe_required'),
    ("I'd prefer a cotton shirt.",None)])
def test_unsupported_frames_remain_refused_without_writes(enabled,text,reason):
    client,repo,_,_,female=enabled;before=counts(repo)
    result=post(client,female,text)
    assert result.status_code==422 and result.json()['outcome']=='UnsupportedSoftPreference'
    assert result.json().get('context_reason')==reason
    assert counts(repo)==before


def test_active_capability_does_not_claim_all_text_preferences_are_disabled(enabled):
    client,_,_,_,_=enabled
    result=client.get('/api/v1/recommendations/capabilities').json()
    assert result['local_preferences']['enabled']
    assert 'separate opt-in P1/C1' in result['language_understanding']['soft_requests']
    assert result['attributes']['grammar_version']=='conversational-attribute-grammar-1.6.0'
    assert result['local_preferences']['grammar_version']=='conversational-attribute-grammar-1.7.0'
