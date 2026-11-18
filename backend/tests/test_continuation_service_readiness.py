"""Focused exhaustion and subsequent service use; all data is disposable."""
from tests.test_mixed_wardrobe_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

def test_single_base_exhaustion_then_soft_request_and_receipt(mixed):
    client,s,pid,_,_,_=mixed
    raw='I need an orange checked top and white cotton trousers.'
    root=post(client,pid,raw);assert root.status_code==201,root.text
    r=root.json();a=r['development_continuation']['next_action'];assert a
    with s.connection() as c:before=c.execute('select count(*) from recommendations').fetchone()[0]
    exhausted=post(client,pid,raw,a['submission_key'],refinement=a['refinement'])
    assert exhausted.status_code==200 and exhausted.json()['outcome']=='RefinementExhausted',exhausted.text
    with s.connection() as c:assert c.execute('select count(*) from recommendations').fetchone()[0]==before
    soft=post(client,pid,"I'd prefer blue trousers.");assert soft.status_code==201,soft.text
    data=soft.json();key=data['provenance']['phase2nd_mixed_selection']['receipt']
    assert post(client,pid,data['request_text'],key).json()['id']==data['id']
    assert client.get('/api/v1/chats/'+data['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
