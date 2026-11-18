"""A spilled rollback-journal writer must not open a second media connection."""
from contextlib import contextmanager
import uuid
import pytest
from tests.test_mixed_wardrobe_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)
from app.development.mixed_wardrobe.store import Store,FixtureError
from app.application.ports.workflow_runtime import runtime


def test_spilled_writer_media_capture_receipt_and_history(mixed,monkeypatch):
    client,s,pid,ids,_,_=mixed
    original=Store.connection
    @contextmanager
    def constrained(self):
        with original(self) as c:
            # Disposable only: trigger the same exclusive lock with a small proof.
            assert c.execute('pragma journal_mode').fetchone()[0]=='delete'
            c.execute('pragma cache_size=1')
            yield c
    monkeypatch.setattr(Store,'connection',constrained)
    calls=[];adapter=runtime().media;path=adapter.path_for_owner
    def observed(*args):calls.append(args[0]);return path(*args)
    monkeypatch.setattr(adapter,'path_for_owner',observed)
    key=uuid.uuid4().hex;r=post(client,pid,'I need jeans.',key);assert r.status_code==201,r.text
    data=r.json();assert data['outcome']=='Selected'
    replay=post(client,pid,'I need jeans.',key);assert replay.status_code==200 and replay.json()['id']==data['id'] and replay.json()['replayed']
    history=client.get('/api/v1/chats/'+data['chat_id'],headers={'X-Wardrobe-Profile-Id':pid});assert history.status_code==200,history.text
    assert history.json()['recommendation']['score_metadata']==data['score_metadata']
    assert not calls,'Mixed capture opened an external media resolver instead of using locked metadata.'
    with s.connection() as c:assert c.execute('select count(*) from phase2nd_mixed_proofs').fetchone()[0]==1
    assert post(client,pid,'I want black trousers.',key).status_code==409


def test_transaction_media_capture_refuses_changed_status_and_escape(mixed):
    client,s,pid,ids,_,_=mixed;owner=s.catalog['owner_id']
    with s.connection() as c:mid=c.execute('select preferred_media_id from garments where id=?',(ids['Blue T-shirt'],)).fetchone()[0]
    def changed():
        with s.connection() as c:c.execute("update media_assets set status='unavailable' where id=?",(mid,))
    with pytest.raises((FixtureError,ValueError)):s.recommend(owner,pid,'I need jeans.',uuid.uuid4().hex,before_lock=changed)
    with s.connection() as c:
        c.execute("update media_assets set status='available',storage_key='../outside.png' where id=?",(mid,))
    (s.media.parent/'outside.png').write_bytes(b'not a qualified in-root media source')
    with s.connection() as c:
        with pytest.raises(ValueError,match='media'):s.capture(c,owner,pid)
